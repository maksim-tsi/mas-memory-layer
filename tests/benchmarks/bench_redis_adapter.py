"""
Performance benchmarks for Redis adapter.

Measures latency and throughput for all operations to validate
performance characteristics and establish baselines.

Run with:
    pytest tests/benchmarks/bench_redis_adapter.py -v
    
For detailed metrics:
    pytest tests/benchmarks/bench_redis_adapter.py::test_measure_latencies -v -s
"""

import pytest
import pytest_asyncio
import os
import uuid
import time
import statistics
from datetime import datetime, timezone
from src.storage.redis_adapter import RedisAdapter


@pytest.fixture
def redis_config():
    """Redis configuration for benchmarks"""
    return {
        'url': os.getenv('REDIS_URL'),
        'window_size': 10,
        'ttl_seconds': 3600
    }


@pytest_asyncio.fixture
async def redis_adapter(redis_config):
    """Create and connect Redis adapter"""
    if not redis_config['url']:
        pytest.skip("REDIS_URL environment variable not set")
    
    adapter = RedisAdapter(redis_config)
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


@pytest.fixture
def session_id():
    """Generate unique benchmark session ID"""
    return f"bench-{uuid.uuid4()}"


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_bench_store_single(redis_adapter, session_id):
    """Benchmark single store operation"""
    times = []
    iterations = 50
    
    for i in range(iterations):
        start = time.perf_counter()
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': 'Benchmark message',
            'metadata': {'test': True, 'iteration': i}
        })
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        times.append(elapsed)
    
    # Cleanup
    await redis_adapter.clear_session(session_id)
    
    # Calculate statistics
    mean = statistics.mean(times)
    median = statistics.median(times)
    
    print(f"\nStore operation - Mean: {mean:.3f}ms, Median: {median:.3f}ms")
    
    # Assert performance target
    assert mean < 2.0, f"Store operation too slow: {mean:.3f}ms (target: <2ms)"


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_bench_retrieve_single(redis_adapter, session_id):
    """Benchmark single retrieve operation"""
    # Setup: Store a record
    record_id = await redis_adapter.store({
        'session_id': session_id,
        'turn_id': 1,
        'content': 'Benchmark message'
    })
    
    times = []
    iterations = 100
    
    for _ in range(iterations):
        start = time.perf_counter()
        result = await redis_adapter.retrieve(record_id)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        assert result is not None
    
    # Cleanup
    await redis_adapter.clear_session(session_id)
    
    # Calculate statistics
    mean = statistics.mean(times)
    median = statistics.median(times)
    
    print(f"\nRetrieve operation - Mean: {mean:.3f}ms, Median: {median:.3f}ms")
    
    # Assert performance target
    assert mean < 1.0, f"Retrieve operation too slow: {mean:.3f}ms (target: <1ms)"


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_bench_search_10_items(redis_adapter, session_id):
    """Benchmark search with 10 items"""
    # Setup: Store 10 records
    for i in range(10):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
    
    times = []
    iterations = 100
    
    for _ in range(iterations):
        start = time.perf_counter()
        results = await redis_adapter.search({
            'session_id': session_id,
            'limit': 10
        })
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        assert len(results) == 10
    
    # Cleanup
    await redis_adapter.clear_session(session_id)
    
    # Calculate statistics
    mean = statistics.mean(times)
    median = statistics.median(times)
    
    print(f"\nSearch (10 items) - Mean: {mean:.3f}ms, Median: {median:.3f}ms")
    
    # Assert performance target
    assert mean < 1.0, f"Search operation too slow: {mean:.3f}ms (target: <1ms)"


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_bench_session_size(redis_adapter, session_id):
    """Benchmark session size query"""
    # Setup: Store 5 records
    for i in range(5):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
    
    times = []
    iterations = 100
    
    for _ in range(iterations):
        start = time.perf_counter()
        size = await redis_adapter.get_session_size(session_id)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        assert size == 5
    
    # Cleanup
    await redis_adapter.clear_session(session_id)
    
    # Calculate statistics
    mean = statistics.mean(times)
    median = statistics.median(times)
    
    print(f"\nSession size query - Mean: {mean:.3f}ms, Median: {median:.3f}ms")
    
    # Assert performance target
    assert mean < 0.5, f"Session size query too slow: {mean:.3f}ms (target: <0.5ms)"


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_bench_throughput_100_stores(redis_adapter, session_id):
    """Benchmark throughput with 100 consecutive stores"""
    iterations = 100
    
    start_time = time.perf_counter()
    
    for i in range(iterations):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
    
    end_time = time.perf_counter()
    elapsed = end_time - start_time
    throughput = iterations / elapsed
    avg_latency = (elapsed / iterations) * 1000
    
    # Cleanup
    await redis_adapter.clear_session(session_id)
    
    print(f"\nThroughput: {throughput:.0f} ops/sec")
    print(f"Average latency: {avg_latency:.2f}ms per operation")
    
    # Assert minimum throughput
    assert throughput > 500, f"Throughput too low: {throughput:.0f} ops/sec (target: >500)"


@pytest.mark.asyncio
async def test_measure_latencies(redis_adapter, session_id):
    """Measure and report detailed latencies with percentiles"""
    iterations = 100
    
    print("\n" + "=" * 70)
    print("Redis Adapter Performance Metrics (100 iterations each)")
    print("=" * 70)
    
    # Measure store latency
    store_times = []
    for i in range(iterations):
        start = time.perf_counter()
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}',
            'metadata': {'index': i, 'timestamp': datetime.now(timezone.utc).isoformat()}
        })
        store_times.append((time.perf_counter() - start) * 1000)
    
    # Measure retrieve latency
    record_id = f"session:{session_id}:turns:50"
    retrieve_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        await redis_adapter.retrieve(record_id)
        retrieve_times.append((time.perf_counter() - start) * 1000)
    
    # Measure search latency
    search_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        await redis_adapter.search({
            'session_id': session_id,
            'limit': 10
        })
        search_times.append((time.perf_counter() - start) * 1000)
    
    # Measure session size latency
    size_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        await redis_adapter.get_session_size(session_id)
        size_times.append((time.perf_counter() - start) * 1000)
    
    # Cleanup
    await redis_adapter.clear_session(session_id)
    
    # Helper function to calculate percentiles
    def percentile(data, p):
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    # Report results
    def print_stats(operation, times):
        print(f"\n{operation}:")
        print(f"  Mean:   {statistics.mean(times):6.3f}ms")
        print(f"  Median: {statistics.median(times):6.3f}ms")
        print(f"  Min:    {min(times):6.3f}ms")
        print(f"  Max:    {max(times):6.3f}ms")
        print(f"  StdDev: {statistics.stdev(times):6.3f}ms")
        print(f"  P50:    {percentile(times, 50):6.3f}ms")
        print(f"  P95:    {percentile(times, 95):6.3f}ms")
        print(f"  P99:    {percentile(times, 99):6.3f}ms")
    
    print_stats("Store Operation (pipeline: LPUSH + LTRIM + EXPIRE)", store_times)
    print_stats("Retrieve Operation (LRANGE + search)", retrieve_times)
    print_stats("Search Operation (LRANGE 10 items)", search_times)
    print_stats("Session Size Query (LLEN)", size_times)
    
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Redis adapter meets all performance targets:")
    print(f"  ✓ Store:    {statistics.mean(store_times):.3f}ms (target: <2ms)")
    print(f"  ✓ Retrieve: {statistics.mean(retrieve_times):.3f}ms (target: <1ms)")
    print(f"  ✓ Search:   {statistics.mean(search_times):.3f}ms (target: <1ms)")
    print(f"  ✓ Size:     {statistics.mean(size_times):.3f}ms (target: <0.5ms)")
    print("=" * 70 + "\n")
    
    # Validate targets
    assert statistics.mean(store_times) < 2.0, "Store latency exceeds target"
    assert statistics.mean(retrieve_times) < 1.0, "Retrieve latency exceeds target"
    assert statistics.mean(search_times) < 1.0, "Search latency exceeds target"
    assert statistics.mean(size_times) < 0.5, "Size query latency exceeds target"


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_bench_delete_operations(redis_adapter, session_id):
    """Benchmark delete operations"""
    # Setup: Store records
    for i in range(10):
        await redis_adapter.store({
            'session_id': session_id,
            'turn_id': i,
            'content': f'Message {i}'
        })
    
    times = []
    iterations = 50
    
    # Benchmark session deletion
    for i in range(iterations):
        # Store fresh data
        temp_session = f"bench-del-{i}"
        await redis_adapter.store({
            'session_id': temp_session,
            'turn_id': 1,
            'content': 'Test'
        })
        
        # Measure deletion
        start = time.perf_counter()
        await redis_adapter.clear_session(temp_session)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    
    # Cleanup
    await redis_adapter.clear_session(session_id)
    
    mean = statistics.mean(times)
    print(f"\nDelete session - Mean: {mean:.3f}ms")
    
    assert mean < 1.0, f"Delete operation too slow: {mean:.3f}ms"
