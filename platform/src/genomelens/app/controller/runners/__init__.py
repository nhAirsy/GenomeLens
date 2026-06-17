"""工作流 runner 子模块：把 WorkflowController 中的长方法拆分到单一职责模块"""

# region import
from __future__ import annotations

from genomelens.app.controller.runners.multi_species_runner import run_multi_species_mcscan
from genomelens.app.controller.runners.pairwise_runner import run_pairwise_mcscan
from genomelens.app.controller.runners.reference_vs_targets_runner import run_reference_vs_targets_mcscan

# endregion


__all__ = [
    "run_pairwise_mcscan",
    "run_reference_vs_targets_mcscan",
    "run_multi_species_mcscan",
]
