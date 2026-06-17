"""统一 analysis request(分析请求) 数据模型"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field

from genomelens.core.json_utils import (
    _bool,
    _dict,
    _dict_list,
    _float,
    _int,
    _nested,
    _optional_int,
    _str,
    _str_list,
)

# endregion


@dataclass(frozen=True)
class AnalysisSpeciesInput:
    """AnalysisSpeciesInput(分析物种输入)：单个物种的文件描述"""

    name: str
    input_mode: str
    bed: str = ""
    cds: str = ""
    gff: str = ""
    genome: str = ""

    def to_json(self) -> dict[str, object]:
        """转为 JSON object(JSON 对象)"""

        data: dict[str, object] = {
            "name": self.name,
            "input_mode": self.input_mode,
        }
        for key, value in {
            "bed": self.bed,
            "cds": self.cds,
            "gff": self.gff,
            "genome": self.genome,
        }.items():
            if value:
                data[key] = value
        return data

    @classmethod
    def from_json(cls, data: dict[str, object]) -> AnalysisSpeciesInput:
        """从 JSON object(JSON 对象) 读取"""

        return cls(
            name=_str(data.get("name")),
            input_mode=_str(data.get("input_mode")),
            bed=_str(data.get("bed")),
            cds=_str(data.get("cds")),
            gff=_str(data.get("gff")),
            genome=_str(data.get("genome")),
        )


@dataclass(frozen=True)
class AnalysisInput:
    """AnalysisInput(分析输入)：输入模式、目录与物种列表"""

    mode: str
    directory: str = ""
    species: list[AnalysisSpeciesInput] = field(default_factory=list)
    reference_index: int = 0

    def to_json(self) -> dict[str, object]:
        data: dict[str, object] = {
            "mode": self.mode,
            "directory": self.directory,
            "species": [item.to_json() for item in self.species],
        }
        # 默认 reference_index 为 0，省略可保持请求体精简并兼容旧版本
        if self.reference_index != 0:
            data["reference_index"] = self.reference_index
        return data

    @classmethod
    def from_json(cls, data: dict[str, object]) -> AnalysisInput:
        species = _dict_list(data.get("species"))

        return cls(
            mode=_str(data.get("mode")),
            directory=_str(data.get("directory")),
            species=[AnalysisSpeciesInput.from_json(item) for item in species],
            reference_index=_int(data.get("reference_index"), default=0),
        )


@dataclass(frozen=True)
class AnalysisOutput:
    """AnalysisOutput(分析输出)：输出目录、覆盖策略和格式"""

    directory: str
    force: bool = False
    formats: list[str] = field(default_factory=lambda: ["png"])

    def to_json(self) -> dict[str, object]:
        return {
            "directory": self.directory,
            "force": self.force,
            "formats": self.formats,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> AnalysisOutput:
        return cls(
            directory=_str(data.get("directory")),
            force=_bool(data.get("force"), default=False),
            formats=_str_list(data.get("formats"), default=["png"]),
        )


@dataclass(frozen=True)
class AnalysisConfigRef:
    """AnalysisConfigRef(分析配置引用)：主配置与方法配置路径"""

    project_config: str = ""
    method_config: str = ""

    def to_json(self) -> dict[str, object]:
        return {
            "project_config": self.project_config,
            "method_config": self.method_config,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> AnalysisConfigRef:
        return cls(
            project_config=_str(data.get("project_config")),
            method_config=_str(data.get("method_config")),
        )


@dataclass(frozen=True)
class AnalysisOptions:
    """AnalysisOptions(分析选项)：方法无关的通用可调参数

    注意：方法专属参数（如 JCVI 的 workflow/blastn/seqids）不放在这里，而是下沉到
    `AnalysisRequest.method_config`。新方法接入时只定义自己的 method config 类型，
    不应再向本类添加字段。
    """

    preset: str = "auto"
    threads: int | None = None
    min_block_size: int | None = None

    def to_json(self) -> dict[str, object]:
        return {
            "preset": self.preset,
            "threads": self.threads,
            "min_block_size": self.min_block_size,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> AnalysisOptions:
        return cls(
            preset=_str(data.get("preset"), default="auto"),
            threads=_optional_int(data.get("threads")),
            min_block_size=_optional_int(data.get("min_block_size")),
        )


@dataclass(frozen=True)
class McscanMethodConfig:
    """McscanMethodConfig(mcscan 方法配置)：mcscan/JCVI 方法专属的内联载荷

    这是 `AnalysisRequest.method_config` 在 method=mcscan 时的具体形态。其他方法
    （syri / pangenome 等）接入时各自定义对应的 method config 类型，互不污染。
    """

    workflow: str = "graphics_synteny"
    jcvi_engine: str = ""
    blastn: str = ""
    makeblastdb: str = ""
    jcvi_layout: str = ""
    jcvi_seqids: str = ""
    allow_simplified_fallback: bool = False
    # 同源搜索与共线性参数
    align_soft: str = "blast"
    dbtype: str = "nucl"
    cscore: float = 0.7
    dist: int = 20
    iter: int = 1
    # 目标基因局部共线性参数
    target_gene_ids: list[str] = field(default_factory=list)
    up: int = 20
    down: int = 20
    split_targets: bool = False
    label_targets: bool = False
    # 图件样式参数
    glyphstyle: str = ""
    glyphcolor: str = ""
    shadestyle: str = ""
    figsize: str = ""
    dpi: int = 300

    def to_json(self) -> dict[str, object]:
        return {
            "workflow": self.workflow,
            "jcvi_engine": self.jcvi_engine,
            "blastn": self.blastn,
            "makeblastdb": self.makeblastdb,
            "jcvi_layout": self.jcvi_layout,
            "jcvi_seqids": self.jcvi_seqids,
            "allow_simplified_fallback": self.allow_simplified_fallback,
            "align_soft": self.align_soft,
            "dbtype": self.dbtype,
            "cscore": self.cscore,
            "dist": self.dist,
            "iter": self.iter,
            "target_gene_ids": list(self.target_gene_ids),
            "up": self.up,
            "down": self.down,
            "split_targets": self.split_targets,
            "label_targets": self.label_targets,
            "glyphstyle": self.glyphstyle,
            "glyphcolor": self.glyphcolor,
            "shadestyle": self.shadestyle,
            "figsize": self.figsize,
            "dpi": self.dpi,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> McscanMethodConfig:
        return cls(
            workflow=_str(data.get("workflow"), default="graphics_synteny"),
            jcvi_engine=_str(data.get("jcvi_engine")),
            blastn=_str(data.get("blastn")),
            makeblastdb=_str(data.get("makeblastdb")),
            jcvi_layout=_str(data.get("jcvi_layout")),
            jcvi_seqids=_str(data.get("jcvi_seqids")),
            allow_simplified_fallback=_bool(data.get("allow_simplified_fallback"), default=False),
            align_soft=_str(data.get("align_soft"), default="blast"),
            dbtype=_str(data.get("dbtype"), default="nucl"),
            cscore=_float(data.get("cscore"), default=0.7),
            dist=_int(data.get("dist"), default=20),
            iter=_int(data.get("iter"), default=1),
            target_gene_ids=_str_list(data.get("target_gene_ids")),
            up=_int(data.get("up"), default=20),
            down=_int(data.get("down"), default=20),
            split_targets=_bool(data.get("split_targets"), default=False),
            label_targets=_bool(data.get("label_targets"), default=False),
            glyphstyle=_str(data.get("glyphstyle")),
            glyphcolor=_str(data.get("glyphcolor")),
            shadestyle=_str(data.get("shadestyle")),
            figsize=_str(data.get("figsize")),
            dpi=_int(data.get("dpi"), default=300),
        )


@dataclass(frozen=True)
class AnalysisRequest:
    """AnalysisRequest(分析请求)：CLI、GUI、插件和 Agent 共用的稳定入口"""

    method: str
    input: AnalysisInput
    output: AnalysisOutput
    config: AnalysisConfigRef = field(default_factory=AnalysisConfigRef)
    options: AnalysisOptions = field(default_factory=AnalysisOptions)
    method_config: dict[str, object] = field(default_factory=dict)
    schema_version: int = 1
    kind: str = "analysis_request"

    def to_json(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "method": self.method,
            "input": self.input.to_json(),
            "output": self.output.to_json(),
            "config": self.config.to_json(),
            "options": self.options.to_json(),
            "method_config": dict(self.method_config),
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> AnalysisRequest:
        return cls(
            schema_version=_int(data.get("schema_version"), default=1),
            kind=_str(data.get("kind"), default="analysis_request"),
            method=_str(data.get("method")),
            input=_nested(AnalysisInput, data.get("input")),
            output=_nested(AnalysisOutput, data.get("output")),
            config=_nested(AnalysisConfigRef, data.get("config")),
            options=_nested(AnalysisOptions, data.get("options")),
            method_config=_dict(data.get("method_config")),
        )
