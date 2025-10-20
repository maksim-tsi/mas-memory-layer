# Storage Adapter Performance Benchmarks

Comprehensive performance benchmarking suite for the MAS Memory Layer storage adapters.

## Overview

This benchmark suite measures the performance characteristics of all four storage adapters:

- **Redis (L1/L2)**: Hot and warm cache layers
- **Qdrant**: L3 semantic search (vector similarity)
- **Neo4j**: L3 graph traversal (entity relationships)
- **Typesense**: L3 full-text search (keyword queries)

The benchmarks use synthetic but realistic workloads that match typical agent memory access patterns.

## Quick Start

### Prerequisites

Ensure all storage backends are running:

```bash
# Redis
redis-server

# Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Neo4j
docker run -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest

# Typesense
docker run -p 8108:8108 typesense/typesense:latest --data-dir=/data --api-key=xyz
```

### Run Benchmark

```bash
# Default: 10,000 operations, all adapters
python tests/benchmarks/bench_storage_adapters.py

# Small workload (1,000 operations) for quick testing
python tests/benchmarks/bench_storage_adapters.py --size 1000

# Large workload (100,000 operations) for stress testing
python tests/benchmarks/bench_storage_adapters.py --size 100000

# Benchmark specific adapters only
python tests/benchmarks/bench_storage_adapters.py --adapters redis_l1 redis_l2

# Custom random seed for reproducibility
python tests/benchmarks/bench_storage_adapters.py --seed 12345
```

### Analyze Results

```bash
# Analyze most recent benchmark results
python tests/benchmarks/results_analyzer.py

# Analyze specific results file
python tests/benchmarks/results_analyzer.py --results benchmarks/results/raw/benchmark_20251021_143022.json

# Custom output directory
python tests/benchmarks/results_analyzer.py --output /path/to/output
```

## Workload Configurations

Pre-defined workload configurations are available in `benchmarks/configs/`:

| Config | Size | Runtime | Purpose |
|--------|------|---------|---------|
| **small** | 1,000 ops | ~1-2 min | Quick testing, CI/CD |
| **medium** | 10,000 ops | ~5-10 min | Default benchmarking |
| **large** | 100,000 ops | ~30-60 min | Stress testing, capacity planning |

### Workload Distribution

All workloads follow the same distribution (matching typical memory access patterns):

- **40%** L1 cache (Redis) - hot data, frequent access
- **30%** L2 cache (Redis) - warm data, moderate access
- **15%** L3 semantic search (Qdrant)
- **10%** L3 graph traversal (Neo4j)
- **5%** L3 full-text search (Typesense)

### Operation Mix

- **70%** read operations (retrieve + search)
- **25%** write operations (store)
- **5%** delete operations

## Output Files

### Raw Results

Located in `benchmarks/results/raw/`:

```
benchmark_20251021_143022.json  # Raw metrics from each adapter
```

Contains:
- Benchmark configuration (size, seed, timestamp)
- Per-adapter metrics (latencies, throughput, success rates)
- Complete operation statistics

### Processed Results

Located in `benchmarks/results/processed/`:

```
summary_20251021_143530.json    # Processed summary statistics
```

Contains:
- Aggregated performance metrics
- Computed percentiles (P50, P95, P99)
- Throughput calculations
- Backend-specific metrics

### Publication Tables

Located in `benchmarks/reports/tables/`:

```
latency_throughput_20251021_143530.md  # Table 1: Performance metrics
reliability_20251021_143530.md         # Table 2: Reliability metrics
```

Publication-ready markdown tables for papers/documentation.

## Example Output

### Table 1: Latency & Throughput Performance

| Storage Adapter | Role | Avg Latency (ms) | P95 Latency (ms) | Throughput (ops/sec) |
|-----------------|------|------------------|------------------|---------------------|
| redis_l1 | L1 Cache (Hot) | 0.85 | 1.42 | 52,000 |
| redis_l2 | L2 Cache (Warm) | 1.23 | 2.15 | 38,000 |
| qdrant | L3 Semantic Search | 8.45 | 18.32 | 8,500 |
| neo4j | L3 Graph Traversal | 15.67 | 42.18 | 3,200 |
| typesense | L3 Full-Text Search | 4.23 | 12.45 | 12,000 |

### Table 2: Reliability & Error Handling

| Storage Adapter | Success Rate | Error Rate | Total Operations | Notes |
|-----------------|--------------|------------|------------------|-------|
| redis_l1 | 100.00% | 0.00% | 4,000 | Production-ready ✅ |
| redis_l2 | 99.95% | 0.05% | 3,000 | Production-ready ✅ |
| qdrant | 99.87% | 0.13% | 1,500 | Production-ready ✅ |
| neo4j | 99.92% | 0.08% | 1,000 | Production-ready ✅ |
| typesense | 99.80% | 0.20% | 500 | Production-ready ✅ |

## Metrics Collected

For each adapter, the following metrics are collected:

### Operation Metrics
- **Total operations**: Count of each operation type
- **Success/error counts**: Operation outcomes
- **Success rate**: Percentage of successful operations

### Performance Metrics
- **Average latency**: Mean operation time
- **Percentile latencies**: P50, P95, P99
- **Min/max latency**: Fastest and slowest operations
- **Throughput**: Operations per second

### Backend-Specific Metrics
- **Redis**: Key count, memory usage
- **Qdrant**: Vector count, collection info
- **Neo4j**: Node count, database name
- **Typesense**: Document count, schema info

## Architecture

The benchmark suite consists of three main components:

### 1. Workload Generator (`workload_generator.py`)

Generates synthetic operations matching real-world patterns:
- Realistic data structures for each adapter
- Proper distribution across storage layers
- Reproducible with random seed

### 2. Benchmark Runner (`bench_storage_adapters.py`)

Executes workload and collects metrics:
- Initializes and connects to all adapters
- Executes operations sequentially
- Leverages existing metrics infrastructure
- Saves raw results to JSON

### 3. Results Analyzer (`results_analyzer.py`)

Processes and presents results:
- Computes aggregate statistics
- Generates publication-ready tables
- Produces summary JSON for further analysis

## Integration with Metrics System

The benchmark leverages the existing metrics infrastructure (implemented in [ADR-001](../../docs/ADR/001-benchmarking-strategy.md)):

- Uses `OperationTimer` context managers (already in adapters)
- Calls `export_metrics('json')` to collect data
- No additional instrumentation needed
- Zero metrics collection overhead (already built-in)

## Customization

### Custom Workload Distribution

```python
from tests.benchmarks.bench_storage_adapters import StorageBenchmark

config = {
    'workload_size': 5000,
    'workload_seed': 99,
    'adapters': ['redis_l1', 'qdrant']  # Only these adapters
}

benchmark = StorageBenchmark(config)
await benchmark.run_benchmark()
```

### Custom Analysis

```python
from tests.benchmarks.results_analyzer import BenchmarkAnalyzer

analyzer = BenchmarkAnalyzer(results_file)
summary = analyzer.generate_summary()

# Access specific metrics
redis_latency = summary['adapters']['redis_l1']['performance']['avg_latency_ms']
print(f"Redis L1 average latency: {redis_latency:.2f}ms")
```

## Troubleshooting

### Adapter Connection Failures

If an adapter fails to connect:
- Ensure the backend service is running
- Check connection configuration in `bench_storage_adapters.py`
- The benchmark will continue with remaining adapters

### Low Throughput

If throughput is unexpectedly low:
- Check system resources (CPU, memory)
- Ensure backends are not throttling
- Consider network latency (use localhost for benchmarks)

### High Error Rates

If error rates exceed 1%:
- Check backend logs for issues
- Verify data format matches adapter expectations
- Consider reducing workload size

## Performance Expectations

Based on architecture design (localhost, adequate resources):

| Adapter | Expected Avg Latency | Expected P95 Latency | Expected Throughput |
|---------|---------------------|---------------------|-------------------|
| Redis (L1/L2) | < 2ms | < 5ms | > 30K ops/sec |
| Qdrant | 5-15ms | 20-30ms | 5-10K ops/sec |
| Neo4j | 10-25ms | 40-60ms | 2-5K ops/sec |
| Typesense | 3-8ms | 15-25ms | 10-15K ops/sec |

## Next Steps

1. **Run benchmarks** with different workload sizes
2. **Compare results** across environments
3. **Track over time** for regression detection
4. **Use in CI/CD** for automated performance testing
5. **Generate publication tables** for papers/reports

## References

- [ADR-002: Storage Performance Benchmarking](../../docs/ADR/002-storage-performance-benchmarking.md)
- [Metrics Implementation](../../docs/reports/metrics-implementation-final.md)
- [Storage Adapter Documentation](../../src/storage/README.md)

## License

See [LICENSE](../../LICENSE) for details.
