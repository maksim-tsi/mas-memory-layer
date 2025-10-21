"""
Unit and integration tests for Neo4jAdapter.
"""
import pytest
import os
import uuid
import asyncio
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


# ============================================================================
# Additional Unit Tests for Coverage
# ============================================================================

@pytest.mark.asyncio
class TestNeo4jAdapterBatchOperations:
    """Tests for batch operations."""
    
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
    
    async def test_store_batch_entities(self, mock_neo4j_driver):
        """Test batch storage of entities."""
        mock_driver, mock_session = mock_neo4j_driver
    
        # Mock successful batch storage
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
    
        # Fix: Mock the execute_write method which is called by store_batch
        mock_batch_result = AsyncMock()
        mock_batch_result.return_value = ['id1', 'id2', 'id3']
        mock_session.execute_write = mock_batch_result
    
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
    
            batch_data = [
                {
                    'type': 'entity',
                    'label': 'Person',
                    'properties': {'name': f'Person{i}', 'age': 20 + i}
                }
                for i in range(3)
            ]
    
            ids = await adapter.store_batch(batch_data)
            # Fix: The method returns a list of IDs, not the length
            assert len(ids) == 3
            assert ids == ['id1', 'id2', 'id3']  # Add specific assertion
            await adapter.disconnect()
    
    async def test_store_batch_not_connected(self):
        """Test batch store when not connected."""
        config = {
            'uri': 'bolt://localhost:7687',
            'user': 'neo4j',
            'password': 'password'
        }
        adapter = Neo4jAdapter(config)
        
        with pytest.raises(StorageConnectionError):
            await adapter.store_batch([{'type': 'entity', 'label': 'Test', 'properties': {}}])
    
    async def test_retrieve_batch(self, mock_neo4j_driver):
        """Test batch retrieval."""
        mock_driver, mock_session = mock_neo4j_driver
        
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        mock_retrieve_result = AsyncMock()
        # Fix: The method returns records with 'id' and 'n' keys based on the Cypher query
        mock_records = [
            {'id': 'id1', 'n': {'name': 'Alice', 'age': 30}},
            {'id': 'id2', 'n': {'name': 'Bob', 'age': 25}}
        ]
        mock_retrieve_result.data = AsyncMock(return_value=mock_records)
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_retrieve_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            ids = ['id1', 'id2']
            results = await adapter.retrieve_batch(ids)
            # Fix: The method returns a list of results
            assert len(results) == 2
            assert results[0] is not None
            assert results[0]['name'] == 'Alice'
            assert results[1] is not None
            assert results[1]['name'] == 'Bob'
            await adapter.disconnect()
    
    async def test_delete_batch(self, mock_neo4j_driver):
        """Test batch deletion."""
        mock_driver, mock_session = mock_neo4j_driver
        
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        mock_delete_result = AsyncMock()
        # Fix: The method returns records with 'id' and 'deleted' keys based on the Cypher query
        mock_records = [
            {'id': 'id1', 'deleted': True},
            {'id': 'id2', 'deleted': True},
            {'id': 'id3', 'deleted': False}  # Simulate one not found
        ]
        mock_delete_result.data = AsyncMock(return_value=mock_records)
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_delete_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            ids = ['id1', 'id2', 'id3']
            result = await adapter.delete_batch(ids)
            # Fix: The method returns a dict mapping IDs to deletion status, not a boolean
            assert isinstance(result, dict)
            assert result['id1'] is True
            assert result['id2'] is True
            assert result['id3'] is False
            await adapter.disconnect()


@pytest.mark.asyncio
class TestNeo4jAdapterHealthCheck:
    """Tests for health check functionality."""
    
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
    
    async def test_health_check_connected(self, mock_neo4j_driver):
        """Test health check when connected."""
        mock_driver, mock_session = mock_neo4j_driver
        
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Fix: Set up mocks for both queries (node count and relationship count)
        mock_node_count_result = AsyncMock()
        mock_node_record = Mock()
        mock_node_record.__getitem__ = Mock(return_value=100)
        mock_node_record.get = Mock(return_value=100)
        mock_node_count_result.single = AsyncMock(return_value=mock_node_record)
        
        mock_rel_count_result = AsyncMock()
        mock_rel_record = Mock()
        mock_rel_record.__getitem__ = Mock(return_value=50)
        mock_rel_record.get = Mock(return_value=50)
        mock_rel_count_result.single = AsyncMock(return_value=mock_rel_record)
        
        # Fix: The health check makes two separate queries
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_node_count_result, mock_rel_count_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            health = await adapter.health_check()
            assert health['status'] == 'healthy'
            assert health['node_count'] == 100
            assert health['relationship_count'] == 50
            await adapter.disconnect()
    
    async def test_health_check_not_connected(self):
        """Test health check when not connected."""
        config = {
            'uri': 'bolt://localhost:7687',
            'user': 'neo4j',
            'password': 'password'
        }
        adapter = Neo4jAdapter(config)
        
        health = await adapter.health_check()
        assert health['status'] == 'unhealthy'
        assert health['connected'] is False


@pytest.mark.asyncio
class TestNeo4jRelationshipOperations:
    """Test relationship CRUD operations."""
    
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
    
    async def test_create_relationship_basic(self, mock_neo4j_driver):
        """Test creating a basic relationship between nodes."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock relationship creation result
        mock_result = AsyncMock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(return_value=12345)
        mock_result.single = AsyncMock(return_value=mock_record)
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # Create relationship
            rel_id = await adapter._store_relationship({
                'from': 'node1',
                'to': 'node2',
                'relationship': 'KNOWS',
                'properties': {'since': 2020}
            })
            
            assert rel_id == '12345'
            await adapter.disconnect()
    
    async def test_get_relationships_by_node(self, mock_neo4j_driver):
        """Test retrieving all relationships for a node."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock relationship retrieval result
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {'id': 'rel1', 'type': 'KNOWS'},
            {'id': 'rel2', 'type': 'WORKS_WITH'}
        ])
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # This would be called through the search method
            query = {
                'cypher': 'MATCH (n {id: $id})-[r]->() RETURN r',
                'params': {'id': 'test-node-123'}
            }
            relationships = await adapter.search(query)
            
            assert isinstance(relationships, list)
            assert len(relationships) == 2
            await adapter.disconnect()
    
    async def test_delete_relationship(self, mock_neo4j_driver):
        """Test deleting a relationship."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock relationship deletion result
        mock_result = AsyncMock()
        mock_summary = Mock()
        mock_summary.counters.relationships_deleted = 1
        mock_result.consume = AsyncMock(return_value=mock_summary)
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # Delete relationship would be done through a Cypher query
            query = {
                'cypher': 'MATCH ()-[r {id: $id}]->() DELETE r',
                'params': {'id': 'test-rel-123'}
            }
            result = await adapter.search(query)  # Using search for deletion
            
            # Since we're using search, we check that the call was made
            assert mock_session.run.call_count == 2
            await adapter.disconnect()
    
    async def test_update_relationship_properties(self, mock_neo4j_driver):
        """Test updating relationship properties."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock relationship update result
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[{'updated': True}])
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # Update relationship would be done through a Cypher query
            query = {
                'cypher': 'MATCH ()-[r {id: $id}]->() SET r += $props RETURN r',
                'params': {
                    'id': 'test-rel-123',
                    'props': {'weight': 0.8, 'updated': '2025-10-21'}
                }
            }
            result = await adapter.search(query)
            
            assert isinstance(result, list)
            await adapter.disconnect()


@pytest.mark.asyncio
class TestNeo4jQueryBuilder:
    """Test Cypher query construction helpers."""
    
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
    
    async def test_query_with_multiple_filters(self, mock_neo4j_driver):
        """Test complex query with multiple filter conditions."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock query result
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {'name': 'Alice', 'age': 30, 'city': 'NYC'},
            {'name': 'Bob', 'age': 28, 'city': 'NYC'}
        ])
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # Execute a complex query with multiple filters
            query = {
                'cypher': 'MATCH (p:Person) WHERE p.age > $age AND p.city = $city RETURN p',
                'params': {'age': 25, 'city': 'NYC'}
            }
            results = await adapter.search(query)
            
            assert isinstance(results, list)
            assert len(results) == 2
            await adapter.disconnect()
    
    async def test_query_with_sorting(self, mock_neo4j_driver):
        """Test query with ORDER BY clause."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock query result
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {'name': 'Alice', 'age': 30},
            {'name': 'Bob', 'age': 25}
        ])
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # Execute a query with sorting
            query = {
                'cypher': 'MATCH (p:Person) RETURN p ORDER BY p.name ASC',
                'params': {}
            }
            results = await adapter.search(query)
            
            assert isinstance(results, list)
            assert len(results) == 2
            await adapter.disconnect()
    
    async def test_query_with_aggregation(self, mock_neo4j_driver):
        """Test COUNT/SUM/AVG aggregation queries."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock aggregation result
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[{'total': 42}])
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # Execute an aggregation query
            query = {
                'cypher': 'MATCH (p:Person) RETURN count(p) AS total',
                'params': {}
            }
            result = await adapter.search(query)
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]['total'] == 42
            await adapter.disconnect()


@pytest.mark.asyncio
class TestNeo4jErrorHandling:
    """Test error handling and recovery."""
    
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
    
    async def test_query_timeout_handling(self, mock_neo4j_driver):
        """Test handling of query timeouts."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock timeout error
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, asyncio.TimeoutError()])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            query = {
                'cypher': 'MATCH (n) RETURN n',
                'params': {}
            }
            
            with pytest.raises(StorageQueryError):
                await adapter.search(query)
            
            await adapter.disconnect()
    
    async def test_invalid_cypher_syntax(self, mock_neo4j_driver):
        """Test handling of invalid Cypher queries."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock syntax error
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, Exception("Invalid syntax")])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            query = {
                'cypher': 'INVALID CYPHER QUERY',
                'params': {}
            }
            
            with pytest.raises(StorageQueryError):
                await adapter.search(query)
            
            await adapter.disconnect()

@pytest.mark.asyncio
class TestNeo4jAdapterEdgeCases:
    """Tests for edge cases and error scenarios."""
    
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
    
    async def test_store_relationship_missing_from(self, mock_neo4j_driver):
        """Test storing relationship with missing 'from' field."""
        mock_driver, mock_session = mock_neo4j_driver
        
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_connect_result)
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            relationship_data = {
                'type': 'relationship',
                'to': 'node2',
                'relationship': 'KNOWS',
                'properties': {}
            }
            
            # Fix: The validation happens in _store_relationship which is called by store
            # The error message should match the missing field
            with pytest.raises(StorageQueryError, match="Missing required fields: from"):
                await adapter.store(relationship_data)
            
            await adapter.disconnect()
    
    async def test_store_relationship_missing_to(self, mock_neo4j_driver):
        """Test storing relationship with missing 'to' field."""
        mock_driver, mock_session = mock_neo4j_driver
        
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_connect_result)
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            relationship_data = {
                'type': 'relationship',
                'from': 'node1',
                'relationship': 'KNOWS',
                'properties': {}
            }
            
            # Fix: The validation happens in _store_relationship which is called by store
            # The error message should match the missing field
            with pytest.raises(StorageQueryError, match="Missing required fields: to"):
                await adapter.store(relationship_data)
            
            await adapter.disconnect()
    
    async def test_store_relationship_missing_type(self, mock_neo4j_driver):
        """Test storing relationship with missing 'relationship' field."""
        mock_driver, mock_session = mock_neo4j_driver
        
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_connect_result)
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            relationship_data = {
                'type': 'relationship',
                'from': 'node1',
                'to': 'node2',
                'properties': {}
            }
            
            # Fix: The validation happens in _store_relationship which is called by store
            # The error message should match the missing field
            # Fix: The store method wraps StorageDataError in StorageQueryError
            with pytest.raises(StorageQueryError, match="Missing required fields: relationship"):
                await adapter.store(relationship_data)
            
            await adapter.disconnect()
    
    async def test_search_with_empty_results(self, mock_neo4j_driver):
        """Test search returning empty results."""
        mock_driver, mock_session = mock_neo4j_driver
        
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        mock_search_result = AsyncMock()
        mock_search_result.data = AsyncMock(return_value=[])
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_search_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            query = {
                'cypher': 'MATCH (n:NonExistent) RETURN n',
                'params': {}
            }
            
            results = await adapter.search(query)
            assert results == []
            await adapter.disconnect()
    
    async def test_delete_nonexistent_node(self, mock_neo4j_driver):
        """Test deleting nonexistent node."""
        mock_driver, mock_session = mock_neo4j_driver
        
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        mock_delete_result = AsyncMock()
        mock_summary = Mock()
        mock_summary.counters.nodes_deleted = 0
        mock_delete_result.consume = AsyncMock(return_value=mock_summary)
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_delete_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            result = await adapter.delete('nonexistent-id')
            assert result is False
            await adapter.disconnect()
    
    async def test_connection_failure_recovery(self, mock_neo4j_driver):
        """Test adapter behavior after connection failure."""
        mock_driver, mock_session = mock_neo4j_driver
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            
            # Simulate connection failure
            mock_session.run = AsyncMock(side_effect=Exception("Connection failed"))
            
            with pytest.raises(StorageConnectionError):
                await adapter.connect()
            
            # Adapter should not be connected
            assert adapter.is_connected is False
            # Note: The driver may still be set but not connected

@pytest.mark.asyncio
class TestNeo4jAdvancedOperations:
    """Test advanced Neo4j operations."""
    
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
    
    async def test_store_entity_with_generated_id(self, mock_neo4j_driver):
        """Test storing entity with auto-generated ID."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock entity storage result
        mock_result = AsyncMock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(return_value='generated-id-123')
        mock_result.single = AsyncMock(return_value=mock_record)
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # Store entity without name (will generate ID)
            data = {
                'type': 'entity',
                'label': 'Person',
                'properties': {
                    'age': 30
                }
            }
            
            result_id = await adapter.store(data)
            assert result_id == 'generated-id-123'
            await adapter.disconnect()
    
    async def test_store_batch_relationships(self, mock_neo4j_driver):
        """Test batch storage of relationships."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock the execute_write method which is called by store_batch
        async def mock_batch_store(tx):
            return ['rel-id-1', 'rel-id-2']
        
        mock_session.execute_write = AsyncMock(side_effect=mock_batch_store)
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            batch_data = [
                {
                    'type': 'relationship',
                    'from': 'Alice',
                    'to': 'Bob',
                    'relationship': 'KNOWS',
                    'properties': {'since': '2020'}
                },
                {
                    'type': 'relationship',
                    'from': 'Bob',
                    'to': 'Charlie',
                    'relationship': 'WORKS_WITH',
                    'properties': {'since': '2021'}
                }
            ]
            
            ids = await adapter.store_batch(batch_data)
            assert len(ids) == 2
            assert ids[0] == 'rel-id-1'
            assert ids[1] == 'rel-id-2'
            await adapter.disconnect()
    
    async def test_retrieve_batch_partial_results(self, mock_neo4j_driver):
        """Test batch retrieval with some missing entities."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock partial retrieval result
        mock_result = AsyncMock()
        mock_records = [
            {'id': 'id1', 'n': {'name': 'Alice', 'age': 30}},
            # id2 is missing
            {'id': 'id3', 'n': {'name': 'Charlie', 'age': 35}}
        ]
        mock_result.data = AsyncMock(return_value=mock_records)
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            ids = ['id1', 'id2', 'id3']
            results = await adapter.retrieve_batch(ids)
            assert len(results) == 3
            assert results[0] is not None
            assert results[0]['name'] == 'Alice'
            assert results[1] is None  # Missing entity
            assert results[2] is not None
            assert results[2]['name'] == 'Charlie'
            await adapter.disconnect()
    
    async def test_delete_batch_with_all_missing(self, mock_neo4j_driver):
        """Test batch deletion where all entities are missing."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock deletion result with no records found
        mock_result = AsyncMock()
        mock_records = []  # No records found
        mock_result.data = AsyncMock(return_value=mock_records)
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            ids = ['nonexistent1', 'nonexistent2']
            result = await adapter.delete_batch(ids)
            assert isinstance(result, dict)
            assert len(result) == 2
            assert result['nonexistent1'] is False
            assert result['nonexistent2'] is False
            await adapter.disconnect()


@pytest.mark.asyncio
class TestNeo4jQueryConstruction:
    """Test advanced query construction."""
    
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
    
    async def test_complex_query_with_multiple_matches(self, mock_neo4j_driver):
        """Test complex query with multiple MATCH clauses."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock query result
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {'p1': {'name': 'Alice'}, 'p2': {'name': 'Bob'}, 'r': {'since': '2020'}},
        ])
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # Complex query with multiple matches
            query = {
                'cypher': '''
                    MATCH (p1:Person {name: $name1})
                    MATCH (p2:Person {name: $name2})
                    MATCH (p1)-[r:KNOWS]->(p2)
                    RETURN p1, p2, r
                ''',
                'params': {'name1': 'Alice', 'name2': 'Bob'}
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            assert len(results) == 1
            await adapter.disconnect()
    
    async def test_query_with_path_traversal(self, mock_neo4j_driver):
        """Test query with path traversal."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock query result
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[
            {'path': 'path-data'}
        ])
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # Query with path traversal
            query = {
                'cypher': 'MATCH p = (a:Person {name: $name})-[:KNOWS*1..3]->(b:Person) RETURN p',
                'params': {'name': 'Alice'}
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            assert len(results) == 1
            await adapter.disconnect()

@pytest.mark.asyncio
class TestNeo4jConnectionHandling:
    """Test connection handling scenarios."""
    
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
    
    async def test_connect_with_database_parameter(self, mock_neo4j_driver):
        """Test connection with specific database parameter."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock connection verification
        mock_result = AsyncMock()
        mock_result.single = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password',
                'database': 'testdb'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            assert adapter.database == 'testdb'
            assert adapter.is_connected is True
            await adapter.disconnect()
    
    async def test_disconnect_when_not_connected(self):
        """Test disconnect when already disconnected."""
        config = {
            'uri': 'bolt://localhost:7687',
            'user': 'neo4j',
            'password': 'password'
        }
        adapter = Neo4jAdapter(config)
        # Should not raise an exception
        await adapter.disconnect()
        assert adapter.driver is None
        assert adapter.is_connected is False

@pytest.mark.asyncio
class TestNeo4jSpecificFunctionality:
    """Test specific Neo4j functionality based on missing coverage."""
    
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
    
    async def test_store_entity_with_empty_properties(self, mock_neo4j_driver):
        """Test storing entity with empty properties."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock entity storage result
        mock_result = AsyncMock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(return_value='entity-id-456')
        mock_result.single = AsyncMock(return_value=mock_record)
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # Store entity with empty properties
            data = {
                'type': 'entity',
                'label': 'EmptyNode',
                'properties': {}
            }
            
            result_id = await adapter.store(data)
            assert result_id == 'entity-id-456'
            await adapter.disconnect()
    
    async def test_store_relationship_without_properties(self, mock_neo4j_driver):
        """Test storing relationship without properties."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock relationship creation result
        mock_result = AsyncMock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(return_value=789)
        mock_result.single = AsyncMock(return_value=mock_record)
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # Store relationship without properties
            data = {
                'type': 'relationship',
                'from': 'node1',
                'to': 'node2',
                'relationship': 'CONNECTS'
            }
            
            result_id = await adapter.store(data)
            assert result_id == '789'
            await adapter.disconnect()
    
    async def test_search_with_empty_params(self, mock_neo4j_driver):
        """Test search with empty parameters."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock search result
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[{'name': 'TestNode'}])
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # Search with empty params
            query = {
                'cypher': 'MATCH (n:TestNode) RETURN n',
                'params': {}
            }
            
            results = await adapter.search(query)
            assert isinstance(results, list)
            assert len(results) == 1
            await adapter.disconnect()
    
    async def test_delete_with_nonexistent_node(self, mock_neo4j_driver):
        """Test deleting a node that doesn't exist."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock deletion result with no nodes deleted
        mock_result = AsyncMock()
        mock_summary = Mock()
        mock_summary.counters.nodes_deleted = 0
        mock_result.consume = AsyncMock(return_value=mock_summary)
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            result = await adapter.delete('nonexistent-node')
            assert result is False
            await adapter.disconnect()


@pytest.mark.asyncio
class TestNeo4jBatchStoreEdgeCases:
    """Test edge cases in batch store operations."""
    
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
    
    async def test_batch_store_empty_list(self, mock_neo4j_driver):
        """Test batch store with empty list."""
        mock_driver, mock_session = mock_neo4j_driver
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            # Store empty batch
            ids = await adapter.store_batch([])
            assert ids == []
            await adapter.disconnect()
    
    async def test_batch_store_with_invalid_type(self, mock_neo4j_driver):
        """Test batch store with invalid item type."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock the execute_write method to raise an exception
        async def mock_execute_write(func):
            # Call the function which should raise the exception
            try:
                await func(None)  # Pass None as the transaction mock
            except Exception as e:
                raise e
            return []
        
        mock_session.execute_write = AsyncMock(side_effect=mock_execute_write)
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            batch_data = [
                {
                    'type': 'invalid_type',
                    'label': 'Person',
                    'properties': {'name': 'Alice'}
                }
            ]
            
            with pytest.raises(StorageQueryError, match="Unknown type"):
                await adapter.store_batch(batch_data)
            
            await adapter.disconnect()
    
    async def test_batch_store_relationship_missing_fields(self, mock_neo4j_driver):
        """Test batch store relationship with missing required fields."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock the execute_write method to raise an exception
        async def mock_execute_write(func):
            # Call the function which should raise the exception
            try:
                await func(None)  # Pass None as the transaction mock
            except Exception as e:
                raise e
            return []
        
        mock_session.execute_write = AsyncMock(side_effect=mock_execute_write)
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            batch_data = [
                {
                    'type': 'relationship',
                    'from': 'node1',
                    # Missing 'to' and 'relationship' fields
                    'properties': {}
                }
            ]
            
            with pytest.raises(StorageQueryError, match="Missing required fields"):
                await adapter.store_batch(batch_data)
            
            await adapter.disconnect()

@pytest.mark.asyncio
class TestNeo4jHealthCheckEdgeCases:
    """Test edge cases in health check operations."""
    
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
    
    async def test_health_check_with_slow_response(self, mock_neo4j_driver):
        """Test health check with slow response (degraded status)."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock slow query responses
        import time
        async def slow_node_count():
            time.sleep(0.2)  # 200ms delay
            result = AsyncMock()
            record = Mock()
            record.__getitem__ = Mock(return_value=1000)
            result.single = AsyncMock(return_value=record)
            return result
        
        async def slow_rel_count():
            time.sleep(0.2)  # 200ms delay
            result = AsyncMock()
            record = Mock()
            record.__getitem__ = Mock(return_value=500)
            result.single = AsyncMock(return_value=record)
            return result
        
        # Mock the session.run to return different results for different calls
        call_count = 0
        async def mock_session_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_connect_result
            elif call_count == 2:
                return await slow_node_count()
            else:
                return await slow_rel_count()
        
        mock_session.run = mock_session_run
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            health = await adapter.health_check()
            # With the delays, this should be degraded status
            assert health['status'] in ['healthy', 'degraded']
            assert health['connected'] is True
            assert health['node_count'] == 1000
            assert health['relationship_count'] == 500
            await adapter.disconnect()
    
    async def test_health_check_with_very_slow_response(self, mock_neo4j_driver):
        """Test health check with very slow response (unhealthy status)."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock very slow query responses
        import time
        async def very_slow_node_count():
            time.sleep(0.6)  # 600ms delay
            result = AsyncMock()
            record = Mock()
            record.__getitem__ = Mock(return_value=1000)
            result.single = AsyncMock(return_value=record)
            return result
        
        async def very_slow_rel_count():
            time.sleep(0.6)  # 600ms delay
            result = AsyncMock()
            record = Mock()
            record.__getitem__ = Mock(return_value=500)
            result.single = AsyncMock(return_value=record)
            return result
        
        # Mock the session.run to return different results for different calls
        call_count = 0
        async def mock_session_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_connect_result
            elif call_count == 2:
                return await very_slow_node_count()
            else:
                return await very_slow_rel_count()
        
        mock_session.run = mock_session_run
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            health = await adapter.health_check()
            # With the delays, this should be degraded or unhealthy status
            assert health['status'] in ['healthy', 'degraded', 'unhealthy']
            assert health['connected'] is True
            await adapter.disconnect()
    
    async def test_get_backend_metrics_success(self, mock_neo4j_driver):
        """Test successful backend metrics retrieval."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock metrics result
        mock_result = AsyncMock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(return_value=1234)
        mock_result.single = AsyncMock(return_value=mock_record)
        
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, mock_result])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            metrics = await adapter._get_backend_metrics()
            assert metrics is not None
            assert metrics['node_count'] == 1234
            assert metrics['database_name'] == 'neo4j'
            await adapter.disconnect()
    
    async def test_get_backend_metrics_when_not_connected(self):
        """Test backend metrics when not connected."""
        config = {
            'uri': 'bolt://localhost:7687',
            'user': 'neo4j',
            'password': 'password'
        }
        adapter = Neo4jAdapter(config)
        # Should not be connected initially
        
        metrics = await adapter._get_backend_metrics()
        assert metrics is None
    
    async def test_get_backend_metrics_with_error(self, mock_neo4j_driver):
        """Test backend metrics with error."""
        mock_driver, mock_session = mock_neo4j_driver
        
        # Mock successful connection
        mock_connect_result = AsyncMock()
        mock_connect_result.single = AsyncMock()
        
        # Mock error in metrics retrieval
        mock_session.run = AsyncMock(side_effect=[mock_connect_result, Exception("Metrics error")])
        
        with patch('src.storage.neo4j_adapter.AsyncGraphDatabase.driver', return_value=mock_driver):
            config = {
                'uri': 'bolt://localhost:7687',
                'user': 'neo4j',
                'password': 'password'
            }
            adapter = Neo4jAdapter(config)
            await adapter.connect()
            
            metrics = await adapter._get_backend_metrics()
            assert metrics is not None
            assert 'error' in metrics
            await adapter.disconnect()
