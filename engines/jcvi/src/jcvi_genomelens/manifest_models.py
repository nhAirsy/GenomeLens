"""engine(引擎) 运行的 manifest dataclasses(清单数据类)"""

# region import
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# endregion


@dataclass(frozen=True)
class GenomeSpec:
    """GenomeSpec(基因组规格)：准备好的 BED 与 CDS 输入"""

    name: str
    bed: Path
    cds: Path


@dataclass(frozen=True)
class ToolchainSpec:
    """ToolchainSpec(工具链规格)：外部 executable(可执行文件) 路径"""

    blastn: Path | None = None
    makeblastdb: Path | None = None
    lastal: Path | None = None
    lastdb: Path | None = None


@dataclass(frozen=True)
class WorkflowOptions:
    """WorkflowOptions(工作流选项)：可调执行参数"""

    threads: int = 4
    min_block_size: int = 5
    formats: list[str] = field(default_factory=lambda: ["png"])
    layout: Path | None = None
    seqids: Path | None = None
    allow_simplified_fallback: bool = False
    # shell 的 mcscan 参数会原样落到这里，再交给具体 workflow 消费。
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
    # 图形样式参数在 shell/engine 间保持字符串协议，避免引入额外解析层。
    # 图件样式参数
    glyphstyle: str = ""
    glyphcolor: str = ""
    shadestyle: str = ""
    figsize: str = ""
    dpi: int = 300


@dataclass(frozen=True)
class EngineTrack:
    """EngineTrack(轨道)：全局核型总图中的一个物种轨道"""

    name: str
    bed: Path


@dataclass(frozen=True)
class EngineEdge:
    """EngineEdge(连接)：两个轨道之间的共线性 simple(简化区块) 文件

    `i`/`j` 是 `tracks` 列表中的下标，`simple` 是 pairwise(两两比较) 阶段
    产出的 `.anchors.simple` 文件路径。
    """

    i: int
    j: int
    simple: Path


@dataclass(frozen=True)
class EngineRunManifest:
    """EngineRunManifest(engine 运行清单)：已校验的公开 manifest(清单)"""

    workflow: str
    toolchain: ToolchainSpec
    options: WorkflowOptions
    # 常规 pairwise 工作流使用 query/subject；全局核型图则改走 tracks/edges。
    query: GenomeSpec | None = None
    subject: GenomeSpec | None = None
    schema_version: int = 1
    task: dict[str, object] = field(default_factory=dict)
    species: list[dict[str, object]] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    meta: dict[str, object] = field(default_factory=dict)
    tracks: list[EngineTrack] = field(default_factory=list)
    edges: list[EngineEdge] = field(default_factory=list)
