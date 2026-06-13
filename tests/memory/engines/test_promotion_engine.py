"""
Tests for PromotionEngine with batch processing and topic segmentation.

Tests the refactored PromotionEngine that implements ADR-003's
batch compression strategy using TopicSegmenter.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.memory.ciar_scorer import CIARScorer
from src.memory.engines.fact_extractor import FactExtractor
from src.memory.engines.promotion_engine import PromotionEngine
from src.memory.engines.topic_segmenter import TopicSegment, TopicSegmenter
from src.memory.models import Fact, FactCategory, FactType
from src.memory.tiers.active_context_tier import ActiveContextTier
from src.memory.tiers.working_memory_tier import WorkingMemoryTier


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
    tier.query_by_session = AsyncMock(return_value=[])
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
        config={"promotion_threshold": 0.5, "batch_min_turns": 10, "batch_max_turns": 20},
    )


@pytest.fixture
def sample_turns():
    """Sample conversation turns for testing."""
    return [
        {
            "role": "user",
            "content": "What's the ETA for container MSCU123?",
            "timestamp": "2025-12-28T10:00:00Z",
        },
        {"role": "assistant", "content": "Let me check.", "timestamp": "2025-12-28T10:00:05Z"},
        {
            "role": "assistant",
            "content": "ETA is Dec 30 at Port of LA.",
            "timestamp": "2025-12-28T10:00:10Z",
        },
        {"role": "user", "content": "Thanks!", "timestamp": "2025-12-28T10:01:00Z"},
        {
            "role": "user",
            "content": "Can you send customs docs?",
            "timestamp": "2025-12-28T10:01:10Z",
        },
        {
            "role": "assistant",
            "content": "I'll email them to you.",
            "timestamp": "2025-12-28T10:01:20Z",
        },
        {"role": "user", "content": "Perfect!", "timestamp": "2025-12-28T10:01:30Z"},
        {
            "role": "user",
            "content": "I need to update delivery address.",
            "timestamp": "2025-12-28T10:02:00Z",
        },
        {
            "role": "assistant",
            "content": "What's the new address?",
            "timestamp": "2025-12-28T10:02:05Z",
        },
        {
            "role": "user",
            "content": "123 Warehouse Lane, Commerce, CA",
            "timestamp": "2025-12-28T10:02:20Z",
        },
    ]


@pytest.mark.asyncio
async def test_process_session_below_threshold(engine, mock_l1, mock_segmenter):
    """Test that processing skips when turn count is below minimum threshold."""
    # Mock L1 with only 5 turns (below min of 10)
    mock_l1.retrieve.return_value = [{"role": "user", "content": f"Message {i}"} for i in range(5)]

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
        message_count=4,
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
        message_count=3,
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
        extracted_at=datetime.now(UTC),
        ciar_score=0.0,
        age_decay=1.0,
        recency_boost=1.0,
        topic_segment_id="seg-1",
        topic_label="Container ETA Query",
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
        extracted_at=datetime.now(UTC),
        ciar_score=0.0,
        age_decay=1.0,
        recency_boost=1.0,
        topic_segment_id="seg-2",
        topic_label="Delivery Address Update",
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
    stored_facts = [call.args[0] for call in mock_l2.store.await_args_list]
    assert {
        fact.metadata["ciar_provenance"]["lifetime_decision_class"]
        for fact in stored_facts
    } == {"store_durable"}


@pytest.mark.asyncio
async def test_segment_gate_records_provenance_and_preserves_current_inheritance(
    mock_l1, mock_l2, mock_segmenter, mock_extractor, sample_turns
):
    """Explicit segment_gate records raw and inherited CIAR while preserving promotion."""
    mock_l1.retrieve.return_value = sample_turns
    mock_l2.ciar_threshold = 0.5
    segment = TopicSegment(
        segment_id="seg-policy",
        topic="Urgent shipment update",
        summary="Shipment update has high segment importance.",
        key_points=["Shipment update"],
        turn_indices=[0, 1, 2],
        certainty=0.9,
        impact=0.9,
    )
    fact = Fact(
        fact_id="fact-low",
        session_id="123",
        content="Assistant said thanks",
        certainty=0.4,
        impact=0.3,
        fact_type=FactType.MENTION,
        fact_category=FactCategory.OPERATIONAL,
    )
    mock_segmenter.segment_turns.return_value = [segment]
    mock_extractor.extract_facts.return_value = [fact]
    engine = PromotionEngine(
        l1_tier=mock_l1,
        l2_tier=mock_l2,
        topic_segmenter=mock_segmenter,
        fact_extractor=mock_extractor,
        ciar_scorer=CIARScorer(),
        config={
            "promotion_threshold": 0.5,
            "batch_min_turns": 10,
            "promotion_policy_mode": "segment_gate",
        },
    )

    stats = await engine.process(session_id="123")

    assert stats["facts_promoted"] == 1
    stored_fact = mock_l2.store.call_args.args[0]
    provenance = stored_fact.metadata["ciar_provenance"]
    assert provenance["promotion_policy_mode"] == "segment_gate"
    assert provenance["raw_fact_ciar"] == 0.12
    assert provenance["post_inheritance_ciar"] == 0.81
    assert provenance["stored_ciar"] == 0.81
    assert provenance["segment_inherited"] is True
    assert provenance["fact_gate_decision"] is False
    assert provenance["lifetime_decision_class"] == "store_segment_inherited"
    assert "inheriting segment-level" in provenance["lifetime_decision_reason"]


@pytest.mark.asyncio
async def test_default_promotion_policy_is_hybrid_gate(
    mock_l1, mock_l2, mock_segmenter, mock_extractor, sample_turns
):
    """Default promotion behavior uses hybrid_gate unless explicitly overridden."""
    mock_l1.retrieve.return_value = sample_turns
    mock_l2.ciar_threshold = 0.5
    segment = TopicSegment(
        segment_id="seg-policy",
        topic="Shipment update",
        summary="Segment is important enough for extraction.",
        key_points=["Shipment update"],
        turn_indices=[0, 1, 2],
        certainty=0.9,
        impact=0.9,
    )
    fact = Fact(
        fact_id="fact-residue",
        session_id="123",
        content="Thanks",
        certainty=0.9,
        impact=0.7,
        fact_type=FactType.MENTION,
        fact_category=FactCategory.OPERATIONAL,
    )
    mock_segmenter.segment_turns.return_value = [segment]
    mock_extractor.extract_facts.return_value = [fact]
    engine = PromotionEngine(
        l1_tier=mock_l1,
        l2_tier=mock_l2,
        topic_segmenter=mock_segmenter,
        fact_extractor=mock_extractor,
        ciar_scorer=CIARScorer(),
        config={"promotion_threshold": 0.5, "batch_min_turns": 10},
    )

    stats = await engine.process(session_id="123")

    assert stats["facts_promoted"] == 0
    assert stats["facts_review_only"] == 1
    provenance = fact.metadata["ciar_provenance"]
    assert provenance["promotion_policy_mode"] == "hybrid_gate"
    assert provenance["review_only"] is True


@pytest.mark.asyncio
async def test_fact_gate_filters_by_pre_inheritance_ciar(
    mock_l1, mock_l2, mock_segmenter, mock_extractor, sample_turns
):
    """fact_gate prevents segment CIAR from promoting low-value facts."""
    mock_l1.retrieve.return_value = sample_turns
    mock_l2.ciar_threshold = 0.5
    segment = TopicSegment(
        segment_id="seg-policy",
        topic="Urgent shipment update",
        summary="Shipment update has high segment importance.",
        key_points=["Shipment update"],
        turn_indices=[0, 1, 2],
        certainty=0.9,
        impact=0.9,
    )
    fact = Fact(
        fact_id="fact-low",
        session_id="123",
        content="Assistant said thanks",
        certainty=0.4,
        impact=0.3,
        fact_type=FactType.MENTION,
        fact_category=FactCategory.OPERATIONAL,
    )
    mock_segmenter.segment_turns.return_value = [segment]
    mock_extractor.extract_facts.return_value = [fact]
    engine = PromotionEngine(
        l1_tier=mock_l1,
        l2_tier=mock_l2,
        topic_segmenter=mock_segmenter,
        fact_extractor=mock_extractor,
        ciar_scorer=CIARScorer(),
        config={
            "promotion_threshold": 0.5,
            "batch_min_turns": 10,
            "promotion_policy_mode": "fact_gate",
        },
    )

    stats = await engine.process(session_id="123")

    assert stats["facts_promoted"] == 0
    assert stats["facts_filtered"] == 1
    mock_l2.store.assert_not_called()
    provenance = fact.metadata["ciar_provenance"]
    assert provenance["promotion_policy_mode"] == "fact_gate"
    assert provenance["raw_fact_ciar"] == 0.12
    assert provenance["stored_ciar"] is None
    assert provenance["segment_inherited"] is False
    assert provenance["lifetime_decision_class"] == "filter_low_ciar"


@pytest.mark.asyncio
async def test_hybrid_gate_marks_conversational_residue_review_only(
    mock_l1, mock_l2, mock_segmenter, mock_extractor, sample_turns
):
    """hybrid_gate keeps obvious residue out of L2 even if raw CIAR is high."""
    mock_l1.retrieve.return_value = sample_turns
    mock_l2.ciar_threshold = 0.5
    segment = TopicSegment(
        segment_id="seg-policy",
        topic="Shipment update",
        summary="Segment is important enough for extraction.",
        key_points=["Shipment update"],
        turn_indices=[0, 1, 2],
        certainty=0.9,
        impact=0.9,
    )
    fact = Fact(
        fact_id="fact-residue",
        session_id="123",
        content="Thanks",
        certainty=0.9,
        impact=0.7,
        fact_type=FactType.MENTION,
        fact_category=FactCategory.OPERATIONAL,
    )
    mock_segmenter.segment_turns.return_value = [segment]
    mock_extractor.extract_facts.return_value = [fact]
    engine = PromotionEngine(
        l1_tier=mock_l1,
        l2_tier=mock_l2,
        topic_segmenter=mock_segmenter,
        fact_extractor=mock_extractor,
        ciar_scorer=CIARScorer(),
        config={
            "promotion_threshold": 0.5,
            "batch_min_turns": 10,
            "promotion_policy_mode": "hybrid_gate",
        },
    )

    stats = await engine.process(session_id="123")

    assert stats["facts_promoted"] == 0
    assert stats["facts_review_only"] == 1
    mock_l2.store.assert_not_called()
    provenance = fact.metadata["ciar_provenance"]
    assert provenance["review_only"] is True
    assert provenance["evidence_quality_flags"]["conversational_residue"] is True
    assert provenance["lifetime_decision_class"] == "review_conversational_residue"


@pytest.mark.asyncio
async def test_hybrid_gate_reviews_low_evidence_without_specific_quality_flag(
    mock_l1, mock_l2, mock_segmenter, mock_extractor, sample_turns
):
    """hybrid_gate labels low-evidence review-only facts when no stronger class applies."""
    mock_l1.retrieve.return_value = sample_turns
    mock_l2.ciar_threshold = 0.5
    segment = TopicSegment(
        segment_id="seg-low-evidence",
        topic="Weak operational note",
        summary="Segment is important enough for extraction.",
        key_points=["Weak note"],
        turn_indices=[0, 1, 2],
        certainty=0.9,
        impact=0.9,
    )
    fact = Fact(
        fact_id="fact-weak",
        session_id="123",
        content="The schedule note is incomplete.",
        certainty=0.5,
        impact=0.5,
        fact_type=FactType.EVENT,
        fact_category=FactCategory.OPERATIONAL,
    )
    mock_segmenter.segment_turns.return_value = [segment]
    mock_extractor.extract_facts.return_value = [fact]
    engine = PromotionEngine(
        l1_tier=mock_l1,
        l2_tier=mock_l2,
        topic_segmenter=mock_segmenter,
        fact_extractor=mock_extractor,
        ciar_scorer=CIARScorer(),
        config={
            "promotion_threshold": 0.5,
            "batch_min_turns": 10,
            "promotion_policy_mode": "hybrid_gate",
        },
    )

    stats = await engine.process(session_id="123")

    assert stats["facts_promoted"] == 0
    assert stats["facts_review_only"] == 1
    provenance = fact.metadata["ciar_provenance"]
    assert provenance["review_only"] is True
    assert provenance["lifetime_decision_class"] == "review_low_evidence"
    assert provenance["lifetime_decision_reason"] == "candidate failed the hybrid evidence gate"


@pytest.mark.asyncio
async def test_hybrid_gate_reviews_assistant_action_but_stores_operational_state(
    mock_l1, mock_l2, mock_segmenter, mock_extractor, sample_turns
):
    """Assistant commitments with domain terms are residue; durable state still stores."""
    mock_l1.retrieve.return_value = sample_turns
    mock_l2.ciar_threshold = 0.5
    segment = TopicSegment(
        segment_id="seg-policy",
        topic="Customs hold release miss",
        summary="Container missed its customs hold release window.",
        key_points=["Missed customs hold release", "Assistant recording note"],
        turn_indices=[0, 1, 2],
        certainty=0.9,
        impact=0.9,
    )
    operational_fact = Fact(
        fact_id="fact-operational",
        session_id="123",
        content="Container MEDU7711009 missed its customs hold release window.",
        certainty=0.94,
        impact=0.9,
        fact_type=FactType.EVENT,
        fact_category=FactCategory.OPERATIONAL,
    )
    assistant_fact = Fact(
        fact_id="fact-assistant-action",
        session_id="123",
        content=(
            "The assistant will record that container MEDU7711009 missed its customs "
            "hold release window."
        ),
        certainty=0.92,
        impact=0.72,
        fact_type=FactType.MENTION,
        fact_category=FactCategory.OPERATIONAL,
    )
    mock_segmenter.segment_turns.return_value = [segment]
    mock_extractor.extract_facts.return_value = [operational_fact, assistant_fact]
    engine = PromotionEngine(
        l1_tier=mock_l1,
        l2_tier=mock_l2,
        topic_segmenter=mock_segmenter,
        fact_extractor=mock_extractor,
        ciar_scorer=CIARScorer(),
        config={
            "promotion_threshold": 0.5,
            "batch_min_turns": 10,
            "promotion_policy_mode": "hybrid_gate",
        },
    )

    stats = await engine.process(session_id="123")

    assert stats["facts_promoted"] == 1
    assert stats["facts_review_only"] == 1
    stored_fact = mock_l2.store.call_args.args[0]
    assert stored_fact.fact_id == "fact-operational"
    stored_flags = operational_fact.metadata["ciar_provenance"]["evidence_quality_flags"]
    assert stored_flags["domain_signal"] is True
    assert stored_flags["assistant_action_residue"] is False
    assistant_provenance = assistant_fact.metadata["ciar_provenance"]
    assert assistant_provenance["review_only"] is True
    assert assistant_provenance["lifetime_decision_class"] == "review_conversational_residue"
    assert assistant_provenance["evidence_quality_flags"]["domain_signal"] is True
    assert assistant_provenance["evidence_quality_flags"]["assistant_action_residue"] is True
    assert assistant_provenance["evidence_quality_flags"]["conversational_residue"] is True


@pytest.mark.asyncio
async def test_hybrid_gate_reviews_speculation_and_inference_but_stores_confirmed_fact(
    mock_l1, mock_l2, mock_segmenter, mock_extractor, sample_turns
):
    """Speculation and assistant inference are review-only, confirmed facts can store."""
    mock_l1.retrieve.return_value = sample_turns
    mock_l2.ciar_threshold = 0.5
    segment = TopicSegment(
        segment_id="seg-speculation",
        topic="Supplier risk and freight preference",
        summary="One speculative supplier risk and one inferred user preference.",
        key_points=["Speculative risk", "Inferred preference", "Confirmed preference"],
        turn_indices=[0, 1, 2],
        certainty=0.9,
        impact=0.9,
    )
    speculative_fact = Fact(
        fact_id="fact-speculative",
        session_id="123",
        content="The supplier might miss the customs document deadline.",
        certainty=0.9,
        impact=0.8,
        fact_type=FactType.EVENT,
        fact_category=FactCategory.OPERATIONAL,
    )
    inferred_fact = Fact(
        fact_id="fact-inferred",
        session_id="123",
        content="The user likely prefers air freight for urgent shipments.",
        certainty=0.9,
        impact=0.8,
        fact_type=FactType.PREFERENCE,
        fact_category=FactCategory.OPERATIONAL,
    )
    confirmed_fact = Fact(
        fact_id="fact-confirmed",
        session_id="123",
        content="The user prefers air freight for urgent shipments.",
        certainty=0.9,
        impact=0.8,
        fact_type=FactType.PREFERENCE,
        fact_category=FactCategory.OPERATIONAL,
    )
    mock_segmenter.segment_turns.return_value = [segment]
    mock_extractor.extract_facts.return_value = [
        speculative_fact,
        inferred_fact,
        confirmed_fact,
    ]
    engine = PromotionEngine(
        l1_tier=mock_l1,
        l2_tier=mock_l2,
        topic_segmenter=mock_segmenter,
        fact_extractor=mock_extractor,
        ciar_scorer=CIARScorer(),
        config={
            "promotion_threshold": 0.5,
            "batch_min_turns": 10,
            "promotion_policy_mode": "hybrid_gate",
        },
    )

    stats = await engine.process(session_id="123")

    assert stats["facts_promoted"] == 1
    assert stats["facts_review_only"] == 2
    stored_fact = mock_l2.store.call_args.args[0]
    assert stored_fact.fact_id == "fact-confirmed"
    speculative_flags = speculative_fact.metadata["ciar_provenance"]["evidence_quality_flags"]
    inferred_flags = inferred_fact.metadata["ciar_provenance"]["evidence_quality_flags"]
    confirmed_flags = confirmed_fact.metadata["ciar_provenance"]["evidence_quality_flags"]
    assert speculative_fact.metadata["ciar_provenance"]["review_only"] is True
    assert (
        speculative_fact.metadata["ciar_provenance"]["lifetime_decision_class"]
        == "review_uncertain_or_inferred"
    )
    assert speculative_flags["speculative_claim"] is True
    assert speculative_flags["assistant_inference"] is False
    assert inferred_fact.metadata["ciar_provenance"]["review_only"] is True
    assert (
        inferred_fact.metadata["ciar_provenance"]["lifetime_decision_class"]
        == "review_uncertain_or_inferred"
    )
    assert inferred_flags["assistant_inference"] is True
    assert inferred_flags["speculative_claim"] is False
    assert confirmed_fact.metadata["ciar_provenance"]["review_only"] is False
    assert confirmed_flags["speculative_claim"] is False
    assert confirmed_flags["assistant_inference"] is False


@pytest.mark.asyncio
async def test_hybrid_gate_reviews_access_reinforced_low_base_evidence(
    mock_l1, mock_l2, mock_segmenter, mock_extractor, sample_turns
):
    """High access cannot be the only reason weak base evidence stores under hybrid_gate."""
    mock_l1.retrieve.return_value = sample_turns
    mock_l2.ciar_threshold = 0.6
    segment = TopicSegment(
        segment_id="seg-recency-access",
        topic="Access-reinforced reference note",
        summary="One weak note has high access, one durable fact has strong base evidence.",
        key_points=["Low-base high-access note", "Strong operational constraint"],
        turn_indices=[0, 1, 2],
        certainty=0.9,
        impact=0.9,
    )
    low_base_fact = Fact(
        fact_id="fact-low-base-accessed",
        session_id="123",
        content="Carrier dashboard reference note was repeatedly opened by the operations team.",
        certainty=0.5,
        impact=0.5,
        access_count=20,
        fact_type=FactType.MENTION,
        fact_category=FactCategory.OPERATIONAL,
    )
    strong_base_fact = Fact(
        fact_id="fact-strong-base-accessed",
        session_id="123",
        content="Customer Acme requires customs paperwork before LA port release.",
        certainty=0.9,
        impact=0.8,
        access_count=20,
        fact_type=FactType.CONSTRAINT,
        fact_category=FactCategory.OPERATIONAL,
    )
    mock_segmenter.segment_turns.return_value = [segment]
    mock_extractor.extract_facts.return_value = [low_base_fact, strong_base_fact]
    engine = PromotionEngine(
        l1_tier=mock_l1,
        l2_tier=mock_l2,
        topic_segmenter=mock_segmenter,
        fact_extractor=mock_extractor,
        ciar_scorer=CIARScorer(),
        config={
            "promotion_threshold": 0.6,
            "batch_min_turns": 10,
            "promotion_policy_mode": "hybrid_gate",
        },
    )

    stats = await engine.process(session_id="123")

    assert stats["facts_promoted"] == 1
    assert stats["facts_review_only"] == 1
    stored_fact = mock_l2.store.call_args.args[0]
    assert stored_fact.fact_id == "fact-strong-base-accessed"
    low_provenance = low_base_fact.metadata["ciar_provenance"]
    low_flags = low_provenance["evidence_quality_flags"]
    assert low_provenance["raw_fact_ciar"] == 0.75
    assert low_provenance["review_only"] is True
    assert low_flags["base_evidence_below_threshold"] is True
    assert low_flags["access_boosted_over_threshold"] is True
    assert low_flags["recency_access_guardrail"] is True
    assert low_provenance["lifetime_decision_class"] == "review_access_boost_only"
    strong_flags = strong_base_fact.metadata["ciar_provenance"]["evidence_quality_flags"]
    assert strong_base_fact.metadata["ciar_provenance"]["review_only"] is False
    assert strong_flags["base_evidence_below_threshold"] is False
    assert strong_flags["access_boosted_over_threshold"] is False
    assert strong_flags["recency_access_guardrail"] is False


@pytest.mark.asyncio
async def test_fact_gate_preserves_access_boost_storage_semantics(
    mock_l1, mock_l2, mock_segmenter, mock_extractor, sample_turns
):
    """The recency/access guardrail is diagnostic only outside hybrid_gate."""
    mock_l1.retrieve.return_value = sample_turns
    mock_l2.ciar_threshold = 0.6
    segment = TopicSegment(
        segment_id="seg-recency-access",
        topic="Access-reinforced reference note",
        summary="A weak note has high access.",
        key_points=["Low-base high-access note"],
        turn_indices=[0, 1, 2],
        certainty=0.9,
        impact=0.9,
    )
    fact = Fact(
        fact_id="fact-low-base-accessed",
        session_id="123",
        content="Carrier dashboard reference note was repeatedly opened by the operations team.",
        certainty=0.5,
        impact=0.5,
        access_count=20,
        fact_type=FactType.MENTION,
        fact_category=FactCategory.OPERATIONAL,
    )
    mock_segmenter.segment_turns.return_value = [segment]
    mock_extractor.extract_facts.return_value = [fact]
    engine = PromotionEngine(
        l1_tier=mock_l1,
        l2_tier=mock_l2,
        topic_segmenter=mock_segmenter,
        fact_extractor=mock_extractor,
        ciar_scorer=CIARScorer(),
        config={
            "promotion_threshold": 0.6,
            "batch_min_turns": 10,
            "promotion_policy_mode": "fact_gate",
        },
    )

    stats = await engine.process(session_id="123")

    assert stats["facts_promoted"] == 1
    assert stats["facts_review_only"] == 0
    mock_l2.store.assert_called_once()
    provenance = fact.metadata["ciar_provenance"]
    assert provenance["stored_ciar"] == 0.75
    assert provenance["review_only"] is False
    assert provenance["lifetime_decision_class"] == "store_durable"
    assert provenance["evidence_quality_flags"]["recency_access_guardrail"] is True


@pytest.mark.asyncio
async def test_contradiction_policy_suppresses_superseded_batch_fact(
    mock_l1, mock_l2, mock_segmenter, mock_extractor, sample_turns
):
    """suppress_superseded keeps current correction and suppresses the old fact."""
    mock_l1.retrieve.return_value = sample_turns
    mock_l2.ciar_threshold = 0.5
    segment = TopicSegment(
        segment_id="seg-contradiction",
        topic="Route correction",
        summary="Shipment route was corrected.",
        key_points=["Oakland", "Los Angeles correction"],
        turn_indices=[0, 1, 2],
        certainty=0.9,
        impact=0.9,
    )
    old_fact = Fact(
        fact_id="fact-old-route",
        session_id="123",
        content="The shipment was scheduled for Oakland.",
        certainty=0.9,
        impact=0.8,
        fact_type=FactType.EVENT,
        fact_category=FactCategory.OPERATIONAL,
    )
    corrected_fact = Fact(
        fact_id="fact-new-route",
        session_id="123",
        content="Correction: it is now rerouted to Los Angeles, not Oakland.",
        certainty=0.95,
        impact=0.9,
        fact_type=FactType.EVENT,
        fact_category=FactCategory.OPERATIONAL,
    )
    mock_segmenter.segment_turns.return_value = [segment]
    mock_extractor.extract_facts.return_value = [old_fact, corrected_fact]
    telemetry = MagicMock()
    telemetry.publish = AsyncMock()
    engine = PromotionEngine(
        l1_tier=mock_l1,
        l2_tier=mock_l2,
        topic_segmenter=mock_segmenter,
        fact_extractor=mock_extractor,
        ciar_scorer=CIARScorer(),
        config={
            "promotion_threshold": 0.5,
            "batch_min_turns": 10,
            "promotion_policy_mode": "hybrid_gate",
            "contradiction_policy_mode": "suppress_superseded",
        },
        telemetry_stream=telemetry,
    )

    stats = await engine.process(session_id="123")

    assert stats["facts_promoted"] == 1
    assert stats["facts_suppressed"] == 1
    stored_fact = mock_l2.store.call_args.args[0]
    assert stored_fact.fact_id == "fact-new-route"
    assert stored_fact.metadata["contradiction_policy"]["supersedes_fact_ids"] == [
        "fact-old-route"
    ]
    assert old_fact.metadata["contradiction_policy"]["decision"] == "SUPPRESS"
    assert old_fact.metadata["contradiction_policy"]["superseded_by_fact_id"] == "fact-new-route"
    assert (
        old_fact.metadata["ciar_provenance"]["lifetime_decision_class"]
        == "suppress_superseded"
    )
    assert any(
        call.kwargs.get("event_type") == "fact_suppressed"
        for call in telemetry.publish.await_args_list
    )
    suppressed_call = next(
        call for call in telemetry.publish.await_args_list
        if call.kwargs.get("event_type") == "fact_suppressed"
    )
    assert suppressed_call.kwargs["data"]["lifetime_decision_class"] == "suppress_superseded"


@pytest.mark.asyncio
async def test_contradiction_policy_metadata_only_stores_both_facts(
    mock_l1, mock_l2, mock_segmenter, mock_extractor, sample_turns
):
    """metadata_only annotates conflict without suppressing historical evidence."""
    mock_l1.retrieve.return_value = sample_turns
    mock_l2.ciar_threshold = 0.5
    segment = TopicSegment(
        segment_id="seg-contradiction",
        topic="Route correction",
        summary="Shipment route was corrected.",
        key_points=["Oakland", "Los Angeles correction"],
        turn_indices=[0, 1, 2],
        certainty=0.9,
        impact=0.9,
    )
    old_fact = Fact(
        fact_id="fact-old-route",
        session_id="123",
        content="The shipment was scheduled for Oakland.",
        certainty=0.9,
        impact=0.8,
        fact_type=FactType.EVENT,
        fact_category=FactCategory.OPERATIONAL,
    )
    corrected_fact = Fact(
        fact_id="fact-new-route",
        session_id="123",
        content="Correction: it is now rerouted to Los Angeles, not Oakland.",
        certainty=0.95,
        impact=0.9,
        fact_type=FactType.EVENT,
        fact_category=FactCategory.OPERATIONAL,
    )
    mock_segmenter.segment_turns.return_value = [segment]
    mock_extractor.extract_facts.return_value = [old_fact, corrected_fact]
    engine = PromotionEngine(
        l1_tier=mock_l1,
        l2_tier=mock_l2,
        topic_segmenter=mock_segmenter,
        fact_extractor=mock_extractor,
        ciar_scorer=CIARScorer(),
        config={
            "promotion_threshold": 0.5,
            "batch_min_turns": 10,
            "promotion_policy_mode": "hybrid_gate",
            "contradiction_policy_mode": "metadata_only",
        },
    )

    stats = await engine.process(session_id="123")

    assert stats["facts_promoted"] == 2
    assert stats["facts_suppressed"] == 0
    assert mock_l2.store.await_count == 2
    assert old_fact.metadata["contradiction_policy"]["decision"] == "ANNOTATE"
    assert corrected_fact.metadata["contradiction_policy"]["supersedes_fact_ids"] == [
        "fact-old-route"
    ]


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
        impact=0.2,  # Low impact
        participant_count=2,
        message_count=2,
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
    segment = TopicSegment(topic="Test Topic", summary="Test summary", certainty=0.8, impact=0.9)

    score = await engine._score_segment(segment)

    # For fresh segments: age_decay=1.0, recency_boost=1.0
    # CIAR = (0.8 x 0.9) x 1.0 x 1.0 = 0.72
    assert score == 0.72


@pytest.mark.asyncio
async def test_format_segment_for_extraction(engine, sample_turns):
    """Test formatting segment for fact extraction."""
    segment = TopicSegment(
        topic="Container ETA",
        summary="User asked about container ETA.",
        key_points=["Container tracking", "ETA query"],
        turn_indices=[0, 1, 2],
    )

    formatted = engine._format_segment_for_extraction(segment, sample_turns)

    assert "Topic: Container ETA" in formatted
    assert "Summary: User asked about container ETA." in formatted
    assert "Key Points:" in formatted
    assert "Container tracking" in formatted
    assert "ETA query" in formatted
    assert "Relevant Conversation:" in formatted
    assert "What's the ETA for container MSCU123?" in formatted
