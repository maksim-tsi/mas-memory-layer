"""
Comprehensive tests for L1 Active Context Tier.

Tests cover:
- Store/retrieve operations
- Turn windowing enforcement
- TTL management
- Redis-PostgreSQL fallback
- Metrics tracking
- Error handling
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import json

from src.memory.tiers.active_context_tier import ActiveContextTier
from src.storage.base import StorageDataError


class TestActiveContextTierStore:
    """Test suite for storing turns in L1."""
    
    @pytest.mark.asyncio
    async def test_store_turn_success(self, redis_adapter, postgres_adapter):
        """Test storing a single turn successfully."""
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter,
            config={'window_size': 10, 'ttl_hours': 24}
        )
        await tier.initialize()
        
        turn_data = {
            'session_id': 'test_session',
            'turn_id': 'turn_001',
            'role': 'user',
            'content': 'Hello, world!',
            'timestamp': datetime.now(timezone.utc),
            'metadata': {'source': 'test'}
        }
        
        turn_id = await tier.store(turn_data)
        
        assert turn_id == 'turn_001'
        
        # Verify Redis was called
        redis_adapter.lpush.assert_called_once()
        redis_adapter.ltrim.assert_called_once()
        redis_adapter.expire.assert_called_once()
        
        # Verify PostgreSQL was called
        postgres_adapter.insert.assert_called_once()
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_store_turn_missing_required_fields(self, redis_adapter, postgres_adapter):
        """Test that storing without required fields raises error."""
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        # Missing 'content' field
        incomplete_data = {
            'session_id': 'test_session',
            'turn_id': 'turn_001',
            'role': 'user'
        }
        
        with pytest.raises(StorageDataError):
            await tier.store(incomplete_data)
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_store_turn_default_timestamp(self, redis_adapter, postgres_adapter):
        """Test that timestamp defaults to utcnow if not provided."""
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        turn_data = {
            'session_id': 'test_session',
            'turn_id': 'turn_001',
            'role': 'user',
            'content': 'Test message'
        }
        
        before = datetime.now(timezone.utc)
        turn_id = await tier.store(turn_data)
        after = datetime.now(timezone.utc)
        
        assert turn_id == 'turn_001'
        
        # Verify timestamp was added
        call_args = redis_adapter.lpush.call_args[0]
        stored_data = json.loads(call_args[1])
        stored_time = datetime.fromisoformat(stored_data['timestamp'])
        
        assert before <= stored_time <= after
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_store_turn_windowing(self, redis_adapter, postgres_adapter):
        """Test that turn windowing trims to max size."""
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter,
            config={'window_size': 5}
        )
        await tier.initialize()
        
        # Store multiple turns
        for i in range(10):
            turn_data = {
                'session_id': 'test_session',
                'turn_id': f'turn_{i:03d}',
                'role': 'user' if i % 2 == 0 else 'assistant',
                'content': f'Message {i}'
            }
            await tier.store(turn_data)
        
        # Verify LTRIM was called to enforce window size
        assert redis_adapter.ltrim.call_count == 10
        # Check last call had correct window size
        last_ltrim_call = redis_adapter.ltrim.call_args[0]
        assert last_ltrim_call[2] == 4  # 0 to 4 = 5 items (window_size - 1)
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_store_turn_ttl_set(self, redis_adapter, postgres_adapter):
        """Test that TTL is set correctly on Redis key."""
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter,
            config={'ttl_hours': 48}
        )
        await tier.initialize()
        
        turn_data = {
            'session_id': 'test_session',
            'turn_id': 'turn_001',
            'role': 'user',
            'content': 'Test message'
        }
        
        await tier.store(turn_data)
        
        # Verify TTL was set (48 hours = 172800 seconds)
        redis_adapter.expire.assert_called_once()
        call_args = redis_adapter.expire.call_args[0]
        assert call_args[1] == 172800
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_store_turn_postgres_disabled(self, redis_adapter, postgres_adapter):
        """Test storing with PostgreSQL backup disabled."""
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter,
            config={'enable_postgres_backup': False}
        )
        await tier.initialize()
        
        turn_data = {
            'session_id': 'test_session',
            'turn_id': 'turn_001',
            'role': 'user',
            'content': 'Test message'
        }
        
        await tier.store(turn_data)
        
        # Verify Redis was called but PostgreSQL was not
        redis_adapter.lpush.assert_called_once()
        postgres_adapter.insert.assert_not_called()
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_store_turn_metrics_tracking(self, redis_adapter, postgres_adapter):
        """Test that metrics are tracked correctly."""
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        turn_data = {
            'session_id': 'test_session',
            'turn_id': 'turn_001',
            'role': 'user',
            'content': 'Test message'
        }
        
        await tier.store(turn_data)
        
        metrics = await tier.get_metrics()
        assert metrics['tier'] == 'ActiveContextTier'
        
        await tier.cleanup()


class TestActiveContextTierRetrieve:
    """Test suite for retrieving turns from L1."""
    
    @pytest.mark.asyncio
    async def test_retrieve_from_redis_hot_path(self, redis_adapter, postgres_adapter):
        """Test retrieval from Redis (hot path)."""
        # Mock Redis returning turns
        mock_turns = [
            json.dumps({
                'turn_id': 'turn_002',
                'role': 'assistant',
                'content': 'Response',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metadata': {}
            }),
            json.dumps({
                'turn_id': 'turn_001',
                'role': 'user',
                'content': 'Hello',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metadata': {}
            })
        ]
        redis_adapter.lrange = AsyncMock(return_value=mock_turns)
        
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        turns = await tier.retrieve('test_session')
        
        assert turns is not None
        assert len(turns) == 2
        assert turns[0]['turn_id'] == 'turn_002'
        assert turns[1]['turn_id'] == 'turn_001'
        
        # Verify Redis was called
        redis_adapter.lrange.assert_called_once()
        # Verify PostgreSQL was not called (hot path)
        postgres_adapter.query.assert_not_called()
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_retrieve_postgres_fallback(self, redis_adapter, postgres_adapter):
        """Test fallback to PostgreSQL when Redis doesn't have data."""
        # Mock Redis with no data
        redis_adapter.lrange = AsyncMock(return_value=[])
        
        # Mock PostgreSQL returning data
        mock_pg_data = [
            {
                'turn_id': 'turn_001',
                'role': 'user',
                'content': 'Hello',
                'timestamp': datetime.now(timezone.utc),
                'metadata': '{}'
            }
        ]
        postgres_adapter.query = AsyncMock(return_value=mock_pg_data)
        
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        turns = await tier.retrieve('test_session')
        
        assert turns is not None
        assert len(turns) == 1
        
        # Verify both were called
        redis_adapter.lrange.assert_called_once()
        postgres_adapter.query.assert_called_once()
        
        # Verify Redis cache rebuild was attempted
        redis_adapter.lpush.assert_called()
        redis_adapter.expire.assert_called()
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_retrieve_redis_failure_fallback(self, redis_adapter, postgres_adapter):
        """Test fallback when Redis fails completely."""
        # Mock Redis raising exception
        redis_adapter.lrange = AsyncMock(side_effect=Exception("Redis connection failed"))
        
        # Mock PostgreSQL returning data
        mock_pg_data = [
            {
                'turn_id': 'turn_001',
                'role': 'user',
                'content': 'Hello',
                'timestamp': datetime.now(timezone.utc),
                'metadata': '{}'
            }
        ]
        postgres_adapter.query = AsyncMock(return_value=mock_pg_data)
        
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        turns = await tier.retrieve('test_session')
        
        assert turns is not None
        assert len(turns) == 1
        
        # Verify PostgreSQL fallback worked
        postgres_adapter.query.assert_called_once()
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_retrieve_not_found(self, redis_adapter, postgres_adapter):
        """Test retrieval when session doesn't exist."""
        redis_adapter.lrange = AsyncMock(return_value=[])
        postgres_adapter.query = AsyncMock(return_value=[])
        
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        turns = await tier.retrieve('nonexistent_session')
        
        assert turns is None
        
        await tier.cleanup()


class TestActiveContextTierQuery:
    """Test suite for querying turns."""
    
    @pytest.mark.asyncio
    async def test_query_with_filters(self, redis_adapter, postgres_adapter):
        """Test querying with filters."""
        mock_results = [
            {
                'turn_id': 'turn_001',
                'role': 'user',
                'content': 'Hello',
                'timestamp': datetime.now(timezone.utc),
                'tier': 'L1'
            }
        ]
        postgres_adapter.query = AsyncMock(return_value=mock_results)
        
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        results = await tier.query(
            filters={'session_id': 'test_session', 'role': 'user'},
            limit=10
        )
        
        assert len(results) == 1
        assert results[0]['turn_id'] == 'turn_001'
        
        # Verify PostgreSQL was called with correct filters
        call_args = postgres_adapter.query.call_args
        assert call_args[1]['filters']['session_id'] == 'test_session'
        assert call_args[1]['filters']['role'] == 'user'
        assert call_args[1]['filters']['tier'] == 'L1'
        
        await tier.cleanup()


class TestActiveContextTierDelete:
    """Test suite for deleting sessions."""
    
    @pytest.mark.asyncio
    async def test_delete_session_success(self, redis_adapter, postgres_adapter):
        """Test successful session deletion."""
        redis_adapter.delete = AsyncMock(return_value=True)
        postgres_adapter.delete = AsyncMock(return_value=True)
        
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        result = await tier.delete('test_session')
        
        assert result is True
        redis_adapter.delete.assert_called_once()
        postgres_adapter.delete.assert_called_once()
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, redis_adapter, postgres_adapter):
        """Test deleting non-existent session."""
        redis_adapter.delete = AsyncMock(return_value=False)
        postgres_adapter.delete = AsyncMock(return_value=False)
        
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        result = await tier.delete('nonexistent_session')
        
        assert result is False
        
        await tier.cleanup()


class TestActiveContextTierHelpers:
    """Test suite for helper methods."""
    
    @pytest.mark.asyncio
    async def test_get_window_size(self, redis_adapter, postgres_adapter):
        """Test getting current window size."""
        redis_adapter.llen = AsyncMock(return_value=5)
        
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        size = await tier.get_window_size('test_session')
        
        assert size == 5
        redis_adapter.llen.assert_called_once()
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, redis_adapter, postgres_adapter):
        """Test health check when all systems healthy."""
        redis_adapter.health_check = AsyncMock(return_value={'status': 'healthy'})
        postgres_adapter.health_check = AsyncMock(return_value={'status': 'healthy'})
        
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter,
            config={'window_size': 20, 'ttl_hours': 24}
        )
        await tier.initialize()
        
        health = await tier.health_check()
        
        assert health['tier'] == 'L1_active_context'
        assert health['status'] == 'healthy'
        assert health['config']['window_size'] == 20
        assert health['config']['ttl_hours'] == 24
        
        await tier.cleanup()
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, redis_adapter, postgres_adapter):
        """Test health check when Redis is unhealthy."""
        redis_adapter.health_check = AsyncMock(return_value={'status': 'unhealthy'})
        postgres_adapter.health_check = AsyncMock(return_value={'status': 'healthy'})
        
        tier = ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter
        )
        await tier.initialize()
        
        health = await tier.health_check()
        
        assert health['status'] == 'degraded'
        
        await tier.cleanup()


class TestActiveContextTierContextManager:
    """Test async context manager usage."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self, redis_adapter, postgres_adapter):
        """Test using tier as async context manager."""
        async with ActiveContextTier(
            redis_adapter=redis_adapter,
            postgres_adapter=postgres_adapter
        ) as tier:
            assert tier.is_initialized()
            
            turn_data = {
                'session_id': 'test_session',
                'turn_id': 'turn_001',
                'role': 'user',
                'content': 'Test'
            }
            
            await tier.store(turn_data)
        
        # After context exit, should be cleaned up
        assert not tier.is_initialized()
