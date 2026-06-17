"""makeblastdb 调用包装器"""

# region import
from __future__ import annotations

from pathlib import Path

from genomelens.toolchain.runtime.subprocess_runner import CommandResult, run_command

# endregion


def run_makeblastdb(makeblastdb: str | Path, fasta: str | Path, dbtype: str = "nucl") -> CommandResult:
    """为 FASTA 文件运行 makeblastdb"""

    # dbtype 默认为 nucl，与当前 shell 侧 CDS/BLAST 工作流保持一致。
    return run_command([makeblastdb, "-in", fasta, "-dbtype", dbtype])
