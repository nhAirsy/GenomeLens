"""GenomeLens 的 HAIant plugin adapter(智然体插件适配器)。

模块职责：
- 无参数时转发到 packaged runtime(打包运行时)，进入 workbench(工作台)。
- 有参数时读取 `params.json`，将平台字段翻译为 GenomeLens CLI(命令行接口)。
- 所有相对路径都按 `params.json` 所在目录解析。

边界：
- 不直接调用 GenomeLens 源码。
- 不实现 synteny(共线性) 算法。
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path


LOGGER_NAME = "genomelens_haiant_plugin"


class PluginError(Exception):
    """HAIant plugin adapter(智然体插件适配器) 预期失败时抛出。"""


def plugin_root() -> Path:
    """返回源码模式或打包模式下的 plugin root(插件根目录)。"""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def runtime_executable() -> Path:
    """定位已打包的 GenomeLens runtime executable(运行时可执行文件)。"""

    env = os.environ.get("GENOMELENS_PLUGIN_RUNTIME", "")
    if env:
        return Path(env).expanduser().resolve(strict=False)
    return plugin_root() / "runtime" / "GenomeLens" / "GenomeLens-runtime.exe"


def parse_bool(value: object) -> bool:
    """解析平台布尔值形式。"""

    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "on"}:
        return True
    if text in {"false", "0", "no", "off", ""}:
        return False
    raise PluginError(f"Invalid boolean value: {value}")


def resolve_param_path(
    base: Path, value: object, *, required: bool = False, must_exist: bool = False
) -> str:
    """按 `params.json` 位置解析参数路径。"""

    if value is None or str(value).strip() == "":
        if required:
            raise PluginError("Required path field is empty")
        return ""
    raw = Path(str(value))
    resolved = raw if raw.is_absolute() else base / raw
    resolved = resolved.resolve(strict=False)
    if must_exist and not resolved.exists():
        raise PluginError(f"Path does not exist: {resolved}")
    return str(resolved)


def load_params(path: str | Path) -> tuple[dict[str, object], Path]:
    """加载 params JSON(参数 JSON)，并返回 payload(载荷) 与基准目录。"""

    source = Path(path).expanduser().resolve(strict=False)
    if not source.is_file():
        raise PluginError(f"params.json not found: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PluginError(f"Invalid JSON: {source}") from exc
    if not isinstance(payload, dict):
        raise PluginError("params.json must contain a JSON object")
    return payload, source.parent


def _formats(value: object) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value]
    else:
        items = [item.strip() for item in str(value or "png").split(",")]
    return [item for item in items if item] or ["png"]


def _species_from_params(
    params: dict[str, object], base: Path, mode: str
) -> list[dict[str, object]]:
    species_payload = params.get("species")
    if not isinstance(species_payload, list) or not species_payload:
        raise PluginError("species must contain at least two entries")
    species: list[dict[str, object]] = []
    for index, item in enumerate(species_payload, start=1):
        if not isinstance(item, dict):
            raise PluginError(f"species[{index}] must be an object")
        name = str(item.get("name") or f"species{index}")
        if mode == "bed_cds":
            species.append(
                {
                    "name": name,
                    "input_mode": "bed_cds",
                    "bed": resolve_param_path(
                        base, item.get("bed"), required=True, must_exist=True
                    ),
                    "cds": resolve_param_path(
                        base, item.get("cds"), required=True, must_exist=True
                    ),
                }
            )
        elif mode == "gff_genome":
            species.append(
                {
                    "name": name,
                    "input_mode": "gff_genome",
                    "gff": resolve_param_path(
                        base, item.get("gff"), required=True, must_exist=True
                    ),
                    "genome": resolve_param_path(
                        base, item.get("genome"), required=True, must_exist=True
                    ),
                }
            )
        else:
            raise PluginError(f"Unsupported input_mode: {mode}")
    if len(species) < 2:
        raise PluginError("At least two species entries are required")
    return species


def _optional_path(base: Path, value: object) -> str:
    return resolve_param_path(base, value, must_exist=bool(value))


def _prepare_input_directory(
    params: dict[str, object], base: Path, output_dir: Path
) -> Path:
    """把平台显式物种清单拷贝到临时输入目录，供 `analyze mcscan` 自动发现。"""

    mode = str(params.get("input_mode") or "bed_cds")
    input_dir = output_dir / ".genomelens_plugin_input"
    input_dir.mkdir(parents=True, exist_ok=True)

    for species in _species_from_params(params, base, mode):
        name = str(species["name"])
        if mode == "bed_cds":
            bed_src = Path(str(species["bed"]))
            cds_src = Path(str(species["cds"]))
            ext = bed_src.suffix
            shutil.copy2(bed_src, input_dir / f"{name}{ext}")
            cds_ext = cds_src.suffix
            shutil.copy2(cds_src, input_dir / f"{name}{cds_ext}")
        else:
            gff_src = Path(str(species["gff"]))
            genome_src = Path(str(species["genome"]))
            shutil.copy2(gff_src, input_dir / f"{name}{gff_src.suffix}")
            shutil.copy2(genome_src, input_dir / f"{name}{genome_src.suffix}")

    return input_dir


def _append_if_truthy(argv: list[str], flag: str, value: object) -> None:
    """当值非空时追加 CLI 参数"""

    if value is None:
        return
    text = str(value).strip()
    if text:
        argv.extend([flag, text])


def write_runtime_request(params: dict[str, object], base: Path) -> Path:
    """写入 GenomeLens analysis request(JSON 请求)，并返回请求文件路径。

    当前 CLI 已移除 `analyze run`，本函数仅保留为轨迹文件；实际运行时通过
    `analyze mcscan` 目录发现模式调用。
    """

    mode = str(params.get("input_mode") or "bed_cds")
    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    request = {
        "schema_version": 1,
        "kind": "analysis_request",
        "method": "mcscan",
        "input": {
            "mode": mode,
            "directory": "",
            "species": _species_from_params(params, base, mode),
        },
        "output": {
            "directory": str(output_dir),
            "force": parse_bool(params.get("force", True)),
            "formats": _formats(params.get("formats") or "png"),
        },
        "config": {
            "project_config": _optional_path(base, params.get("config")),
            "method_config": _optional_path(base, params.get("jcvi_config")),
        },
        "options": {
            "preset": str(params.get("preset") or "auto"),
            "threads": int(params.get("threads") or 4),
            "min_block_size": int(params.get("min_block_size") or 5),
            "workflow": str(params.get("workflow") or "graphics_synteny"),
            "jcvi_engine": _optional_path(base, params.get("jcvi_engine")),
            "blastn": _optional_path(base, params.get("blastn")),
            "makeblastdb": _optional_path(base, params.get("makeblastdb")),
            "jcvi_layout": _optional_path(base, params.get("jcvi_layout")),
            "jcvi_seqids": _optional_path(base, params.get("jcvi_seqids")),
            "allow_simplified_fallback": parse_bool(
                params.get("allow_simplified_fallback", False)
            ),
        },
    }
    target = output_dir / "genomelens_request.json"
    target.write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target


def setup_adapter_logging(base: Path, output_dir_value: object) -> logging.Logger:
    """参数可用时，在 `output_dir/run.log` 下设置 adapter logs(适配器日志)。"""

    output_dir = Path(resolve_param_path(base, output_dir_value or "output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / "run.log"
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    close_adapter_logging()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="a")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def close_adapter_logging() -> None:
    """Flush and close HAIant adapter logging handlers."""

    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.flush()
        finally:
            handler.close()


def _build_runtime_command(params_path: str | Path) -> list[str]:
    """把 `params.json` 转换为 GenomeLens runtime argv(运行时参数向量)。

    当前 CLI 仅保留 `analyze mcscan`，因此先把平台显式物种清单拷贝到临时输入
    目录，再按目录发现模式调用 `analyze mcscan`。
    """

    params, base = load_params(params_path)
    logger = setup_adapter_logging(base, params.get("output_dir"))
    logger.info("Loaded params.json: %s", params_path)
    runtime = runtime_executable()
    if not runtime.is_file():
        raise PluginError(f"GenomeLens runtime executable not found: {runtime}")

    output_dir = Path(resolve_param_path(base, params.get("output_dir") or "output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    input_dir = _prepare_input_directory(params, base, output_dir)

    # 保留请求文件作为运行轨迹，实际 CLI 不再读取它
    write_runtime_request(params, base)

    argv = [
        str(runtime),
        "analyze",
        "mcscan",
        str(input_dir),
        str(output_dir),
        "--force",
    ]

    _append_if_truthy(argv, "--config", _optional_path(base, params.get("config")))
    _append_if_truthy(
        argv, "--jcvi-config", _optional_path(base, params.get("jcvi_config"))
    )
    _append_if_truthy(argv, "--threads", params.get("threads"))
    _append_if_truthy(argv, "--min-block-size", params.get("min_block_size"))
    _append_if_truthy(argv, "--jcvi-workflow", params.get("workflow"))
    _append_if_truthy(argv, "--formats", ",".join(_formats(params.get("formats"))))
    _append_if_truthy(
        argv, "--jcvi-engine", _optional_path(base, params.get("jcvi_engine"))
    )
    _append_if_truthy(argv, "--blastn", _optional_path(base, params.get("blastn")))
    _append_if_truthy(
        argv, "--makeblastdb", _optional_path(base, params.get("makeblastdb"))
    )
    _append_if_truthy(
        argv, "--jcvi-layout", _optional_path(base, params.get("jcvi_layout"))
    )
    _append_if_truthy(
        argv, "--jcvi-seqids", _optional_path(base, params.get("jcvi_seqids"))
    )

    if parse_bool(params.get("allow_simplified_fallback", False)):
        argv.append("--allow-simplified-fallback")

    logger.info("Dispatching GenomeLens runtime: %s", argv)
    return argv


def build_runtime_command(params_path: str | Path) -> list[str]:
    """Build GenomeLens runtime argv and release adapter log handles."""

    try:
        return _build_runtime_command(params_path)
    finally:
        close_adapter_logging()


def run_runtime(argv: list[str]) -> int:
    """运行已打包 runtime(运行时)，并返回退出码。"""

    completed = subprocess.run(argv, shell=False, check=False)
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    """plugin executable(插件可执行文件) 入口。"""

    if argv is None:
        argv = sys.argv[1:]
    try:
        runtime = runtime_executable()
        if not argv:
            if not runtime.is_file():
                raise PluginError(f"GenomeLens runtime executable not found: {runtime}")
            return run_runtime([str(runtime)])
        if len(argv) != 1:
            raise PluginError("Expected zero arguments or one params.json path")
        return run_runtime(build_runtime_command(argv[0]))
    except PluginError as exc:
        print(f"GenomeLens HAIant plugin error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
