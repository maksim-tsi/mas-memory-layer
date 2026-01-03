"""
Tests for PromotionEngine with batch processing and topic segmentation.

Tests the refactored PromotionEngine that implements ADR-003's
batch compression strategy using TopicSegmenter.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.memory.engines.promotion_engine import PromotionEngine
from src.memory.tiers.active_context_tier import ActiveContextTier
from src.memory.tiers.working_memory_tier import WorkingMemoryTier
from src.memory.engines.topic_segmenter import TopicSegmenter, TopicSegment
from src.memory.engines.fact_extractor import FactExtractor
from src.memory.ciar_scorer import CIARScorer
from src.memory.models import Fact, FactType, FactCategory
from datetime import datetime, timezone


@pytest.fixture
def mock_l1():
    """Mock L1 Active Context tier."""
    tier = MagicMock(spec=ActiveContextTier)
    tier.retrieve = AsyncMock()
    tier.health_check = AsyncMock(return_value={"status": "healthy"})
    return tier


@pytest.fixture
def mock_l2():
    """Mock L2 Working Memory tier."""
    tier = MagicMock(spec=WorkingMemoryTier)
    tier.store = AsyncMock()
    tier.health_check = AsyncMock(return_value={"status": "healthy"})
    return tier


@pytest.fixture
def mock_segmenter():
    """Mock TopicSegmenter."""
    segmenter = MagicMock(spec=TopicSegmenter)
    segmenter.segment_turns = AsyncMock()
    return segmenter


@pytest.fixture
def mock_extractor():
    """Mock FactExtractor."""
    extractor = MagicMock(spec=FactExtractor)
    extractor.extract_facts = AsyncMock()
    return extractor


@pytest.fixture
def mock_scorer():
    """Mock CIARScorer."""
    scorer = MagicMock(spec=CIARScorer)
    scorer.calculate = MagicMock()
    return scorer


@pytest.fixture
def engine(mock_l1, mock_l2, mock_segmenter, mock_extractor, mock_scorer):
    """Create PromotionEngine with mocked dependencies."""
    return PromotionEngine(
        l1_tier=mock_l1,
        l2_tier=mock_l2,
        topic_segmenter=mock_segmenter,
        fact_extractor=mock_extractor,
        ciar_scorer=mock_scorer,
        config={
            "promotion_threshold": 0.5,
            "batch_min_turns": 10,
            "batch_max_turns": 20
        }
    )


@pytest.fixture
def sample_turns():
    """Sample conversation turns for testing."""
    return [
        {"role": "user", "content": "What's the ETA for container MSCU123?", "timestamp": "2025-12-28T10:00:00Z"},
        {"role": "assistant", "content": "Let me check.", "timestamp": "2025-12-28T10:00:05Z"},
        {"role": "assistant", "content": "ETA is Dec 30 at Port of LA.", "timestamp": "2025-12-28T10:00:10Z"},
        {"role": "user", "content": "Thanks!", "timestamp": "2025-12-28T10:01:00Z"},
        {"role": "user", "content": "Can you send customs docs?", "timestamp": "2025-12-28T10:01:10Z"},
        {"role": "assistant", "content": "I'll email them to you.", "timestamp": "2025-12-28T10:01:20Z"},
        {"role": "user", "content": "Perfect!", "timestamp": "2025-12-28T10:01:30Z"},
        {"role": "user", "content": "I need to update delivery address.", "timestamp": "2025-12-28T10:02:00Z"},
        {"role": "assistant", "content": "What's the new address?", "timestamp": "2025-12-28T10:02:05Z"},
        {"role": "user", "content": "123 Warehouse Lane, Commerce, CA", "timestamp": "2025-12-28T10:02:20Z"}
    ]


@pytest.mark.asyncio
async def test_process_session_below_threshold(engine, mock_l1, mock_segmenter):
    """Test that processing skips when turn count is below minimum threshold."""
    # Mock L1 with only 5 turns (below min of 10)
    mock_l1.retrieve.return_value = [
        {"role": "user", "content": f"Message {i}"}
        for i in range(5)
    ]
    
    stats = await engine.process(session_id="123")
    
    assert stats["turns_retrieved"] == 5
    assert stats["segments_created"] == 0
    assert stats["facts_promoted"] == 0
    
    # Segmenter should not be called
    mock_segmenter.segment_turns.assert_not_called()


@pytest.mark.asyncio
async def test_process_session_batch_success(
    engine, mock_l1, mock_l2, mock_segmenter, mock_extractor, mock_scorer, sample_turns
):
    """Test successful batch processing with topic segmentation and fact promotion."""
    # Mock L1 returns 10 turns (meets threshold)
    mock_l1.retrieve.return_value = sample_turns
    
    # Mock TopicSegmenter returns 2 segments
    segment1 = TopicSegment(
        segment_id="seg-1",
        topic="Container ETA Query",
        summary="User asked about container ETA, assistant provided Dec 30 ETA.",
        key_points=["Container MSCU123", "ETA Dec 30", "Port of LA"],
        turn_indices=[0, 1, 2, 3],
        certainty=0.9,
        impact=0.8,
        participant_count=2,
        message_count=4
    )
    
    segment2 = TopicSegment(
        segment_id="seg-2",
        topic="Delivery Address Update",
        summary="User requested delivery address update to 123 Warehouse Lane.",
        key_points=["Address update", "123 Warehouse Lane"],
        turn_indices=[7, 8, 9],
        certainty=0.95,
        impact=0.9,
        participant_count=2,
        message_count=3
    )
    
    mock_segmenter.segment_turns.return_value = [segment1, segment2]
    
    # Mock FactExtractor returns facts for each segment
    fact1 = Fact(
        fact_id="fact-1",
        session_id="123",
        content="Container MSCU123 ETA is December 30 at Port of LA",
        fact_type=FactType.EVENT,
        fact_category=FactCategory.OPERATIONAL,
        certainty=0.9,
        impact=0.8,
        source_type="llm",
        extracted_at=datetime.now(timezone.utc),
        ciar_score=0.0,
        age_decay=1.0,
        recency_boost=1.0,
        topic_segment_id="seg-1",
        topic_label="Container ETA Query"
    )
    
    fact2 = Fact(
        fact_id="fact-2",
        session_id="123",
        content="Delivery address updated to 123 Warehouse Lane, Commerce, CA",
        fact_type=FactType.EVENT,
        fact_category=FactCategory.OPERATIONAL,
        certainty=0.95,
        impact=0.9,
        source_type="llm",
        extracted_at=datetime.now(timezone.utc),
        ciar_score=0.0,
        age_decay=1.0,
        recency_boost=1.0,
        topic_segment_id="seg-2",
        topic_label="Delivery Address Update"
    )
    
    # First call returns facts for segment1, second call for segment2
    mock_extractor.extract_facts.side_effect = [[fact1], [fact2]]
    
    # Mock Scorer returns high scores for both facts
    mock_scorer.calculate.side_effect = [0.85, 0.90]
    
    stats = await engine.process(session_id="123")
    
    assert stats["turns_retrieved"] == 10
    assert stats["segments_created"] == 2
    assert stats["segments_promoted"] == 2
    assert stats["facts_extracted"] == 2
    assert stats["facts_promoted"] == 2
    assert stats["errors"] == 0
    
    # Verify segmenter was called with chronological turns
    mock_segmenter.segment_turns.assert_called_once()
    
    # Verify extractor was called twice (once per segment)
    assert mock_extractor.extract_facts.call_count == 2
    
    # Verify L2 store was called twice
    assert mock_l2.store.call_count == 2


@pytest.mark.asyncio
async def test_process_session_segment_below_threshold(
    engine, mock_l1, mock_segmenter, mock_extractor, mock_l2, sample_turns
):
    """Test that low-scoring segments are filtered out."""
    mock_l1.retrieve.return_value = sample_turns
    
    # Create segment with low certainty/impact -> low CIAR score
    low_segment = TopicSegment(
        segment_id="seg-low",
        topic="Small Talk",
        summary="Casual greetings and acknowledgments.",
        key_points=["Hello", "Thanks"],
        turn_indices=[0, 1],
        certainty=0.3,  # Low certainty
        impact=0.2,     # Low impact
        participant_count=2,
        message_count=2
    )
    
    mock_segmenter.segment_turns.return_value = [low_segment]
    
    stats = await engine.process(session_id="123")
    
    # Segment created but not promoted (score = 0.3 * 0.2 = 0.06, below threshold 0.5)
    assert stats["segments_created"] == 1
    assert stats["segments_promoted"] == 0
    assert stats["facts_promoted"] == 0
    
    # Extractor should not be called for low-scoring segments
    mock_extractor.extract_facts.assert_not_called()
    mock_l2.store.assert_not_called()


@pytest.mark.asyncio
async def test_process_session_no_segments(engine, mock_l1, mock_segmenter, sample_turns):
    """Test handling when segmenter returns no segments."""
    mock_l1.retrieve.return_value = sample_turns
    mock_segmenter.segment_turns.return_value = []
    
    stats = await engine.process(session_id="123")
    
    assert stats["turns_retrieved"] == 10
    assert stats["segments_created"] == 0
    assert stats["facts_promoted"] == 0


@pytest.mark.asyncio
async def test_process_no_session_id(engine):
    """Test handling when no session_id is provided."""
    result = await engine.process()
    assert result["status"] == "skipped"
    assert result["reason"] == "no_session_id"


@pytest.mark.asyncio
async def test_process_no_turns(engine, mock_l1):
    """Test handling when L1 returns no turns."""
    mock_l1.retrieve.return_value = []
    
    stats = await engine.process(session_id="123")
    
    assert stats["turns_retrieved"] == 0
    assert stats["facts_promoted"] == 0


@pytest.mark.asyncio
async def test_health_check(engine):
    """Test health check includes configuration."""
    health = await engine.health_check()
    
    assert health["status"] == "healthy"
    assert health["l1"]["status"] == "healthy"
    assert health["l2"]["status"] == "healthy"
    assert health["config"]["promotion_threshold"] == 0.5
    assert health["config"]["batch_min_turns"] == 10
    assert health["config"]["batch_max_turns"] == 20


@pytest.mark.asyncio
async def test_score_segment(engine):
    """Test segment-level CIAR scoring."""
    segment = TopicSegment(
        topic="Test Topic",
        summary="Test summary",
        certainty=0.8,
        impact=0.9
    )
    
    score = await engine._score_segment(segment)
    
    # For fresh segments: age_decay=1.0, recency_boost=1.0
    # CIAR = (0.8 × 0.9) × 1.0 × 1.0 = 0.72
    assert score == 0.72


@pytest.mark.asyncio
async def test_format_segment_for_extraction(engine, sample_turns):
    """Test formatting segment for fact extraction."""
    segment = TopicSegment(
        topic="Container ETA",
        summary="User asked about container ETA.",
        key_points=["Container tracking", "ETA query"],
        turn_indices=[0, 1, 2]
    )
    
    formatted = engine._format_segment_for_extraction(segment, sample_turns)
    
    assert "Topic: Container ETA" in formatted
    assert "Summary: User asked about container ETA." in formatted
    assert "Key Points:" in formatted
    assert "Container tracking" in formatted
    assert "ETA query" in formatted
    assert "Relevant Conversation:" in formatted
    assert "What's the ETA for container MSCU123?" in formatted
