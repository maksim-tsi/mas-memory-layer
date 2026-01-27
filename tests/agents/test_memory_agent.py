"""Tests for MemoryAgent implementation."""

import pytest

from src.agents.memory_agent import MemoryAgent
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
async def test_memory_agent_run_turn_uses_context_block():
    """Ensure MemoryAgent builds a prompt with context and uses the LLM client."""
    context_block = ContextBlock(
        session_id="session-123",
        recent_turns=[{"role": "user", "content": "Hello"}],
        significant_facts=[],
    )

    llm_client = StubLLMClient(text="Acknowledged.")
    memory_system = StubMemorySystem(context_block=context_block)

    agent = MemoryAgent(
        agent_id="memory-agent",
        llm_client=llm_client,
        memory_system=memory_system,
    )

    request = RunTurnRequest(
        session_id="session-123",
        role="user",
        content="Remember my order.",
        turn_id=1,
    )

    response = await agent.run_turn(request)

    assert response.session_id == "session-123"
    assert response.role == "assistant"
    assert response.content == "Acknowledged."

    assert memory_system.calls
    assert llm_client.prompts
    prompt = llm_client.prompts[0]
    assert "Recent Conversation" in prompt
    assert "Remember my order." in prompt


@pytest.mark.asyncio
async def test_memory_agent_health_check_reports_ready():
    """MemoryAgent health check should return status metadata."""
    llm_client = StubLLMClient(text="Ready")

    agent = MemoryAgent(
        agent_id="memory-agent",
        llm_client=llm_client,
        memory_system=None,
    )

    status = await agent.health_check()

    assert status["status"] == "healthy"
    assert status["agent_id"] == "memory-agent"
    assert status["llm_providers"] == ["stub"]
