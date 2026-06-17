"""工作流编排器：根据请求特征选择执行策略"""

# region import
from __future__ import annotations

import warnings
from dataclasses import replace

from genomelens.analysis.request_models import AnalysisRequest
from genomelens.app.controller.state_machine import WorkflowState
from genomelens.app.controller.strategies.pairwise_aggregated import PairwiseAggregatedMultiSpecies
from genomelens.app.controller.workflow_provider import WorkflowProvider
from genomelens.app.events.signal_bus import SignalBus
from genomelens.core.services.scoring_provider import NoOpScoringProvider, ScoringProvider
from genomelens.core.summary_models import RunSummary

# endregion


class WorkflowOrchestrator:
    """WorkflowOrchestrator(工作流编排器)：把请求路由到合适的执行策略"""

    def __init__(self, scoring_provider: ScoringProvider | None = None) -> None:
        self._scoring_provider = scoring_provider or NoOpScoringProvider()

    def run(
        self,
        request: AnalysisRequest,
        provider: WorkflowProvider,
        signal_bus: SignalBus,
    ) -> RunSummary:
        """根据物种数量和 provider 能力选择策略并执行"""

        result = self._execute(request, provider, signal_bus)
        return self._apply_scoring(result, request)

    def _execute(
        self,
        request: AnalysisRequest,
        provider: WorkflowProvider,
        signal_bus: SignalBus,
    ) -> RunSummary:
        """根据请求特征路由到具体策略"""

        species_count = len(request.input.species)

        # 恰好两个物种：直接交给 provider 的 pairwise 能力
        if species_count == 2:
            return provider.run(request, signal_bus)

        # 多于两个物种且 provider 声明原生支持：走原生多物种策略
        if provider.supports_native_multi_species():
            from genomelens.app.controller.strategies.native_multi_species import NativeMultiSpecies

            return NativeMultiSpecies().execute(request, provider, signal_bus)

        # 默认：pairwise 聚合策略
        return PairwiseAggregatedMultiSpecies().execute(request, provider, signal_bus)

    def _apply_scoring(self, summary: RunSummary, request: AnalysisRequest) -> RunSummary:
        """在工作流成功后注入评分结果；评分失败不改变原始 SUCCEEDED 状态"""

        if summary.status != "SUCCEEDED" or not self._scoring_provider.is_available():
            return summary

        try:
            scoring = self._scoring_provider.score(summary, request)
            return replace(summary, scoring=scoring)
        except Exception as exc:  # noqa: BLE001 - 评分是增量增强，失败不应影响主流程
            warnings.warn(f"Scoring provider failed and was skipped: {exc}", stacklevel=2)
            return summary

    def _emit_state(self, signal_bus: SignalBus, state: WorkflowState) -> None:
        """统一发射状态事件"""

        signal_bus.emit("state", state=state.value)
