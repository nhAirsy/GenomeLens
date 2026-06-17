"""共享 workflow(工作流) 辅助模块"""

# region import
from __future__ import annotations

from pathlib import Path

# endregion


def read_bed_names(path: Path) -> list[str]:
    """从类 BED 文件读取 gene names(基因名称)"""

    names: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 4:
            # 第 4 列是 BED name，GenomeLens/JCVI 都把它当作基因主键。
            names.append(parts[3])
    return names
