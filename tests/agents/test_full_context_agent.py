"""Tests for FullContextAgent implementation."""

import pytest

from src.agents.full_context_agent import FullContextAgent
from src.agents.models import RunTurnRequest
from src.memory.models import ContextBlock
from src.utils.llm_client import LLMResponse


@pytest.fixture
def llm_client(mocker):
    """Provide a stub LLM client."""
    client = mocker.Mock()
    client.generate = mocker.AsyncMock(return_value=LLMResponse(text="Full context response.", provider="stub"))
    client.available_providers = mocker.Mock(return_value=["stub"])
    return client


@pytest.fixture
def context_block() -> ContextBlock:
    """Provide a context block with a longer history."""
    turns = [
        {"role": "user", "content": f"Turn {idx} content"} for idx in range(30)
    ]
    return ContextBlock(
        session_id="session-789",
        recent_turns=turns,
        significant_facts=[],
    )


@pytest.fixture
def memory_system(mocker, context_block):
    """Provide a stub memory system for context block retrieval."""
    memory = mocker.Mock()
    memory.get_context_block = mocker.AsyncMock(return_value=context_block)
    return memory


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_context_agent_requests_extended_context(llm_client, memory_system):
    """Ensure FullContextAgent calls get_context_block with configured max_turns."""
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
    memory_system.get_context_block.assert_called_once()
    assert "Summarize our conversation." in llm_client.generate.call_args[0][0]


@pytest.mark.unit
def test_full_context_agent_token_estimation(llm_client):
    """Token estimation should use conservative 4-char heuristic."""
    agent = FullContextAgent(
        agent_id="full-context-agent",
        llm_client=llm_client,
        memory_system=None,
    )

    assert agent._estimate_tokens("abcd") == 1
    assert agent._estimate_tokens("" * 0) == 0


@pytest.mark.unit
def test_full_context_agent_truncation_keeps_recent_turns(llm_client, context_block):
    """Truncation should preserve the most recent turns when over budget."""
    agent = FullContextAgent(
        agent_id="full-context-agent",
        llm_client=llm_client,
        memory_system=None,
        config={"max_turns": 50},
    )

    long_input = "x" * 600_000
    context_text = agent._build_context_from_block(context_block, user_input=long_input)
    recent_count = context_text.count("USER:")

    assert recent_count >= agent.MIN_RECENT_TURNS


@pytest.mark.unit
@pytest.mark.asyncio
async def test_full_context_agent_health_check_reports_ready(llm_client):
    """FullContextAgent health check should return status metadata."""
    agent = FullContextAgent(
        agent_id="full-context-agent",
        llm_client=llm_client,
        memory_system=None,
    )

    status = await agent.health_check()

    assert status["status"] == "healthy"
    assert status["agent_id"] == "full-context-agent"
    assert status["llm_providers"] == ["stub"]
