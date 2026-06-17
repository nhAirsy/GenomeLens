"""GenomeLens 顶层 argparse 入口"""

# region import
from __future__ import annotations

import argparse
import shlex
import sys

from genomelens._version import __version__
from genomelens.app.errors.error_reporter import exit_code_for, format_user_error
from genomelens.cli.commands import analyze, check, clean, config
from genomelens.cli.ui import (
    StyledArgumentParser,
    clear_screen,
    prompt_text,
    render_command_error,
    render_workbench_banner,
)

# endregion


def build_parser() -> argparse.ArgumentParser:
    """构建完整命令树"""

    parser = StyledArgumentParser(
        prog="genomelens",
        description="GenomeLens 共线性分析工作台",
        epilog="提示：不带参数运行会进入彩色交互工作台",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"GenomeLens Shell {__version__}",
        help="显示版本号并退出",
    )  # 注册基础信息

    subparsers = parser.add_subparsers(dest="command", title="命令")

    # region 通过引用注册的核心功能类命令树
    check.register(subparsers)
    config.register(subparsers)
    analyze.register(subparsers)  # 核心功能命令 - 分析
    clean.register(subparsers)

    # endregion

    # region 仅在 main 下注册的辅助功能类命令树
    # 帮助
    help_parser = subparsers.add_parser("help", help="显示指定命令的参数说明")
    help_parser.add_argument("command_path", nargs="*", metavar="COMMAND", help="命令路径，例如 analyze mcscan")
    help_parser.add_argument("-c", "--command", default="", help='命令路径字符串，例如 "analyze mcscan"')
    help_parser.set_defaults(func=run_help)

    # 进入交互式工作台
    workbench_parser = subparsers.add_parser("workbench", help="进入交互式工作台")
    workbench_parser.set_defaults(func=run_workbench)

    # endregion

    return parser


# region 一些内部函数
def _subparser_map(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    # argparse 没有公开 API 暴露子解析器树，因此这里统一封装一次内部遍历
    for action in parser._actions:  # noqa: SLF001 - argparse 没有公开的子命令遍历 API
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001 - 只读 argparse 内部结构
            return dict(action.choices)
    return {}


def _find_parser(root: argparse.ArgumentParser, command_path: list[str]) -> argparse.ArgumentParser | None:
    parser = root
    for name in command_path:
        children = _subparser_map(parser)
        if name not in children:
            return None
        parser = children[name]
    return parser


# endregion


# region 帮助/运行工作台
def run_help(args: argparse.Namespace) -> int:
    """显示指定命令的帮助文本"""

    root = build_parser()

    # `help analyze mcscan` 和 `help -c "analyze mcscan"` 走同一条路径解析逻辑
    command_path = shlex.split(args.command) if args.command else list(args.command_path)
    parser = _find_parser(root, command_path) if command_path else root
    if parser is None:
        print(f"未知命令：{' '.join(command_path)}", file=sys.stderr)
        return 2
    parser.print_help()
    return 0


def run_workbench(_args: argparse.Namespace | None = None) -> int:
    """运行一个轻量交互式 workbench(工作台)"""

    print(render_workbench_banner())
    while True:
        try:
            line = input(prompt_text()).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not line:
            continue
        if line.lower() in {"exit", "quit"}:
            return 0
        if line.lower() in {"clear", "cls"}:
            clear_screen()
            continue

        # 交互工作台复用主入口，这样帮助、错误码和命令行为与普通 CLI 完全一致
        code = main(shlex.split(line))
        if code:
            print(render_command_error(code))

    return 0


# endregion


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # 没有参数时直接进入工作台
    if not argv:
        return run_workbench()

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse 默认直接退出进程；这里收口成整数返回码，方便测试和工作台复用
        return int(exc.code or 0)

    if not hasattr(args, "func"):
        parser.print_help()
        return 2

    try:
        return int(args.func(args) or 0)
    except Exception as exc:
        # CLI 边界统一转成用户可读错误与稳定退出码
        print(format_user_error(exc), file=sys.stderr)
        return exit_code_for(exc)


if __name__ == "__main__":  # 简单的启动
    raise SystemExit(main())
