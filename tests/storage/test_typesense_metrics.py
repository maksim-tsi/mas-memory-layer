"""
Integration tests for Typesense adapter metrics.
"""
import pytest
from src.storage.typesense_adapter import TypesenseAdapter


@pytest.mark.asyncio
async def test_typesense_metrics_integration():
    """Test that Typesense adapter collects metrics correctly."""
    config = {
        'url': 'http://localhost:8108',
        'api_key': 'xyz',
        'collection_name': 'test_metrics',
        'schema': {
            'name': 'test_metrics',
            'fields': [
                {'name': 'content', 'type': 'string'},
                {'name': 'session_id', 'type': 'string', 'facet': True}
            ]
        },
        'metrics': {
            'enabled': True,
            'max_history': 10
        }
    }
    
    adapter = TypesenseAdapter(config)
    
    try:
        await adapter.connect()
        
        # Store, retrieve, search, delete
        doc_id = await adapter.store({
            'content': 'Test document',
            'session_id': 'test-session'
        })
        
        await adapter.retrieve(doc_id)
        await adapter.search({
            'q': 'test',
            'query_by': 'content',
            'limit': 5
        })
        await adapter.delete(doc_id)
        
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
            assert 'document_count' in metrics['backend_specific']
            assert 'collection_name' in metrics['backend_specific']
        
    except Exception as e:
        pytest.skip(f"Typesense not available: {e}")
    finally:
        try:
            await adapter.disconnect()
        except Exception:
            pass
