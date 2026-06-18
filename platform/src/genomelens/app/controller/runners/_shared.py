"""WorkflowController 与 runner 之间共享的辅助函数"""

# region import
from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from genomelens.analysis.methods.mcscan_summary import McscanSummaryExtension
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.app.errors import messages
from genomelens.core.models import ArtifactRecord, GenomeInputSpec, PreparedGenomeInputSpec
from genomelens.core.preprocessing.annotation_preprocessor import preprocess_one, write_preprocessing_summary
from genomelens.core.summary_models import RunSummary, ScoringBlock, UiBlock

# endregion


if TYPE_CHECKING:
    from genomelens.core.jcvi_adapter.adapter_models import JcviRunResult, McscanRequest
    from genomelens.core.summary_models import PairwiseJobSummary
    from genomelens.data.workspace.output_layout import OutputLayout


# region 请求元数据辅助函数
def species_summary(request: McscanRequest) -> list[dict[str, object]]:
    """把 request.species 转成 summary 列表"""

    # 顶层 summary 统一使用 query / subject / additional 三段式角色，兼容现有 pairwise 执行层
    return [
        {
            "name": species.name,
            "role": "query" if index == 0 else "subject" if index == 1 else "additional",
            "input_mode": species.mode,
        }
        for index, species in enumerate(request.species)
    ]


def artifact_record(
    artifact_id: str,
    artifact_type: str,
    path: object,
    produced_by: str,
    *,
    preview: bool = False,
) -> dict[str, object] | None:
    """把单个 artifact 路径转成可序列化记录"""

    if not path:
        return None

    text = str(path)
    suffix = Path(text).suffix.lower().lstrip(".")

    return ArtifactRecord(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        path=text,
        produced_by=produced_by,
        format=suffix,
        preview=preview,
    ).to_json()


def artifact_index(
    request: McscanRequest,
    engine_result: JcviRunResult,
    final_figures: list[str],
    *,
    manifest_path: Path,
    run_log: Path,
) -> list[dict[str, object]]:
    """为 pairwise 结果构建 artifact 索引"""

    records: list[dict[str, object]] = []

    # 这些产物是 CLI、GUI 和后续调试最常用的固定入口，优先放在索引前部
    for artifact_id, artifact_type, value in [
        ("input_manifest", "manifest", manifest_path),
        ("engine_summary", "summary", engine_result.summary_path),
        ("run_log", "log", run_log),
        ("blast_table", "blast_table", engine_result.artifacts.get("blast_table", "")),
        ("anchors", "anchors", engine_result.artifacts.get("anchors", "")),
        ("simple", "simple", engine_result.artifacts.get("simple", "")),
        ("blocks", "blocks", engine_result.artifacts.get("blocks", "")),
    ]:
        record = artifact_record(artifact_id, artifact_type, value, request.jcvi_workflow)
        if record:
            records.append(record)

    for index, figure in enumerate(final_figures, start=1):
        record = artifact_record(f"figure_{index}", "figure", figure, request.jcvi_workflow, preview=True)
        if record:
            records.append(record)

    return records


def scoring_placeholder() -> ScoringBlock:
    """统一的 scoring(评分) 占位块

    注意：这是未来 ML Scoring Layer 接入前的占位。后续把评分结果纳入统一
    artifact/summary schema 时，应从这里开始收口，而不是再在各工作流里手写。
    """

    return ScoringBlock(message=messages.SCORING_NOT_RUN)


def ui_block(
    status: str,
    final_figures: list[str],
    *,
    summary_path: Path,
    log_path: Path,
) -> UiBlock:
    """统一的 ui(界面) 块。GUI/工作台读取的渲染契约，两类工作流共用同一构造"""

    return UiBlock(
        state=status,
        progress=1.0 if status == "SUCCEEDED" else 0.0,
        primary_figures=list(final_figures),
        summary_path=str(summary_path),
        log_path=str(log_path),
    )


def pair_id(species_a_name: str, species_b_name: str) -> str:
    """两个物种名称组成 pair id"""

    return f"{species_a_name}__{species_b_name}"


def copy_pairwise_figures(pair_id: str, figures: list[str], target_dir: Path) -> list[str]:
    """把 pairwise 图件复制到 figures 根目录，并加上 pair 前缀"""

    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []

    for figure in figures:
        source = Path(figure)
        if source.is_file():
            # 顶层 figures 目录按 pair 前缀去重，避免多个子任务都叫 `dotplot.png`
            target = target_dir / f"{pair_id}.{source.name}"
            shutil.copy2(source, target)
            copied.append(str(target))

    return copied


def prepare_inputs(
    set_state: Callable[[WorkflowState], None],
    request: McscanRequest,
    layout: OutputLayout,
) -> tuple[PreparedGenomeInputSpec, PreparedGenomeInputSpec, list[dict[str, object]]]:
    """预处理输入或返回已准备好的输入"""

    def prepare_one(species: GenomeInputSpec) -> tuple[PreparedGenomeInputSpec, dict[str, object] | None]:
        if species.prepared:
            return species.prepared, None

        raw = species.raw
        if raw is None:
            raise RuntimeError(f"{species.name} input was expected but missing")

        result = preprocess_one(species.name, raw.gff, raw.genome, layout.prepared)
        return PreparedGenomeInputSpec(result.bed, result.cds), result.summary

    if request.query.raw or request.subject.raw:
        set_state(WorkflowState.PREPROCESSING_ANNOTATIONS)

    query, query_summary = prepare_one(request.query)
    subject, subject_summary = prepare_one(request.subject)

    # 预处理摘要会进入最终 run_summary，供 GUI/CLI 解释 GFF+FASTA 是如何落到 BED+CDS 的
    summaries = [summary for summary in [query_summary, subject_summary] if summary is not None]
    if summaries:
        write_preprocessing_summary(layout.preprocessing_summary, summaries)

    return query, subject, summaries


def write_run_summary(layout: OutputLayout, summary: RunSummary) -> None:
    """把 run_summary 写入磁盘"""

    layout.run_summary.write_text(json.dumps(summary.to_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_multi_run_summary(
    request: McscanRequest,
    layout: OutputLayout,
    pairwise_jobs: list[PairwiseJobSummary],
    final_figures: list[str],
    *,
    pairing_strategy: str,
    global_figures: list[str] | None = None,
    reference_name: str | None = None,
    native_multi_species: bool = False,
    native_layout: dict[str, object] | None = None,
) -> RunSummary:
    """为 multi-species 或 reference-vs-targets 构造顶层 RunSummary"""

    # 顶层多物种状态以所有子任务是否成功为准；局部失败仍保留已产出的子任务图件
    status = "SUCCEEDED" if all(item.status == "SUCCEEDED" for item in pairwise_jobs) else "FAILED"

    artifact_index = [
        item
        for item in [
            artifact_record("input_manifest", "manifest", layout.manifest, request.jcvi_workflow),
            artifact_record("run_log", "log", layout.logs / "run.log", request.jcvi_workflow),
        ]
        if item
    ]

    # 多物种顶层只归档聚合后的图件，不重复塞入每个子任务的全部中间产物
    for index, figure in enumerate(final_figures, start=1):
        record = artifact_record(f"figure_{index}", "figure", figure, request.jcvi_workflow, preview=True)
        if record:
            artifact_index.append(record)

    extension = McscanSummaryExtension(
        jcvi_backend="jcvi-genomelens-engine",
        jcvi_workflow=request.jcvi_workflow,
        species_count=len(request.species),
        pairing_strategy=pairing_strategy,
        pairwise_jobs=pairwise_jobs,
        global_figures=global_figures or [],
        reference_name=reference_name,
        native_multi_species=native_multi_species,
        native_layout=native_layout,
    )

    return RunSummary(
        status=status,
        schema_version=2,
        workflow="mcscan",
        method="mcscan",
        task=request.task_spec.to_manifest_json(),
        species=species_summary(request),
        final_figures=final_figures,
        artifact_index=artifact_index,
        logs={"run_log": str(layout.logs / "run.log")},
        ui=ui_block(
            status,
            final_figures,
            summary_path=layout.run_summary,
            log_path=layout.logs / "run.log",
        ),
        scoring=scoring_placeholder(),
        method_data=extension.to_dict(),
    )


# endregion
