"""运行摘要数据模型"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from genomelens.app.errors import messages
from genomelens.core.json_utils import (
    _any_list,
    _dict,
    _dict_list,
    _float,
    _int,
    _str,
    _str_dict,
    _str_list,
)

# endregion


@dataclass(frozen=True)
class CheckToolItem:
    """CheckToolItem(检查工具项)：单个工具/引擎的诊断结果"""

    status: str
    path: str = ""
    message: str = ""
    extra: dict[str, object] = field(default_factory=dict)

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        data: dict[str, object] = {"status": self.status}
        if self.path:
            data["path"] = self.path
        if self.message:
            data["message"] = self.message
        if self.extra:
            data.update(self.extra)
        return data

    @classmethod
    def from_json(cls, data: dict[str, object]) -> CheckToolItem:
        """从 JSON object(JSON 对象) 读取"""

        # 其余扩展字段保留在 extra，避免 check 协议扩展时破坏旧调用方。
        extra = {k: v for k, v in data.items() if k not in {"status", "path", "message"}}
        return cls(
            status=_str(data.get("status")),
            path=_str(data.get("path")),
            message=_str(data.get("message")),
            extra=extra,
        )


@dataclass(frozen=True)
class CheckReport:
    """CheckReport(检查报告)：check 命令的结构化输出"""

    status: str
    blastn: CheckToolItem
    makeblastdb: CheckToolItem
    magick: CheckToolItem
    jcvi_engine: CheckToolItem
    install_attempts: list[dict[str, object]] = field(default_factory=list)
    engine_candidate_names: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "status": self.status,
            "blastn": self.blastn.to_json(),
            "makeblastdb": self.makeblastdb.to_json(),
            "magick": self.magick.to_json(),
            "jcvi_engine": self.jcvi_engine.to_json(),
            "install_attempts": list(self.install_attempts),
            "engine_candidate_names": list(self.engine_candidate_names),
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> CheckReport:
        """从 JSON object(JSON 对象) 读取"""

        def _tool(key: str) -> CheckToolItem:
            item = data.get(key)
            # check 输出层总是期待完整结构，缺项时也要给出 unknown 占位。
            return CheckToolItem.from_json(item) if isinstance(item, dict) else CheckToolItem(status="unknown")

        return cls(
            status=_str(data.get("status")),
            blastn=_tool("blastn"),
            makeblastdb=_tool("makeblastdb"),
            magick=_tool("magick"),
            jcvi_engine=_tool("jcvi_engine"),
            install_attempts=_dict_list(data.get("install_attempts")),
            engine_candidate_names=_str_list(data.get("engine_candidate_names")),
        )


@dataclass(frozen=True)
class PairwiseJobSummary:
    """PairwiseJobSummary(配对子任务摘要)：多物种/reference-vs-targets 中的单对结果"""

    pair_id: str
    species_a_name: str
    species_b_name: str
    status: str
    outdir: str
    run_summary_path: str = ""
    engine_summary_path: str = ""
    blast_table: str = ""
    anchors_path: str = ""
    simple_path: str = ""
    blocks_path: str = ""
    query_bed: str = ""
    subject_bed: str = ""
    final_figures: list[str] = field(default_factory=list)
    error: dict[str, str] | None = None

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        data: dict[str, object] = {
            "pair_id": self.pair_id,
            "species_a_name": self.species_a_name,
            "species_b_name": self.species_b_name,
            "status": self.status,
            "outdir": self.outdir,
        }
        # pairwise 子任务的产物多少取决于工作流，因此按需序列化更利于阅读。
        if self.run_summary_path:
            data["run_summary_path"] = self.run_summary_path
        if self.engine_summary_path:
            data["engine_summary_path"] = self.engine_summary_path
        if self.blast_table:
            data["blast_table"] = self.blast_table
        if self.anchors_path:
            data["anchors_path"] = self.anchors_path
        if self.simple_path:
            data["simple_path"] = self.simple_path
        if self.blocks_path:
            data["blocks_path"] = self.blocks_path
        if self.query_bed:
            data["query_bed"] = self.query_bed
        if self.subject_bed:
            data["subject_bed"] = self.subject_bed
        if self.final_figures:
            data["final_figures"] = list(self.final_figures)
        if self.error is not None:
            data["error"] = dict(self.error)
        return data

    @classmethod
    def from_json(cls, data: dict[str, object]) -> PairwiseJobSummary:
        """从 JSON object(JSON 对象) 读取"""

        error = data.get("error")
        return cls(
            pair_id=_str(data.get("pair_id")),
            species_a_name=_str(data.get("species_a_name")),
            species_b_name=_str(data.get("species_b_name")),
            status=_str(data.get("status")),
            outdir=_str(data.get("outdir")),
            run_summary_path=_str(data.get("run_summary_path")),
            engine_summary_path=_str(data.get("engine_summary_path")),
            blast_table=_str(data.get("blast_table")),
            anchors_path=_str(data.get("anchors_path")),
            simple_path=_str(data.get("simple_path")),
            blocks_path=_str(data.get("blocks_path")),
            query_bed=_str(data.get("query_bed")),
            subject_bed=_str(data.get("subject_bed")),
            final_figures=_str_list(data.get("final_figures")),
            error=_str_dict(error) if isinstance(error, dict) else None,
        )


@dataclass(frozen=True)
class UiBlock:
    """UiBlock(UI 块)：供 GUI/工作台读取的渲染契约"""

    state: str
    progress: float
    primary_figures: list[str]
    summary_path: str
    log_path: str

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "state": self.state,
            "progress": self.progress,
            "primary_figures": list(self.primary_figures),
            "summary_path": self.summary_path,
            "log_path": self.log_path,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> UiBlock:
        """从 JSON object(JSON 对象) 读取"""

        return cls(
            state=_str(data.get("state")),
            progress=_float(data.get("progress"), default=0.0),
            primary_figures=_str_list(data.get("primary_figures")),
            summary_path=_str(data.get("summary_path")),
            log_path=_str(data.get("log_path")),
        )


@dataclass(frozen=True)
class ScoringBlock:
    """ScoringBlock(评分块)：未来 ML Scoring Layer 接入前的占位结构"""

    status: str = "not_run"
    scores: list[object] = field(default_factory=list)
    ranking: list[object] = field(default_factory=list)
    message: str = messages.SCORING_NOT_RUN
    artifact_path: str = ""
    model_version: str = ""

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        return {
            "status": self.status,
            "scores": list(self.scores),
            "ranking": list(self.ranking),
            "message": self.message,
            "artifact_path": self.artifact_path,
            "model_version": self.model_version,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> ScoringBlock:
        """从 JSON object(JSON 对象) 读取"""

        return cls(
            status=_str(data.get("status"), default="not_run"),
            scores=_any_list(data.get("scores")),
            ranking=_any_list(data.get("ranking")),
            message=_str(data.get("message")),
            artifact_path=_str(data.get("artifact_path")),
            model_version=_str(data.get("model_version")),
        )


@dataclass(frozen=True)
class RunSummary:
    """RunSummary(运行摘要)：方法无关的顶层摘要壳

    方法专属字段全部下沉到 `method_data`，由具体方法扩展（如 McscanSummaryExtension）
    负责填充。序列化时 `method_data` 会扁平展开到顶层，从而保持 schema_version=2 的
    JSON 兼容；反序列化时未知字段会被收集回 `method_data`，实现前向兼容。
    """

    status: str
    schema_version: int
    workflow: str
    task: dict[str, object]
    species: list[dict[str, object]]
    final_figures: list[str]
    artifact_index: list[dict[str, object]]
    logs: dict[str, str]
    ui: UiBlock
    scoring: ScoringBlock
    method: str = ""
    method_data: dict[str, object] = field(default_factory=dict)
    analysis_request_path: str = ""

    _KNOWN_TOP_KEYS: ClassVar[set[str]] = {
        "status",
        "schema_version",
        "workflow",
        "task",
        "species",
        "final_figures",
        "artifact_index",
        "logs",
        "ui",
        "scoring",
        "method",
        "method_data",
        "analysis_request_path",
    }

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        data: dict[str, object] = {
            "status": self.status,
            "schema_version": self.schema_version,
            "workflow": self.workflow,
            "task": dict(self.task),
            "species": list(self.species),
            "final_figures": list(self.final_figures),
            "artifact_index": list(self.artifact_index),
            "logs": dict(self.logs),
            "ui": self.ui.to_json(),
            "scoring": self.scoring.to_json(),
        }
        if self.method:
            data["method"] = self.method
        # 方法扩展字段扁平展开，保持与旧版 run_summary.json 字段布局一致
        data.update(self.method_data)
        if self.analysis_request_path:
            data["analysis_request_path"] = self.analysis_request_path
        return data

    @classmethod
    def from_json(cls, data: dict[str, object]) -> RunSummary:
        """从 JSON object(JSON 对象) 读取"""

        method_data = {k: v for k, v in data.items() if k not in cls._KNOWN_TOP_KEYS}
        return cls(
            status=_str(data.get("status")),
            schema_version=_int(data.get("schema_version"), default=2),
            workflow=_str(data.get("workflow")),
            task=_dict(data.get("task")),
            species=_dict_list(data.get("species")),
            final_figures=_str_list(data.get("final_figures")),
            artifact_index=_dict_list(data.get("artifact_index")),
            logs=_str_dict(data.get("logs")),
            ui=UiBlock.from_json(_dict(data.get("ui"))),
            scoring=ScoringBlock.from_json(_dict(data.get("scoring"))),
            method=_str(data.get("method")),
            method_data=method_data,
            analysis_request_path=_str(data.get("analysis_request_path")),
        )
