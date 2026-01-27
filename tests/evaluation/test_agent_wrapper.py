"""Unit tests for the FastAPI agent wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sys
import types

import pytest
from fastapi.testclient import TestClient

from src.agents.models import RunTurnRequest, RunTurnResponse


def _install_memory_system_stub() -> None:
    """Install a minimal memory_system stub for import isolation."""
    if "memory_system" in sys.modules:
        return
    module = types.ModuleType("memory_system")

    class _UnifiedMemorySystem:  # pragma: no cover - minimal stub
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

    module.UnifiedMemorySystem = _UnifiedMemorySystem
    sys.modules["memory_system"] = module


_install_memory_system_stub()

from src.evaluation import agent_wrapper  # noqa: E402


@dataclass
class _FactStub:
    fact_id: str


@pytest.fixture
def wrapper_config() -> agent_wrapper.WrapperConfig:
    """Provide a wrapper configuration for unit tests."""
    return agent_wrapper.WrapperConfig(
        agent_type="full",
        port=8080,
        model="test-model",
        redis_url="redis://localhost:6379/0",
        postgres_url="postgresql://test:test@localhost:5432/test",
        session_prefix="full",
        window_size=10,
        ttl_hours=24,
        min_ciar=0.5,
    )


@pytest.fixture
def wrapper_state(mocker: pytest.MockFixture) -> agent_wrapper.AgentWrapperState:
    """Build a wrapper state with mocked dependencies."""
    async def _run_turn(request: RunTurnRequest) -> RunTurnResponse:
        return RunTurnResponse(
            session_id=request.session_id,
            role="assistant",
            content="Acknowledged.",
            turn_id=request.turn_id,
            metadata={"source": "unit"},
            timestamp=datetime.now(timezone.utc),
        )

    agent = mocker.Mock(spec=agent_wrapper.BaseAgent)
    agent.run_turn = mocker.AsyncMock(side_effect=_run_turn)
    agent.health_check = mocker.AsyncMock(return_value={"status": "ok"})
    agent.cleanup_session = mocker.AsyncMock()
    agent.close = mocker.AsyncMock()

    l1_tier = mocker.Mock(spec=agent_wrapper.ActiveContextTier)
    l1_tier.store = mocker.AsyncMock()
    l1_tier.retrieve = mocker.AsyncMock(return_value=[])
    l1_tier.delete = mocker.AsyncMock(return_value=True)
    l1_tier.health_check = mocker.AsyncMock(return_value={"status": "ok"})
    l1_tier.cleanup = mocker.AsyncMock()

    l2_tier = mocker.Mock(spec=agent_wrapper.WorkingMemoryTier)
    l2_tier.query_by_session = mocker.AsyncMock(return_value=[])
    l2_tier.delete = mocker.AsyncMock()
    l2_tier.health_check = mocker.AsyncMock(return_value={"status": "ok"})
    l2_tier.cleanup = mocker.AsyncMock()

    redis_client = mocker.Mock()
    redis_client.ping.return_value = True
    redis_client.close = mocker.Mock()

    return agent_wrapper.AgentWrapperState(
        agent=agent,
        memory_system=mocker.Mock(spec=agent_wrapper.UnifiedMemorySystem),
        l1_tier=l1_tier,
        l2_tier=l2_tier,
        redis_client=redis_client,
        session_prefix="full",
    )


@pytest.fixture
def test_client(mocker: pytest.MockFixture, wrapper_config, wrapper_state):
    """Provide a FastAPI test client with patched lifespan state."""
    mocker.patch("src.evaluation.agent_wrapper.initialize_state", new=mocker.AsyncMock(return_value=wrapper_state))
    mocker.patch("src.evaluation.agent_wrapper.shutdown_state", new=mocker.AsyncMock())
    app = agent_wrapper.create_app(wrapper_config)
    with TestClient(app) as client:
        yield client


@pytest.mark.unit
def test_apply_prefix_idempotent(wrapper_state):
    """Ensure session prefixes are applied once and remain stable."""
    session_id = "test-session"
    prefixed = wrapper_state.apply_prefix(session_id)
    assert prefixed == "full:test-session"
    assert wrapper_state.apply_prefix(prefixed) == prefixed


@pytest.mark.unit
def test_run_turn_success(test_client, wrapper_state):
    """Verify /run_turn stores turns and returns a response."""
    payload = {
        "session_id": "test-session",
        "role": "user",
        "content": "Hello",
        "turn_id": 0,
        "metadata": {"source": "unit"},
    }

    response = test_client.post("/run_turn", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "full:test-session"
    assert body["role"] == "assistant"
    assert wrapper_state.agent.run_turn.await_count == 1
    assert wrapper_state.l1_tier.store.await_count == 2


@pytest.mark.unit
def test_run_turn_error_returns_500(test_client, wrapper_state):
    """Ensure errors from the agent surface as HTTP 500 responses."""
    wrapper_state.agent.run_turn.side_effect = RuntimeError("boom")
    payload = {
        "session_id": "test-session",
        "role": "user",
        "content": "Hello",
        "turn_id": 0,
    }

    response = test_client.post("/run_turn", json=payload)

    assert response.status_code == 500
    assert "boom" in response.json()["detail"]


@pytest.mark.unit
def test_sessions_endpoint_tracks_prefixed_sessions(test_client):
    """Confirm sessions endpoint exposes tracked prefixed session IDs."""
    payload = {
        "session_id": "test-session",
        "role": "user",
        "content": "Hello",
        "turn_id": 0,
    }
    test_client.post("/run_turn", json=payload)

    response = test_client.get("/sessions")

    assert response.status_code == 200
    assert response.json()["sessions"] == ["full:test-session"]


@pytest.mark.unit
def test_memory_state_counts(test_client, wrapper_state):
    """Ensure memory_state returns counts for L1 and L2 data."""
    wrapper_state.l1_tier.retrieve.return_value = ["a", "b"]
    wrapper_state.l2_tier.query_by_session.return_value = [_FactStub("1"), _FactStub("2"), _FactStub("3")]

    response = test_client.get("/memory_state", params={"session_id": "test-session"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "full:test-session"
    assert payload["l1_turns"] == 2
    assert payload["l2_facts"] == 3


@pytest.mark.unit
def test_cleanup_force_all(test_client, wrapper_state):
    """Verify cleanup_force removes all sessions and returns deletion counts."""
    wrapper_state.sessions.update({"full:alpha", "full:beta"})
    wrapper_state.l2_tier.query_by_session.return_value = [_FactStub("a"), _FactStub("b")]

    response = test_client.post("/cleanup_force", params={"session_id": "all"})

    assert response.status_code == 200
    results = response.json()["results"]
    assert set(results.keys()) == {"full:alpha", "full:beta"}
    assert wrapper_state.sessions == set()


@pytest.mark.unit
def test_health_endpoint_reports_status(test_client):
    """Validate health endpoint aggregates subsystem health checks."""
    response = test_client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["redis"] is True
    assert body["l1"] == {"status": "ok"}
    assert body["l2"] == {"status": "ok"}
    assert body["agent"] == {"status": "ok"}


@pytest.mark.unit
def test_parse_args_valid():
    """Ensure CLI parsing accepts required arguments."""
    args = agent_wrapper.parse_args(["--agent-type", "full", "--port", "8080"])

    assert args.agent_type == "full"
    assert args.port == 8080
    assert args.model == "gemini-2.5-flash-lite"


@pytest.mark.unit
def test_build_config_from_env(monkeypatch):
    """Ensure configuration uses environment variables when building config."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://user:pass@localhost:5432/test")
    monkeypatch.setenv("MAS_L1_WINDOW", "15")
    monkeypatch.setenv("MAS_L1_TTL_HOURS", "12")
    monkeypatch.setenv("MAS_MIN_CIAR", "0.7")

    args = agent_wrapper.parse_args(["--agent-type", "full", "--port", "8080", "--model", "unit-model"])
    config = agent_wrapper.build_config(args)

    assert config.session_prefix == "full"
    assert config.window_size == 15
    assert config.ttl_hours == 12
    assert config.min_ciar == 0.7
    assert config.model == "unit-model"
