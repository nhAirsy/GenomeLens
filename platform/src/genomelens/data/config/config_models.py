"""GenomeLens shell(外壳) 的配置 dataclasses(数据类)"""

# region import
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from genomelens.core.json_utils import _bool, _dict, _float, _int, _str, _str_list

# endregion


@dataclass
class WorkspaceConfig:
    """WorkspaceConfig(工作区配置)：runtime files(运行时文件) 的默认根目录"""

    workspace_root: str
    temp_root: str
    default_output_root: str
    jcvi_config_path: str = ""


@dataclass
class ToolchainConfig:
    """ToolchainConfig(工具链配置)：显式 executable(可执行文件) 覆盖项"""

    jcvi_engine_path: str = ""
    blastn_path: str = ""
    makeblastdb_path: str = ""
    lastal_path: str = ""
    lastdb_path: str = ""
    magick_path: str = ""


@dataclass
class RuntimeDefaults:
    """RuntimeDefaults(运行默认值)：通用运行级默认值"""

    default_threads: int = 4
    default_formats: list[str] = field(default_factory=lambda: ["png"])
    log_level: str = "INFO"


@dataclass
class McscanDefaults:
    """McscanDefaults(MCscan 默认参数)：共线性分析核心参数"""

    workflow: str = "graphics_synteny"
    min_block_size: int = 5
    align_soft: str = "blast"
    dbtype: str = "nucl"
    cscore: float = 0.7
    dist: int = 20
    iter: int = 1
    reference: str = ""


@dataclass
class LocalSyntenyDefaults:
    """LocalSyntenyDefaults(目标基因局部共线性默认参数)"""

    target_gene_ids: list[str] = field(default_factory=list)
    up: int = 20
    down: int = 20
    split_targets: bool = False
    label_targets: bool = False
    glyphstyle: str = ""
    glyphcolor: str = ""
    shadestyle: str = ""
    figsize: str = ""
    dpi: int = 300


@dataclass
class ConfigModel:
    """ConfigModel(总配置)：持久化 JSON schema(JSON 结构) 第 2 版

    第 2 版 JCVI 子配置按用途分组：toolchain、runtime、mcscan、local_synteny。
    """

    workspace: WorkspaceConfig
    toolchain: ToolchainConfig = field(default_factory=ToolchainConfig)
    runtime: RuntimeDefaults = field(default_factory=RuntimeDefaults)
    mcscan: McscanDefaults = field(default_factory=McscanDefaults)
    local_synteny: LocalSyntenyDefaults = field(default_factory=LocalSyntenyDefaults)
    schema_version: int = 2

    def to_project_json_dict(self) -> dict[str, object]:
        """序列化为工具本身配置文件"""

        # 主配置只保留 shell 自己要直接读取的稳定入口字段。
        return {
            "schema_version": self.schema_version,
            "workspace_root": self.workspace.workspace_root,
            "temp_root": self.workspace.temp_root,
            "default_output_root": self.workspace.default_output_root,
            "log_level": self.runtime.log_level,
            "jcvi_config_path": self.workspace.jcvi_config_path,
        }

    def to_jcvi_json_dict(self) -> dict[str, object]:
        """序列化为 JCVI 子工具配置文件（分组结构）"""

        # 写盘结构尽量与内存 dataclass 分组一致，降低配置漂移风险。
        return {
            "schema_version": self.schema_version,
            "toolchain": {
                "jcvi_engine_path": self.toolchain.jcvi_engine_path,
                "blastn_path": self.toolchain.blastn_path,
                "makeblastdb_path": self.toolchain.makeblastdb_path,
                "lastal_path": self.toolchain.lastal_path,
                "lastdb_path": self.toolchain.lastdb_path,
                "magick_path": self.toolchain.magick_path,
            },
            "runtime": {
                "threads": self.runtime.default_threads,
                "formats": self.runtime.default_formats,
            },
            "mcscan": {
                "workflow": self.mcscan.workflow,
                "min_block_size": self.mcscan.min_block_size,
                "align_soft": self.mcscan.align_soft,
                "dbtype": self.mcscan.dbtype,
                "cscore": self.mcscan.cscore,
                "dist": self.mcscan.dist,
                "iter": self.mcscan.iter,
                "reference": self.mcscan.reference,
            },
            "local_synteny": {
                "target_gene_ids": list(self.local_synteny.target_gene_ids),
                "up": self.local_synteny.up,
                "down": self.local_synteny.down,
                "split_targets": self.local_synteny.split_targets,
                "label_targets": self.local_synteny.label_targets,
                "glyphstyle": self.local_synteny.glyphstyle,
                "glyphcolor": self.local_synteny.glyphcolor,
                "shadestyle": self.local_synteny.shadestyle,
                "figsize": self.local_synteny.figsize,
                "dpi": self.local_synteny.dpi,
            },
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, object]) -> ConfigModel:
        """从当前配置 JSON 协议反序列化（仅第 2 版分组结构）"""

        workspace_root = _str(data.get("workspace_root"), default=default_workspace_root())
        workspace = WorkspaceConfig(
            workspace_root=normalize_path_string(workspace_root),
            temp_root=normalize_path_string(_str(data.get("temp_root"), default=str(Path(workspace_root) / "temp"))),
            default_output_root=normalize_path_string(
                _str(data.get("default_output_root"), default=str(Path(workspace_root) / "results"))
            ),
            jcvi_config_path=normalize_optional_path(data.get("jcvi_config_path")),
        )

        toolchain_raw = _dict(data.get("toolchain"))
        toolchain = ToolchainConfig(
            jcvi_engine_path=normalize_optional_path(toolchain_raw.get("jcvi_engine_path")),
            blastn_path=normalize_optional_path(toolchain_raw.get("blastn_path")),
            makeblastdb_path=normalize_optional_path(toolchain_raw.get("makeblastdb_path")),
            lastal_path=normalize_optional_path(toolchain_raw.get("lastal_path")),
            lastdb_path=normalize_optional_path(toolchain_raw.get("lastdb_path")),
            magick_path=normalize_optional_path(toolchain_raw.get("magick_path")),
        )

        runtime_raw = _dict(data.get("runtime"))
        runtime = RuntimeDefaults(
            # log_level 仍属于 shell 运行时，所以继续保留在主配置平面
            default_threads=_int(runtime_raw.get("threads"), default=4),
            default_formats=_str_list(runtime_raw.get("formats"), default=["png"]),
            log_level=_str(data.get("log_level"), default="INFO"),
        )

        mcscan_raw = _dict(data.get("mcscan"))
        mcscan = McscanDefaults(
            workflow=_str(mcscan_raw.get("workflow"), default="graphics_synteny"),
            min_block_size=_int(mcscan_raw.get("min_block_size"), default=5),
            align_soft=_str(mcscan_raw.get("align_soft"), default="blast"),
            dbtype=_str(mcscan_raw.get("dbtype"), default="nucl"),
            cscore=_float(mcscan_raw.get("cscore"), default=0.7),
            dist=_int(mcscan_raw.get("dist"), default=20),
            iter=_int(mcscan_raw.get("iter"), default=1),
            reference=_str(mcscan_raw.get("reference")),
        )

        local_raw = _dict(data.get("local_synteny"))
        local_synteny = LocalSyntenyDefaults(
            # 目标基因必须保持 list 语义，避免字符串被拆成字符列表
            target_gene_ids=_str_list(local_raw.get("target_gene_ids")),
            up=_int(local_raw.get("up"), default=20),
            down=_int(local_raw.get("down"), default=20),
            split_targets=_bool(local_raw.get("split_targets"), default=False),
            label_targets=_bool(local_raw.get("label_targets"), default=False),
            glyphstyle=_str(local_raw.get("glyphstyle")),
            glyphcolor=_str(local_raw.get("glyphcolor")),
            shadestyle=_str(local_raw.get("shadestyle")),
            figsize=_str(local_raw.get("figsize")),
            dpi=_int(local_raw.get("dpi"), default=300),
        )

        return cls(
            workspace=workspace,
            toolchain=toolchain,
            runtime=runtime,
            mcscan=mcscan,
            local_synteny=local_synteny,
            schema_version=_int(data.get("schema_version"), default=2),
        )

    def as_nested_dict(self) -> dict[str, object]:
        """返回供内部调试使用的嵌套 dict(字典)"""

        return asdict(self)


def default_workspace_root() -> str:
    """返回默认用户工作区根目录"""

    return normalize_path_string(Path.home() / "GenomeLensWork")


def normalize_path_string(path: str | Path) -> str:
    """规范化路径，不要求目标已经存在"""

    return str(Path(path).expanduser().resolve(strict=False))


def normalize_optional_path(value: object) -> str:
    """规范化可选路径字段，同时保留空字符串"""

    if value is None or str(value).strip() == "":
        return ""

    # 只有真正配置了路径时才做绝对化，空串语义要原样保留。
    return normalize_path_string(str(value))
