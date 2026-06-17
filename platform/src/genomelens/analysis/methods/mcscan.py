"""mcscan analysis method(mcscan 分析方法) 适配器"""

# region import
from __future__ import annotations

from genomelens.analysis.methods.mcscan_request_mapping import to_mcscan_request
from genomelens.analysis.request_models import AnalysisRequest
from genomelens.core.summary_models import RunSummary
from genomelens.core.synteny_pipeline import run_mcscan

# endregion


def run_mcscan_method(request: AnalysisRequest) -> RunSummary:
    """运行 mcscan analysis method(mcscan 分析方法)"""

    return run_mcscan(to_mcscan_request(request))
