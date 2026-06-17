"""在 shell(外壳) 中不导入 jcvi 的前提下探测可选 compiled extensions(编译扩展)"""

# region import
from __future__ import annotations

from pathlib import Path

# endregion


def probe_pyd(path: str | Path) -> dict[str, str]:
    """返回 compiled extension(编译扩展) 路径的简单状态"""

    target = Path(path)
    # shell 侧只做存在性探测，不在这里尝试真正 import 扩展模块。
    return {"status": "ok" if target.is_file() else "missing", "path": str(target)}
