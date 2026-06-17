"""Reference-vs-targets MCscan runner：参考物种对多个目标物种运行局部共线性"""

# region import
from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from dataclasses import replace

from genomelens.app.controller.runners._shared import (
    build_multi_run_summary,
    copy_pairwise_figures,
    pair_id,
    species_summary,
    write_run_summary,
)
from genomelens.app.controller.runners.pairwise_runner import run_pairwise_mcscan
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.core.jcvi_adapter.adapter_models import McscanRequest
from genomelens.core.summary_models import PairwiseJobSummary, RunSummary
from genomelens.core.validators import validate_request
from genomelens.data.logging.log_setup import close_logging, setup_logging
from genomelens.data.workspace.output_layout import OutputLayout, create_output_layout

# endregion


def _prepare_reference_workspace(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
) -> tuple[OutputLayout, dict[str, object]]:
    """校验请求、创建工作区并写入顶层 manifest"""

    set_state(WorkflowState.VALIDATING_INPUTS)
    validate_request(request)

    set_state(WorkflowState.PREPARING_WORKSPACE)
    layout = create_output_layout(request.outdir, force=request.force)
    setup_logging(layout.logs / "run.log").info("Starting GenomeLens reference-vs-targets workflow")

    reference = request.query
    targets = [request.subject, *request.additional_species]

    # 顶层 manifest 只描述编排关系；真实 pairwise manifest 会在子任务目录里分别写出
    manifest = {
        "schema_version": 2,
        "workflow": "mcscan",
        "task": request.task_spec.to_manifest_json(),
        "species": species_summary(request),
        "pairing_strategy": "reference_vs_targets",
        "pair_count": len(targets),
        "reference_name": reference.name,
        "target_names": [t.name for t in targets],
    }
    layout.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(layout.manifest, layout.inputs / "input_manifest.json")

    return layout, manifest


def _run_reference_pairwise_jobs(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
    layout: OutputLayout,
) -> tuple[list[PairwiseJobSummary], list[str]]:
    """以参考物种为中心，分别与每个目标物种运行 pairwise 子任务"""

    reference = request.query
    targets = [request.subject, *request.additional_species]

    pairwise_jobs: list[PairwiseJobSummary] = []
    final_figures: list[str] = []
    pairwise_root = layout.intermediate / "pairwise"

    for target in targets:
        name = pair_id(reference.name, target.name)
        pair_outdir = pairwise_root / name

        # 每个目标物种都复用同一参考物种，只替换 subject 与输出目录
        pair_request = replace(
            request,
            query=reference,
            subject=target,
            additional_species=[],
            outdir=pair_outdir,
            force=True,
        )

        try:
            pair_summary = run_pairwise_mcscan(set_state, pair_request)
        except Exception as exc:  # noqa: BLE001 - 汇总需要记录单个 pair 失败原因
            pairwise_jobs.append(
                PairwiseJobSummary(
                    pair_id=name,
                    species_a_name=reference.name,
                    species_b_name=target.name,
                    status="FAILED",
                    outdir=str(pair_outdir),
                    run_summary_path=str(pair_outdir / "report" / "run_summary.json"),
                    error={"type": exc.__class__.__name__, "message": str(exc)},
                    final_figures=[],
                )
            )
            continue

        # 顶层结果目录只保留归档图件，子任务目录继续保存完整 pairwise 中间结果
        copied_figures = copy_pairwise_figures(name, list(pair_summary.final_figures), layout.figures)
        final_figures.extend(copied_figures)

        pairwise_jobs.append(
            PairwiseJobSummary(
                pair_id=name,
                species_a_name=reference.name,
                species_b_name=target.name,
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


def _run_reference_vs_targets_mcscan(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
) -> RunSummary:
    """以参考物种为中心，分别与每个目标物种运行局部共线性"""

    layout, _manifest = _prepare_reference_workspace(set_state, request)
    pairwise_jobs, final_figures = _run_reference_pairwise_jobs(set_state, request, layout)

    reference = request.query
    run_summary = build_multi_run_summary(
        request,
        layout,
        pairwise_jobs,
        final_figures,
        pairing_strategy="reference_vs_targets",
        reference_name=reference.name,
    )

    write_run_summary(layout, run_summary)
    set_state(WorkflowState.SUCCEEDED if run_summary.status == "SUCCEEDED" else WorkflowState.FAILED)

    return run_summary


def run_reference_vs_targets_mcscan(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
) -> RunSummary:
    """Run reference-vs-targets MCscan and release task log handles."""

    try:
        return _run_reference_vs_targets_mcscan(set_state, request)
    finally:
        close_logging()
