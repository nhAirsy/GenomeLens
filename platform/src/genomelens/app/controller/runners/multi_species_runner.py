"""Multi-species MCscan runner：多物种拆成多个 pairwise 并汇总全局核型总图"""

# region import
from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from dataclasses import replace
from itertools import combinations
from pathlib import Path
from typing import Any, cast

from genomelens.app.controller.runners._shared import (
    build_multi_run_summary,
    copy_pairwise_figures,
    pair_id,
    species_summary,
    write_run_summary,
)
from genomelens.app.controller.runners.pairwise_runner import run_pairwise_mcscan
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.core.jcvi_adapter.adapter import JcviEngineAdapter
from genomelens.core.jcvi_adapter.adapter_models import McscanRequest
from genomelens.core.summary_models import PairwiseJobSummary, RunSummary
from genomelens.core.validators import validate_request
from genomelens.data.logging.log_setup import close_logging, setup_logging
from genomelens.data.workspace.output_layout import OutputLayout, create_output_layout
from genomelens.toolchain.runtime.resource_locator import locate_engine

# endregion


def _build_global_karyotype(
    request: McscanRequest,
    pairwise_jobs: list[PairwiseJobSummary],
    layout: OutputLayout,
) -> list[str]:
    """把成功 pairwise(两两比较) 的 simple 边聚合成一张全局核型总图

    track(轨道) 顺序按 `request.species` 固定；只有当至少两个物种、且至少有一条
    成功 pairwise 的 simple 边可用时才生成总图。任何一步失败都不影响已产出的
    pairwise 结果，只是跳过总图。
    """

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

        # 总图只依赖各 pairwise 成功产出的 simple 边与 BED，不重新回溯原始输入
        track_beds.setdefault(name_a, query_bed)
        track_beds.setdefault(name_b, subject_bed)
        edges.append({"i": track_index[name_a], "j": track_index[name_b], "simple": simple})

    # 至少两个轨道有 bed、且至少一条边，才有总图可画
    usable_tracks = [name for name in species_order if name in track_beds]
    if len(usable_tracks) < 2 or not edges:
        return []

    # 重新映射 track 下标到「实际有 bed 的轨道」的连续下标空间
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

        # 总图也走顶层 figures 归档，保持和 pairwise 图件相同的用户可见位置
        return copy_pairwise_figures("global", [str(item) for item in figures], layout.figures)
    except Exception:  # noqa: BLE001 - 总图是增量产物，失败不应影响已成功的 pairwise 结果
        return []


def _prepare_multi_species_workspace(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
) -> tuple[OutputLayout, dict[str, object]]:
    """校验请求、创建工作区并写入顶层 manifest"""

    set_state(WorkflowState.VALIDATING_INPUTS)
    validate_request(request)

    set_state(WorkflowState.PREPARING_WORKSPACE)
    layout = create_output_layout(request.outdir, force=request.force)
    setup_logging(layout.logs / "run.log").info("Starting GenomeLens multi-species workflow")

    manifest = {
        "schema_version": 2,
        "workflow": "mcscan",
        "task": request.task_spec.to_manifest_json(),
        "species": species_summary(request),
        "pairing_strategy": "all_vs_all_pairwise",
        "pair_count": len(request.species) * (len(request.species) - 1) // 2,
    }
    layout.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(layout.manifest, layout.inputs / "input_manifest.json")

    return layout, manifest


def _run_multi_pairwise_jobs(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
    layout: OutputLayout,
) -> tuple[list[PairwiseJobSummary], list[str]]:
    """把多物种拆成多个 pairwise 子任务运行，汇总各子任务产物"""

    pairwise_jobs: list[PairwiseJobSummary] = []
    final_figures: list[str] = []
    pairwise_root = layout.intermediate / "pairwise"

    for query, subject in combinations(request.species, 2):
        name = pair_id(query.name, subject.name)
        pair_outdir = pairwise_root / name

        # 多物种顶层 request 在这里被收缩成单对 request，pairwise runner 无需知道全局上下文
        pair_request = replace(
            request,
            query=query,
            subject=subject,
            additional_species=[],
            outdir=pair_outdir,
            force=True,
        )

        try:
            pair_summary = run_pairwise_mcscan(set_state, pair_request)
        except Exception as exc:  # noqa: BLE001 - 多物种汇总需要记录单个 pairwise 子任务失败原因
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

        # 每对图件复制到顶层 results/figures，同时保留原 pairwise 目录中的完整结果
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
                engine_summary_path=str(pair_summary.method_data.get("engine_summary_path", "")),
                blast_table=str(pair_summary.method_data.get("blast_table", "")),
                anchors_path=str(pair_summary.method_data.get("anchors_path", "")),
                simple_path=str(pair_summary.method_data.get("simple_path", "")),
                blocks_path=str(pair_summary.method_data.get("blocks_path", "")),
                query_bed=str(pair_summary.method_data.get("query_bed", "")),
                subject_bed=str(pair_summary.method_data.get("subject_bed", "")),
                final_figures=copied_figures,
            )
        )

    return pairwise_jobs, final_figures


def _run_multi_species_mcscan(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
) -> RunSummary:
    """把多物种任务拆成多个 pairwise(两两比较) 任务并汇总结果"""

    layout, _manifest = _prepare_multi_species_workspace(set_state, request)
    pairwise_jobs, final_figures = _run_multi_pairwise_jobs(set_state, request, layout)

    global_figures = _build_global_karyotype(request, pairwise_jobs, layout)
    final_figures.extend(global_figures)

    run_summary = build_multi_run_summary(
        request,
        layout,
        pairwise_jobs,
        final_figures,
        pairing_strategy="all_vs_all_pairwise",
        global_figures=global_figures,
    )

    write_run_summary(layout, run_summary)
    set_state(WorkflowState.SUCCEEDED if run_summary.status == "SUCCEEDED" else WorkflowState.FAILED)

    return run_summary


def run_multi_species_mcscan(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
) -> RunSummary:
    """Run multi-species MCscan and release task log handles."""

    try:
        return _run_multi_species_mcscan(set_state, request)
    finally:
        close_logging()
