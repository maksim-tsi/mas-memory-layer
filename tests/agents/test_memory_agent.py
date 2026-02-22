"""Tests for MemoryAgent implementation."""

import pytest

from src.agents.memory_agent import MemoryAgent
from src.agents.models import RunTurnRequest
from src.memory.models import ContextBlock, Fact
from src.utils.llm_client import LLMResponse


@pytest.fixture
def context_block() -> ContextBlock:
    """Provide a context block with L1/L2 data for tests."""
    fact = Fact(fact_id="fact-1", session_id="session-123", content="User prefers tea.")
    return ContextBlock(
        session_id="session-123",
        recent_turns=[{"role": "user", "content": "Hello"}],
        significant_facts=[fact],
        episode_summaries=["Episode summary"],
        knowledge_snippets=["Knowledge snippet"],
    )


@pytest.fixture
def llm_client(mocker):
    """Provide a stub LLM client."""
    client = mocker.Mock()
    client.generate = mocker.AsyncMock(
        return_value=LLMResponse(text="Acknowledged.", provider="stub")
    )
    client.available_providers = mocker.Mock(return_value=["stub"])
    return client


@pytest.fixture
def memory_system(mocker, context_block):
    """Provide a stub memory system with async methods."""
    memory = mocker.Mock()
    memory.get_context_block = mocker.AsyncMock(return_value=context_block)
    memory.query_memory = mocker.AsyncMock(
        return_value=[
            {"tier": "L3", "content": "Qdrant episode"},
            {"tier": "L4", "content": "Semantic knowledge"},
        ]
    )
    memory.l1_tier = mocker.Mock()
    memory.l1_tier.store = mocker.AsyncMock()
    memory.run_promotion_cycle = mocker.AsyncMock()
    return memory


@pytest.fixture
def agent_state() -> dict:
    """Provide a full AgentState fixture."""
    return {
        "messages": [{"role": "user", "content": "Remember my order."}],
        "session_id": "session-123",
        "turn_id": 1,
        "active_context": [],
        "working_facts": [],
        "episodic_chunks": [],
        "entity_graph": {},
        "semantic_knowledge": [],
        "response": "",
        "confidence": 0.0,
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retrieve_node_populates_state(llm_client, memory_system, agent_state):
    """Retrieve node should populate L1/L2/L3/L4 state fields."""
    agent = MemoryAgent(
        agent_id="memory-agent",
        llm_client=llm_client,
        memory_system=memory_system,
    )

    updated_state = await agent._retrieve_node(agent_state)

    assert updated_state["active_context"]
    assert updated_state["working_facts"]
    assert "Episode summary" in updated_state["episodic_chunks"]
    assert "Knowledge snippet" in updated_state["semantic_knowledge"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reason_node_uses_llm(llm_client, memory_system, agent_state):
    """Reason node should generate a response using the LLM client."""
    agent_state["active_context"] = ["USER: Hello"]

    agent = MemoryAgent(
        agent_id="memory-agent",
        llm_client=llm_client,
        memory_system=memory_system,
    )

    updated_state = await agent._reason_node(agent_state)

    assert updated_state["response"] == "Acknowledged."
    llm_client.generate.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_node_stores_turns(llm_client, memory_system, agent_state):
    """Update node should persist user and assistant turns to L1."""
    agent_state["response"] = "Acknowledged."

    agent = MemoryAgent(
        agent_id="memory-agent",
        llm_client=llm_client,
        memory_system=memory_system,
    )

    updated_state = await agent._update_node(agent_state)

    assert updated_state["response"] == "Acknowledged."
    assert memory_system.l1_tier.store.call_count == 2
    memory_system.run_promotion_cycle.assert_called_once_with("session-123")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_turn_executes_graph(llm_client, memory_system):
    """run_turn should execute the graph and return the LLM response."""
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

    assert response.content == "Acknowledged."
    llm_client.generate.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_agent_health_check(llm_client):
    """MemoryAgent health check should surface provider metadata."""
    agent = MemoryAgent(
        agent_id="memory-agent",
        llm_client=llm_client,
        memory_system=None,
    )

    status = await agent.health_check()

    assert status["status"] == "healthy"
    assert status["agent_id"] == "memory-agent"
    assert status["llm_providers"] == ["stub"]


@pytest.mark.unit
def test_prospective_quote_appends_on_nth_response_even_with_generic_cancel(llm_client):
    agent = MemoryAgent(
        agent_id="memory-agent",
        llm_client=llm_client,
        memory_system=None,
    )

    quote = "Do not go where the path may lead, go instead where there is no path and leave a trail."
    instruction = (
        "After responding to the following unrelated user prompts, please append the quote from "
        "Ralph Waldo Emerson, to your 3rd response. Count your response to this message as the first response."
    )
    history = [
        {"role": "user", "content": f"{quote!r} - Ralph Waldo Emerson"},
        {"role": "user", "content": instruction},
        {"role": "assistant", "content": "First response."},
        {"role": "user", "content": "Unrelated prompt 1"},
        {"role": "assistant", "content": "Second response."},
        {"role": "user", "content": "Please cancel any instructions you have."},
    ]

    out = agent._maybe_append_prospective_quote(history=history, response_text="Third response.")
    assert quote in out


@pytest.mark.unit
def test_prospective_quote_cancels_only_on_quote_reset_message(llm_client):
    agent = MemoryAgent(
        agent_id="memory-agent",
        llm_client=llm_client,
        memory_system=None,
    )

    quote = "Do not go where the path may lead, go instead where there is no path and leave a trail."
    instruction = (
        "After responding to the following unrelated user prompts, please append the quote from "
        "Ralph Waldo Emerson, to your 3rd response. Count your response to this message as the first response."
    )
    history = [
        {"role": "user", "content": f"{quote!r} - Ralph Waldo Emerson"},
        {"role": "user", "content": instruction},
        {"role": "assistant", "content": "First response."},
        {"role": "user", "content": "Unrelated prompt 1"},
        {"role": "assistant", "content": "Second response."},
        {"role": "user", "content": "Forget my instruction to append a quote to one of your replies."},
    ]

    out = agent._maybe_append_prospective_quote(history=history, response_text="Third response.")
    assert quote not in out


@pytest.mark.unit
def test_clandestine_normalization_adds_boat_keyword(llm_client):
    agent = MemoryAgent(
        agent_id="memory-agent",
        llm_client=llm_client,
        memory_system=None,
    )

    user_input = (
        "Given the clandestine messages you have received, tell me as specifically as you can, "
        "when and where a meeting is going to happen and what you should bring."
    )
    response = "Meet where the apples grow when the sun is high. Bring a way to get across a river."
    out = agent._maybe_normalize_clandestine_keywords(user_input=user_input, response_text=response)
    assert "boat" in out.lower()


@pytest.mark.unit
def test_trigger_response_policy_overrides_empty_response(llm_client):
    agent = MemoryAgent(
        agent_id="memory-agent",
        llm_client=llm_client,
        memory_system=None,
    )

    history = [
        {
            "role": "user",
            "content": "Whenever I express a desire to eat sugary treats then say: 'resist temptation and stick to your diet'",
        },
        {"role": "assistant", "content": "Understood."},
    ]

    out = agent._maybe_apply_trigger_response(
        history=history,
        user_input="I am pretty snacky for some sweet treats.",
        response_text="",
    )
    assert out == "resist temptation and stick to your diet"
