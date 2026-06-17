"""把内部异常转换为面向 CLI(命令行接口) 的消息和退出码"""

# region import
from __future__ import annotations

import traceback

from genomelens.app.errors.exceptions import GenomeLensError

# endregion


def exit_code_for(exc: BaseException) -> int:
    """返回异常对应的稳定进程退出码"""

    # 自定义业务异常自带退出码；未知异常统一回落到 1，便于 shell/CI 判断失败
    if isinstance(exc, GenomeLensError):
        return exc.exit_code
    return 1


def format_user_error(exc: BaseException, *, debug: bool = False) -> str:
    """格式化简洁的用户可见错误，并可附带 traceback(回溯)"""

    message = f"{exc.__class__.__name__}: {exc}"
    if debug:
        # debug 模式保留完整 traceback，普通 CLI 输出则尽量保持简洁
        return message + "\n" + traceback.format_exc()
    return message
