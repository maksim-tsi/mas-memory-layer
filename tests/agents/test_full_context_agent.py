"""Tests for FullContextAgent implementation."""

import pytest

from src.agents.full_context_agent import FullContextAgent
from src.agents.models import RunTurnRequest
from src.memory.models import ContextBlock
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
    """Stub memory system for context block retrieval."""

    def __init__(self, context_block: ContextBlock) -> None:
        self.context_block = context_block
        self.calls = []

    async def get_context_block(
        self,
        session_id: str,
        min_ciar: float,
        max_turns: int,
        max_facts: int,
    ) -> ContextBlock:
        self.calls.append(
            {
                "session_id": session_id,
                "min_ciar": min_ciar,
                "max_turns": max_turns,
                "max_facts": max_facts,
            }
        )
        return self.context_block


@pytest.mark.asyncio
async def test_full_context_agent_requests_extended_context():
    """Ensure FullContextAgent calls get_context_block with configured max_turns."""
    context_block = ContextBlock(
        session_id="session-789",
        recent_turns=[{"role": "user", "content": "Hello"}],
        significant_facts=[],
    )

    llm_client = StubLLMClient(text="Full context response.")
    memory_system = StubMemorySystem(context_block=context_block)

    agent = FullContextAgent(
        agent_id="full-context-agent",
        llm_client=llm_client,
        memory_system=memory_system,
        config={"max_turns": 50},
    )

    request = RunTurnRequest(
        session_id="session-789",
        role="user",
        content="Summarize our conversation.",
        turn_id=3,
    )

    response = await agent.run_turn(request)

    assert response.content == "Full context response."
    assert memory_system.calls
    assert memory_system.calls[0]["max_turns"] == 50
    prompt = llm_client.prompts[0]
    assert "Summarize our conversation." in prompt


@pytest.mark.asyncio
async def test_full_context_agent_health_check_reports_ready():
    """FullContextAgent health check should return status metadata."""
    llm_client = StubLLMClient(text="Ready")

    agent = FullContextAgent(
        agent_id="full-context-agent",
        llm_client=llm_client,
        memory_system=None,
    )

    status = await agent.health_check()

    assert status["status"] == "healthy"
    assert status["agent_id"] == "full-context-agent"
    assert status["llm_providers"] == ["stub"]
