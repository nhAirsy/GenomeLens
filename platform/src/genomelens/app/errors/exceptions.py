"""领域异常及其稳定退出码语义"""

# region import
from __future__ import annotations

from genomelens.app.errors.error_codes import ErrorCode

# endregion


class GenomeLensError(Exception):
    """GenomeLens 预期失败的基础异常"""

    exit_code = 1

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = ErrorCode.UNKNOWN,
        message_key: str = "",
    ) -> None:
        super().__init__(message)
        # code/message_key 会被 CLI 格式化层和潜在 GUI 层复用。
        self.code = code
        self.message_key = message_key


class InputValidationError(GenomeLensError):
    """用户输入或 CLI(命令行接口) 组合无效时抛出"""

    exit_code = 3

    def __init__(self, message: str) -> None:
        super().__init__(message, code=ErrorCode.REQUEST_INVALID)


class WorkspaceError(GenomeLensError):
    """无法创建或安全复用工作区时抛出"""

    exit_code = 4

    def __init__(self, message: str) -> None:
        super().__init__(message, code=ErrorCode.WORKSPACE_ERROR)


class ToolchainError(GenomeLensError):
    """无法定位或执行必需 runtime tool(运行时工具) 时抛出"""

    exit_code = 5

    def __init__(self, message: str, *, code: ErrorCode = ErrorCode.TOOLCHAIN_MISSING) -> None:
        # toolchain 失败既可能是“找不到”，也可能是“存在但不可运行”，所以 code 可覆写。
        super().__init__(message, code=code)


class EngineProbeError(GenomeLensError):
    """外部 engine probe(引擎探测) 契约失败时抛出"""

    exit_code = 5

    def __init__(self, message: str) -> None:
        super().__init__(message, code=ErrorCode.ENGINE_FAILED)


class EngineRunError(GenomeLensError):
    """外部 engine(引擎) 运行失败时抛出"""

    exit_code = 7

    def __init__(self, message: str) -> None:
        super().__init__(message, code=ErrorCode.ENGINE_FAILED)


class SummaryParseError(GenomeLensError):
    """engine summary(引擎摘要) 缺失或格式错误时抛出"""

    exit_code = 7

    def __init__(self, message: str) -> None:
        super().__init__(message, code=ErrorCode.SUMMARY_PARSE_ERROR)


class ConfigError(GenomeLensError):
    """配置文件解析或校验失败时抛出"""

    exit_code = 3

    def __init__(self, message: str) -> None:
        super().__init__(message, code=ErrorCode.CONFIG_INVALID)
