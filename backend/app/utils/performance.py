import time
import logging
from typing import Dict, List

logger = logging.getLogger("performance_monitor")

class PerformanceMonitor:
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {
            "planning_times_ms": [],
            "tool_execution_times_ms": [],
            "llm_inference_times_ms": [],
            "browser_execution_times_ms": [],
            "desktop_action_times_ms": [],
            "websocket_latencies_ms": []
        }
        self.limit = 100

    def log_metric(self, metric_name: str, value_ms: float):
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        self.metrics[metric_name].append(value_ms)

        if len(self.metrics[metric_name]) > self.limit:
            self.metrics[metric_name] = self.metrics[metric_name][-self.limit:]

    def get_averages(self) -> Dict[str, float]:
        averages = {}
        for k, v in self.metrics.items():
            if v:
                averages[k] = sum(v) / len(v)
            else:
                averages[k] = 0.0
        return averages

    def generate_report(self):
        avg = self.get_averages()
        report = "--- Performance Report ---\n"
        for k, v in avg.items():
            report += f"{k}: {v:.2f} ms\n"
        logger.info(report)
        return report

performance_monitor = PerformanceMonitor()
