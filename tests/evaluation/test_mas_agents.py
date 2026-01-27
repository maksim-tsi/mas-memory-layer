"""Unit tests for GoodAI MAS agent interfaces."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def mas_agents_module():
    """Load the MAS agent module from the benchmark workspace."""
    _install_litellm_stub()
    benchmark_root = Path(__file__).resolve().parents[2] / "benchmarks" / "goodai-ltm-benchmark"
    if str(benchmark_root) not in sys.path:
        sys.path.insert(0, str(benchmark_root))
    return importlib.import_module("model_interfaces.mas_agents")


def _install_litellm_stub() -> None:
    """Provide a minimal litellm stub for benchmark imports."""
    if "litellm" in sys.modules:
        return

    litellm_stub = types.ModuleType("litellm")
    litellm_stub.modify_params = True
    litellm_stub.model_alias_map = {}
    litellm_stub.model_cost = {}
    litellm_stub.openai_key = None
    litellm_stub.anthropic_key = None

    def _token_counter(*_args, **_kwargs):
        return 1

    def _get_max_tokens(*_args, **_kwargs):
        return 0

    def _completion_cost(*_args, **_kwargs):
        return 0.0

    class _Choice:
        def __init__(self) -> None:
            self.message = types.SimpleNamespace(content="stub")

    class _Response:
        def __init__(self) -> None:
            self.choices = [_Choice()]

    def _completion(*_args, **_kwargs):
        return _Response()

    litellm_stub.token_counter = _token_counter
    litellm_stub.get_max_tokens = _get_max_tokens
    litellm_stub.completion_cost = _completion_cost
    litellm_stub.completion = _completion

    exceptions_stub = types.ModuleType("litellm.exceptions")

    class ContextWindowExceededError(Exception):
        """Stub exception used by benchmark tokenizer."""

    exceptions_stub.ContextWindowExceededError = ContextWindowExceededError

    sys.modules["litellm"] = litellm_stub
    sys.modules["litellm.exceptions"] = exceptions_stub


@pytest.fixture
def session(mas_agents_module):
    """Provide a configured MAS wrapper session."""
    return mas_agents_module.MASWrapperSession(run_name="unit-run", session_prefix="full")


@pytest.mark.unit
def test_prefixed_session_id(session):
    """Ensure session IDs are prefixed exactly once."""
    session.session_id = "abc123"
    assert session._prefixed_session_id() == "full:abc123"
    session.session_id = "full:abc123"
    assert session._prefixed_session_id() == "full:abc123"


@pytest.mark.unit
def test_reply_returns_agent_response_without_http(session):
    """Ensure reply returns provided agent response and skips HTTP calls."""
    response = session.reply("Hi", agent_response="ready")
    assert response == "ready"


@pytest.mark.unit
def test_post_with_retry_success(mocker, session):
    """Ensure successful responses return JSON without retries."""
    response = mocker.Mock()
    response.status_code = 200
    response.json.return_value = {"content": "ok"}
    mocker.patch("model_interfaces.mas_agents.requests.post", return_value=response)

    payload = {"session_id": "full:test", "role": "user", "content": "hello", "turn_id": 0}
    result = session._post_with_retry(payload)

    assert result == {"content": "ok"}


@pytest.mark.unit
def test_post_with_retry_retries_with_backoff(mocker, session):
    """Verify exponential backoff occurs when requests fail."""
    response = mocker.Mock()
    response.status_code = 200
    response.json.return_value = {"content": "ok"}

    post_mock = mocker.patch(
        "model_interfaces.mas_agents.requests.post",
        side_effect=[RuntimeError("fail"), RuntimeError("fail"), response],
    )
    sleep_mock = mocker.patch("model_interfaces.mas_agents.time.sleep")

    payload = {"session_id": "full:test", "role": "user", "content": "hello", "turn_id": 0}
    result = session._post_with_retry(payload)

    assert result == {"content": "ok"}
    assert post_mock.call_count == 3
    sleep_mock.assert_any_call(0.5)
    sleep_mock.assert_any_call(1.0)


@pytest.mark.unit
def test_post_with_retry_raises_after_max(mocker, session):
    """Ensure errors surface after exhausting retries."""
    mocker.patch(
        "model_interfaces.mas_agents.requests.post",
        side_effect=RuntimeError("fail"),
    )
    mocker.patch("model_interfaces.mas_agents.time.sleep")

    payload = {"session_id": "full:test", "role": "user", "content": "hello", "turn_id": 0}

    with pytest.raises(RuntimeError, match="Failed to call MAS wrapper"):
        session._post_with_retry(payload)


@pytest.mark.unit
def test_update_costs_noop_when_local(session, monkeypatch):
    """Ensure cost tracking is skipped for local runs."""
    session.is_local = True
    session.costs_usd = 1.0
    session._update_costs("prompt", "response")
    assert session.costs_usd == 1.0


@pytest.mark.unit
def test_update_costs_uses_token_counts(session, mocker, monkeypatch):
    """Validate cost calculation uses token counts when available."""
    session.is_local = False
    session.costs_usd = 0.0
    mocker.patch("model_interfaces.mas_agents.count_tokens_for_model", side_effect=[10, 5])
    monkeypatch.setenv("MAS_WRAPPER_COST_IN", "0.01")
    monkeypatch.setenv("MAS_WRAPPER_COST_OUT", "0.02")

    session._update_costs("prompt", "response")

    assert session.costs_usd == pytest.approx(0.2, rel=1e-3)


@pytest.mark.unit
def test_save_and_load_session(tmp_path, mas_agents_module, monkeypatch):
    """Ensure session persistence writes and reads session state."""
    interface_module = importlib.import_module("model_interfaces.interface")
    monkeypatch.setattr(interface_module, "PERSISTENCE_DIR", tmp_path)

    session = mas_agents_module.MASWrapperSession(run_name="unit-run", session_prefix="rag")
    session.session_id = "session-1"
    session.turn_id = 3
    session.endpoint = "http://localhost:8081"

    session.save_path.mkdir(parents=True, exist_ok=True)
    session.save()

    session.session_id = "session-2"
    session.turn_id = 0
    session.endpoint = "http://localhost:1234"
    session.load()

    assert session.session_id == "session-1"
    assert session.turn_id == 3
    assert session.endpoint == "http://localhost:8081"
