"""多物种布局优化服务"""

# region import
from __future__ import annotations

from typing import Protocol, runtime_checkable

from genomelens.core.models import GenomeInputSpec

# endregion


@runtime_checkable
class LayoutOptimizer(Protocol):
    """LayoutOptimizer(布局优化器)：根据物种和共线性边优化全局排列"""

    def optimize(
        self,
        species: list[GenomeInputSpec],
        edges: list[dict[str, object]],
    ) -> dict[str, object]:
        """返回包含优化后布局信息的字典

        返回字典至少包含 ``species_order``，后续渲染层按该顺序绘制物种轨道。
        """

        ...


class NoOpLayoutOptimizer:
    """NoOpLayoutOptimizer(空布局优化器)：保持输入顺序不变"""

    def optimize(
        self,
        species: list[GenomeInputSpec],
        edges: list[dict[str, object]],
    ) -> dict[str, object]:
        """直接返回输入物种顺序，不做任何优化"""

        return {
            "species_order": [item.name for item in species],
            "edges": list(edges),
            "optimized": False,
        }
