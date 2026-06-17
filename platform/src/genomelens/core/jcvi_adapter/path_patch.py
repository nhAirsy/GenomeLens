"""Windows 路径规范化辅助模块"""

# region import
from __future__ import annotations

from pathlib import Path

# endregion


def absolute_path(value: str | Path) -> str:
    """返回供 manifest JSON(清单 JSON) 使用的绝对路径字符串"""

    if not value:
        return ""
    # manifest 对外使用字符串协议，这里集中处理 Path -> 绝对字符串 的收敛。
    return str(Path(value).expanduser().resolve(strict=False))
