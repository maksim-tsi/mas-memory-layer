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