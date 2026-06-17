import logging
import shutil
from pathlib import Path

from jcvi_genomelens.runtime.logging_utils import close_engine_logging, setup_engine_logging


def _file_handler(logger: logging.Logger) -> logging.FileHandler:
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler
    raise AssertionError("file handler not found")


def test_setup_engine_logging_closes_previous_file_handler(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    logger = setup_engine_logging(first_dir / "run.log")
    first_handler = _file_handler(logger)

    setup_engine_logging(tmp_path / "second" / "run.log")

    assert first_handler.stream is None
    shutil.rmtree(first_dir)
    close_engine_logging()


def test_close_engine_logging_releases_log_directory(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    logger = setup_engine_logging(log_dir / "run.log")
    logger.info("write before closing")

    close_engine_logging()

    assert logger.handlers == []
    shutil.rmtree(log_dir)
    assert not log_dir.exists()
