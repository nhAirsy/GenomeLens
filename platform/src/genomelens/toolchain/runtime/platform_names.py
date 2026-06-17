"""按平台生成 executable(可执行文件) 候选名称"""

# region import
from __future__ import annotations

import sys

# endregion


def is_windows() -> bool:
    """当前 runtime(运行时) 是 Windows 时返回 True"""

    return sys.platform.startswith("win")


def executable_candidates(name: str) -> list[str]:
    """返回当前平台优先尝试的 executable(可执行文件) 名称"""

    if is_windows():
        # Windows 上优先尝试显式 .exe，再回退到裸名，兼容 PATH/包装差异。
        return [f"{name}.exe", name]
    return [name]


def blastn_candidates() -> list[str]:
    # 这些小包装函数把调用方从具体二进制名里解耦出来。
    return executable_candidates("blastn")


def makeblastdb_candidates() -> list[str]:
    return executable_candidates("makeblastdb")


def magick_candidates() -> list[str]:
    return executable_candidates("magick")


def lastal_candidates() -> list[str]:
    return executable_candidates("lastal")


def lastdb_candidates() -> list[str]:
    return executable_candidates("lastdb")


def jcvi_engine_candidates() -> list[str]:
    return executable_candidates("jcvi-genomelens")


def genomelens_runtime_candidates() -> list[str]:
    return executable_candidates("GenomeLens-runtime")
