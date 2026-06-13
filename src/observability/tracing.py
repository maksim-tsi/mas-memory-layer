"""Shared OpenTelemetry/Phoenix tracing helpers for YAAM policy-layer spans."""

from __future__ import annotations

import json
from contextlib import nullcontext
from typing import Any

OPENINFERENCE_SPAN_KIND = "openinference.span.kind"


def _get_tracer(tracer_name: str) -> Any | None:
    """Return a tracer when OpenTelemetry is available."""
    try:
        from opentelemetry import trace
    except Exception:  # pragma: no cover - optional dependency
        return None
    return trace.get_tracer(tracer_name)


class _SpanManager:
    """Wrap a tracer span manager to attach initial attributes on entry."""

    def __init__(self, manager: Any, attributes: dict[str, Any]) -> None:
        self._manager = manager
        self._attributes = attributes

    def __enter__(self) -> Any:
        span = self._manager.__enter__()
        set_span_attributes(span, self._attributes)
        return span

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return bool(self._manager.__exit__(exc_type, exc, tb))


def start_span(
    tracer_name: str,
    span_name: str,
    kind: str,
    attributes: dict[str, Any] | None = None,
) -> Any:
    """Start a current span when tracing is enabled, else return a no-op manager."""
    tracer = _get_tracer(tracer_name)
    if not tracer or not hasattr(tracer, "start_as_current_span"):
        return nullcontext(None)

    initial_attributes = {OPENINFERENCE_SPAN_KIND: kind}
    if attributes:
        initial_attributes.update(attributes)
    return _SpanManager(tracer.start_as_current_span(span_name), initial_attributes)


def set_span_attributes(span: Any, attributes: dict[str, Any]) -> None:
    """Attach normalized attributes to a recording span."""
    if not span or not hasattr(span, "is_recording") or not span.is_recording():
        return

    for key, value in attributes.items():
        if value is None:
            continue
        if isinstance(value, str | bool | int | float):
            span.set_attribute(key, value)
            continue
        try:
            span.set_attribute(key, json.dumps(value, ensure_ascii=True))
        except TypeError:
            span.set_attribute(key, str(value))


def set_span_error(span: Any, exc: Exception) -> None:
    """Record error details on the active span."""
    set_span_attributes(
        span,
        {
            "error.type": type(exc).__name__,
            "error.message": str(exc),
        },
    )
    try:
        from opentelemetry.trace import Status, StatusCode
    except Exception:  # pragma: no cover - optional dependency
        return
    if span and hasattr(span, "set_status"):
        span.set_status(Status(StatusCode.ERROR, str(exc)))


def current_trace_metadata(span: Any) -> dict[str, str]:
    """Return current span identifiers when they are available."""
    if not span or not hasattr(span, "get_span_context"):
        return {}
    try:
        span_context = span.get_span_context()
    except Exception:  # pragma: no cover - defensive fallback
        return {}
    if not getattr(span_context, "is_valid", False):
        return {}
    return {
        "yaam_trace_id": f"{span_context.trace_id:032x}",
        "yaam_span_id": f"{span_context.span_id:016x}",
    }
