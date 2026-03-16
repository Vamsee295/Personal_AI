"""
utils/logger.py – Structured, coloured logging for the entire backend.
"""

from __future__ import annotations
import logging
import sys
from pathlib import Path
from app.config import settings


_FMT = "%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name."""
    logger = logging.getLogger(name)

    if logger.handlers:            # already configured
        return logger

    logger.setLevel(settings.LOG_LEVEL)

    # ── Console handler ───────────────────────────────────────────
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter(_FMT, datefmt=_DATE_FMT))
    logger.addHandler(ch)

    # ── File handler (optional) ───────────────────────────────────
    log_dir = Path(settings.LOG_DIR)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "backend.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter(_FMT, datefmt=_DATE_FMT))
        logger.addHandler(fh)
    except Exception:  # don't crash if log dir is read-only
        pass

    return logger
