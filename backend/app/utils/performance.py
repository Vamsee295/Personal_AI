"""
utils/performance.py - Monitors subsystem performance natively.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("performance")

REPORT_FILE = Path(__file__).resolve().parent.parent.parent / "logs" / "performance_report.json"

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "planning_times_ms": [],
            "tool_execution_times_ms": [],
            "browser_response_times_ms": [],
            "llm_response_times_ms": []
        }

    def log_metric(self, category: str, duration_ms: float) -> None:
        """Log a specific metric category."""
        if category in self.metrics:
            self.metrics[category].append(duration_ms)
            # Keep array sizes manageable
            if len(self.metrics[category]) > 1000:
                self.metrics[category].pop(0)

    def generate_report(self) -> None:
        """Write out the aggregated averages to a JSON file."""
        report = {"timestamp": datetime.utcnow().isoformat() + "Z", "averages_ms": {}}
        
        for k, v in self.metrics.items():
            if v:
                report["averages_ms"][k] = sum(v) / len(v)
            else:
                report["averages_ms"][k] = 0.0

        try:
            REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(REPORT_FILE, "w") as f:
                json.dump(report, f, indent=4)
            logger.info("Performance report generated.")
        except Exception as e:
            logger.error(f"Failed to save performance report: {e}")

performance_monitor = PerformanceMonitor()
