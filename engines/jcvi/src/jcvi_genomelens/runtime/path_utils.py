"""路径兼容性辅助模块"""

# region import
from __future__ import annotations

from pathlib import Path

# endregion


def ensure_dir(path: str | Path) -> Path:
    """创建并返回目录路径"""

    target = Path(path).expanduser().resolve(strict=False)
    # engine workflow 常把 outdir/path 当作“存在即可”的契约，这里集中兜底。
    target.mkdir(parents=True, exist_ok=True)
    return target
