#!/usr/bin/env python3
"""Export Phoenix spans for one or more projects without reading secrets."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def project_slug(project: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in project)


def build_url(
    *,
    base_url: str,
    project: str,
    limit: int,
    cursor: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> str:
    query: dict[str, str | int] = {"limit": limit}
    if cursor:
        query["cursor"] = cursor
    if start_time:
        query["start_time"] = start_time
    if end_time:
        query["end_time"] = end_time
    encoded_project = quote(project, safe="")
    return (
        f"{base_url.rstrip('/')}/v1/projects/{encoded_project}/spans?"
        f"{urlencode(query)}"
    )


def fetch_json(url: str, *, timeout: float) -> dict[str, Any] | list[Any]:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_spans_and_cursor(payload: dict[str, Any] | list[Any]) -> tuple[list[dict[str, Any]], str | None]:
    if isinstance(payload, list):
        spans = [span for span in payload if isinstance(span, dict)]
        return spans, None
    if not isinstance(payload, dict):
        return [], None

    raw_spans = (
        payload.get("data")
        or payload.get("spans")
        or payload.get("items")
        or payload.get("results")
        or []
    )
    spans = [span for span in raw_spans if isinstance(span, dict)]
    cursor = (
        payload.get("next_cursor")
        or payload.get("next")
        or payload.get("cursor")
        or (payload.get("pagination") or {}).get("next_cursor")
    )
    return spans, str(cursor) if cursor else None


def fetch_project_spans(
    *,
    base_url: str,
    project: str,
    limit: int,
    timeout: float,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict[str, Any]:
    pages: list[dict[str, Any] | list[Any]] = []
    spans: list[dict[str, Any]] = []
    cursor: str | None = None

    while True:
        payload = fetch_json(
            build_url(
                base_url=base_url,
                project=project,
                limit=limit,
                cursor=cursor,
                start_time=start_time,
                end_time=end_time,
            ),
            timeout=timeout,
        )
        pages.append(payload)
        page_spans, cursor = extract_spans_and_cursor(payload)
        spans.extend(page_spans)
        if not cursor:
            break

    return {
        "project": project,
        "exported_at": utc_now(),
        "span_count": len(spans),
        "pages": pages,
        "spans": spans,
    }


def nested_get(value: dict[str, Any], keys: tuple[str, ...]) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def span_attributes(span: dict[str, Any]) -> dict[str, Any]:
    attrs = span.get("attributes") or span.get("span_attributes") or {}
    return attrs if isinstance(attrs, dict) else {}


def span_name(span: dict[str, Any]) -> str:
    attrs = span_attributes(span)
    return str(
        span.get("name")
        or span.get("span_name")
        or nested_get(span, ("context", "span_name"))
        or attrs.get("span.name")
        or "unknown"
    )


def span_kind(span: dict[str, Any]) -> str:
    attrs = span_attributes(span)
    return str(
        span.get("span_kind")
        or span.get("kind")
        or attrs.get("openinference.span.kind")
        or "unknown"
    )


def span_status(span: dict[str, Any]) -> str:
    raw_status = span.get("status_code") or span.get("status") or nested_get(span, ("status", "code"))
    if isinstance(raw_status, dict):
        raw_status = raw_status.get("code")
    return str(raw_status or "unknown")


def summarize_project(export: dict[str, Any]) -> dict[str, Any]:
    spans = [span for span in export.get("spans", []) if isinstance(span, dict)]
    names = Counter(span_name(span) for span in spans)
    kinds = Counter(span_kind(span) for span in spans)
    statuses = Counter(span_status(span) for span in spans)
    error_count = sum(
        count for status, count in statuses.items() if status.upper() == "ERROR"
    )
    return {
        "project": export["project"],
        "span_count": len(spans),
        "span_counts_by_name": dict(sorted(names.items())),
        "span_counts_by_kind": dict(sorted(kinds.items())),
        "span_counts_by_status": dict(sorted(statuses.items())),
        "error_count": error_count,
        "ciar_score_span_count": names.get("yaam.ciar.score", 0),
        "fact_extract_span_count": names.get("yaam.llm.fact_extract", 0),
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Phoenix spans for CIAR projects.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--project", action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--start-time")
    parser.add_argument("--end-time")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.limit <= 0 or args.limit > 1000:
        raise SystemExit("--limit must be between 1 and 1000")

    exports = []
    summaries = []
    for project in args.project:
        export = fetch_project_spans(
            base_url=args.base_url,
            project=project,
            limit=args.limit,
            timeout=args.timeout,
            start_time=args.start_time,
            end_time=args.end_time,
        )
        exports.append(export)
        summaries.append(summarize_project(export))
        write_json(args.output_dir / f"{project_slug(project)}.json", export)

    summary = {
        "base_url": args.base_url.rstrip("/"),
        "exported_at": utc_now(),
        "project_count": len(args.project),
        "total_span_count": sum(item["span_count"] for item in summaries),
        "projects": summaries,
    }
    write_json(args.summary_output, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
