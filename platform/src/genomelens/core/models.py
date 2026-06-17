"""shell(外壳) 侧分析请求的核心 dataclasses(数据类)"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# endregion


@dataclass(frozen=True)
class RawAnnotationInputSpec:
    """RawAnnotationInputSpec(原始注释输入)：GFF/GTF 加 genome FASTA(基因组序列)"""

    gff: Path
    genome: Path


@dataclass(frozen=True)
class PreparedGenomeInputSpec:
    """PreparedGenomeInputSpec(标准输入)：BED 加 CDS FASTA"""

    bed: Path
    cds: Path


@dataclass(frozen=True)
class GenomeInputSpec:
    """GenomeInputSpec(基因组输入)：比较中的一个具名物种侧"""

    name: str
    prepared: PreparedGenomeInputSpec | None = None
    raw: RawAnnotationInputSpec | None = None

    @property
    def mode(self) -> str:
        """返回公开输入模式名称"""

        # prepared/raw 是当前两种互斥入口，mode 属性负责把内部状态折叠成稳定字符串
        if self.prepared:
            return "bed_cds"
        if self.raw:
            return "gff_genome"
        return "unknown"


@dataclass(frozen=True)
class AnalysisTaskSpec:
    """AnalysisTaskSpec(分析任务规格)：面向平台核心的稳定任务描述"""

    task_id: str
    task_type: str
    workflow: str
    species: list[GenomeInputSpec]
    source: str = "genomelens-shell"

    def to_manifest_json(self) -> dict[str, object]:
        """转成 engine manifest(引擎清单) 可直接写入的公开字段"""

        # task manifest 只保留跨层稳定字段，避免把 shell 内部对象结构泄漏到 engine 协议
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "workflow": self.workflow,
            "source": self.source,
        }


@dataclass(frozen=True)
class ArtifactRecord:
    """ArtifactRecord(产物记录)：供报告、GUI 和后续评分模块统一读取"""

    artifact_id: str
    artifact_type: str
    path: str
    produced_by: str
    format: str = ""
    preview: bool = False
    input_refs: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def to_json(self) -> dict[str, object]:
        """转成稳定 JSON(结构化数据)"""

        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "path": self.path,
            "produced_by": self.produced_by,
            "format": self.format,
            "preview": self.preview,
            "input_refs": self.input_refs,
            "metadata": self.metadata,
        }
