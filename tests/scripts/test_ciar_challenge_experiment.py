"""Unit tests for the CIAR challenge experiment harness."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_EXPERIMENTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "experiments"
sys.path.insert(0, str(_EXPERIMENTS_DIR))

import run_ciar_challenge as ciar_experiment  # noqa: E402
from run_ciar_challenge import (  # noqa: E402
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

    assert len(scenarios) >= 6
    assert {scenario.expectation for scenario in scenarios} >= {
        "promote",
        "ignore",
        "should_conflict",
        "should_not_floor",
        "needs_review",
    }
    assert all(len(scenario.turns) >= 10 for scenario in scenarios)


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
        @classmethod
        def from_env(cls):
            client = cls()
            client.health_check = failing_health_check
            return client

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr("src.llm.client.LLMClient", FakeLLMClient)
        result = await experiment._run_provider_health_check()
    finally:
        monkeypatch.undo()

    assert result["status"] == "failed"
    assert result["required"] is False
    assert result["error_type"] == "TimeoutError"
