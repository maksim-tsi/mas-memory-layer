"""Unit tests for API Wall tracing and response metadata."""

from __future__ import annotations

import importlib
import sys
import types
from datetime import UTC, datetime
from types import SimpleNamespace

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


class _FakeSpan:
    def __init__(self, trace_id: int, span_id: int) -> None:
        self.attributes: dict[str, object] = {}
        self.status = None
        self._context = SimpleNamespace(trace_id=trace_id, span_id=span_id, is_valid=True)

    def is_recording(self) -> bool:
        return True

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def get_span_context(self) -> SimpleNamespace:
        return self._context

    def set_status(self, status: object) -> None:
        self.status = status


class _FakeSpanManager:
    def __init__(self, span: _FakeSpan) -> None:
        self._span = span

    def __enter__(self) -> _FakeSpan:
        return self._span

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _FakeTracer:
    def __init__(self, span: _FakeSpan) -> None:
        self._span = span
        self.started: list[dict[str, object]] = []

    def start_as_current_span(self, name: str, context: object | None = None) -> _FakeSpanManager:
        self.started.append({"name": name, "context": context})
        return _FakeSpanManager(self._span)


@pytest.fixture
def server_module(monkeypatch: pytest.MonkeyPatch):
    """Import the API Wall module with minimal required environment."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("MAS_AGENT_TYPE", "full")
    module = importlib.import_module("src.server")
    return importlib.reload(module)


@pytest.fixture
def wrapper_config(server_module):
    """Provide an API Wall configuration for unit tests."""
    return server_module.agent_wrapper.WrapperConfig(
        agent_type="full",
        agent_variant="unit",
        port=8080,
        model="test-model",
        redis_url="redis://localhost:6379/0",
        postgres_url="postgresql://test:test@localhost:5432/test",
        session_prefix="full__unit",
        window_size=10,
        ttl_hours=24,
        min_ciar=0.5,
    )


@pytest.fixture
def wrapper_state(server_module, mocker: pytest.MockFixture):
    """Build wrapper state with mocked dependencies for API Wall tests."""

    async def _run_turn(request: RunTurnRequest, history=None) -> RunTurnResponse:
        del history
        return RunTurnResponse(
            session_id=request.session_id,
            role="assistant",
            content="Acknowledged.",
            turn_id=request.turn_id,
            metadata={
                "source": "unit",
                "llm_provider": "groq",
                "llm_model": "openai/gpt-oss-120b",
            },
            timestamp=datetime.now(UTC),
        )

    agent = mocker.Mock(spec=server_module.agent_wrapper.BaseAgent)
    agent.run_turn = mocker.AsyncMock(side_effect=_run_turn)
    agent.health_check = mocker.AsyncMock(return_value={"status": "ok"})
    agent.cleanup_session = mocker.AsyncMock()
    agent.close = mocker.AsyncMock()

    l1_tier = mocker.Mock(spec=server_module.agent_wrapper.ActiveContextTier)
    l1_tier.store = mocker.AsyncMock()
    l1_tier.retrieve = mocker.AsyncMock(return_value=[])
    l1_tier.delete = mocker.AsyncMock(return_value=True)
    l1_tier.health_check = mocker.AsyncMock(return_value={"status": "ok"})
    l1_tier.cleanup = mocker.AsyncMock()

    l2_tier = mocker.Mock(spec=server_module.agent_wrapper.WorkingMemoryTier)
    l2_tier.query_by_session = mocker.AsyncMock(return_value=[])
    l2_tier.delete = mocker.AsyncMock()
    l2_tier.health_check = mocker.AsyncMock(return_value={"status": "ok"})
    l2_tier.cleanup = mocker.AsyncMock()

    redis_client = mocker.Mock()
    redis_client.ping.return_value = True
    redis_client.close = mocker.Mock()

    rate_limiter = mocker.Mock()
    rate_limiter.wait_if_needed = mocker.AsyncMock()
    rate_limiter.record_usage = mocker.Mock()
    rate_limiter.register_error = mocker.Mock()

    return server_module.agent_wrapper.AgentWrapperState(
        agent=agent,
        memory_system=mocker.Mock(spec=server_module.agent_wrapper.UnifiedMemorySystem),
        l1_tier=l1_tier,
        l2_tier=l2_tier,
        redis_client=redis_client,
        agent_type="full",
        agent_variant="unit",
        session_prefix="full__unit",
        rate_limiter=rate_limiter,
    )


@pytest.fixture
def test_client(server_module, wrapper_config, wrapper_state, mocker: pytest.MockFixture):
    """Provide a TestClient with patched API Wall lifespan dependencies."""
    mocker.patch.object(server_module, "_ensure_api_wall_tracing")
    mocker.patch.object(
        server_module.agent_wrapper,
        "initialize_state",
        new=mocker.AsyncMock(return_value=wrapper_state),
    )
    mocker.patch.object(
        server_module.agent_wrapper,
        "shutdown_state",
        new=mocker.AsyncMock(),
    )
    app = server_module.create_app(wrapper_config)
    with TestClient(app) as client:
        yield client


@pytest.mark.unit
def test_chat_completions_adds_trace_metadata(
    server_module, test_client, wrapper_state, mocker: pytest.MockFixture
):
    """Ensure API Wall responses expose trace ids and enrich the request span."""
    fake_span = _FakeSpan(
        trace_id=int("1234567890abcdef1234567890abcdef", 16),
        span_id=int("1234567890abcdef", 16),
    )
    fake_tracer = _FakeTracer(fake_span)
    parent_context = {}
    mocker.patch.object(server_module, "_get_api_wall_tracer", return_value=fake_tracer)
    mocker.patch.object(server_module, "_extract_parent_context", return_value=parent_context)

    response = test_client.post(
        "/v1/chat/completions",
        json={
            "messages": [{"role": "user", "content": "Hello"}],
            "model": "openai/gpt-oss-120b",
        },
        headers={
            "X-Session-Id": "trace-test",
            "traceparent": "00-1234567890abcdef1234567890abcdef-1234567890abcdef-01",
        },
    )

    assert response.status_code == 200
    body = response.json()
    metadata = body["metadata"]

    assert metadata["client_session_id"] == "trace-test"
    assert metadata["yaam_session_id"] == "full__unit:trace-test"
    assert metadata["yaam_trace_id"] == "1234567890abcdef1234567890abcdef"
    assert metadata["yaam_span_id"] == "1234567890abcdef"
    assert metadata["llm_provider"] == "groq"
    assert metadata["llm_model"] == "openai/gpt-oss-120b"

    assert fake_tracer.started == [
        {
            "name": "yaam.api_wall.chat_completions",
            "context": parent_context,
        }
    ]
    assert fake_span.attributes["yaam.client_session_id"] == "trace-test"
    assert fake_span.attributes["yaam.session_id"] == "full__unit:trace-test"
    assert fake_span.attributes["yaam.agent_type"] == "full"
    assert fake_span.attributes["yaam.agent_variant"] == "unit"
    assert fake_span.attributes["yaam.llm_provider"] == "groq"
    assert fake_span.attributes["yaam.llm_model"] == "openai/gpt-oss-120b"
    assert fake_span.attributes["yaam.trace_id"] == "1234567890abcdef1234567890abcdef"

    run_request = wrapper_state.agent.run_turn.await_args.args[0]
    assert run_request.metadata is not None
    assert run_request.metadata["skip_l1_write"] is True


@pytest.mark.unit
def test_chat_completions_allows_metadata_override_for_skip_l1_write(test_client, wrapper_state):
    """Ensure request metadata can explicitly enable L1 writes for controlled experiments."""
    response = test_client.post(
        "/v1/chat/completions",
        json={
            "messages": [{"role": "user", "content": "Persist this turn for retrieval."}],
            "model": "openai/gpt-oss-120b",
            "metadata": {
                "skip_l1_write": False,
                "experiment_label": "phoenix-option-a",
            },
        },
        headers={"X-Session-Id": "override-test"},
    )

    assert response.status_code == 200

    run_request = wrapper_state.agent.run_turn.await_args.args[0]
    assert run_request.metadata is not None
    assert run_request.metadata["skip_l1_write"] is False
    assert run_request.metadata["experiment_label"] == "phoenix-option-a"


@pytest.mark.unit
def test_episode_consolidation_endpoint(
    server_module, test_client, wrapper_state, mocker: pytest.MockFixture
):
    """Ensure the consolidation endpoint accepts episodes and offloads to L2."""
    fake_span = _FakeSpan(
        trace_id=int("1234567890abcdef1234567890abcdef", 16),
        span_id=int("1234567890abcdef", 16),
    )
    fake_tracer = _FakeTracer(fake_span)
    parent_context = {}
    mocker.patch.object(server_module, "_get_api_wall_tracer", return_value=fake_tracer)
    mocker.patch.object(server_module, "_extract_parent_context", return_value=parent_context)

    # Mock the handle_external_episode function to ensure it gets called
    wrapper_state.memory_system.handle_external_episode = mocker.AsyncMock()

    payload = {
        "session_id": "test_sandwich_session",
        "agent_id": "sandwich-orchestrator",
        "final_state": {
            "prompt": "Test prompt",
            "drafts": ["draft 1", "draft 2"],
            "solver_iis_logs": [],
            "final_routing_parameters": {"strategy": "default"},
        },
        "metadata": {"status": "success", "duration_seconds": 12.5, "solver_attempts": 2},
    }

    headers = {"traceparent": "00-1234567890abcdef1234567890abcdef-1234567890abcdef-01"}

    response = test_client.post("/v1/memory/episode/consolidate", json=payload, headers=headers)

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}

    # The BackgroundTask should have executed the handoff logic
    wrapper_state.memory_system.handle_external_episode.assert_called_once_with(
        session_id="test_sandwich_session",
        agent_id="sandwich-orchestrator",
        final_state=payload["final_state"],
        metadata=payload["metadata"],
    )
