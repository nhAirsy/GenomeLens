"""写出 `engine_run_summary.json`"""

# region import
from __future__ import annotations

import json
from pathlib import Path

from jcvi_genomelens._version import ENGINE_NAME, ENGINE_VERSION, JCVI_UPSTREAM_VERSION, PATCHSET_VERSION
from jcvi_genomelens.runtime.command_runner import CommandAudit
from jcvi_genomelens.runtime_profile import build_runtime_profile

# endregion


def _artifact_index(artifacts: dict[str, object], workflow: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    image_suffixes = {".png", ".pdf", ".svg", ".jpg", ".jpeg"}
    for key, value in artifacts.items():
        values = value if isinstance(value, list) else [value]
        for index, item in enumerate(values):
            if not isinstance(item, str) or not item:
                continue
            suffix = Path(item).suffix.lower().lstrip(".")
            artifact_id = key if len(values) == 1 else f"{key}_{index + 1}"
            # engine summary 先把 artifact 平铺成索引，方便 shell/GUI 不理解业务键也能浏览。
            records.append(
                {
                    "artifact_id": artifact_id,
                    "artifact_type": key,
                    "path": item,
                    "produced_by": workflow,
                    "format": suffix,
                    "preview": Path(item).suffix.lower() in image_suffixes,
                    "input_refs": [],
                    "metadata": {},
                }
            )
    return records


def write_summary(
    path: str | Path,
    *,
    status: str,
    workflow: str,
    commands: list[CommandAudit],
    artifacts: dict[str, object],
    logs: dict[str, str],
    schema_version: int = 1,
    task: dict[str, object] | None = None,
    species: list[dict[str, object]] | None = None,
    expected_outputs: list[str] | None = None,
    error: object = None,
) -> Path:
    """写出公开 engine summary(引擎摘要)"""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    profile = build_runtime_profile()
    # 运行时画像与版本信息在 engine 侧一次性固化，shell 层只做透传。
    payload = {
        "status": status,
        "schema_version": schema_version,
        "workflow": workflow,
        "task": task or {},
        "species": species or [],
        "expected_outputs": expected_outputs or [],
        "engine_name": ENGINE_NAME,
        "engine_version": ENGINE_VERSION,
        "jcvi_upstream_version": JCVI_UPSTREAM_VERSION,
        "distribution": "source",
        "patchset": PATCHSET_VERSION,
        **profile,
        "commands": [command.to_json() for command in commands],
        "artifacts": artifacts,
        "artifact_index": _artifact_index(artifacts, workflow),
        "logs": logs,
        "error": error,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target
