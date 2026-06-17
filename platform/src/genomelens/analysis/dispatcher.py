"""AnalysisDispatcher(分析调度器)"""

# region import
from __future__ import annotations

import json
from pathlib import Path

from genomelens.analysis.methods.registry import get_method
from genomelens.analysis.request_loader import write_analysis_request
from genomelens.analysis.request_models import AnalysisRequest
from genomelens.analysis.request_normalizer import normalize_analysis_request
from genomelens.app.controller.orchestrator import WorkflowOrchestrator
from genomelens.app.errors import messages
from genomelens.app.errors.exceptions import InputValidationError
from genomelens.app.events.signal_bus import SignalBus
from genomelens.core.summary_models import RunSummary

# endregion


class AnalysisDispatcher:
    """统一调度 analysis request(分析请求)"""

    def dispatch(self, request: AnalysisRequest) -> RunSummary:
        """运行一个 AnalysisRequest(分析请求)"""

        # dispatcher 永远先消费规范化后的请求，这样 CLI、插件和未来 GUI 入口都复用同一条执行路径
        normalized = normalize_analysis_request(request)
        plugin = get_method(normalized.method)
        if plugin is None:
            raise InputValidationError(messages.REQUEST_UNSUPPORTED_METHOD.format(method=normalized.method))

        plugin.validate_request(normalized)
        provider = plugin.get_provider()
        summary = WorkflowOrchestrator().run(normalized, provider, SignalBus())
        if isinstance(summary, dict):
            summary = RunSummary.from_json(summary)

        # request 快照在 summary 生成后回填，确保最终 run_summary 指向的是实际执行参数
        self._write_request_snapshot(normalized, summary)
        return summary

    def _write_request_snapshot(self, request: AnalysisRequest, summary: RunSummary) -> None:
        outdir = Path(request.output.directory).expanduser().resolve(strict=False)
        request_path = write_analysis_request(request, outdir / "inputs" / "analysis_request.json")
        data = summary.to_json()
        data["analysis_request_path"] = str(request_path)

        # run_summary 已由 runner 写出，这里只做补充字段回填，避免 dispatcher 重新组装摘要对象
        run_summary_path = outdir / "report" / "run_summary.json"
        if run_summary_path.is_file():
            run_summary_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
