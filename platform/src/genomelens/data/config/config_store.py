"""读取和写入 GenomeLens configuration JSON(配置 JSON)"""

# region import
from __future__ import annotations

import json
import os
from pathlib import Path

from genomelens.app.errors.exceptions import WorkspaceError
from genomelens.core.json_utils import _str
from genomelens.data.config.config_models import (
    ConfigModel,
    WorkspaceConfig,
    default_workspace_root,
    normalize_path_string,
)

# endregion


DEFAULT_CONFIG_NAME = "genomelens.config.json"
DEFAULT_JCVI_CONFIG_NAME = "jcvi.config.json"


def default_config(workspace: str | Path | None = None) -> ConfigModel:
    """为工作区构建默认配置模型"""

    root = normalize_path_string(workspace or default_workspace_root())
    jcvi_path = normalize_path_string(Path(root) / DEFAULT_JCVI_CONFIG_NAME)
    return ConfigModel(
        workspace=WorkspaceConfig(
            workspace_root=root,
            temp_root=normalize_path_string(Path(root) / "temp"),
            default_output_root=normalize_path_string(Path(root) / "results"),
            jcvi_config_path=jcvi_path,
        )
    )


def default_config_path(workspace: str | Path | None = None) -> Path:
    """返回工作区的默认配置路径"""

    root = Path(normalize_path_string(workspace or default_workspace_root()))
    return root / DEFAULT_CONFIG_NAME


def default_jcvi_config_path(workspace: str | Path | None = None) -> Path:
    """返回工作区的默认 JCVI 配置路径"""

    root = Path(normalize_path_string(workspace or default_workspace_root()))
    return root / DEFAULT_JCVI_CONFIG_NAME


def _write_json_file(payload: dict[str, object], path: str | Path, *, force: bool = False) -> Path:
    target = Path(path).expanduser().resolve(strict=False)
    if target.exists() and not force:
        raise WorkspaceError(f"配置已经存在：{target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def write_split_config(
    config: ConfigModel,
    config_path: str | Path,
    jcvi_config_path: str | Path,
    *,
    force: bool = False,
) -> tuple[Path, Path]:
    """写出工具主配置和 JCVI 子配置两个文件"""

    jcvi_path = Path(jcvi_config_path).expanduser().resolve(strict=False)

    # 主配置里会回写 JCVI 子配置的最终路径，保证后续只读主配置时也能找到子配置
    config.workspace.jcvi_config_path = normalize_path_string(jcvi_path)
    main_path = _write_json_file(config.to_project_json_dict(), config_path, force=force)
    written_jcvi = _write_json_file(config.to_jcvi_json_dict(), jcvi_path, force=force)
    return main_path, written_jcvi


def _read_json_object(path: str | Path, label: str) -> dict[str, object]:
    source = Path(path).expanduser().resolve(strict=False)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise WorkspaceError(f"{label} 必须是 JSON object(对象)：{source}")
    return data


def _merge_jcvi_config(config: ConfigModel, path: str | Path) -> ConfigModel:
    jcvi_data = _read_json_object(path, "JCVI 配置")

    # JCVI 子配置只覆盖 toolchain/runtime/mcscan/local_synteny 相关字段，不改主工作区根目录
    merged = ConfigModel.from_json_dict(
        {
            "workspace_root": config.workspace.workspace_root,
            "temp_root": config.workspace.temp_root,
            "default_output_root": config.workspace.default_output_root,
            "jcvi_config_path": normalize_path_string(path),
            "log_level": config.runtime.log_level,
            **jcvi_data,
        }
    )
    return ConfigModel(
        workspace=WorkspaceConfig(
            workspace_root=config.workspace.workspace_root,
            temp_root=config.workspace.temp_root,
            default_output_root=config.workspace.default_output_root,
            jcvi_config_path=normalize_path_string(path),
        ),
        toolchain=merged.toolchain,
        runtime=merged.runtime,
        mcscan=merged.mcscan,
        local_synteny=merged.local_synteny,
        schema_version=max(config.schema_version, merged.schema_version),
    )


def read_config(path: str | Path, *, jcvi_config_path: str | Path | None = None) -> ConfigModel:
    """读取 config JSON(配置 JSON)，并按需合并 JCVI 子配置"""

    source = Path(path).expanduser().resolve(strict=False)
    data = _read_json_object(source, "配置")
    config = ConfigModel.from_json_dict(data)
    raw_jcvi = (
        _str(jcvi_config_path) or _str(data.get("jcvi_config_path")) or os.environ.get("GENOMELENS_JCVI_CONFIG", "")
    )
    if not raw_jcvi.strip():
        return config

    # 允许主配置里的 JCVI 路径使用相对路径，并以主配置文件所在目录为基准解析
    jcvi_source = Path(raw_jcvi).expanduser()
    if not jcvi_source.is_absolute():
        jcvi_source = source.parent / jcvi_source
    jcvi_source = jcvi_source.resolve(strict=False)
    if not jcvi_source.is_file():
        raise WorkspaceError(f"JCVI 配置不存在：{jcvi_source}")
    return _merge_jcvi_config(config, jcvi_source)


def read_optional_config(
    path: str | Path | None = None,
    *,
    jcvi_config_path: str | Path | None = None,
) -> ConfigModel | None:
    """读取显式 config(配置)，或读取 `GENOMELENS_CONFIG` 指向的配置"""

    raw = str(path or os.environ.get("GENOMELENS_CONFIG", "")).strip()
    if not raw:
        raw_jcvi = _str(jcvi_config_path) or os.environ.get("GENOMELENS_JCVI_CONFIG", "")
        if raw_jcvi:
            # 只有 JCVI 子配置时，基于默认主配置补齐工作区字段，避免调用方手写兜底逻辑
            config = default_config()
            source = Path(raw_jcvi).expanduser().resolve(strict=False)
            if not source.is_file():
                raise WorkspaceError(f"JCVI 配置不存在：{source}")
            return _merge_jcvi_config(config, source)
        return None
    source = Path(raw).expanduser().resolve(strict=False)
    if not source.is_file():
        raise WorkspaceError(f"配置不存在：{source}")
    return read_config(source, jcvi_config_path=jcvi_config_path)
