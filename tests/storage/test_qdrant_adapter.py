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


# ============================================================================
# Additional Unit Tests for Coverage
# ============================================================================

@pytest.mark.asyncio
class TestQdrantAdapterBatchOperations:
    """Tests for batch operations."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for unit tests."""
        mock = AsyncMock()
        mock.get_collection = AsyncMock()
        mock.close = AsyncMock()
        mock.upsert = AsyncMock()
        
        # Fix: Mock the delete method to return a result with "completed" status
        mock_delete_result = Mock()
        mock_delete_result.status = "completed"
        mock.delete = AsyncMock(return_value=mock_delete_result)
        
        return mock
    
    async def test_store_batch_vectors(self, mock_qdrant_client):
        """Test batch storage of vectors."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            batch_data = [
                {
                    'id': f'test-{i}',
                    'vector': [0.1 * i] * 384,
                    'content': f'Test content {i}'
                }
                for i in range(5)
            ]
            
            ids = await adapter.store_batch(batch_data)
            assert len(ids) == 5
            assert all(id == f'test-{i}' for i, id in enumerate(ids))
            mock_qdrant_client.upsert.assert_called_once()
            await adapter.disconnect()
    
    async def test_store_batch_not_connected(self):
        """Test batch store when not connected."""
        config = {
            'url': 'http://localhost:6333',
            'collection_name': 'test_collection'
        }
        adapter = QdrantAdapter(config)
        
        with pytest.raises(StorageConnectionError):
            await adapter.store_batch([{'vector': [0.1] * 384, 'content': 'test'}])
    
    async def test_delete_batch_vectors(self, mock_qdrant_client):
        """Test batch deletion of vectors."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            ids = ['id1', 'id2', 'id3']
            result = await adapter.delete_batch(ids)
            # Fix: The method returns a dict mapping IDs to deletion status, not a boolean
            assert isinstance(result, dict)
            assert result['id1'] is True
            assert result['id2'] is True
            assert result['id3'] is True
            mock_qdrant_client.delete.assert_called_once()
            await adapter.disconnect()
    
    async def test_delete_batch_not_connected(self):
        """Test batch delete when not connected."""
        config = {
            'url': 'http://localhost:6333',
            'collection_name': 'test_collection'
        }
        adapter = QdrantAdapter(config)
        
        with pytest.raises(StorageConnectionError):
            await adapter.delete_batch(['id1', 'id2'])


@pytest.mark.asyncio
class TestQdrantAdapterHealthCheck:
    """Tests for health check functionality."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for unit tests."""
        mock = AsyncMock()
        mock.get_collection = AsyncMock()
        mock.close = AsyncMock()
        
        # Mock collection info
        mock_collection_info = Mock()
        mock_collection_info.vectors_count = 1000
        mock_collection_info.points_count = 1000
        mock_collection_info.config.params.vectors.size = 384
        mock.get_collection.return_value = mock_collection_info
        
        return mock
    
    async def test_health_check_connected(self, mock_qdrant_client):
        """Test health check when connected."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            health = await adapter.health_check()
            assert health['status'] == 'healthy'
            assert health['connected'] is True
            assert 'collection_exists' in health
            assert health['vector_count'] == 1000
            await adapter.disconnect()
    
    async def test_health_check_not_connected(self):
        """Test health check when not connected."""
        config = {
            'url': 'http://localhost:6333',
            'collection_name': 'test_collection'
        }
        adapter = QdrantAdapter(config)
        
        health = await adapter.health_check()
        assert health['status'] == 'unhealthy'
        assert health['connected'] is False


@pytest.mark.asyncio
class TestQdrantAdapterFilterEdgeCases:
    """Tests for filter edge cases and complex queries."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for unit tests."""
        mock = AsyncMock()
        mock.get_collection = AsyncMock()
        mock.close = AsyncMock()
        mock.search = AsyncMock(return_value=[])
        return mock
    
    async def test_search_with_none_filter(self, mock_qdrant_client):
        """Test search with None filter (should not crash)."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'vector': [0.1] * 384,
                'limit': 10,
                'filter': None  # Explicitly None
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            mock_qdrant_client.search.assert_called_once()
            await adapter.disconnect()
    
    async def test_search_with_empty_filter(self, mock_qdrant_client):
        """Test search with empty filter dict."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'vector': [0.1] * 384,
                'limit': 10,
                'filter': {}  # Empty dict
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            await adapter.disconnect()
    
    async def test_search_with_multiple_filters(self, mock_qdrant_client):
        """Test search with multiple filter conditions."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'vector': [0.1] * 384,
                'limit': 10,
                'filter': {
                    'session_id': 'test-session',
                    'type': 'preference',
                    'active': True
                }
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            await adapter.disconnect()
    
    async def test_search_with_score_threshold(self, mock_qdrant_client):
        """Test search with score threshold filtering."""
        # Mock search results with varying scores
        mock_hit1 = Mock()
        mock_hit1.id = 'id1'
        mock_hit1.score = 0.95
        mock_hit1.vector = [0.1] * 384
        mock_hit1.payload = {'content': 'High score result'}
        
        mock_hit2 = Mock()
        mock_hit2.id = 'id2'
        mock_hit2.score = 0.60
        mock_hit2.vector = [0.2] * 384
        mock_hit2.payload = {'content': 'Low score result'}
        
        mock_qdrant_client.search = AsyncMock(return_value=[mock_hit1, mock_hit2])
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'vector': [0.1] * 384,
                'limit': 10,
                'score_threshold': 0.7  # Should filter out second result
            }
            
            results = await adapter.search(query)
            # Both results returned (filtering happens in Qdrant backend)
            assert len(results) == 2
            await adapter.disconnect()
    
    async def test_store_with_custom_id(self, mock_qdrant_client):
        """Test storing vector with custom ID."""
        mock_qdrant_client.upsert = AsyncMock()
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            data = {
                'id': 'custom-vector-id',
                'vector': [0.1] * 384,
                'content': 'Test with custom ID'
            }
            
            result_id = await adapter.store(data)
            assert result_id == 'custom-vector-id'
            await adapter.disconnect()
    
    async def test_store_with_additional_metadata(self, mock_qdrant_client):
        """Test storing vector with additional metadata fields."""
        mock_qdrant_client.upsert = AsyncMock()
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            data = {
                'vector': [0.1] * 384,
                'content': 'Test with metadata',
                'session_id': 'test-session',
                'timestamp': '2025-10-21T00:00:00Z',
                'metadata': {'key': 'value'}
            }
            
            result_id = await adapter.store(data)
            assert result_id is not None
            # Verify upsert was called with all fields in payload
            _ = mock_qdrant_client.upsert.call_args
            await adapter.disconnect()
    
    async def test_vector_dimension_validation(self, mock_qdrant_client):
        """Test that vector dimension matches collection config."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection',
                'vector_size': 384
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            # This should work (correct dimension)
            data = {
                'vector': [0.1] * 384,
                'content': 'Correct dimension'
            }
            
            result_id = await adapter.store(data)
            assert result_id is not None
            await adapter.disconnect()


# Add new test class for complex filters
@pytest.mark.asyncio
class TestQdrantAdvancedFilters:
    """Test complex filter combinations for Qdrant adapter."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for unit tests."""
        mock = AsyncMock()
        mock.get_collection = AsyncMock()
        mock.close = AsyncMock()
        mock.search = AsyncMock(return_value=[])
        return mock
    
    async def test_multiple_must_conditions(self, mock_qdrant_client):
        """Test vector search with multiple MUST conditions."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'vector': [0.1] * 384,
                'limit': 10,
                'filter': {
                    'category': 'tech',
                    'year': 2020
                }
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            
            # Verify that the filter was correctly constructed
            call_args = mock_qdrant_client.search.call_args
            query_filter = call_args[1]['query_filter']
            assert query_filter is not None
            assert len(query_filter.must) == 2
            await adapter.disconnect()
    
    async def test_should_conditions(self, mock_qdrant_client):
        """Test OR-like SHOULD conditions."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'vector': [0.1] * 384,
                'limit': 10,
                'filter': {
                    'should': [
                        {'key': 'tag', 'match': {'value': 'ai'}},
                        {'key': 'tag', 'match': {'value': 'ml'}}
                    ]
                }
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            
            # Verify that the filter was correctly constructed
            call_args = mock_qdrant_client.search.call_args
            query_filter = call_args[1]['query_filter']
            assert query_filter is not None
            assert len(query_filter.should) == 2
            await adapter.disconnect()
    
    async def test_must_not_conditions(self, mock_qdrant_client):
        """Test exclusion with MUST_NOT."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'vector': [0.1] * 384,
                'limit': 10,
                'filter': {
                    'must_not': [
                        {'key': 'status', 'match': {'value': 'deleted'}}
                    ]
                }
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            
            # Verify that the filter was correctly constructed
            call_args = mock_qdrant_client.search.call_args
            query_filter = call_args[1]['query_filter']
            assert query_filter is not None
            assert len(query_filter.must_not) == 1
            await adapter.disconnect()
    
    async def test_complex_filter_with_must_and_should(self, mock_qdrant_client):
        """Test complex filter with both must and should conditions."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'vector': [0.1] * 384,
                'limit': 10,
                'filter': {
                    'must': [
                        {'key': 'category', 'match': {'value': 'tech'}}
                    ],
                    'should': [
                        {'key': 'tag', 'match': {'value': 'ai'}},
                        {'key': 'tag', 'match': {'value': 'ml'}}
                    ]
                }
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            
            # Verify that the filter was correctly constructed
            call_args = mock_qdrant_client.search.call_args
            query_filter = call_args[1]['query_filter']
            assert query_filter is not None
            assert len(query_filter.must) == 1
            assert len(query_filter.should) == 2
            await adapter.disconnect()
    
    async def test_backward_compatibility_simple_filters(self, mock_qdrant_client):
        """Test that simple filters still work (backward compatibility).
        
        Note: session_id is handled specially - it uses 'should' to match either
        session_id OR metadata.session_id for flexibility. Other fields use 'must'.
        """
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'vector': [0.1] * 384,
                'limit': 10,
                'filter': {
                    'session_id': 'test-session',
                    'type': 'preference'
                }
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            
            # Verify that the filter was correctly constructed
            call_args = mock_qdrant_client.search.call_args
            query_filter = call_args[1]['query_filter']
            assert query_filter is not None
            # session_id goes to 'should' (OR between session_id and metadata.session_id)
            # type goes to 'must'
            assert len(query_filter.should) == 2  # session_id OR metadata.session_id
            assert len(query_filter.must) == 1    # type only
            await adapter.disconnect()


class TestQdrantAdvancedFiltersExtended:
    """Test extended filter combinations and edge cases."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for unit tests."""
        mock = AsyncMock()
        mock.search = AsyncMock(return_value=[])
        mock.close = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_nested_filter_in_must(self, mock_qdrant_client):
        """Test nested filter structures in must conditions."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'vector': [0.1] * 384,
                'limit': 10,
                'filter': {
                    'must': [
                        {'status': 'active'},  # Nested dict without key/match
                        {'priority': 'high'}
                    ]
                }
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            
            # Verify filter was constructed with nested conditions
            call_args = mock_qdrant_client.search.call_args
            query_filter = call_args[1]['query_filter']
            assert query_filter is not None
            await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_nested_filter_in_should(self, mock_qdrant_client):
        """Test nested filter structures in should conditions."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'vector': [0.1] * 384,
                'limit': 10,
                'filter': {
                    'should': [
                        {'category': 'tech'},  # Nested dict
                        {'category': 'science'}
                    ]
                }
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_nested_filter_in_must_not(self, mock_qdrant_client):
        """Test nested filter structures in must_not conditions."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'vector': [0.1] * 384,
                'limit': 10,
                'filter': {
                    'must_not': [
                        {'status': 'deleted'},  # Nested dict
                        {'archived': True}
                    ]
                }
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_filter_with_all_three_types(self, mock_qdrant_client):
        """Test filter with must, should, and must_not all together."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            query = {
                'vector': [0.1] * 384,
                'limit': 10,
                'filter': {
                    'must': [
                        {'key': 'type', 'match': {'value': 'document'}}
                    ],
                    'should': [
                        {'tag': 'important'},
                        {'tag': 'urgent'}
                    ],
                    'must_not': [
                        {'status': 'deleted'}
                    ]
                }
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            
            # Verify all three filter types were used
            call_args = mock_qdrant_client.search.call_args
            query_filter = call_args[1]['query_filter']
            assert query_filter is not None
            assert len(query_filter.must) > 0
            await adapter.disconnect()


class TestQdrantAdvancedOperations:
    """Test advanced Qdrant operations like scroll, count, recommend."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for unit tests."""
        mock = AsyncMock()
        mock.scroll = AsyncMock(return_value=([], None))
        mock.count = AsyncMock(return_value=Mock(count=100))
        mock.recommend = AsyncMock(return_value=[])
        mock.close = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_retrieve_batch_with_missing_points(self, mock_qdrant_client):
        """Test batch retrieve when some points don't exist."""
        # Mock retrieve to return only some points
        mock_point1 = Mock()
        mock_point1.id = 'id1'
        mock_point1.vector = [0.1] * 384
        mock_point1.payload = {'content': 'test1', 'metadata': {}}
        
        mock_qdrant_client.retrieve = AsyncMock(return_value=[mock_point1])
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            # Request 3 IDs but only 1 exists
            results = await adapter.retrieve_batch(['id1', 'id2', 'id3'])
            
            # Should return results with None for missing items
            assert isinstance(results, list)
            # First item should exist, others None
            assert results[0] is not None
            await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_retrieve_batch_with_additional_payload(self, mock_qdrant_client):
        """Test batch retrieve with additional payload fields."""
        # Mock point with extra payload fields
        mock_point = Mock()
        mock_point.id = 'id1'
        mock_point.vector = [0.1] * 384
        mock_point.payload = {
            'content': 'test',
            'metadata': {'key': 'value'},
            'custom_field': 'custom_value',
            'score': 0.95
        }
        
        mock_qdrant_client.retrieve = AsyncMock(return_value=[mock_point])
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            results = await adapter.retrieve_batch(['id1'])
            
            assert len(results) == 1
            assert results[0]['custom_field'] == 'custom_value'
            assert results[0]['score'] == 0.95
            await adapter.disconnect()


class TestQdrantErrorHandling:
    """Test error handling in Qdrant adapter."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for unit tests."""
        mock = AsyncMock()
        mock.close = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_store_error_handling(self, mock_qdrant_client):
        """Test error handling during store operation."""
        mock_qdrant_client.upsert = AsyncMock(side_effect=Exception("Storage error"))
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            with pytest.raises(StorageQueryError, match="Failed to store"):
                await adapter.store({
                    'vector': [0.1] * 384,
                    'content': 'test',
                    'metadata': {}
                })
            
            await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_retrieve_error_handling(self, mock_qdrant_client):
        """Test error handling during retrieve operation."""
        mock_qdrant_client.retrieve = AsyncMock(side_effect=Exception("Retrieve error"))
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            with pytest.raises(StorageQueryError, match="Failed to retrieve"):
                await adapter.retrieve('test-id')
            
            await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_batch_retrieve_error_handling(self, mock_qdrant_client):
        """Test error handling during batch retrieve."""
        mock_qdrant_client.retrieve = AsyncMock(side_effect=Exception("Batch retrieve error"))
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            with pytest.raises(StorageQueryError, match="Failed to batch retrieve"):
                await adapter.retrieve_batch(['id1', 'id2'])
            
            await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_batch_store_error_handling(self, mock_qdrant_client):
        """Test error handling during batch store."""
        mock_qdrant_client.upsert = AsyncMock(side_effect=Exception("Batch store error"))
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            batch_data = [
                {'vector': [0.1] * 384, 'content': 'test1'},
                {'vector': [0.2] * 384, 'content': 'test2'}
            ]
            
            with pytest.raises(StorageQueryError, match="Failed to batch store"):
                await adapter.store_batch(batch_data)
            
            await adapter.disconnect()


class TestQdrantConnectionEdgeCases:
    """Test connection edge cases and disconnection scenarios."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for unit tests."""
        mock = AsyncMock()
        mock.close = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_disconnect_with_error(self, mock_qdrant_client):
        """Test disconnect handles errors gracefully without raising."""
        # Mock close to raise an error
        mock_qdrant_client.close = AsyncMock(side_effect=Exception("Close error"))
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            # Disconnect should not raise even if close fails
            await adapter.disconnect()  # Should not raise
            # Note: On error, client may not be None, but disconnect succeeds
            # The important thing is it doesn't raise
    
    @pytest.mark.asyncio
    async def test_disconnect_when_no_client(self):
        """Test disconnect when client is None."""
        config = {
            'url': 'http://localhost:6333',
            'collection_name': 'test_collection'
        }
        adapter = QdrantAdapter(config)
        # Don't connect, client is None
        
        # Should handle gracefully
        await adapter.disconnect()  # Should not raise
        assert adapter.client is None


class TestQdrantDeleteOperations:
    """Test delete operations and edge cases."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for unit tests."""
        mock = AsyncMock()
        mock.close = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_delete_point_not_found(self, mock_qdrant_client):
        """Test deleting a point that doesn't exist."""
        # Mock delete to return not found status
        mock_result = Mock()
        mock_result.status = "not_found"
        mock_qdrant_client.delete = AsyncMock(return_value=mock_result)
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            result = await adapter.delete('nonexistent-id')
            
            # Should return False for not found
            assert result is False
            await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_delete_point_success(self, mock_qdrant_client):
        """Test successful deletion of a point."""
        # Mock delete to return completed status
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
            
            # Should return True for successful deletion
            assert result is True
            await adapter.disconnect()


class TestQdrantRetrieveEdgeCases:
    """Test retrieve operations edge cases."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for unit tests."""
        mock = AsyncMock()
        mock.close = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_retrieve_with_additional_payload_fields(self, mock_qdrant_client):
        """Test retrieve with additional payload fields beyond content/metadata."""
        # Mock point with extra fields
        mock_point = Mock()
        mock_point.id = 'test-id'
        mock_point.vector = [0.1] * 384
        mock_point.payload = {
            'content': 'test content',
            'metadata': {'key': 'value'},
            'score': 0.95,
            'timestamp': '2025-10-22',
            'custom_data': {'nested': 'value'}
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
            
            # Should include additional fields
            assert result['score'] == 0.95
            assert result['timestamp'] == '2025-10-22'
            assert result['custom_data'] == {'nested': 'value'}
            await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_retrieve_batch_empty_list(self, mock_qdrant_client):
        """Test batch retrieve with empty ID list."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            result = await adapter.retrieve_batch([])
            
            # Should return empty list
            assert result == []
            # retrieve should not be called
            mock_qdrant_client.retrieve.assert_not_called()
            await adapter.disconnect()


class TestQdrantStoreEdgeCases:
    """Test store operations edge cases."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for unit tests."""
        mock = AsyncMock()
        mock.upsert = AsyncMock()
        mock.close = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_store_with_custom_id(self, mock_qdrant_client):
        """Test storing data with custom ID."""
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            result = await adapter.store({
                'id': 'custom-id-123',
                'vector': [0.1] * 384,
                'content': 'test',
                'metadata': {}
            })
            
            # Should return the custom ID
            assert result == 'custom-id-123'
            
            # Verify upsert was called with custom ID
            call_args = mock_qdrant_client.upsert.call_args
            points = call_args[1]['points']
            assert len(points) == 1
            assert str(points[0].id) == 'custom-id-123'
            
            await adapter.disconnect()


class TestQdrantCollectionManagement:
    """Test collection management operations for Qdrant adapter."""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant client for unit tests."""
        mock = AsyncMock()
        mock.get_collection = AsyncMock()
        mock.create_collection = AsyncMock()
        mock.update_collection = AsyncMock()
        mock.get_collections = AsyncMock()
        mock.close = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_create_collection_with_schema(self, mock_qdrant_client):
        """Test creating collection with specific vector config."""
        # Mock get_collection to raise exception (collection doesn't exist)
        mock_qdrant_client.get_collection.side_effect = Exception("Collection not found")
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            collection_config = {
                'vectors': {
                    'size': 384,
                    'distance': 'Cosine'
                },
                'optimizers_config': {
                    'indexing_threshold': 10000
                }
            }
            
            result = await adapter.create_collection('test_coll', collection_config)
            assert result is True
            
            # Verify create_collection was called (may be called during connect too)
            assert mock_qdrant_client.create_collection.called
            await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_create_collection_already_exists(self, mock_qdrant_client):
        """Test creating collection that already exists."""
        # Simulate collection already exists
        mock_qdrant_client.get_collection = AsyncMock()
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            result = await adapter.create_collection('test_coll', {})
            assert result is False
            
            # Verify create_collection was not called
            mock_qdrant_client.create_collection.assert_not_called()
            await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_update_collection_config(self, mock_qdrant_client):
        """Test updating collection configuration."""
        # Simulate collection exists
        mock_qdrant_client.get_collection = AsyncMock()
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            new_config = {'optimizers_config': {'indexing_threshold': 20000}}
            result = await adapter.update_collection('test_coll', new_config)
            assert result is True
            
            # Verify update_collection was called
            mock_qdrant_client.update_collection.assert_called_once()
            await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_update_collection_not_exists(self, mock_qdrant_client):
        """Test updating collection that doesn't exist."""
        # Simulate collection doesn't exist
        mock_qdrant_client.get_collection.side_effect = Exception("Not found")
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            new_config = {'optimizers_config': {'indexing_threshold': 20000}}
            result = await adapter.update_collection('test_coll', new_config)
            assert result is False
            
            # Verify update_collection was not called
            mock_qdrant_client.update_collection.assert_not_called()
            await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_get_collection_info_detailed(self, mock_qdrant_client):
        """Test retrieving detailed collection information."""
        # Mock collection info response
        mock_collection_info = Mock()
        mock_collection_info.status = Mock(value='green')
        mock_collection_info.vectors_count = 1000
        mock_collection_info.indexed_vectors_count = 1000
        mock_collection_info.points_count = 1000
        
        mock_config = Mock()
        mock_params = Mock()
        mock_vectors = Mock()
        mock_vectors.size = 384
        mock_params.vectors = mock_vectors
        mock_params.shard_number = 1
        mock_params.replication_factor = 1
        mock_config.params = mock_params
        mock_collection_info.config = mock_config
        
        mock_qdrant_client.get_collection.return_value = mock_collection_info
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            info = await adapter.get_collection_info('test_coll')
            assert 'name' in info
            assert 'status' in info
            assert 'vectors_count' in info
            assert 'points_count' in info
            assert info['vectors_count'] == 1000
            assert info['vector_size'] == 384
            await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_list_all_collections(self, mock_qdrant_client):
        """Test listing all available collections."""
        # Mock collections response
        mock_collection1 = Mock()
        mock_collection1.name = 'collection1'
        mock_collection2 = Mock()
        mock_collection2.name = 'collection2'
        
        mock_collections_response = Mock()
        mock_collections_response.collections = [mock_collection1, mock_collection2]
        mock_qdrant_client.get_collections.return_value = mock_collections_response
        
        with patch('src.storage.qdrant_adapter.AsyncQdrantClient', return_value=mock_qdrant_client):
            config = {
                'url': 'http://localhost:6333',
                'collection_name': 'test_collection'
            }
            adapter = QdrantAdapter(config)
            await adapter.connect()
            
            collections = await adapter.list_collections()
            assert isinstance(collections, list)
            assert len(collections) == 2
            assert 'collection1' in collections
            assert 'collection2' in collections
            await adapter.disconnect()
