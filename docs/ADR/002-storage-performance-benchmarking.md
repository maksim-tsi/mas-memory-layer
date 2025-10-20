# ADR-002: Storage Performance Benchmarking Strategy

**Date**: October 21, 2025  
**Status**: Proposed  
**Decision Makers**: MAS Memory Layer Team  
**Related**: [ADR-001: Benchmarking Strategy](001-benchmarking-strategy.md), [Metrics Implementation Final](../reports/metrics-implementation-final.md)

---

## Context

We have successfully implemented comprehensive metrics collection across all four storage adapters (Redis, Qdrant, Neo4j, Typesense). Each adapter now tracks:

- Operation timing (connect, disconnect, store, retrieve, search, delete)
- Success/failure rates
- Performance metrics (avg, min, max, p50, p95, p99 latencies)
- Backend-specific metrics

**Current State**:
- ✅ Metrics infrastructure: 100% complete
- ✅ All adapters instrumented
- ✅ Integration tests passing
- ⚠️ No performance benchmarks exist yet

**Need**: 
We need to demonstrate the performance characteristics of our multi-layered memory architecture for:
1. Publication/paper results section
2. Production capacity planning
3. Performance regression detection
4. Architecture validation

---

## Decision

We will create a **micro-benchmark suite** that leverages our existing metrics infrastructure to measure real-world performance of the storage layer.

### Scope

**In Scope**:
- Benchmark all 4 specialized storage adapters
- Use synthetic but realistic workload patterns
- Generate publication-ready performance tables
- Measure latency, throughput, and reliability

**Out of Scope**:
- PostgreSQL baseline comparison (different capabilities = apples to oranges)
- Full application-level benchmarks (e.g., GoodAI LTM benchmark)
- Memory overhead measurement
- Network latency isolation

### Approach

#### 1. Synthetic Workload Generator

Create realistic operation patterns matching production usage:

```
Workload Distribution:
- 40% L1 cache operations (Redis) - hot data, frequent access
- 30% L2 cache operations (Redis) - warm data, moderate access  
- 15% L3 semantic search (Qdrant) - vector similarity queries
- 10% L3 graph traversal (Neo4j) - relationship queries
- 5% L3 full-text search (Typesense) - keyword searches
```

**Rationale**: Distribution reflects typical agent memory access patterns where:
- Hot cache (L1) serves immediate context
- Warm cache (L2) serves recent history
- L3 serves deep retrieval needs

#### 2. Benchmark Execution

```python
# Pseudo-code workflow
for each adapter in [redis_l1, redis_l2, qdrant, neo4j, typesense]:
    adapter.connect()
    
    # Execute workload (metrics auto-collected)
    for operation in synthetic_workload:
        await adapter.execute(operation)
    
    # Export metrics using existing infrastructure
    metrics = await adapter.export_metrics('json')
    save_results(adapter_name, metrics)
    
    adapter.disconnect()
```

**Key Advantage**: Uses existing metrics infrastructure - no new instrumentation needed.

#### 3. Results Analysis

Generate two publication-ready tables:

**Table 1: Latency & Throughput Performance**

| Storage Adapter | Role | Avg Latency (ms) | P95 Latency (ms) | Throughput (ops/sec) |
|----------------|------|------------------|------------------|---------------------|
| RedisAdapter | L1 Cache | TBD | TBD | TBD |
| RedisAdapter | L2 Cache | TBD | TBD | TBD |
| QdrantAdapter | L3 Semantic Search | TBD | TBD | TBD |
| Neo4jAdapter | L3 Graph Traversal | TBD | TBD | TBD |
| TypesenseAdapter | L3 Full-Text Search | TBD | TBD | TBD |

**Table 2: Reliability Metrics**

| Storage Adapter | Success Rate | Error Rate | Notes |
|----------------|--------------|------------|-------|
| All Adapters | > 99.9% | < 0.1% | Production-ready error handling |

---

## Expected Outcomes

### Hypothesis: Performance Characteristics

Based on architecture design, we expect:

| Adapter | Expected Avg Latency | Expected P95 Latency | Expected Throughput | Rationale |
|---------|---------------------|---------------------|-------------------|-----------|
| Redis (L1) | < 1ms | < 2ms | > 50K ops/sec | In-memory, minimal compute |
| Redis (L2) | < 2ms | < 5ms | > 30K ops/sec | In-memory, slightly cooler data |
| Qdrant | 5-15ms | 20-30ms | 5-10K ops/sec | Vector similarity computation |
| Neo4j | 10-25ms | 40-60ms | 2-5K ops/sec | Graph traversal complexity |
| Typesense | 3-8ms | 15-25ms | 10-15K ops/sec | Optimized search engine |

### Success Criteria

Benchmark is successful if:
- ✅ All adapters achieve > 99.9% success rate
- ✅ L1 cache < 5ms P95 latency
- ✅ L2 cache < 10ms P95 latency  
- ✅ L3 adapters < 100ms P95 latency
- ✅ Results are reproducible (< 10% variance across runs)

---

## Implementation Plan

### Phase 1: Core Infrastructure
**Files to Create**:
- `tests/benchmarks/workload_generator.py` - Synthetic workload generation
- `tests/benchmarks/bench_storage_adapters.py` - Main benchmark runner
- `tests/benchmarks/results_analyzer.py` - Results analysis and table generation

### Phase 2: Configuration
**Files to Create**:
- `benchmarks/configs/workload_small.yaml` - 1K operations (quick test)
- `benchmarks/configs/workload_medium.yaml` - 10K operations (default)
- `benchmarks/configs/workload_large.yaml` - 100K operations (stress test)

### Phase 3: Execution & Analysis
**Directories**:
- `benchmarks/results/raw/` - JSON metrics exports
- `benchmarks/results/processed/` - Analyzed results
- `benchmarks/reports/tables/` - Publication-ready markdown tables
- `benchmarks/reports/figures/` - Performance charts (optional)

### Phase 4: Documentation
**Files to Create**:
- `benchmarks/README.md` - How to run benchmarks
- `requirements-benchmark.txt` - Additional dependencies (if any)

---

## Alternatives Considered

### Alternative 1: PostgreSQL Baseline Comparison
**Rejected**: PostgreSQL is not designed for the same use cases:
- No native vector similarity search (without pgvector extension)
- Graph queries require recursive CTEs (much slower than Neo4j)
- Full-text search less optimized than Typesense
- Comparison would be unfair ("apples to oranges")

### Alternative 2: Full GoodAI LTM Benchmark
**Rejected for this phase**: 
- Too heavyweight (hours to run)
- Tests full system, not storage layer isolation
- Already planned separately in ADR-001
- Micro-benchmarks provide faster feedback

### Alternative 3: Mock/Simulated Adapters
**Rejected**: 
- Would not validate real-world performance
- Defeats purpose of benchmarking
- We need actual database performance characteristics

---

## Consequences

### Positive
- ✅ **Fast execution**: Micro-benchmark runs in minutes
- ✅ **Leverages existing work**: Uses completed metrics infrastructure
- ✅ **Reproducible**: Synthetic workload ensures consistency
- ✅ **Publication-ready**: Direct table generation
- ✅ **CI-friendly**: Can run in automated pipelines
- ✅ **Regression detection**: Baseline for future changes

### Negative
- ⚠️ **Requires running services**: All 4 backends must be available
- ⚠️ **Synthetic workload**: May not match all real-world patterns
- ⚠️ **Environment sensitive**: Results vary by hardware/network
- ⚠️ **No baseline comparison**: Can't show improvement vs. monolithic approach

### Neutral
- ℹ️ Complements (not replaces) full system benchmarks
- ℹ️ Focuses on storage layer only
- ℹ️ Results specific to test environment

---

## Future Enhancements

### Near-term (Optional)
1. **Visualization**: Generate latency distribution charts
2. **Comparison Runs**: Track performance over time
3. **CI Integration**: Run on every commit to dev branch
4. **Resource Monitoring**: Add CPU/memory profiling

### Long-term
1. **Multi-environment**: Benchmark on different hardware
2. **Scaling Tests**: Measure performance with varying data sizes
3. **Concurrency Tests**: Multi-threaded workload simulation
4. **Real Workload Replay**: Capture and replay production patterns

---

## References

- [ADR-001: Benchmarking Strategy](001-benchmarking-strategy.md)
- [Metrics Implementation Final Report](../reports/metrics-implementation-final.md)
- [Metrics Quick Reference](../reports/metrics-quick-reference.md)
- Existing metrics infrastructure: `src/storage/metrics/`

---

## Notes

This ADR focuses on **storage layer performance validation** using the metrics infrastructure we've already built. It provides fast, reproducible results for publication and capacity planning without the overhead of full system benchmarks.

The decision to exclude PostgreSQL baseline comparison is deliberate - we're measuring specialized adapters against their intended use cases, not comparing different architectural approaches.

---

**Next Steps**:
1. ✅ Get approval on this ADR
2. 🔄 Implement workload generator
3. 🔄 Create benchmark runner
4. 🔄 Execute benchmarks and collect results
5. 🔄 Generate publication tables
6. 🔄 Update paper/documentation with results
