"""
Unit and integration tests for TypesenseAdapter.
"""
import pytest
import pytest_asyncio
import os
import uuid
from unittest.mock import AsyncMock, Mock, patch
from src.storage.typesense_adapter import TypesenseAdapter
from src.storage.base import StorageConnectionError, StorageDataError, StorageQueryError
import httpx

# ============================================================================
# Unit Tests (with mocks)
# ============================================================================

@pytest.mark.asyncio
class TestTypesenseAdapterUnit:
    """Unit tests for TypesenseAdapter (mocked dependencies)."""
    
    @pytest.fixture
    def mock_httpx_client(self):
        """Mock HTTPX client for unit tests."""
        mock = AsyncMock()
        mock.aclose = AsyncMock()
        mock.get = AsyncMock()
        mock.post = AsyncMock()
        mock.delete = AsyncMock()
        return mock
    
    async def test_init(self):
        """Test adapter initialization."""
        config = {
            'url': 'http://localhost:8108',
            'api_key': 'test_key',
            'collection_name': 'test_collection'
        }
        adapter = TypesenseAdapter(config)
        assert adapter.url == 'http://localhost:8108'
        assert adapter.api_key == 'test_key'
        assert adapter.collection_name == 'test_collection'
        assert adapter.client is None
    
    async def test_init_missing_credentials(self):
        """Test adapter initialization with missing credentials."""
        config = {'url': 'http://localhost:8108'}
        with pytest.raises(StorageDataError):
            TypesenseAdapter(config)
    
    async def test_connect_success(self, mock_httpx_client):
        """Test successful connection."""
        # Mock response for collection check (collection exists)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx_client.get.return_value = mock_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            assert adapter.client is not None
            assert adapter.is_connected is True
    
    async def test_connect_collection_created(self, mock_httpx_client):
        """Test connection when collection needs to be created."""
        # Mock response for collection check (collection doesn't exist)
        not_found_response = Mock()
        not_found_response.status_code = 404
        not_found_response.raise_for_status = Mock()
        
        # Mock response for collection creation
        create_response = Mock()
        create_response.status_code = 200
        create_response.raise_for_status = Mock()
        
        mock_httpx_client.get.return_value = not_found_response
        mock_httpx_client.post.return_value = create_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection',
                'schema': {
                    'name': 'test_collection',
                    'fields': [
                        {'name': 'content', 'type': 'string'}
                    ]
                }
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            assert adapter.client is not None
            assert adapter.is_connected is True
            # Should call post to create collection
            mock_httpx_client.post.assert_called_once()
    
    async def test_disconnect(self, mock_httpx_client):
        """Test disconnection."""
        # Mock response for collection check
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx_client.get.return_value = mock_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            await adapter.disconnect()
            mock_httpx_client.aclose.assert_called_once()
            assert adapter.client is None
            assert adapter.is_connected is False
    
    async def test_store_success(self, mock_httpx_client):
        """Test successful document storage."""
        # Mock response for collection check
        collection_response = Mock()
        collection_response.status_code = 200
        mock_httpx_client.get.return_value = collection_response
        
        # Mock response for document storage
        store_response = Mock()
        store_response.status_code = 200
        store_response.raise_for_status = Mock()
        store_response.json = Mock(return_value={'id': 'doc-id'})
        mock_httpx_client.post.return_value = store_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            data = {
                'content': 'Test document',
                'metadata': {'key': 'value'}
            }
            
            result_id = await adapter.store(data)
            assert result_id == 'doc-id'
            mock_httpx_client.post.assert_called_once()
    
    async def test_store_with_id(self, mock_httpx_client):
        """Test document storage with provided ID."""
        # Mock response for collection check
        collection_response = Mock()
        collection_response.status_code = 200
        mock_httpx_client.get.return_value = collection_response
        
        # Mock response for document storage
        store_response = Mock()
        store_response.status_code = 200
        store_response.raise_for_status = Mock()
        store_response.json = Mock(return_value={'id': 'provided-id'})
        mock_httpx_client.post.return_value = store_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            data = {
                'id': 'provided-id',
                'content': 'Test document',
                'metadata': {'key': 'value'}
            }
            
            result_id = await adapter.store(data)
            assert result_id == 'provided-id'
    
    async def test_store_not_connected(self):
        """Test storage when not connected."""
        config = {
            'url': 'http://localhost:8108',
            'api_key': 'test_key',
            'collection_name': 'test_collection'
        }
        adapter = TypesenseAdapter(config)
        
        data = {
            'content': 'Test document'
        }
        
        with pytest.raises(StorageConnectionError):
            await adapter.store(data)
    
    async def test_store_http_error(self, mock_httpx_client):
        """Test storage with HTTP error."""
        # Mock response for collection check
        collection_response = Mock()
        collection_response.status_code = 200
        mock_httpx_client.get.return_value = collection_response
        
        # Mock HTTP error for document storage
        store_response = Mock()
        store_response.status_code = 400
        store_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError("Bad Request", request=Mock(), response=store_response))
        mock_httpx_client.post.return_value = store_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            data = {
                'content': 'Test document'
            }
            
            with pytest.raises(StorageQueryError):
                await adapter.store(data)
    
    async def test_retrieve_success(self, mock_httpx_client):
        """Test successful document retrieval."""
        # Mock response for collection check
        collection_response = Mock()
        collection_response.status_code = 200
        mock_httpx_client.get.return_value = collection_response
        
        # Mock response for document retrieval
        retrieve_response = Mock()
        retrieve_response.status_code = 200
        retrieve_response.raise_for_status = Mock()
        retrieve_response.json = Mock(return_value={'id': 'doc-id', 'content': 'Test document'})
        mock_httpx_client.get.return_value = retrieve_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            result = await adapter.retrieve('doc-id')
            assert result is not None
            assert result['id'] == 'doc-id'
            assert result['content'] == 'Test document'
    
    async def test_retrieve_not_found(self, mock_httpx_client):
        """Test retrieval when document is not found."""
        # Mock response for collection check
        collection_response = Mock()
        collection_response.status_code = 200
        mock_httpx_client.get.return_value = collection_response
        
        # Mock response for document retrieval (not found)
        retrieve_response = Mock()
        retrieve_response.status_code = 404
        retrieve_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError("Not Found", request=Mock(), response=retrieve_response))
        mock_httpx_client.get.return_value = retrieve_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            result = await adapter.retrieve('non-existent-id')
            assert result is None
    
    async def test_search_success(self, mock_httpx_client):
        """Test successful search operation."""
        # Mock response for collection check
        collection_response = Mock()
        collection_response.status_code = 200
        mock_httpx_client.get.return_value = collection_response
        
        # Mock response for search
        search_response = Mock()
        search_response.status_code = 200
        search_response.raise_for_status = Mock()
        search_response.json = Mock(return_value={
            'hits': [
                {
                    'document': {
                        'id': 'doc-1',
                        'content': 'First document'
                    },
                    'highlights': []
                },
                {
                    'document': {
                        'id': 'doc-2',
                        'content': 'Second document'
                    },
                    'highlights': []
                }
            ]
        })
        mock_httpx_client.get.return_value = search_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            query = {
                'q': 'document',
                'query_by': 'content',
                'limit': 5
            }
            
            results = await adapter.search(query)
            assert len(results) == 2
            assert results[0]['id'] == 'doc-1'
            assert results[1]['id'] == 'doc-2'
    
    async def test_search_missing_required_fields(self, mock_httpx_client):
        """Test search with missing required fields."""
        # Mock response for collection check
        collection_response = Mock()
        collection_response.status_code = 200
        mock_httpx_client.get.return_value = collection_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            # Missing 'q' field
            query = {
                'query_by': 'content'
            }
            
            with pytest.raises(StorageDataError):
                await adapter.search(query)
    
    async def test_delete_success(self, mock_httpx_client):
        """Test successful document deletion."""
        # Mock response for collection check
        collection_response = Mock()
        collection_response.status_code = 200
        mock_httpx_client.get.return_value = collection_response
        
        # Mock response for document deletion
        delete_response = Mock()
        delete_response.status_code = 200
        mock_httpx_client.delete.return_value = delete_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            result = await adapter.delete('doc-id')
            assert result is True
            mock_httpx_client.delete.assert_called_once()
    
    async def test_delete_not_connected(self):
        """Test deletion when not connected."""
        config = {
            'url': 'http://localhost:8108',
            'api_key': 'test_key',
            'collection_name': 'test_collection'
        }
        adapter = TypesenseAdapter(config)
        
        with pytest.raises(StorageConnectionError):
            await adapter.delete('doc-id')
    
    async def test_connect_missing_api_key(self):
        """Test initialization fails when API key is missing."""
        config = {
            'url': 'http://localhost:8108',
            'api_key': '',  # Empty API key
            'collection_name': 'test_collection'
        }
        
        with pytest.raises(StorageDataError, match="URL and API key required"):
            TypesenseAdapter(config)
    
    async def test_connect_http_error(self, mock_httpx_client):
        """Test connection handling HTTP errors."""
        mock_httpx_client.get.side_effect = httpx.HTTPError("Connection failed")
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            
            with pytest.raises(StorageConnectionError, match="Failed to connect"):
                await adapter.connect()
    
    async def test_disconnect_when_not_connected(self):
        """Test disconnect when already disconnected."""
        config = {
            'url': 'http://localhost:8108',
            'api_key': 'test_key',
            'collection_name': 'test_collection'
        }
        adapter = TypesenseAdapter(config)
        
        # Should not raise error
        await adapter.disconnect()
        assert adapter.is_connected is False
    
    async def test_store_generic_error(self, mock_httpx_client):
        """Test store handling generic errors."""
        mock_httpx_client.post.side_effect = Exception("Unexpected error")
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            with pytest.raises(StorageQueryError, match="Store failed"):
                await adapter.store({'content': 'test'})
    
    async def test_retrieve_http_error(self, mock_httpx_client):
        """Test retrieve handling HTTP status errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            "Server error", request=Mock(), response=mock_response
        ))
        mock_httpx_client.get.return_value = mock_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            with pytest.raises(StorageQueryError, match="Retrieve failed"):
                await adapter.retrieve('doc-id')
    
    async def test_retrieve_generic_error(self, mock_httpx_client):
        """Test retrieve handling generic errors."""
        mock_httpx_client.get.side_effect = Exception("Unexpected error")
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            with pytest.raises(StorageQueryError, match="Retrieve failed"):
                await adapter.retrieve('doc-id')
    
    async def test_search_http_error(self, mock_httpx_client):
        """Test search handling HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            "Server error", request=Mock(), response=mock_response
        ))
        mock_httpx_client.get.return_value = mock_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            with pytest.raises(StorageQueryError, match="Search failed"):
                await adapter.search({'q': 'test', 'query_by': 'content'})
    
    async def test_search_generic_error(self, mock_httpx_client):
        """Test search handling generic errors."""
        mock_httpx_client.get.side_effect = Exception("Unexpected error")
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            with pytest.raises(StorageQueryError, match="Search failed"):
                await adapter.search({'q': 'test', 'query_by': 'content'})
    
    async def test_search_empty_results(self, mock_httpx_client):
        """Test search with no hits."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={'hits': []})
        mock_response.raise_for_status = Mock()
        mock_httpx_client.get.return_value = mock_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            results = await adapter.search({'q': 'nonexistent', 'query_by': 'content'})
            assert results == []
    
    async def test_search_not_connected(self):
        """Test search when not connected."""
        config = {
            'url': 'http://localhost:8108',
            'api_key': 'test_key',
            'collection_name': 'test_collection'
        }
        adapter = TypesenseAdapter(config)
        
        with pytest.raises(StorageConnectionError):
            await adapter.search({'q': 'test', 'query_by': 'content'})
    
    async def test_delete_exception(self, mock_httpx_client):
        """Test delete handling exceptions."""
        mock_httpx_client.delete.side_effect = Exception("Delete failed")
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            result = await adapter.delete('doc-id')
            assert result is False

# ============================================================================
# Integration Tests (real Typesense)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestTypesenseAdapterIntegration:
    """Integration tests for TypesenseAdapter (real Typesense)."""
    
    @pytest_asyncio.fixture
    async def typesense_config(self):
        """Typesense configuration for integration tests."""
        collection_name = f'test_collection_{uuid.uuid4().hex[:8]}'
        config = {
            'url': os.getenv('TYPESENSE_URL', 'http://192.168.107.187:8108'),
            'api_key': os.getenv('TYPESENSE_API_KEY', 'xyz'),
            'collection_name': collection_name,
            'schema': {
                'name': collection_name,  # Schema name must match collection name
                'enable_nested_fields': True,  # Required for object type fields
                'fields': [
                    {'name': 'id', 'type': 'string'},  # Explicit ID field
                    {'name': 'content', 'type': 'string'},
                    {'name': 'session_id', 'type': 'string', 'facet': True, 'optional': True},
                    {'name': 'created_at', 'type': 'int64', 'optional': True},
                    {'name': 'metadata', 'type': 'object', 'optional': True}  # Object type requires enable_nested_fields
                ]
            }
        }
        
        yield config
        
        # Cleanup: Delete test collection after test completes
        try:
            async with httpx.AsyncClient(
                headers={'X-TYPESENSE-API-KEY': config['api_key']},
                timeout=10.0
            ) as client:
                await client.delete(
                    f"{config['url']}/collections/{collection_name}"
                )
        except Exception:
            pass  # Collection might not exist if test failed early
    
    async def test_full_workflow(self, typesense_config):
        """Test complete CRUD workflow."""
        adapter = TypesenseAdapter(typesense_config)
        await adapter.connect()
        
        try:
            # Store document
            document_data = {
                'content': 'Test document for integration',
                'session_id': f'test-session-{uuid.uuid4().hex[:8]}',
                'metadata': {
                    'test_id': str(uuid.uuid4()),
                    'type': 'integration_test'
                }
            }
            
            doc_id = await adapter.store(document_data)
            assert doc_id is not None
            
            # Retrieve document
            retrieved = await adapter.retrieve(doc_id)
            assert retrieved is not None
            assert retrieved['content'] == 'Test document for integration'
            assert 'metadata' in retrieved
            
            # Search documents
            search_query = {
                'q': 'integration',
                'query_by': 'content',
                'limit': 5
            }
            
            search_results = await adapter.search(search_query)
            assert len(search_results) >= 1
            assert any(r['id'] == doc_id for r in search_results)
            
            # Delete document
            deleted = await adapter.delete(doc_id)
            assert deleted is True
            
            # Verify deletion
            retrieved_after_delete = await adapter.retrieve(doc_id)
            assert retrieved_after_delete is None
            
        finally:
            await adapter.disconnect()
    
    async def test_context_manager(self, typesense_config):
        """Test context manager protocol."""
        async with TypesenseAdapter(typesense_config) as adapter:
            assert adapter.is_connected is True
            
            # Simple operation to verify connection
            document_data = {
                'content': 'Context manager test',
                'session_id': f'test-session-{uuid.uuid4().hex[:8]}'
            }
            
            doc_id = await adapter.store(document_data)
            assert doc_id is not None
            
            # Clean up
            await adapter.delete(doc_id)
        
        # Should be disconnected after context
        assert adapter.is_connected is False


# ============================================================================
# Additional Unit Tests for Coverage
# ============================================================================

@pytest.mark.asyncio
class TestTypesenseAdapterBatchOperations:
    """Tests for batch operations."""
    
    @pytest.fixture
    def mock_httpx_client(self):
        """Mock HTTPX client for unit tests."""
        mock = AsyncMock()
        mock.aclose = AsyncMock()
        
        # Mock successful batch response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={'success': True})
        mock_response.raise_for_status = Mock()
        
        mock.post = AsyncMock(return_value=mock_response)
        mock.delete = AsyncMock(return_value=mock_response)
        return mock
    
    async def test_store_batch_documents(self, mock_httpx_client):
        """Test batch storage of documents."""
        # Mock collection exists check
        mock_get_response = AsyncMock()
        mock_get_response.status_code = 200
        mock_get_response.json = AsyncMock(return_value={'name': 'test_collection'})
        mock_get_response.raise_for_status = Mock()
        mock_httpx_client.get = AsyncMock(return_value=mock_get_response)
        
        with patch('httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            batch_data = [
                {
                    'id': f'doc-{i}',
                    'content': f'Test document {i}',
                    'session_id': 'test-session'
                }
                for i in range(5)
            ]
            
            ids = await adapter.store_batch(batch_data)
            assert len(ids) == 5
            await adapter.disconnect()
    
    async def test_store_batch_not_connected(self):
        """Test batch store when not connected."""
        config = {
            'url': 'http://localhost:8108',
            'api_key': 'test_key',
            'collection_name': 'test_collection'
        }
        adapter = TypesenseAdapter(config)
        
        with pytest.raises(StorageConnectionError):
            await adapter.store_batch([{'content': 'test'}])
    
    async def test_retrieve_batch_documents(self, mock_httpx_client):
        """Test batch retrieval of documents."""
        # Mock collection exists check
        mock_get_response = AsyncMock()
        mock_get_response.status_code = 200
        mock_get_response.json = AsyncMock(return_value={
            'name': 'test_collection',
            'hits': [
                {'document': {'id': 'doc1', 'content': 'Content 1'}},
                {'document': {'id': 'doc2', 'content': 'Content 2'}}
            ]
        })
        mock_get_response.raise_for_status = Mock()
        mock_httpx_client.get = AsyncMock(return_value=mock_get_response)
        
        with patch('httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            ids = ['doc1', 'doc2']
            results = await adapter.retrieve_batch(ids)
            assert len(results) == 2
            await adapter.disconnect()
    
    async def test_delete_batch_documents(self, mock_httpx_client):
        """Test batch deletion of documents."""
        # Mock collection exists check
        mock_get_response = AsyncMock()
        mock_get_response.status_code = 200
        mock_get_response.json = AsyncMock(return_value={'name': 'test_collection'})
        mock_get_response.raise_for_status = Mock()
        mock_httpx_client.get = AsyncMock(return_value=mock_get_response)
        
        with patch('httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            ids = ['doc1', 'doc2', 'doc3']
            result = await adapter.delete_batch(ids)
            # Fix: The method returns a dict mapping IDs to deletion status, not a boolean
            assert isinstance(result, dict)
            assert result['doc1'] is True
            assert result['doc2'] is True
            assert result['doc3'] is True
            await adapter.disconnect()


@pytest.mark.asyncio
class TestTypesenseAdapterHealthCheck:
    """Tests for health check functionality."""
    
    @pytest.fixture
    def mock_httpx_client(self):
        """Mock HTTPX client for unit tests."""
        mock = AsyncMock()
        mock.aclose = AsyncMock()
        return mock
    
    async def test_health_check_connected(self, mock_httpx_client):
        """Test health check when connected."""
        # Mock collection info response
        mock_get_response = AsyncMock()
        mock_get_response.status_code = 200
        mock_get_response.json = AsyncMock(return_value={
            'name': 'test_collection',
            'num_documents': 1000,
            'fields': [
                {'name': 'content', 'type': 'string'},
                {'name': 'session_id', 'type': 'string'}
            ]
        })
        mock_get_response.raise_for_status = Mock()
        mock_httpx_client.get = AsyncMock(return_value=mock_get_response)
        
        with patch('httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            health = await adapter.health_check()
            assert health['status'] == 'healthy'
            assert health['connected'] is True
            # Fix: The health check returns 'collection_exists' not 'collection_info'
            assert 'collection_exists' in health
            assert health['document_count'] == 1000
            await adapter.disconnect()
    
    async def test_health_check_not_connected(self):
        """Test health check when not connected."""
        config = {
            'url': 'http://localhost:8108',
            'api_key': 'test_key',
            'collection_name': 'test_collection'
        }
        adapter = TypesenseAdapter(config)
        
        health = await adapter.health_check()
        assert health['status'] == 'unhealthy'  # Fix: Should be 'unhealthy' not 'disconnected'
        assert health['connected'] is False


@pytest.mark.asyncio
class TestTypesenseAdapterSchemaAndSearch:
    """Tests for schema management and complex search scenarios."""
    
    @pytest.fixture
    def mock_httpx_client(self):
        """Mock HTTPX client for unit tests."""
        mock = AsyncMock()
        mock.aclose = AsyncMock()
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={'name': 'test_collection'})
        mock_response.raise_for_status = Mock()
        
        mock.get = AsyncMock(return_value=mock_response)
        mock.post = AsyncMock(return_value=mock_response)
        return mock
    
    async def test_search_with_filter_by(self, mock_httpx_client):
        """Test search with filter_by parameter."""
        # Mock search response
        mock_search_response = AsyncMock()
        mock_search_response.status_code = 200
        mock_search_response.json = AsyncMock(return_value={
            'hits': [
                {'document': {'id': 'doc1', 'content': 'Test content', 'session_id': 'session1'}},
                {'document': {'id': 'doc2', 'content': 'Another test', 'session_id': 'session1'}}
            ]
        })
        mock_search_response.raise_for_status = Mock()
        mock_httpx_client.get = AsyncMock(return_value=mock_search_response)
        
        with patch('httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            query = {
                'q': 'test',
                'query_by': 'content',
                'filter_by': 'session_id:=session1',
                'limit': 10
            }
            
            results = await adapter.search(query)
            assert len(results) == 2
            assert all(r['session_id'] == 'session1' for r in results)
            await adapter.disconnect()
    
    async def test_search_with_facet_by(self, mock_httpx_client):
        """Test search with facet_by parameter."""
        # Mock search response with facets
        mock_search_response = AsyncMock()
        mock_search_response.status_code = 200
        mock_search_response.json = AsyncMock(return_value={
            'hits': [
                {'document': {'id': 'doc1', 'content': 'Test', 'category': 'A'}},
                {'document': {'id': 'doc2', 'content': 'Test', 'category': 'B'}}
            ],
            'facet_counts': [
                {'field_name': 'category', 'counts': [
                    {'value': 'A', 'count': 1},
                    {'value': 'B', 'count': 1}
                ]}
            ]
        })
        mock_search_response.raise_for_status = Mock()
        mock_httpx_client.get = AsyncMock(return_value=mock_search_response)
        
        with patch('httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            query = {
                'q': 'test',
                'query_by': 'content',
                'facet_by': 'category',
                'limit': 10
            }
            
            results = await adapter.search(query)
            assert len(results) == 2
            await adapter.disconnect()
    
    async def test_search_with_sort_by(self, mock_httpx_client):
        """Test search with sort_by parameter."""
        # Mock search response
        mock_search_response = AsyncMock()
        mock_search_response.status_code = 200
        mock_search_response.json = AsyncMock(return_value={
            'hits': [
                {'document': {'id': 'doc1', 'content': 'Test', 'timestamp': 1000}},
                {'document': {'id': 'doc2', 'content': 'Test', 'timestamp': 900}}
            ]
        })
        mock_search_response.raise_for_status = Mock()
        mock_httpx_client.get = AsyncMock(return_value=mock_search_response)
        
        with patch('httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            query = {
                'q': 'test',
                'query_by': 'content',
                'sort_by': 'timestamp:desc',
                'limit': 10
            }
            
            results = await adapter.search(query)
            assert len(results) == 2
            # First result should have higher timestamp
            assert results[0]['timestamp'] >= results[1]['timestamp']
            await adapter.disconnect()
    
    async def test_search_empty_results(self, mock_httpx_client):
        """Test search returning empty results."""
        # Mock empty search response
        mock_search_response = AsyncMock()
        mock_search_response.status_code = 200
        mock_search_response.json = AsyncMock(return_value={'hits': []})
        mock_search_response.raise_for_status = Mock()
        mock_httpx_client.get = AsyncMock(return_value=mock_search_response)
        
        with patch('httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            query = {
                'q': 'nonexistent',
                'query_by': 'content',
                'limit': 10
            }
            
            results = await adapter.search(query)
            assert results == []
            await adapter.disconnect()
    
    async def test_store_with_auto_id(self, mock_httpx_client):
        """Test storing document without explicit ID (auto-generated)."""
        # Mock successful store response
        mock_post_response = AsyncMock()
        mock_post_response.status_code = 201
        mock_post_response.json = AsyncMock(return_value={'id': 'auto-generated-id'})
        mock_post_response.raise_for_status = Mock()
        mock_httpx_client.post = AsyncMock(return_value=mock_post_response)
        
        with patch('httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            data = {
                'content': 'Test document without ID',
                'session_id': 'test-session'
            }
            
            result_id = await adapter.store(data)
            # Should either be auto-generated or returned from API
            assert result_id is not None
            await adapter.disconnect()
    
    async def test_http_error_handling(self, mock_httpx_client):
        """Test handling of HTTP errors."""
        # Mock HTTP error
        mock_error_response = AsyncMock()
        mock_error_response.status_code = 500
        mock_error_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            "Internal Server Error",
            request=Mock(),
            response=Mock(status_code=500)
        ))
        mock_httpx_client.post = AsyncMock(return_value=mock_error_response)
        
        with patch('httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            await adapter.connect()
            
            data = {'content': 'Test'}
            
            with pytest.raises(StorageQueryError):
                await adapter.store(data)
            
            await adapter.disconnect()


# ============================================================================
# Additional Unit Tests for Missing Coverage Lines
# ============================================================================

@pytest.mark.asyncio
class TestTypesenseAdapterExtendedCoverage:
    """Tests to cover remaining missing lines."""
    
    @pytest.fixture
    def mock_httpx_client(self):
        """Mock HTTPX client for unit tests."""
        mock = AsyncMock()
        mock.aclose = AsyncMock()
        mock.get = AsyncMock()
        mock.post = AsyncMock()
        mock.delete = AsyncMock()
        return mock
    
    async def test_store_batch_empty_list(self, mock_httpx_client):
        """Test store_batch with empty list."""
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            result = await adapter.store_batch([])
            assert result == []
    
    async def test_store_batch_http_error(self, mock_httpx_client):
        """Test store_batch handling HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            "Server error", request=Mock(), response=mock_response
        ))
        mock_httpx_client.post.return_value = mock_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            with pytest.raises(StorageQueryError, match="Batch store failed"):
                await adapter.store_batch([{'content': 'test'}])
    
    async def test_store_batch_generic_error(self, mock_httpx_client):
        """Test store_batch handling generic errors."""
        mock_httpx_client.post.side_effect = Exception("Unexpected error")
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            with pytest.raises(StorageQueryError, match="Batch store failed"):
                await adapter.store_batch([{'content': 'test'}])
    
    async def test_delete_batch_empty_list(self, mock_httpx_client):
        """Test delete_batch with empty list."""
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            result = await adapter.delete_batch([])
            assert result == {}
    
    async def test_delete_batch_fallback_on_failure(self, mock_httpx_client):
        """Test delete_batch falls back to individual deletes on batch failure."""
        # First call (batch delete) returns non-200
        batch_response = Mock()
        batch_response.status_code = 400
        
        # Individual delete calls return 200
        individual_response = Mock()
        individual_response.status_code = 200
        
        mock_httpx_client.delete.side_effect = [
            batch_response,
            individual_response,
            individual_response
        ]
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            result = await adapter.delete_batch(['id1', 'id2'])
            assert result == {'id1': True, 'id2': True}
            assert mock_httpx_client.delete.call_count == 3  # 1 batch + 2 individual
    
    async def test_delete_batch_fallback_with_failures(self, mock_httpx_client):
        """Test delete_batch fallback handles individual failures."""
        # Batch delete fails
        batch_response = Mock()
        batch_response.status_code = 400
        
        # Individual deletes: first succeeds, second fails
        success_response = Mock()
        success_response.status_code = 200
        
        mock_httpx_client.delete.side_effect = [
            batch_response,
            success_response,
            Exception("Delete failed")
        ]
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            result = await adapter.delete_batch(['id1', 'id2'])
            assert result == {'id1': True, 'id2': False}
    
    async def test_delete_batch_generic_error(self, mock_httpx_client):
        """Test delete_batch handling generic errors."""
        mock_httpx_client.delete.side_effect = Exception("Unexpected error")
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            with pytest.raises(StorageQueryError, match="Batch delete failed"):
                await adapter.delete_batch(['id1', 'id2'])
    
    async def test_health_check_http_error(self, mock_httpx_client):
        """Test health_check handling HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            "Server error", request=Mock(), response=mock_response
        ))
        mock_httpx_client.get.return_value = mock_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            health = await adapter.health_check()
            assert health['status'] == 'unhealthy'
            assert 'error' in health
    
    async def test_health_check_generic_error(self, mock_httpx_client):
        """Test health_check handling generic errors."""
        mock_httpx_client.get.side_effect = Exception("Unexpected error")
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            health = await adapter.health_check()
            assert health['status'] == 'unhealthy'
            assert 'error' in health
    
    async def test_get_backend_metrics_not_connected(self, mock_httpx_client):
        """Test _get_backend_metrics when not connected."""
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = False
            adapter.client = None
            
            metrics = await adapter._get_backend_metrics()
            assert metrics is None
    
    async def test_get_backend_metrics_http_error(self, mock_httpx_client):
        """Test _get_backend_metrics handling HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            "Server error", request=Mock(), response=mock_response
        ))
        mock_httpx_client.get.return_value = mock_response
        
        with patch('src.storage.typesense_adapter.httpx.AsyncClient', return_value=mock_httpx_client):
            config = {
                'url': 'http://localhost:8108',
                'api_key': 'test_key',
                'collection_name': 'test_collection'
            }
            adapter = TypesenseAdapter(config)
            adapter._connected = True
            adapter.client = mock_httpx_client
            
            metrics = await adapter._get_backend_metrics()
            assert metrics is not None
            assert 'error' in metrics