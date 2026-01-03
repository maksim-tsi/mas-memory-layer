import pytest
from unittest.mock import AsyncMock, MagicMock
from src.memory.engines.fact_extractor import FactExtractor
from src.utils.llm_client import LLMClient, LLMResponse
from src.memory.models import FactType, FactCategory

@pytest.fixture
def mock_llm_client():
    client = MagicMock(spec=LLMClient)
    client.generate = AsyncMock()
    return client

@pytest.fixture
def extractor(mock_llm_client):
    return FactExtractor(llm_client=mock_llm_client)

@pytest.mark.asyncio
async def test_extract_facts_llm_success(extractor, mock_llm_client):
    # Mock LLM response
    mock_response = LLMResponse(
        text='''
        {
            "facts": [
                {
                    "content": "User prefers dark mode",
                    "type": "preference",
                    "category": "personal",
                    "certainty": 0.9,
                    "impact": 0.8
                }
            ]
        }
        ''',
        provider="test_provider"
    )
    mock_llm_client.generate.return_value = mock_response

    facts = await extractor.extract_facts("I prefer dark mode", metadata={"session_id": "123"})
    
    assert len(facts) == 1
    assert facts[0].content == "User prefers dark mode"
    assert facts[0].fact_type == FactType.PREFERENCE
    assert facts[0].fact_category == FactCategory.PERSONAL
    assert facts[0].session_id == "123"
    assert facts[0].source_type == "llm_extraction"

@pytest.mark.asyncio
async def test_extract_facts_llm_failure_fallback(extractor, mock_llm_client):
    # Mock LLM failure
    mock_llm_client.generate.side_effect = Exception("LLM Error")

    # Test fallback rule for email
    text = "Contact me at test@example.com"
    facts = await extractor.extract_facts(text, metadata={"session_id": "123"})
    
    assert len(facts) == 1
    assert "test@example.com" in facts[0].content
    assert facts[0].fact_type == FactType.ENTITY
    assert facts[0].source_type == "rule_fallback"

@pytest.mark.asyncio
async def test_extract_facts_empty_input(extractor):
    facts = await extractor.extract_facts("")
    assert len(facts) == 0

@pytest.mark.asyncio
async def test_extract_facts_invalid_json_fallback(extractor, mock_llm_client):
    # Mock invalid JSON response
    mock_response = LLMResponse(
        text='Invalid JSON',
        provider="test_provider"
    )
    mock_llm_client.generate.return_value = mock_response

    # Should fall back to rules
    text = "I love coding"
    facts = await extractor.extract_facts(text, metadata={"session_id": "123"})
    
    assert len(facts) == 1
    assert "I love coding" in facts[0].content
    assert facts[0].fact_type == FactType.PREFERENCE
    assert facts[0].source_type == "rule_fallback"
