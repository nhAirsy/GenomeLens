"""engine probe payload(引擎探测载荷) 生成"""

# region import
from __future__ import annotations

import platform
import sys

from jcvi_genomelens._version import ENGINE_NAME, ENGINE_VERSION, JCVI_UPSTREAM_VERSION, PATCHSET_VERSION
from jcvi_genomelens.runtime_profile import build_runtime_profile
from jcvi_genomelens.workflow_contract import SUPPORTED_WORKFLOWS

# endregion


BUNDLED_JCVI_MODULES = [
    "jcvi.compara.synteny",
    "jcvi.compara.catalog",
    "jcvi.graphics.synteny",
    "jcvi.graphics.dotplot",
    "jcvi.graphics.karyotype",
]


def build_probe_payload() -> dict[str, object]:
    """返回公开 probe JSON(探测 JSON) 契约"""

    profile = build_runtime_profile()
    # probe 输出既给 shell 做能力探测，也给 check 命令做诊断展示。
    return {
        "engine_name": ENGINE_NAME,
        "engine_version": ENGINE_VERSION,
        "jcvi_upstream_version": JCVI_UPSTREAM_VERSION,
        "jcvi_runtime_version": JCVI_UPSTREAM_VERSION,
        "patchset": PATCHSET_VERSION,
        "python": platform.python_version(),
        "distribution": "source",
        "status": "ok",
        # capabilities/dispatchable_workflows 目前保持同值，给未来更细粒度区分留接口。
        "capabilities": list(SUPPORTED_WORKFLOWS),
        "dispatchable_workflows": list(SUPPORTED_WORKFLOWS),
        "bundled_jcvi_modules": BUNDLED_JCVI_MODULES,
        "platform": sys.platform,
        **profile,
    }
