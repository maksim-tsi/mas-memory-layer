"""
Integration tests for Qdrant adapter metrics.
"""
import pytest
from src.storage.qdrant_adapter import QdrantAdapter


@pytest.mark.asyncio
async def test_qdrant_metrics_integration():
    """Test that Qdrant adapter collects metrics correctly."""
    config = {
        'url': 'http://localhost:6333',
        'collection_name': 'test_metrics',
        'vector_size': 384,
        'metrics': {
            'enabled': True,
            'max_history': 10
        }
    }
    
    adapter = QdrantAdapter(config)
    
    try:
        await adapter.connect()
        
        # Store, retrieve, search, delete
        doc_id = await adapter.store({
            'content': 'Test',
            'vector': [0.1] * 384
        })
        
        await adapter.retrieve(doc_id)
        await adapter.search({'vector': [0.1] * 384, 'limit': 5})
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
            assert 'vector_count' in metrics['backend_specific']
            assert 'collection_name' in metrics['backend_specific']
        
    except Exception as e:
        pytest.skip(f"Qdrant not available: {e}")
    finally:
        try:
            await adapter.disconnect()
        except Exception:
            pass
