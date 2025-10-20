"""
Unit and integration tests for QdrantAdapter.
"""
import pytest
import os
import uuid
from unittest.mock import AsyncMock, Mock, patch
from src.storage.qdrant_adapter import QdrantAdapter
from src.storage.base import StorageConnectionError, StorageDataError, StorageQueryError

# ============================================================================
# Unit Tests (with mocks)
# ============================================================================

@pytest.mark.asyncio
class TestQdrantAdapterUnit:
    """Unit tests for QdrantAdapter (mocked dependencies)."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for unit tests."""
        mock = AsyncMock()
        mock.get_collection = AsyncMock()
        mock.create_collection = AsyncMock()
        mock.close = AsyncMock()
        mock.upsert = AsyncMock()
        mock.retrieve = AsyncMock(return_value=[])
        mock.search = AsyncMock(return_value=[])
        mock.delete = AsyncMock()
        return mock
    
    async def test_init(self):
        """Test adapter initialization."""
        config = {
            'url': 'http://localhost:6333',
            'collection_name': 'test_collection'
        }
        adapter = QdrantAdapter(config)
        assert adapter.url == 'http://localhost:6333'
        assert adapter.collection_name == 'test_collection'
        assert adapter.client is None
    
    async def test_init_missing_url(self):
        """Test adapter initialization with missing URL."""
        config = {'collection_name': 'test_collection'}
        with pytest.raises(StorageDataError):
            QdrantAdapter(config)
    
    async def test_connect_success(self, mock_qdrant_client):
        """Test successful connection."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            assert adapter.client is not None
            assert adapter.is_connected is True
    
    async def test_connect_collection_exists(self, mock_qdrant_client):
        """Test connection when collection already exists."""
        # Make get_collection not raise an exception to simulate existing collection
        mock_qdrant_client.get_collection = AsyncMock()
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            # Should not call create_collection
            mock_qdrant_client.create_collection.assert_not_called()
    
    async def test_connect_collection_created(self, mock_qdrant_client):
        """Test connection when collection needs to be created."""
        # Make get_collection raise an exception to simulate missing collection
        mock_qdrant_client.get_collection = AsyncMock(side_effect=Exception("Not found"))
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            # Should call create_collection
            mock_qdrant_client.create_collection.assert_called_once()
    
    async def test_disconnect(self, mock_qdrant_client):
        """Test disconnection."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            await adapter.disconnect()
            mock_qdrant_client.close.assert_called_once()
            assert adapter.client is None
            assert adapter.is_connected is False
    
    async def test_store_success(self, mock_qdrant_client):
        """Test successful storage of vector data."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            data = {
                'vector': [0.1, 0.2, 0.3],
                'content': 'Test content',
                'metadata': {'key': 'value'}
            }
            
            result_id = await adapter.store(data)
            assert isinstance(result_id, str)
            assert len(result_id) > 0
            mock_qdrant_client.upsert.assert_called_once()
    
    async def test_store_missing_required_fields(self, mock_qdrant_client):
        """Test storage with missing required fields."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            # Missing vector
            data = {
                'content': 'Test content'
            }
            
            with pytest.raises(StorageDataError):
                await adapter.store(data)
    
    async def test_store_not_connected(self):
        """Test storage when not connected."""
        config = {
            'url': 'http://localhost:6333',
            'collection_name': 'test_collection'
        }
        adapter = QdrantAdapter(config)
        
        data = {
            'vector': [0.1, 0.2, 0.3],
            'content': 'Test content'
        }
        
        with pytest.raises(StorageConnectionError):
            await adapter.store(data)
    
    async def test_retrieve_success(self, mock_qdrant_client):
        """Test successful retrieval of vector data."""
        # Mock a point response
        mock_point = Mock()
        mock_point.id = 'test-id'
        mock_point.vector = [0.1, 0.2, 0.3]
        mock_point.payload = {
            'content': 'Test content',
            'metadata': {'key': 'value'}
        }
        mock_qdrant_client.retrieve = AsyncMock(return_value=[mock_point])
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            result = await adapter.retrieve('test-id')
            assert result is not None
            assert result['id'] == 'test-id'
            assert result['content'] == 'Test content'
    
    async def test_retrieve_not_found(self, mock_qdrant_client):
        """Test retrieval when point is not found."""
        mock_qdrant_client.retrieve = AsyncMock(return_value=[])
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            result = await adapter.retrieve('non-existent-id')
            assert result is None
    
    async def test_search_success(self, mock_qdrant_client):
        """Test successful search operation."""
        # Mock search results
        mock_hit = Mock()
        mock_hit.id = 'test-id'
        mock_hit.vector = [0.1, 0.2, 0.3]
        mock_hit.payload = {
            'content': 'Test content',
            'metadata': {'key': 'value'}
        }
        mock_hit.score = 0.95
        mock_qdrant_client.search = AsyncMock(return_value=[mock_hit])
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'vector': [0.1, 0.2, 0.3],
                'limit': 5
            }
            
            results = await adapter.search(query)
            assert len(results) == 1
            assert results[0]['id'] == 'test-id'
            assert results[0]['score'] == 0.95
    
    async def test_search_missing_vector(self, mock_qdrant_client):
        """Test search with missing vector."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'limit': 5
            }
            
            with pytest.raises(StorageDataError):
                await adapter.search(query)
    
    async def test_delete_success(self, mock_qdrant_client):
        """Test successful deletion."""
        mock_result = Mock()
        mock_result.status = "completed"
        mock_qdrant_client.delete = AsyncMock(return_value=mock_result)
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            result = await adapter.delete('test-id')
            assert result is True
            mock_qdrant_client.delete.assert_called_once()
    
    async def test_delete_not_connected(self):
        """Test deletion when not connected."""
        config = {
            'url': 'http://localhost:6333',
            'collection_name': 'test_collection'
        }
        adapter = QdrantAdapter(config)
        
        with pytest.raises(StorageConnectionError):
            await adapter.delete('test-id')

# ============================================================================
# Integration Tests (real Qdrant)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestQdrantAdapterIntegration:
    """Integration tests for QdrantAdapter (real Qdrant)."""
    
    @pytest.fixture
    def qdrant_config(self):
        """Qdrant configuration for integration tests."""
        return {
            'url': os.getenv('QDRANT_URL', 'http://localhost:6333'),
            'collection_name': f'test_collection_{uuid.uuid4().hex[:8]}'
        }
    
    async def test_full_workflow(self, qdrant_config):
        """Test complete CRUD workflow."""
        adapter = QdrantAdapter(qdrant_config)
        await adapter.connect()
        
        try:
            # Store vector
            vector_data = {
                'vector': [0.1] * 384,  # 384-dimensional vector
                'content': 'Test vector for integration',
                'metadata': {
                    'test_id': str(uuid.uuid4()),
                    'type': 'integration_test'
                }
            }
            
            point_id = await adapter.store(vector_data)
            assert point_id is not None
            
            # Retrieve vector
            retrieved = await adapter.retrieve(point_id)
            assert retrieved is not None
            assert retrieved['content'] == 'Test vector for integration'
            assert 'metadata' in retrieved
            
            # Search similar vectors
            search_query = {
                'vector': [0.1] * 384,
                'limit': 5,
                'score_threshold': 0.0
            }
            
            search_results = await adapter.search(search_query)
            assert len(search_results) >= 1
            assert any(r['id'] == point_id for r in search_results)
            
            # Delete vector
            deleted = await adapter.delete(point_id)
            assert deleted is True
            
            # Verify deletion
            retrieved_after_delete = await adapter.retrieve(point_id)
            assert retrieved_after_delete is None
            
        finally:
            await adapter.disconnect()
    
    async def test_context_manager(self, qdrant_config):
        """Test context manager protocol."""
        async with QdrantAdapter(qdrant_config) as adapter:
            assert adapter.is_connected is True
            
            # Simple operation to verify connection
            vector_data = {
                'vector': [0.2] * 384,
                'content': 'Context manager test'
            }
            
            point_id = await adapter.store(vector_data)
            assert point_id is not None
            
            # Clean up
            await adapter.delete(point_id)
        
        # Should be disconnected after context
        assert adapter.is_connected is False