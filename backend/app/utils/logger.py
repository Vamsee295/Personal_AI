"""
utils/logger.py – Structured, coloured logging for the entire backend.
"""

from __future__ import annotations
import logging
import sys
from pathlib import Path
from app.config import settings


import json
import datetime

_FMT = "%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

class StructuredJSONFormatter(logging.Formatter):
    """Format logs as structured JSON."""
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "module": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Attach any extra kwargs (like task_id, tool, duration) if provided
        if hasattr(record, "task_id"):
            log_record["task_id"] = record.task_id
        if hasattr(record, "tool"):
            log_record["tool"] = record.tool
        if hasattr(record, "duration_ms"):
            log_record["duration_ms"] = record.duration_ms

        return json.dumps(log_record)

def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name."""
    logger = logging.getLogger(name)

    if logger.handlers:            # already configured
        return logger

    logger.setLevel(settings.LOG_LEVEL)

    # ── Console handler (Standard Text) ───────────────────────────
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter(_FMT, datefmt=_DATE_FMT))
    logger.addHandler(ch)

    # ── File handler (Structured JSON) ────────────────────────────
    log_dir = Path(settings.LOG_DIR)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "backend.jsonl", encoding="utf-8")
        fh.setFormatter(StructuredJSONFormatter())
        logger.addHandler(fh)
    except Exception:  # don't crash if log dir is read-only
        pass

    return logger
