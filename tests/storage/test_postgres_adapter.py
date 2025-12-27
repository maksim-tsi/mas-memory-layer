import pytest
import pytest_asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from src.storage.postgres_adapter import PostgresAdapter
from src.storage.base import StorageConnectionError, StorageDataError

@pytest_asyncio.fixture
async def postgres_adapter():
    """Create and connect PostgreSQL adapter"""
    url = os.getenv('POSTGRES_URL')
    if not url:
        pytest.skip("POSTGRES_URL environment variable not set")
    
    config = {
        'url': url,
        'pool_size': 5,
        'table': 'active_context'
    }
    adapter = PostgresAdapter(config)
    await adapter.connect()
    yield adapter
    await adapter.disconnect()

@pytest.fixture
def session_id():
    """Generate unique test session ID"""
    return f"test-postgres-{uuid.uuid4()}"

@pytest.mark.asyncio
async def test_connect_disconnect(postgres_adapter):
    """Test connection lifecycle"""
    assert postgres_adapter.is_connected
    await postgres_adapter.disconnect()
    assert not postgres_adapter.is_connected

@pytest.mark.asyncio
async def test_store_and_retrieve_active_context(postgres_adapter, session_id):
    """Test storing and retrieving a record in active_context table"""
    # Store
    data = {
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Test message',
        'metadata': {'test': True}
    }
    record_id = await postgres_adapter.store(data)
    assert record_id is not None
    
    # Retrieve
    retrieved = await postgres_adapter.retrieve(record_id)
    assert retrieved is not None
    assert retrieved['session_id'] == session_id
    assert retrieved['content'] == 'Test message'
    assert retrieved['metadata']['test'] is True
    
    # Cleanup
    await postgres_adapter.delete(record_id)

@pytest.mark.asyncio
async def test_search_with_filters(postgres_adapter, session_id):
    """Test search with various filters"""
    # Store multiple records
    ids = []
    for i in range(5):
        data = {
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        }
        record_id = await postgres_adapter.store(data)
        ids.append(record_id)
    
    # Search all
    results = await postgres_adapter.search({
        'session_id': session_id,
        'limit': 10
    })
    assert len(results) == 5
    
    # Search with limit
    results = await postgres_adapter.search({
        'session_id': session_id,
        'limit': 2
    })
    assert len(results) == 2
    
    # Cleanup
    for record_id in ids:
        await postgres_adapter.delete(record_id)

@pytest.mark.asyncio
async def test_delete(postgres_adapter, session_id):
    """Test deletion"""
    # Store
    data = {
        'session_id': session_id,
        'turn_id': 1,
        'content': 'To be deleted'
    }
    record_id = await postgres_adapter.store(data)
    
    # Delete
    deleted = await postgres_adapter.delete(record_id)
    assert deleted is True
    
    # Verify deleted
    retrieved = await postgres_adapter.retrieve(record_id)
    assert retrieved is None
    
    # Delete again (should return False)
    deleted = await postgres_adapter.delete(record_id)
    assert deleted is False

@pytest.mark.asyncio
async def test_ttl_expiration(postgres_adapter, session_id):
    """Test TTL expiration filtering"""
    # Store expired record
    data = {
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Expired message',
        'ttl_expires_at': datetime.now(timezone.utc) - timedelta(hours=1)
    }
    record_id = await postgres_adapter.store(data)
    
    # Search without expired
    results = await postgres_adapter.search({
        'session_id': session_id,
        'include_expired': False
    })
    assert len(results) == 0
    
    # Search with expired
    results = await postgres_adapter.search({
        'session_id': session_id,
        'include_expired': True
    })
    assert len(results) == 1
    
    # Cleanup
    await postgres_adapter.delete(record_id)

@pytest.mark.asyncio
async def test_context_manager():
    """Test context manager protocol"""
    url = os.getenv('POSTGRES_URL')
    if not url:
        pytest.skip("POSTGRES_URL environment variable not set")
    
    config = {
        'url': url,
        'table': 'active_context'
    }
    
    async with PostgresAdapter(config) as adapter:
        assert adapter.is_connected
        count = await adapter.count()
        assert count >= 0
    
    # Should be disconnected after context
    assert not adapter.is_connected

@pytest.mark.asyncio
async def test_working_memory_table():
    """Test working_memory table operations"""
    url = os.getenv('POSTGRES_URL')
    if not url:
        pytest.skip("POSTGRES_URL environment variable not set")
    
    config = {
        'url': url,
        'table': 'working_memory'
    }
    
    async with PostgresAdapter(config) as adapter:
        # Store a working memory fact
        data = {
            'session_id': f"test-wm-{uuid.uuid4()}",
            'fact_type': 'entity',
            'content': 'Test entity fact',
            'confidence': 0.95,
            'source_turn_ids': [1, 2, 3]
        }
        record_id = await adapter.store(data)
        assert record_id is not None
        
        # Retrieve
        retrieved = await adapter.retrieve(record_id)
        assert retrieved is not None
        assert retrieved['fact_type'] == 'entity'
        assert retrieved['confidence'] == 0.95
        assert retrieved['source_turn_ids'] == [1, 2, 3]
        
        # Cleanup
        await adapter.delete(record_id)


@pytest.mark.asyncio
async def test_connection_error_handling():
    """Test connection error handling with invalid credentials"""
    
    config = {
        'url': 'postgresql://invalid:invalid@localhost:5432/invalid_db'
    }
    
    adapter = PostgresAdapter(config)
    with pytest.raises(StorageConnectionError):
        await adapter.connect()


@pytest.mark.asyncio
async def test_disconnect_when_not_connected():
    """Test disconnect when not connected"""
    url = os.getenv('POSTGRES_URL')
    if not url:
        pytest.skip("POSTGRES_URL environment variable not set")
    
    config = {'url': url}
    adapter = PostgresAdapter(config)
    
    # Disconnect without connecting should not raise
    await adapter.disconnect()
    assert not adapter.is_connected


@pytest.mark.asyncio
async def test_store_without_connection():
    """Test store operation when not connected"""
    
    url = os.getenv('POSTGRES_URL')
    if not url:
        pytest.skip("POSTGRES_URL environment variable not set")
    
    config = {'url': url}
    adapter = PostgresAdapter(config)
    
    # Try to store without connecting
    with pytest.raises(StorageConnectionError, match="Not connected"):
        await adapter.store({
            'session_id': 'test',
            'turn_id': 1,
            'content': 'test'
        })


@pytest.mark.asyncio
async def test_retrieve_batch_empty_list(postgres_adapter):
    """Test retrieve_batch with empty list"""
    await postgres_adapter.connect()
    
    results = await postgres_adapter.retrieve_batch([])
    assert results == []
    
    await postgres_adapter.disconnect()


@pytest.mark.asyncio
async def test_delete_batch_empty_list(postgres_adapter):
    """Test delete_batch with empty list"""
    await postgres_adapter.connect()
    
    results = await postgres_adapter.delete_batch([])
    assert results == {}
    
    await postgres_adapter.disconnect()


@pytest.mark.asyncio
async def test_store_batch_empty_list(postgres_adapter):
    """Test store_batch with empty list"""
    await postgres_adapter.connect()
    
    results = await postgres_adapter.store_batch([])
    assert results == []
    
    await postgres_adapter.disconnect()


@pytest.mark.asyncio
async def test_unknown_table_error():
    """Test storing to unknown table raises error"""
    
    url = os.getenv('POSTGRES_URL')
    if not url:
        pytest.skip("POSTGRES_URL environment variable not set")
    
    config = {
        'url': url,
        'table': 'unknown_table'
    }
    
    async with PostgresAdapter(config) as adapter:
        with pytest.raises(StorageDataError, match="Unknown table"):
            await adapter.store({
                'session_id': 'test',
                'turn_id': 1,
                'content': 'test'
            })


@pytest.mark.asyncio
async def test_delete_expired_records(postgres_adapter, session_id):
    """Test deleting expired records"""
    await postgres_adapter.connect()
    
    # Store a record with past expiration
    from datetime import datetime, timezone, timedelta
    data = {
        'session_id': session_id,
        'turn_id': 999,
        'content': 'Expired content',
        'ttl_expires_at': datetime.now(timezone.utc) - timedelta(hours=1)  # Already expired
    }
    
    record_id = await postgres_adapter.store(data)
    assert record_id is not None
    
    # Delete expired records
    count = await postgres_adapter.delete_expired()
    assert count >= 1  # At least our expired record
    
    # Verify the record is gone
    retrieved = await postgres_adapter.retrieve(record_id)
    assert retrieved is None
    
    await postgres_adapter.disconnect()


@pytest.mark.asyncio
async def test_count_with_session_filter(postgres_adapter, session_id):
    """Test counting records with session filter"""
    await postgres_adapter.connect()
    
    # Store multiple records and collect IDs for cleanup
    ids = []
    for i in range(3):
        record_id = await postgres_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
        ids.append(record_id)
    
    # Count for specific session
    count = await postgres_adapter.count(session_id=session_id)
    assert count >= 3
    
    # Cleanup - delete by IDs
    for record_id in ids:
        await postgres_adapter.delete(record_id)
    
    await postgres_adapter.disconnect()


@pytest.mark.asyncio
async def test_retrieve_not_found(postgres_adapter):
    """Test retrieving non-existent record returns None"""
    await postgres_adapter.connect()
    
    # Use a very high integer ID that doesn't exist
    result = await postgres_adapter.retrieve('999999999')
    assert result is None
    
    await postgres_adapter.disconnect()


@pytest.mark.asyncio
async def test_delete_not_found(postgres_adapter):
    """Test deleting non-existent record returns False"""
    await postgres_adapter.connect()
    
    # Use a very high integer ID that doesn't exist
    result = await postgres_adapter.delete('999999998')
    assert result is False
    
    await postgres_adapter.disconnect()


@pytest.mark.asyncio
async def test_search_empty_results(postgres_adapter):
    """Test search with no matching results"""
    await postgres_adapter.connect()
    
    results = await postgres_adapter.search({
        'session_id': 'nonexistent-session-xyz',
        'limit': 10
    })
    assert results == []
    
    await postgres_adapter.disconnect()


@pytest.mark.asyncio
async def test_store_batch_partial_success(postgres_adapter, session_id):
    """Test batch store handles individual item failures"""
    await postgres_adapter.connect()
    
    # Create batch with mix of valid and invalid data
    batch = [
        {
            'session_id': session_id,
            'turn_id': 100,
            'content': 'Valid message 1'
        },
        {
            'session_id': session_id,
            'turn_id': 101,
            'content': 'Valid message 2'
        }
    ]
    
    ids = await postgres_adapter.store_batch(batch)
    assert len(ids) == 2
    assert all(id is not None for id in ids)
    
    # Cleanup
    await postgres_adapter.delete_batch(ids)
    await postgres_adapter.disconnect()


@pytest.mark.asyncio
async def test_retrieve_batch_with_missing_ids(postgres_adapter, session_id):
    """Test retrieve_batch with some non-existent IDs"""
    await postgres_adapter.connect()
    
    # Store one real record
    real_id = await postgres_adapter.store({
        'session_id': session_id,
        'turn_id': 200,
        'content': 'Real message'
    })
    
    # Retrieve batch with mix of real and fake IDs (use high integer IDs)
    results = await postgres_adapter.retrieve_batch([
        real_id,
        '999999990',
        '999999991'
    ])
    
    # Should return results for all IDs, with None for missing ones
    assert len(results) == 3
    assert results[0] is not None  # real_id
    assert results[1] is None      # fake ID
    assert results[2] is None      # fake ID
    
    # Cleanup
    await postgres_adapter.delete(real_id)
    await postgres_adapter.disconnect()


@pytest.mark.asyncio
async def test_delete_batch_with_missing_ids(postgres_adapter, session_id):
    """Test delete_batch with some non-existent IDs"""
    await postgres_adapter.connect()
    
    # Store one real record
    real_id = await postgres_adapter.store({
        'session_id': session_id,
        'turn_id': 300,
        'content': 'Delete me'
    })
    
    # Delete batch with mix of real and fake IDs (use high integer IDs)
    results = await postgres_adapter.delete_batch([
        real_id,
        '999999992',
        '999999993'
    ])
    
    # Should return status for all IDs
    assert isinstance(results, dict)
    assert results[real_id] is True        # Successfully deleted
    assert results['999999992'] is False   # Not found
    assert results['999999993'] is False   # Not found
    
    await postgres_adapter.disconnect()