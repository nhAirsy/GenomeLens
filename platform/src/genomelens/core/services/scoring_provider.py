"""ML 评分跨切服务"""

# region import
from __future__ import annotations

from typing import Protocol, runtime_checkable

from genomelens.analysis.request_models import AnalysisRequest
from genomelens.core.summary_models import RunSummary, ScoringBlock

# endregion


@runtime_checkable
class ScoringProvider(Protocol):
    """ScoringProvider(评分提供者)：在工作流成功后对结果进行评分"""

    def is_available(self) -> bool:
        """返回当前评分服务是否可用"""

        ...

    def score(self, summary: RunSummary, request: AnalysisRequest) -> ScoringBlock:
        """根据 RunSummary 与原始请求生成评分块"""

        ...


class NoOpScoringProvider:
    """NoOpScoringProvider(空评分提供者)：默认占位，不执行实际评分"""

    def is_available(self) -> bool:
        """空评分提供者永远返回不可用"""

        return False

    def score(self, summary: RunSummary, request: AnalysisRequest) -> ScoringBlock:
        """直接返回现有 scoring 块，不做任何修改"""

        return summary.scoring
