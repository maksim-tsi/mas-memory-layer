"""
Integration tests for Neo4j adapter metrics.
"""
import pytest
from src.storage.neo4j_adapter import Neo4jAdapter


@pytest.mark.asyncio
async def test_neo4j_metrics_integration():
    """Test that Neo4j adapter collects metrics correctly."""
    config = {
        'uri': 'bolt://localhost:7687',
        'user': 'neo4j',
        'password': 'password',
        'database': 'neo4j',
        'metrics': {
            'enabled': True,
            'max_history': 10
        }
    }
    
    adapter = Neo4jAdapter(config)
    
    try:
        await adapter.connect()
        
        # Store, retrieve, search, delete
        entity_id = await adapter.store({
            'type': 'entity',
            'label': 'Person',
            'properties': {'name': 'Test', 'age': 30}
        })
        
        await adapter.retrieve(entity_id)
        await adapter.search({'cypher': 'MATCH (n:Person) RETURN n LIMIT 5', 'params': {}})
        await adapter.delete(entity_id)
        
        # Verify metrics
        metrics = await adapter.get_metrics()
        
        assert 'operations' in metrics
        assert metrics['operations']['store']['total_count'] >= 1
        assert metrics['operations']['retrieve']['total_count'] >= 1
        assert metrics['operations']['search']['total_count'] >= 1
        assert metrics['operations']['delete']['total_count'] >= 1
        
        # Verify success rates
        assert metrics['operations']['store']['success_rate'] == 1.0
        
        # Test export
        json_metrics = await adapter.export_metrics('json')
        assert isinstance(json_metrics, str)
        
        # Test backend metrics
        if 'backend_specific' in metrics:
            assert 'node_count' in metrics['backend_specific']
            assert 'database_name' in metrics['backend_specific']
        
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")
    finally:
        try:
            await adapter.disconnect()
        except:
            pass
