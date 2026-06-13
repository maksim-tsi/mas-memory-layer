"""
Thread-safe in-memory metrics storage with history limits.
"""

import asyncio
from collections import defaultdict, deque
from typing import Any


class MetricsStorage:
    """
    Thread-safe in-memory metrics storage with history limits.
    """

    def __init__(self, max_history: int = 1000, max_errors: int = 100):
        self.max_history = max_history
        self.max_errors = max_errors
        self._operations: defaultdict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=max_history)
        )
        self._counters: defaultdict[str, int] = defaultdict(int)
        self._errors: deque[dict[str, Any]] = deque(maxlen=max_errors)
        self._lock = asyncio.Lock()

    async def add_operation(self, operation: str, record: dict[str, Any]) -> None:
        """Add operation record with automatic history limiting."""
        async with self._lock:
            self._operations[operation].append(record)

    async def increment_counter(self, key: str, amount: int = 1) -> None:
        """Increment a counter."""
        async with self._lock:
            self._counters[key] += amount

    async def add_error(self, error_record: dict[str, Any]) -> None:
        """Add error record."""
        async with self._lock:
            self._errors.append(error_record)

    async def get_all(self) -> dict[str, Any]:
        """Get all stored metrics."""
        async with self._lock:
            return {
                "operations": {k: list(v) for k, v in self._operations.items()},
                "counters": dict(self._counters),
                "errors": list(self._errors),
            }

    async def reset(self) -> None:
        """Clear all metrics."""
        async with self._lock:
            self._operations.clear()
            self._counters.clear()
            self._errors.clear()
