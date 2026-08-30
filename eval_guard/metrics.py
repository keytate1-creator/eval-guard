"""
Evaluation metrics, rubric scoring, and latency benchmark utilities.
"""

from __future__ import annotations

import math
from typing import List, Dict, Any
from eval_guard.core import EvaluationReport


class BenchmarkTracker:
    """Tracks latency metrics and throughput across evaluation workloads."""

    def __init__(self) -> None:
        self.latencies_us: List[float] = []
        self.total_samples: int = 0
        self.passed_samples: int = 0

    def record(self, report: EvaluationReport) -> None:
        self.latencies_us.append(report.latency_us)
        self.total_samples += 1
        if report.passed:
            self.passed_samples += 1

    def summary(self) -> Dict[str, Any]:
        if not self.latencies_us:
            return {
                "total_samples": 0,
                "pass_rate": 0.0,
                "avg_latency_us": 0.0,
                "p95_latency_us": 0.0,
                "p99_latency_us": 0.0,
            }

        sorted_lat = sorted(self.latencies_us)
        count = len(sorted_lat)

        def percentile(p: float) -> float:
            idx = int(math.ceil((p / 100.0) * count)) - 1
            return sorted_lat[max(0, min(idx, count - 1))]

        return {
            "total_samples": self.total_samples,
            "pass_rate": round(self.passed_samples / self.total_samples, 4),
            "avg_latency_us": round(sum(sorted_lat) / count, 2),
            "p50_latency_us": round(percentile(50.0), 2),
            "p95_latency_us": round(percentile(95.0), 2),
            "p99_latency_us": round(percentile(99.0), 2),
        }
