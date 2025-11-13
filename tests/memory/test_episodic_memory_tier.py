"""
Tests for L3 Episodic Memory Tier.

Tests dual-indexed episode storage with Qdrant (vector) and Neo4j (graph),
bi-temporal properties, and hybrid retrieval patterns.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from src.memory.tiers.episodic_memory_tier import EpisodicMemoryTier
from src.memory.models import Episode
from src.storage.qdrant_adapter import QdrantAdapter
from src.storage.neo4j_adapter import Neo4jAdapter


@pytest.fixture
def mock_qdrant_adapter():
    """Mock Qdrant adapter for testing."""
    adapter = AsyncMock(spec=QdrantAdapter)
    adapter.initialize = AsyncMock()
    adapter.connect = AsyncMock()
    adapter.disconnect = AsyncMock()
    adapter.create_collection = AsyncMock()
    adapter.upsert = AsyncMock()
    adapter.search = AsyncMock(return_value=[])
    adapter.delete = AsyncMock()
    adapter.health_check = AsyncMock(return_value={'status': 'healthy'})
    return adapter


@pytest.fixture
def mock_neo4j_adapter():
    """Mock Neo4j adapter for testing."""
    adapter = AsyncMock(spec=Neo4jAdapter)
    adapter.initialize = AsyncMock()
    adapter.connect = AsyncMock()
    adapter.disconnect = AsyncMock()
    adapter.execute_query = AsyncMock(return_value=[])
    adapter.health_check = AsyncMock(return_value={'status': 'healthy'})
    return adapter


@pytest_asyncio.fixture
async def episodic_tier(mock_qdrant_adapter, mock_neo4j_adapter):
    """Fixture providing configured L3 tier."""
    tier = EpisodicMemoryTier(
        qdrant_adapter=mock_qdrant_adapter,
        neo4j_adapter=mock_neo4j_adapter,
        config={'collection_name': 'episodes_test', 'vector_size': 1536}
    )
    await tier.initialize()
    return tier


@pytest.fixture
def sample_episode():
    """Sample episode for testing."""
    now = datetime.now(timezone.utc)
    return Episode(
        episode_id='ep_001',
        session_id='session_1',
        summary='User discussed project requirements and deadlines',
        narrative='During the meeting, user outlined...',
        source_fact_ids=['fact_001', 'fact_002', 'fact_003'],
        fact_count=3,
        time_window_start=now - timedelta(hours=1),
        time_window_end=now,
        duration_seconds=3600.0,
        fact_valid_from=now - timedelta(hours=1),
        fact_valid_to=None,
        source_observation_timestamp=now,
        embedding_model='text-embedding-ada-002',
        topics=['project', 'requirements', 'deadlines'],
        importance_score=0.85,
        entities=[],
        relationships=[]
    )


@pytest.fixture
def sample_embedding():
    """Sample 1536-dimension embedding vector."""
    return [0.1] * 1536


# ============================================
# Store Tests
# ============================================

class TestEpisodicMemoryTierStore:
    """Test episode storage with dual indexing."""
    
    @pytest.mark.asyncio
    async def test_store_episode_with_dual_indexing(
        self, episodic_tier, sample_episode, sample_embedding
    ):
        """Test storing episode in both Qdrant and Neo4j."""
        # Setup
        episodic_tier.neo4j.execute_query = AsyncMock(return_value=[{'id': 'ep_001'}])
        
        # Store episode
        episode_id = await episodic_tier.store({
            'episode': sample_episode,
            'embedding': sample_embedding,
            'entities': [],
            'relationships': []
        })
        
        # Verify
        assert episode_id == 'ep_001'
        episodic_tier.qdrant.upsert.assert_called_once()
        # Neo4j should be called at least twice (create episode + link indexes)
        assert episodic_tier.neo4j.execute_query.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_store_episode_with_entities(
        self, episodic_tier, sample_episode, sample_embedding
    ):
        """Test storing episode with entity relationships."""
        # Setup
        entities = [
            {
                'entity_id': 'entity_1',
                'name': 'Project Alpha',
                'type': 'project',
                'properties': {'status': 'active'},
                'confidence': 0.9
            },
            {
                'entity_id': 'entity_2',
                'name': 'John Doe',
                'type': 'person',
                'properties': {'role': 'manager'},
                'confidence': 0.95
            }
        ]
        
        episodic_tier.neo4j.execute_query = AsyncMock(return_value=[{'id': 'ep_001'}])
        
        # Store
        episode_id = await episodic_tier.store({
            'episode': sample_episode,
            'embedding': sample_embedding,
            'entities': entities,
            'relationships': []
        })
        
        # Verify entities were created
        assert episode_id == 'ep_001'
        # Should call Neo4j for: create episode + 2 entities + link indexes
        assert episodic_tier.neo4j.execute_query.call_count >= 4
    
    @pytest.mark.asyncio
    async def test_store_episode_validates_embedding_size(
        self, episodic_tier, sample_episode
    ):
        """Test that invalid embedding size is rejected."""
        wrong_size_embedding = [0.1] * 512  # Wrong size
        
        with pytest.raises(ValueError, match="Embedding required with size 1536"):
            await episodic_tier.store({
                'episode': sample_episode,
                'embedding': wrong_size_embedding,
                'entities': [],
                'relationships': []
            })
    
    @pytest.mark.asyncio
    async def test_store_episode_requires_embedding(
        self, episodic_tier, sample_episode
    ):
        """Test that embedding is required."""
        with pytest.raises(ValueError, match="Embedding required"):
            await episodic_tier.store({
                'episode': sample_episode,
                'embedding': None,
                'entities': [],
                'relationships': []
            })
    
    @pytest.mark.asyncio
    async def test_store_updates_cross_references(
        self, episodic_tier, sample_episode, sample_embedding
    ):
        """Test that Qdrant vector_id is stored in Neo4j."""
        # Setup
        episodic_tier.neo4j.execute_query = AsyncMock(return_value=[{'id': 'ep_001'}])
        
        # Store
        await episodic_tier.store({
            'episode': sample_episode,
            'embedding': sample_embedding,
            'entities': [],
            'relationships': []
        })
        
        # Verify link update was called
        calls = episodic_tier.neo4j.execute_query.call_args_list
        link_call = [c for c in calls if 'SET e.vectorId' in str(c)]
        assert len(link_call) > 0


# ============================================
# Retrieve Tests
# ============================================

class TestEpisodicMemoryTierRetrieve:
    """Test episode retrieval by ID."""
    
    @pytest.mark.asyncio
    async def test_retrieve_existing_episode(
        self, episodic_tier, sample_episode
    ):
        """Test retrieving episode that exists."""
        # Setup mock response
        now = datetime.now(timezone.utc)
        episodic_tier.neo4j.execute_query = AsyncMock(return_value=[{
            'e': {
                'episodeId': 'ep_001',
                'sessionId': 'session_1',
                'summary': 'Test summary',
                'narrative': 'Test narrative',
                'factCount': 3,
                'timeWindowStart': now.isoformat(),
                'timeWindowEnd': now.isoformat(),
                'durationSeconds': 3600.0,
                'factValidFrom': now.isoformat(),
                'factValidTo': None,
                'sourceObservationTimestamp': now.isoformat(),
                'importanceScore': 0.85,
                'vectorId': 'ep_001'
            }
        }])
        
        # Retrieve
        episode = await episodic_tier.retrieve('ep_001')
        
        # Verify
        assert episode is not None
        assert episode.episode_id == 'ep_001'
        assert episode.session_id == 'session_1'
        assert episode.summary == 'Test summary'
        assert episode.importance_score == 0.85
    
    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_episode(self, episodic_tier):
        """Test retrieving episode that doesn't exist."""
        # Setup
        episodic_tier.neo4j.execute_query = AsyncMock(return_value=[])
        
        # Retrieve
        episode = await episodic_tier.retrieve('nonexistent')
        
        # Verify
        assert episode is None
    
    @pytest.mark.asyncio
    async def test_retrieve_parses_timestamps(self, episodic_tier):
        """Test that ISO timestamps are correctly parsed."""
        now = datetime.now(timezone.utc)
        episodic_tier.neo4j.execute_query = AsyncMock(return_value=[{
            'e': {
                'episodeId': 'ep_001',
                'sessionId': 'session_1',
                'summary': 'Test episode summary with sufficient length for validation',
                'factCount': 1,
                'timeWindowStart': now.isoformat(),
                'timeWindowEnd': now.isoformat(),
                'durationSeconds': 100.0,
                'factValidFrom': now.isoformat(),
                'factValidTo': None,
                'sourceObservationTimestamp': now.isoformat(),
                'importanceScore': 0.5
            }
        }])
        
        episode = await episodic_tier.retrieve('ep_001')
        
        assert isinstance(episode.time_window_start, datetime)
        assert isinstance(episode.fact_valid_from, datetime)


# ============================================
# Search Tests
# ============================================

class TestEpisodicMemoryTierSearch:
    """Test vector similarity search."""
    
    @pytest.mark.asyncio
    async def test_search_similar_episodes(
        self, episodic_tier, sample_embedding
    ):
        """Test finding similar episodes via vector search."""
        # Setup mock results
        now = datetime.now(timezone.utc)
        episodic_tier.qdrant.search = AsyncMock(return_value=[
            {
                'id': 'ep_001',
                'score': 0.92,
                'payload': {
                    'episode_id': 'ep_001',
                    'session_id': 'session_1',
                    'summary': 'Similar episode',
                    'fact_count': 3,
                    'time_window_start': now.isoformat(),
                    'time_window_end': now.isoformat(),
                    'fact_valid_from': now.isoformat(),
                    'fact_valid_to': None,
                    'importance_score': 0.85,
                    'topics': ['test']
                }
            }
        ])
        
        # Search
        results = await episodic_tier.search_similar(
            query_embedding=sample_embedding,
            limit=5
        )
        
        # Verify
        assert len(results) == 1
        assert results[0].episode_id == 'ep_001'
        assert results[0].metadata['similarity_score'] == 0.92
        episodic_tier.qdrant.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_with_filters(
        self, episodic_tier, sample_embedding
    ):
        """Test similarity search with filters."""
        episodic_tier.qdrant.search = AsyncMock(return_value=[])
        
        # Search with filters
        filters = {'session_id': 'session_1', 'min_importance': 0.7}
        await episodic_tier.search_similar(
            query_embedding=sample_embedding,
            limit=10,
            filters=filters
        )
        
        # Verify filters passed to Qdrant
        call_args = episodic_tier.qdrant.search.call_args
        assert call_args.kwargs['filter_dict'] == filters


# ============================================
# Graph Query Tests
# ============================================

class TestEpisodicMemoryTierGraphQueries:
    """Test Neo4j graph queries."""
    
    @pytest.mark.asyncio
    async def test_query_graph_custom_cypher(self, episodic_tier):
        """Test executing custom Cypher query."""
        # Setup
        episodic_tier.neo4j.execute_query = AsyncMock(return_value=[
            {'name': 'Entity1', 'count': 5}
        ])
        
        # Execute custom query
        query = "MATCH (e:Entity) RETURN e.name as name, count(*) as count"
        results = await episodic_tier.query_graph(query, {'param': 'value'})
        
        # Verify
        assert len(results) == 1
        assert results[0]['name'] == 'Entity1'
        episodic_tier.neo4j.execute_query.assert_called_once_with(
            query, {'param': 'value'}
        )
    
    @pytest.mark.asyncio
    async def test_get_episode_entities(self, episodic_tier):
        """Test retrieving entities for an episode (hypergraph)."""
        # Setup mock entities
        episodic_tier.neo4j.execute_query = AsyncMock(return_value=[
            {
                'entity': {
                    'entityId': 'entity_1',
                    'name': 'Project Alpha',
                    'type': 'project'
                },
                'r': {
                    'confidence': 0.9,
                    'factValidFrom': '2025-01-01T00:00:00+00:00',
                    'factValidTo': None
                }
            },
            {
                'entity': {
                    'entityId': 'entity_2',
                    'name': 'John Doe',
                    'type': 'person'
                },
                'r': {
                    'confidence': 0.95,
                    'factValidFrom': '2025-01-01T00:00:00+00:00',
                    'factValidTo': None
                }
            }
        ])
        
        # Get entities
        entities = await episodic_tier.get_episode_entities('ep_001')
        
        # Verify
        assert len(entities) == 2
        assert entities[0]['name'] == 'Project Alpha'
        assert entities[0]['confidence'] == 0.9
        assert entities[1]['name'] == 'John Doe'
        assert entities[1]['confidence'] == 0.95
    
    @pytest.mark.asyncio
    async def test_query_temporal(self, episodic_tier):
        """Test bi-temporal query for episodes valid at specific time."""
        # Setup
        now = datetime.now(timezone.utc)
        episodic_tier.neo4j.execute_query = AsyncMock(return_value=[
            {
                'e': {
                    'episodeId': 'ep_001',
                    'sessionId': 'session_1',
                    'summary': 'Valid episode',
                    'factCount': 2,
                    'timeWindowStart': now.isoformat(),
                    'timeWindowEnd': now.isoformat(),
                    'durationSeconds': 100.0,
                    'factValidFrom': (now - timedelta(days=1)).isoformat(),
                    'factValidTo': None,
                    'sourceObservationTimestamp': now.isoformat(),
                    'importanceScore': 0.8
                }
            }
        ])
        
        # Query
        query_time = now
        episodes = await episodic_tier.query_temporal(
            query_time=query_time,
            session_id='session_1',
            limit=10
        )
        
        # Verify
        assert len(episodes) == 1
        assert episodes[0].episode_id == 'ep_001'
        
        # Verify query included temporal filter
        call_args = episodic_tier.neo4j.execute_query.call_args
        assert 'factValidFrom' in call_args[0][0]
        assert 'factValidTo' in call_args[0][0]


# ============================================
# Query Tests
# ============================================

class TestEpisodicMemoryTierQuery:
    """Test general episode queries."""
    
    @pytest.mark.asyncio
    async def test_query_by_session(self, episodic_tier):
        """Test querying episodes by session."""
        now = datetime.now(timezone.utc)
        episodic_tier.neo4j.execute_query = AsyncMock(return_value=[
            {
                'e': {
                    'episodeId': 'ep_001',
                    'sessionId': 'session_1',
                    'summary': 'Episode 1 with sufficient length for validation',
                    'factCount': 2,
                    'timeWindowStart': now.isoformat(),
                    'timeWindowEnd': now.isoformat(),
                    'durationSeconds': 100.0,
                    'factValidFrom': now.isoformat(),
                    'factValidTo': None,
                    'sourceObservationTimestamp': now.isoformat(),
                    'importanceScore': 0.9
                }
            }
        ])
        
        episodes = await episodic_tier.query(
            filters={'session_id': 'session_1'},
            limit=10
        )
        
        assert len(episodes) == 1
        assert episodes[0].session_id == 'session_1'
    
    @pytest.mark.asyncio
    async def test_query_by_importance(self, episodic_tier):
        """Test filtering by minimum importance score."""
        now = datetime.now(timezone.utc)
        episodic_tier.neo4j.execute_query = AsyncMock(return_value=[
            {
                'e': {
                    'episodeId': 'ep_001',
                    'sessionId': 'session_1',
                    'summary': 'Important episode',
                    'factCount': 5,
                    'timeWindowStart': now.isoformat(),
                    'timeWindowEnd': now.isoformat(),
                    'durationSeconds': 100.0,
                    'factValidFrom': now.isoformat(),
                    'factValidTo': None,
                    'sourceObservationTimestamp': now.isoformat(),
                    'importanceScore': 0.95
                }
            }
        ])
        
        episodes = await episodic_tier.query(
            filters={'min_importance': 0.8},
            limit=10
        )
        
        assert len(episodes) == 1
        assert episodes[0].importance_score >= 0.8


# ============================================
# Delete Tests
# ============================================

class TestEpisodicMemoryTierDelete:
    """Test episode deletion from both stores."""
    
    @pytest.mark.asyncio
    async def test_delete_episode_from_both_stores(self, episodic_tier):
        """Test deleting episode removes it from Qdrant and Neo4j."""
        # Setup - episode exists
        now = datetime.now(timezone.utc)
        episodic_tier.neo4j.execute_query = AsyncMock(side_effect=[
            # First call: retrieve episode
            [{
                'e': {
                    'episodeId': 'ep_001',
                    'sessionId': 'session_1',
                    'summary': 'Test episode summary with sufficient length',
                    'factCount': 1,
                    'timeWindowStart': now.isoformat(),
                    'timeWindowEnd': now.isoformat(),
                    'durationSeconds': 100.0,
                    'factValidFrom': now.isoformat(),
                    'factValidTo': None,
                    'sourceObservationTimestamp': now.isoformat(),
                    'importanceScore': 0.5,
                    'vectorId': 'ep_001'
                }
            }],
            # Second call: delete episode
            []
        ])
        
        # Delete
        result = await episodic_tier.delete('ep_001')
        
        # Verify
        assert result is True
        episodic_tier.qdrant.delete.assert_called_once()
        assert episodic_tier.neo4j.execute_query.call_count == 2
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_episode(self, episodic_tier):
        """Test deleting episode that doesn't exist."""
        episodic_tier.neo4j.execute_query = AsyncMock(return_value=[])
        
        result = await episodic_tier.delete('nonexistent')
        
        assert result is False
        episodic_tier.qdrant.delete.assert_not_called()


# ============================================
# Health Check Tests
# ============================================

class TestEpisodicMemoryTierHealthCheck:
    """Test health check aggregation."""
    
    @pytest.mark.asyncio
    async def test_health_check_both_healthy(self, episodic_tier):
        """Test health check when both stores are healthy."""
        episodic_tier.qdrant.health_check = AsyncMock(
            return_value={'status': 'healthy'}
        )
        episodic_tier.neo4j.health_check = AsyncMock(
            return_value={'status': 'healthy'}
        )
        episodic_tier.neo4j.execute_query = AsyncMock(
            return_value=[{'count': 42}]
        )
        
        health = await episodic_tier.health_check()
        
        assert health['tier'] == 'L3_episodic_memory'
        assert health['status'] == 'healthy'
        assert health['statistics']['total_episodes'] == 42
        assert 'qdrant' in health['storage']
        assert 'neo4j' in health['storage']
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, episodic_tier):
        """Test health check when one store is unhealthy."""
        episodic_tier.qdrant.health_check = AsyncMock(
            return_value={'status': 'healthy'}
        )
        episodic_tier.neo4j.health_check = AsyncMock(
            return_value={'status': 'unhealthy'}
        )
        episodic_tier.neo4j.execute_query = AsyncMock(
            return_value=[{'count': 0}]
        )
        
        health = await episodic_tier.health_check()
        
        assert health['status'] == 'degraded'


# ============================================
# Context Manager Tests
# ============================================

class TestEpisodicMemoryTierContextManager:
    """Test async context manager protocol."""
    
    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(
        self, mock_qdrant_adapter, mock_neo4j_adapter
    ):
        """Test that context manager properly initializes and cleans up."""
        tier = EpisodicMemoryTier(
            qdrant_adapter=mock_qdrant_adapter,
            neo4j_adapter=mock_neo4j_adapter
        )
        
        async with tier:
            # Verify connect called during initialization (via parent's initialize)
            mock_qdrant_adapter.connect.assert_called_once()
            mock_neo4j_adapter.connect.assert_called_once()
        
        # Verify disconnect called during cleanup (__aexit__)
        mock_qdrant_adapter.disconnect.assert_called_once()
        mock_neo4j_adapter.disconnect.assert_called_once()
