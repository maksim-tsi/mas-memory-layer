# Benchmark Quick Reference

## Prerequisites
```bash
# Ensure storage backends are running:
redis-server                                                          # Redis (ports 6379)
docker run -p 6333:6333 qdrant/qdrant                                # Qdrant
docker run -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest   # Neo4j
docker run -p 8108:8108 typesense/typesense:latest --api-key=xyz    # Typesense
```

## Quick Commands

### Run Benchmark (Default: 10K ops)
```bash
source .venv/bin/activate
python scripts/run_storage_benchmark.py
```

### Run Small Benchmark (1K ops - Quick Test)
```bash
python scripts/run_storage_benchmark.py run --size 1000
```

### Run Large Benchmark (100K ops - Stress Test)
```bash
python scripts/run_storage_benchmark.py run --size 100000
```

### Benchmark Specific Adapters Only
```bash
python scripts/run_storage_benchmark.py run --adapters redis_l1 redis_l2
```

### Analyze Most Recent Results
```bash
python scripts/run_storage_benchmark.py analyze
```

### Analyze Specific Results File
```bash
python tests/benchmarks/results_analyzer.py --results benchmarks/results/raw/benchmark_20251021_143022.json
```

## Output Locations

- **Raw Results**: `benchmarks/results/raw/benchmark_TIMESTAMP.json`
- **Summary**: `benchmarks/results/processed/summary_TIMESTAMP.json`
- **Tables**: `benchmarks/reports/tables/latency_throughput_TIMESTAMP.md`
- **Tables**: `benchmarks/reports/tables/reliability_TIMESTAMP.md`

## Expected Performance

| Adapter | Avg Latency | P95 Latency | Throughput |
|---------|-------------|-------------|------------|
| Redis L1/L2 | < 2ms | < 5ms | > 30K ops/sec |
| Qdrant | 5-15ms | 20-30ms | 5-10K ops/sec |
| Neo4j | 10-25ms | 40-60ms | 2-5K ops/sec |
| Typesense | 3-8ms | 15-25ms | 10-15K ops/sec |

## Troubleshooting

**Connection Failed?**
- Check if backend service is running
- Verify ports are not blocked
- Check logs in benchmark output

**Low Throughput?**
- Ensure localhost testing (not remote)
- Check system resources
- Verify no throttling

**High Error Rate?**
- Check backend logs
- Verify data format compatibility
- Try smaller workload first

## More Info

📖 Full Documentation: `benchmarks/README.md`  
📋 ADR: `docs/ADR/002-storage-performance-benchmarking.md`  
🎯 Implementation: `BENCHMARK_IMPLEMENTATION.md`
