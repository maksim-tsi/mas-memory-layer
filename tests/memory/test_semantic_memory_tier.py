"""
Tests for L4 Semantic Memory Tier.

Tests distilled knowledge document storage, full-text search,
faceted filtering, and provenance tracking.
"""

import warnings
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from pydantic import ValidationError

from src.memory.models import KnowledgeDocument
from src.memory.tiers.semantic_memory_tier import SemanticMemoryTier
from src.storage.typesense_adapter import TypesenseAdapter


@pytest.fixture
def mock_typesense_adapter():
    """Mock Typesense adapter for testing."""
    adapter = AsyncMock(spec=TypesenseAdapter)
    adapter.initialize = AsyncMock()
    adapter.connect = AsyncMock()
    adapter.disconnect = AsyncMock()
    adapter.index_document = AsyncMock()
    adapter.get_document = AsyncMock(return_value=None)
    adapter.search = AsyncMock(return_value={"hits": []})
    adapter.update_document = AsyncMock()
    adapter.delete_document = AsyncMock()
    adapter.health_check = AsyncMock(return_value={"status": "healthy"})
    return adapter


@pytest_asyncio.fixture
async def semantic_tier(mock_typesense_adapter, monkeypatch):
    """Fixture providing configured L4 tier."""
    monkeypatch.setenv("MAS_V2_MODE", "false")
    tier = SemanticMemoryTier(
        typesense_adapter=mock_typesense_adapter, config={"collection_name": "knowledge_test"}
    )
    await tier.initialize()
    return tier


def test_semantic_tier_syncs_versioned_collection_to_adapter(
    mock_typesense_adapter, monkeypatch
):
    """Adapter schema reconciliation must target the tier's resolved collection."""
    monkeypatch.setenv("MAS_V2_MODE", "true")

    tier = SemanticMemoryTier(
        typesense_adapter=mock_typesense_adapter,
        config={
            "collection_name": "yaam-scm-cognitive-sandwich",
            "project_id": "scm-cognitive-sandwich",
        },
    )

    assert tier.collection_name == "yaam-scm-cognitive-sandwich_v2"
    assert mock_typesense_adapter.collection_name == tier.collection_name


@pytest.fixture
def sample_knowledge():
    """Sample knowledge document for testing."""
    return KnowledgeDocument(
        knowledge_id="know_001",
        title="User prefers morning meetings",
        content="Based on multiple interactions, the user consistently schedules meetings in the morning hours (8-11 AM) and mentions being most productive during this time.",
        knowledge_type="preference",
        confidence_score=0.85,
        source_episode_ids=["ep_001", "ep_002", "ep_005"],
        episode_count=3,
        provenance_links=["session_1", "session_2"],
        category="personal",
        tags=["scheduling", "preferences", "productivity"],
        domain="work-habits",
        distilled_at=datetime.now(UTC),
        access_count=0,
        usefulness_score=0.7,
        validation_count=0,
    )


def test_knowledge_document_typesense_document_preserves_cognitive_sandwich_metadata():
    """L4 must index only canonical Cognitive Sandwich metadata for domain views."""
    knowledge = KnowledgeDocument(
        knowledge_id="know_cognitive_001",
        title="Cognitive Sandwich artifact repair report",
        content="Final report for a repaired Cognitive Sandwich artifact.",
        metadata={
            "domain": "cognitive_sandwich",
            "project_id": "scm-cognitive-sandwich",
            "client_session_id": "session-readiness-001",
            "artifact_id": "artifact-readiness-001",
            "revision_id": "revision-002",
            "parent_revision_id": "revision-001",
            "feedback_id": "feedback-001",
            "commit_id": "commit-001",
            "run_id": "artifact-run-001",
            "thread_id": "thread-001",
            "incident_id": "incident-readiness-001",
            "scenario_id": "scenario-readiness-001",
            "artifact_kind": "milp_model",
            "artifact_status": "committed",
            "revision_number": "2",
            "verification_state": "feasible",
            "feedback_type": "solver_iis",
            "source_system": "scm-cognitive-sandwich",
            "payload_hash": "sha256:repair",
            "fatal_status": "resolved",
            "retry_count": 1,
            "api_token": "secret",
        },
    )

    document = knowledge.to_typesense_document()

    assert document["domain"] == "cognitive_sandwich"
    assert document["project_id"] == "scm-cognitive-sandwich"
    assert document["artifact_id"] == "artifact-readiness-001"
    assert document["run_id"] == "artifact-run-001"
    assert document["incident_id"] == "incident-readiness-001"
    assert document["revision_number"] == 2
    assert document["retry_count"] == 1
    assert "api_token" not in document


# ============================================
# Store Tests
# ============================================


class TestSemanticMemoryTierStore:
    """Test knowledge document storage."""

    @pytest.mark.asyncio
    async def test_store_knowledge_document(self, semantic_tier, sample_knowledge):
        """Test storing knowledge document."""
        # Store
        knowledge_id = await semantic_tier.store(sample_knowledge)

        # Verify
        assert knowledge_id == "know_001"
        semantic_tier.typesense.index_document.assert_called_once()

        # Verify correct data format
        call_args = semantic_tier.typesense.index_document.call_args
        doc = call_args.kwargs["document"]
        assert doc["id"] == "know_001"
        assert doc["title"] == "User prefers morning meetings"
        assert doc["confidence_score"] == 0.85
        assert "scheduling" in doc["tags"]
        assert doc["project_id"] == "test"

    @pytest.mark.asyncio
    async def test_store_from_dict(self, semantic_tier):
        """Test storing knowledge from dict."""
        knowledge_dict = {
            "knowledge_id": "know_002",
            "title": "Test knowledge",
            "content": "Test content here",
            "knowledge_type": "insight",
            "confidence_score": 0.9,
            "episode_count": 5,
        }

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            knowledge_id = await semantic_tier.store(knowledge_dict)

        assert knowledge_id == "know_002"
        semantic_tier.typesense.index_document.assert_called_once()
        assert any(
            issubclass(warning.category, DeprecationWarning) for warning in captured
        ), "Expected DeprecationWarning for dict input"

    @pytest.mark.asyncio
    async def test_store_validates_data(self, semantic_tier):
        """Test that invalid data is rejected."""
        invalid_dict = {
            "knowledge_id": "know_003",
            "title": "Too short",  # Title must be >= 5 chars, this passes
            "content": "Short",  # Content must be >= 10 chars, this fails
            "confidence_score": 1.5,  # Invalid score > 1.0
        }

        with pytest.raises(ValidationError):
            await semantic_tier.store(invalid_dict)


# ============================================
# Retrieve Tests
# ============================================


class TestSemanticMemoryTierRetrieve:
    """Test knowledge document retrieval."""

    @pytest.mark.asyncio
    async def test_retrieve_existing_knowledge(self, semantic_tier, sample_knowledge):
        """Test retrieving knowledge that exists."""
        # Setup mock response
        now = datetime.now(UTC)
        semantic_tier.typesense.get_document = AsyncMock(
            return_value={
                "id": "know_001",
                "title": "Test knowledge",
                "content": "Test content here with enough characters",
                "knowledge_type": "insight",
                "confidence_score": 0.85,
                "source_episode_ids": ["ep_001"],
                "episode_count": 1,
                "provenance_links": [],
                "category": "technical",
                "tags": ["test"],
                "domain": "testing",
                "project_id": "scm-cognitive-sandwich",
                "client_session_id": "session-readiness-001",
                "artifact_id": "artifact-readiness-001",
                "run_id": "artifact-run-001",
                "incident_id": "incident-readiness-001",
                "revision_number": 2,
                "retry_count": 1,
                "distilled_at": int(now.timestamp()),
                "access_count": 5,
                "usefulness_score": 0.8,
                "validation_count": 2,
            }
        )

        # Mock update for access tracking
        semantic_tier.typesense.update_document = AsyncMock()

        # Retrieve
        knowledge = await semantic_tier.retrieve("know_001")

        # Verify
        assert knowledge is not None
        assert isinstance(knowledge, KnowledgeDocument)
        assert knowledge.knowledge_id == "know_001"
        assert knowledge.title == "Test knowledge"
        assert knowledge.confidence_score == 0.85
        assert knowledge.metadata["project_id"] == "scm-cognitive-sandwich"
        assert knowledge.metadata["client_session_id"] == "session-readiness-001"
        assert knowledge.metadata["artifact_id"] == "artifact-readiness-001"
        assert knowledge.metadata["run_id"] == "artifact-run-001"
        assert knowledge.metadata["incident_id"] == "incident-readiness-001"
        assert knowledge.metadata["revision_number"] == 2
        assert knowledge.metadata["retry_count"] == 1

        # Verify access was updated
        semantic_tier.typesense.update_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_knowledge(self, semantic_tier):
        """Test retrieving knowledge that doesn't exist."""
        semantic_tier.typesense.get_document = AsyncMock(return_value=None)

        knowledge = await semantic_tier.retrieve("nonexistent")

        assert knowledge is None

    @pytest.mark.asyncio
    async def test_retrieve_updates_access_count(self, semantic_tier):
        """Test that retrieval updates access tracking."""
        now = datetime.now(UTC)
        semantic_tier.typesense.get_document = AsyncMock(
            return_value={
                "id": "know_001",
                "title": "Test knowledge",
                "content": "Test content here with enough characters",
                "knowledge_type": "insight",
                "confidence_score": 0.85,
                "episode_count": 1,
                "distilled_at": int(now.timestamp()),
                "access_count": 5,
                "usefulness_score": 0.8,
                "validation_count": 0,
            }
        )
        semantic_tier.typesense.update_document = AsyncMock()

        await semantic_tier.retrieve("know_001")

        # Verify update was called
        semantic_tier.typesense.update_document.assert_called_once()
        call_args = semantic_tier.typesense.update_document.call_args
        updated_doc = call_args.kwargs["document"]

        # Access count should be incremented
        assert updated_doc["access_count"] == 6


# ============================================
# Search Tests
# ============================================


class TestSemanticMemoryTierSearch:
    """Test full-text search."""

    @pytest.mark.asyncio
    async def test_search_by_text(self, semantic_tier):
        """Test full-text search."""
        # Setup mock results
        now = datetime.now(UTC)
        semantic_tier.typesense.search = AsyncMock(
            return_value={
                "hits": [
                    {
                        "document": {
                            "id": "know_001",
                            "title": "Morning meetings preference",
                            "content": "User prefers morning meetings at 9 AM daily",
                            "knowledge_type": "preference",
                            "confidence_score": 0.9,
                            "episode_count": 3,
                            "domain": "cognitive_sandwich",
                            "project_id": "scm-cognitive-sandwich",
                            "client_session_id": "session-readiness-001",
                            "artifact_id": "artifact-readiness-001",
                            "run_id": "artifact-run-001",
                            "incident_id": "incident-readiness-001",
                            "revision_number": 2,
                            "retry_count": 1,
                            "distilled_at": int(now.timestamp()),
                            "access_count": 10,
                            "usefulness_score": 0.85,
                            "validation_count": 2,
                        },
                        "text_match": 0.95,
                    }
                ]
            }
        )

        # Search
        results = await semantic_tier.search(query_text="morning meetings", limit=10)

        # Verify
        assert len(results) == 1
        assert results[0].knowledge_id == "know_001"
        assert results[0].title == "Morning meetings preference"
        assert results[0].metadata["search_score"] == 0.95
        assert results[0].metadata["artifact_id"] == "artifact-readiness-001"
        assert results[0].metadata["run_id"] == "artifact-run-001"
        assert results[0].metadata["incident_id"] == "incident-readiness-001"
        assert results[0].metadata["revision_number"] == 2
        assert results[0].metadata["retry_count"] == 1

        # Verify search was called correctly
        semantic_tier.typesense.search.assert_called_once()
        call_args = semantic_tier.typesense.search.call_args
        assert call_args.kwargs["query"] == "morning meetings"
        assert call_args.kwargs["query_by"] == "title,content"

    @pytest.mark.asyncio
    async def test_search_by_exact_metadata_uses_wildcard_without_sort(
        self, semantic_tier
    ):
        """Deterministic domain projections must not depend on text ranking."""
        now = datetime.now(UTC)
        semantic_tier.typesense.search = AsyncMock(
            return_value={
                "hits": [
                    {
                        "document": {
                            "id": "know_cognitive_001",
                            "title": "Cognitive Sandwich artifact repair report",
                            "content": "Final artifact report.",
                            "knowledge_type": "artifact",
                            "confidence_score": 0.95,
                            "episode_count": 1,
                            "domain": "cognitive_sandwich",
                            "project_id": "scm-cognitive-sandwich",
                            "client_session_id": "session-readiness-001",
                            "artifact_id": "artifact-readiness-001",
                            "run_id": "artifact-run-001",
                            "incident_id": "incident-readiness-001",
                            "distilled_at": int(now.timestamp()),
                            "access_count": 0,
                            "usefulness_score": 0.9,
                            "validation_count": 0,
                        }
                    }
                ]
            }
        )

        results = await semantic_tier.search_by_exact_metadata(
            "project_id:=`scm-cognitive-sandwich` && domain:=`cognitive_sandwich` "
            "&& artifact_id:=`artifact-readiness-001`",
            limit=500,
        )

        assert [result.knowledge_id for result in results] == ["know_cognitive_001"]
        assert results[0].metadata["artifact_id"] == "artifact-readiness-001"
        assert results[0].metadata["run_id"] == "artifact-run-001"
        assert results[0].metadata["incident_id"] == "incident-readiness-001"
        semantic_tier.typesense.search.assert_called_once()
        call_args = semantic_tier.typesense.search.call_args
        assert call_args.kwargs["query"] == "*"
        assert call_args.kwargs["limit"] == 250
        assert call_args.kwargs["sort_by"] is None
        assert "artifact_id:=`artifact-readiness-001`" in call_args.kwargs["filter_by"]

    @pytest.mark.asyncio
    async def test_search_with_type_filter(self, semantic_tier):
        """Test search with knowledge type filter."""
        semantic_tier.typesense.search = AsyncMock(return_value={"hits": []})

        await semantic_tier.search(
            query_text="test", filters={"knowledge_type": "preference"}, limit=10
        )

        call_args = semantic_tier.typesense.search.call_args
        filter_by = call_args.kwargs["filter_by"]
        assert "knowledge_type:=preference" in filter_by

    @pytest.mark.asyncio
    async def test_search_with_category_filter(self, semantic_tier):
        """Test search with category filter."""
        semantic_tier.typesense.search = AsyncMock(return_value={"hits": []})

        await semantic_tier.search(query_text="test", filters={"category": "personal"}, limit=10)

        call_args = semantic_tier.typesense.search.call_args
        filter_by = call_args.kwargs["filter_by"]
        assert "category:=personal" in filter_by

    @pytest.mark.asyncio
    async def test_search_with_confidence_filter(self, semantic_tier):
        """Test search with minimum confidence filter."""
        semantic_tier.typesense.search = AsyncMock(return_value={"hits": []})

        await semantic_tier.search(query_text="test", filters={"min_confidence": 0.8}, limit=10)

        call_args = semantic_tier.typesense.search.call_args
        filter_by = call_args.kwargs["filter_by"]
        assert "confidence_score:>=0.8" in filter_by

    @pytest.mark.asyncio
    async def test_search_with_tags_filter(self, semantic_tier):
        """Test search with tags filter."""
        semantic_tier.typesense.search = AsyncMock(return_value={"hits": []})

        await semantic_tier.search(
            query_text="test", filters={"tags": ["productivity", "scheduling"]}, limit=10
        )

        call_args = semantic_tier.typesense.search.call_args
        filter_by = call_args.kwargs["filter_by"]
        assert "tags:=" in filter_by

    @pytest.mark.asyncio
    async def test_search_with_multiple_filters(self, semantic_tier):
        """Test search combining multiple filters."""
        semantic_tier.typesense.search = AsyncMock(return_value={"hits": []})

        await semantic_tier.search(
            query_text="test",
            filters={"knowledge_type": "preference", "category": "personal", "min_confidence": 0.7},
            limit=10,
        )

        call_args = semantic_tier.typesense.search.call_args
        filter_by = call_args.kwargs["filter_by"]

        # All filters should be ANDed together
        assert "knowledge_type:=preference" in filter_by
        assert "category:=personal" in filter_by
        assert "confidence_score:>=0.7" in filter_by
        assert " && " in filter_by


# ============================================
# Query Tests
# ============================================


class TestSemanticMemoryTierQuery:
    """Test general queries without text search."""

    @pytest.mark.asyncio
    async def test_query_uses_wildcard_search(self, semantic_tier):
        """Test that query uses wildcard for non-text queries."""
        semantic_tier.typesense.search = AsyncMock(return_value={"hits": []})

        await semantic_tier.query(filters={"knowledge_type": "insight"}, limit=10)

        call_args = semantic_tier.typesense.search.call_args
        assert call_args.kwargs["query"] == "*"


# ============================================
# Update Tests
# ============================================


class TestSemanticMemoryTierUpdate:
    """Test knowledge document updates."""

    @pytest.mark.asyncio
    async def test_update_usefulness_score(self, semantic_tier):
        """Test updating usefulness score."""
        # Setup - document exists
        now = datetime.now(UTC)
        semantic_tier.typesense.get_document = AsyncMock(
            return_value={
                "id": "know_001",
                "title": "Test knowledge",
                "content": "Test content here with enough characters",
                "knowledge_type": "insight",
                "confidence_score": 0.85,
                "episode_count": 1,
                "distilled_at": int(now.timestamp()),
                "access_count": 5,
                "usefulness_score": 0.7,
                "validation_count": 2,
            }
        )
        semantic_tier.typesense.update_document = AsyncMock()

        # Update usefulness
        result = await semantic_tier.update_usefulness("know_001", 0.9)

        # Verify
        assert result is True
        semantic_tier.typesense.update_document.assert_called()

        # Check updated values
        call_args = semantic_tier.typesense.update_document.call_args
        updated_doc = call_args.kwargs["document"]
        assert updated_doc["usefulness_score"] == 0.9
        assert updated_doc["validation_count"] == 3

    @pytest.mark.asyncio
    async def test_update_nonexistent_knowledge(self, semantic_tier):
        """Test updating knowledge that doesn't exist."""
        semantic_tier.typesense.get_document = AsyncMock(return_value=None)

        result = await semantic_tier.update_usefulness("nonexistent", 0.9)

        assert result is False
        semantic_tier.typesense.update_document.assert_not_called()


# ============================================
# Delete Tests
# ============================================


class TestSemanticMemoryTierDelete:
    """Test knowledge document deletion."""

    @pytest.mark.asyncio
    async def test_delete_knowledge(self, semantic_tier):
        """Test deleting knowledge document."""
        result = await semantic_tier.delete("know_001")

        assert result is True
        semantic_tier.typesense.delete_document.assert_called_once_with(
            collection_name="knowledge_test", document_id="know_001"
        )


# ============================================
# Statistics Tests
# ============================================


class TestSemanticMemoryTierStatistics:
    """Test collection statistics."""

    @pytest.mark.asyncio
    async def test_get_statistics_with_data(self, semantic_tier):
        """Test statistics calculation with sample data."""
        now = datetime.now(UTC)

        # Mock search to return sample documents
        semantic_tier.typesense.search = AsyncMock(
            return_value={
                "hits": [
                    {
                        "document": {
                            "id": f"know_{i:03d}",
                            "title": f"Knowledge {i}",
                            "content": f"Content for knowledge document {i} with enough characters",
                            "knowledge_type": "preference" if i < 3 else "insight",
                            "confidence_score": 0.7 + (i * 0.05),
                            "episode_count": i + 1,
                            "category": "personal" if i < 2 else "technical",
                            "distilled_at": int(now.timestamp()),
                            "access_count": i * 10,
                            "usefulness_score": 0.5 + (i * 0.1),
                            "validation_count": i,
                        },
                        "text_match": 1.0,
                    }
                    for i in range(5)
                ]
            }
        )

        stats = await semantic_tier.get_statistics()

        assert stats["total_documents"] == 5
        assert stats["avg_confidence"] > 0.7
        assert stats["avg_usefulness"] > 0.5
        assert "preference" in stats["knowledge_types"]
        assert "insight" in stats["knowledge_types"]
        assert "most_useful" in stats
        assert "most_accessed" in stats

    @pytest.mark.asyncio
    async def test_get_statistics_empty_collection(self, semantic_tier):
        """Test statistics with empty collection."""
        semantic_tier.typesense.search = AsyncMock(return_value={"hits": []})

        stats = await semantic_tier.get_statistics()

        assert stats["total_documents"] == 0
        assert stats["avg_confidence"] == 0.0
        assert stats["avg_usefulness"] == 0.0


# ============================================
# Health Check Tests
# ============================================


class TestSemanticMemoryTierHealthCheck:
    """Test health check."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, semantic_tier):
        """Test health check when Typesense is healthy."""
        # Setup
        semantic_tier.typesense.health_check = AsyncMock(return_value={"status": "healthy"})
        semantic_tier.typesense.search = AsyncMock(
            return_value={
                "hits": [
                    {
                        "document": {
                            "id": "know_001",
                            "title": "Test Knowledge Title",
                            "content": "Test content with enough characters here",
                            "knowledge_type": "insight",
                            "confidence_score": 0.8,
                            "episode_count": 1,
                            "distilled_at": int(datetime.now(UTC).timestamp()),
                            "access_count": 1,
                            "usefulness_score": 0.7,
                            "validation_count": 0,
                        },
                        "text_match": 1.0,
                    }
                ]
            }
        )

        health = await semantic_tier.health_check()

        assert health["tier"] == "L4_semantic_memory"
        assert health["status"] == "healthy"
        assert "typesense" in health["storage"]
        assert "statistics" in health
        assert health["statistics"]["total_documents"] == 1

    @pytest.mark.asyncio
    async def test_health_check_uses_typesense_document_count_without_sample_search(
        self, semantic_tier
    ):
        """Test health check avoids wildcard statistics search when count is available."""
        semantic_tier.typesense.health_check = AsyncMock(
            return_value={"status": "healthy", "document_count": 7}
        )
        semantic_tier.typesense.search = AsyncMock()

        health = await semantic_tier.health_check()

        assert health["status"] == "healthy"
        assert health["statistics"]["total_documents"] == 7
        semantic_tier.typesense.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, semantic_tier):
        """Test health check when Typesense is unhealthy."""
        semantic_tier.typesense.health_check = AsyncMock(return_value={"status": "unhealthy"})
        semantic_tier.typesense.search = AsyncMock(return_value={"hits": []})

        health = await semantic_tier.health_check()

        assert health["status"] == "unhealthy"


# ============================================
# Context Manager Tests
# ============================================


class TestSemanticMemoryTierContextManager:
    """Test async context manager protocol."""

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self, mock_typesense_adapter):
        """Test that context manager properly initializes and cleans up."""
        tier = SemanticMemoryTier(typesense_adapter=mock_typesense_adapter)

        async with tier:
            # Verify initialize called during __aenter__
            # Note: SemanticMemoryTier uses base class initialize which calls connect
            mock_typesense_adapter.connect.assert_called_once()

        # Verify disconnect called during cleanup (__aexit__)
        mock_typesense_adapter.disconnect.assert_called_once()
