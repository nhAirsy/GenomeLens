"""reference_resolver(参考物种解析器)：参考物种索引与 JCVI 配置路径解析"""

# region import
from __future__ import annotations

import argparse
from pathlib import Path

from genomelens.analysis.normalization.input_resolver import _path
from genomelens.analysis.request_models import AnalysisSpeciesInput
from genomelens.app.errors import messages
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.data.config.config_models import ConfigModel

# endregion


def _resolve_reference_index(reference: str, species: list[AnalysisSpeciesInput]) -> int:
    """解析参考物种：接受物种名称或 1-based 索引，空字符串默认 0"""

    text = str(reference or "").strip()
    if not text:
        return 0
    if text.isdigit():
        index = int(text) - 1
        if 0 <= index < len(species):
            return index
        raise InputValidationError(messages.INPUT_REFERENCE_OUT_OF_RANGE.format(index=text, count=len(species)))

    names = [s.name for s in species]
    if text in names:
        return names.index(text)

    # 尝试大小写不敏感匹配
    lower_map = {name.lower(): idx for idx, name in enumerate(names)}
    if text.lower() in lower_map:
        return lower_map[text.lower()]
    raise InputValidationError(messages.INPUT_REFERENCE_NOT_FOUND.format(name=text, available=", ".join(names)))


def _reference(args: argparse.Namespace, config: ConfigModel | None) -> str:
    """CLI `--reference` 优先，否则读取 config.mcscan.reference"""

    value = str(getattr(args, "reference", "") or "").strip()
    if value:
        return value
    if config:
        return str(config.mcscan.reference or "")
    return ""


def _resolve_jcvi_config(args: argparse.Namespace) -> str:
    """解析 `analyze mcscan` 的 JCVI 配置文件路径

    优先级：
    1. CLI 显式 `--jcvi-config`
    2. 位置参数 `jcvi_config_positional`
    3. 输入目录下的 `jcvi.config.json`
    4. 当前工作目录下的 `jcvi.config.json`
    """

    explicit = str(args.jcvi_config or "").strip()
    if explicit:
        return str(_path(explicit))

    positional = str(getattr(args, "jcvi_config_positional", "") or "").strip()
    if positional:
        return str(_path(positional))

    input_dir = Path(str(args.input_dir or ".")).expanduser().resolve(strict=False)
    candidate = input_dir / "jcvi.config.json"
    if candidate.is_file():
        return str(candidate)

    cwd_candidate = Path.cwd() / "jcvi.config.json"
    if cwd_candidate.is_file():
        return str(cwd_candidate)
    return ""
