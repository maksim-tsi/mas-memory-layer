"""Tests for Phoenix span export helper."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_DEBUG_DIR = Path(__file__).parent.parent.parent / "scripts" / "debug"
sys.path.insert(0, str(_DEBUG_DIR))

import export_phoenix_spans as exporter  # noqa: E402


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_fetch_project_spans_follows_pagination(mocker) -> None:
    payloads = [
        {
            "data": [
                {
                    "name": "yaam.ciar.score",
                    "span_kind": "TOOL",
                    "status_code": "OK",
                }
            ],
            "next_cursor": "abc",
        },
        {
            "data": [
                {
                    "name": "yaam.llm.fact_extract",
                    "span_kind": "LLM",
                    "status_code": "ERROR",
                }
            ]
        },
    ]
    opened_urls: list[str] = []

    def fake_urlopen(request, timeout: float):
        opened_urls.append(request.full_url)
        return FakeResponse(payloads.pop(0))

    mocker.patch.object(exporter, "urlopen", side_effect=fake_urlopen)

    result = exporter.fetch_project_spans(
        base_url="http://phoenix.local/",
        project="project one",
        limit=100,
        timeout=5,
    )

    assert result["span_count"] == 2
    assert "project%20one" in opened_urls[0]
    assert "cursor=abc" in opened_urls[1]


def test_summarize_project_counts_names_kinds_statuses() -> None:
    export = {
        "project": "ciar-project",
        "spans": [
            {
                "name": "yaam.ciar.score",
                "span_kind": "TOOL",
                "status_code": "OK",
            },
            {
                "name": "yaam.llm.fact_extract",
                "attributes": {"openinference.span.kind": "LLM"},
                "status": {"code": "ERROR"},
            },
            {
                "span_name": "other",
                "kind": "CHAIN",
                "status_code": "OK",
            },
        ],
    }

    summary = exporter.summarize_project(export)

    assert summary["span_count"] == 3
    assert summary["ciar_score_span_count"] == 1
    assert summary["fact_extract_span_count"] == 1
    assert summary["error_count"] == 1
    assert summary["span_counts_by_kind"] == {"CHAIN": 1, "LLM": 1, "TOOL": 1}


def test_main_writes_project_exports_and_summary(tmp_path: Path, mocker) -> None:
    def fake_fetch_project_spans(**kwargs):
        project = kwargs["project"]
        return {
            "project": project,
            "exported_at": "2026-05-23T00:00:00+00:00",
            "span_count": 1,
            "pages": [{"data": []}],
            "spans": [
                {
                    "name": "yaam.ciar.score",
                    "span_kind": "TOOL",
                    "status_code": "OK",
                }
            ],
        }

    mocker.patch.object(exporter, "fetch_project_spans", side_effect=fake_fetch_project_spans)
    output_dir = tmp_path / "spans"
    summary_output = tmp_path / "summary.json"

    status = exporter.main(
        [
            "--base-url",
            "http://phoenix.local",
            "--output-dir",
            str(output_dir),
            "--summary-output",
            str(summary_output),
            "--project",
            "project/unsafe",
            "--project",
            "project-two",
        ]
    )

    assert status == 0
    assert (output_dir / "project_unsafe.json").exists()
    assert (output_dir / "project-two.json").exists()
    summary = json.loads(summary_output.read_text(encoding="utf-8"))
    assert summary["project_count"] == 2
    assert summary["total_span_count"] == 2


def test_main_rejects_invalid_limit(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="--limit must be between 1 and 1000"):
        exporter.main(
            [
                "--base-url",
                "http://phoenix.local",
                "--output-dir",
                str(tmp_path),
                "--summary-output",
                str(tmp_path / "summary.json"),
                "--project",
                "project",
                "--limit",
                "1001",
            ]
        )
