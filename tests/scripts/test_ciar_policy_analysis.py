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
    operational_classification: dict[str, object] | None = None,
) -> Path:
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "summary.md").write_text("# Summary\n", encoding="utf-8")
    suppression_enabled = contradiction_policy == "suppress_superseded"
    contradiction_promoted = 1 if suppression_enabled else 2
    contradiction_suppressed = 1 if suppression_enabled else 0
    repeated_promoted = 1 if suppression_enabled else 3
    repeated_suppressed = 2 if suppression_enabled else 0
    manifest = {
        "run_id": run_id,
        "completed_at": "2026-05-20T00:00:00+00:00",
        "dry_run": False,
        "model": "test-model",
        "runtime": {
            "promotion_policy_mode": promotion_policy,
            "contradiction_policy_mode": contradiction_policy,
        },
        "phoenix_ui_check": {"ok": True},
        "provider_health": {"status": "skipped", "reason": "checked separately"},
        "cleanup": {"session": {"l1_deleted": True, "l2_deleted": False}},
    }
    if operational_classification is not None:
        manifest["operational_classification"] = operational_classification
    write_json(
        run_dir / "run_manifest.json",
        manifest,
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
            "assistant_acknowledgement_noise": {
                "segments_promoted": 0,
                "facts_extracted": 0,
                "facts_promoted": 0,
                "facts_filtered": 0,
                "facts_review_only": 0,
                "facts_suppressed": 0,
            },
            "urgent_with_chatter": {
                "segments_promoted": 1,
                "facts_extracted": 2,
                "facts_promoted": 1,
                "facts_filtered": 0,
                "facts_review_only": 1,
                "facts_suppressed": 0,
            },
            "speculative_claim": {
                "segments_promoted": 1,
                "facts_extracted": 1,
                "facts_promoted": 0,
                "facts_filtered": 0,
                "facts_review_only": 1,
                "facts_suppressed": 0,
            },
            "assistant_inferred": {
                "segments_promoted": 1,
                "facts_extracted": 1,
                "facts_promoted": 0,
                "facts_filtered": 0,
                "facts_review_only": 1,
                "facts_suppressed": 0,
            },
            "access_reinforced_low_signal": {
                "segments_promoted": 1,
                "facts_extracted": 1,
                "facts_promoted": 0,
                "facts_filtered": 0,
                "facts_review_only": 1,
                "facts_suppressed": 0,
            },
            "contradiction_update": {
                "segments_promoted": 1,
                "facts_extracted": 2,
                "facts_promoted": contradiction_promoted,
                "facts_filtered": 0,
                "facts_review_only": 0,
                "facts_suppressed": contradiction_suppressed,
            },
            "repeated_correction": {
                "segments_promoted": 1,
                "facts_extracted": 3,
                "facts_promoted": repeated_promoted,
                "facts_filtered": 0,
                "facts_review_only": 0,
                "facts_suppressed": repeated_suppressed,
            },
        },
    )
    alternative_scores = [
        {
            "scenario_id": "segment_mismatch",
            "content": "Urgent container temperature excursion.",
            "raw_fact_ciar": 0.9,
            "stored_ciar": 0.9,
            "lifetime_decision_class": "store_durable",
            "lifetime_decision_reason": "stored as durable memory",
        },
        {
            "scenario_id": "segment_mismatch",
            "content": "The user said thanks and asked to continue later.",
            "raw_fact_ciar": 0.135,
            "stored_ciar": None,
            "review_only": True,
            "lifetime_decision_class": "review_conversational_residue",
            "lifetime_decision_reason": "candidate is chatter",
            "evidence_quality_flags": {
                "conversational_residue": True,
                "low_value_chatter": True,
            },
        },
        {
            "scenario_id": "urgent_with_chatter",
            "content": "Container MEDU7711009 missed its customs hold release window.",
            "raw_fact_ciar": 0.846,
            "stored_ciar": 0.846,
            "lifetime_decision_class": "store_durable",
            "lifetime_decision_reason": "stored as durable memory",
            "evidence_quality_flags": {"domain_signal": True},
        },
        {
            "scenario_id": "urgent_with_chatter",
            "content": (
                "The assistant will record that container MEDU7711009 missed its "
                "customs hold release window."
            ),
            "raw_fact_ciar": 0.6624,
            "stored_ciar": None,
            "review_only": True,
            "lifetime_decision_class": "review_conversational_residue",
            "lifetime_decision_reason": "candidate is assistant-action residue",
            "evidence_quality_flags": {
                "conversational_residue": True,
                "assistant_action_residue": True,
                "domain_signal": True,
            },
        },
        {
            "scenario_id": "speculative_claim",
            "content": "The supplier might miss the customs document deadline.",
            "raw_fact_ciar": 0.231,
            "stored_ciar": None,
            "review_only": True,
            "lifetime_decision_class": "review_uncertain_or_inferred",
            "lifetime_decision_reason": "candidate is speculative",
            "evidence_quality_flags": {
                "speculative_claim": True,
                "assistant_inference": False,
            },
        },
        {
            "scenario_id": "assistant_inferred",
            "content": "The user likely prefers air freight for urgent shipments.",
            "raw_fact_ciar": 0.336,
            "stored_ciar": None,
            "review_only": True,
            "lifetime_decision_class": "review_uncertain_or_inferred",
            "lifetime_decision_reason": "candidate is inferred",
            "evidence_quality_flags": {
                "speculative_claim": False,
                "assistant_inference": True,
            },
        },
        {
            "scenario_id": "access_reinforced_low_signal",
            "content": "Carrier dashboard reference note was repeatedly opened by the operations team.",
            "raw_fact_ciar": 0.75,
            "stored_ciar": None,
            "review_only": True,
            "lifetime_decision_class": "review_access_boost_only",
            "lifetime_decision_reason": "access boost only",
            "evidence_quality_flags": {
                "base_evidence_below_threshold": True,
                "access_boosted_over_threshold": True,
                "recency_access_guardrail": True,
            },
        },
        {
            "scenario_id": "contradiction_update",
            "content": "The shipment is rerouted to Los Angeles.",
            "raw_fact_ciar": 0.8,
            "stored_ciar": 0.8,
            "lifetime_decision_class": "store_durable",
            "lifetime_decision_reason": "stored as durable memory",
        },
    ]
    if suppression_enabled:
        alternative_scores.extend(
            [
                {
                    "scenario_id": "contradiction_update",
                    "content": "The shipment was scheduled for Oakland.",
                    "suppressed": True,
                    "lifetime_decision_class": "suppress_superseded",
                    "lifetime_decision_reason": "superseded by update",
                },
                {
                    "scenario_id": "repeated_correction",
                    "content": (
                        "Latest correction: shipment ALFA-4421 is now routed to "
                        "Long Beach instead of Los Angeles or Oakland."
                    ),
                    "raw_fact_ciar": 0.85,
                    "stored_ciar": 0.85,
                    "lifetime_decision_class": "store_durable",
                    "lifetime_decision_reason": "stored as durable memory",
                },
                {
                    "scenario_id": "repeated_correction",
                    "content": "Shipment ALFA-4421 was scheduled for Oakland.",
                    "suppressed": True,
                    "lifetime_decision_class": "suppress_superseded",
                    "lifetime_decision_reason": "superseded by update",
                },
                {
                    "scenario_id": "repeated_correction",
                    "content": "Update: shipment ALFA-4421 is now routed to Los Angeles.",
                    "suppressed": True,
                    "lifetime_decision_class": "suppress_superseded",
                    "lifetime_decision_reason": "superseded by update",
                },
            ]
        )
    else:
        alternative_scores.extend(
            [
                {
                    "scenario_id": "contradiction_update",
                    "content": "The shipment was scheduled for Oakland.",
                    "raw_fact_ciar": 0.7,
                    "stored_ciar": 0.7,
                    "lifetime_decision_class": "store_durable",
                    "lifetime_decision_reason": "stored as durable memory",
                },
                {
                    "scenario_id": "repeated_correction",
                    "content": "Shipment ALFA-4421 was scheduled for Oakland.",
                    "raw_fact_ciar": 0.72,
                    "stored_ciar": 0.72,
                    "lifetime_decision_class": "store_durable",
                    "lifetime_decision_reason": "stored as durable memory",
                },
                {
                    "scenario_id": "repeated_correction",
                    "content": "Update: shipment ALFA-4421 is now routed to Los Angeles.",
                    "raw_fact_ciar": 0.75,
                    "stored_ciar": 0.75,
                    "lifetime_decision_class": "store_durable",
                    "lifetime_decision_reason": "stored as durable memory",
                },
                {
                    "scenario_id": "repeated_correction",
                    "content": (
                        "Latest correction: shipment ALFA-4421 is now routed to "
                        "Long Beach instead of Los Angeles or Oakland."
                    ),
                    "raw_fact_ciar": 0.85,
                    "stored_ciar": 0.85,
                    "lifetime_decision_class": "store_durable",
                    "lifetime_decision_reason": "stored as durable memory",
                },
            ]
        )
    write_json(run_dir / "alternative_scores.json", alternative_scores)
    write_jsonl(
        run_dir / "events.jsonl",
        [
            {
                "event_type": "fact_review_only",
                "session_id": f"{run_id}__segment_mismatch",
                "data": {"content": "The user thanked the assistant."},
            }
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
    assert config["repeated_correction"]["facts_suppressed"] == 2
    assert (
        report["suppression_evaluation"]["hybrid_gate+suppress_superseded"][
            "repeated_correction"
        ]["suppression_rate"]
        == 0.6667
    )
    assert (
        report["runs"][0]["operational_classification"]["run_quality"]
        == "policy_evidence_with_warnings"
    )
    assert report["run_quality_counts"] == {"policy_evidence_with_warnings": 1}
    lifetime = report["lifetime_decision_evaluation"][
        "hybrid_gate+suppress_superseded"
    ]
    assert lifetime["segment_mismatch"]["lifetime_decision_counts"] == {
        "review_conversational_residue": 1,
        "store_durable": 1,
    }
    assert lifetime["contradiction_update"]["lifetime_decision_counts"] == {
        "store_durable": 1,
        "suppress_superseded": 1,
    }
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
    assert "## Run Quality" in markdown
    assert "## Suppression Evaluation" in markdown
    assert "## Speculative Evaluation" in markdown
    assert "## Residue Evaluation" in markdown
    assert "## Recency/Access Evaluation" in markdown
    assert "## Lifetime Decision Evaluation" in markdown
    assert "`contradiction_update`" in markdown
    assert "`speculative_claim`" in markdown
    assert "`urgent_with_chatter`" in markdown
    assert "`access_reinforced_low_signal`" in markdown
    assert "`review_conversational_residue`" in markdown
    assert "`store_durable`" in markdown
    assert "`policy_evidence_with_warnings`" in markdown


def test_aggregate_runs_preserves_manifest_operational_classification(tmp_path: Path) -> None:
    run_dir = make_run(
        tmp_path,
        run_id="ciar-exp-live-default-hybrid-gate-off-20260520-01",
        promotion_policy="hybrid_gate",
        contradiction_policy="off",
        operational_classification={
            "run_quality": "operational_noise",
            "policy_evidence": False,
            "reasons": ["provider fallback or LLM response warnings detected: 1"],
            "signals": {
                "completed": True,
                "dry_run": False,
                "provider_health_status": "checked",
                "provider_fallback_detected": True,
                "phoenix_ui_ok": True,
                "artifact_complete": True,
                "cleanup_status": "ok",
                "scenario_errors": 0,
                "llm_response_warning_count": 1,
            },
        },
    )

    report = aggregate_runs([run_dir])

    assert report["runs"][0]["operational_classification"]["run_quality"] == (
        "operational_noise"
    )
    assert report["run_quality_counts"] == {"operational_noise": 1}


def test_aggregate_runs_infers_conservative_classification_for_old_manifest(
    tmp_path: Path,
) -> None:
    run_dir = make_run(
        tmp_path,
        run_id="ciar-exp-live-default-hybrid-gate-off-20260520-02",
        promotion_policy="hybrid_gate",
        contradiction_policy="off",
    )
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("operational_classification", None)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = aggregate_runs([run_dir])

    assert report["runs"][0]["operational_classification"]["run_quality"] == (
        "policy_evidence_with_warnings"
    )


def test_suppression_evaluation_compares_focused_policy_modes(tmp_path: Path) -> None:
    off_run = make_run(
        tmp_path,
        run_id="ciar-exp-dry-suppression-eval-off-20260523-01",
        promotion_policy="hybrid_gate",
        contradiction_policy="off",
    )
    metadata_run = make_run(
        tmp_path,
        run_id="ciar-exp-dry-suppression-eval-metadata-20260523-01",
        promotion_policy="hybrid_gate",
        contradiction_policy="metadata_only",
    )
    suppress_run = make_run(
        tmp_path,
        run_id="ciar-exp-dry-suppression-eval-suppress-20260523-01",
        promotion_policy="hybrid_gate",
        contradiction_policy="suppress_superseded",
    )

    report = aggregate_runs([off_run, metadata_run, suppress_run])
    evaluation = report["suppression_evaluation"]

    off_repeated = evaluation["hybrid_gate+off"]["repeated_correction"]
    metadata_repeated = evaluation["hybrid_gate+metadata_only"]["repeated_correction"]
    suppress_contradiction = evaluation["hybrid_gate+suppress_superseded"][
        "contradiction_update"
    ]
    suppress_repeated = evaluation["hybrid_gate+suppress_superseded"][
        "repeated_correction"
    ]

    assert off_repeated["facts_promoted"] == 3
    assert off_repeated["facts_suppressed"] == 0
    assert off_repeated["suppression_rate"] == 0.0
    assert metadata_repeated["facts_promoted"] == 3
    assert metadata_repeated["facts_suppressed"] == 0
    assert suppress_contradiction["facts_promoted"] == 1
    assert suppress_contradiction["facts_suppressed"] == 1
    assert suppress_contradiction["suppression_rate"] == 0.5
    assert suppress_repeated["facts_promoted"] == 1
    assert suppress_repeated["facts_suppressed"] == 2
    assert suppress_repeated["suppression_rate"] == 0.6667
    assert suppress_repeated["suppressed_contents"] == [
        "Shipment ALFA-4421 was scheduled for Oakland.",
        "Update: shipment ALFA-4421 is now routed to Los Angeles.",
    ]


def test_residue_evaluation_reports_review_only_residue_without_promoted_residue(
    tmp_path: Path,
) -> None:
    run_dir = make_run(
        tmp_path,
        run_id="ciar-exp-dry-residue-tightening-20260523-01",
        promotion_policy="hybrid_gate",
        contradiction_policy="off",
    )

    report = aggregate_runs([run_dir])
    evaluation = report["residue_evaluation"]["hybrid_gate+off"]

    assert evaluation["small_talk"]["facts_promoted"] == 0
    assert evaluation["assistant_acknowledgement_noise"]["facts_promoted"] == 0
    assert evaluation["segment_mismatch"]["facts_promoted"] == 1
    assert evaluation["segment_mismatch"]["facts_review_only"] == 1
    assert evaluation["segment_mismatch"]["residue_promoted"] == 0
    assert evaluation["segment_mismatch"]["residue_review_only"] == 1
    assert evaluation["urgent_with_chatter"]["facts_promoted"] == 1
    assert evaluation["urgent_with_chatter"]["facts_review_only"] == 1
    assert evaluation["urgent_with_chatter"]["residue_promoted"] == 0
    assert evaluation["urgent_with_chatter"]["residue_review_only"] == 1
    assert "The user said thanks and asked to continue later." in (
        evaluation["segment_mismatch"]["review_only_contents"]
    )


def test_speculative_evaluation_reports_review_only_uncertainty_flags(
    tmp_path: Path,
) -> None:
    run_dir = make_run(
        tmp_path,
        run_id="ciar-exp-dry-speculative-review-only-20260523-01",
        promotion_policy="hybrid_gate",
        contradiction_policy="off",
    )

    report = aggregate_runs([run_dir])
    evaluation = report["speculative_evaluation"]["hybrid_gate+off"]

    assert evaluation["speculative_claim"]["facts_promoted"] == 0
    assert evaluation["speculative_claim"]["facts_review_only"] == 1
    assert evaluation["speculative_claim"]["speculative_promoted"] == 0
    assert evaluation["speculative_claim"]["speculative_review_only"] == 1
    assert evaluation["assistant_inferred"]["facts_promoted"] == 0
    assert evaluation["assistant_inferred"]["facts_review_only"] == 1
    assert evaluation["assistant_inferred"]["assistant_inference_promoted"] == 0
    assert evaluation["assistant_inferred"]["assistant_inference_review_only"] == 1
    assert "The supplier might miss the customs document deadline." in (
        evaluation["speculative_claim"]["review_only_contents"]
    )
    assert "The user likely prefers air freight for urgent shipments." in (
        evaluation["assistant_inferred"]["review_only_contents"]
    )


def test_recency_access_evaluation_reports_guardrail_review_only(
    tmp_path: Path,
) -> None:
    run_dir = make_run(
        tmp_path,
        run_id="ciar-exp-dry-recency-access-guardrail-20260523-01",
        promotion_policy="hybrid_gate",
        contradiction_policy="off",
    )

    report = aggregate_runs([run_dir])
    evaluation = report["recency_access_evaluation"]["hybrid_gate+off"]

    assert evaluation["access_reinforced_low_signal"]["facts_promoted"] == 0
    assert evaluation["access_reinforced_low_signal"]["facts_review_only"] == 1
    assert evaluation["access_reinforced_low_signal"]["guardrail_promoted"] == 0
    assert evaluation["access_reinforced_low_signal"]["guardrail_review_only"] == 1
    assert "Carrier dashboard reference note was repeatedly opened by the operations team." in (
        evaluation["access_reinforced_low_signal"]["review_only_contents"]
    )


def test_suppression_evaluation_omits_runs_without_focused_scenarios(
    tmp_path: Path,
) -> None:
    run_dir = make_run(
        tmp_path,
        run_id="ciar-exp-old-small-talk-only-20260520-01",
        promotion_policy="hybrid_gate",
        contradiction_policy="off",
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
            }
        },
    )
    write_json(run_dir / "alternative_scores.json", [])

    report = aggregate_runs([run_dir])

    assert report["suppression_evaluation"] == {}
    assert report["residue_evaluation"]["hybrid_gate+off"]["small_talk"]["facts_promoted"] == 0
    assert report["speculative_evaluation"] == {}
    assert report["recency_access_evaluation"] == {}
    assert "## Suppression Evaluation" in render_markdown(report)
    assert "## Residue Evaluation" in render_markdown(report)
    assert "## Speculative Evaluation" in render_markdown(report)
    assert "## Recency/Access Evaluation" in render_markdown(report)
