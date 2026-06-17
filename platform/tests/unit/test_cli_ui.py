import argparse

from genomelens.cli.main import main
from genomelens.cli.ui import StyledArgumentParser, prompt_text, render_command_error, render_workbench_banner


def test_workbench_banner_plain_text() -> None:
    banner = render_workbench_banner(color=False)
    assert "GenomeLens" in banner
    assert "常用命令" in banner
    assert "analyze mcscan" in banner
    assert "analyze run" not in banner
    assert "analyze template" not in banner
    assert "可用分析方法" in banner
    assert "mcscan" in banner
    assert "\033[" not in banner


def test_prompt_and_error_plain_text() -> None:
    assert prompt_text(color=False) == "GenomeLens > "
    assert render_command_error(7, color=False) == "命令退出，退出码 7"


def test_styled_argument_parser_localizes_help() -> None:
    parser = StyledArgumentParser(prog="genomelens", description="中文说明")
    parser.add_argument("--flag", action="store_true", help="测试开关")
    subparsers = parser.add_subparsers(dest="command", title="命令")
    subparsers.add_parser("check", help="检查环境")

    help_text = parser.format_help()

    assert "用法:" in help_text
    assert "选项:" in help_text
    assert "命令:" in help_text
    assert "中文说明" in help_text
    assert "显示帮助信息并退出" in help_text


def test_styled_argument_parser_colors_argument_and_description(monkeypatch) -> None:
    monkeypatch.setenv("GENOMELENS_FORCE_COLOR", "1")
    parser = StyledArgumentParser(prog="genomelens", description="中文说明")
    parser.add_argument("--flag", action="store_true", help="测试开关")

    help_text = parser.format_help()

    assert "\033[38;2;125;211;217m--flag\033[0m" in help_text
    assert "\033[38;2;156;163;175m测试开关\033[0m" in help_text


def test_styled_argument_parser_colors_wrapped_positional_argument(monkeypatch) -> None:
    monkeypatch.setenv("GENOMELENS_FORCE_COLOR", "1")
    parser = StyledArgumentParser(
        prog="genomelens",
        formatter_class=lambda prog: argparse.HelpFormatter(prog, width=42),
    )
    parser.add_argument("jcvi_config_positional", nargs="?", help="optional JCVI config path")

    help_text = parser.format_help()

    assert "\033[38;2;125;211;217mjcvi_config_positional\033[0m" in help_text
    assert "\033[38;2;156;163;175moptional JCVI config\033[0m" in help_text
    assert "\033[38;2;156;163;175mpath\033[0m" in help_text


def test_workbench_exits_cleanly_on_keyboard_interrupt(monkeypatch) -> None:
    def raise_keyboard_interrupt(_prompt: str) -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", raise_keyboard_interrupt)

    assert main([]) == 0
