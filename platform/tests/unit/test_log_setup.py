import logging
import shutil
from pathlib import Path

from genomelens.data.logging.log_setup import close_logging, setup_logging


def _file_handler(logger: logging.Logger) -> logging.FileHandler:
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler
    raise AssertionError("file handler not found")


def test_setup_logging_closes_previous_file_handler(tmp_path: Path) -> None:
    first_dir = tmp_path / "first" / "logs"
    logger = setup_logging(first_dir / "run.log")
    first_handler = _file_handler(logger)

    setup_logging(tmp_path / "second" / "logs" / "run.log")

    assert first_handler.stream is None
    shutil.rmtree(first_dir)
    close_logging()


def test_close_logging_releases_log_directory(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    logger = setup_logging(log_dir / "run.log")
    logger.info("write before closing")

    close_logging()

    assert logger.handlers == []
    shutil.rmtree(log_dir)
    assert not log_dir.exists()
