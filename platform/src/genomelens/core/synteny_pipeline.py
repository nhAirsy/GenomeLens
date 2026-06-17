"""shell(外壳) 侧 synteny pipeline(共线性流水线) 门面"""

# region import
from __future__ import annotations

from genomelens.app.controller.workflow_controller import WorkflowController
from genomelens.core.jcvi_adapter.adapter_models import McscanRequest
from genomelens.core.summary_models import RunSummary

# endregion


def run_mcscan(request: McscanRequest) -> RunSummary:
    """通过应用控制器运行一次 MCscan workflow(MCscan 工作流)"""

    # 保留这个门面函数，便于脚本调用方不必感知 app/controller 分层。
    return WorkflowController().run_mcscan(request)
