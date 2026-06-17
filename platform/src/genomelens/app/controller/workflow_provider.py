"""工作流提供者协议"""

# region import
from __future__ import annotations

from typing import Protocol

from genomelens.analysis.request_models import AnalysisRequest
from genomelens.app.events.signal_bus import SignalBus
from genomelens.core.summary_models import RunSummary

# endregion


class WorkflowProvider(Protocol):
    """WorkflowProvider(工作流提供者)：具体分析方法与平台编排器之间的协议

    每个分析方法（mcscan、syri、pangenome 等）实现一个 provider，
    由 `WorkflowOrchestrator` 根据物种数量和 provider 能力决定如何调用。
    """

    @property
    def name(self) -> str:
        """返回方法名称，用于日志与调试"""

        ...

    def supports_native_multi_species(self) -> bool:
        """是否支持原生多物种执行（非 pairwise 聚合）"""

        ...

    def run(self, request: AnalysisRequest, signal_bus: SignalBus) -> RunSummary:
        """执行一次分析任务

        调用方保证传入的 request 已经过规范化，且 species 数量适合该 provider
        （pairwise 场景下为 2 个物种，原生多物种场景下为 2+ 个物种）。
        """

        ...
