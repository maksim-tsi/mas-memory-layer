"""Unit tests for the CIAR challenge experiment harness."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_EXPERIMENTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "experiments"
sys.path.insert(0, str(_EXPERIMENTS_DIR))

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
