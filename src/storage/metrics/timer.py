"""
Context manager to time and automatically record operations.
"""

import time
from typing import Any

from .collector import MetricsCollector


class OperationTimer:
    """
    Context manager to time and automatically record operations.

    Usage:
        async with OperationTimer(metrics, 'store', metadata={'has_id': True}):
            # ... perform operation ...
            pass
    """

    def __init__(
        self, collector: MetricsCollector, operation: str, metadata: dict[str, Any] | None = None
    ):
        self.collector = collector
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time: float | None = None
        self.success = True

    def start(self) -> "OperationTimer":
        """Start the timer manually."""
        self.start_time = time.perf_counter()
        return self

    async def stop(self, success: bool = True) -> float:
        """Stop the timer and record the operation."""
        if not self.collector.enabled:
            return 0.0

        if self.start_time is None:
            return 0.0

        duration_ms = (time.perf_counter() - self.start_time) * 1000

        await self.collector.record_operation(self.operation, duration_ms, success, self.metadata)
        return duration_ms

    async def __aenter__(self) -> "OperationTimer":
        return self.start()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        success = (exc_type is None) and self.success
        await self.stop(success)

        if not success and self.collector.track_errors and exc_val:
            await self.collector.record_error(type(exc_val).__name__, self.operation, str(exc_val))

        return False  # Don't suppress exceptions
