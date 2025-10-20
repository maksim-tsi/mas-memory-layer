# Lightweight Benchmarking Setup & Improvement Plan

**Date**: October 21, 2025  
**Status**: 🔄 Planning  
**Priority**: High  
**Related**: [ADR-002](../ADR/002-storage-performance-benchmarking.md), [BENCHMARK_IMPLEMENTATION.md](../../BENCHMARK_IMPLEMENTATION.md)

---

## Problem Analysis

After implementing and running the storage adapter benchmark suite, we identified three issues affecting result quality:

### Current Benchmark Results

| Adapter | Success Rate | Issue |
|---------|--------------|-------|
| Redis L1/L2 | 100% | ✅ Working perfectly |
| Qdrant | 57.50% | ⚠️ **0% store success** (199 failures) |
| Neo4j | 87.45% | ⚠️ **55.5% store success** (61 failures) |
| Typesense | 41.18% | ⚠️ Collection doesn't exist |

### Root Cause Analysis

#### 1. Qdrant: 0% Store Success (Critical)

**Observed Behavior:**
- `store`: 0/199 (0.0%) ❌
- `retrieve`: 221/221 (100.0%) ✅
- `search`: 138/262 (52.7%) ⚠️
- `delete`: 78/78 (100.0%) ✅

**Root Cause:**
The Qdrant adapter is **synchronously storing vectors via upsert**, which in high-throughput scenarios may face:
- Collection lock contention during batch operations
- Vector index rebuild delays
- HNSW index update bottlenecks
- Network latency on remote connections (192.168.107.187)

**Evidence from Code Analysis:**
```python
# src/storage/qdrant_adapter.py:207
await self.client.upsert(
    collection_name=self.collection_name,
    points=[point]  # Single point per call - inefficient
)
```

**Why This Matters:**
- Qdrant's HNSW index requires rebuilding on writes
- Single-point upserts in rapid succession cause index thrashing
- Remote network latency (LAN vs localhost) amplifies the issue

#### 2. Neo4j: 55.5% Store Success (Moderate)

**Observed Behavior:**
- `store`: 76/137 (55.5%) ⚠️
- All relationship stores fail due to missing nodes
- Entity stores work but relationship stores fail cascadingly

**Root Cause:**
The workload generator creates relationships **before corresponding entities exist**:

```python
# tests/benchmarks/workload_generator.py
if data['type'] == 'relationship':
    data['from'] = random.choice(self.stored_ids['neo4j']) if self.stored_ids['neo4j'] else entity_id
    data['to'] = random.choice(self.stored_ids['neo4j']) if self.stored_ids['neo4j'] else entity_id
```

**Problem:** When `stored_ids['neo4j']` is empty initially, relationships use the current `entity_id` as both from/to, but that entity hasn't been stored yet.

#### 3. Typesense: 41.18% Success (Collection Missing)

**Root Cause:**
- Collection `benchmark_documents` doesn't exist
- Typesense adapter doesn't auto-create collections on connect (unlike Qdrant)
- All operations fail with HTTP 404

---

## Solution Strategy

### Phase 1: Quick Wins (Immediate - 1 hour)

#### 1.1. Fix Workload Generator Logic ✅ **DONE**

**Issue:** Neo4j relationships reference non-existent entities  
**Solution:** Ensure entities are stored before creating relationships

```python
# Improved approach:
def _generate_neo4j_store(self) -> WorkloadOperation:
    entity_id = str(uuid.uuid4())
    
    # 70% entities, 30% relationships (only if entities exist)
    if random.random() < 0.7 or len(self.stored_ids['neo4j']) < 2:
        # Store entity
        data = {
            'type': 'entity',
            'label': random.choice(['Person', 'Topic', 'Event', 'Concept']),
            'properties': {
                'name': self._random_text(5, 20),
                'session_id': random.choice(self.session_ids),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        }
    else:
        # Store relationship (entities guaranteed to exist)
        data = {
            'type': 'relationship',
            'from': random.choice(self.stored_ids['neo4j']),
            'to': random.choice(self.stored_ids['neo4j']),
            'relationship': random.choice(['KNOWS', 'RELATED_TO', 'MENTIONS', 'FOLLOWS']),
            'properties': {
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        }
```

**Status:** ✅ Partially done (field naming fixed), needs ratio adjustment

#### 1.2. Auto-Create Typesense Collection

**Issue:** Collection doesn't exist, all operations fail  
**Solution:** Make Typesense adapter create collection on connect (like Qdrant does)

```python
# src/storage/typesense_adapter.py
async def connect(self) -> None:
    async with OperationTimer(self.metrics, 'connect'):
        # ... existing connection code ...
        
        # Check if collection exists, create if not
        try:
            self.client.collections[self.collection_name].retrieve()
        except Exception:
            # Create collection
            schema = {
                'name': self.collection_name,
                'fields': [
                    {'name': 'content', 'type': 'string'},
                    {'name': 'title', 'type': 'string'},
                    {'name': 'session_id', 'type': 'string'},
                    {'name': 'timestamp', 'type': 'int64'}
                ],
                'default_sorting_field': 'timestamp'
            }
            self.client.collections.create(schema)
            logger.info(f"Created Typesense collection: {self.collection_name}")
```

**Impact:** Enables Typesense benchmarking, expected ~95%+ success rate

#### 1.3. Add Pre-Warming Phase to Benchmark

**Issue:** Initial operations fail because no data exists  
**Solution:** Add warm-up phase that stores baseline data before main workload

```python
# tests/benchmarks/bench_storage_adapters.py
async def _warm_up_adapter(self, adapter, adapter_name: str) -> None:
    """Pre-populate adapter with baseline data."""
    logger.info(f"Warming up {adapter_name}...")
    
    warmup_counts = {
        'redis_l1': 50,
        'redis_l2': 50,
        'qdrant': 100,      # Need vectors for search
        'neo4j': 50,        # Need entities for relationships
        'typesense': 50     # Need docs for search
    }
    
    count = warmup_counts.get(adapter_name, 50)
    generator = WorkloadGenerator(seed=42)
    
    for i in range(count):
        op = generator._generate_store_op(adapter_name)
        try:
            await self._execute_operation(adapter, op)
        except Exception:
            pass  # Ignore warmup errors
    
    logger.info(f"✓ {adapter_name} warmed up ({count} items)")
```

**Impact:** Eliminates cold-start bias, improves realistic success rates

---

### Phase 2: Performance Optimization (Short-term - 2-4 hours)

#### 2.1. Implement Qdrant Batch Upsert

**Issue:** Single-point upserts cause index thrashing  
**Current:** 0% success rate on stores  
**Solution:** Batch upsert points (10-50 at a time)

```python
# src/storage/qdrant_adapter.py - New method
async def store_batch(self, items: List[Dict[str, Any]]) -> List[str]:
    """
    Optimized batch upsert for Qdrant.
    
    Batching reduces index rebuild overhead from N rebuilds to 1.
    """
    async with OperationTimer(self.metrics, 'store_batch'):
        if not self._connected or not self.client:
            raise StorageConnectionError("Not connected to Qdrant")
        
        points = []
        ids = []
        
        for data in items:
            validate_required_fields(data, ['vector', 'content'])
            point_id = data.get('id', str(uuid.uuid4()))
            ids.append(point_id)
            
            payload = {
                'content': data['content'],
                'metadata': data.get('metadata', {}),
            }
            for key, value in data.items():
                if key not in ['vector', 'content', 'id', 'metadata']:
                    payload[key] = value
            
            points.append(PointStruct(
                id=point_id,
                vector=data['vector'],
                payload=payload
            ))
        
        # Single batch upsert
        await self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        return [str(id) for id in ids]
```

**Update Benchmark Runner:**
```python
# Accumulate stores and batch them
BATCH_SIZE = 20
pending_stores = {adapter_name: [] for adapter_name in adapters}

for op in workload:
    if op.op_type == 'store':
        pending_stores[op.adapter].append(op.data)
        
        if len(pending_stores[op.adapter]) >= BATCH_SIZE:
            # Flush batch
            await adapter.store_batch(pending_stores[op.adapter])
            pending_stores[op.adapter] = []
    else:
        # Flush any pending stores first
        if pending_stores[op.adapter]:
            await adapter.store_batch(pending_stores[op.adapter])
            pending_stores[op.adapter] = []
        
        # Execute other operation
        await execute_operation(op)
```

**Expected Impact:**
- Qdrant store success: 0% → 95%+
- 10-20x throughput improvement
- Reduced index rebuild overhead

#### 2.2. Add Connection Pooling Metrics

**Issue:** Remote connections (LAN) may timeout under load  
**Solution:** Add connection pool metrics and retry logic

```python
# src/storage/metrics/collector.py - Add new metrics
class MetricsCollector:
    def __init__(self, config: Dict[str, Any]):
        # ... existing code ...
        self.connection_metrics = {
            'active_connections': 0,
            'connection_errors': 0,
            'retry_count': 0,
            'timeout_count': 0
        }
```

#### 2.3. Implement Intelligent Retry with Exponential Backoff

**Issue:** Network blips cause cascading failures  
**Solution:** Add retry decorator for transient failures

```python
# src/storage/base.py - New decorator
def with_retry(max_retries=3, backoff_factor=0.5):
    """Retry decorator for transient failures."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (StorageTimeoutError, StorageConnectionError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        await asyncio.sleep(wait_time)
                        logger.warning(f"Retry {attempt+1}/{max_retries} after {wait_time}s")
            raise last_exception
        return wrapper
    return decorator

# Apply to adapters:
@with_retry(max_retries=3)
async def store(self, data: Dict[str, Any]) -> str:
    # ... existing code ...
```

---

### Phase 3: Metrics Enhancement (Medium-term - 4-6 hours)

#### 3.1. Add Database-Specific Performance Metrics

**Problem:** Generic metrics miss database-specific bottlenecks

**Qdrant-Specific Metrics:**
```python
async def _get_backend_metrics(self) -> Optional[Dict[str, Any]]:
    """Enhanced Qdrant metrics."""
    if not self._connected or not self.client:
        return None
    
    collection = await self.client.get_collection(self.collection_name)
    
    return {
        'vector_count': collection.points_count,
        'indexed_vectors': collection.indexed_vectors_count,
        'segments_count': collection.segments_count,
        'index_build_status': collection.status,  # NEW
        'disk_data_size_bytes': collection.disk_data_size,  # NEW
        'ram_data_size_bytes': collection.ram_data_size,  # NEW
        'optimization_status': collection.optimizer_status,  # NEW
    }
```

**Neo4j-Specific Metrics:**
```python
async def _get_backend_metrics(self) -> Optional[Dict[str, Any]]:
    """Enhanced Neo4j metrics."""
    cypher = """
        CALL dbms.queryJmx('org.neo4j:instance=kernel#0,name=Transactions')
        YIELD attributes
        RETURN attributes.NumberOfOpenTransactions.value AS open_tx,
               attributes.PeakNumberOfConcurrentTransactions.value AS peak_tx
    """
    
    async with self.driver.session(database=self.database) as session:
        result = await session.run(cypher)
        tx_metrics = await result.single()
        
        # Also get node/rel counts
        stats = await session.run("""
            MATCH (n) RETURN count(n) AS nodes
            UNION ALL
            MATCH ()-[r]->() RETURN count(r) AS relationships
        """)
        
        return {
            'node_count': node_count,
            'relationship_count': rel_count,
            'open_transactions': tx_metrics['open_tx'],  # NEW
            'peak_transactions': tx_metrics['peak_tx'],  # NEW
            'cache_hits': cache_stats,  # NEW
        }
```

**Typesense-Specific Metrics:**
```python
async def _get_backend_metrics(self) -> Optional[Dict[str, Any]]:
    """Enhanced Typesense metrics."""
    collection = self.client.collections[self.collection_name].retrieve()
    
    return {
        'document_count': collection['num_documents'],
        'memory_bytes': collection['num_memory_shards'],  # NEW
        'disk_bytes': collection['num_disk_shards'],  # NEW
        'schema_fields': len(collection['fields']),
    }
```

#### 3.2. Add Workload-Aware Metrics

**Problem:** Need to understand which workload patterns cause issues

```python
# src/storage/metrics/collector.py
class MetricsCollector:
    def record_operation_context(
        self,
        operation: str,
        context: Dict[str, Any]
    ):
        """Record contextual metadata for operations."""
        self.operation_contexts.append({
            'operation': operation,
            'workload_phase': context.get('phase'),  # warmup, main, cooldown
            'batch_size': context.get('batch_size'),
            'concurrent_ops': context.get('concurrent_ops'),
            'timestamp': datetime.now().isoformat()
        })
```

#### 3.3. Generate Performance Heatmaps

**Goal:** Visualize performance across operation types and adapters

```python
# tests/benchmarks/results_analyzer.py
def generate_performance_heatmap(self, output_file: Path):
    """Generate heatmap showing latency by adapter and operation."""
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    # Build matrix: adapters x operations
    adapters = ['redis_l1', 'redis_l2', 'qdrant', 'neo4j', 'typesense']
    operations = ['store', 'retrieve', 'search', 'delete']
    
    matrix = []
    for adapter in adapters:
        row = []
        for op in operations:
            latency = self._get_operation_latency(adapter, op)
            row.append(latency)
        matrix.append(row)
    
    # Plot heatmap
    sns.heatmap(matrix, annot=True, xticklabels=operations, 
                yticklabels=adapters, cmap='YlOrRd')
    plt.title('Storage Adapter Performance Heatmap (ms)')
    plt.savefig(output_file)
```

---

### Phase 4: Benchmark Configuration (Medium-term - 2-3 hours)

#### 4.1. Separate Workload Profiles

**Problem:** One-size-fits-all workload doesn't match real usage

**Create Workload Profiles:**
```yaml
# benchmarks/configs/profile_cache_heavy.yaml
name: cache_heavy
description: Heavy L1/L2 cache usage (hot path)
size: 10000
seed: 42
distribution:
  redis_l1: 0.60    # 60% hot cache
  redis_l2: 0.30    # 30% warm cache
  qdrant: 0.05      # 5% semantic
  neo4j: 0.03       # 3% graph
  typesense: 0.02   # 2% search

operation_mix:
  read: 0.80        # 80% reads (realistic cache)
  write: 0.15       # 15% writes
  delete: 0.05      # 5% deletes

# benchmarks/configs/profile_semantic_heavy.yaml
name: semantic_heavy
description: Heavy semantic search (research/discovery)
distribution:
  redis_l1: 0.10
  redis_l2: 0.10
  qdrant: 0.50      # 50% semantic search
  neo4j: 0.20       # 20% graph traversal
  typesense: 0.10   # 10% full-text

operation_mix:
  read: 0.90        # 90% reads (search-heavy)
  write: 0.08
  delete: 0.02
```

#### 4.2. Add Concurrent Workload Option

**Problem:** Sequential operations don't test real concurrency

```python
# tests/benchmarks/bench_storage_adapters.py
class StorageBenchmark:
    async def run_concurrent_benchmark(
        self,
        workload_size: int,
        concurrency: int = 10
    ):
        """Run benchmark with concurrent operations."""
        
        # Split workload into chunks
        chunks = self._chunk_workload(workload, concurrency)
        
        # Run chunks concurrently
        tasks = []
        for chunk in chunks:
            task = asyncio.create_task(
                self._execute_workload_chunk(adapter, chunk)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
```

#### 4.3. Environment-Specific Configuration

**Problem:** Localhost vs LAN vs WAN have different characteristics

```yaml
# benchmarks/configs/environment_lan.yaml
name: lan_environment
description: Benchmarking over LAN (192.168.x.x)
timeout_multiplier: 2.0
retry_config:
  max_retries: 3
  backoff_factor: 0.5
batch_sizes:
  qdrant: 50      # Larger batches over LAN
  neo4j: 20
  typesense: 30
expected_latencies:
  redis: 5ms      # LAN adds ~2-3ms
  qdrant: 20ms
  neo4j: 40ms
```

---

## Implementation Roadmap

### Week 1: Critical Fixes (Must Have)

| Task | Priority | Effort | Impact | Status |
|------|----------|--------|--------|--------|
| Fix Neo4j relationship logic | P0 | 30m | High | ✅ Partial |
| Add Typesense auto-create | P0 | 1h | High | 🔄 TODO |
| Add benchmark warm-up phase | P0 | 1h | High | 🔄 TODO |
| Implement Qdrant batch upsert | P0 | 2h | Critical | 🔄 TODO |
| Add retry logic | P1 | 1h | Medium | 🔄 TODO |

**Expected Results After Week 1:**
- Redis: 100% (no change) ✅
- Qdrant: 95%+ (up from 57%) 📈
- Neo4j: 95%+ (up from 87%) 📈
- Typesense: 95%+ (up from 41%) 📈

### Week 2: Metrics Enhancement (Should Have)

| Task | Priority | Effort | Impact | Status |
|------|----------|--------|--------|--------|
| Enhanced DB-specific metrics | P1 | 3h | Medium | 🔄 TODO |
| Workload-aware metrics | P2 | 2h | Low | 🔄 TODO |
| Performance heatmaps | P2 | 2h | Medium | 🔄 TODO |

### Week 3: Configuration & Profiles (Nice to Have)

| Task | Priority | Effort | Impact | Status |
|------|----------|--------|--------|--------|
| Workload profiles | P2 | 2h | Medium | 🔄 TODO |
| Concurrent benchmarks | P2 | 2h | Medium | 🔄 TODO |
| Environment configs | P3 | 1h | Low | 🔄 TODO |

---

## Success Criteria

### Minimum Viable Benchmark (Week 1)

✅ **All adapters achieve >95% success rate**  
✅ **Realistic workload with warm-up phase**  
✅ **Proper batching for Qdrant**  
✅ **Auto-collection creation for Typesense**  
✅ **Clean publication-ready tables**

### Enhanced Benchmark (Week 2-3)

✅ **Database-specific performance insights**  
✅ **Multiple workload profiles**  
✅ **Concurrent operation testing**  
✅ **Performance visualization (heatmaps)**  
✅ **Environment-aware configuration**

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Qdrant index thrashing persists | Medium | High | Implement index optimization parameters |
| Network latency dominates results | High | Medium | Document as LAN overhead, test localhost |
| Neo4j transaction contention | Low | Medium | Add transaction pooling config |
| Typesense schema mismatches | Low | Low | Validate schema before operations |

---

## Alternative Approaches Considered

### 1. Mock Backends Instead of Real Services

**Pros:** No infrastructure dependencies, faster execution  
**Cons:** Not realistic, defeats purpose of performance validation  
**Decision:** ❌ Rejected - Need real performance characteristics

### 2. Use Docker Compose for Consistent Environment

**Pros:** Reproducible, localhost testing, version-pinned  
**Cons:** Requires Docker, slower than remote dedicated servers  
**Decision:** ⏸️ Consider for CI/CD, keep LAN for dev

### 3. Separate Benchmark per Adapter

**Pros:** Isolated testing, easier debugging  
**Cons:** Loses comparative analysis, more maintenance  
**Decision:** ❌ Rejected - Comparison is key value

---

## Metrics We're NOT Collecting (And Why)

### ❌ Memory Profiling per Operation
**Why:** Python memory profiling adds 30-50% overhead, skews latency results  
**Alternative:** Use backend-specific memory metrics (Qdrant RAM, Neo4j heap)

### ❌ Network Packet Analysis
**Why:** Out of scope, infra team responsibility  
**Alternative:** Document expected LAN latency overhead

### ❌ Disk I/O Per Operation
**Why:** Backends abstract this, we measure end-to-end latency  
**Alternative:** Use backend metrics (Qdrant disk_data_size)

### ❌ CPU/Thread Profiling
**Why:** Python's async model makes this misleading  
**Alternative:** Track concurrent operations count

---

## Documentation Updates Required

### 1. Update ADR-002
- Add "Lessons Learned" section
- Document batch upsert decision
- Explain warm-up phase rationale

### 2. Update benchmarks/README.md
- Add "Known Limitations" section
- Document expected success rates
- Add troubleshooting for <95% success

### 3. Create benchmarks/TROUBLESHOOTING.md
- Low success rates debugging
- Network latency identification
- Batch size tuning guide

---

## Next Actions

### Immediate (Today)

1. ✅ **Create this plan document**
2. 🔄 **Implement Neo4j entity-first logic** (30 minutes)
3. 🔄 **Add Typesense auto-create collection** (1 hour)
4. 🔄 **Test with 1K workload** (10 minutes)

### Tomorrow

5. 🔄 **Implement Qdrant batch upsert** (2 hours)
6. 🔄 **Add benchmark warm-up phase** (1 hour)
7. 🔄 **Run full 10K benchmark** (30 minutes)
8. 🔄 **Generate publication tables** (15 minutes)

### This Week

9. 🔄 **Add retry logic** (1 hour)
10. 🔄 **Update documentation** (1 hour)
11. 🔄 **Create troubleshooting guide** (1 hour)

---

## Conclusion

The benchmark suite is **functionally complete** but needs **quality improvements** to produce publication-worthy results. The issues are well-understood and have clear solutions:

1. **Qdrant**: Needs batch operations (architectural issue)
2. **Neo4j**: Needs entity-first workload (workload issue)
3. **Typesense**: Needs auto-create (initialization issue)

**Estimated time to >95% success rates: 4-6 hours**

After Phase 1 implementation, we'll have:
- Clean, reproducible benchmarks
- Realistic success rates (>95% all adapters)
- Publication-ready performance tables
- Foundation for enhanced metrics (Phases 2-3)

The plan is **incremental** and **pragmatic** - we can ship Phase 1 results to the paper while continuing Phase 2-3 enhancements.

---

**Status**: Ready for implementation  
**Owner**: Development Team  
**Review Date**: October 22, 2025
