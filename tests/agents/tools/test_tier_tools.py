"""Tests for tier-specific memory tools."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from src.agents.tools.tier_tools import (
    L2SearchFactsInput,
    L3SearchEpisodesInput,
    L4SearchKnowledgeInput,
    l2_search_facts,
    l3_query_graph,
    l3_search_episodes,
    l4_search_knowledge,
)
from src.memory.models import Episode, Fact, KnowledgeDocument


@dataclass
class MockContext:
    """Mock runtime context for tool tests."""

    session_id: str = "session-123"
    memory_system: object | None = None


@dataclass
class MockToolRuntime:
    """Mock LangChain tool runtime for direct coroutine calls."""

    context: object
    state: dict

    async def stream_status(self, _status: str) -> None:
        return None


class TestTierToolMetadata:
    """Metadata sanity checks for tier tools."""

    def test_l2_search_facts_metadata(self):
        assert l2_search_facts.name == "l2_search_facts"
        assert l2_search_facts.args_schema == L2SearchFactsInput

    def test_l3_search_episodes_metadata(self):
        assert l3_search_episodes.name == "l3_search_episodes"
        assert l3_search_episodes.args_schema == L3SearchEpisodesInput

    def test_l4_search_knowledge_metadata(self):
        assert l4_search_knowledge.name == "l4_search_knowledge"
        assert l4_search_knowledge.args_schema == L4SearchKnowledgeInput


@pytest.mark.asyncio
class TestTierTools:
    """Behavior checks with mocked runtime context."""

    async def test_l2_search_facts_uses_l2_tier_runtime_attr(self, mocker):
        l2_tier = mocker.Mock()
        l2_tier.ciar_threshold = 0.6
        l2_tier.search_facts = mocker.AsyncMock(
            return_value=[
                Fact(fact_id="fact-1", session_id="session-123", content="Tea preference")
            ]
        )
        memory_system = type("MemorySystem", (), {"l2_tier": l2_tier})()
        runtime = MockToolRuntime(context=MockContext(memory_system=memory_system), state={})

        result = await l2_search_facts.coroutine(query="tea", runtime=runtime)
        payload = json.loads(result)

        assert payload["results_count"] == 1
        l2_tier.search_facts.assert_awaited_once_with(
            query="tea",
            session_id="session-123",
            min_ciar=None,
            limit=20,
        )

    async def test_l3_query_graph_uses_l3_tier_runtime_attr(self, mocker):
        l3_tier = mocker.Mock()
        l3_tier.query_graph = mocker.AsyncMock(return_value=[{"episode_id": "episode-1"}])
        memory_system = type("MemorySystem", (), {"l3_tier": l3_tier})()
        runtime = MockToolRuntime(context=MockContext(memory_system=memory_system), state={})

        template = mocker.Mock()
        template.merge_params.return_value = {"container_id": "MAEU1234567"}
        mocker.patch(
            "src.agents.tools.tier_tools.validate_and_execute_template",
            return_value=(True, "", "MATCH (n) RETURN n"),
        )
        mocker.patch("src.agents.tools.tier_tools.get_template", return_value=template)

        result = await l3_query_graph.coroutine(
            template_name="get_container_journey",
            parameters={"container_id": "MAEU1234567"},
            runtime=runtime,
        )
        payload = json.loads(result)

        assert payload["results_count"] == 1
        l3_tier.query_graph.assert_awaited_once_with(
            cypher_query="MATCH (n) RETURN n",
            parameters={"container_id": "MAEU1234567"},
        )

    async def test_l3_search_episodes_executes_embedding_search(self, mocker):
        llm_client = mocker.Mock()
        llm_client.get_embedding = mocker.AsyncMock(return_value=[0.1, 0.2, 0.3])

        episode = Episode(
            episode_id="episode-1",
            session_id="session-123",
            summary="Container delay at port due to customs hold.",
            narrative="A shipment was delayed at the port during customs clearance.",
            source_fact_ids=["fact-1"],
            fact_count=1,
            time_window_start=datetime(2026, 3, 10, 9, 0, tzinfo=UTC),
            time_window_end=datetime(2026, 3, 10, 10, 0, tzinfo=UTC),
            fact_valid_from=datetime(2026, 3, 10, 9, 0, tzinfo=UTC),
            source_observation_timestamp=datetime(2026, 3, 10, 9, 0, tzinfo=UTC),
            importance_score=0.8,
            topics=["delay", "customs"],
        )
        episode.metadata["similarity_score"] = 0.91

        l3_tier = mocker.Mock()
        l3_tier.search_similar = mocker.AsyncMock(return_value=[episode])
        memory_system = type("MemorySystem", (), {"l3_tier": l3_tier, "llm_client": llm_client})()
        runtime = MockToolRuntime(context=MockContext(memory_system=memory_system), state={})

        result = await l3_search_episodes.coroutine(
            query="customs port delay",
            limit=5,
            filters={"topic": "delay", "session_id": "other-session"},
            runtime=runtime,
        )
        payload = json.loads(result)

        assert payload["results_count"] == 1
        assert payload["filters"]["session_id"] == "session-123"
        assert payload["episodes"][0]["similarity_score"] == 0.91
        llm_client.get_embedding.assert_awaited_once_with("customs port delay")
        l3_tier.search_similar.assert_awaited_once_with(
            query_embedding=[0.1, 0.2, 0.3],
            limit=5,
            filters={"topic": "delay", "session_id": "session-123"},
        )

    async def test_l4_search_knowledge_uses_l4_tier_runtime_attr(self, mocker):
        document = KnowledgeDocument(
            knowledge_id="knowledge-1",
            title="Delay pattern",
            content="Customs delays increase when documentation arrives incomplete.",
            knowledge_type="pattern",
            confidence_score=0.84,
            episode_count=3,
            category="delays",
            tags=["customs", "documentation"],
            distilled_at=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
        )
        document.metadata["search_score"] = 42.0

        l4_tier = mocker.Mock()
        l4_tier.search = mocker.AsyncMock(return_value=[document])
        memory_system = type("MemorySystem", (), {"l4_tier": l4_tier})()
        runtime = MockToolRuntime(context=MockContext(memory_system=memory_system), state={})

        result = await l4_search_knowledge.coroutine(
            query="customs delay",
            filters={"category": "delays"},
            limit=3,
            runtime=runtime,
        )
        payload = json.loads(result)

        assert payload["results_count"] == 1
        assert payload["documents"][0]["distilled_at"] == "2026-03-10T12:00:00+00:00"
        assert payload["documents"][0]["search_score"] == 42.0
        l4_tier.search.assert_awaited_once_with(
            query_text="customs delay",
            filters={"category": "delays"},
            limit=3,
        )
