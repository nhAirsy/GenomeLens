"""Pairwise MCscan runner：两个物种的真实 JCVI 工作流"""

# region import
from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import replace
from typing import Any, cast

from genomelens.analysis.methods.mcscan_summary import McscanSummaryExtension
from genomelens.app.controller.runners._shared import (
    artifact_index as build_artifact_index,
)
from genomelens.app.controller.runners._shared import (
    prepare_inputs,
    scoring_placeholder,
    species_summary,
    ui_block,
    write_run_summary,
)
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.app.errors import messages
from genomelens.app.errors.error_codes import ErrorCode
from genomelens.app.errors.exceptions import ToolchainError
from genomelens.core.jcvi_adapter.adapter import JcviEngineAdapter
from genomelens.core.jcvi_adapter.adapter_models import JcviRunResult, McscanRequest
from genomelens.core.models import PreparedGenomeInputSpec
from genomelens.core.summary_models import RunSummary
from genomelens.core.validators import validate_request
from genomelens.core.visualization.figure_archiver import archive_figures
from genomelens.data.logging.log_setup import close_logging, setup_logging
from genomelens.data.workspace.output_layout import OutputLayout, create_output_layout
from genomelens.toolchain.runtime.platform_names import (
    blastn_candidates,
    lastal_candidates,
    lastdb_candidates,
    makeblastdb_candidates,
)
from genomelens.toolchain.runtime.resource_locator import (
    LocatedResource,
    locate_engine,
    locate_tool,
)
from genomelens.toolchain.runtime.toolchain_installer import install_toolchain

# endregion


def _prepare_pairwise_inputs(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
) -> tuple[OutputLayout, McscanRequest, PreparedGenomeInputSpec, PreparedGenomeInputSpec, list[dict[str, object]]]:
    """校验请求、准备工作区并预处理输入"""

    validate_request(request)
    if len(request.species) != 2:
        raise ToolchainError(
            "pairwise runner 只接受两个物种",
            code=ErrorCode.REQUEST_INVALID,
        )

    set_state(WorkflowState.PREPARING_WORKSPACE)
    layout = create_output_layout(request.outdir, force=request.force)
    logger = setup_logging(layout.logs / "run.log")
    logger.info("Starting GenomeLens workflow")

    query, subject, preprocess_summaries = prepare_inputs(set_state, request, layout)

    effective_request = request
    if request.target_gene_ids:
        # pairwise runner 是局部共线性的唯一入口，带目标基因时在这里切换到底层 local_synteny workflow
        effective_request = replace(request, jcvi_workflow="local_synteny")

    return layout, effective_request, query, subject, preprocess_summaries


def _resolve_pairwise_toolchain(
    request: McscanRequest,
) -> tuple[LocatedResource, LocatedResource, LocatedResource, str, str]:
    """定位引擎与 BLAST/LAST 工具链，必要时自动安装 BLAST+"""

    engine = locate_engine(explicit=request.jcvi_engine)
    blastn = locate_tool("blast", explicit=request.blastn_path, packaged_names=blastn_candidates())
    makeblastdb = locate_tool("blast", explicit=request.makeblastdb_path, packaged_names=makeblastdb_candidates())

    if not blastn.ok or not makeblastdb.ok:
        # BLAST+ 是当前主链必需依赖，因此先尝试自动安装，再决定是否报错
        install_result = install_toolchain("blast")
        if not install_result.ok:
            raise ToolchainError(
                messages.TOOLCHAIN_BLAST_NOT_FOUND.format(message=install_result.message),
            )
        blastn = locate_tool("blast", explicit=request.blastn_path, packaged_names=blastn_candidates())
        makeblastdb = locate_tool("blast", explicit=request.makeblastdb_path, packaged_names=makeblastdb_candidates())

    lastal_path = ""
    lastdb_path = ""
    if request.align_soft == "last":
        lastal = locate_tool("last", explicit=request.lastal_path, packaged_names=lastal_candidates())
        lastdb = locate_tool("last", explicit=request.lastdb_path, packaged_names=lastdb_candidates())
        if not lastal.ok or not lastdb.ok:
            raise ToolchainError(
                messages.TOOLCHAIN_LAST_NOT_FOUND,
                code=ErrorCode.TOOLCHAIN_MISSING,
            )
        lastal_path = lastal.path
        lastdb_path = lastdb.path

    if not engine.ok:
        raise ToolchainError(
            messages.TOOLCHAIN_ENGINE_NOT_FOUND.format(message=engine.message),
        )
    if not blastn.ok:
        raise ToolchainError(
            messages.TOOLCHAIN_GENERIC_NOT_FOUND.format(message=blastn.message),
        )
    if not makeblastdb.ok:
        raise ToolchainError(
            messages.TOOLCHAIN_GENERIC_NOT_FOUND.format(message=makeblastdb.message),
        )

    return engine, blastn, makeblastdb, lastal_path, lastdb_path


def _resolve_pairwise_task_and_species(
    engine_result: JcviRunResult,
    manifest: dict[str, object],
    request: McscanRequest,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """优先使用引擎返回的 task/species，缺失时回退到 manifest 或请求本身"""

    # 公开摘要优先信任引擎实际回报，只有缺字段时才回退到 shell 侧已知信息
    task = engine_result.task or (
        cast(dict[str, object], manifest.get("task"))
        if isinstance(manifest.get("task"), dict)
        else request.task_spec.to_manifest_json()
    )
    species = engine_result.species or (
        cast(list[dict[str, object]], manifest.get("species"))
        if isinstance(manifest.get("species"), list)
        else species_summary(request)
    )
    return task, species


def _build_pairwise_run_summary(
    request: McscanRequest,
    effective_request: McscanRequest,
    layout: OutputLayout,
    engine_result: JcviRunResult,
    manifest: dict[str, object],
    engine: LocatedResource,
    probe: dict[str, object],
    query: PreparedGenomeInputSpec,
    subject: PreparedGenomeInputSpec,
    preprocess_summaries: list[dict[str, object]],
    final_figures: list[str],
    status: str,
) -> RunSummary:
    """根据 pairwise 运行结果构造 RunSummary"""

    run_log = layout.logs / "run.log"
    task, species = _resolve_pairwise_task_and_species(engine_result, manifest, request)

    artifact_index = build_artifact_index(
        effective_request,
        engine_result,
        final_figures,
        manifest_path=layout.manifest,
        run_log=run_log,
    )

    extension = McscanSummaryExtension(
        jcvi_backend="jcvi-genomelens-engine",
        jcvi_workflow=effective_request.jcvi_workflow,
        jcvi_engine_path=engine.path,
        jcvi_distribution=engine_result.distribution or str(probe.get("distribution", "")),
        jcvi_engine_version=engine_result.engine_version or str(probe.get("engine_version", "")),
        jcvi_upstream_version=engine_result.jcvi_upstream_version or str(probe.get("jcvi_upstream_version", "")),
        jcvi_patchset=engine_result.patchset or str(probe.get("patchset", "")),
        jcvi_runtime_mode=engine_result.runtime_mode or str(probe.get("runtime_mode", "")),
        jcvi_loaded_extensions=engine_result.loaded_extensions or cast(list[str], probe.get("loaded_extensions", [])),
        jcvi_missing_extensions=engine_result.missing_extensions
        or cast(list[str], probe.get("missing_extensions", [])),
        engine_summary_path=str(engine_result.summary_path),
        blast_table=str(engine_result.artifacts.get("blast_table", "")),
        anchors_path=str(engine_result.artifacts.get("anchors", "")),
        simple_path=str(engine_result.artifacts.get("simple", "")),
        blocks_path=str(engine_result.artifacts.get("blocks", "")),
        query_bed=str(query.bed),
        subject_bed=str(subject.bed),
        preprocess_summaries=preprocess_summaries,
        preprocessing_summary_path=str(layout.preprocessing_summary) if preprocess_summaries else "",
        simplified_fallback=bool(engine_result.artifacts.get("simplified_fallback", False)),
        species_a_name=request.query.name,
        species_b_name=request.subject.name,
        species_a_input_mode=request.query.mode,
        species_b_input_mode=request.subject.mode,
        species_a_bed=str(query.bed),
        species_b_bed=str(subject.bed),
    )

    return RunSummary(
        status=status,
        schema_version=2,
        workflow="mcscan",
        method="mcscan",
        task=task,
        species=species,
        final_figures=final_figures,
        artifact_index=artifact_index,
        logs={"run_log": str(run_log)},
        ui=ui_block(status, final_figures, summary_path=layout.run_summary, log_path=run_log),
        scoring=scoring_placeholder(),
        method_data=extension.to_dict(),
    )


def _run_pairwise_mcscan(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
) -> RunSummary:
    """运行一对物种的真实 JCVI 工作流并写出 `run_summary.json`"""

    set_state(WorkflowState.VALIDATING_INPUTS)
    layout, effective_request, query, subject, preprocess_summaries = _prepare_pairwise_inputs(set_state, request)

    set_state(WorkflowState.CHECKING_TOOLCHAIN)
    engine, blastn, makeblastdb, lastal_path, lastdb_path = _resolve_pairwise_toolchain(effective_request)

    adapter = JcviEngineAdapter(engine.path)
    probe = adapter.probe()

    set_state(WorkflowState.WRITING_MANIFEST)
    manifest = adapter.build_manifest(
        effective_request,
        query=query,
        subject=subject,
        blastn_path=blastn.path,
        makeblastdb_path=makeblastdb.path,
        lastal_path=lastal_path,
        lastdb_path=lastdb_path,
    )
    adapter.write_manifest(manifest, layout.manifest)
    shutil.copy2(layout.manifest, layout.inputs / "input_manifest.json")

    set_state(WorkflowState.RUNNING_ENGINE)
    engine_result = adapter.run_manifest(layout.manifest, layout.jcvi)

    set_state(WorkflowState.FINALIZING)
    figures = cast(list[Any], engine_result.artifacts.get("figures") or [])

    # engine 内部图件先落在中间目录，再统一归档到 results/figures 供用户与 GUI 消费
    final_figures = archive_figures([str(item) for item in figures], layout.figures)
    status = "SUCCEEDED" if engine_result.status == "ok" else "FAILED"

    run_summary = _build_pairwise_run_summary(
        request,
        effective_request,
        layout,
        engine_result,
        manifest,
        engine,
        probe,
        query,
        subject,
        preprocess_summaries,
        final_figures,
        status,
    )

    write_run_summary(layout, run_summary)
    set_state(WorkflowState.SUCCEEDED if run_summary.status == "SUCCEEDED" else WorkflowState.FAILED)

    return run_summary


def run_pairwise_mcscan(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
) -> RunSummary:
    """Run pairwise MCscan and release task log handles."""

    try:
        return _run_pairwise_mcscan(set_state, request)
    finally:
        close_logging()
