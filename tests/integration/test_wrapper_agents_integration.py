"""Integration tests for the MAS FastAPI wrapper with real storage backends."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
import os
import sys
import types
import uuid

import pytest
from fastapi.testclient import TestClient

from src.agents.models import RunTurnResponse


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
class _IntegrationConfig:
    agent_type: str
    port: int
    session_prefix: str


def _require_integration_env() -> None:
    if not os.environ.get("REDIS_URL"):
        pytest.skip("REDIS_URL not set; integration tests require Redis.")
    if not os.environ.get("POSTGRES_URL"):
        pytest.skip("POSTGRES_URL not set; integration tests require PostgreSQL.")


def _build_config(agent_type: str, port: int) -> agent_wrapper.WrapperConfig:
    return agent_wrapper.WrapperConfig(
        agent_type=agent_type,
        port=port,
        model="gemini-2.5-flash-lite",
        redis_url=os.environ["REDIS_URL"],
        postgres_url=os.environ["POSTGRES_URL"],
        session_prefix=agent_wrapper.SESSION_PREFIXES[agent_type],
        window_size=10,
        ttl_hours=24,
        min_ciar=0.6,
    )


def _patch_agent_for_tests(state, mocker: pytest.MockFixture) -> None:
    async def _run_turn(request):
        return RunTurnResponse(
            session_id=request.session_id,
            role="assistant",
            content="Integration response.",
            turn_id=request.turn_id,
            metadata={"source": "integration"},
            timestamp=datetime.now(timezone.utc),
        )

    state.agent.run_turn = mocker.AsyncMock(side_effect=_run_turn)
    state.agent.health_check = mocker.AsyncMock(return_value={"status": "ok"})


@pytest.mark.integration
def test_full_wrapper_session_isolation(redis_key_validator, mocker):
    """Ensure full sessions do not leak keys into rag/full_context namespaces."""
    _require_integration_env()

    config = _build_config("full", 8080)
    app = agent_wrapper.create_app(config)

    with TestClient(app) as client:
        _patch_agent_for_tests(client.app.state.wrapper, mocker)
        session_id = f"test-session-{uuid.uuid4().hex}"
        payload = {
            "session_id": session_id,
            "role": "user",
            "content": "Hello",
            "turn_id": 0,
        }
        response = client.post("/run_turn", json=payload)
        assert response.status_code == 200

    prefixed_id = f"full:{session_id}"
    redis_key_validator(f"l1:session:{prefixed_id}", expected_count=1)
    redis_key_validator(f"l1:session:rag:{session_id}", expected_count=0)
    redis_key_validator(f"l1:session:full_context:{session_id}", expected_count=0)

    with TestClient(app) as client:
        cleanup = client.post("/cleanup_force", params={"session_id": session_id})
        assert cleanup.status_code == 200


@pytest.mark.integration
def test_parallel_wrapper_startup_health(mocker):
    """Ensure wrapper instances for all agent types start and report health."""
    _require_integration_env()

    configs = [
        _IntegrationConfig("full", 8080, "full"),
        _IntegrationConfig("rag", 8081, "rag"),
        _IntegrationConfig("full_context", 8082, "full_context"),
    ]

    with ExitStack() as stack:
        clients = {}
        for entry in configs:
            config = _build_config(entry.agent_type, entry.port)
            app = agent_wrapper.create_app(config)
            client = stack.enter_context(TestClient(app))
            _patch_agent_for_tests(client.app.state.wrapper, mocker)
            clients[entry.agent_type] = client

        for agent_type, client in clients.items():
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] in {"ok", "degraded"}
            assert response.json()["agent"] == {"status": "ok"}
