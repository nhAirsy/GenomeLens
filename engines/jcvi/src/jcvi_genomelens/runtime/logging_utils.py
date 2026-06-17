"""engine(引擎) 日志设置"""

# region import
from __future__ import annotations

import logging
from pathlib import Path

# endregion


LOGGER_NAME = "jcvi_genomelens"


def _close_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.flush()
        finally:
            handler.close()


def close_engine_logging() -> None:
    """Flush and close JCVI engine logging handlers."""

    _close_handlers(logging.getLogger(LOGGER_NAME))


def setup_engine_logging(path: str | Path) -> logging.Logger:
    """创建写出 UTF-8 日志的 engine logger(引擎日志器)"""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # engine 统一使用固定 logger 名称，方便 shell 层按单文件收集运行日志。
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    # 同进程重复运行时先清空旧 handler，避免日志重复写入。
    _close_handlers(logger)
    handler = logging.FileHandler(target, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger
