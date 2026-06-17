"""engine workflows(引擎工作流) 的 command audit(命令审计) 结构"""

# region import
from __future__ import annotations

import contextlib
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

# endregion


@dataclass(frozen=True)
class CommandAudit:
    """CommandAudit(命令审计)：记录类命令工作流步骤"""

    name: str
    argv: list[str]
    returncode: int
    cwd: str = ""
    stdout: str = ""
    stderr: str = ""

    def to_json(self) -> dict[str, object]:
        """序列化为 summary JSON(摘要 JSON)"""

        return {
            "name": self.name,
            "argv": self.argv,
            "returncode": self.returncode,
            "cwd": self.cwd,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


def run_command(argv: list[str], *, cwd: str | Path | None = None, timeout: int = 600) -> CommandAudit:
    """运行外部命令并捕获输出"""

    # 所有 engine 外部进程都走同一审计结构，便于失败时统一写进 summary。
    completed = subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        timeout=timeout,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        shell=False,
        check=False,
    )
    return CommandAudit(
        name=Path(argv[0]).name,
        argv=argv,
        returncode=completed.returncode,
        cwd=str(cwd) if cwd else "",
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_python_step(
    name: str,
    func: Callable[[list[str]], object],
    args: list[str],
    *,
    cwd: str | Path | None = None,
) -> CommandAudit:
    """运行进程内 JCVI 步骤，并捕获 stdout/stderr 供审计"""

    old_cwd = Path.cwd()
    stdout = StringIO()
    stderr = StringIO()
    returncode = 0
    try:
        if cwd is not None:
            import os

            os.chdir(cwd)
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            # 部分 JCVI 入口仍是函数式调用，这里把它们伪装成“可审计命令”。
            func(args)
    except SystemExit as exc:
        returncode = int(exc.code or 0)
    except Exception as exc:  # noqa: BLE001 - engine boundary records arbitrary JCVI failures
        returncode = 1
        stderr.write(f"{exc.__class__.__name__}: {exc}")
    finally:
        if cwd is not None:
            import os

            # Python 进程内步骤会改 cwd，结束时一定恢复，避免污染后续工作流步骤。
            os.chdir(old_cwd)
    return CommandAudit(
        name=name,
        argv=[name, *args],
        returncode=returncode,
        cwd=str(cwd) if cwd else "",
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )
