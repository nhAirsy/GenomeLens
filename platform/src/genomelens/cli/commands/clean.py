"""`genomelens clean` 命令"""

# region import
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from genomelens.app.errors.exceptions import WorkspaceError

# endregion


def register(subparsers: argparse._SubParsersAction) -> None:
    """注册 clean 命令"""

    parser = subparsers.add_parser("clean", help="清理临时文件和缓存")
    parser.add_argument("--workspace", default=str(Path.home() / "GenomeLensWork"), help="workspace(工作区) 根目录")
    parser.add_argument("--cache", action="store_true", help="清理缓存目录")
    parser.add_argument("--all", action="store_true", help="清理临时目录和缓存目录")
    parser.add_argument("--yes", action="store_true", help="确认删除")
    parser.set_defaults(func=run_clean)


def run_clean(args: argparse.Namespace) -> int:
    """清理临时目录和缓存目录，不触碰正式输出"""

    if not args.yes:
        raise WorkspaceError("未传入 --yes，拒绝清理")
    workspace = Path(args.workspace).expanduser().resolve(strict=False)
    targets: list[Path] = []
    if args.all:
        targets.extend([workspace / "temp", workspace / "cache"])
    elif args.cache:
        targets.append(workspace / "cache")
    else:
        targets.append(workspace / "temp")

    # clean 只触碰 temp/cache，显式避开 results 等正式产物目录
    for target in targets:
        if target.exists():
            shutil.rmtree(target)
            print(f"已删除：{target}")
        else:
            print(f"不存在，跳过：{target}")
    return 0
