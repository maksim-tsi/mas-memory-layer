# A Hybrid, Multi-Layered Memory System for Advanced Multi-Agent Systems

This repository contains the source code and architectural documentation for a novel, multi-layered memory architecture designed to enable state-of-the-art performance in Multi-Agent Systems (MAS) for complex decision support, with a specific focus on logistics and supply chain management.

This work is being developed in preparation for a submission to the **AIMS 2025 (Artificial Intelligence Models and Systems) Conference**.

## 1. Abstract & Core Problem

Standard Large Language Model (LLM) agents are often limited by their stateless nature and finite context windows. In complex, dynamic domains like supply chain management, these limitations prevent agents from performing sophisticated, long-term reasoning and effective real-time collaboration.

This project addresses this critical gap by introducing a hybrid memory architecture that provides agents with a cognitive framework inspired by human memory. The system cleanly separates high-speed, volatile "working memory" from a durable, structured "long-term memory," enabling a group of specialized agents to reason individually, collaborate seamlessly, and learn from their collective experience.

## 2. Core Architectural Principles

The design of this system is founded on five core principles that collectively enable advanced agentic capabilities:

1.  **Computational State Persistence:** Memory serves as an active computational workspace, allowing agents to persist and manipulate intermediate states for complex, multi-step reasoning.
2.  **Collaborative Workspace:** The system provides a shared, negotiable state space where multiple agents can jointly construct, modify, and agree upon solutions in real-time.
3.  **Structured Reasoning for High-Stakes Reliability:** It enforces structured, auditable reasoning schemas (Schema-Guided Reasoning) to ensure safety, compliance, and predictable performance in mission-critical domains.
4.  **Promotion via Calculated Significance:** An intelligent information lifecycle engine promotes information from private to shared memory only when its calculated significance (based on certainty, impact, and criticality) exceeds a dynamic threshold.
5.  **Archiving via Knowledge Distillation:** The system actively learns by "distilling" resolved events from shared memory into high-value assets (patterns, metrics, relationships) that are stored in a specialized, persistent knowledge layer for future strategic use.

## 3. System Architecture

The architecture is composed of two primary layers, unified by a single access facade:

![System Architecture Diagram](docs/architecture.png)
*(Self-referential note: It would be best to generate this Mermaid diagram as an image and place it in a `docs` folder)*

```mermaid
graph TD
    subgraph "Multi-Agent System (LangGraph Orchestrator)"
        A1[Vessel Agent]
        A2[Port Agent]
        A3[Customs Agent]
    end

    subgraph "Unified Memory System (Single Facade)"
        subgraph "Operating Memory Layer (Redis)"
            direction LR
            P[Personal Scratchpads]
            SWS[Shared Workspace]
        end

        subgraph "Persistent Knowledge Layer"
            direction LR
            VEC[(Qdrant)]
            GPH[(Neo4j)]
            SRCH[(Meilisearch)]
            REL[(PostgreSQL)]
        end
    end

    A1 & A2 & A3 -- "Unified API" --> Unified Memory System

```

### Components

*   **Operating Memory Layer (Redis):** Serves as the high-speed, volatile working memory.
    *   **Personal Scratchpads (Redis Hashes):** Private, isolated state for each agent.
    *   **Shared Workspace (Redis Hashes & Pub/Sub):** The real-time "negotiation table" for inter-agent collaboration.

*   **Persistent Knowledge Layer (Specialized Databases):** The system's long-term memory, where distilled knowledge is archived.
    *   **Qdrant (Vector Store):** Stores experiential patterns for semantic similarity search.
    *   **Neo4j (Graph Store):** Stores entities and relationships for causal and relational analysis.
    *   **Meilisearch (Search Store):** Stores operational knowledge (e.g., protocols, documents) for fast full-text search.
    *   **PostgreSQL (Relational Store):** Stores structured metrics and auditable event logs.

*   **Unified Memory System (`UnifiedMemorySystem`):** A single, clean facade that provides agents with a unified interface for all memory operations, intelligently routing requests to the appropriate underlying layer.

## 4. Evaluation & Benchmarking

To rigorously validate the performance of our hybrid memory architecture, we employ a multi-faceted benchmarking strategy at both the storage and system levels.

### 4.1 Storage Layer Performance Benchmarks ✅ Implemented

We have implemented a comprehensive micro-benchmark suite that measures the performance characteristics of all storage adapters in isolation. This validates our architectural hypothesis that specialized storage backends provide superior performance for their designated use cases.

**Benchmark Approach:**
- **Synthetic Workload Generation**: Realistic operation patterns matching production memory access (40% L1 cache, 30% L2 cache, 30% L3 specialized storage)
- **Direct Metrics Collection**: Leverages existing metrics infrastructure with no additional instrumentation overhead
- **Publication-Ready Output**: Generates markdown tables for research papers and reports

**Measured Metrics:**
- Latency distributions (average, P50, P95, P99)
- Throughput (operations per second)
- Reliability (success rates, error rates)
- Backend-specific performance characteristics

**Quick Start:**
```bash
# Run default benchmark (10,000 operations)
source .venv/bin/activate
python scripts/run_storage_benchmark.py

# Run quick test (1,000 operations)
python scripts/run_storage_benchmark.py run --size 1000

# Analyze results and generate tables
python scripts/run_storage_benchmark.py analyze
```

See [`benchmarks/README.md`](benchmarks/README.md) for complete documentation and [`docs/ADR/002-storage-performance-benchmarking.md`](docs/ADR/002-storage-performance-benchmarking.md) for architectural rationale.

### 4.2 System-Level Benchmarks 🚧 Planned

For end-to-end system evaluation, we will use the **GoodAI LTM (Long-Term Memory) Benchmark**, which tests temporal dynamics and information lifecycle management across long-running conversations.

**Evaluation Strategy:**

Three distinct system configurations will be compared:

1. **Full Hybrid System:** Our complete architecture utilizing both Operating Memory (L1/L2) and Persistent Knowledge Layer (L3) with intelligent consolidation.
2. **Standard RAG Baseline:** A conventional single-layer RAG agent using only vector search without tiered memory management.
3. **Full-Context Baseline:** A naive approach that passes the entire conversation history to the LLM on every turn, establishing an upper bound for accuracy but demonstrating severe efficiency limitations.

**Measured Dimensions:**
- **Functional Correctness:** Accuracy in retrieving and synthesizing information from long conversation histories
- **Operational Efficiency:** Latency, token cost, and cache hit rates across different memory span sizes (32k and 120k tokens)

### Documentation

Comprehensive documentation for our benchmark evaluation approach is available in the `docs/` directory:

- **Evaluation Discussion & Strategy:** [`docs/ADR/discussion-evaluation.md`](docs/ADR/discussion-evaluation.md) - Detailed analysis of benchmark selection rationale and our phased implementation plan
- **Use Case Specifications:**
  - [`docs/uc-01.md`](docs/uc-01.md) - GoodAI LTM Benchmark with Full Hybrid System
  - [`docs/uc-02.md`](docs/uc-02.md) - GoodAI LTM Benchmark with Standard RAG Baseline
  - [`docs/uc-03.md`](docs/uc-03.md) - GoodAI LTM Benchmark with Full-Context Baseline
- **Sequence Diagrams:**
  - [`docs/sd-01.md`](docs/sd-01.md) - Full System execution flow
  - [`docs/sd-02.md`](docs/sd-02.md) - Standard RAG execution flow
  - [`docs/sd-03.md`](docs/sd-03.md) - Full-Context execution flow
- **Data Dictionaries:**
  - [`docs/dd-01.md`](docs/dd-01.md) - Full System data structures
  - [`docs/dd-02.md`](docs/dd-02.md) - Standard RAG data structures
  - [`docs/dd-03.md`](docs/dd-03.md) - Full-Context data structures

These documents provide detailed specifications of the experimental setup, component interactions, data flows, and success criteria for each benchmark configuration.

## 5. Code Structure

The repository is organized into a modular and decoupled structure:

```
.
├── src/
│   ├── storage/              # Storage layer with adapter pattern
│   │   ├── base.py          # Base adapter interface
│   │   ├── redis_adapter.py     # Redis (L1/L2 working memory)
│   │   ├── qdrant_adapter.py    # Qdrant (vector embeddings)
│   │   ├── neo4j_adapter.py     # Neo4j (graph relationships)
│   │   ├── typesense_adapter.py # Typesense (full-text search)
│   │   ├── postgres_adapter.py  # PostgreSQL (structured data)
│   │   └── metrics/         # Metrics collection & observability
│   │       ├── collector.py     # Main metrics collector
│   │       ├── timer.py         # Operation timing
│   │       ├── storage.py       # Metrics storage
│   │       ├── aggregator.py    # Statistics aggregation
│   │       └── exporters.py     # Export to JSON/CSV/Prometheus
│   ├── memory/               # Memory layer components (planned)
│   ├── agents/               # Agent implementations (planned)
│   └── evaluation/           # Benchmark evaluation code (planned)
|
├── tests/
│   ├── storage/              # Storage layer tests
│   │   ├── test_base.py         # Base adapter tests
│   │   ├── test_metrics.py      # Metrics unit tests
│   │   ├── test_*_metrics.py    # Adapter integration tests
│   │   └── test_*.py            # Individual adapter tests
│   └── benchmarks/           # Performance benchmarks
│       ├── bench_redis_adapter.py
│       ├── bench_storage_adapters.py  # Multi-adapter benchmark runner
│       ├── workload_generator.py      # Synthetic workload generator
│       └── results_analyzer.py        # Results analysis & tables
|
├── benchmarks/
│   ├── configs/
│   │   ├── workload_small.yaml         # 1K ops benchmark config
│   │   ├── workload_medium.yaml        # 10K ops (default)
│   │   └── workload_large.yaml         # 100K ops stress test
│   ├── results/
│   │   ├── raw/                        # JSON metrics output
│   │   └── processed/                  # Summary statistics
│   ├── reports/
│   │   ├── tables/                     # Publication-ready tables
│   │   └── figures/                    # Optional visualizations
│   ├── README.md                       # Benchmark documentation
│   └── QUICK_REFERENCE.md              # Quick command reference
|
├── docs/
│   ├── ADR/
│   │   ├── discussion-evaluation.md    # System benchmark strategy
│   │   ├── 001-benchmarking-strategy.md
│   │   └── 002-storage-performance-benchmarking.md  # Storage micro-benchmarks
│   ├── IAC/
│   │   ├── database-setup.md           # Infrastructure setup
│   │   └── connectivity-cheatsheet.md
│   ├── reports/
│   │   ├── code-review-priority-*.md   # Code reviews
│   │   ├── metrics-*.md                # Metrics documentation
│   │   └── implementation-*.md         # Progress reports
│   ├── specs/
│   │   └── spec-phase1-storage-layer.md
│   ├── uc-*.md                         # Use case specifications
│   ├── sd-*.md                         # Sequence diagrams
│   ├── dd-*.md                         # Data dictionaries
│   └── metrics_usage.md                # Metrics usage guide
|
├── examples/
│   ├── logistics_simulation.py    # Demo script
│   └── metrics_demo.py            # Metrics demonstration
|
├── scripts/
│   ├── setup_database.sh          # Database initialization
│   ├── run_tests.sh               # Test runner
│   ├── run_smoke_tests.sh         # Connectivity tests
│   ├── demo_health_check.py       # Health check demo
│   ├── run_storage_benchmark.py   # Storage performance benchmarks
│   └── verify_metrics_implementation.py
|
├── migrations/
│   ├── 001_active_context.sql     # Database migrations
│   └── README.md
|
├── BENCHMARK_IMPLEMENTATION.md   # Storage benchmark suite summary
├── DEVLOG.md                     # Development log & progress tracking
└── README.md                     # This file
```

## 6. Current Implementation Status

### Phase 1: Storage Layer ✅ Complete

The foundational storage layer is fully implemented and production-ready:

**Storage Adapters (All 4 Complete):**
- ✅ **Redis Adapter** - High-speed working memory (L1/L2)
- ✅ **Qdrant Adapter** - Vector embeddings & semantic search (L3)
- ✅ **Neo4j Adapter** - Graph relationships & entity storage (L4)
- ✅ **Typesense Adapter** - Full-text search & knowledge retrieval (L5)

**Features:**
- ✅ Unified adapter interface with consistent API
- ✅ Async/await support throughout
- ✅ Batch operations for high-performance scenarios
- ✅ Health check endpoints for monitoring
- ✅ **Comprehensive metrics & observability** (Grade: A+ 100/100)
  - Operation timing and latency tracking (avg, min, max, percentiles)
  - Success/failure rates with error tracking
  - Throughput metrics (ops/sec, bytes/sec)
  - Backend-specific metrics for each adapter
  - Export to JSON, CSV, Prometheus, Markdown formats
- ✅ Extensive test coverage (20+ tests passing)
- ✅ Production-ready error handling
- ✅ Complete documentation

**Metrics & Observability:**

All storage adapters are fully instrumented with comprehensive metrics collection:

```python
# Enable metrics on any adapter
config = {
    'uri': 'bolt://localhost:7687',
    'metrics': {
        'enabled': True,
        'max_history': 1000,
        'percentiles': [50, 95, 99]
    }
}

adapter = Neo4jAdapter(config)

# Metrics collected automatically
await adapter.store(data)
await adapter.search(query)

# Get detailed metrics
metrics = await adapter.get_metrics()
print(f"Average latency: {metrics['operations']['store']['avg_latency_ms']}ms")
print(f"Success rate: {metrics['operations']['store']['success_rate']*100}%")
print(f"P95 latency: {metrics['operations']['store']['p95_latency_ms']}ms")

# Export for monitoring systems
prometheus_metrics = await adapter.export_metrics('prometheus')
```

See [`docs/metrics_usage.md`](docs/metrics_usage.md) for complete metrics documentation.

### Phase 2: Memory Layer 🚧 Planned

Next phase will implement the intelligent memory management layer:
- Personal agent scratchpads
- Shared workspace for collaboration
- Information lifecycle management (CIAR/EPDL)
- Knowledge distillation and consolidation

### Phase 3: Evaluation Framework 🚧 Planned

Implementation of GoodAI LTM Benchmark for validation:
- Full hybrid system evaluation
- Baseline comparisons (RAG, full-context)
- Performance metrics and analysis

## 7. Getting Started

### Prerequisites

*   Python 3.11+ (recommended)
*   Access to infrastructure services (PostgreSQL, Redis, Qdrant, Neo4j, Typesense)
*   Python virtual environment (venv recommended - see [`docs/python-environment-setup.md`](docs/python-environment-setup.md))

### 1. Set Up Backend Services

This project requires Redis, PostgreSQL, Qdrant, Neo4j, and Meilisearch. 

**Important:** This project uses a dedicated PostgreSQL database named `mas_memory` to ensure complete isolation from other projects. See [`docs/IAC/database-setup.md`](docs/IAC/database-setup.md) for detailed setup instructions.

```bash
# Create the dedicated PostgreSQL database
./scripts/setup_database.sh

# Start all required database services (if using Docker)
docker-compose up -d
```

### 2. Create Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip
```

See [`docs/python-environment-setup.md`](docs/python-environment-setup.md) for detailed setup instructions.

### 3. Install Dependencies

Install the required Python packages from `requirements.txt`.

```bash
pip install -r requirements.txt

# Optional: Install test dependencies
pip install -r requirements-test.txt
```

### 4. Run Tests

Verify the implementation with the comprehensive test suite:

```bash
# Run all storage layer tests
./scripts/run_tests.sh

# Run specific test categories
pytest tests/storage/test_base.py -v           # Base adapter tests
pytest tests/storage/test_metrics.py -v        # Metrics tests
pytest tests/storage/test_redis_metrics.py -v  # Redis integration tests

# Run with coverage
pytest tests/storage/ --cov=src/storage --cov-report=html
```

### 5. Verify Infrastructure & Health

```bash
# Run smoke tests to verify all services are accessible
./scripts/run_smoke_tests.sh --summary

# Check health of all adapters
python scripts/demo_health_check.py
```

### 6. Explore Metrics & Monitoring

```bash
# See metrics in action
python examples/metrics_demo.py

# Verify metrics implementation
python scripts/verify_metrics_implementation.py
```

### 7. Run Storage Performance Benchmarks

Validate storage layer performance with comprehensive micro-benchmarks:

```bash
# Run default benchmark (10K operations, ~5-10 minutes)
python scripts/run_storage_benchmark.py

# Quick test (1K operations, ~1-2 minutes)
python scripts/run_storage_benchmark.py run --size 1000

# Stress test (100K operations, ~30-60 minutes)
python scripts/run_storage_benchmark.py run --size 100000

# Benchmark specific adapters
python scripts/run_storage_benchmark.py run --adapters redis_l1 redis_l2

# Analyze results and generate publication tables
python scripts/run_storage_benchmark.py analyze
```

Results are saved to:
- **Raw metrics**: `benchmarks/results/raw/benchmark_TIMESTAMP.json`
- **Tables**: `benchmarks/reports/tables/latency_throughput_TIMESTAMP.md`
- **Summary**: `benchmarks/results/processed/summary_TIMESTAMP.json`

See [`benchmarks/README.md`](benchmarks/README.md) and [`benchmarks/QUICK_REFERENCE.md`](benchmarks/QUICK_REFERENCE.md) for complete documentation.

### 8. Run the Demonstration (Coming Soon)

The `examples/logistics_simulation.py` script will provide a concrete demonstration of the memory system in action, simulating the collaborative resolution of a supply chain disruption.

```bash
# Coming in Phase 2
# python examples/logistics_simulation.py
```

## 8. How to Use the Storage Layer

The storage layer provides a clean, unified interface for all data persistence needs:

```python
from src.storage.redis_adapter import RedisAdapter
from src.storage.qdrant_adapter import QdrantAdapter
from src.storage.neo4j_adapter import Neo4jAdapter
from src.storage.typesense_adapter import TypesenseAdapter

# Initialize adapters with metrics enabled
redis_config = {
    'host': 'localhost',
    'port': 6379,
    'metrics': {'enabled': True}
}
redis = RedisAdapter(redis_config)
await redis.connect()

# Store data
doc_id = await redis.store({'key': 'session:123', 'data': {'state': 'active'}})

# Retrieve data
data = await redis.retrieve(doc_id)

# Search/query
results = await redis.search({'pattern': 'session:*'})

# Batch operations for performance
ids = await redis.store_batch([doc1, doc2, doc3])
items = await redis.retrieve_batch(ids)

# Health monitoring
health = await redis.health_check()
print(f"Status: {health['status']}, Latency: {health['latency_ms']}ms")

# Get comprehensive metrics
metrics = await redis.get_metrics()
print(f"Operations: {metrics['operations']}")
print(f"Backend stats: {metrics.get('backend_specific', {})}")

# Export for monitoring systems
await redis.export_metrics('prometheus')
await redis.export_metrics('json')
```

**All adapters share the same interface:**
- `connect()` / `disconnect()` - Connection management
- `store(data)` - Store a single item
- `retrieve(id)` - Retrieve by ID
- `search(query)` - Query/search operations
- `delete(id)` - Delete an item
- `store_batch(items)` - Batch store
- `retrieve_batch(ids)` - Batch retrieve
- `delete_batch(ids)` - Batch delete
- `health_check()` - Health status
- `get_metrics()` - Retrieve metrics
- `export_metrics(format)` - Export metrics

## 9. How to Use (Future: Unified Memory System)

Once Phase 2 is complete, the unified memory system will provide a higher-level abstraction:

```python
# Future API (Phase 2)
# memory = UnifiedMemorySystem(redis_client, knowledge_manager)

# Agent uses personal (short-term) memory
# state = memory.get_personal_state(agent_id)
# state.scratchpad["congestion_level"] = 0.91
# memory.update_personal_state(state)

# Agent queries persistent (long-term) knowledge
# past_patterns = memory.query_knowledge(
#     store_type="vector",
#     query_text="Find similar congestion events"
# )
```

## 10. Development Guidelines

### Contributing to this Project

All development happens on the `dev` branch. When contributing:

1. **Track Your Work**: Update [`DEVLOG.md`](DEVLOG.md) before committing significant changes
   - Include date, summary, files changed, and status
   - Reference the commit hash after pushing
   - Follow the entry template in DEVLOG.md

2. **Commit Convention**: Use conventional commit messages:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation
   - `test:` - Tests
   - `refactor:` - Code refactoring

3. **Branch Strategy**:
   - Work on `dev` branch
   - Keep `main` stable
   - Create feature branches from `dev` for larger features

4. **Documentation**: Keep docs in sync with code changes
   - Update relevant ADRs if architecture changes
   - Update implementation plan if timeline shifts
   - Add entries to DEVLOG.md for tracking progress

See [`DEVLOG.md`](DEVLOG.md) for complete development history and progress tracking.

## 9. Future Work

This architecture provides a robust foundation for building highly capable multi-agent systems. Future research will focus on:

*   **Implementing the CIAR/EPDL Lifecycle Engine:** Building the intelligent logic for automatic information promotion and knowledge distillation.
*   **Integration with LangGraph:** Integrating this memory system as the backend for a stateful LangGraph orchestrator.
*   **Advanced Benchmarking:** Evaluating the system's performance on standardized logistics and supply chain management benchmarks.

Contributions and feedback are welcome. Please open an issue to discuss any proposed changes or enhancements.