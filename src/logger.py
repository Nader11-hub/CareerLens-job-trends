from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from src.config import settings

LOG_FORMAT = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str = "careerlens", log_level: str | None = None) -> logging.Logger:
    """Configure and return an application logger."""

    logger = logging.getLogger(name)
    if getattr(logger, "_careerlens_configured", False):
        return logger

    numeric_level = getattr(logging, (log_level or settings.log_level).upper(), logging.INFO)
    logger.setLevel(numeric_level)
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    settings.logs_path.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        settings.logs_path / settings.log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger._careerlens_configured = True  # type: ignore[attr-defined]
    return logger


logger = setup_logger()
