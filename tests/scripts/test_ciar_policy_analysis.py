"""Tests for CIAR policy artifact aggregation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_EXPERIMENTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "experiments"
sys.path.insert(0, str(_EXPERIMENTS_DIR))

from analyze_ciar_policy_runs import aggregate_runs, render_markdown  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def make_run(
    tmp_path: Path,
    *,
    run_id: str,
    promotion_policy: str,
    contradiction_policy: str,
) -> Path:
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "summary.md").write_text("# Summary\n", encoding="utf-8")
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": run_id,
            "completed_at": "2026-05-20T00:00:00+00:00",
            "model": "test-model",
            "runtime": {
                "promotion_policy_mode": promotion_policy,
                "contradiction_policy_mode": contradiction_policy,
            },
            "provider_health": {"status": "skipped"},
        },
    )
    write_json(
        run_dir / "promotion_results.json",
        {
            "small_talk": {
                "segments_promoted": 0,
                "facts_extracted": 0,
                "facts_promoted": 0,
                "facts_filtered": 0,
                "facts_review_only": 0,
                "facts_suppressed": 0,
            },
            "segment_mismatch": {
                "segments_promoted": 1,
                "facts_extracted": 2,
                "facts_promoted": 1,
                "facts_filtered": 0,
                "facts_review_only": 1,
                "facts_suppressed": 0,
            },
            "contradiction_update": {
                "segments_promoted": 1,
                "facts_extracted": 2,
                "facts_promoted": 1,
                "facts_filtered": 0,
                "facts_review_only": 0,
                "facts_suppressed": 1,
            },
        },
    )
    write_json(
        run_dir / "alternative_scores.json",
        [
            {
                "scenario_id": "segment_mismatch",
                "content": "Urgent container temperature excursion.",
                "raw_fact_ciar": 0.9,
                "stored_ciar": 0.9,
            },
            {
                "scenario_id": "contradiction_update",
                "content": "The shipment is rerouted to Los Angeles.",
                "raw_fact_ciar": 0.8,
                "stored_ciar": 0.8,
            },
        ],
    )
    write_jsonl(
        run_dir / "events.jsonl",
        [
            {
                "event_type": "fact_review_only",
                "session_id": f"{run_id}__segment_mismatch",
                "data": {"content": "The user thanked the assistant."},
            },
            {
                "event_type": "fact_suppressed",
                "session_id": f"{run_id}__contradiction_update",
                "data": {"content": "The shipment was scheduled for Oakland."},
            },
        ],
    )
    return run_dir


def test_aggregate_runs_groups_by_policy_configuration(tmp_path: Path) -> None:
    run_dir = make_run(
        tmp_path,
        run_id="ciar-exp-live-default-hybrid-gate-suppress-20260520-01",
        promotion_policy="hybrid_gate",
        contradiction_policy="suppress_superseded",
    )

    report = aggregate_runs([run_dir])

    assert report["run_count"] == 1
    assert report["artifact_gaps"] == []
    config = report["by_config"]["hybrid_gate+suppress_superseded"]
    assert config["small_talk"]["facts_promoted"] == 0
    assert config["segment_mismatch"]["facts_review_only"] == 1
    assert config["contradiction_update"]["facts_suppressed"] == 1
    assert (
        report["recommendation_inputs"]["hybrid_gate+suppress_superseded"][
            "contradiction_suppressed"
        ]
        == 1
    )


def test_render_markdown_includes_recommendation_table(tmp_path: Path) -> None:
    run_dir = make_run(
        tmp_path,
        run_id="ciar-exp-live-default-fact-gate-off-20260520-01",
        promotion_policy="fact_gate",
        contradiction_policy="off",
    )

    markdown = render_markdown(aggregate_runs([run_dir]))

    assert "# CIAR Default Policy Analysis" in markdown
    assert "`fact_gate+off`" in markdown
    assert "Small Talk Promoted" in markdown
