"""Tests for RAGAgent implementation."""

import pytest

from src.agents.models import RunTurnRequest
from src.agents.rag_agent import RAGAgent
from src.utils.llm_client import LLMResponse


@pytest.fixture
def llm_client(mocker):
    """Provide a stub LLM client."""
    client = mocker.Mock()
    client.generate = mocker.AsyncMock(return_value=LLMResponse(text="Here are the details.", provider="stub"))
    client.available_providers = mocker.Mock(return_value=["stub"])
    return client


@pytest.fixture
def vector_store(mocker):
    """Provide a stub vector store client."""
    store = mocker.Mock()
    store.add_documents = mocker.Mock()
    store.query_similar = mocker.Mock(return_value=[{"content": "Order #42 is pending."}])
    return store


@pytest.fixture
def memory_system(mocker, vector_store):
    """Provide a stub memory system with knowledge manager."""
    memory = mocker.Mock()
    knowledge_manager = mocker.Mock()
    knowledge_manager.vector_store = vector_store
    memory.knowledge_manager = knowledge_manager
    return memory


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_agent_run_turn_indexes_and_queries(llm_client, memory_system, vector_store):
    """Ensure RAGAgent indexes the turn and uses retrievals in prompt."""
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
    vector_store.add_documents.assert_called_once()
    vector_store.query_similar.assert_called_once_with(query_text=request.content, top_k=5)
    llm_client.generate.assert_called_once()

    prompt = llm_client.generate.call_args[0][0]
    assert "Order #42 is pending." in prompt
    assert "What is the status of my order?" in prompt


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_agent_health_check_reports_ready(llm_client):
    """RAGAgent health check should return status metadata."""
    agent = RAGAgent(
        agent_id="rag-agent",
        llm_client=llm_client,
        memory_system=None,
    )

    status = await agent.health_check()

    assert status["status"] == "healthy"
    assert status["agent_id"] == "rag-agent"
    assert status["llm_providers"] == ["stub"]
