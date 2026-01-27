"""Tests for RAGAgent implementation."""

import pytest

from src.agents.models import RunTurnRequest
from src.agents.rag_agent import RAGAgent
from src.utils.llm_client import LLMResponse


class StubLLMClient:
    """Stub LLM client for agent tests."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.prompts = []

    async def generate(self, prompt: str, model: str | None = None) -> LLMResponse:
        self.prompts.append(prompt)
        return LLMResponse(text=self._text, provider="stub", model=model)

    def available_providers(self) -> list[str]:
        return ["stub"]


class StubMemorySystem:
    """Stub memory system for retrieval queries."""

    def __init__(self, retrievals: list[dict[str, str]]) -> None:
        self.retrievals = retrievals
        self.calls = []

    async def query_memory(self, session_id: str, query: str, limit: int) -> list[dict[str, str]]:
        self.calls.append({"session_id": session_id, "query": query, "limit": limit})
        return self.retrievals


@pytest.mark.asyncio
async def test_rag_agent_run_turn_queries_memory():
    """Ensure RAGAgent queries memory and uses retrievals in prompt."""
    llm_client = StubLLMClient(text="Here are the details.")
    memory_system = StubMemorySystem(retrievals=[{"content": "Order #42 is pending."}])

    agent = RAGAgent(
        agent_id="rag-agent",
        llm_client=llm_client,
        memory_system=memory_system,
        config={"top_k": 5},
    )

    request = RunTurnRequest(
        session_id="session-456",
        role="user",
        content="What is the status of my order?",
        turn_id=2,
    )

    response = await agent.run_turn(request)

    assert response.content == "Here are the details."
    assert memory_system.calls
    assert llm_client.prompts
    prompt = llm_client.prompts[0]
    assert "Order #42 is pending." in prompt
    assert "What is the status of my order?" in prompt


@pytest.mark.asyncio
async def test_rag_agent_health_check_reports_ready():
    """RAGAgent health check should return status metadata."""
    llm_client = StubLLMClient(text="Ready")

    agent = RAGAgent(
        agent_id="rag-agent",
        llm_client=llm_client,
        memory_system=None,
    )

    status = await agent.health_check()

    assert status["status"] == "healthy"
    assert status["agent_id"] == "rag-agent"
    assert status["llm_providers"] == ["stub"]
