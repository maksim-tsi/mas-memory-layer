import httpx
import pytest
from fastapi import FastAPI

from src.api.v2_router import router
from src.evaluation.agent_wrapper import AgentWrapperState
from src.memory.ciar_formula import calculate_ciar_score


@pytest.mark.asyncio
async def test_v2_l2_store_uses_consistent_ciar_components(mocker):
    """The v2 semantic L2 store route should not create contradictory CIAR data."""
    captured = {}
    l2_tier = mocker.Mock()

    async def store_fact(fact):
        captured["fact"] = fact
        return fact.fact_id

    l2_tier.store = mocker.AsyncMock(side_effect=store_fact)
    l2_tier.query_by_session = mocker.AsyncMock(return_value=[])

    app = FastAPI()
    app.include_router(router)
    app.state.wrapper = AgentWrapperState(
        agent=mocker.Mock(),
        memory_system=mocker.Mock(),
        l1_tier=mocker.Mock(),
        l2_tier=l2_tier,
        redis_client=mocker.Mock(),
        agent_type="test",
        agent_variant="test",
        session_prefix="test",
        rate_limiter=mocker.Mock(),
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v2/memory/l2/facts",
            json={
                "session_id": "session-1",
                "task_id": "task-1",
                "agent_id": "agent-1",
                "action": "store",
                "content": "Important semantic memory assertion.",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    l2_tier.store.assert_awaited_once()

    fact = captured["fact"]
    expected = calculate_ciar_score(
        fact.certainty,
        fact.impact,
        fact.age_decay,
        fact.recency_boost,
    )
    assert fact.ciar_score == expected == 1.0
    assert fact.metadata["agent_id"] == "agent-1"
    assert fact.metadata["task_id"] == "task-1"
    assert fact.metadata["ciar_score_source"] == "v2_semantic_store"
