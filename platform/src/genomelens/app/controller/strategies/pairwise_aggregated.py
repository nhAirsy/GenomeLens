"""Pairwise 聚合多物种策略

当 provider 不声明原生多物种支持时，把 N 个物种拆成多个 pairwise 子任务，
再汇总结果并可选生成全局核型总图。
"""

# region import
from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from dataclasses import replace
from itertools import combinations
from pathlib import Path
from typing import Any, cast

from genomelens.analysis.methods.mcscan_request_mapping import to_mcscan_request
from genomelens.analysis.request_models import AnalysisRequest, AnalysisSpeciesInput
from genomelens.app.controller.runners._shared import (
    build_multi_run_summary,
    copy_pairwise_figures,
    pair_id,
    species_summary,
    write_run_summary,
)
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.app.controller.workflow_provider import WorkflowProvider
from genomelens.app.events.signal_bus import SignalBus
from genomelens.core.jcvi_adapter.adapter import JcviEngineAdapter
from genomelens.core.jcvi_adapter.adapter_models import McscanRequest
from genomelens.core.services.layout_optimizer import LayoutOptimizer, NoOpLayoutOptimizer
from genomelens.core.summary_models import PairwiseJobSummary, RunSummary
from genomelens.data.logging.log_setup import close_logging, setup_logging
from genomelens.data.workspace.output_layout import OutputLayout, create_output_layout
from genomelens.toolchain.runtime.resource_locator import locate_engine

# endregion


def _set_state(signal_bus: SignalBus, state: WorkflowState) -> None:
    """通过 signal_bus 发射状态事件"""

    signal_bus.emit("state", state=state.value)


def _build_global_karyotype(
    request: McscanRequest,
    pairwise_jobs: list[PairwiseJobSummary],
    layout: OutputLayout,
) -> list[str]:
    """把成功 pairwise 的 simple 边聚合成一张全局核型总图"""

    species_order = [item.name for item in request.species]
    track_index = {name: index for index, name in enumerate(species_order)}
    track_beds: dict[str, str] = {}
    edges: list[dict[str, object]] = []

    for job in pairwise_jobs:
        if job.status != "SUCCEEDED":
            continue

        simple = job.simple_path
        query_bed = job.query_bed
        subject_bed = job.subject_bed
        name_a = job.species_a_name
        name_b = job.species_b_name

        if not (simple and query_bed and subject_bed and Path(simple).is_file()):
            continue
        if name_a not in track_index or name_b not in track_index:
            continue

        track_beds.setdefault(name_a, query_bed)
        track_beds.setdefault(name_b, subject_bed)
        edges.append({"i": track_index[name_a], "j": track_index[name_b], "simple": simple})

    usable_tracks = [name for name in species_order if name in track_beds]
    if len(usable_tracks) < 2 or not edges:
        return []

    compact_index = {name: index for index, name in enumerate(usable_tracks)}
    tracks = [{"name": name, "bed": track_beds[name]} for name in usable_tracks]
    remapped_edges: list[dict[str, object]] = []

    for edge in edges:
        name_a = species_order[int(cast(int, edge["i"]))]
        name_b = species_order[int(cast(int, edge["j"]))]
        if name_a in compact_index and name_b in compact_index:
            remapped_edges.append({"i": compact_index[name_a], "j": compact_index[name_b], "simple": edge["simple"]})

    if not remapped_edges:
        return []

    try:
        engine = locate_engine(explicit=request.jcvi_engine)
        if not engine.ok:
            return []

        adapter = JcviEngineAdapter(engine.path)
        global_dir = layout.intermediate / "global_karyotype"
        global_dir.mkdir(parents=True, exist_ok=True)

        manifest = adapter.build_global_karyotype_manifest(
            tracks=tracks,
            edges=remapped_edges,
            blastn_path=request.blastn_path,
            makeblastdb_path=request.makeblastdb_path,
            formats=request.formats,
            task={"workflow": "graphics_karyotype_global", "task_type": "global_synteny"},
            species=species_summary(request),
        )
        manifest_path = global_dir / "global_manifest.json"
        adapter.write_manifest(manifest, manifest_path)
        result = adapter.run_manifest(manifest_path, global_dir)
        figures = cast(
            list[Any],
            result.artifacts.get("global_karyotype_figures") or result.artifacts.get("figures") or [],
        )

        return copy_pairwise_figures("global", [str(item) for item in figures], layout.figures)
    except Exception:  # noqa: BLE001 - 总图是增量产物，失败不应影响已成功的 pairwise 结果
        return []


def _prepare_workspace(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
    pairing_strategy: str,
    pair_count: int,
    reference_name: str | None,
    target_names: list[str] | None,
) -> tuple[OutputLayout, dict[str, object]]:
    """校验请求、创建工作区并写入顶层 manifest"""

    set_state(WorkflowState.VALIDATING_INPUTS)
    # 依赖 provider 在执行子任务前完成校验，这里只做工作区准备

    set_state(WorkflowState.PREPARING_WORKSPACE)
    layout = create_output_layout(request.outdir, force=request.force)
    setup_logging(layout.logs / "run.log").info("Starting GenomeLens %s workflow", pairing_strategy)

    manifest: dict[str, object] = {
        "schema_version": 2,
        "workflow": "mcscan",
        "task": request.task_spec.to_manifest_json(),
        "species": species_summary(request),
        "pairing_strategy": pairing_strategy,
        "pair_count": pair_count,
    }
    if reference_name is not None:
        manifest["reference_name"] = reference_name
    if target_names is not None:
        manifest["target_names"] = target_names

    layout.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(layout.manifest, layout.inputs / "input_manifest.json")

    return layout, manifest


def _narrow_request(
    request: AnalysisRequest,
    query: AnalysisSpeciesInput,
    subject: AnalysisSpeciesInput,
    pair_outdir: Path,
) -> AnalysisRequest:
    """把原始请求收缩为只包含两个物种的 pairwise 请求，并指向独立的子任务输出目录"""

    new_input = replace(request.input, species=[query, subject], reference_index=0)
    new_output = replace(request.output, directory=str(pair_outdir), force=True)
    return replace(request, input=new_input, output=new_output)


def _pair_species_for_mode(
    request: AnalysisRequest,
) -> tuple[str, list[tuple[AnalysisSpeciesInput, AnalysisSpeciesInput]]]:
    """根据请求特征决定配对模式，并返回 (mode, pairs)"""

    species = request.input.species
    target_gene_ids = request.method_config.get("target_gene_ids") or []

    if target_gene_ids:
        reference_index = request.input.reference_index
        reference = species[reference_index]
        targets = species[:reference_index] + species[reference_index + 1 :]
        pairs = [(reference, target) for target in targets]
        return "reference_vs_targets", pairs

    pairs = list(combinations(species, 2))
    return "all_vs_all_pairwise", pairs


def _run_pairwise_jobs(
    set_state: Callable[[WorkflowState], None],
    original_request: AnalysisRequest,
    provider: WorkflowProvider,
    layout: OutputLayout,
    signal_bus: SignalBus,
) -> tuple[list[PairwiseJobSummary], list[str]]:
    """把多物种请求拆成 pairwise 子任务并逐个执行"""

    mode, pairs = _pair_species_for_mode(original_request)
    pairwise_jobs: list[PairwiseJobSummary] = []
    final_figures: list[str] = []
    pairwise_root = layout.intermediate / "pairwise"

    for query, subject in pairs:
        name = pair_id(query.name, subject.name)
        pair_outdir = pairwise_root / name

        pair_request = _narrow_request(original_request, query, subject, pair_outdir)

        try:
            pair_summary = provider.run(pair_request, signal_bus)
        except Exception as exc:  # noqa: BLE001 - 汇总需要记录单个 pairwise 子任务失败原因
            pairwise_jobs.append(
                PairwiseJobSummary(
                    pair_id=name,
                    species_a_name=query.name,
                    species_b_name=subject.name,
                    status="FAILED",
                    outdir=str(pair_outdir),
                    run_summary_path=str(pair_outdir / "report" / "run_summary.json"),
                    error={"type": exc.__class__.__name__, "message": str(exc)},
                    final_figures=[],
                )
            )
            continue

        # 子任务产物路径现在存放在 RunSummary.method_data 中
        md = pair_summary.method_data
        copied_figures = copy_pairwise_figures(name, list(pair_summary.final_figures), layout.figures)
        final_figures.extend(copied_figures)

        pairwise_jobs.append(
            PairwiseJobSummary(
                pair_id=name,
                species_a_name=query.name,
                species_b_name=subject.name,
                status=pair_summary.status,
                outdir=str(pair_outdir),
                run_summary_path=str(pair_outdir / "report" / "run_summary.json"),
                engine_summary_path=str(md.get("engine_summary_path", "")),
                blast_table=str(md.get("blast_table", "")),
                anchors_path=str(md.get("anchors_path", "")),
                simple_path=str(md.get("simple_path", "")),
                blocks_path=str(md.get("blocks_path", "")),
                query_bed=str(md.get("query_bed", "")),
                subject_bed=str(md.get("subject_bed", "")),
                final_figures=copied_figures,
            )
        )

    return pairwise_jobs, final_figures


def _build_edges_for_layout_optimizer(
    pairwise_jobs: list[PairwiseJobSummary],
) -> list[dict[str, object]]:
    """从成功的 pairwise 子任务中提取 simple 边，供布局优化器使用"""

    edges: list[dict[str, object]] = []
    for job in pairwise_jobs:
        if job.status != "SUCCEEDED":
            continue
        simple = job.simple_path
        if not (simple and Path(simple).is_file()):
            continue
        edges.append(
            {
                "source": job.species_a_name,
                "target": job.species_b_name,
                "simple": simple,
            }
        )
    return edges


class PairwiseAggregatedMultiSpecies:
    """PairwiseAggregatedMultiSpecies：把多物种任务拆成 pairwise 子任务并汇总"""

    def __init__(self, layout_optimizer: LayoutOptimizer | None = None) -> None:
        self._layout_optimizer = layout_optimizer or NoOpLayoutOptimizer()

    def execute(
        self,
        request: AnalysisRequest,
        provider: WorkflowProvider,
        signal_bus: SignalBus,
    ) -> RunSummary:
        """Execute pairwise aggregation and release task log handles."""

        try:
            return self._execute(request, provider, signal_bus)
        finally:
            close_logging()

    def _execute(
        self,
        request: AnalysisRequest,
        provider: WorkflowProvider,
        signal_bus: SignalBus,
    ) -> RunSummary:
        """执行 pairwise 聚合的多物种分析"""

        mcscan_request = to_mcscan_request(request)
        mode, pairs = _pair_species_for_mode(request)

        reference_name: str | None = None
        target_names: list[str] | None = None
        if mode == "reference_vs_targets":
            reference = request.input.species[request.input.reference_index]
            reference_name = reference.name
            target_names = [subject.name for _query, subject in pairs]

        def set_state(state: WorkflowState) -> None:
            _set_state(signal_bus, state)

        layout, _manifest = _prepare_workspace(
            set_state,
            mcscan_request,
            pairing_strategy=mode,
            pair_count=len(pairs),
            reference_name=reference_name,
            target_names=target_names,
        )
        pairwise_jobs, final_figures = _run_pairwise_jobs(set_state, request, provider, layout, signal_bus)

        edges = _build_edges_for_layout_optimizer(pairwise_jobs)
        layout_result = self._layout_optimizer.optimize(mcscan_request.species, edges)

        global_figures = _build_global_karyotype(mcscan_request, pairwise_jobs, layout)
        final_figures.extend(global_figures)

        run_summary = build_multi_run_summary(
            mcscan_request,
            layout,
            pairwise_jobs,
            final_figures,
            pairing_strategy=mode,
            global_figures=global_figures,
            reference_name=reference_name,
            native_layout=layout_result,
        )

        write_run_summary(layout, run_summary)
        set_state(WorkflowState.SUCCEEDED if run_summary.status == "SUCCEEDED" else WorkflowState.FAILED)

        return run_summary
