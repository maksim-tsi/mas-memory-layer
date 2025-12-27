import pytest
from unittest.mock import AsyncMock, MagicMock
from src.memory.engines.promotion_engine import PromotionEngine
from src.memory.tiers.active_context_tier import ActiveContextTier
from src.memory.tiers.working_memory_tier import WorkingMemoryTier
from src.memory.engines.fact_extractor import FactExtractor
from src.memory.ciar_scorer import CIARScorer
from src.memory.models import Fact, FactType, FactCategory
from datetime import datetime, timezone

@pytest.fixture
def mock_l1():
    tier = MagicMock(spec=ActiveContextTier)
    tier.retrieve = AsyncMock()
    tier.health_check = AsyncMock(return_value={"status": "healthy"})
    return tier

@pytest.fixture
def mock_l2():
    tier = MagicMock(spec=WorkingMemoryTier)
    tier.store = AsyncMock()
    tier.health_check = AsyncMock(return_value={"status": "healthy"})
    return tier

@pytest.fixture
def mock_extractor():
    extractor = MagicMock(spec=FactExtractor)
    extractor.extract_facts = AsyncMock()
    return extractor

@pytest.fixture
def mock_scorer():
    scorer = MagicMock(spec=CIARScorer)
    scorer.calculate = MagicMock()
    return scorer

@pytest.fixture
def engine(mock_l1, mock_l2, mock_extractor, mock_scorer):
    return PromotionEngine(
        l1_tier=mock_l1,
        l2_tier=mock_l2,
        fact_extractor=mock_extractor,
        ciar_scorer=mock_scorer,
        config={"promotion_threshold": 0.5}
    )

@pytest.mark.asyncio
async def test_process_session_success(engine, mock_l1, mock_l2, mock_extractor, mock_scorer):
    # Mock L1 turns
    mock_l1.retrieve.return_value = [
        {"role": "user", "content": "I like blue"},
        {"role": "assistant", "content": "Noted"}
    ]
    
    # Mock Extracted Facts
    fact = Fact(
        fact_id="1",
        session_id="123",
        content="User likes blue",
        fact_type=FactType.PREFERENCE,
        fact_category=FactCategory.PERSONAL,
        certainty=0.9,
        impact=0.8,
        source_type="llm",
        extracted_at=datetime.now(timezone.utc),
        ciar_score=0.0,
        age_decay=1.0,
        recency_boost=1.0
    )
    mock_extractor.extract_facts.return_value = [fact]
    
    # Mock Scorer (High score -> Promote)
    mock_scorer.calculate.return_value = 0.8
    
    stats = await engine.process(session_id="123")
    
    assert stats["turns_retrieved"] == 2
    assert stats["facts_extracted"] == 1
    assert stats["facts_promoted"] == 1
    assert stats["errors"] == 0
    
    # Verify L2 store called
    mock_l2.store.assert_called_once()
    stored_data = mock_l2.store.call_args[0][0]
    assert stored_data["content"] == "User likes blue"
    assert stored_data["ciar_score"] == 0.8

@pytest.mark.asyncio
async def test_process_session_low_score(engine, mock_l1, mock_l2, mock_extractor, mock_scorer):
    # Mock L1 turns
    mock_l1.retrieve.return_value = [{"role": "user", "content": "Hi"}]
    
    # Mock Extracted Facts
    fact = Fact(
        fact_id="1",
        session_id="123",
        content="User said Hi",
        fact_type=FactType.MENTION,
        fact_category=FactCategory.OPERATIONAL,
        certainty=0.5,
        impact=0.1,
        source_type="llm",
        extracted_at=datetime.now(timezone.utc),
        ciar_score=0.0,
        age_decay=1.0,
        recency_boost=1.0
    )
    mock_extractor.extract_facts.return_value = [fact]
    
    # Mock Scorer (Low score -> Do not promote)
    mock_scorer.calculate.return_value = 0.1
    
    stats = await engine.process(session_id="123")
    
    assert stats["facts_promoted"] == 0
    mock_l2.store.assert_not_called()

@pytest.mark.asyncio
async def test_process_no_session_id(engine):
    result = await engine.process()
    assert result["status"] == "skipped"

@pytest.mark.asyncio
async def test_health_check(engine):
    health = await engine.health_check()
    assert health["status"] == "healthy"
    assert health["l1"]["status"] == "healthy"
    assert health["l2"]["status"] == "healthy"
