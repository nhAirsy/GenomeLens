"""定位 runtime tools(运行时工具)，避免写死开发机路径"""

# region import
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from genomelens.data.config.config_models import ConfigModel
from genomelens.toolchain.runtime.platform_names import jcvi_engine_candidates

# endregion


@dataclass(frozen=True)
class LocatedResource:
    """LocatedResource(定位结果)：路径与状态 metadata(元数据)"""

    name: str
    status: str
    path: str = ""
    message: str = ""

    @property
    def ok(self) -> bool:
        """资源可用时返回 True"""

        return self.status == "ok"


def project_root() -> Path:
    """从已安装源码布局推断 monorepo(单仓库) 根目录"""

    return Path(__file__).resolve().parents[5]


def runtime_root() -> Path:
    """返回打包 runtime(运行时) 根目录或源码项目根目录"""

    # frozen 模式下资源跟随可执行文件；源码模式下回到 monorepo 根目录找本地 toolchains
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return project_root()


def _existing_file(candidates: list[str | Path]) -> str:
    """返回首个存在的文件路径，找不到时返回空字符串"""

    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser().resolve(strict=False)
        if path.is_file():
            return str(path)
    return ""


def locate_on_path(names: list[str]) -> str:
    """通过检查 PATH 名称定位 executable(可执行文件)"""

    for name in names:
        found = shutil.which(name)
        if found:
            return str(Path(found).resolve(strict=False))
    return ""


def _tool_env_candidates(name: str, packaged_names: list[str]) -> list[str]:
    """根据工具名返回对应环境变量覆盖路径"""

    # 环境变量名与工具能力解耦，调用方只需给出常用 executable 名称集合
    normalized = {item.lower() for item in packaged_names}
    if "blastn" in normalized or "blastn.exe" in normalized:
        return [os.environ.get("GENOMELENS_BLASTN", "")]
    if "makeblastdb" in normalized or "makeblastdb.exe" in normalized:
        return [os.environ.get("GENOMELENS_MAKEBLASTDB", "")]
    if "lastal" in normalized or "lastal.exe" in normalized:
        return [os.environ.get("GENOMELENS_LASTAL", "")]
    if "lastdb" in normalized or "lastdb.exe" in normalized:
        return [os.environ.get("GENOMELENS_LASTDB", "")]
    if name == "imagemagick" or "magick" in normalized or "magick.exe" in normalized:
        return [os.environ.get("GENOMELENS_MAGICK", "")]
    return []


def locate_engine(*, explicit: str = "", config: ConfigModel | None = None) -> LocatedResource:
    """按要求的优先级定位外部 jcvi-genomelens engine(引擎)"""

    root = project_root()
    runtime = runtime_root()
    meipass = Path(getattr(sys, "_MEIPASS", root))
    configured = config.toolchain.jcvi_engine_path if config else ""
    candidates: list[str | Path] = [
        explicit,
        configured,
        os.environ.get("GENOMELENS_JCVI_ENGINE", ""),
        root / "engines" / "jcvi" / "src" / "jcvi_genomelens" / "cli.py",
    ]

    # 候选路径同时覆盖源码树、本地缓存、打包资源和 PyInstaller 解包目录
    for exe_name in jcvi_engine_candidates():
        candidates.extend(
            [
                runtime / "resources" / "toolchain" / "jcvi-genomelens" / "bin" / exe_name,
                root / "platform" / "resources" / "toolchain" / "jcvi-genomelens" / "bin" / exe_name,
                root / "toolchains" / "jcvi-genomelens" / "current" / exe_name,
                meipass / "resources" / "toolchain" / "jcvi-genomelens" / "bin" / exe_name,
            ]
        )
    path = _existing_file(candidates) or locate_on_path(jcvi_engine_candidates())
    if path:
        return LocatedResource(name="jcvi_engine", status="ok", path=path)
    return LocatedResource(name="jcvi_engine", status="missing", message="jcvi-genomelens executable was not found")


def locate_tool(
    name: str,
    explicit: str = "",
    config_value: str = "",
    packaged_names: list[str] | None = None,
) -> LocatedResource:
    """定位 BLAST 或 ImageMagick 工具

    工具查找在显式覆盖之后有意优先使用系统安装：
    explicit/config/env(显式/配置/环境) -> PATH -> packaged resources(打包资源)
    -> source-tree toolchains(源码树工具链)。
    """

    root = project_root()
    runtime = runtime_root()
    packaged_names = packaged_names or [name]

    # 显式路径/配置/环境变量一旦命中，优先级高于系统 PATH 和随包资源
    override = _existing_file([explicit, config_value, *_tool_env_candidates(name, packaged_names)])
    if override:
        return LocatedResource(name=name, status="ok", path=override)
    system_path = locate_on_path(packaged_names)
    if system_path:
        return LocatedResource(name=name, status="ok", path=system_path)
    candidates: list[str | Path] = []
    for exe_name in packaged_names:
        candidates.extend(
            [
                runtime / "resources" / "toolchain" / name / "bin" / exe_name,
                runtime / "resources" / "toolchain" / name / exe_name,
                root / "platform" / "resources" / "toolchain" / name / "bin" / exe_name,
                root / "toolchains" / name / "current" / "bin" / exe_name,
                root / "toolchains" / name / "current" / exe_name,
            ]
        )
    path = _existing_file(candidates)
    if path:
        return LocatedResource(name=name, status="ok", path=path)
    return LocatedResource(name=name, status="missing", message=f"{name} was not found")
