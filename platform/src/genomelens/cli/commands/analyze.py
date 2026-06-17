"""`genomelens analyze` 命令注册"""

# region import
from __future__ import annotations

import argparse
import json
from functools import partial

from genomelens.analysis.dispatcher import AnalysisDispatcher
from genomelens.analysis.methods.registry import MethodPlugin, MethodRegistry
from genomelens.cli.ui import render_analysis_summary
from genomelens.core.summary_models import RunSummary

# endregion


def register(subparsers: argparse._SubParsersAction) -> None:
    """注册 analyze 命令及其所有已注册方法子命令"""

    parser = subparsers.add_parser("analyze", help="运行 GenomeLens 分析")
    nested = parser.add_subparsers(dest="analysis_command", required=True)

    registry = MethodRegistry()
    for plugin in registry.list_all():
        method_parser = nested.add_parser(plugin.name, help=plugin.description)
        plugin.add_cli_arguments(method_parser)
        method_parser.set_defaults(func=partial(_run_plugin, plugin=plugin))


def _print_summary(summary: RunSummary | dict[str, object], json_output: bool = False) -> int:
    """输出分析摘要"""

    run_summary = summary if isinstance(summary, RunSummary) else RunSummary.from_json(summary)

    if json_output:
        # JSON 模式保留原始结构，供插件、脚本或其他进程直接消费
        print(json.dumps(run_summary.to_json(), ensure_ascii=False, indent=2))
    else:
        print(render_analysis_summary(run_summary))

    return 0 if run_summary.status == "SUCCEEDED" else 7


def _run_plugin(args: argparse.Namespace, plugin: MethodPlugin) -> int:
    """运行任意已注册方法子命令"""

    request = plugin.build_request(args)
    summary = AnalysisDispatcher().dispatch(request)
    return _print_summary(summary, json_output=bool(getattr(args, "json", False)))
