"""analysis/normalization(分析请求归一化子包)

把 `request_normalizer.py` 中混杂的职责拆成单一模块，公共 API 仍通过
`genomelens.analysis.request_normalizer` 暴露。"""

# region import
from __future__ import annotations

from genomelens.analysis.normalization.input_resolver import discover_species_from_directory
from genomelens.analysis.normalization.reference_resolver import (
    _reference,
    _resolve_jcvi_config,
    _resolve_reference_index,
)
from genomelens.analysis.normalization.request_assembler import (
    mcscan_auto_request_from_cli,
    mcscan_template_request,
    normalize_analysis_request,
    read_request_config,
)

# endregion


__all__ = [
    # 这里显式列出对外 API，避免调用方依赖子模块内部实现细节。
    "discover_species_from_directory",
    "read_request_config",
    "mcscan_auto_request_from_cli",
    "normalize_analysis_request",
    "mcscan_template_request",
    "_resolve_reference_index",
    "_reference",
    "_resolve_jcvi_config",
]
