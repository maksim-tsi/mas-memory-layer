"""Tests for query-aware cross-tier retrieval in UnifiedMemorySystem."""

from datetime import UTC, datetime

import pytest

from src.memory.models import Episode, Fact, KnowledgeDocument, SearchWeights
from src.memory.unified_memory_system import UnifiedMemorySystem


def _build_episode(episode_id: str, summary: str, similarity_score: float) -> Episode:
    episode = Episode(
        episode_id=episode_id,
        session_id="session-123",
        summary=summary,
        fact_count=2,
        time_window_start=datetime.now(UTC),
        time_window_end=datetime.now(UTC),
        fact_valid_from=datetime.now(UTC),
        source_observation_timestamp=datetime.now(UTC),
        importance_score=0.4,
    )
    episode.metadata["similarity_score"] = similarity_score
    return episode


def _build_knowledge(knowledge_id: str, title: str, search_score: float) -> KnowledgeDocument:
    document = KnowledgeDocument(
        knowledge_id=knowledge_id,
        title=title,
        content=f"Knowledge content for {title}",
        knowledge_type="insight",
        confidence_score=0.6,
        distilled_at=datetime.now(UTC),
    )
    document.metadata["search_score"] = search_score
    return document


@pytest.mark.asyncio
async def test_query_memory_uses_query_conditioned_l3_and_l4(mocker):
    """Unified retrieval should use embedding-backed L3 and text-query L4 search paths."""
    redis_client = mocker.Mock()
    redis_client.ping.return_value = True
    knowledge_manager = mocker.Mock()

    llm_client = mocker.Mock()
    llm_client.get_embedding = mocker.AsyncMock(return_value=[0.1, 0.2, 0.3])

    l2_tier = mocker.Mock()
    l2_tier.search_facts = mocker.AsyncMock(
        return_value=[
            Fact(
                fact_id="fact-1",
                session_id="session-123",
                content="Port congestion fact",
                ciar_score=0.7,
            )
        ]
    )

    l3_tier = mocker.Mock()
    l3_tier.search_similar = mocker.AsyncMock(
        return_value=[_build_episode("ep-1", "Episode about port congestion", 0.9)]
    )
    l3_tier.query = mocker.AsyncMock(return_value=[])

    l4_tier = mocker.Mock()
    l4_tier.search = mocker.AsyncMock(return_value=[_build_knowledge("kg-1", "Port rule", 120.0)])
    l4_tier.query = mocker.AsyncMock(return_value=[])

    system = UnifiedMemorySystem(
        redis_client=redis_client,
        knowledge_manager=knowledge_manager,
        llm_client=llm_client,
        l2_tier=l2_tier,
        l3_tier=l3_tier,
        l4_tier=l4_tier,
    )

    results = await system.query_memory(
        session_id="session-123",
        query="port congestion",
        limit=5,
        weights=SearchWeights(l2_weight=0.2, l3_weight=0.4, l4_weight=0.4),
    )

    llm_client.get_embedding.assert_awaited_once_with("port congestion")
    l3_tier.search_similar.assert_awaited_once_with(
        query_embedding=[0.1, 0.2, 0.3],
        limit=5,
        filters={"session_id": "session-123"},
    )
    l4_tier.search.assert_awaited_once_with(query_text="port congestion", limit=5)
    l3_tier.query.assert_not_called()
    l4_tier.query.assert_not_called()

    assert {result["tier"] for result in results} == {"L2", "L3", "L4"}
    assert (
        results[0]["metadata"].get("similarity_score") == 0.9
        or results[0]["metadata"].get("search_score") == 120.0
    )


@pytest.mark.asyncio
async def test_query_memory_varies_with_query_input(mocker):
    """Different queries should drive different L3/L4 results."""
    redis_client = mocker.Mock()
    redis_client.ping.return_value = True
    knowledge_manager = mocker.Mock()

    async def embedding_side_effect(
        text: str, model: str | None = None, provider: str | None = None
    ):
        return [1.0] if text == "port congestion" else [2.0]

    llm_client = mocker.Mock()
    llm_client.get_embedding = mocker.AsyncMock(side_effect=embedding_side_effect)

    l3_tier = mocker.Mock()

    async def l3_side_effect(query_embedding, limit=10, filters=None):
        if query_embedding == [1.0]:
            return [_build_episode("ep-port", "Episode about port congestion", 0.9)]
        return [_build_episode("ep-stock", "Episode about safety stock", 0.9)]

    l3_tier.search_similar = mocker.AsyncMock(side_effect=l3_side_effect)

    l4_tier = mocker.Mock()

    async def l4_side_effect(query_text, filters=None, limit=10, filter_by=None):
        if query_text == "port congestion":
            return [_build_knowledge("kg-port", "Port knowledge", 100.0)]
        return [_build_knowledge("kg-stock", "Stock knowledge", 100.0)]

    l4_tier.search = mocker.AsyncMock(side_effect=l4_side_effect)

    system = UnifiedMemorySystem(
        redis_client=redis_client,
        knowledge_manager=knowledge_manager,
        llm_client=llm_client,
        l3_tier=l3_tier,
        l4_tier=l4_tier,
    )

    port_results = await system.query_memory(
        session_id="session-123",
        query="port congestion",
        limit=5,
        weights=SearchWeights(l2_weight=0.0, l3_weight=0.5, l4_weight=0.5),
    )
    stock_results = await system.query_memory(
        session_id="session-123",
        query="safety stock",
        limit=5,
        weights=SearchWeights(l2_weight=0.0, l3_weight=0.5, l4_weight=0.5),
    )

    assert [result["content"] for result in port_results] != [
        result["content"] for result in stock_results
    ]


@pytest.mark.asyncio
async def test_query_memory_skips_l3_when_llm_client_missing(mocker):
    """L3 retrieval should degrade gracefully when embeddings are unavailable."""
    redis_client = mocker.Mock()
    redis_client.ping.return_value = True
    knowledge_manager = mocker.Mock()

    l3_tier = mocker.Mock()
    l3_tier.search_similar = mocker.AsyncMock(return_value=[])

    l4_tier = mocker.Mock()
    l4_tier.search = mocker.AsyncMock(
        return_value=[_build_knowledge("kg-1", "Fallback knowledge", 80.0)]
    )

    system = UnifiedMemorySystem(
        redis_client=redis_client,
        knowledge_manager=knowledge_manager,
        llm_client=None,
        l3_tier=l3_tier,
        l4_tier=l4_tier,
    )

    results = await system.query_memory(
        session_id="session-123",
        query="fallback query",
        limit=5,
        weights=SearchWeights(l2_weight=0.0, l3_weight=0.5, l4_weight=0.5),
    )

    l3_tier.search_similar.assert_not_called()
    l4_tier.search.assert_awaited_once_with(query_text="fallback query", limit=5)
    assert len(results) == 1
    assert results[0]["tier"] == "L4"
