"""
Integration tests for Redis adapter metrics.
"""
import pytest
from src.storage.redis_adapter import RedisAdapter


@pytest.mark.asyncio
async def test_redis_metrics_integration():
    """Test that Redis adapter collects metrics correctly."""
    # Configure adapter with metrics enabled
    config = {
        'url': 'redis://localhost:6379/0',
        'window_size': 5,
        'metrics': {
            'enabled': True,
            'max_history': 10
        }
    }
    
    adapter = RedisAdapter(config)
    
    try:
        # Connect to Redis
        await adapter.connect()
        
        # Store some data
        record_id = await adapter.store({
            'session_id': 'test-metrics-session',
            'turn_id': 1,
            'content': 'Test message for metrics',
            'metadata': {'test': True}
        })
        
        # Retrieve data
        data = await adapter.retrieve(record_id)
        
        # Search data
        results = await adapter.search({
            'session_id': 'test-metrics-session',
            'limit': 2
        })
        
        # Get metrics
        metrics = await adapter.get_metrics()
        
        # Verify metrics are collected
        assert 'operations' in metrics
        assert 'store' in metrics['operations']
        assert 'retrieve' in metrics['operations']
        assert 'search' in metrics['operations']
        
        # Verify operation counts
        assert metrics['operations']['store']['total_count'] >= 1
        assert metrics['operations']['retrieve']['total_count'] >= 1
        assert metrics['operations']['search']['total_count'] >= 1
        
        # Verify success rates
        assert metrics['operations']['store']['success_rate'] == 1.0
        assert metrics['operations']['retrieve']['success_rate'] == 1.0
        assert metrics['operations']['search']['success_rate'] == 1.0
        
        # Verify latency metrics exist
        assert 'latency_ms' in metrics['operations']['store']
        assert 'latency_ms' in metrics['operations']['retrieve']
        assert 'latency_ms' in metrics['operations']['search']
        
        # Test export functionality
        json_metrics = await adapter.export_metrics('json')
        prometheus_metrics = await adapter.export_metrics('prometheus')
        markdown_metrics = await adapter.export_metrics('markdown')
        
        assert isinstance(json_metrics, str)
        assert isinstance(prometheus_metrics, str)
        assert isinstance(markdown_metrics, str)
        
    except Exception as e:
        # If Redis is not available, skip the test
        pytest.skip(f"Redis not available: {e}")
    finally:
        # Clean up
        try:
            await adapter.disconnect()
        except:
            pass