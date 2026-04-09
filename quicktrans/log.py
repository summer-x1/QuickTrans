"""Logging setup with rotation."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from types import SimpleNamespace

LOG_DIR: str = os.path.expanduser("~/.config/quicktrans")
LOG_FILE: str = os.path.join(LOG_DIR, "quicktrans.log")


def setup_logging(config: SimpleNamespace) -> logging.Logger:
    """Set up a rotating file logger."""
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("quicktrans")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=config.log_max_bytes,
            backupCount=config.log_backup_count,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
