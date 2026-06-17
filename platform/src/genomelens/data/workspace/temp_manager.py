"""临时目录生命周期辅助模块"""

# region import
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

# endregion


@dataclass
class TempManager:
    """TempManager(临时目录管理器)：持有安全临时根目录"""

    root: Path

    def create(self) -> Path:
        """创建并返回临时根目录"""

        # 调用方持有 TempManager 时，只约定 root，不关心具体 mkdir 细节。
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    def clean(self) -> None:
        """仅在临时根目录存在时删除它"""

        if self.root.exists():
            # 临时目录允许整树删除，但删除边界严格限定在 manager.root。
            shutil.rmtree(self.root)
