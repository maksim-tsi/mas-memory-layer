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