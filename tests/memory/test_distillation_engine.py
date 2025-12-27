"""
Tests for DistillationEngine (L3 → L4 Knowledge Creation)
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.memory.engines.distillation_engine import DistillationEngine
from src.memory.models import Episode, KnowledgeDocument
from src.memory.tiers.episodic_memory_tier import EpisodicMemoryTier
from src.memory.tiers.semantic_memory_tier import SemanticMemoryTier
from src.utils.providers import BaseProvider
from src.utils.llm_client import LLMResponse


@pytest.fixture
def mock_episodic_tier():
    """Mock EpisodicMemoryTier."""
    tier = MagicMock(spec=EpisodicMemoryTier)
    tier.health_check = AsyncMock(return_value={"status": "healthy"})
    tier.query_temporal = AsyncMock()
    tier.query = AsyncMock()
    return tier


@pytest.fixture
def mock_semantic_tier():
    """Mock SemanticMemoryTier."""
    tier = MagicMock(spec=SemanticMemoryTier)
    tier.health_check = AsyncMock(return_value={"status": "healthy"})
    tier.store = AsyncMock(return_value="doc_123")
    return tier


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    provider = MagicMock(spec=BaseProvider)
    provider.name = "mock_provider"
    provider.generate = AsyncMock(return_value=LLMResponse(
        text="""Title: Container Handling Best Practices

This knowledge document summarizes key patterns from recent container operations.

Key_points:
- Always verify container seal integrity before loading
- Maintain proper weight distribution for stability
- Use specialized equipment for refrigerated containers
- Document any damage immediately
- Follow port-specific loading sequences
""",
        provider="mock_provider"
    ))
    return provider


@pytest.fixture
def sample_episodes():
    """Create sample episodes for testing."""
    return [
        Episode(
            episode_id="ep_001",
            session_id="session_001",
            summary="Container loading at USLAX terminal",
            source_fact_ids=["fact_001", "fact_002", "fact_003"],
            entities=[{"name": "USLAX"}, {"name": "MAERSK"}, {"name": "40HC"}, {"name": "Terminal_2"}],
            time_window_start=datetime(2025, 12, 20, 10, 0, 0),
            time_window_end=datetime(2025, 12, 20, 12, 0, 0),
            fact_valid_from=datetime(2025, 12, 20, 10, 0, 0),
            source_observation_timestamp=datetime(2025, 12, 20, 12, 0, 0),
            metadata={
                "port_code": "USLAX",
                "shipping_line": "MAERSK",
                "container_type": "40HC",
                "terminal_id": "Terminal_2"
            }
        ),
        Episode(
            episode_id="ep_002",
            session_id="session_001",
            summary="Refrigerated container inspection",
            source_fact_ids=["fact_004", "fact_005"],
            entities=[{"name": "USLAX"}, {"name": "40RF"}, {"name": "temperature_control"}],
            time_window_start=datetime(2025, 12, 20, 14, 0, 0),
            time_window_end=datetime(2025, 12, 20, 15, 0, 0),
            fact_valid_from=datetime(2025, 12, 20, 14, 0, 0),
            source_observation_timestamp=datetime(2025, 12, 20, 15, 0, 0),
            metadata={
                "port_code": "USLAX",
                "container_type": "40RF",
                "terminal_id": "Terminal_2"
            }
        ),
        Episode(
            episode_id="ep_003",
            session_id="session_001",
            summary="Weight distribution issue resolution",
            source_fact_ids=["fact_006", "fact_007", "fact_008"],
            entities=[{"name": "USLAX"}, {"name": "MSC"}, {"name": "container_stacking"}],
            time_window_start=datetime(2025, 12, 20, 16, 0, 0),
            time_window_end=datetime(2025, 12, 20, 17, 0, 0),
            fact_valid_from=datetime(2025, 12, 20, 16, 0, 0),
            source_observation_timestamp=datetime(2025, 12, 20, 17, 0, 0),
            metadata={
                "port_code": "USLAX",
                "shipping_line": "MSC",
                "terminal_id": "Terminal_2"
            }
        ),
        Episode(
            episode_id="ep_004",
            session_id="session_002",
            summary="Damaged container documentation",
            source_fact_ids=["fact_009", "fact_010"],
            entities=[{"name": "USLAX"}, {"name": "damage_report"}, {"name": "insurance"}],
            time_window_start=datetime(2025, 12, 21, 9, 0, 0),
            time_window_end=datetime(2025, 12, 21, 10, 0, 0),
            fact_valid_from=datetime(2025, 12, 21, 9, 0, 0),
            source_observation_timestamp=datetime(2025, 12, 21, 10, 0, 0),
            metadata={
                "port_code": "USLAX",
                "terminal_id": "Terminal_2"
            }
        ),
        Episode(
            episode_id="ep_005",
            session_id="session_002",
            summary="Loading sequence optimization",
            source_fact_ids=["fact_011", "fact_012", "fact_013"],
            entities=[{"name": "USLAX"}, {"name": "loading_plan"}, {"name": "efficiency"}],
            time_window_start=datetime(2025, 12, 21, 11, 0, 0),
            time_window_end=datetime(2025, 12, 21, 13, 0, 0),
            fact_valid_from=datetime(2025, 12, 21, 11, 0, 0),
            source_observation_timestamp=datetime(2025, 12, 21, 13, 0, 0),
            metadata={
                "port_code": "USLAX",
                "terminal_id": "Terminal_2"
            }
        )
    ]


@pytest.mark.asyncio
async def test_distillation_engine_initialization(
    mock_episodic_tier,
    mock_semantic_tier,
    mock_llm_provider
):
    """Test DistillationEngine initialization."""
    engine = DistillationEngine(
        episodic_tier=mock_episodic_tier,
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider,
        episode_threshold=3
    )
    
    assert engine.episodic_tier == mock_episodic_tier
    assert engine.semantic_tier == mock_semantic_tier
    assert engine.episode_threshold == 3
    assert engine.llm_client is not None
    assert engine.domain_config is not None


@pytest.mark.asyncio
async def test_below_threshold_skip(
    mock_episodic_tier,
    mock_semantic_tier,
    mock_llm_provider,
    sample_episodes
):
    """Test that distillation is skipped when below episode threshold."""
    # Return only 2 episodes (below threshold of 5)
    mock_episodic_tier.query.return_value = sample_episodes[:2]
    
    engine = DistillationEngine(
        episodic_tier=mock_episodic_tier,
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider,
        episode_threshold=5
    )
    
    result = await engine.process()
    
    assert result["status"] == "skipped"
    assert result["reason"] == "below_threshold"
    assert result["episode_count"] == 2
    assert result["threshold"] == 5


@pytest.mark.asyncio
async def test_force_process_override(
    mock_episodic_tier,
    mock_semantic_tier,
    mock_llm_provider,
    sample_episodes
):
    """Test that force_process=True overrides threshold check."""
    mock_episodic_tier.query.return_value = sample_episodes[:2]
    
    engine = DistillationEngine(
        episodic_tier=mock_episodic_tier,
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider,
        episode_threshold=5
    )
    
    result = await engine.process(force_process=True)
    
    assert result["status"] == "success"
    assert result["processed_episodes"] == 2
    assert result["created_documents"] > 0


@pytest.mark.asyncio
async def test_successful_distillation(
    mock_episodic_tier,
    mock_semantic_tier,
    mock_llm_provider,
    sample_episodes
):
    """Test successful distillation of episodes into knowledge documents."""
    mock_episodic_tier.query.return_value = sample_episodes
    
    engine = DistillationEngine(
        episodic_tier=mock_episodic_tier,
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider,
        episode_threshold=3
    )
    
    result = await engine.process()
    
    assert result["status"] == "success"
    assert result["processed_episodes"] == 5
    assert result["created_documents"] > 0
    
    # Should create documents for each knowledge type (5 types in default config)
    assert result["created_documents"] == 5
    
    # Verify semantic tier was called for each document
    assert mock_semantic_tier.store.call_count == 5


@pytest.mark.asyncio
async def test_session_filter(
    mock_episodic_tier,
    mock_semantic_tier,
    mock_llm_provider,
    sample_episodes
):
    """Test filtering episodes by session_id."""
    mock_episodic_tier.query.return_value = sample_episodes
    
    engine = DistillationEngine(
        episodic_tier=mock_episodic_tier,
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider,
        episode_threshold=3
    )
    
    result = await engine.process(session_id="session_001")
    
    # Only 3 episodes belong to session_001
    assert result["processed_episodes"] == 3


@pytest.mark.asyncio
async def test_metadata_extraction(
    mock_episodic_tier,
    mock_semantic_tier,
    mock_llm_provider,
    sample_episodes
):
    """Test extraction of metadata from episodes."""
    mock_episodic_tier.query.return_value = sample_episodes
    
    # Track the stored documents
    stored_docs = []
    async def capture_store(doc):
        stored_docs.append(doc)
        return f"doc_{len(stored_docs)}"
    
    mock_semantic_tier.store = AsyncMock(side_effect=capture_store)
    
    engine = DistillationEngine(
        episodic_tier=mock_episodic_tier,
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider,
        episode_threshold=3
    )
    
    result = await engine.process()
    
    assert result["status"] == "success"
    assert len(stored_docs) > 0
    
    # Check first document has expected metadata
    first_doc = stored_docs[0]
    assert isinstance(first_doc, KnowledgeDocument)
    assert first_doc.metadata is not None
    assert "port_code" in first_doc.metadata
    assert first_doc.metadata["port_code"] == "USLAX"
    assert first_doc.metadata["source_episode_count"] == 5


@pytest.mark.asyncio
async def test_provenance_tracking(
    mock_episodic_tier,
    mock_semantic_tier,
    mock_llm_provider,
    sample_episodes
):
    """Test that source episode IDs are tracked in knowledge documents."""
    mock_episodic_tier.query.return_value = sample_episodes
    
    stored_docs = []
    async def capture_store(doc):
        stored_docs.append(doc)
        return f"doc_{len(stored_docs)}"
    
    mock_semantic_tier.store = AsyncMock(side_effect=capture_store)
    
    engine = DistillationEngine(
        episodic_tier=mock_episodic_tier,
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider,
        episode_threshold=3
    )
    
    await engine.process()
    
    # Check provenance
    for doc in stored_docs:
        assert len(doc.source_episode_ids) == 5
        assert "ep_001" in doc.source_episode_ids
        assert "ep_005" in doc.source_episode_ids


@pytest.mark.asyncio
async def test_llm_failure_handling(
    mock_episodic_tier,
    mock_semantic_tier,
    mock_llm_provider,
    sample_episodes
):
    """Test handling of LLM failures during synthesis."""
    mock_episodic_tier.query.return_value = sample_episodes
    
    # Make LLM fail
    mock_llm_provider.generate = AsyncMock(side_effect=Exception("LLM timeout"))
    
    engine = DistillationEngine(
        episodic_tier=mock_episodic_tier,
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider,
        episode_threshold=3
    )
    
    result = await engine.process()
    
    # Should complete with 0 documents created (all failed)
    assert result["status"] == "success"
    assert result["created_documents"] == 0


@pytest.mark.asyncio
async def test_health_check(
    mock_episodic_tier,
    mock_semantic_tier,
    mock_llm_provider
):
    """Test health check of distillation engine."""
    engine = DistillationEngine(
        episodic_tier=mock_episodic_tier,
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider
    )
    
    health = await engine.health_check()
    
    assert health["service"] == "DistillationEngine"
    assert health["status"] == "healthy"
    assert health["checks"]["episodic_tier"] is True
    assert health["checks"]["semantic_tier"] is True
    assert health["checks"]["llm_client"] is True


@pytest.mark.asyncio
async def test_health_check_degraded(
    mock_episodic_tier,
    mock_semantic_tier,
    mock_llm_provider
):
    """Test degraded health when a component is unhealthy."""
    # Make semantic tier unhealthy
    mock_semantic_tier.health_check = AsyncMock(return_value={"status": "unhealthy"})
    
    engine = DistillationEngine(
        episodic_tier=mock_episodic_tier,
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider
    )
    
    health = await engine.health_check()
    
    assert health["status"] == "degraded"
    assert health["checks"]["semantic_tier"] is False


@pytest.mark.asyncio
async def test_multiple_knowledge_types(
    mock_episodic_tier,
    mock_semantic_tier,
    mock_llm_provider,
    sample_episodes
):
    """Test that all knowledge types are generated."""
    mock_episodic_tier.query.return_value = sample_episodes
    
    stored_docs = []
    async def capture_store(doc):
        stored_docs.append(doc)
        return f"doc_{len(stored_docs)}"
    
    mock_semantic_tier.store = AsyncMock(side_effect=capture_store)
    
    engine = DistillationEngine(
        episodic_tier=mock_episodic_tier,
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider,
        episode_threshold=3
    )
    
    await engine.process()
    
    # Should have 5 different knowledge types
    knowledge_types = [doc.knowledge_type for doc in stored_docs]
    assert "summary" in knowledge_types
    assert "insight" in knowledge_types
    assert "pattern" in knowledge_types
    assert "recommendation" in knowledge_types
    assert "rule" in knowledge_types


@pytest.mark.asyncio
async def test_metrics_collection(
    mock_episodic_tier,
    mock_semantic_tier,
    mock_llm_provider,
    sample_episodes
):
    """Test that metrics are collected during processing."""
    mock_episodic_tier.query.return_value = sample_episodes
    
    engine = DistillationEngine(
        episodic_tier=mock_episodic_tier,
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider,
        episode_threshold=3,
        metrics_enabled=True
    )
    
    result = await engine.process()
    
    assert "elapsed_ms" in result
    assert result["elapsed_ms"] > 0
    
    # Get metrics
    metrics = await engine.get_metrics()
    assert "distillation" in metrics["operations"]
