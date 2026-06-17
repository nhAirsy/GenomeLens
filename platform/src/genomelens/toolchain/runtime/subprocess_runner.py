"""安全 subprocess(子进程) 执行包装器"""

# region import
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# endregion


@dataclass(frozen=True)
class CommandResult:
    """CommandResult(命令结果)：结构化 subprocess(子进程) 输出"""

    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    cwd: str | None = None

    @property
    def ok(self) -> bool:
        """命令成功退出时返回 True"""

        return self.returncode == 0


def normalize_argv(argv: list[str | Path]) -> list[str]:
    """把 Path 参数和 Python 脚本转换为可执行 argv(参数向量)"""

    if not argv:
        return []
    first = Path(str(argv[0]))
    normalized = [str(item) for item in argv]
    if first.suffix.lower() == ".py":
        # 源码模式下允许直接传入脚本路径，这里统一补成 `python script.py ...`
        return [sys.executable, *normalized]
    return normalized


def run_command(argv: list[str | Path], *, cwd: str | Path | None = None, timeout: int = 600) -> CommandResult:
    """以 `shell=False` 运行命令，并捕获 UTF-8 文本输出"""

    normalized = normalize_argv(argv)
    completed = subprocess.run(
        normalized,
        cwd=str(cwd) if cwd else None,
        timeout=timeout,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        shell=False,
        check=False,
    )

    # 所有调用方都通过结构化结果读取 stdout/stderr，避免在多层之间传裸 CompletedProcess
    return CommandResult(
        argv=normalized,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        cwd=str(cwd) if cwd else None,
    )
