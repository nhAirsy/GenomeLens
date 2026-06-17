import json
import logging
import os
import shutil
from pathlib import Path

from genomelens_haiant_plugin import (
    build_runtime_command,
    close_adapter_logging,
    parse_bool,
    setup_adapter_logging,
)


def test_parse_bool_forms() -> None:
    assert parse_bool("yes") is True
    assert parse_bool("0") is False


def _file_handler(logger: logging.Logger) -> logging.FileHandler:
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler
    raise AssertionError("file handler not found")


def test_setup_adapter_logging_closes_previous_file_handler(tmp_path: Path) -> None:
    logger = setup_adapter_logging(tmp_path, "first")
    first_handler = _file_handler(logger)

    setup_adapter_logging(tmp_path, "second")

    assert first_handler.stream is None
    shutil.rmtree(tmp_path / "first")
    close_adapter_logging()


def test_build_runtime_command_resolves_relative_paths(
    tmp_path: Path, monkeypatch
) -> None:
    runtime = tmp_path / "GenomeLens-runtime.exe"
    runtime.write_text("", encoding="utf-8")
    monkeypatch.setenv("GENOMELENS_PLUGIN_RUNTIME", str(runtime))
    root = Path(__file__).resolve().parents[3]
    sample_params = root / "references" / "samples" / "haiant" / "params.json"
    params_payload = json.loads(sample_params.read_text(encoding="utf-8"))
    for item in params_payload["species"]:
        for key in ("bed", "cds", "gff", "genome"):
            if item.get(key):
                item[key] = str(
                    (sample_params.parent / item[key]).resolve(strict=False)
                )
    params_payload["output_dir"] = str(tmp_path / "output")
    params = tmp_path / "params.json"
    params.write_text(json.dumps(params_payload, ensure_ascii=False), encoding="utf-8")
    argv = build_runtime_command(params)
    assert argv[:3] == [str(runtime), "analyze", "mcscan"]
    input_dir = Path(argv[3])
    output_dir = Path(argv[4])
    assert input_dir.is_dir()
    assert output_dir.is_dir()
    # 插件会把物种文件拷贝到临时输入目录供 analyze mcscan 自动发现
    copied_beds = list(input_dir.glob("*.bed"))
    assert len(copied_beds) == 2
    assert logging.getLogger("genomelens_haiant_plugin").handlers == []
    os.environ.pop("GENOMELENS_PLUGIN_RUNTIME", None)
