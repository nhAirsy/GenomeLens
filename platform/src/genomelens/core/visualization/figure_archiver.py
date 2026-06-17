"""把最终 figure artifacts(图件制品) 复制到公开结果目录"""

# region import
from __future__ import annotations

import shutil
from pathlib import Path

# endregion


def archive_figures(figures: list[str], target_dir: str | Path) -> list[str]:
    """把 figures(图件) 复制到 `results/figures`，并返回最终路径"""

    destination = Path(target_dir)
    destination.mkdir(parents=True, exist_ok=True)
    archived: list[str] = []
    for figure in figures:
        source = Path(figure)
        if source.is_file():
            target = destination / source.name
            if source.resolve(strict=False) != target.resolve(strict=False):
                # engine 产物可能散落在多个子目录，这里统一归档到公开结果目录。
                shutil.copy2(source, target)
            archived.append(str(target))
    return archived
