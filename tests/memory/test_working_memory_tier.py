"""
Comprehensive tests for L2 Working Memory Tier.

Tests cover:
- Store facts with CIAR scoring
- CIAR threshold enforcement
- Retrieve with access tracking
- Query by session, type, CIAR score
- CIAR score updates
- Access tracking and recency boost
- TTL and cleanup
- Health checks
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from src.memory.tiers.working_memory_tier import WorkingMemoryTier
from src.memory.models import Fact, FactType


class TestWorkingMemoryTierStore:
    """Test suite for storing facts in L2."""
    
    @pytest.mark.asyncio
    async def test_store_fact_success(self, postgres_adapter):
        """Test storing a fact above CIAR threshold."""
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter,
            config={'ciar_threshold': 0.6}
        )
        await tier.initialize()
        
        fact_data = {
            'fact_id': 'fact-001',
            'session_id': 'session-123',
            'content': 'User prefers email communication',
            'ciar_score': 0.75,
            'certainty': 0.85,
            'impact': 0.90,
            'fact_type': FactType.PREFERENCE,
            'source_uri': 'l1:session:123:turn:005'
        }
        
        fact_id = await tier.store(fact_data)
        
        assert fact_id == 'fact-001'
        postgres_adapter.insert.assert_called_once()
        call_args = postgres_adapter.insert.call_args[0]
        assert call_args[0] == 'working_memory'
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_store_fact_below_threshold(self, postgres_adapter):
        """Test that facts below CIAR threshold are rejected."""
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter,
            config={'ciar_threshold': 0.6}
        )
        await tier.initialize()
        
        low_ciar_fact = {
            'fact_id': 'fact-002',
            'session_id': 'session-123',
            'content': 'Random mention',
            'ciar_score': 0.4,  # Below threshold
            'certainty': 0.5,
            'impact': 0.8
        }
        
        with pytest.raises(ValueError, match="below threshold"):
            await tier.store(low_ciar_fact)
        
        # Should not have called insert
        postgres_adapter.insert.assert_not_called()
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_store_fact_with_model(self, postgres_adapter):
        """Test storing using Fact model directly."""
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter,
            config={'ciar_threshold': 0.6}
        )
        await tier.initialize()
        
        fact = Fact(
            fact_id='fact-003',
            session_id='session-123',
            content='User works in logistics',
            ciar_score=0.80,
            certainty=0.90,
            impact=0.90,
            fact_type=FactType.ENTITY
        )
        
        fact_id = await tier.store(fact)
        
        assert fact_id == 'fact-003'
        postgres_adapter.insert.assert_called_once()
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_store_fact_custom_threshold(self, postgres_adapter):
        """Test using custom CIAR threshold."""
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter,
            config={'ciar_threshold': 0.8}  # Higher threshold
        )
        await tier.initialize()
        
        # Fact with CIAR 0.75 (above default 0.6 but below 0.8)
        fact_data = {
            'fact_id': 'fact-004',
            'session_id': 'session-123',
            'content': 'Medium significance fact',
            'ciar_score': 0.75,
            'certainty': 0.85,
            'impact': 0.88
        }
        
        with pytest.raises(ValueError, match="below threshold 0.8"):
            await tier.store(fact_data)
        
        await tier.cleanup()


class TestWorkingMemoryTierRetrieve:
    """Test suite for retrieving facts."""
    
    @pytest.mark.asyncio
    async def test_retrieve_fact_success(self, postgres_adapter):
        """Test retrieving an existing fact."""
        # Mock PostgreSQL query to return a fact
        mock_fact_data = {
            'fact_id': 'fact-001',
            'session_id': 'session-123',
            'content': 'Test fact',
            'ciar_score': 0.75,
            'certainty': 0.85,
            'impact': 0.90,
            'age_decay': 1.0,
            'recency_boost': 1.0,
            'source_uri': None,
            'source_type': 'extracted',
            'fact_type': 'preference',
            'fact_category': None,
            'metadata': '{}',
            'extracted_at': datetime.now(timezone.utc),
            'last_accessed': datetime.now(timezone.utc),
            'access_count': 0
        }
        postgres_adapter.query = AsyncMock(return_value=[mock_fact_data])
        postgres_adapter.update = AsyncMock()
        
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter,
            config={'ciar_threshold': 0.6}
        )
        await tier.initialize()
        
        fact = await tier.retrieve('fact-001')
        
        assert fact is not None
        assert fact.fact_id == 'fact-001'
        assert fact.content == 'Test fact'
        
        # Verify access tracking was updated
        postgres_adapter.update.assert_called_once()
        update_call = postgres_adapter.update.call_args
        assert update_call[0][0] == 'working_memory'
        assert update_call[1]['filters']['fact_id'] == 'fact-001'
        assert 'access_count' in update_call[1]['data']
        assert update_call[1]['data']['access_count'] == 1
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_retrieve_fact_not_found(self, postgres_adapter):
        """Test retrieving non-existent fact."""
        postgres_adapter.query = AsyncMock(return_value=[])
        
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        fact = await tier.retrieve('nonexistent-fact')
        
        assert fact is None
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_retrieve_updates_recency_boost(self, postgres_adapter):
        """Test that retrieval updates recency boost."""
        mock_fact_data = {
            'fact_id': 'fact-001',
            'session_id': 'session-123',
            'content': 'Test fact',
            'ciar_score': 0.75,
            'certainty': 0.85,
            'impact': 0.90,
            'age_decay': 1.0,
            'recency_boost': 1.0,
            'source_uri': None,
            'source_type': 'extracted',
            'fact_type': None,
            'fact_category': None,
            'metadata': '{}',
            'extracted_at': datetime.now(timezone.utc),
            'last_accessed': datetime.now(timezone.utc),
            'access_count': 5  # Already accessed 5 times
        }
        postgres_adapter.query = AsyncMock(return_value=[mock_fact_data])
        postgres_adapter.update = AsyncMock()
        
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter,
            config={'recency_boost_alpha': 0.05}
        )
        await tier.initialize()
        
        fact = await tier.retrieve('fact-001')
        assert fact is not None
        
        # Verify recency boost increased
        update_data = postgres_adapter.update.call_args[1]['data']
        assert 'recency_boost' in update_data
        # With access_count=6, recency_boost should be 1 + (0.05 * 6) = 1.3
        assert update_data['recency_boost'] == pytest.approx(1.3, rel=0.01)
        
        await tier.cleanup()


class TestWorkingMemoryTierQuery:
    """Test suite for querying facts."""
    
    @pytest.mark.asyncio
    async def test_query_by_session(self, postgres_adapter):
        """Test querying facts by session."""
        mock_facts = [
            {
                'fact_id': 'fact-001',
                'session_id': 'session-123',
                'content': 'Fact 1',
                'ciar_score': 0.85,
                'certainty': 0.90,
                'impact': 0.95,
                'age_decay': 1.0,
                'recency_boost': 1.0,
                'source_uri': None,
                'source_type': 'extracted',
                'fact_type': None,
                'fact_category': None,
                'metadata': '{}',
                'extracted_at': datetime.now(timezone.utc),
                'last_accessed': datetime.now(timezone.utc),
                'access_count': 0
            },
            {
                'fact_id': 'fact-002',
                'session_id': 'session-123',
                'content': 'Fact 2',
                'ciar_score': 0.75,
                'certainty': 0.85,
                'impact': 0.90,
                'age_decay': 1.0,
                'recency_boost': 1.0,
                'source_uri': None,
                'source_type': 'extracted',
                'fact_type': None,
                'fact_category': None,
                'metadata': '{}',
                'extracted_at': datetime.now(timezone.utc),
                'last_accessed': datetime.now(timezone.utc),
                'access_count': 0
            }
        ]
        postgres_adapter.query = AsyncMock(return_value=mock_facts)
        
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter,
            config={'ciar_threshold': 0.6}
        )
        await tier.initialize()
        
        facts = await tier.query_by_session('session-123')
        
        assert len(facts) == 2
        assert all(f.session_id == 'session-123' for f in facts)
        assert facts[0].ciar_score >= tier.ciar_threshold
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_query_by_type(self, postgres_adapter):
        """Test querying facts by type."""
        mock_facts = [
            {
                'fact_id': 'fact-001',
                'session_id': 'session-123',
                'content': 'User prefers X',
                'ciar_score': 0.85,
                'certainty': 0.90,
                'impact': 0.95,
                'age_decay': 1.0,
                'recency_boost': 1.0,
                'source_uri': None,
                'source_type': 'extracted',
                'fact_type': 'preference',
                'fact_category': None,
                'metadata': '{}',
                'extracted_at': datetime.now(timezone.utc),
                'last_accessed': datetime.now(timezone.utc),
                'access_count': 0
            }
        ]
        postgres_adapter.query = AsyncMock(return_value=mock_facts)
        
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        facts = await tier.query_by_type(FactType.PREFERENCE)
        
        assert len(facts) == 1
        assert facts[0].fact_type == FactType.PREFERENCE
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_query_filters_low_ciar(self, postgres_adapter):
        """Test that query filters out low CIAR scores by default."""
        mock_facts = [
            {
                'fact_id': 'fact-001',
                'session_id': 'session-123',
                'content': 'High CIAR',
                'ciar_score': 0.85,
                'certainty': 0.90,
                'impact': 0.95,
                'age_decay': 1.0,
                'recency_boost': 1.0,
                'source_uri': None,
                'source_type': 'extracted',
                'fact_type': None,
                'fact_category': None,
                'metadata': '{}',
                'extracted_at': datetime.now(timezone.utc),
                'last_accessed': datetime.now(timezone.utc),
                'access_count': 0
            },
            {
                'fact_id': 'fact-002',
                'session_id': 'session-123',
                'content': 'Low CIAR',
                'ciar_score': 0.45,  # Below threshold
                'certainty': 0.50,
                'impact': 0.90,
                'age_decay': 1.0,
                'recency_boost': 1.0,
                'source_uri': None,
                'source_type': 'extracted',
                'fact_type': None,
                'fact_category': None,
                'metadata': '{}',
                'extracted_at': datetime.now(timezone.utc),
                'last_accessed': datetime.now(timezone.utc),
                'access_count': 0
            }
        ]
        postgres_adapter.query = AsyncMock(return_value=mock_facts)
        
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter,
            config={'ciar_threshold': 0.6}
        )
        await tier.initialize()
        
        facts = await tier.query(filters={'session_id': 'session-123'})
        
        # Should only return fact with CIAR >= 0.6
        assert len(facts) == 1
        assert facts[0].ciar_score >= 0.6
        
        await tier.cleanup()


class TestWorkingMemoryTierCIARUpdates:
    """Test suite for CIAR score updates."""
    
    @pytest.mark.asyncio
    async def test_update_ciar_score_direct(self, postgres_adapter):
        """Test directly updating CIAR score."""
        postgres_adapter.update = AsyncMock()
        postgres_adapter.query = AsyncMock(return_value=[{
            'fact_id': 'fact-001',
            'session_id': 'session-123',
            'content': 'Test',
            'ciar_score': 0.70,
            'certainty': 0.80,
            'impact': 0.90,
            'age_decay': 1.0,
            'recency_boost': 1.0,
            'source_uri': None,
            'source_type': 'extracted',
            'fact_type': None,
            'fact_category': None,
            'metadata': '{}',
            'extracted_at': datetime.now(timezone.utc),
            'last_accessed': datetime.now(timezone.utc),
            'access_count': 0
        }])
        
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        result = await tier.update_ciar_score('fact-001', ciar_score=0.85)
        
        assert result is True
        postgres_adapter.update.assert_called_once()
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_update_ciar_components(self, postgres_adapter):
        """Test updating CIAR components with automatic score recalculation."""
        mock_fact = {
            'fact_id': 'fact-001',
            'session_id': 'session-123',
            'content': 'Test',
            'ciar_score': 0.72,
            'certainty': 0.80,
            'impact': 0.90,
            'age_decay': 1.0,
            'recency_boost': 1.0,
            'source_uri': None,
            'source_type': 'extracted',
            'fact_type': None,
            'fact_category': None,
            'metadata': '{}',
            'extracted_at': datetime.now(timezone.utc),
            'last_accessed': datetime.now(timezone.utc),
            'access_count': 0
        }
        postgres_adapter.query = AsyncMock(return_value=[mock_fact])
        postgres_adapter.update = AsyncMock()
        
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        # Update certainty component (fact is retrieved, so access tracking updates recency_boost)
        result = await tier.update_ciar_score(
            'fact-001',
            certainty=0.95,
            impact=0.90
        )
        
        assert result is True
        
        # Check that CIAR was recalculated with updated recency_boost
        update_data = postgres_adapter.update.call_args[1]['data']
        # The retrieve call in update_ciar_score updates recency_boost to 1.05 (access_count=1)
        expected_ciar = (0.95 * 0.90) * 1.0 * 1.05
        assert update_data['ciar_score'] == pytest.approx(expected_ciar, rel=0.02)
        
        await tier.cleanup()


class TestWorkingMemoryTierDelete:
    """Test suite for deleting facts."""
    
    @pytest.mark.asyncio
    async def test_delete_fact_success(self, postgres_adapter):
        """Test successful fact deletion."""
        postgres_adapter.delete = AsyncMock(return_value=True)
        
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        result = await tier.delete('fact-001')
        
        assert result is True
        postgres_adapter.delete.assert_called_once()
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_delete_fact_not_found(self, postgres_adapter):
        """Test deleting non-existent fact."""
        postgres_adapter.delete = AsyncMock(return_value=False)
        
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        result = await tier.delete('nonexistent-fact')
        
        assert result is False
        
        await tier.cleanup()


class TestWorkingMemoryTierHealthCheck:
    """Test suite for health checks."""
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, postgres_adapter):
        """Test health check when system is healthy."""
        postgres_adapter.health_check = AsyncMock(return_value={'status': 'healthy'})
        postgres_adapter.query = AsyncMock(return_value=[
            {'ciar_score': 0.85},
            {'ciar_score': 0.75},
            {'ciar_score': 0.65}
        ])
        
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter,
            config={'ciar_threshold': 0.6}
        )
        await tier.initialize()
        
        health = await tier.health_check()
        
        assert health['tier'] == 'L2_working_memory'
        assert health['status'] == 'healthy'
        assert 'statistics' in health
        assert health['statistics']['total_facts'] == 3
        assert 'config' in health
        assert health['config']['ciar_threshold'] == 0.6
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, postgres_adapter):
        """Test health check when PostgreSQL is unhealthy."""
        postgres_adapter.health_check = AsyncMock(return_value={'status': 'unhealthy'})
        postgres_adapter.query = AsyncMock(return_value=[])
        
        tier = WorkingMemoryTier(
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        health = await tier.health_check()
        
        assert health['status'] == 'degraded'
        
        await tier.cleanup()


class TestWorkingMemoryTierContextManager:
    """Test async context manager usage."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self, postgres_adapter):
        """Test using tier as async context manager."""
        postgres_adapter.insert = AsyncMock()
        
        async with WorkingMemoryTier(
            postgres_adapter=postgres_adapter,
            config={'ciar_threshold': 0.6}
        ) as tier:
            assert tier.is_initialized()
            
            fact_data = {
                'fact_id': 'fact-001',
                'session_id': 'session-123',
                'content': 'Test fact',
                'ciar_score': 0.75,
                'certainty': 0.85,
                'impact': 0.90
            }
            
            await tier.store(fact_data)
        
        # After context exit, should be cleaned up
        assert not tier.is_initialized()
