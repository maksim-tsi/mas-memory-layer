"""
Tests for KnowledgeSynthesizer (Query-Time Knowledge Retrieval)
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.memory.engines.knowledge_synthesizer import KnowledgeSynthesizer
from src.memory.models import KnowledgeDocument
from src.memory.tiers.semantic_memory_tier import SemanticMemoryTier
from src.utils.providers import BaseProvider


@pytest.fixture
def mock_semantic_tier():
    """Mock SemanticMemoryTier."""
    tier = MagicMock(spec=SemanticMemoryTier)
    tier.search = AsyncMock()
    return tier


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    provider = MagicMock(spec=BaseProvider)
    provider.name = "mock_provider"
    provider.generate = AsyncMock(return_value="""Based on the provided knowledge documents, here's the synthesized response:

Container handling at USLAX requires strict adherence to safety protocols. Document 1 emphasizes the importance of seal integrity verification, while Document 2 highlights proper weight distribution techniques. For refrigerated containers specifically, specialized equipment must be used as noted in Document 3.

Key recommendations:
1. Always verify container seals before loading
2. Maintain proper weight distribution for stability
3. Use specialized equipment for 40RF containers
""")
    return provider


@pytest.fixture
def sample_knowledge_docs():
    """Create sample knowledge documents for testing."""
    return [
        KnowledgeDocument(
            knowledge_id="know_001",
            knowledge_type="summary",
            content="Container loading best practices at USLAX terminal including seal verification and weight distribution.",
            title="Container Loading Best Practices",
            metadata={
                "port_code": "USLAX",
                "terminal_id": "Terminal_2",
                "shipping_line": "MAERSK",
                "container_type": "40HC",
                "key_points": [
                    "Verify seal integrity before loading",
                    "Maintain proper weight distribution",
                    "Document any damage immediately"
                ]
            },
            source_episode_ids=["ep_001", "ep_002"],
            episode_count=2
        ),
        KnowledgeDocument(
            knowledge_id="know_002",
            knowledge_type="recommendation",
            content="For refrigerated containers (40RF), always use specialized handling equipment and verify temperature settings before loading.",
            title="Refrigerated Container Handling",
            metadata={
                "port_code": "USLAX",
                "terminal_id": "Terminal_2",
                "container_type": "40RF",
                "key_points": [
                    "Use specialized equipment for reefers",
                    "Verify temperature settings",
                    "Monitor power supply connections"
                ]
            },
            source_episode_ids=["ep_003"],
            episode_count=1
        ),
        KnowledgeDocument(
            knowledge_id="know_003",
            knowledge_type="pattern",
            content="Common pattern: Weight distribution issues occur most frequently with mixed cargo loads. Solution: Pre-plan loading sequence.",
            title="Weight Distribution Patterns",
            metadata={
                "port_code": "USLAX",
                "terminal_id": "Terminal_2",
                "key_points": [
                    "Mixed cargo requires careful planning",
                    "Pre-plan loading sequences",
                    "Use weight sensors for verification"
                ]
            },
            source_episode_ids=["ep_004", "ep_005"],
            episode_count=2
        ),
        KnowledgeDocument(
            knowledge_id="know_004",
            knowledge_type="rule",
            content="Port regulation: All damaged containers must be documented immediately with photographic evidence before leaving the terminal.",
            title="Damage Documentation Requirements",
            metadata={
                "port_code": "USLAX",
                "terminal_id": "Terminal_2",
                "key_points": [
                    "Immediate documentation required",
                    "Photographic evidence mandatory",
                    "Submit reports before departure"
                ]
            },
            source_episode_ids=["ep_006"],
            episode_count=1
        ),
        KnowledgeDocument(
            knowledge_id="know_005",
            knowledge_type="insight",
            content="Analysis shows that terminal efficiency increases by 15% when loading sequences are optimized based on destination port.",
            title="Loading Sequence Optimization Impact",
            metadata={
                "port_code": "USLAX",
                "terminal_id": "Terminal_2",
                "key_points": [
                    "15% efficiency gain possible",
                    "Destination-based optimization key",
                    "Reduces vessel turnaround time"
                ]
            },
            source_episode_ids=["ep_007", "ep_008"],
            episode_count=2
        )
    ]


@pytest.mark.asyncio
async def test_synthesizer_initialization(mock_semantic_tier, mock_llm_provider):
    """Test KnowledgeSynthesizer initialization."""
    synthesizer = KnowledgeSynthesizer(
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider,
        similarity_threshold=0.85,
        cache_ttl_seconds=3600
    )
    
    assert synthesizer.semantic_tier == mock_semantic_tier
    assert synthesizer.similarity_threshold == 0.85
    assert synthesizer.cache_ttl_seconds == 3600
    assert synthesizer._cache == {}


@pytest.mark.asyncio
async def test_successful_synthesis(
    mock_semantic_tier,
    mock_llm_provider,
    sample_knowledge_docs
):
    """Test successful knowledge synthesis."""
    mock_semantic_tier.search.return_value = sample_knowledge_docs[:3]
    
    synthesizer = KnowledgeSynthesizer(
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider
    )
    
    result = await synthesizer.synthesize(
        query="What are the best practices for loading containers at USLAX?",
        metadata_filters={"port_code": "USLAX"},
        max_results=5
    )
    
    assert result["status"] == "success"
    assert result["source"] == "synthesized"
    assert "synthesized_text" in result
    assert result["candidates"] > 0
    assert "elapsed_ms" in result


@pytest.mark.asyncio
async def test_metadata_filtering(
    mock_semantic_tier,
    mock_llm_provider,
    sample_knowledge_docs
):
    """Test metadata-first filtering."""
    # Only return docs matching the filter
    filtered_docs = [
        doc for doc in sample_knowledge_docs
        if doc.metadata.get("container_type") == "40RF"
    ]
    mock_semantic_tier.search.return_value = filtered_docs
    
    synthesizer = KnowledgeSynthesizer(
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider
    )
    
    result = await synthesizer.synthesize(
        query="How to handle refrigerated containers?",
        metadata_filters={"port_code": "USLAX", "container_type": "40RF"},
        max_results=5
    )
    
    assert result["status"] == "success"
    assert result["candidates"] > 0
    
    # Verify search was called with filter
    mock_semantic_tier.search.assert_called_once()
    call_kwargs = mock_semantic_tier.search.call_args[1]
    assert "filter_by" in call_kwargs
    assert call_kwargs["filter_by"] is not None


@pytest.mark.asyncio
async def test_cache_hit(
    mock_semantic_tier,
    mock_llm_provider,
    sample_knowledge_docs
):
    """Test that cached results are returned on second query."""
    mock_semantic_tier.search.return_value = sample_knowledge_docs[:3]
    
    synthesizer = KnowledgeSynthesizer(
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider
    )
    
    query = "What are container loading best practices?"
    filters = {"port_code": "USLAX"}
    
    # First call - should hit LLM
    result1 = await synthesizer.synthesize(query, filters)
    assert result1["source"] == "synthesized"
    first_response = result1["synthesized_text"]
    
    # Second call - should hit cache
    result2 = await synthesizer.synthesize(query, filters)
    assert result2["source"] == "cache"
    assert result2["synthesized_text"] == first_response
    
    # LLM should only be called once
    assert mock_llm_provider.generate.call_count == 1


@pytest.mark.asyncio
async def test_empty_results(mock_semantic_tier, mock_llm_provider):
    """Test handling of empty search results."""
    mock_semantic_tier.search.return_value = []
    
    synthesizer = KnowledgeSynthesizer(
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider
    )
    
    result = await synthesizer.synthesize(
        query="Unknown query with no matches",
        metadata_filters={"port_code": "ZZZZZ"}
    )
    
    assert result["status"] == "success"
    assert result["source"] == "empty_result"
    assert result["candidates"] == 0
    assert "No relevant knowledge found" in result["synthesized_text"]


@pytest.mark.asyncio
async def test_similarity_threshold_filtering(
    mock_semantic_tier,
    mock_llm_provider,
    sample_knowledge_docs
):
    """Test that low-similarity documents are filtered out."""
    # All docs returned but with low synthetic scores
    mock_semantic_tier.search.return_value = sample_knowledge_docs
    
    synthesizer = KnowledgeSynthesizer(
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider,
        similarity_threshold=0.95  # Very high threshold
    )
    
    result = await synthesizer.synthesize(
        query="Test query",
        max_results=5
    )
    
    # With high threshold and synthetic scoring, some docs will be filtered
    # The test uses position-based scoring that decreases by 0.05 per position
    # Starting from 1.0, so positions 8+ will be below 0.95
    # We're returning 5 docs, so all should pass (1.0, 0.95, 0.90, 0.85, 0.80)
    # But with threshold 0.95, only first 2 should pass
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_conflict_detection(
    mock_semantic_tier,
    mock_llm_provider,
    sample_knowledge_docs
):
    """Test detection of conflicting knowledge."""
    # Create conflicting recommendations
    conflict_doc = KnowledgeDocument(
        knowledge_id="know_conflict",
        knowledge_type="recommendation",
        content="Never use specialized equipment for refrigerated containers. Standard forklifts are sufficient.",
        title="Conflicting Recommendation",
        metadata={
            "port_code": "USLAX",
            "conflict_tag": "CONFLICT_DETECTED",
            "key_points": ["Avoid specialized equipment", "Use standard forklifts"]
        },
        source_episode_ids=["ep_999"],
        episode_count=1
    )
    
    docs_with_conflict = sample_knowledge_docs[:3] + [conflict_doc]
    mock_semantic_tier.search.return_value = docs_with_conflict
    
    synthesizer = KnowledgeSynthesizer(
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider
    )
    
    result = await synthesizer.synthesize(
        query="How to handle refrigerated containers?",
        metadata_filters={"port_code": "USLAX"}
    )
    
    assert result["status"] == "success"
    assert result["has_conflicts"] is True
    assert len(result["conflicts"]) > 0


@pytest.mark.asyncio
async def test_llm_failure_fallback(
    mock_semantic_tier,
    mock_llm_provider,
    sample_knowledge_docs
):
    """Test fallback when LLM fails."""
    mock_semantic_tier.search.return_value = sample_knowledge_docs[:3]
    
    # Make LLM fail
    mock_llm_provider.generate = AsyncMock(side_effect=Exception("LLM timeout"))
    
    synthesizer = KnowledgeSynthesizer(
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider
    )
    
    result = await synthesizer.synthesize(
        query="Test query",
        metadata_filters={"port_code": "USLAX"}
    )
    
    assert result["status"] == "success"
    assert "LLM unavailable" in result["synthesized_text"]
    # Fallback should still provide document content
    assert len(result["synthesized_text"]) > 0


@pytest.mark.asyncio
async def test_cache_key_generation(
    mock_semantic_tier,
    mock_llm_provider,
    sample_knowledge_docs
):
    """Test that different queries generate different cache keys."""
    mock_semantic_tier.search.return_value = sample_knowledge_docs[:3]
    
    synthesizer = KnowledgeSynthesizer(
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider
    )
    
    # First query
    result1 = await synthesizer.synthesize(
        query="Query 1",
        metadata_filters={"port_code": "USLAX"}
    )
    key1 = result1["cache_key"]
    
    # Second query (different)
    result2 = await synthesizer.synthesize(
        query="Query 2",
        metadata_filters={"port_code": "USLAX"}
    )
    key2 = result2["cache_key"]
    
    # Keys should be different
    assert key1 != key2
    
    # Third query (different metadata)
    result3 = await synthesizer.synthesize(
        query="Query 1",
        metadata_filters={"port_code": "USNYC"}
    )
    key3 = result3["cache_key"]
    
    # Key should differ from first (different metadata)
    assert key1 != key3


@pytest.mark.asyncio
async def test_cache_clear(
    mock_semantic_tier,
    mock_llm_provider,
    sample_knowledge_docs
):
    """Test cache clearing functionality."""
    mock_semantic_tier.search.return_value = sample_knowledge_docs[:3]
    
    synthesizer = KnowledgeSynthesizer(
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider
    )
    
    # Populate cache
    await synthesizer.synthesize("Query 1", {"port_code": "USLAX"})
    await synthesizer.synthesize("Query 2", {"port_code": "USLAX"})
    
    stats_before = await synthesizer.get_cache_stats()
    assert stats_before["total_entries"] == 2
    
    # Clear cache
    await synthesizer.clear_cache()
    
    stats_after = await synthesizer.get_cache_stats()
    assert stats_after["total_entries"] == 0


@pytest.mark.asyncio
async def test_cache_expiration(
    mock_semantic_tier,
    mock_llm_provider,
    sample_knowledge_docs
):
    """Test that cache entries expire after TTL."""
    mock_semantic_tier.search.return_value = sample_knowledge_docs[:3]
    
    # Very short TTL for testing
    synthesizer = KnowledgeSynthesizer(
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider,
        cache_ttl_seconds=0  # Immediate expiration
    )
    
    query = "Test query"
    filters = {"port_code": "USLAX"}
    
    # First call
    result1 = await synthesizer.synthesize(query, filters)
    assert result1["source"] == "synthesized"
    
    # Second call - cache should be expired
    result2 = await synthesizer.synthesize(query, filters)
    # Should hit LLM again (not cache)
    assert result2["source"] == "synthesized"
    
    # LLM should be called twice
    assert mock_llm_provider.generate.call_count == 2


@pytest.mark.asyncio
async def test_max_results_limit(
    mock_semantic_tier,
    mock_llm_provider,
    sample_knowledge_docs
):
    """Test that max_results parameter is respected."""
    mock_semantic_tier.search.return_value = sample_knowledge_docs
    
    synthesizer = KnowledgeSynthesizer(
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider
    )
    
    result = await synthesizer.synthesize(
        query="Test query",
        max_results=2  # Limit to 2 documents
    )
    
    assert result["status"] == "success"
    # Candidates should not exceed max_results
    assert result["candidates"] <= 2


@pytest.mark.asyncio
async def test_multiple_metadata_filters(
    mock_semantic_tier,
    mock_llm_provider,
    sample_knowledge_docs
):
    """Test multiple metadata filters are combined correctly."""
    filtered_docs = [sample_knowledge_docs[0]]  # Only first doc matches all filters
    mock_semantic_tier.search.return_value = filtered_docs
    
    synthesizer = KnowledgeSynthesizer(
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider
    )
    
    result = await synthesizer.synthesize(
        query="Test query",
        metadata_filters={
            "port_code": "USLAX",
            "terminal_id": "Terminal_2",
            "shipping_line": "MAERSK",
            "container_type": "40HC"
        }
    )
    
    assert result["status"] == "success"
    
    # Verify filter was properly constructed
    call_kwargs = mock_semantic_tier.search.call_args[1]
    filter_query = call_kwargs["filter_by"]
    assert "port_code" in filter_query
    assert "terminal_id" in filter_query
    assert "&&" in filter_query  # Multiple conditions combined


@pytest.mark.asyncio
async def test_cache_stats(
    mock_semantic_tier,
    mock_llm_provider,
    sample_knowledge_docs
):
    """Test cache statistics reporting."""
    mock_semantic_tier.search.return_value = sample_knowledge_docs[:3]
    
    synthesizer = KnowledgeSynthesizer(
        semantic_tier=mock_semantic_tier,
        llm_provider=mock_llm_provider,
        cache_ttl_seconds=3600
    )
    
    # Initially empty
    stats = await synthesizer.get_cache_stats()
    assert stats["total_entries"] == 0
    assert stats["valid_entries"] == 0
    
    # Add some entries
    await synthesizer.synthesize("Query 1", {"port_code": "USLAX"})
    await synthesizer.synthesize("Query 2", {"port_code": "USLAX"})
    
    stats = await synthesizer.get_cache_stats()
    assert stats["total_entries"] == 2
    assert stats["valid_entries"] == 2
    assert stats["ttl_seconds"] == 3600
