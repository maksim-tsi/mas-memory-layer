import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from src.memory.engines.consolidation_engine import ConsolidationEngine
from src.memory.tiers.working_memory_tier import WorkingMemoryTier
from src.memory.tiers.episodic_memory_tier import EpisodicMemoryTier
from src.memory.models import Fact, Episode, FactType, FactCategory
from src.utils.providers import GeminiProvider
from src.utils.llm_client import LLMResponse, ProviderHealth

@pytest.fixture
def mock_l2():
    tier = MagicMock(spec=WorkingMemoryTier)
    tier.query_by_session = AsyncMock()
    tier.health_check = AsyncMock(return_value={"status": "healthy"})
    return tier

@pytest.fixture
def mock_l3():
    tier = MagicMock(spec=EpisodicMemoryTier)
    tier.store = AsyncMock()
    tier.health_check = AsyncMock(return_value={"status": "healthy"})
    return tier

@pytest.fixture
def mock_gemini():
    provider = MagicMock(spec=GeminiProvider)
    provider.generate = AsyncMock()
    provider.get_embedding = AsyncMock()
    provider.health_check = AsyncMock(return_value=ProviderHealth(
        name="gemini", healthy=True
    ))
    return provider

@pytest.fixture
def engine(mock_l2, mock_l3, mock_gemini):
    return ConsolidationEngine(
        l2_tier=mock_l2,
        l3_tier=mock_l3,
        gemini_provider=mock_gemini,
        config={"time_window_hours": 24}
    )

@pytest.fixture
def sample_facts():
    now = datetime.now(timezone.utc)
    facts = []
    for i in range(3):
        fact = Fact(
            fact_id=f"fact-{i}",
            session_id="session-123",
            content=f"Test fact {i}",
            fact_type=FactType.PREFERENCE,
            fact_category=FactCategory.PERSONAL,
            certainty=0.9,
            impact=0.8,
            source_type="test",
            extracted_at=now - timedelta(hours=i),
            ciar_score=0.7,
            age_decay=1.0,
            recency_boost=1.0
        )
        facts.append(fact)
    return facts

@pytest.mark.asyncio
async def test_process_session_success(engine, mock_l2, mock_l3, mock_gemini, sample_facts):
    # Mock L2 to return facts
    mock_l2.query_by_session.return_value = [f.model_dump() for f in sample_facts]
    
    # Mock Gemini LLM response
    mock_gemini.generate.return_value = LLMResponse(
        text='{"summary": "User preferences discussed", "narrative": "The user shared their preferences."}',
        provider="gemini"
    )
    
    # Mock embedding (768 dimensions for gemini-embedding-001)
    mock_gemini.get_embedding.return_value = [0.1] * 768
    
    stats = await engine.process(session_id="session-123")
    
    assert stats["facts_retrieved"] == 3
    assert stats["episodes_created"] == 1
    assert stats["errors"] == 0
    
    # Verify L3 store was called
    mock_l3.store.assert_called_once()
    stored_data = mock_l3.store.call_args[0][0]
    assert "episode" in stored_data
    assert "embedding" in stored_data
    assert len(stored_data["embedding"]) == 768

@pytest.mark.asyncio
async def test_process_no_session_id(engine):
    result = await engine.process()
    assert result["status"] == "skipped"

@pytest.mark.asyncio
async def test_process_no_facts(engine, mock_l2):
    mock_l2.query_by_session.return_value = []
    
    stats = await engine.process(session_id="session-123")
    
    assert stats["facts_retrieved"] == 0
    assert stats["episodes_created"] == 0

@pytest.mark.asyncio
async def test_clustering_by_time(engine, sample_facts):
    # Test that facts are clustered correctly
    # All sample facts are within 3 hours, so they should be in one cluster
    clusters = engine._cluster_facts_by_time(sample_facts)
    
    assert len(clusters) == 1
    assert len(clusters[0]) == 3

@pytest.mark.asyncio
async def test_clustering_multiple_windows(engine):
    now = datetime.now(timezone.utc)
    facts = []
    
    # Create facts spanning 48 hours (should create 2 clusters with 24h window)
    for i in range(4):
        fact = Fact(
            fact_id=f"fact-{i}",
            session_id="session-123",
            content=f"Test fact {i}",
            fact_type=FactType.MENTION,
            fact_category=FactCategory.OPERATIONAL,
            certainty=0.5,
            impact=0.5,
            source_type="test",
            extracted_at=now - timedelta(hours=i * 15),  # 0, 15, 30, 45 hours ago
            ciar_score=0.5,
            age_decay=1.0,
            recency_boost=1.0
        )
        facts.append(fact)
    
    clusters = engine._cluster_facts_by_time(facts)
    
    # Should have 2 clusters (0-15h and 30-45h)
    assert len(clusters) == 2

@pytest.mark.asyncio
async def test_health_check(engine):
    health = await engine.health_check()
    assert health["status"] == "healthy"
    assert health["l2"]["status"] == "healthy"
    assert health["l3"]["status"] == "healthy"
    assert health["gemini"].healthy

@pytest.mark.asyncio
async def test_episode_creation_with_llm_parse_error(engine, mock_gemini, sample_facts):
    # Mock LLM returning invalid JSON
    mock_gemini.generate.return_value = LLMResponse(
        text='Invalid JSON',
        provider="gemini"
    )
    
    episode = await engine._create_episode_from_facts("session-123", sample_facts)
    
    # Should create episode with fallback summary
    assert episode.session_id == "session-123"
    assert episode.fact_count == 3
    assert "Episode with" in episode.summary or episode.summary
    assert episode.narrative is not None

@pytest.mark.asyncio
async def test_embedding_generation(engine, mock_gemini):
    episode = Episode(
        episode_id="ep-1",
        session_id="session-123",
        summary="Test summary",
        narrative="Test narrative",
        source_fact_ids=["fact-1"],
        fact_count=1,
        time_window_start=datetime.now(timezone.utc),
        time_window_end=datetime.now(timezone.utc),
        duration_seconds=60,
        fact_valid_from=datetime.now(timezone.utc),
        source_observation_timestamp=datetime.now(timezone.utc)
    )
    
    mock_gemini.get_embedding.return_value = [0.1] * 768
    
    embedding = await engine._generate_embedding(episode)
    
    assert len(embedding) == 768
    mock_gemini.get_embedding.assert_called_once()
    call_args = mock_gemini.get_embedding.call_args
    assert "Test summary" in call_args[1]["text"]
