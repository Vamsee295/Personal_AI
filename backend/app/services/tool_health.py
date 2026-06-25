"""
services/tool_health.py – Tracks the status and availability of all major sub-systems.
"""

from __future__ import annotations
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger("tool_health")

class ToolHealthManager:
    def __init__(self):
        self.subsystems = {
            "browser": {"status": "unknown", "last_error": None, "last_success": None, "available": False},
            "voice": {"status": "unknown", "last_error": None, "last_success": None, "available": False},
            "memory": {"status": "unknown", "last_error": None, "last_success": None, "available": False},
            "ollama": {"status": "unknown", "last_error": None, "last_success": None, "available": False},
            "database": {"status": "unknown", "last_error": None, "last_success": None, "available": False},
        }

    def report_success(self, subsystem: str) -> None:
        """Mark a subsystem as healthy and available."""
        if subsystem in self.subsystems:
            self.subsystems[subsystem]["status"] = "healthy"
            self.subsystems[subsystem]["available"] = True
            self.subsystems[subsystem]["last_success"] = datetime.utcnow().isoformat()
            self.subsystems[subsystem]["last_error"] = None

    def report_error(self, subsystem: str, error_msg: str) -> None:
        """Mark a subsystem as degraded or unavailable."""
        if subsystem in self.subsystems:
            self.subsystems[subsystem]["status"] = "degraded"
            self.subsystems[subsystem]["available"] = False
            self.subsystems[subsystem]["last_error"] = f"{datetime.utcnow().isoformat()}: {error_msg}"
            logger.error(f"Health Check Failed - {subsystem.upper()}: {error_msg}")

    def get_health(self) -> Dict[str, Any]:
        """Get the current state of all subsystems."""
        return self.subsystems

    def is_available(self, subsystem: str) -> bool:
        """Check if a specific tool/subsystem is safe to use."""
        return self.subsystems.get(subsystem, {}).get("available", False)

tool_health = ToolHealthManager()
