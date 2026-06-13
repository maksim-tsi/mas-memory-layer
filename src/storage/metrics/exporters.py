"""
Export metrics in various formats.
"""

import json
from typing import Any


def export_metrics(metrics: dict[str, Any], format: str = "dict") -> dict[str, Any] | str:
    """
    Export metrics in specified format.

    Args:
        metrics: Metrics dictionary from MetricsCollector.get_metrics()
        format: 'dict', 'json', 'prometheus', 'csv', 'markdown'

    Returns:
        Metrics in requested format
    """
    if format == "dict":
        return metrics
    elif format == "json":
        return json.dumps(metrics, indent=2)
    elif format == "prometheus":
        return _to_prometheus(metrics)
    elif format == "csv":
        return _to_csv(metrics)
    elif format == "markdown":
        return _to_markdown(metrics)
    else:
        raise ValueError(f"Unsupported format: {format}")


def _to_prometheus(metrics: dict[str, Any]) -> str:
    """Convert metrics to Prometheus format."""
    lines = []
    lines.append("# HELP storage_operations_total Total storage operations")
    lines.append("# TYPE storage_operations_total counter")

    for operation, stats in metrics.get("operations", {}).items():
        if isinstance(stats, dict) and "total_count" in stats:
            lines.append(
                f'storage_operations_total{{operation="{operation}",status="total"}} {stats["total_count"]}'
            )
            lines.append(
                f'storage_operations_total{{operation="{operation}",status="success"}} {stats.get("success_count", 0)}'
            )
            lines.append(
                f'storage_operations_total{{operation="{operation}",status="error"}} {stats.get("error_count", 0)}'
            )

    lines.append("")
    lines.append("# HELP storage_operation_duration_milliseconds Operation duration")
    lines.append("# TYPE storage_operation_duration_milliseconds histogram")

    for operation, stats in metrics.get("operations", {}).items():
        if isinstance(stats, dict) and "latency_ms" in stats:
            latency = stats["latency_ms"]
            for percentile, value in latency.items():
                if percentile.startswith("p"):
                    # Convert percentile string like 'p50' to float 0.5
                    percentile_num = percentile[1:]
                    quantile = int(percentile_num) / 100.0 if percentile_num.isdigit() else 0.5
                    lines.append(
                        f'storage_operation_duration_milliseconds{{operation="{operation}",quantile="{quantile}"}} {value}'
                    )

    return "\n".join(lines)


def _to_csv(metrics: dict[str, Any]) -> str:
    """Convert metrics to CSV format."""
    lines = ["timestamp,operation,total_count,success_count,error_count,avg_latency_ms"]

    for operation, stats in metrics.get("operations", {}).items():
        if isinstance(stats, dict) and "total_count" in stats:
            avg_latency = (
                stats.get("latency_ms", {}).get("avg", 0)
                if isinstance(stats.get("latency_ms"), dict)
                else 0
            )
            lines.append(
                f"{metrics.get('timestamp', '')},{operation},{stats.get('total_count', 0)},{stats.get('success_count', 0)},{stats.get('error_count', 0)},{avg_latency}"
            )

    # Add errors section
    errors = metrics.get("errors", {})
    if errors and (errors.get("by_type") or errors.get("recent_errors")):
        lines.append("")  # Empty line separator
        lines.append("error_type,count")
        for error_type, count in errors.get("by_type", {}).items():
            lines.append(f"{error_type},{count}")

        if errors.get("recent_errors"):
            lines.append("")  # Empty line separator
            lines.append("recent_errors_timestamp,error_type,operation,message")
            for error in errors.get("recent_errors", [])[:10]:  # Last 10 errors
                timestamp = error.get("timestamp", "")
                error_type = error.get("type", "")
                operation = error.get("operation", "")
                message = error.get("message", "").replace(
                    ",", ";"
                )  # Replace commas to avoid CSV issues
                lines.append(f"{timestamp},{error_type},{operation},{message}")

    return "\n".join(lines)


def _to_markdown(metrics: dict[str, Any]) -> str:
    """Convert metrics to Markdown format."""
    lines = ["# Storage Adapter Metrics", ""]
    lines.append(f"**Timestamp**: {metrics.get('timestamp', 'N/A')}")
    lines.append(f"**Uptime**: {metrics.get('uptime_seconds', 0)}s")
    lines.append("")
    lines.append("## Operations")
    lines.append("| Operation | Total | Success Rate | Avg Latency (ms) | P95 Latency (ms) |")
    lines.append("|-----------|-------|--------------|------------------|------------------|")

    for operation, stats in metrics.get("operations", {}).items():
        if isinstance(stats, dict) and "total_count" in stats:
            success_rate = stats.get("success_rate", 0) * 100
            avg_latency = (
                stats.get("latency_ms", {}).get("avg", 0)
                if isinstance(stats.get("latency_ms"), dict)
                else 0
            )
            p95_latency = (
                stats.get("latency_ms", {}).get("p95", 0)
                if isinstance(stats.get("latency_ms"), dict)
                else 0
            )
            lines.append(
                f"| {operation} | {stats.get('total_count', 0)} | {success_rate:.2f}% | {avg_latency:.2f} | {p95_latency:.2f} |"
            )

    return "\n".join(lines)
