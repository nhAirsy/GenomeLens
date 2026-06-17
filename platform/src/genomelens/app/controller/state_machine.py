"""工作流状态定义"""

# region import
from __future__ import annotations

from enum import StrEnum

# endregion


class WorkflowState(StrEnum):
    """WorkflowState(工作流状态)：合法的高层状态"""

    # 这些状态会被 SignalBus、CLI 工作台和后续 GUI 共用，命名保持稳定比细粒度更重要
    PENDING = "PENDING"
    VALIDATING_INPUTS = "VALIDATING_INPUTS"
    PREPROCESSING_ANNOTATIONS = "PREPROCESSING_ANNOTATIONS"
    PREPARING_WORKSPACE = "PREPARING_WORKSPACE"
    CHECKING_TOOLCHAIN = "CHECKING_TOOLCHAIN"
    WRITING_MANIFEST = "WRITING_MANIFEST"
    RUNNING_ENGINE = "RUNNING_ENGINE"
    PARSING_ENGINE_SUMMARY = "PARSING_ENGINE_SUMMARY"
    FINALIZING = "FINALIZING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
