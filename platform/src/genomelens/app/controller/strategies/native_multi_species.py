"""原生多物种策略桩

未来某个引擎声明支持原生多物种分析时，再填充此策略。
当前仅作为 `WorkflowOrchestrator` 的扩展点保留。
"""

# region import
from __future__ import annotations

from genomelens.analysis.request_models import AnalysisRequest
from genomelens.app.controller.workflow_provider import WorkflowProvider
from genomelens.app.events.signal_bus import SignalBus
from genomelens.core.summary_models import RunSummary

# endregion


class NativeMultiSpecies:
    """NativeMultiSpecies(原生多物种策略)：直接调用 provider 的多物种能力"""

    def execute(
        self,
        request: AnalysisRequest,
        provider: WorkflowProvider,
        signal_bus: SignalBus,
    ) -> RunSummary:
        """把请求直接交给支持原生多物种的 provider"""

        # 当前没有真实引擎实现该能力，保留桩以便后续切换
        raise NotImplementedError(
            f"method '{provider.name}' declares native multi-species support but no implementation is available"
        )
