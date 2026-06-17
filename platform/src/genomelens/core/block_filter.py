"""可选的显示层 block(区块) 过滤"""

# region import
from __future__ import annotations

# endregion


def keep_block(size: int, *, min_block_size: int) -> bool:
    """block(区块) 通过显示层过滤时返回 True"""

    # 展示层过滤只关心块大小阈值，不参与任何上游生物学计算。
    return size >= min_block_size
