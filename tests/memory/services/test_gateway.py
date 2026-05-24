import pytest

from src.memory.services import MemoryGatewayService, PermissionPolicy, ScopeEnvelope
from src.memory.services.permissions import YAAMPermissionError


@pytest.mark.asyncio
async def test_query_memory_normalizes_unified_results(mocker) -> None:
    memory_system = mocker.Mock()
    memory_system.query_memory = mocker.AsyncMock(
        return_value=[
            {
                "content": "Crane maintenance affects dock three.",
                "tier": "L2",
                "score": 0.7,
                "metadata": {"fact_id": "fact-a", "api_token": "secret"},
            }
        ]
    )
    service = MemoryGatewayService(memory_system)
    scope = ScopeEnvelope(session_id="session-a", agent_id="agent-a")

    results = await service.query_memory(scope, query="dock status", limit=1)

    assert len(results) == 1
    assert results[0].source_id == "fact-a"
    assert results[0].metadata["api_token"] == "[REDACTED]"
    memory_system.query_memory.assert_awaited_once()


@pytest.mark.asyncio
async def test_store_l2_fact_denies_writes_by_default(mocker) -> None:
    memory_system = mocker.Mock()
    memory_system.l2_tier = mocker.Mock()
    service = MemoryGatewayService(memory_system)
    scope = ScopeEnvelope(session_id="session-a", agent_id="agent-a")

    with pytest.raises(YAAMPermissionError):
        await service.store_l2_fact(scope, content="A scoped fact.")


@pytest.mark.asyncio
async def test_store_l2_fact_persists_when_allowlisted(mocker) -> None:
    l2_tier = mocker.Mock()
    l2_tier.store = mocker.AsyncMock(return_value="fact-stored")
    memory_system = mocker.Mock()
    memory_system.l2_tier = l2_tier
    service = MemoryGatewayService(
        memory_system,
        PermissionPolicy(
            enable_writes=True,
            allowlisted_tools=frozenset({"yaam.l2.store_fact"}),
        ),
    )
    scope = ScopeEnvelope(session_id="session-a", agent_id="agent-a", task_id="task-a")

    ack = await service.store_l2_fact(
        scope,
        content="A scoped fact.",
        metadata={"password": "secret", "source": "test"},
    )

    assert ack.created_id == "fact-stored"
    assert ack.provenance is not None
    assert ack.provenance.agent_id == "agent-a"
    stored_fact = l2_tier.store.await_args.args[0]
    assert stored_fact.session_id == "session-a"
    assert stored_fact.metadata["password"] == "[REDACTED]"
    assert stored_fact.metadata["task_id"] == "task-a"


@pytest.mark.asyncio
async def test_health_check_redacts_tier_health(mocker) -> None:
    l2_tier = mocker.Mock()
    l2_tier.health_check = mocker.AsyncMock(
        return_value={"status": "ok", "connection_token": "secret"}
    )
    memory_system = mocker.Mock()
    memory_system.l1_tier = None
    memory_system.l2_tier = l2_tier
    memory_system.l3_tier = None
    memory_system.l4_tier = None
    service = MemoryGatewayService(memory_system)

    health = await service.health_check()

    assert health.status == "ok"
    assert health.tiers["L2"]["connection_token"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_get_fact_allows_wildcard_resource_scope(mocker) -> None:
    l2_tier = mocker.Mock()
    l2_tier.retrieve = mocker.AsyncMock(
        return_value=mocker.Mock(
            fact_id="fact-a",
            session_id="session-a",
            content="A scoped fact.",
            ciar_score=0.9,
            metadata={},
            extracted_at=None,
            created_at=None,
        )
    )
    memory_system = mocker.Mock()
    memory_system.l2_tier = l2_tier
    service = MemoryGatewayService(memory_system)

    result = await service.get_fact(ScopeEnvelope(session_id="*", agent_id="reader"), "fact-a")

    assert result is not None
    assert result.source_id == "fact-a"
