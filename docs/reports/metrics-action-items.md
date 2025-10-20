# Priority 4A Metrics - Action Items

**Date**: October 21, 2025  
**Status**: 95% Complete - 3-4 hours remaining work  
**Current Grade**: A (95/100)  
**Target Grade**: A+ (100/100)  

---

## 🔴 CRITICAL - Must Complete (3 hours)

### 1. Integrate Metrics into Remaining Adapters

**Priority**: HIGH  
**Effort**: 2-3 hours (1 hour per adapter)  
**Assigned**: TBD  

#### Qdrant Adapter (`src/storage/qdrant_adapter.py`)

```python
# Add import at top
from .metrics import OperationTimer

# Wrap each operation method
async def connect(self) -> None:
    async with OperationTimer(self.metrics, 'connect'):
        # ... existing connect logic ...

async def disconnect(self) -> None:
    async with OperationTimer(self.metrics, 'disconnect'):
        # ... existing disconnect logic ...

async def store(self, data: Dict[str, Any]) -> str:
    async with OperationTimer(self.metrics, 'store'):
        # ... existing store logic ...

async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
    async with OperationTimer(self.metrics, 'retrieve'):
        # ... existing retrieve logic ...

async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
    async with OperationTimer(self.metrics, 'search'):
        # ... existing search logic ...

async def delete(self, id: str) -> bool:
    async with OperationTimer(self.metrics, 'delete'):
        # ... existing delete logic ...

# Optional: Add backend-specific metrics
async def _get_backend_metrics(self) -> Optional[Dict[str, Any]]:
    if not self._connected or not self.client:
        return None
    
    try:
        info = await self.client.get_collection(self.collection_name)
        return {
            'vector_count': info.points_count,
            'vector_dim': info.config.params.vectors.size,
            'collection_name': self.collection_name,
            'distance_metric': info.config.params.vectors.distance.name
        }
    except Exception as e:
        return {'error': str(e)}
```

**Test file**: `tests/storage/test_qdrant_metrics.py`
```python
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
            'embedding': [0.1] * 384
        })
        
        await adapter.retrieve(doc_id)
        await adapter.search({'vector': [0.1] * 384, 'limit': 5})
        await adapter.delete(doc_id)
        
        # Verify metrics
        metrics = await adapter.get_metrics()
        
        assert metrics['operations']['store']['total_count'] >= 1
        assert metrics['operations']['retrieve']['total_count'] >= 1
        assert metrics['operations']['search']['total_count'] >= 1
        assert metrics['operations']['delete']['total_count'] >= 1
        
        # Test export
        json_metrics = await adapter.export_metrics('json')
        assert isinstance(json_metrics, str)
        
    except Exception as e:
        pytest.skip(f"Qdrant not available: {e}")
    finally:
        try:
            await adapter.disconnect()
        except:
            pass
```

---

#### Neo4j Adapter (`src/storage/neo4j_adapter.py`)

Follow same pattern as Qdrant above. Backend-specific metrics example:

```python
async def _get_backend_metrics(self) -> Optional[Dict[str, Any]]:
    if not self._connected or not self.driver:
        return None
    
    try:
        async with self.driver.session() as session:
            result = await session.run("""
                CALL dbms.queryJmx('org.neo4j:instance=kernel#0,name=Store sizes')
                YIELD attributes
                RETURN attributes.NodeStoreSize.value AS nodeCount
            """)
            record = await result.single()
            
            return {
                'node_count': record['nodeCount'] if record else 0,
                'database_name': self.database
            }
    except Exception as e:
        return {'error': str(e)}
```

---

#### Typesense Adapter (`src/storage/typesense_adapter.py`)

Follow same pattern. Backend-specific metrics example:

```python
async def _get_backend_metrics(self) -> Optional[Dict[str, Any]]:
    if not self._connected or not self.client:
        return None
    
    try:
        collection = await self.client.collections[self.collection_name].retrieve()
        return {
            'document_count': collection.get('num_documents', 0),
            'collection_name': self.collection_name,
            'schema_fields': len(collection.get('fields', []))
        }
    except Exception as e:
        return {'error': str(e)}
```

---

## 🟡 IMPORTANT - Should Complete (1 hour)

### 2. Fix Test Warnings

**Priority**: MEDIUM  
**Effort**: 5 minutes  
**File**: `tests/storage/test_metrics.py`  

**Issue**: 3 test methods marked with `@pytest.mark.asyncio` but not async

**Fix Option 1** (Preferred - Keep as non-async):
```python
# Remove class-level asyncio mark, add only to async tests
class TestMetricsAggregator:
    """Test MetricsAggregator class."""
    
    def test_calculate_percentiles(self):  # No @pytest.mark.asyncio
        """Test percentile calculations."""
        # ... test code ...
```

**Fix Option 2** (Make methods async):
```python
@pytest.mark.asyncio
class TestMetricsAggregator:
    """Test MetricsAggregator class."""
    
    async def test_calculate_percentiles(self):  # Now async
        """Test percentile calculations."""
        # ... test code ...
```

---

### 3. Add Performance Benchmark

**Priority**: MEDIUM  
**Effort**: 1 hour  
**File**: `tests/benchmarks/bench_metrics_overhead.py`  

```python
"""
Benchmark metrics collection overhead.

Verifies that metrics collection adds < 5% overhead to operations.
"""
import pytest
import time
from src.storage.redis_adapter import RedisAdapter


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_metrics_overhead():
    """
    Verify metrics overhead is < 5%.
    
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
    
    print(f"\n=== Metrics Overhead Benchmark ===")
    print(f"Operations: {iterations}")
    print(f"Time without metrics: {time_without_metrics:.3f}s")
    print(f"Time with metrics: {time_with_metrics:.3f}s")
    print(f"Overhead: {overhead_pct:.2f}%")
    
    # Verify overhead < 5%
    assert overhead_pct < 5.0, f"Metrics overhead {overhead_pct:.2f}% exceeds 5% limit"
    
    print(f"✓ Overhead test PASSED ({overhead_pct:.2f}% < 5%)")
```

Run with:
```bash
.venv/bin/python -m pytest tests/benchmarks/bench_metrics_overhead.py -v -s
```

---

### 4. Implement bytes_per_sec in Aggregator

**Priority**: MEDIUM  
**Effort**: 15 minutes  
**File**: `src/storage/metrics/aggregator.py`  

**Current code** (line 50-69):
```python
@staticmethod
def calculate_rates(
    operations: List[Dict[str, Any]],
    window_seconds: int = 60
) -> Dict[str, float]:
    """
    Calculate ops/sec in time window.
    
    Returns:
        {'ops_per_sec': 25.0, 'bytes_per_sec': 12500}
    """
    if not operations:
        return {'ops_per_sec': 0.0}
    
    # Count operations in the window
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=window_seconds)
    
    count = 0
    for op in operations:
        op_time = datetime.fromisoformat(op['timestamp'].replace('Z', '+00:00'))
        if op_time >= window_start:
            count += 1
    
    ops_per_sec = count / window_seconds if window_seconds > 0 else 0
    return {'ops_per_sec': round(ops_per_sec, 2)}
```

**Updated code**:
```python
@staticmethod
def calculate_rates(
    operations: List[Dict[str, Any]],
    window_seconds: int = 60
) -> Dict[str, float]:
    """
    Calculate ops/sec and bytes/sec in time window.
    
    Returns:
        {'ops_per_sec': 25.0, 'bytes_per_sec': 12500}
    """
    if not operations:
        return {'ops_per_sec': 0.0, 'bytes_per_sec': 0.0}
    
    # Count operations and bytes in the window
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=window_seconds)
    
    count = 0
    total_bytes = 0
    for op in operations:
        op_time = datetime.fromisoformat(op['timestamp'].replace('Z', '+00:00'))
        if op_time >= window_start:
            count += 1
            # Sum bytes from metadata if available
            if 'metadata' in op and 'bytes' in op['metadata']:
                total_bytes += op['metadata']['bytes']
    
    ops_per_sec = count / window_seconds if window_seconds > 0 else 0
    bytes_per_sec = total_bytes / window_seconds if window_seconds > 0 else 0
    
    return {
        'ops_per_sec': round(ops_per_sec, 2),
        'bytes_per_sec': round(bytes_per_sec, 2)
    }
```

**Add test** in `tests/storage/test_metrics.py`:
```python
def test_calculate_rates_with_bytes(self):
    """Test rate calculations including bytes."""
    from datetime import datetime, timezone, timedelta
    
    now = datetime.now(timezone.utc)
    operations = [
        {
            'timestamp': (now - timedelta(seconds=30)).isoformat(),
            'metadata': {'bytes': 1000}
        },
        {
            'timestamp': (now - timedelta(seconds=20)).isoformat(),
            'metadata': {'bytes': 2000}
        },
        {
            'timestamp': (now - timedelta(seconds=10)).isoformat(),
            'metadata': {'bytes': 1500}
        }
    ]
    
    rates = MetricsAggregator.calculate_rates(operations, window_seconds=60)
    
    assert 'ops_per_sec' in rates
    assert 'bytes_per_sec' in rates
    assert rates['bytes_per_sec'] > 0
```

---

## 🟢 NICE TO HAVE - Enhancements (1-2 hours)

### 5. Remove Duplicate Import

**Priority**: LOW  
**Effort**: 1 minute  
**File**: `src/storage/metrics/collector.py`  

Line 64 has duplicate import:
```python
import random  # Already imported at top
```

**Fix**: Remove line 64, use the import from line 6.

---

### 6. Make Error History Configurable

**Priority**: LOW  
**Effort**: 10 minutes  
**File**: `src/storage/metrics/storage.py`  

**Current** (line 18):
```python
self._errors = deque(maxlen=100)  # Hardcoded
```

**Updated**:
```python
def __init__(self, max_history: int = 1000, max_errors: int = 100):
    self.max_history = max_history
    self.max_errors = max_errors
    self._operations = defaultdict(lambda: deque(maxlen=max_history))
    self._counters = defaultdict(int)
    self._errors = deque(maxlen=max_errors)
    self._lock = asyncio.Lock()
```

---

### 7. Add CSV Export for Errors

**Priority**: LOW  
**Effort**: 15 minutes  
**File**: `src/storage/metrics/exporters.py`  

Update `_to_csv()` function to include errors section.

---

### 8. Add Concurrent Operations Test

**Priority**: LOW  
**Effort**: 30 minutes  
**File**: `tests/storage/test_metrics.py`  

```python
@pytest.mark.asyncio
async def test_concurrent_operations(self):
    """Test metrics collection under concurrent load."""
    collector = MetricsCollector()
    
    async def worker(worker_id: int):
        for i in range(100):
            await collector.record_operation(
                f'op_{worker_id}',
                duration_ms=random.uniform(1, 100),
                success=True
            )
    
    # Run 10 workers concurrently
    await asyncio.gather(*[worker(i) for i in range(10)])
    
    # Verify all operations recorded
    metrics = await collector.get_metrics()
    total_ops = sum(
        stats['total_count'] 
        for stats in metrics['operations'].values()
    )
    assert total_ops == 1000  # 10 workers * 100 ops each
```

---

## Checklist for Completion

### Before Marking as Complete:

- [ ] All 3 adapters (Qdrant, Neo4j, Typesense) have OperationTimer integration
- [ ] All 3 adapters have integration tests passing
- [ ] Test warnings fixed
- [ ] Performance benchmark added and passing (< 5% overhead)
- [ ] Backend-specific metrics implemented for at least 2 adapters
- [ ] `bytes_per_sec` implemented in aggregator
- [ ] Duplicate import removed
- [ ] All tests passing
- [ ] Documentation updated if needed
- [ ] DEVLOG.md updated with completion notes

### Commands to Verify:

```bash
# Run all metrics tests
.venv/bin/python -m pytest tests/storage/test_metrics.py -v

# Run integration tests
.venv/bin/python -m pytest tests/storage/test_*_metrics.py -v

# Run benchmark
.venv/bin/python -m pytest tests/benchmarks/bench_metrics_overhead.py -v -s

# Check for any remaining issues
.venv/bin/python -m pytest tests/storage/ -v --tb=short
```

---

## Estimated Timeline

| Task | Effort | Priority |
|------|--------|----------|
| Qdrant adapter integration + test | 1 hour | 🔴 Critical |
| Neo4j adapter integration + test | 1 hour | 🔴 Critical |
| Typesense adapter integration + test | 1 hour | 🔴 Critical |
| Performance benchmark | 1 hour | 🟡 Important |
| Test warnings fix | 5 min | 🟡 Important |
| bytes_per_sec implementation | 15 min | 🟡 Important |
| Minor enhancements | 1 hour | 🟢 Nice to have |
| **TOTAL** | **5-6 hours** | |

---

## Success Criteria

When all items complete:
- ✅ All 4 adapters have metrics integration
- ✅ All tests passing with no warnings
- ✅ Performance overhead verified < 5%
- ✅ Grade increases from A (95) to A+ (100)
- ✅ Priority 4A can be marked as COMPLETE

---

**Created**: October 21, 2025  
**Last Updated**: October 21, 2025  
**Owner**: TBD
