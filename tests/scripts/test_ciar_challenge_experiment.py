"""Unit tests for the CIAR challenge experiment harness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_EXPERIMENTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "experiments"
sys.path.insert(0, str(_EXPERIMENTS_DIR))

import run_ciar_challenge as ciar_experiment  # noqa: E402
from run_ciar_challenge import (  # noqa: E402
    CannedFactExtractor,
    CIARChallengeExperiment,
    ExperimentConfig,
    ExperimentState,
    ObservedCIARScorer,
    Scenario,
    build_default_scenarios,
    resolve_phoenix_endpoint,
)


class FakeScorer:
    threshold = 0.6

    def calculate_components(self, fact):
        return {
            "certainty": fact["certainty"],
            "impact": fact["impact"],
            "age_decay": 1.0,
            "recency_boost": 1.0,
            "base_score": fact["certainty"] * fact["impact"],
            "temporal_score": 1.0,
            "final_score": fact["certainty"] * fact["impact"],
        }

    def calculate(self, fact):
        return fact["certainty"] * fact["impact"]


class DummyState:
    def __init__(self):
        self.ciar_calls = []


def complete_artifacts() -> dict[str, bool]:
    return {name: True for name in ciar_experiment.REQUIRED_OPERATIONAL_ARTIFACTS}


def test_operational_classifier_marks_clean_dry_run_policy_evidence() -> None:
    classification = ciar_experiment.classify_operational_run(
        manifest={
            "completed_at": "2026-05-23T00:00:00+00:00",
            "dry_run": True,
            "phoenix_ui_check": {"ok": True},
            "provider_health": {"status": "missing"},
            "cleanup": "dry_run_noop",
        },
        promotion_stats={"small_talk": {"errors": 0}},
        events=[],
        alternative_scores=[],
        artifacts=complete_artifacts(),
    )

    assert classification["run_quality"] == "policy_evidence"
    assert classification["policy_evidence"] is True


def test_operational_classifier_marks_skipped_provider_health_as_warning() -> None:
    classification = ciar_experiment.classify_operational_run(
        manifest={
            "completed_at": "2026-05-23T00:00:00+00:00",
            "dry_run": False,
            "phoenix_ui_check": {"ok": True},
            "provider_health": {
                "status": "skipped",
                "reason": "provider checked separately",
                "required": False,
            },
            "cleanup": {"session": {"l1_deleted": True, "l2_deleted": False}},
        },
        promotion_stats={"small_talk": {"errors": 0}},
        events=[],
        alternative_scores=[],
        artifacts=complete_artifacts(),
    )

    assert classification["run_quality"] == "policy_evidence_with_warnings"
    assert classification["policy_evidence"] is True
    assert "provider health skipped" in classification["reasons"][0]


def test_operational_classifier_marks_rule_fallback_as_operational_noise() -> None:
    classification = ciar_experiment.classify_operational_run(
        manifest={
            "completed_at": "2026-05-23T00:00:00+00:00",
            "dry_run": False,
            "phoenix_ui_check": {"ok": True},
            "provider_health": {"status": "checked", "required": False},
            "cleanup": {"session": {"l1_deleted": True, "l2_deleted": True}},
        },
        promotion_stats={"small_talk": {"errors": 0}},
        events=[],
        alternative_scores=[
            {"evidence_quality_flags": {"rule_fallback": True}},
        ],
        artifacts=complete_artifacts(),
    )

    assert classification["run_quality"] == "operational_noise"
    assert classification["policy_evidence"] is False
    assert classification["signals"]["provider_fallback_detected"] is True


def test_operational_classifier_marks_missing_completion_or_artifact_incomplete() -> None:
    artifacts = complete_artifacts()
    artifacts["summary.md"] = False

    classification = ciar_experiment.classify_operational_run(
        manifest={
            "dry_run": True,
            "phoenix_ui_check": {"ok": True},
            "provider_health": {"status": "missing"},
            "cleanup": "dry_run_noop",
        },
        promotion_stats={"small_talk": {"errors": 0}},
        events=[],
        alternative_scores=[],
        artifacts=artifacts,
    )

    assert classification["run_quality"] == "incomplete"
    assert classification["policy_evidence"] is False
    assert classification["signals"]["artifact_complete"] is False


def test_operational_classifier_marks_partial_cleanup_as_warning() -> None:
    classification = ciar_experiment.classify_operational_run(
        manifest={
            "completed_at": "2026-05-23T00:00:00+00:00",
            "dry_run": False,
            "phoenix_ui_check": {"ok": True},
            "provider_health": {"status": "checked", "required": False},
            "cleanup": {
                "session-a": {"l1_deleted": True, "l2_deleted": True},
                "session-b": {"l1_error": "timeout", "l2_deleted": False},
            },
        },
        promotion_stats={"small_talk": {"errors": 0}},
        events=[],
        alternative_scores=[],
        artifacts=complete_artifacts(),
    )

    assert classification["run_quality"] == "policy_evidence_with_warnings"
    assert classification["policy_evidence"] is True
    assert classification["signals"]["cleanup_status"] == "partial"


def test_resolve_phoenix_rejects_stale_localhost_default() -> None:
    with pytest.raises(ValueError, match="localhost:6006"):
        resolve_phoenix_endpoint(
            explicit_endpoint="http://localhost:6006/v1/traces",
            access_mode="auto",
        )


def test_resolve_phoenix_allows_explicit_tunnel_port() -> None:
    endpoint, mode = resolve_phoenix_endpoint(
        explicit_endpoint="http://127.0.0.1:16006/v1/traces",
        access_mode="auto",
    )

    assert endpoint == "http://127.0.0.1:16006/v1/traces"
    assert mode == "configured"


def test_default_scenarios_are_batch_ready() -> None:
    scenarios = build_default_scenarios()
    scenario_ids = {scenario.scenario_id for scenario in scenarios}
    repeated = next(scenario for scenario in scenarios if scenario.scenario_id == "repeated_correction")

    assert len(scenarios) >= 12
    assert scenario_ids >= {
        "stale_preference",
        "explicit_reversal",
        "repeated_correction",
        "assistant_acknowledgement_noise",
        "urgent_with_chatter",
        "access_reinforced_low_signal",
    }
    assert {scenario.expectation for scenario in scenarios} >= {
        "promote",
        "ignore",
        "should_conflict",
        "should_not_floor",
        "needs_review",
    }
    assert all(len(scenario.turns) >= 10 for scenario in scenarios)
    assert repeated.expectation == "should_conflict"
    repeated_text = " ".join(turn["content"] for turn in repeated.turns[:3])
    assert "ALFA-4421" in repeated_text
    assert "Oakland" in repeated_text
    assert "Los Angeles" in repeated_text
    assert "Long Beach" in repeated_text
    assert "dispatch" in repeated_text
    assert "carrier booking" in repeated_text
    assert "port appointment" in repeated_text
    assert "customs destination" in repeated_text
    assert "delivery planning" in repeated_text
    assert "Long Beach is the current route" in repeated.turns[2]["content"]
    assert "superseded" in repeated.turns[2]["content"]


@pytest.mark.asyncio
async def test_canned_fact_extractor_returns_repeated_correction_route_facts() -> None:
    extractor = CannedFactExtractor()

    facts = await extractor.extract_facts(
        "repeated route correction",
        {
            "topic_segment_id": "repeated_correction-seg",
            "session_id": "session-1",
            "topic_label": "Repeated correction",
        },
    )

    assert len(facts) == 3
    contents = [fact.content for fact in facts]
    assert contents == [
        "Shipment ALFA-4421 was scheduled for Oakland.",
        "Update: shipment ALFA-4421 is now routed to Los Angeles.",
        (
            "Latest correction: shipment ALFA-4421 is now routed to Long Beach "
            "instead of Los Angeles or Oakland."
        ),
    ]


@pytest.mark.asyncio
async def test_canned_fact_extractor_returns_residue_tightening_facts() -> None:
    extractor = CannedFactExtractor()

    acknowledgement_facts = await extractor.extract_facts(
        "acknowledgement only",
        {
            "topic_segment_id": "assistant_acknowledgement_noise-seg",
            "session_id": "session-ack",
            "topic_label": "Assistant acknowledgement noise",
        },
    )
    urgent_facts = await extractor.extract_facts(
        "urgent chatter",
        {
            "topic_segment_id": "urgent_with_chatter-seg",
            "session_id": "session-urgent",
            "topic_label": "Urgent with chatter",
        },
    )

    assert [fact.content for fact in acknowledgement_facts] == [
        "The user thanked the assistant.",
        "The assistant acknowledged the user's thanks.",
    ]
    assert [fact.content for fact in urgent_facts] == [
        "Container MEDU7711009 missed its customs hold release window.",
        (
            "The assistant will record that container MEDU7711009 missed its "
            "customs hold release window."
        ),
    ]


@pytest.mark.asyncio
async def test_dry_residue_tightening_reviews_chatter_without_losing_operational_facts(
    tmp_path: Path,
) -> None:
    config = ExperimentConfig(
        run_id="ciar-test-residue-tightening",
        output_dir=tmp_path,
        dry_run=True,
        keep_data=False,
        model="test-model",
        min_ciar=0.6,
        phoenix_endpoint="http://127.0.0.1:16006/v1/traces",
        phoenix_project_name="ciar-test",
        phoenix_access_mode="configured",
        scenario_ids=[
            "small_talk",
            "segment_mismatch",
            "assistant_acknowledgement_noise",
            "urgent_with_chatter",
        ],
        promotion_policy_mode="hybrid_gate",
        contradiction_policy_mode="off",
    )
    experiment = CIARChallengeExperiment(config)

    state = await experiment.run()

    assert state.promotion_stats["small_talk"]["facts_promoted"] == 0
    assert state.promotion_stats["assistant_acknowledgement_noise"]["facts_promoted"] == 0
    assert state.promotion_stats["segment_mismatch"]["facts_promoted"] == 1
    assert state.promotion_stats["segment_mismatch"]["facts_review_only"] == 1
    assert state.promotion_stats["urgent_with_chatter"]["facts_promoted"] == 1
    assert state.promotion_stats["urgent_with_chatter"]["facts_review_only"] == 1

    promoted = {
        row["content"]
        for row in state.alternative_scores
        if not row.get("review_only") and row.get("suppressed") is not True
    }
    review_only = {
        row["content"]: row["evidence_quality_flags"]
        for row in state.alternative_scores
        if row.get("review_only")
    }
    lifetime_classes = {
        row["content"]: row["lifetime_decision_class"]
        for row in state.alternative_scores
    }
    assert "Container MAEU9182736 had a temperature excursion above threshold." in promoted
    assert "Container MEDU7711009 missed its customs hold release window." in promoted
    assert all(row.get("lifetime_decision_class") for row in state.alternative_scores)
    assert (
        lifetime_classes["Container MAEU9182736 had a temperature excursion above threshold."]
        == "store_durable"
    )
    assert (
        "The user said thanks and asked to continue later."
        in review_only
    )
    assert review_only[
        "The user said thanks and asked to continue later."
    ]["conversational_residue"] is True
    assert (
        lifetime_classes["The user said thanks and asked to continue later."]
        == "review_conversational_residue"
    )
    assistant_row = (
        "The assistant will record that container MEDU7711009 missed its "
        "customs hold release window."
    )
    assert assistant_row in review_only
    assert review_only[assistant_row]["assistant_action_residue"] is True
    assert review_only[assistant_row]["conversational_residue"] is True
    assert lifetime_classes[assistant_row] == "review_conversational_residue"


@pytest.mark.asyncio
async def test_dry_speculative_claims_are_review_only_with_positive_controls(
    tmp_path: Path,
) -> None:
    config = ExperimentConfig(
        run_id="ciar-test-speculative-review-only",
        output_dir=tmp_path,
        dry_run=True,
        keep_data=False,
        model="test-model",
        min_ciar=0.6,
        phoenix_endpoint="http://127.0.0.1:16006/v1/traces",
        phoenix_project_name="ciar-test",
        phoenix_access_mode="configured",
        scenario_ids=[
            "speculative_claim",
            "assistant_inferred",
            "clear_constraint",
            "urgent_event",
        ],
        promotion_policy_mode="hybrid_gate",
        contradiction_policy_mode="off",
    )
    experiment = CIARChallengeExperiment(config)

    state = await experiment.run()

    assert state.promotion_stats["speculative_claim"]["segments_promoted"] == 1
    assert state.promotion_stats["speculative_claim"]["facts_extracted"] == 1
    assert state.promotion_stats["speculative_claim"]["facts_promoted"] == 0
    assert state.promotion_stats["speculative_claim"]["facts_review_only"] == 1
    assert state.promotion_stats["assistant_inferred"]["segments_promoted"] == 1
    assert state.promotion_stats["assistant_inferred"]["facts_extracted"] == 1
    assert state.promotion_stats["assistant_inferred"]["facts_promoted"] == 0
    assert state.promotion_stats["assistant_inferred"]["facts_review_only"] == 1
    assert state.promotion_stats["clear_constraint"]["facts_promoted"] == 1
    assert state.promotion_stats["urgent_event"]["facts_promoted"] == 1

    review_only = {
        row["scenario_id"]: row
        for row in state.alternative_scores
        if row.get("review_only")
    }
    assert review_only["speculative_claim"]["evidence_quality_flags"][
        "speculative_claim"
    ] is True
    assert (
        review_only["speculative_claim"]["lifetime_decision_class"]
        == "review_uncertain_or_inferred"
    )
    assert review_only["assistant_inferred"]["evidence_quality_flags"][
        "assistant_inference"
    ] is True
    assert (
        review_only["assistant_inferred"]["lifetime_decision_class"]
        == "review_uncertain_or_inferred"
    )
    assert all(
        not row.get("review_only")
        for row in state.alternative_scores
        if row["scenario_id"] in {"clear_constraint", "urgent_event"}
    )


@pytest.mark.asyncio
async def test_dry_recency_access_guardrail_reviews_low_signal_access_boost(
    tmp_path: Path,
) -> None:
    config = ExperimentConfig(
        run_id="ciar-test-recency-access-guardrail",
        output_dir=tmp_path,
        dry_run=True,
        keep_data=False,
        model="test-model",
        min_ciar=0.6,
        phoenix_endpoint="http://127.0.0.1:16006/v1/traces",
        phoenix_project_name="ciar-test",
        phoenix_access_mode="configured",
        scenario_ids=[
            "access_reinforced_low_signal",
            "clear_constraint",
            "urgent_event",
        ],
        promotion_policy_mode="hybrid_gate",
        contradiction_policy_mode="off",
    )
    experiment = CIARChallengeExperiment(config)

    state = await experiment.run()

    stats = state.promotion_stats["access_reinforced_low_signal"]
    assert stats["segments_promoted"] == 1
    assert stats["facts_extracted"] == 1
    assert stats["facts_promoted"] == 0
    assert stats["facts_review_only"] == 1
    assert state.promotion_stats["clear_constraint"]["facts_promoted"] == 1
    assert state.promotion_stats["urgent_event"]["facts_promoted"] == 1

    review_only = {
        row["scenario_id"]: row
        for row in state.alternative_scores
        if row.get("review_only")
    }
    guardrail_row = review_only["access_reinforced_low_signal"]
    flags = guardrail_row["evidence_quality_flags"]
    assert guardrail_row["raw_fact_ciar"] == 0.75
    assert guardrail_row["lifetime_decision_class"] == "review_access_boost_only"
    assert flags["base_evidence_below_threshold"] is True
    assert flags["access_boosted_over_threshold"] is True
    assert flags["recency_access_guardrail"] is True
    assert all(
        not row.get("review_only")
        for row in state.alternative_scores
        if row["scenario_id"] in {"clear_constraint", "urgent_event"}
    )


@pytest.mark.asyncio
async def test_dry_repeated_correction_suppresses_old_and_middle_routes(
    tmp_path: Path,
) -> None:
    config = ExperimentConfig(
        run_id="ciar-test-repeated-correction",
        output_dir=tmp_path,
        dry_run=True,
        keep_data=False,
        model="test-model",
        min_ciar=0.6,
        phoenix_endpoint="http://127.0.0.1:16006/v1/traces",
        phoenix_project_name="ciar-test",
        phoenix_access_mode="configured",
        scenario_ids=["repeated_correction"],
        promotion_policy_mode="hybrid_gate",
        contradiction_policy_mode="suppress_superseded",
    )
    experiment = CIARChallengeExperiment(config)

    state = await experiment.run()

    stats = state.promotion_stats["repeated_correction"]
    assert stats["segments_promoted"] == 1
    assert stats["facts_extracted"] == 3
    assert stats["facts_promoted"] == 1
    assert stats["facts_suppressed"] == 2

    significance_events = [
        event
        for event in state.events
        if event.get("event_type") == "significance_scored"
        and event.get("session_id", "").endswith("__repeated_correction")
    ]
    assert len(significance_events) == 1
    significance = significance_events[0]["data"]
    assert significance["ciar_score"] >= 0.6
    assert significance["certainty"] == pytest.approx(0.95)
    assert significance["impact"] == pytest.approx(0.9)
    assert "topic_excerpt" in significance
    assert "summary_excerpt" in significance
    assert "ALFA-4421" in significance["summary_excerpt"]

    suppressed_rows = [
        row for row in state.alternative_scores if row.get("suppressed") is True
    ]
    stored_rows = [
        row for row in state.alternative_scores if row.get("suppressed") is not True
    ]
    assert len(suppressed_rows) == 2
    assert len(stored_rows) == 1
    assert "Long Beach" in stored_rows[0]["content"]
    assert stored_rows[0]["lifetime_decision_class"] == "store_durable"
    assert {row["content"] for row in suppressed_rows} == {
        "Shipment ALFA-4421 was scheduled for Oakland.",
        "Update: shipment ALFA-4421 is now routed to Los Angeles.",
    }
    assert {row["lifetime_decision_class"] for row in suppressed_rows} == {
        "suppress_superseded"
    }


def test_observed_ciar_scorer_delegates_without_changing_score(tmp_path: Path) -> None:
    state = DummyState()
    scorer = ObservedCIARScorer(FakeScorer(), tmp_path, state)
    fact = {
        "fact_id": "fact-1",
        "session_id": "session-1",
        "content": "Test fact",
        "certainty": 0.8,
        "impact": 0.5,
    }

    score = scorer.calculate(fact)

    assert score == 0.4
    assert state.ciar_calls[0]["session_id"] == "session-1"
    assert state.ciar_calls[0]["score"] == 0.4
    assert state.ciar_calls[0]["components"]["base_score"] == 0.4
    assert (tmp_path / "ciar_calls.jsonl").exists()


@pytest.mark.asyncio
async def test_score_alternatives_matches_raw_ciar_when_storage_rewrites_fact_id(
    tmp_path: Path,
) -> None:
    config = ExperimentConfig(
        run_id="ciar-test",
        output_dir=tmp_path,
        dry_run=True,
        keep_data=False,
        model="test-model",
        min_ciar=0.6,
        phoenix_endpoint="http://127.0.0.1:16006/v1/traces",
        phoenix_project_name="ciar-test",
        phoenix_access_mode="configured",
    )
    experiment = CIARChallengeExperiment(config)
    state = ExperimentState(config=config)
    scenario = Scenario(
        scenario_id="segment_mismatch",
        title="Segment mismatch",
        expectation="should_not_floor",
        turns=[],
    )
    state.scenarios = [scenario]
    state.session_by_scenario = {"segment_mismatch": "session-1"}
    state.events = [
        {
            "event_type": "significance_scored",
            "session_id": "session-1",
            "data": {"ciar_score": 0.9},
        }
    ]
    state.ciar_calls = [
        {
            "fact_id": "pre-store-uuid",
            "session_id": "session-1",
            "content": "The user thanked the assistant.",
            "score": 0.4,
            "components": {"certainty": 0.8, "impact": 0.5},
        }
    ]
    state.l2_facts = {
        "segment_mismatch": [
            {
                "fact_id": "42",
                "session_id": "session-1",
                "content": "The user thanked the assistant.",
                "ciar_score": 0.9,
                "certainty": 0.9,
                "impact": 1.0,
                "source_type": "extracted",
            }
        ]
    }

    await experiment.score_alternatives(state)

    assert state.alternative_scores[0]["raw_fact_ciar"] == 0.4
    assert state.alternative_scores[0]["fact_gate_decision"] is False
    assert state.alternative_scores[0]["floor_applied"] is True


@pytest.mark.asyncio
async def test_score_alternatives_recovers_provenance_from_events_when_storage_drops_metadata(
    tmp_path: Path,
) -> None:
    config = ExperimentConfig(
        run_id="ciar-test",
        output_dir=tmp_path,
        dry_run=True,
        keep_data=False,
        model="test-model",
        min_ciar=0.6,
        phoenix_endpoint="http://127.0.0.1:16006/v1/traces",
        phoenix_project_name="ciar-test",
        phoenix_access_mode="configured",
        promotion_policy_mode="hybrid_gate",
    )
    experiment = CIARChallengeExperiment(config)
    state = ExperimentState(config=config)
    scenario = Scenario(
        scenario_id="segment_mismatch",
        title="Segment mismatch",
        expectation="should_not_floor",
        turns=[],
    )
    state.scenarios = [scenario]
    state.session_by_scenario = {"segment_mismatch": "session-1"}
    state.events = [
        {
            "event_type": "fact_promoted",
            "session_id": "session-1",
            "data": {
                "fact_id": "pre-store-uuid",
                "content": "Urgent container temperature excursion.",
                "ciar_provenance": {
                    "promotion_policy_mode": "hybrid_gate",
                    "segment_ciar": 0.9,
                    "raw_fact_ciar": 0.8,
                    "pre_inheritance_ciar": 0.8,
                    "post_inheritance_ciar": 0.8,
                    "stored_ciar": 0.8,
                    "ciar_score_source": "raw_fact",
                    "segment_inherited": False,
                    "fact_gate_decision": True,
                    "lifetime_decision_class": "store_durable",
                    "lifetime_decision_reason": "stored as durable memory",
                    "evidence_quality_flags": {"domain_signal": True},
                },
            },
        }
    ]
    state.ciar_calls = []
    state.l2_facts = {
        "segment_mismatch": [
            {
                "fact_id": "42",
                "session_id": "session-1",
                "content": "Urgent container temperature excursion.",
                "ciar_score": 0.8,
                "certainty": 1.0,
                "impact": 0.8,
                "source_type": "extracted",
                "metadata": {},
            }
        ]
    }

    await experiment.score_alternatives(state)

    row = state.alternative_scores[0]
    assert row["promotion_policy_mode"] == "hybrid_gate"
    assert row["raw_fact_ciar"] == 0.8
    assert row["stored_ciar"] == 0.8
    assert row["ciar_score_source"] == "raw_fact"
    assert row["lifetime_decision_class"] == "store_durable"
    assert row["evidence_quality_flags"]["domain_signal"] is True


@pytest.mark.asyncio
async def test_score_alternatives_records_suppressed_facts_from_events(
    tmp_path: Path,
) -> None:
    config = ExperimentConfig(
        run_id="ciar-test",
        output_dir=tmp_path,
        dry_run=True,
        keep_data=False,
        model="test-model",
        min_ciar=0.6,
        phoenix_endpoint="http://127.0.0.1:16006/v1/traces",
        phoenix_project_name="ciar-test",
        phoenix_access_mode="configured",
        promotion_policy_mode="hybrid_gate",
        contradiction_policy_mode="suppress_superseded",
    )
    experiment = CIARChallengeExperiment(config)
    state = ExperimentState(config=config)
    scenario = Scenario(
        scenario_id="contradiction_update",
        title="Contradiction update",
        expectation="should_conflict",
        turns=[],
    )
    state.scenarios = [scenario]
    state.session_by_scenario = {"contradiction_update": "session-1"}
    state.events = [
        {
            "event_type": "fact_suppressed",
            "session_id": "session-1",
            "data": {
                "fact_id": "fact-old-route",
                "content": "The shipment was scheduled for Oakland.",
                "ciar_provenance": {
                    "promotion_policy_mode": "hybrid_gate",
                    "raw_fact_ciar": 0.72,
                    "fact_gate_decision": True,
                    "lifetime_decision_class": "suppress_superseded",
                    "lifetime_decision_reason": "superseded_by_explicit_update",
                },
                "contradiction_policy": {
                    "mode": "suppress_superseded",
                    "decision": "SUPPRESS",
                    "superseded_by_fact_id": "fact-new-route",
                },
            },
        }
    ]
    state.ciar_calls = []
    state.l2_facts = {"contradiction_update": []}

    await experiment.score_alternatives(state)

    row = state.alternative_scores[0]
    assert row["suppressed"] is True
    assert row["contradiction_policy_mode"] == "suppress_superseded"
    assert row["contradiction_policy"]["superseded_by_fact_id"] == "fact-new-route"
    assert row["lifetime_decision_class"] == "suppress_superseded"


@pytest.mark.asyncio
async def test_preflight_records_provider_health_skip_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "present")
    monkeypatch.setenv("REDIS_URL", "redis://example.test:6379/0")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://example.test/db")
    monkeypatch.setattr(
        ciar_experiment,
        "check_http_reachable",
        lambda url: {"ok": True, "status": 200, "url": url},
    )
    config = ExperimentConfig(
        run_id="ciar-test",
        output_dir=tmp_path,
        dry_run=False,
        keep_data=False,
        model="test-model",
        min_ciar=0.6,
        phoenix_endpoint="http://phoenix.test:6006/v1/traces",
        phoenix_project_name="ciar-test",
        phoenix_access_mode="configured",
        skip_provider_health=True,
        provider_health_skip_reason="known Redis setup interaction",
    )
    experiment = CIARChallengeExperiment(config)
    state = ExperimentState(config=config)

    await experiment.preflight(state)

    assert state.manifest["provider_health"] == {
        "status": "skipped",
        "reason": "known Redis setup interaction",
        "required": False,
    }


@pytest.mark.asyncio
async def test_provider_health_failure_is_recorded_when_not_required(tmp_path: Path) -> None:
    config = ExperimentConfig(
        run_id="ciar-test",
        output_dir=tmp_path,
        dry_run=False,
        keep_data=False,
        model="test-model",
        min_ciar=0.6,
        phoenix_endpoint="http://phoenix.test:6006/v1/traces",
        phoenix_project_name="ciar-test",
        phoenix_access_mode="configured",
        provider_health_timeout_s=0.1,
    )
    experiment = CIARChallengeExperiment(config)

    async def failing_health_check() -> dict[str, object]:
        raise TimeoutError("provider health timed out")

    class FakeLLMClient:
        closed = False

        @classmethod
        def from_env(cls):
            client = cls()
            client.health_check = failing_health_check
            return client

        async def close(self):
            FakeLLMClient.closed = True
            return {"status": "ok", "errors": []}

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr("src.llm.client.LLMClient", FakeLLMClient)
        result = await experiment._run_provider_health_check()
    finally:
        monkeypatch.undo()

    assert result["status"] == "failed"
    assert result["required"] is False
    assert result["error_type"] == "TimeoutError"
    assert result["cleanup"] == {"status": "ok", "errors": []}
    assert FakeLLMClient.closed is True


@pytest.mark.asyncio
async def test_preflight_records_provider_health_cleanup_and_post_redis_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "present")
    monkeypatch.setenv("REDIS_URL", "redis://example.test:6379/0")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://user:secret@example.test/db")
    monkeypatch.setattr(
        ciar_experiment,
        "check_http_reachable",
        lambda url: {"ok": True, "status": 200, "url": url},
    )
    config = ExperimentConfig(
        run_id="ciar-test",
        output_dir=tmp_path,
        dry_run=False,
        keep_data=False,
        model="test-model",
        min_ciar=0.6,
        phoenix_endpoint="http://phoenix.test:6006/v1/traces",
        phoenix_project_name="ciar-test",
        phoenix_access_mode="configured",
        require_provider_health=True,
    )
    experiment = CIARChallengeExperiment(config)
    state = ExperimentState(config=config)

    async def fake_provider_health() -> dict[str, object]:
        return {
            "status": "checked",
            "required": True,
            "cleanup": {"status": "ok", "errors": []},
            "reports": {},
        }

    async def fake_redis_probe() -> dict[str, object]:
        return {"ok": True, "elapsed_ms": 1.0}

    experiment._run_provider_health_check = fake_provider_health
    experiment._run_post_health_redis_probe = fake_redis_probe

    await experiment.preflight(state)

    assert state.manifest["provider_health"]["cleanup"] == {"status": "ok", "errors": []}
    assert state.manifest["provider_health"]["post_health_redis_probe"] == {
        "ok": True,
        "elapsed_ms": 1.0,
    }


@pytest.mark.asyncio
async def test_preflight_blocks_required_health_when_post_redis_probe_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "present")
    monkeypatch.setenv("REDIS_URL", "redis://example.test:6379/0")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://user:secret@example.test/db")
    monkeypatch.setattr(
        ciar_experiment,
        "check_http_reachable",
        lambda url: {"ok": True, "status": 200, "url": url},
    )
    config = ExperimentConfig(
        run_id="ciar-test",
        output_dir=tmp_path,
        dry_run=False,
        keep_data=False,
        model="test-model",
        min_ciar=0.6,
        phoenix_endpoint="http://phoenix.test:6006/v1/traces",
        phoenix_project_name="ciar-test",
        phoenix_access_mode="configured",
        require_provider_health=True,
    )
    experiment = CIARChallengeExperiment(config)
    state = ExperimentState(config=config)

    async def fake_provider_health() -> dict[str, object]:
        return {
            "status": "checked",
            "required": True,
            "cleanup": {"status": "ok", "errors": []},
            "reports": {},
        }

    async def failing_redis_probe() -> dict[str, object]:
        return {"ok": False, "error_type": "StorageTimeoutError", "error": "timeout"}

    experiment._run_provider_health_check = fake_provider_health
    experiment._run_post_health_redis_probe = failing_redis_probe

    with pytest.raises(RuntimeError, match="Post-health Redis probe failed"):
        await experiment.preflight(state)

    manifest = json.loads((experiment.output_dir / "run_manifest.json").read_text())
    assert manifest["provider_health"]["post_health_redis_probe"]["ok"] is False
    assert manifest["operational_classification"]["run_quality"] == "incomplete"


def live_setup_config(tmp_path: Path) -> ExperimentConfig:
    return ExperimentConfig(
        run_id="ciar-live-setup-test",
        output_dir=tmp_path,
        dry_run=False,
        keep_data=False,
        model="test-model",
        min_ciar=0.6,
        phoenix_endpoint="http://phoenix.test:6006/v1/traces",
        phoenix_project_name="ciar-live-setup-test",
        phoenix_access_mode="configured",
    )


class FakeRedisAdapter:
    def __init__(self, config):
        self.config = config


class FakePostgresAdapter:
    def __init__(self, config):
        self.config = config


class FakeTier:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def initialize(self) -> None:
        return None


class FailingL1Tier(FakeTier):
    async def initialize(self) -> None:
        raise TimeoutError("Redis timeout for postgresql://user:secret@postgres.test/db")


class FakeLLMClient:
    @classmethod
    def from_env(cls):
        return cls()

    def available_providers(self):
        return ["fake-provider"]


class FakePromotionEngine:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeTopicSegmenter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeFactExtractor:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeCIARScorer:
    threshold = 0.6

    def calculate(self, fact):
        return 0.6

    def calculate_components(self, fact):
        return {"final_score": 0.6}


def patch_live_setup_dependencies(monkeypatch: pytest.MonkeyPatch, *, l1_tier=FakeTier) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://redis.test:6379/0")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://user:secret@postgres.test/db")
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://phoenix.test:6006/v1/traces")
    monkeypatch.setenv("MAS_REDIS_TIMEOUT", "12.5")
    monkeypatch.setattr("src.llm.client.ensure_phoenix_instrumentation", lambda: None)
    monkeypatch.setattr("src.llm.client.LLMClient", FakeLLMClient)
    monkeypatch.setattr("src.storage.redis_adapter.RedisAdapter", FakeRedisAdapter)
    monkeypatch.setattr("src.storage.postgres_adapter.PostgresAdapter", FakePostgresAdapter)
    monkeypatch.setattr("src.memory.tiers.ActiveContextTier", l1_tier)
    monkeypatch.setattr("src.memory.tiers.WorkingMemoryTier", FakeTier)
    monkeypatch.setattr("src.memory.engines.promotion_engine.PromotionEngine", FakePromotionEngine)
    monkeypatch.setattr("src.memory.engines.topic_segmenter.TopicSegmenter", FakeTopicSegmenter)
    monkeypatch.setattr("src.memory.engines.fact_extractor.FactExtractor", FakeFactExtractor)
    monkeypatch.setattr("src.memory.ciar_scorer.CIARScorer", FakeCIARScorer)


@pytest.mark.asyncio
async def test_setup_runtime_failure_writes_run_error_and_incomplete_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_live_setup_dependencies(monkeypatch, l1_tier=FailingL1Tier)
    config = live_setup_config(tmp_path)
    experiment = CIARChallengeExperiment(config)
    state = ExperimentState(config=config)

    with pytest.raises(TimeoutError):
        await experiment.setup_runtime(state)

    manifest = json.loads((experiment.output_dir / "run_manifest.json").read_text())
    run_error = json.loads((experiment.output_dir / "run_error.json").read_text())

    assert manifest["runtime_setup"]["status"] == "failed"
    assert manifest["runtime_setup"]["failure_phase"] == "l1_initialize_started"
    assert manifest["runtime_setup"]["error_type"] == "TimeoutError"
    assert manifest["operational_classification"]["run_quality"] == "incomplete"
    assert run_error["failure_phase"] == "l1_initialize_started"
    assert run_error["error_type"] == "TimeoutError"
    assert "secret" not in run_error["error"]
    assert manifest["runtime_setup"]["service_endpoints"]["postgres"]["password_present"] is True


@pytest.mark.asyncio
async def test_setup_runtime_success_records_runtime_setup_phases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_live_setup_dependencies(monkeypatch)
    config = live_setup_config(tmp_path)
    experiment = CIARChallengeExperiment(config)
    state = ExperimentState(config=config)

    await experiment.setup_runtime(state)

    manifest = json.loads((experiment.output_dir / "run_manifest.json").read_text())
    phase_names = [phase["name"] for phase in manifest["runtime_setup"]["phases"]]
    assert manifest["runtime_setup"]["status"] == "ok"
    assert manifest["runtime_setup"]["redis_timeout_s"] == 12.5
    assert "redis_adapter_created" in phase_names
    assert "l1_initialize_started" in phase_names
    assert "l1_initialize_ok" in phase_names
    assert "l2_initialize_started" in phase_names
    assert "l2_initialize_ok" in phase_names
    assert manifest["runtime"]["provider_order"] == ["fake-provider"]
