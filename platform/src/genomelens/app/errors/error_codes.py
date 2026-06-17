"""ErrorCode(错误码)：供 GUI/插件/CI 做程序化错误识别"""

# region import
from __future__ import annotations

from enum import Enum

# endregion


class ErrorCode(Enum):
    """GenomeLens 平台级错误码

    错误码与 HTTP 状态码无关，它描述的是「哪一类平台失败」，便于上层
    （GUI、插件、Agent）统一处理重试、提示或兜底策略。
    """

    # 这些值面向 GUI / 插件 / 自动化调用方，名称应保持稳定。
    UNKNOWN = "unknown"
    REQUEST_INVALID = "request_invalid"
    TOOLCHAIN_MISSING = "toolchain_missing"
    ENGINE_FAILED = "engine_failed"
    INPUT_NOT_FOUND = "input_not_found"
    CONFIG_INVALID = "config_invalid"
    WORKSPACE_ERROR = "workspace_error"
    SUMMARY_PARSE_ERROR = "summary_parse_error"
