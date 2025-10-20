import asyncio
import pytest
import pytest_asyncio
import os
import uuid
from datetime import datetime, timezone
from src.storage.redis_adapter import RedisAdapter
from src.storage.base import StorageConnectionError, StorageDataError

@pytest_asyncio.fixture
async def redis_adapter():
    """Create and connect Redis adapter"""
    url = os.getenv('REDIS_URL')
    if not url:
        pytest.skip("REDIS_URL environment variable not set")
    
    config = {
        'url': url,
        'window_size': 5,
        'ttl_seconds': 3600  # 1 hour for tests
    }
    adapter = RedisAdapter(config)
    await adapter.connect()
    yield adapter
    await adapter.disconnect()

@pytest.fixture
def session_id():
    """Generate unique test session ID"""
    return f"test-redis-{uuid.uuid4()}"

@pytest_asyncio.fixture
async def cleanup_session(redis_adapter):
    """Cleanup test sessions after test"""
    sessions_to_clean = []
    
    def register(session_id: str):
        sessions_to_clean.append(session_id)
    
    yield register
    
    # Cleanup
    for session_id in sessions_to_clean:
        await redis_adapter.clear_session(session_id)

@pytest.mark.asyncio
async def test_connect_disconnect(redis_adapter):
    """Test connection lifecycle"""
    assert redis_adapter.is_connected
    await redis_adapter.disconnect()
    assert not redis_adapter.is_connected

@pytest.mark.asyncio
async def test_store_and_retrieve(redis_adapter, session_id, cleanup_session):
    """Test storing and retrieving a turn"""
    cleanup_session(session_id)
    
    # Store
    data = {
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Test message',
        'metadata': {'role': 'user'}
    }
    record_id = await redis_adapter.store(data)
    assert record_id is not None
    assert session_id in record_id
    
    # Retrieve
    retrieved = await redis_adapter.retrieve(record_id)
    assert retrieved is not None
    assert retrieved['turn_id'] == 1
    assert retrieved['content'] == 'Test message'
    assert retrieved['metadata']['role'] == 'user'

@pytest.mark.asyncio
async def test_window_size_limiting(redis_adapter, session_id, cleanup_session):
    """Test that window size is enforced"""
    cleanup_session(session_id)
    
    # Store more than window_size turns
    for i in range(10):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
    
    # Check that only window_size items are kept
    size = await redis_adapter.get_session_size(session_id)
    assert size == 5  # window_size from fixture
    
    # Most recent should be available
    results = await redis_adapter.search({
        'session_id': session_id,
        'limit': 10
    })
    assert len(results) == 5
    assert results[0]['turn_id'] == 9  # Most recent first

@pytest.mark.asyncio
async def test_search_with_pagination(redis_adapter, session_id, cleanup_session):
    """Test search with limit and offset"""
    cleanup_session(session_id)
    
    # Store 5 turns
    for i in range(5):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
    
    # Get first 2
    results = await redis_adapter.search({
        'session_id': session_id,
        'limit': 2
    })
    assert len(results) == 2
    assert results[0]['turn_id'] == 4  # Most recent
    assert results[1]['turn_id'] == 3
    
    # Get next 2 with offset
    results = await redis_adapter.search({
        'session_id': session_id,
        'limit': 2,
        'offset': 2
    })
    assert len(results) == 2
    assert results[0]['turn_id'] == 2
    assert results[1]['turn_id'] == 1

@pytest.mark.asyncio
async def test_delete_session(redis_adapter, session_id, cleanup_session):
    """Test deleting entire session cache"""
    cleanup_session(session_id)
    
    # Store some turns
    await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Message'
    })
    
    # Verify exists
    exists = await redis_adapter.session_exists(session_id)
    assert exists is True
    
    # Delete session
    deleted = await redis_adapter.clear_session(session_id)
    assert deleted is True
    
    # Verify gone
    exists = await redis_adapter.session_exists(session_id)
    assert exists is False

@pytest.mark.asyncio
async def test_ttl_refresh(redis_adapter, session_id, cleanup_session):
    """Test TTL refresh"""
    cleanup_session(session_id)
    
    # Store turn
    await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Message'
    })
    
    # Refresh TTL
    refreshed = await redis_adapter.refresh_ttl(session_id)
    assert refreshed is True

@pytest.mark.asyncio
async def test_ttl_refresh_on_search_enabled(session_id):
    """TTL should extend on search when refresh_ttl_on_read is enabled"""
    url = os.getenv('REDIS_URL')
    if not url:
        pytest.skip("REDIS_URL environment variable not set")

    config = {
        'url': url,
        'window_size': 5,
        'ttl_seconds': 30,
        'refresh_ttl_on_read': True,
    }

    async with RedisAdapter(config) as adapter:
        session = session_id
        await adapter.clear_session(session)

        try:
            await adapter.store({
                'session_id': session,
                'turn_id': 1,
                'content': 'Message',
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })

            key = adapter._make_key(session)
            assert adapter.client is not None

            await adapter.client.expire(key, 2)
            ttl_before = await adapter.client.pttl(key)
            assert 0 < ttl_before <= 2000

            await adapter.search({'session_id': session, 'limit': 1})

            ttl_after = await adapter.client.pttl(key)
            assert ttl_after > ttl_before
            assert ttl_after > 5000  # ttl_seconds (30s) reapplied on read
        finally:
            await adapter.clear_session(session)

@pytest.mark.asyncio
async def test_ttl_not_refreshed_when_disabled(redis_adapter, session_id, cleanup_session):
    """TTL should not extend when refresh_ttl_on_read is disabled"""
    cleanup_session(session_id)

    record_id = await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Message',
    })

    key = redis_adapter._make_key(session_id)
    assert redis_adapter.client is not None

    await redis_adapter.client.expire(key, 5)
    await asyncio.sleep(0.05)
    ttl_before = await redis_adapter.client.pttl(key)
    assert 0 < ttl_before <= 5000

    await redis_adapter.retrieve(record_id)

    ttl_after = await redis_adapter.client.pttl(key)
    assert 0 < ttl_after < 5000
    assert ttl_after <= ttl_before

@pytest.mark.asyncio
async def test_ttl_refresh_on_retrieve_enabled(session_id):
    """TTL should extend on retrieve when refresh_ttl_on_read is enabled"""
    url = os.getenv('REDIS_URL')
    if not url:
        pytest.skip("REDIS_URL environment variable not set")

    config = {
        'url': url,
        'window_size': 5,
        'ttl_seconds': 30,
        'refresh_ttl_on_read': True,
    }

    async with RedisAdapter(config) as adapter:
        session = session_id
        await adapter.clear_session(session)

        try:
            record_id = await adapter.store({
                'session_id': session,
                'turn_id': 1,
                'content': 'Message',
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })

            key = adapter._make_key(session)
            assert adapter.client is not None

            # Set short TTL
            await adapter.client.expire(key, 2)
            ttl_before = await adapter.client.pttl(key)
            assert 0 < ttl_before <= 2000

            # Retrieve should refresh TTL
            await adapter.retrieve(record_id)

            ttl_after = await adapter.client.pttl(key)
            assert ttl_after > ttl_before
            assert ttl_after > 5000  # ttl_seconds (30s) reapplied on read
        finally:
            await adapter.clear_session(session)

@pytest.mark.asyncio
async def test_context_manager():
    """Test context manager protocol"""
    url = os.getenv('REDIS_URL')
    if not url:
        pytest.skip("REDIS_URL environment variable not set")
    
    config = {
        'url': url,
        'window_size': 10
    }
    
    async with RedisAdapter(config) as adapter:
        assert adapter.is_connected
        exists = await adapter.session_exists('test')
        assert isinstance(exists, bool)
    
    # Should be disconnected after context
    assert not adapter.is_connected

@pytest.mark.asyncio
async def test_missing_session_id():
    """Test error on missing session_id"""
    url = os.getenv('REDIS_URL')
    if not url:
        pytest.skip("REDIS_URL environment variable not set")
    
    config = {'url': url}
    
    async with RedisAdapter(config) as adapter:
        with pytest.raises(StorageDataError):
            await adapter.search({})  # Missing session_id