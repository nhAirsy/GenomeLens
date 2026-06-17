"""option_merger(选项合并器)：CLI、配置与默认值的三方合并"""

# region import
from __future__ import annotations

import argparse
import os

from genomelens.data.config.config_models import ConfigModel
from genomelens.parsers import parse_formats

# endregion


def _formats(args: argparse.Namespace, config: ConfigModel | None) -> list[str]:
    if str(args.formats).strip():
        return parse_formats(args.formats)

    # 运行时默认格式集中放在 runtime 组，避免 method config 重复维护同一来源
    if config:
        return parse_formats(config.runtime.default_formats)
    return ["png"]


def _threads(args: argparse.Namespace, config: ConfigModel | None) -> int | None:
    if args.threads is not None:
        return int(args.threads)
    if config:
        return int(config.runtime.default_threads)

    # auto 工作流：默认把线程数限制在 1~8 之间
    return max(1, min(os.cpu_count() or 4, 8))


def _min_block_size(args: argparse.Namespace, config: ConfigModel | None) -> int | None:
    if args.min_block_size is not None:
        return int(args.min_block_size)
    if config:
        return int(config.mcscan.min_block_size)
    return None


def _workflow(args: argparse.Namespace, config: ConfigModel | None) -> str:
    if str(args.jcvi_workflow).strip():
        return str(args.jcvi_workflow)

    # workflow 默认值属于 mcscan 方法语义，不从 runtime 通用配置读取
    if config:
        return config.mcscan.workflow
    return "graphics_synteny"


def _align_soft(args: argparse.Namespace, config: ConfigModel | None) -> str:
    if str(args.align_soft).strip():
        return str(args.align_soft)
    if config:
        return config.mcscan.align_soft
    return "blast"


def _dbtype(args: argparse.Namespace, config: ConfigModel | None) -> str:
    if str(args.dbtype).strip():
        return str(args.dbtype)
    if config:
        return config.mcscan.dbtype
    return "nucl"


def _cscore(args: argparse.Namespace, config: ConfigModel | None) -> float:
    if args.cscore is not None:
        return float(args.cscore)
    if config:
        return float(config.mcscan.cscore)
    return 0.7


def _dist(args: argparse.Namespace, config: ConfigModel | None) -> int:
    if args.dist is not None:
        return int(args.dist)
    if config:
        return int(config.mcscan.dist)
    return 20


def _iter(args: argparse.Namespace, config: ConfigModel | None) -> int:
    if args.iter is not None:
        return int(args.iter)
    if config:
        return int(config.mcscan.iter)
    return 1


def _up(args: argparse.Namespace, config: ConfigModel | None) -> int:
    if args.up is not None:
        return int(args.up)

    if config:
        return int(config.local_synteny.up)
    return 20


def _down(args: argparse.Namespace, config: ConfigModel | None) -> int:
    if args.down is not None:
        return int(args.down)

    if config:
        return int(config.local_synteny.down)
    return 20


def _dpi(args: argparse.Namespace, config: ConfigModel | None) -> int:
    if args.dpi is not None:
        return int(args.dpi)

    if config:
        return int(config.local_synteny.dpi)
    return 300


def _target_gene_ids(args: argparse.Namespace, config: ConfigModel | None) -> list[str]:
    text = str(args.target_genes).strip()
    if text:
        # CLI 入口使用逗号分隔字符串，配置文件则已经是规范化后的 list[str]
        return [item.strip() for item in text.split(",") if item.strip()]
    if config:
        return list(config.local_synteny.target_gene_ids)
    return []


def _split_targets(args: argparse.Namespace, config: ConfigModel | None) -> bool:
    if args.split_targets:
        return True
    if config:
        return bool(config.local_synteny.split_targets)
    return False


def _label_targets(args: argparse.Namespace, config: ConfigModel | None) -> bool:
    if args.label_targets:
        return True
    if config:
        return bool(config.local_synteny.label_targets)
    return False


def _style_arg(args: argparse.Namespace, config: ConfigModel | None, name: str) -> str:
    value = str(getattr(args, name, "") or "").strip()
    if value:
        return value

    # 样式参数暂时统一复用 local_synteny 配置组，避免在多处复制默认值来源
    if config:
        return str(getattr(config.local_synteny, name, "") or "")
    return ""


def _string_arg(args: argparse.Namespace, name: str) -> str:
    return str(getattr(args, name, "") or "").strip()
