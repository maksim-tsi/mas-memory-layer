"""Integration test for verifying intelligent instruction recall."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# Redis import removed as it was unused and causing issues
from src.agents.memory_agent import MemoryAgent
from src.agents.runtime import AgentState
from src.memory.models import Fact, FactCategory, FactType


@pytest.fixture
def memory_agent():
    """Create a MemoryAgent instance with mocked dependencies."""
    # Mock LLM Client
    mock_llm = MagicMock()

    # Mock Memory System
    mock_memory = MagicMock()

    # Initialize MemoryAgent
    agent = MemoryAgent(
        agent_id="test_agent",
        llm_client=mock_llm,
        memory_system=mock_memory,
        config={"model": "test-model"},
    )
    return agent


@pytest.mark.asyncio
async def test_instruction_formatting_and_prompt_injection(memory_agent):
    """Verify that INSTRUCTION facts are correctly formatted into [ACTIVE STANDING ORDERS]."""

    # 1. Create a mock instruction fact
    instruction_fact = Fact(
        fact_id=str(uuid4()),
        session_id="test_session",
        content="When turn count is 5, say 'Bingo'.",
        fact_type=FactType.INSTRUCTION,
        fact_category=FactCategory.OPERATIONAL,
        source_uri="test",
        source_type="test",
        extracted_at=datetime.now(UTC),
        ciar_score=0.9,
    )

    # 2. Create a mock regular fact
    regular_fact = Fact(
        fact_id=str(uuid4()),
        session_id="test_session",
        content=" The sky is blue.",
        fact_type=FactType.ENTITY,
        fact_category=FactCategory.OPERATIONAL,
        source_uri="test",
        source_type="test",
        extracted_at=datetime.now(UTC),
        ciar_score=0.8,
    )

    # 3. Mock agent state with these facts
    state: AgentState = {
        "messages": [{"role": "user", "content": "Hello"}],
        "session_id": "test_session",
        "turn_id": 4,
        "working_facts": [instruction_fact, regular_fact],
        "active_context": [],
        "episodic_chunks": [],
        "semantic_knowledge": [],
        "entity_graph": {},
        "response": "",
        "confidence": 0.0,
        "metadata": {},
    }

    # 4. Generate context string
    # We need to bypass the _ensure_state_defaults if we call _format_context directly
    # or just rely on the fact that existing code passes state dict
    context_text = memory_agent._format_context(state)

    # 5. Verify [ACTIVE STANDING ORDERS] section
    assert "## [ACTIVE STANDING ORDERS]" in context_text
    assert "You MUST obey these user-defined constraints above all else:" in context_text
    assert "- When turn count is 5, say 'Bingo'." in context_text

    # 6. Verify regular facts separation
    assert "## Key Facts (Working Memory)" in context_text
    assert "1.  The sky is blue." in context_text

    # 7. Verify prompt build includes Session State
    prompt = memory_agent._build_prompt(context_text, "Hello")
    assert "## Session State" in prompt
    assert "- Current Turn:" in prompt


@pytest.mark.asyncio
async def test_extraction_schema_includes_instruction():
    """Verify that the extraction schema validation accepts 'instruction' type."""
    from src.memory.schemas.fact_extraction import FACT_EXTRACTION_SCHEMA

    # Inspect the schema structure (it's a google.genai.types.Schema object)
    # We can check the enum values in the 'facts' items properties

    facts_schema = FACT_EXTRACTION_SCHEMA.properties["facts"]
    items_schema = facts_schema.items
    type_schema = items_schema.properties["type"]

    assert "instruction" in type_schema.enum
