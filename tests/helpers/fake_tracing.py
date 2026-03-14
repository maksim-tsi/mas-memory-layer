"""Shared fake tracing primitives for observability unit tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


class FakeSpan:
    """Minimal recording span used by unit tests."""

    def __init__(self, name: str, trace_id: int = 1, span_id: int = 1) -> None:
        self.name = name
        self.attributes: dict[str, object] = {}
        self.status = None
        self._context = SimpleNamespace(trace_id=trace_id, span_id=span_id, is_valid=True)

    def is_recording(self) -> bool:
        return True

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def get_span_context(self) -> SimpleNamespace:
        return self._context

    def set_status(self, status: object) -> None:
        self.status = status


class FakeSpanManager:
    """Context manager wrapper for FakeSpan."""

    def __init__(self, span: FakeSpan) -> None:
        self._span = span

    def __enter__(self) -> FakeSpan:
        return self._span

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False


class FakeTracer:
    """Create a new FakeSpan for each started span and record start order."""

    def __init__(self) -> None:
        self.started: list[dict[str, object]] = []
        self.spans: list[FakeSpan] = []

    def start_as_current_span(self, name: str, context: object | None = None) -> FakeSpanManager:
        span = FakeSpan(name=name, trace_id=len(self.spans) + 1, span_id=len(self.spans) + 1)
        self.spans.append(span)
        self.started.append({"name": name, "context": context, "span": span})
        return FakeSpanManager(span)
