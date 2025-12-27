"""
Benchmark metrics collection overhead.

Verifies that metrics collection adds reasonable overhead to operations.
"""
import pytest
import time
from src.storage.redis_adapter import RedisAdapter


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_metrics_overhead():
    """
    Verify metrics overhead is reasonable.
    
    This test runs operations with and without metrics enabled
    and compares the execution time.
    """
    iterations = 1000
    
    # Setup: Redis without metrics
    config_no_metrics = {
        'url': 'redis://localhost:6379/0',
        'window_size': 10,
        'metrics': {'enabled': False}
    }
    
    adapter_no_metrics = RedisAdapter(config_no_metrics)
    await adapter_no_metrics.connect()
    
    # Benchmark without metrics
    start = time.perf_counter()
    for i in range(iterations):
        await adapter_no_metrics.store({
            'session_id': 'bench-session',
            'turn_id': i,
            'content': f'Benchmark message {i}'
        })
    time_without_metrics = time.perf_counter() - start
    await adapter_no_metrics.disconnect()
    
    # Setup: Redis with metrics
    config_with_metrics = {
        'url': 'redis://localhost:6379/0',
        'window_size': 10,
        'metrics': {
            'enabled': True,
            'max_history': 1000,
            'track_errors': True,
            'track_data_volume': True
        }
    }
    
    adapter_with_metrics = RedisAdapter(config_with_metrics)
    await adapter_with_metrics.connect()
    
    # Benchmark with metrics
    start = time.perf_counter()
    for i in range(iterations):
        await adapter_with_metrics.store({
            'session_id': 'bench-session-metrics',
            'turn_id': i,
            'content': f'Benchmark message {i}'
        })
    time_with_metrics = time.perf_counter() - start
    await adapter_with_metrics.disconnect()
    
    # Calculate overhead
    overhead_pct = ((time_with_metrics - time_without_metrics) / time_without_metrics) * 100
    
    print("\n=== Metrics Overhead Benchmark ===")
    print(f"Operations: {iterations}")
    print(f"Time without metrics: {time_without_metrics:.3f}s")
    print(f"Time with metrics: {time_with_metrics:.3f}s")
    print(f"Overhead: {overhead_pct:.2f}%")
    
    # Verify overhead is reasonable (less than 20%)
    assert overhead_pct < 20.0, f"Metrics overhead {overhead_pct:.2f}% exceeds reasonable limit"
    
    print(f"✓ Overhead test PASSED ({overhead_pct:.2f}% < 20%)")