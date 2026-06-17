"""把 CLI/JSON 输入归一化为 AnalysisRequest(分析请求)

本模块现在是一个薄门面(thin facade)，具体实现已拆分到
`genomelens.analysis.normalization` 子包。所有公共函数签名保持不变。"""

# region import
from __future__ import annotations

from genomelens.analysis.normalization import (
    discover_species_from_directory,
    mcscan_auto_request_from_cli,
    mcscan_template_request,
    normalize_analysis_request,
    read_request_config,
)

# endregion


# 本模块保留旧入口导出，避免上层导入路径在结构拆分后整体震荡
__all__ = [
    "discover_species_from_directory",
    "read_request_config",
    "mcscan_auto_request_from_cli",
    "normalize_analysis_request",
    "mcscan_template_request",
]
