"""CLI(命令行接口) 与 workflow(工作流) 运行的日志初始化"""

# region import
from __future__ import annotations

import logging
import sys
from pathlib import Path

# endregion


LOGGER_NAME = "genomelens"


def _close_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.flush()
        finally:
            handler.close()


def close_logging() -> None:
    """Flush and close GenomeLens logging handlers."""

    _close_handlers(logging.getLogger(LOGGER_NAME))


def setup_logging(log_file: str | Path | None = None, *, level: str = "INFO") -> logging.Logger:
    """配置 root logging(根日志)，可选写出 UTF-8 日志文件"""

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    # 反复初始化时先清空旧 handler，避免同一条日志被重复输出。
    _close_handlers(logger)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(formatter)
    logger.addHandler(stream)
    if log_file is not None:
        path = Path(log_file)
        # 文件日志目录在这里兜底创建，调用方不必额外关心父目录是否存在。
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger
