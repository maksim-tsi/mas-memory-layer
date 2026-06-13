"""
Calculate statistical aggregations from raw metrics.
"""

import math
from datetime import UTC
from typing import Any


class MetricsAggregator:
    """
    Calculate statistical aggregations from raw metrics.
    """

    @staticmethod
    def calculate_percentiles(
        values: list[float], percentiles: list[int] | None = None
    ) -> dict[str, float]:
        """
        Calculate percentiles from list of values.

        Returns:
            {'p50': 10.2, 'p95': 35.8, 'p99': 89.1}
        """
        if percentiles is None:
            percentiles = [50, 95, 99]
        if not values:
            return {f"p{p}": 0.0 for p in percentiles}

        sorted_values = sorted(values)
        result = {}

        for percentile in percentiles:
            # Calculate index using linear interpolation
            index = (percentile / 100.0) * (len(sorted_values) - 1)
            if index.is_integer():
                result[f"p{percentile}"] = sorted_values[int(index)]
            else:
                lower_index = math.floor(index)
                upper_index = math.ceil(index)
                fraction = index - lower_index
                result[f"p{percentile}"] = (
                    sorted_values[lower_index] * (1 - fraction)
                    + sorted_values[upper_index] * fraction
                )

        return result

    @staticmethod
    def calculate_rates(
        operations: list[dict[str, Any]], window_seconds: int = 60
    ) -> dict[str, float]:
        """
        Calculate ops/sec and bytes/sec in time window.

        Returns:
            {'ops_per_sec': 25.0, 'bytes_per_sec': 12500}
        """
        if not operations:
            return {"ops_per_sec": 0.0, "bytes_per_sec": 0.0}

        # Count operations and bytes in the window
        from datetime import datetime, timedelta

        now = datetime.now(UTC)
        window_start = now - timedelta(seconds=window_seconds)

        count = 0
        total_bytes = 0
        for op in operations:
            op_time = datetime.fromisoformat(op["timestamp"].replace("Z", "+00:00"))
            if op_time >= window_start:
                count += 1
                # Sum bytes from metadata if available
                if "metadata" in op and "bytes" in op["metadata"]:
                    total_bytes += op["metadata"]["bytes"]

        ops_per_sec = count / window_seconds if window_seconds > 0 else 0
        bytes_per_sec = total_bytes / window_seconds if window_seconds > 0 else 0

        return {"ops_per_sec": round(ops_per_sec, 2), "bytes_per_sec": round(bytes_per_sec, 2)}

    @staticmethod
    def calculate_latency_stats(
        durations: list[float], percentiles: list[int] | None = None
    ) -> dict[str, Any]:
        """
        Calculate comprehensive latency statistics.

        Returns:
            {
                'min': 2.3,
                'max': 145.2,
                'avg': 12.5,
                'p50': 10.2,
                'p95': 35.8,
                'p99': 89.1
            }
        """
        if percentiles is None:
            percentiles = [50, 95, 99]
        if not durations:
            return {"min": 0.0, "max": 0.0, "avg": 0.0, **{f"p{p}": 0.0 for p in percentiles}}

        min_val = min(durations)
        max_val = max(durations)
        avg_val = sum(durations) / len(durations)
        percentile_vals = MetricsAggregator.calculate_percentiles(durations, percentiles)

        return {
            "min": round(min_val, 2),
            "max": round(max_val, 2),
            "avg": round(avg_val, 2),
            **{f"p{p}": round(percentile_vals[f"p{p}"], 2) for p in percentiles},
        }
