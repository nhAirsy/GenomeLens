"""排序聚合服务"""

# region import
from __future__ import annotations

from typing import Protocol, runtime_checkable

# endregion


@runtime_checkable
class RankingAggregationService(Protocol):
    """RankingAggregationService(排序聚合服务)：合并多个评分模型的排序结果"""

    def aggregate(self, rankings: list[dict[str, object]]) -> dict[str, object]:
        """把多组排序聚合成一组最终排序"""

        ...


class NoOpRankingAggregationService:
    """NoOpRankingAggregationService(空排序聚合服务)：直接返回首个输入"""

    def aggregate(self, rankings: list[dict[str, object]]) -> dict[str, object]:
        """不做聚合，仅返回第一个排序或空字典"""

        return rankings[0] if rankings else {}
