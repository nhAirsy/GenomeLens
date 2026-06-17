"""blastn 调用包装器"""

# region import
from __future__ import annotations

from pathlib import Path

from genomelens.toolchain.runtime.subprocess_runner import CommandResult, run_command

# endregion


def run_blastn(
    blastn: str | Path,
    query: str | Path,
    db: str | Path,
    out: str | Path,
    *,
    threads: int = 4,
) -> CommandResult:
    """运行 blastn 并生成表格输出"""

    # 统一通过 subprocess_runner 返回结构化结果，调用方不用直接摸 subprocess。
    return run_command(
        [
            blastn,
            "-query",
            query,
            "-db",
            db,
            "-out",
            out,
            "-outfmt",
            "6",
            "-num_threads",
            str(threads),
        ]
    )
