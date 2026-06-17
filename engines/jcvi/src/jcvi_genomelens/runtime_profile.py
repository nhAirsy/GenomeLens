"""Engine runtime profile helpers"""

# region import
from __future__ import annotations

import importlib

# endregion


CYTHON_EXTENSION_MODULES = (
    "jcvi.formats.cblast",
    "jcvi.assembly.chic",
)


def build_runtime_profile() -> dict[str, object]:
    """Describe the current engine runtime mode and compiled extensions"""

    loaded: list[str] = []
    missing: list[str] = []
    errors: dict[str, str] = {}
    for module_name in CYTHON_EXTENSION_MODULES:
        try:
            importlib.import_module(module_name)
            loaded.append(module_name)
        except ModuleNotFoundError:
            # 缺少可选扩展不应阻止 engine 运行，只影响 runtime_mode/诊断信息。
            missing.append(module_name)
        except Exception as exc:  # noqa: BLE001 - diagnostic payload should report import failures verbatim
            errors[module_name] = f"{exc.__class__.__name__}: {exc}"
    # 只要有扩展成功加载就标记 accelerated；具体缺哪些扩展仍由明细字段表达。
    runtime_mode = "accelerated" if loaded else "core"
    return {
        "runtime_mode": runtime_mode,
        "loaded_extensions": loaded,
        "missing_extensions": missing,
        "extension_errors": errors,
    }
