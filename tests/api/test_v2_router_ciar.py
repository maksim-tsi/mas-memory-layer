import httpx
import pytest
from fastapi import FastAPI

from src.api.v2_router import router
from src.evaluation.agent_wrapper import AgentWrapperState
from src.memory.ciar_formula import calculate_ciar_score
from src.memory.models import Fact


def _build_app(mocker, *, memory_system=None, l2_tier=None, l3_tier=None, l4_tier=None):
    app = FastAPI()
    app.include_router(router)
    app.state.wrapper = AgentWrapperState(
        agent=mocker.Mock(),
        memory_system=memory_system or mocker.Mock(),
        l1_tier=mocker.Mock(),
        l2_tier=l2_tier or mocker.Mock(),
        l3_tier=l3_tier,
        l4_tier=l4_tier,
        redis_client=mocker.Mock(),
        agent_type="test",
        agent_variant="test",
        session_prefix="test",
        rate_limiter=mocker.Mock(),
    )
    return app


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

    app = _build_app(mocker, l2_tier=l2_tier)

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


@pytest.mark.asyncio
async def test_v2_l2_store_preserves_traceparent_in_service_metadata(mocker):
    captured = {}
    l2_tier = mocker.Mock()

    async def store_fact(fact):
        captured["fact"] = fact
        return fact.fact_id

    l2_tier.store = mocker.AsyncMock(side_effect=store_fact)
    app = _build_app(mocker, l2_tier=l2_tier)

    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00"
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v2/memory/l2/facts",
            headers={"traceparent": traceparent},
            json={
                "session_id": "session-1",
                "task_id": "task-1",
                "agent_id": "agent-1",
                "action": "store",
                "content": "Traceable semantic memory assertion.",
            },
        )

    assert response.status_code == 200
    assert captured["fact"].metadata["traceparent"] == traceparent


@pytest.mark.asyncio
async def test_v2_l2_retrieve_keeps_legacy_fact_response_shape(mocker):
    l2_tier = mocker.Mock()
    l2_tier.query_by_session = mocker.AsyncMock(
        return_value=[
            Fact(
                fact_id="fact-1",
                session_id="session-1",
                content="Legacy clients still receive facts.",
                ciar_score=1.0,
                certainty=1.0,
                impact=1.0,
                age_decay=1.0,
                recency_boost=1.0,
                metadata={"agent_id": "agent-1"},
            )
        ]
    )
    app = _build_app(mocker, l2_tier=l2_tier)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v2/memory/l2/facts",
            json={
                "session_id": "session-1",
                "task_id": "task-1",
                "agent_id": "agent-1",
                "action": "retrieve",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["facts"][0]["fact_id"] == "fact-1"
    assert body["facts"][0]["content"] == "Legacy clients still receive facts."
    l2_tier.query_by_session.assert_awaited_once_with(session_id="session-1")


@pytest.mark.asyncio
async def test_v2_l3_assimilate_uses_shared_service_and_preserves_provider_failure_shape(
    mocker,
):
    captured = {}
    l3_tier = mocker.Mock()

    async def store_episode(episode_input):
        captured["episode_input"] = episode_input
        return "episode-stored"

    l3_tier.store = mocker.AsyncMock(side_effect=store_episode)
    memory_system = mocker.Mock()
    memory_system.l3_tier = l3_tier
    memory_system.llm_client = mocker.Mock()
    memory_system.llm_client.get_embedding = mocker.AsyncMock(return_value=[0.1] * 64)
    memory_system.llm_client.generate = mocker.AsyncMock(return_value="ok")
    app = _build_app(mocker, memory_system=memory_system, l3_tier=l3_tier)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v2/memory/l3/assimilate",
            json={
                "session_id": "session-1",
                "agent_id": "agent-1",
                "text_to_assimilate": "A durable project memory should be captured.",
                "domain_tags": ["engineering"],
            },
        )

    assert response.status_code == 201
    assert response.json() == {"status": "success", "episode_id": "episode-stored"}
    memory_system.llm_client.get_embedding.assert_awaited_once()
    memory_system.llm_client.generate.assert_awaited_once()
    assert captured["episode_input"].episode.metadata["agent_id"] == "agent-1"
    assert captured["episode_input"].entities[0]["name"] == "ExtractedEntity"

    memory_system.llm_client.get_embedding = mocker.AsyncMock(side_effect=RuntimeError("boom"))
    memory_system.llm_client.generate = mocker.AsyncMock()
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        failure = await client.post(
            "/v2/memory/l3/assimilate",
            json={
                "session_id": "session-1",
                "agent_id": "agent-1",
                "text_to_assimilate": "This provider call fails.",
                "domain_tags": [],
            },
        )

    assert failure.status_code == 502
    assert "YAAM internal LLM pipeline failed" in failure.json()["detail"]


@pytest.mark.asyncio
async def test_v2_l4_finalize_uses_shared_service_and_keeps_response_shape(mocker):
    captured = {}
    l4_tier = mocker.Mock()

    async def store_document(document):
        captured["document"] = document
        return "knowledge-stored"

    l4_tier.store = mocker.AsyncMock(side_effect=store_document)
    memory_system = mocker.Mock()
    memory_system.l4_tier = l4_tier
    app = _build_app(mocker, memory_system=memory_system, l4_tier=l4_tier)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v2/memory/l4/finalize",
            json={
                "session_id": "session-1",
                "task_id": "task-1",
                "title": "Consensus Memory",
                "final_artifact": "A sufficiently detailed final artifact.",
                "consensus_metadata": {"reviewed_by": "agent-1"},
            },
        )

    assert response.status_code == 201
    assert response.json() == {"status": "success", "knowledge_id": "knowledge-stored"}
    assert captured["document"].metadata["task_id"] == "task-1"
    assert captured["document"].metadata["agent_id"] == "rest-v2"
    assert captured["document"].metadata["reviewed_by"] == "agent-1"
