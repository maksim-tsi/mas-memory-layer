"""
Unit and integration tests for Neo4jAdapter.
"""
import pytest
import os
import uuid
from unittest.mock import AsyncMock, Mock, patch
from src.storage.neo4j_adapter import Neo4jAdapter
from src.storage.base import StorageConnectionError, StorageDataError, StorageQueryError

# ============================================================================
# Unit Tests (with mocks)
# ============================================================================

@pytest.mark.asyncio
class TestNeo4jAdapterUnit:
    """Unit tests for Neo4jAdapter (mocked dependencies)."""
    
    @pytest.fixture
    def mock_neo4j_driver(self):
        """Mock Neo4j driver for unit tests."""
        mock_driver = Mock()
        mock_session = AsyncMock()
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session.return_value = mock_session_context
        mock_driver.close = AsyncMock()
        return mock_driver, mock_session
    
    async def test_init(self):
        """Test adapter initialization."""
        config = {
            'uri': 'bolt://localhost:7687',
            'user': 'neo4j',
            'password': 'password'
        }
        adapter = Neo4jAdapter(config)
        assert adapter.uri == 'bolt://localhost:7687'
        assert adapter.user == 'neo4j'
        assert adapter.password == 'password'
        assert adapter.driver is None
    
    async def test_init_missing_credentials(self):
        """Test adapter initialization with missing credentials."""
        config = {'uri': 'bolt://localhost:7687'}
        with pytest.raises(StorageDataError):
            Neo4jAdapter(config)
    
    async def test_connect_success(self, mock_neo4j_driver):
        """Test successful connection."""
        mock_driver, mock_session = mock_neo4j_driver
        mock_session.run = AsyncMock()
        mock_result = AsyncMock()
        mock_session.run.return_value = mock_result
        mock_result.single = AsyncMock()
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            assert adapter.driver is not None
            assert adapter.is_connected is True
    
    async def test_disconnect(self, mock_neo4j_driver):
        """Test disconnection."""
        mock_driver, mock_session = mock_neo4j_driver
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            await adapter.disconnect()
            mock_driver.close.assert_called_once()
            assert adapter.driver is None
            assert adapter.is_connected is False
    
    async def test_store_entity_success(self, mock_neo4j_driver):
        """Test successful storage of entity."""
        mock_driver, mock_session = mock_neo4j_driver
        mock_result = AsyncMock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(return_value='entity-id')
        mock_result.single = AsyncMock(return_value=mock_record)
        
        # Create a separate mock for the connect verification call
        mock_connect_result = AsyncMock()
        mock_connect_record = Mock()
        mock_connect_result.single = AsyncMock(return_value=mock_connect_record)
        
        # Set up the session mock to return different results for different calls
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            data = {
                'type': 'entity',
                'label': 'Person',
                'properties': {
                    'name': 'Alice',
                    'age': 30
                }
            }
            
            result_id = await adapter.store(data)
            assert result_id == 'entity-id'
            # Check that run was called for the store operation (second call)
            assert mock_session.run.call_count == 2
    
    async def test_store_relationship_success(self, mock_neo4j_driver):
        """Test successful storage of relationship."""
        mock_driver, mock_session = mock_neo4j_driver
        mock_result = AsyncMock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(return_value=123)
        mock_result.single = AsyncMock(return_value=mock_record)
        
        # Create a separate mock for the connect verification call
        mock_connect_result = AsyncMock()
        mock_connect_record = Mock()
        mock_connect_result.single = AsyncMock(return_value=mock_connect_record)
        
        # Set up the session mock to return different results for different calls
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            data = {
                'type': 'relationship',
                'from': 'Alice',
                'to': 'Bob',
                'relationship': 'KNOWS',
                'properties': {
                    'since': '2020'
                }
            }
            
            result_id = await adapter.store(data)
            assert result_id == '123'
            # Check that run was called for the store operation (second call)
            assert mock_session.run.call_count == 2
    
    async def test_store_invalid_type(self, mock_neo4j_driver):
        """Test storage with invalid type."""
        mock_driver, mock_session = mock_neo4j_driver
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            data = {
                'type': 'invalid',
                'label': 'Person'
            }
            
            with pytest.raises(StorageQueryError):
                await adapter.store(data)
    
    async def test_store_missing_required_fields(self, mock_neo4j_driver):
        """Test storage with missing required fields."""
        mock_driver, mock_session = mock_neo4j_driver
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # Missing type
            data = {
                'label': 'Person'
            }
            
            with pytest.raises(StorageDataError):
                await adapter.store(data)
    
    async def test_store_not_connected(self):
        """Test storage when not connected."""
        config = {
            'uri': 'bolt://localhost:7687',
            'user': 'neo4j',
            'password': 'password'
        }
        adapter = Neo4jAdapter(config)
        
        data = {
            'type': 'entity',
            'label': 'Person',
            'properties': {'name': 'Alice'}
        }
        
        with pytest.raises(StorageConnectionError):
            await adapter.store(data)
    
    async def test_retrieve_success(self, mock_neo4j_driver):
        """Test successful retrieval of entity."""
        mock_driver, mock_session = mock_neo4j_driver
        mock_result = AsyncMock()
        mock_record = Mock()
        mock_node = {
            'name': 'Alice',
            'age': 30
        }
        mock_record.__getitem__ = Mock(side_effect=lambda key: mock_node if key == 'n' else None)
        mock_result.single = AsyncMock(return_value=mock_record)
        
        # Create a separate mock for the connect verification call
        mock_connect_result = AsyncMock()
        mock_connect_record = Mock()
        mock_connect_result.single = AsyncMock(return_value=mock_connect_record)
        
        # Set up the session mock to return different results for different calls
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            result = await adapter.retrieve('entity-id')
            assert result is not None
            assert 'name' in result
    
    async def test_retrieve_not_found(self, mock_neo4j_driver):
        """Test retrieval when entity is not found."""
        mock_driver, mock_session = mock_neo4j_driver
        mock_result = AsyncMock()
        mock_session.run.return_value = mock_result
        mock_result.single = AsyncMock(return_value=None)
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            result = await adapter.retrieve('non-existent-id')
            assert result is None
    
    async def test_search_success(self, mock_neo4j_driver):
        """Test successful search operation."""
        mock_driver, mock_session = mock_neo4j_driver
        mock_result = AsyncMock()
        mock_session.run.return_value = mock_result
        mock_result.data = AsyncMock(return_value=[{'name': 'Alice'}, {'name': 'Bob'}])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            query = {
                'cypher': 'MATCH (p:Person) RETURN p.name',
                'params': {}
            }
            
            results = await adapter.search(query)
            assert len(results) == 2
            assert results[0]['name'] == 'Alice'
    
    async def test_search_missing_cypher(self, mock_neo4j_driver):
        """Test search with missing cypher query."""
        mock_driver, mock_session = mock_neo4j_driver
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            query = {
                'params': {}
            }
            
            with pytest.raises(StorageDataError):
                await adapter.search(query)
    
    async def test_delete_success(self, mock_neo4j_driver):
        """Test successful deletion."""
        mock_driver, mock_session = mock_neo4j_driver
        mock_result = AsyncMock()
        mock_summary = Mock()
        mock_summary.counters.nodes_deleted = 1
        mock_result.consume = AsyncMock(return_value=mock_summary)
        
        # Create a separate mock for the connect verification call
        mock_connect_result = AsyncMock()
        mock_connect_record = Mock()
        mock_connect_result.single = AsyncMock(return_value=mock_connect_record)
        
        # Set up the session mock to return different results for different calls
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            result = await adapter.delete('entity-id')
            assert result is True
            # Check that run was called for the delete operation (second call)
            assert mock_session.run.call_count == 2
    
    async def test_delete_not_connected(self):
        """Test deletion when not connected."""
        config = {
            'uri': 'bolt://localhost:7687',
            'user': 'neo4j',
            'password': 'password'
        }
        adapter = Neo4jAdapter(config)
        
        with pytest.raises(StorageConnectionError):
            await adapter.delete('entity-id')

# ============================================================================
# Integration Tests (real Neo4j)
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestNeo4jAdapterIntegration:
    """Integration tests for Neo4jAdapter (real Neo4j)."""
    
    @pytest.fixture
    def neo4j_config(self):
        """Neo4j configuration for integration tests."""
        return {
            'uri': os.getenv('NEO4J_BOLT', 'bolt://localhost:7687'),
            'user': os.getenv('NEO4J_USER', 'neo4j'),
            'password': os.getenv('NEO4J_PASSWORD', 'password'),
            'database': 'neo4j'
        }
    
    async def test_full_workflow(self, neo4j_config):
        """Test complete CRUD workflow."""
        adapter = Neo4jAdapter(neo4j_config)
        await adapter.connect()
        
        try:
            # Store entities
            person1_data = {
                'type': 'entity',
                'label': 'Person',
                'properties': {
                    'name': f'Alice_{uuid.uuid4().hex[:8]}',
                    'age': 30,
                    'test_id': str(uuid.uuid4())
                }
            }
            
            person2_data = {
                'type': 'entity',
                'label': 'Person',
                'properties': {
                    'name': f'Bob_{uuid.uuid4().hex[:8]}',
                    'age': 25,
                    'test_id': str(uuid.uuid4())
                }
            }
            
            person1_id = await adapter.store(person1_data)
            person2_id = await adapter.store(person2_data)
            
            assert person1_id is not None
            assert person2_id is not None
            
            # Store relationship
            relationship_data = {
                'type': 'relationship',
                'from': person1_data['properties']['name'],
                'to': person2_data['properties']['name'],
                'relationship': 'KNOWS',
                'properties': {
                    'since': '2020',
                    'test_id': str(uuid.uuid4())
                }
            }
            
            relationship_id = await adapter.store(relationship_data)
            assert relationship_id is not None
            
            # Search relationships
            search_query = {
                'cypher': 'MATCH (p1:Person)-[r:KNOWS]->(p2:Person) WHERE r.test_id = $test_id RETURN p1, r, p2',
                'params': {
                    'test_id': relationship_data['properties']['test_id']
                }
            }
            
            search_results = await adapter.search(search_query)
            assert len(search_results) >= 1
            
            # Delete entities (will also delete relationships)
            deleted1 = await adapter.delete(person1_id)
            assert deleted1 is True
            
        finally:
            await adapter.disconnect()
    
    async def test_context_manager(self, neo4j_config):
        """Test context manager protocol."""
        async with Neo4jAdapter(neo4j_config) as adapter:
            assert adapter.is_connected is True
            
            # Simple operation to verify connection
            test_data = {
                'type': 'entity',
                'label': 'TestNode',
                'properties': {
                    'name': f'Test_{uuid.uuid4().hex[:8]}',
                    'test': True
                }
            }
            
            node_id = await adapter.store(test_data)
            assert node_id is not None
            
            # Clean up
            await adapter.delete(node_id)
        
        # Should be disconnected after context
        assert adapter.is_connected is False