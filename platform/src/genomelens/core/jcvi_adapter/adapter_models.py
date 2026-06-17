"""JCVI 引擎适配器专用的请求与结果数据模型"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from genomelens.core.models import AnalysisTaskSpec, GenomeInputSpec

# endregion


@dataclass(frozen=True)
class McscanRequest:
    """McscanRequest(共线性请求)：完整 shell 侧请求"""

    query: GenomeInputSpec
    subject: GenomeInputSpec
    outdir: Path
    additional_species: list[GenomeInputSpec] = field(default_factory=list)
    threads: int = 4
    min_block_size: int = 5
    formats: list[str] = field(default_factory=lambda: ["png"])
    jcvi_engine: str = ""
    jcvi_workflow: str = "graphics_synteny"
    blastn_path: str = ""
    makeblastdb_path: str = ""
    lastal_path: str = ""
    lastdb_path: str = ""
    jcvi_layout: str = ""
    jcvi_seqids: str = ""
    allow_simplified_fallback: bool = False
    force: bool = False

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

    @property
    def species(self) -> list[GenomeInputSpec]:
        """返回当前任务涉及的物种列表，未来可扩展为多物种 species[]"""

        return [self.query, self.subject, *self.additional_species]

    @property
    def task_id(self) -> str:
        """返回稳定但可读的任务标识"""

        # task_id 会出现在 manifest、summary 和多物种汇总里，优先保证可追踪性而非短小
        names = "__".join(species.name for species in self.species)
        return f"{names}__{self.jcvi_workflow}"

    @property
    def task_spec(self) -> AnalysisTaskSpec:
        """构建平台核心使用的任务规格"""

        return AnalysisTaskSpec(
            task_id=self.task_id,
            # 当前平台仍按“恰好两个物种 / 超过两个物种”区分 pairwise 与 multi-species 顶层任务类型
            task_type="pairwise_synteny" if len(self.species) == 2 else "multi_species_synteny",
            workflow=self.jcvi_workflow,
            species=self.species,
        )


@dataclass(frozen=True)
class JcviRunResult:
    """JcviRunResult(engine 结果)：解析后的 engine summary(引擎摘要) 字段"""

    status: str
    summary_path: Path
    engine_version: str
    jcvi_upstream_version: str
    patchset: str
    artifacts: dict[str, object]
    distribution: str = ""
    runtime_mode: str = ""
    loaded_extensions: list[str] = field(default_factory=list)
    missing_extensions: list[str] = field(default_factory=list)
    task: dict[str, object] = field(default_factory=dict)
    species: list[dict[str, object]] = field(default_factory=list)
    artifact_index: list[dict[str, object]] = field(default_factory=list)
    error: object = None
