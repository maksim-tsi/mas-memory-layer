"""Unit tests for the 12-hour memory-layer audit script."""

# ruff: noqa: I001

from __future__ import annotations

import sys
from pathlib import Path


_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from audit_memory_layer_12h import (  # noqa: E402
    build_report,
    extract_error_lines,
    mask_url,
    parse_memory_endpoint_counts,
    parse_memory_http_statuses,
)


def test_parse_memory_endpoint_counts_orders_descending() -> None:
    log_text = "\n".join(
        [
            'INFO: "POST /v2/memory/l2/facts HTTP/1.1" 201 Created',
            'INFO: "POST /v2/memory/l2/facts HTTP/1.1" 201 Created',
            'INFO: "POST /v2/memory/l4/finalize HTTP/1.1" 201 Created',
        ]
    )
    counts = parse_memory_endpoint_counts(log_text)
    assert next(iter(counts.keys())) == "/v2/memory/l2/facts"
    assert counts["/v2/memory/l2/facts"] == 2
    assert counts["/v2/memory/l4/finalize"] == 1


def test_parse_memory_http_statuses_groups_by_endpoint() -> None:
    log_text = "\n".join(
        [
            'INFO: 1.2.3.4 - "POST /v2/memory/l2/facts HTTP/1.1" 201 Created',
            'INFO: 1.2.3.4 - "POST /v2/memory/l2/facts HTTP/1.1" 500 Internal Server Error',
            'INFO: 1.2.3.4 - "POST /v2/memory/l4/finalize HTTP/1.1" 201 Created',
        ]
    )
    statuses = parse_memory_http_statuses(log_text)
    assert statuses["/v2/memory/l2/facts"]["201"] == 1
    assert statuses["/v2/memory/l2/facts"]["500"] == 1
    assert statuses["/v2/memory/l4/finalize"]["201"] == 1


def test_extract_error_lines_filters_expected_patterns() -> None:
    log_text = "\n".join(
        [
            "INFO: started",
            "Provider 'gemini' failed:",
            "ERROR: connection timeout while writing fact",
            "INFO: completed",
        ]
    )
    errors = extract_error_lines(log_text)
    assert len(errors) == 2
    assert "failed" in errors[0].lower()
    assert "timeout" in errors[1].lower()


def test_mask_url_hides_password() -> None:
    raw = "postgresql://user:secret@db.example:5432/mas"
    assert mask_url(raw) == "postgresql://user:***@db.example:5432/mas"


def test_build_report_contains_key_sections() -> None:
    report = build_report(
        generated_at="2026-04-17T10:00:00+00:00",
        since="12h",
        container="mas-memory-layer-mas-agent-1",
        health={"raw": "running restart=0 oom=false", "ok": True},
        envs={
            "POSTGRES_URL": "postgresql://user:secret@host:5432/db",
            "QDRANT_URL": "http://host:6333",
            "NEO4J_URI": "bolt://host:7687",
        },
        endpoint_counts={"/v2/memory/l2/facts": 10},
        endpoint_statuses={"/v2/memory/l2/facts": {"201": 10}},
        error_lines=["Provider 'gemini' failed:"],
        pg_stats={"ok": True, "candidates": ["l2_facts"], "counts": []},
        q_stats={"ok": True, "collection_count": 1, "collections": []},
        n_stats={"ok": False, "error": "auth failed"},
    )
    assert "YAAM Memory Layer Audit" in report
    assert "Memory Endpoint Request Volume" in report
    assert "PostgreSQL (L1/L2)" in report
    assert "Qdrant (L3 Vectors)" in report
    assert "Neo4j (L3 Graph)" in report
