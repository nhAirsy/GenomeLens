"""`genomelens config` 命令"""

# region import
from __future__ import annotations

import argparse
from pathlib import Path

from genomelens.data.config.config_store import (
    default_config,
    default_config_path,
    default_jcvi_config_path,
    write_split_config,
)

# endregion


def register(subparsers: argparse._SubParsersAction) -> None:
    """注册 config 命令"""

    parser = subparsers.add_parser("config", help="管理 GenomeLens 配置")
    nested = parser.add_subparsers(dest="config_command", required=True)
    init_parser = nested.add_parser("init", help="写出默认配置")
    init_parser.add_argument("--workspace", required=True, help="运行时文件 workspace(工作区) 根目录")
    init_parser.add_argument("--config-path", default="", help="显式主配置文件路径")
    init_parser.add_argument("--jcvi-config-path", default="", help="显式 JCVI 配置文件路径")
    init_parser.add_argument("--force", action="store_true", help="覆盖已有配置")
    init_parser.set_defaults(func=run_init)


def run_init(args: argparse.Namespace) -> int:
    """写出默认 config JSON(配置 JSON) 文件"""

    config = default_config(args.workspace)

    # 路径既允许显式覆盖，也允许按 workspace 规则自动推导，便于首次初始化与批处理复用
    path = Path(args.config_path) if args.config_path else default_config_path(args.workspace)
    jcvi_path = Path(args.jcvi_config_path) if args.jcvi_config_path else default_jcvi_config_path(args.workspace)
    written_main, written_jcvi = write_split_config(config, path, jcvi_path, force=args.force)
    print(f"已写入主配置：{written_main}")
    print(f"已写入 JCVI 配置：{written_jcvi}")
    return 0
