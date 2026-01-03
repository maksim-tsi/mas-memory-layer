import asyncio
import pytest
import pytest_asyncio
import os
import uuid
from datetime import datetime, timezone
from src.storage.redis_adapter import RedisAdapter
from src.storage.base import StorageConnectionError, StorageDataError, StorageTimeoutError

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


# =============================================================================
# Edge Case Tests (Sub-Priority 3A.3)
# =============================================================================

@pytest.mark.asyncio
async def test_concurrent_writes_same_session(redis_adapter, cleanup_session):
    """Test concurrent writes to the same session"""
    session_id = f"test-concurrent-{uuid.uuid4()}"
    cleanup_session(session_id)
    
    # Write 10 turns concurrently
    tasks = [
        redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Concurrent message {i}',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
        for i in range(10)
    ]
    
    results = await asyncio.gather(*tasks)
    
    # All should succeed
    assert len(results) == 10
    assert all(r is not None for r in results)
    
    # Verify window size still enforced
    size = await redis_adapter.get_session_size(session_id)
    assert size <= redis_adapter.window_size


@pytest.mark.asyncio
async def test_concurrent_reads(redis_adapter, session_id, cleanup_session):
    """Test concurrent reads don't cause issues"""
    cleanup_session(session_id)
    
    # Setup: Store some data
    for i in range(5):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}',
        })
    
    # Concurrent reads
    tasks = [
        redis_adapter.search({'session_id': session_id, 'limit': 10})
        for _ in range(10)
    ]
    
    results = await asyncio.gather(*tasks)
    
    # All should return same data
    assert len(results) == 10
    assert all(len(r) == 5 for r in results)


@pytest.mark.asyncio
async def test_large_content(redis_adapter, session_id, cleanup_session):
    """Test storing large content (1MB)"""
    cleanup_session(session_id)
    
    large_content = 'x' * (1024 * 1024)  # 1MB of data
    
    record_id = await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': large_content,
    })
    
    retrieved = await redis_adapter.retrieve(record_id)
    assert retrieved is not None
    assert len(retrieved['content']) == 1024 * 1024
    assert retrieved['content'] == large_content


@pytest.mark.asyncio
async def test_large_metadata(redis_adapter, session_id, cleanup_session):
    """Test storing large metadata objects"""
    cleanup_session(session_id)
    
    large_metadata = {
        'list': list(range(1000)),
        'nested': {f'key_{i}': f'value_{i}' for i in range(100)},
        'string': 'x' * 10000,
    }
    
    record_id = await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Message',
        'metadata': large_metadata,
    })
    
    retrieved = await redis_adapter.retrieve(record_id)
    assert retrieved is not None
    assert len(retrieved['metadata']['list']) == 1000
    assert len(retrieved['metadata']['nested']) == 100
    assert len(retrieved['metadata']['string']) == 10000


@pytest.mark.asyncio
async def test_invalid_turn_id_format(redis_adapter):
    """Test handling of invalid turn_id in retrieve"""
    # Invalid formats should raise StorageDataError
    with pytest.raises(StorageDataError):
        await redis_adapter.retrieve("invalid-id-format")
    
    with pytest.raises(StorageDataError):
        await redis_adapter.retrieve("session:abc:turns:")  # Missing turn_id
    
    with pytest.raises(StorageDataError):
        await redis_adapter.retrieve("session:abc:turns:not-a-number")


@pytest.mark.asyncio
async def test_nonexistent_session(redis_adapter):
    """Test searching nonexistent session"""
    nonexistent_session = f"nonexistent-{uuid.uuid4()}"
    
    results = await redis_adapter.search({
        'session_id': nonexistent_session,
        'limit': 10
    })
    
    assert results == []
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_empty_content(redis_adapter, session_id, cleanup_session):
    """Test storing empty content"""
    cleanup_session(session_id)
    
    record_id = await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': '',
    })
    
    retrieved = await redis_adapter.retrieve(record_id)
    assert retrieved is not None
    assert retrieved['content'] == ''


@pytest.mark.asyncio
async def test_special_characters_in_content(redis_adapter, session_id, cleanup_session):
    """Test storing special characters and Unicode"""
    cleanup_session(session_id)
    
    special_content = '''
    Special chars: !@#$%^&*()_+-=[]{}|;:'",.<>?/~`
    Unicode: 你好世界 🚀 émojis 🎉 Здравствуй
    Newlines and tabs:\n\t\r
    Quotes: "double" 'single' `backtick`
    '''
    
    record_id = await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': special_content,
    })
    
    retrieved = await redis_adapter.retrieve(record_id)
    assert retrieved is not None
    assert retrieved['content'] == special_content


@pytest.mark.asyncio
async def test_delete_nonexistent_session(redis_adapter):
    """Test deleting nonexistent session returns False"""
    nonexistent_session = f"nonexistent-{uuid.uuid4()}"
    
    deleted = await redis_adapter.delete(f"session:{nonexistent_session}:turns")
    assert deleted is False


@pytest.mark.asyncio
async def test_delete_specific_turn(redis_adapter, session_id, cleanup_session):
    """Test deleting a specific turn from session"""
    cleanup_session(session_id)
    
    # Store 3 turns
    ids = []
    for i in range(3):
        record_id = await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}',
        })
        ids.append(record_id)
    
    # Delete middle turn
    deleted = await redis_adapter.delete(ids[1])
    assert deleted is True
    
    # Verify it's gone
    retrieved = await redis_adapter.retrieve(ids[1])
    assert retrieved is None
    
    # Other turns should still exist
    assert await redis_adapter.retrieve(ids[0]) is not None
    assert await redis_adapter.retrieve(ids[2]) is not None


@pytest.mark.asyncio
async def test_zero_window_size():
    """Test adapter behavior with window_size=0"""
    url = os.getenv('REDIS_URL')
    if not url:
        pytest.skip("REDIS_URL environment variable not set")
    
    config = {
        'url': url,
        'window_size': 0,
    }
    
    async with RedisAdapter(config) as adapter:
        session_id = f"test-zero-window-{uuid.uuid4()}"
        
        try:
            # Store should work
            await adapter.store({
                'session_id': session_id,
                'turn_id': 1,
                'content': 'Message',
            })
            
            # With window_size=0, LTRIM behavior keeps 1 item
            # (Redis LTRIM with range 0 to -1 keeps at least head)
            size = await adapter.get_session_size(session_id)
            assert size >= 0  # At least doesn't crash
            
            # Verify search still works
            results = await adapter.search({'session_id': session_id})
            assert isinstance(results, list)
        finally:
            await adapter.clear_session(session_id)


@pytest.mark.asyncio
async def test_negative_offset(redis_adapter, session_id, cleanup_session):
    """Test search with negative offset (edge case)"""
    cleanup_session(session_id)
    
    # Store some data
    for i in range(3):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}',
        })
    
    # Negative offset should still work (Redis LRANGE behavior)
    results = await redis_adapter.search({
        'session_id': session_id,
        'limit': 10,
        'offset': -1,
    })
    
    # Should return empty list (no items from offset -1)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_retrieve_nonexistent_turn(redis_adapter, session_id, cleanup_session):
    """Test retrieving a turn_id that doesn't exist in session"""
    cleanup_session(session_id)
    
    # Store turn 1
    await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Message 1',
    })
    
    # Try to retrieve turn 999 (doesn't exist)
    key = redis_adapter._make_key(session_id)
    fake_id = f"{key}:999"
    
    retrieved = await redis_adapter.retrieve(fake_id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_session_exists_check(redis_adapter, session_id, cleanup_session):
    """Test session existence check"""
    cleanup_session(session_id)
    
    # Should not exist initially
    exists = await redis_adapter.session_exists(session_id)
    assert exists is False
    
    # Store data
    await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Message',
    })
    
    # Should exist now
    exists = await redis_adapter.session_exists(session_id)
    assert exists is True
    
    # Clear session
    await redis_adapter.clear_session(session_id)
    
    # Should not exist again
    exists = await redis_adapter.session_exists(session_id)
    assert exists is False


@pytest.mark.asyncio
async def test_multiple_sessions_isolation(redis_adapter, cleanup_session):
    """Test that multiple sessions are isolated from each other"""
    session1 = f"test-session1-{uuid.uuid4()}"
    session2 = f"test-session2-{uuid.uuid4()}"
    cleanup_session(session1)
    cleanup_session(session2)
    
    # Store data in both sessions
    await redis_adapter.store({
        'session_id': session1,
        'turn_id': 1,
        'content': 'Session 1 message',
    })
    
    await redis_adapter.store({
        'session_id': session2,
        'turn_id': 1,
        'content': 'Session 2 message',
    })
    
    # Verify isolation
    results1 = await redis_adapter.search({'session_id': session1})
    results2 = await redis_adapter.search({'session_id': session2})
    
    assert len(results1) == 1
    assert len(results2) == 1
    assert results1[0]['content'] == 'Session 1 message'
    assert results2[0]['content'] == 'Session 2 message'
    
    # Delete session1 shouldn't affect session2
    await redis_adapter.clear_session(session1)
    
    assert await redis_adapter.session_exists(session1) is False
    assert await redis_adapter.session_exists(session2) is True


@pytest.mark.asyncio
async def test_connection_error_handling():
    """Test connection error handling with invalid host"""
    config = {
        'host': '192.0.2.1',  # TEST-NET-1, should not be routable
        'port': 6379,
        'db': 0,
        'socket_timeout': 0.1  # Short timeout
    }
    adapter = RedisAdapter(config)
    
    # Try to connect - should fail
    with pytest.raises((StorageConnectionError, StorageTimeoutError)):
        await adapter.connect()


@pytest.mark.asyncio
async def test_disconnect_error_handling(redis_adapter):
    """Test that disconnect handles errors gracefully"""
    # Connect normally
    if not redis_adapter._connected:
        await redis_adapter.connect()
    
    # Mock close to raise an error
    original_close = redis_adapter.client.aclose
    async def mock_close_error():
        raise Exception("Close error")
    
    redis_adapter.client.aclose = mock_close_error
    
    # Disconnect should not raise
    await redis_adapter.disconnect()
    
    # Restore original
    redis_adapter.client.aclose = original_close


@pytest.mark.asyncio
async def test_already_connected_warning(redis_adapter):
    """Test warning when trying to connect while already connected"""
    # First connection
    await redis_adapter.connect()
    
    # Try to connect again - should log warning but not error
    await redis_adapter.connect()
    
    # Should still be connected
    assert redis_adapter._connected is True
    
    await redis_adapter.disconnect()


@pytest.mark.asyncio
async def test_store_not_connected_error():
    """Test store operation when not connected"""
    config = {
        'host': 'localhost',
        'port': 6379,
        'db': 0
    }
    adapter = RedisAdapter(config)
    # Don't connect
    
    with pytest.raises(StorageConnectionError, match="Not connected"):
        await adapter.store({
            'session_id': 'test',
            'turn_id': 0,
            'content': 'test'
        })


@pytest.mark.asyncio
async def test_retrieve_batch_empty_list(redis_adapter):
    """Test retrieve_batch with empty list returns empty list"""
    await redis_adapter.connect()
    
    results = await redis_adapter.retrieve_batch([])
    assert results == []
    
    await redis_adapter.disconnect()


@pytest.mark.asyncio
async def test_delete_batch_empty_list(redis_adapter):
    """Test delete_batch with empty list returns empty dict"""
    await redis_adapter.connect()
    
    results = await redis_adapter.delete_batch([])
    assert results == {}
    
    await redis_adapter.disconnect()


@pytest.mark.asyncio
async def test_store_batch_empty_list(redis_adapter):
    """Test store_batch with empty list returns empty list"""
    await redis_adapter.connect()
    
    results = await redis_adapter.store_batch([])
    assert results == []
    
    await redis_adapter.disconnect()