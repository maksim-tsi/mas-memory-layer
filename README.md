# A Hybrid, Multi-Layered Memory System for Advanced Multi-Agent Systems

This repository contains the source code and architectural documentation for a novel, multi-layered memory architecture designed to enable state-of-the-art performance in Multi-Agent Systems (MAS) for complex decision support, with a specific focus on logistics and supply chain management.

This work is being developed in preparation for a submission to the **AIMS 2025 (Artificial Intelligence Models and Systems) Conference**.

---

## 🚧 **Current Status: Phase 1 Complete | Phase 2A 92% Complete | Phase 2B-2D Not Started**

**Overall ADR-003 Completion: ~43%**

**Phase 1 (Storage Adapters):** ✅ 100% Complete - 143/143 tests passing  
**Phase 2A (Memory Tiers):** 🚧 92% Complete - 70/76 tests passing (6 Pydantic validation errors)  
**Phase 2B (LLM Integration):** ❌ 0% Complete - Connectivity verified, production code not started  
**Phase 2C-2D (Lifecycle Engines):** ❌ 0% Complete - Blocked by Phase 2B

**What's Complete**: 
- ✅ Storage infrastructure (5 database adapters, metrics, benchmarks)
- ✅ Memory tier classes (L1-L4 with dual-indexing, bi-temporal model)
- ✅ CIAR scoring system (calculation logic)
- ✅ Data models (Fact, Episode, KnowledgeDocument)
- ✅ LLM provider connectivity (7 models tested across 3 providers)

**What's Missing**: 
- ❌ Multi-provider LLM client (`src/utils/llm_client.py`)
- ❌ Lifecycle engines (Promotion, Consolidation, Distillation)
- ❌ LLM-based fact extraction and episode summarization
- ❌ Circuit breaker pattern for resilience
- ❌ Autonomous memory management (L1→L2→L3→L4 flow)

**See**: 
- [ADR-003 Architecture Review](docs/reports/adr-003-architecture-review.md) for gap analysis
- [DEVLOG 2025-11-12](DEVLOG.md#2025-11-12---multi-provider-llm-engine-status-review--phase-2b-gap-analysis-) for comprehensive LLM engine status

## Developer Updates

### 2025-11-15 — Demo: File Output & Test Coverage

Added developer-facing improvements to the `LLMClient` demo harness:
- `--output-format` (ndjson | json-array)
- `--output-mode` (overwrite | append)
- File output support for NDJSON and JSON arrays, with append/overwrite semantics
- Unit tests verifying NDJSON and JSON-array file behavior were added (`tests/utils/test_llm_client_demo_output.py`) and are passing locally

See `scripts/README.md` and `scripts/llm_client_demo.README.md` for example usage and details.


---

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

## 5. Quick Start

**Current Status**: Storage adapters are production-ready. Memory tier logic and lifecycle engines are not yet implemented (see [ADR-003 Review](docs/reports/adr-003-architecture-review.md)).

### Prerequisites

**System Requirements:**
- Python 3.11+
- PostgreSQL client tools (`psql`) - Required for database setup and migrations
- Docker & Docker Compose (for databases)

**Infrastructure:**
- PostgreSQL, Redis, Neo4j, Qdrant, and Typesense services

**Installing PostgreSQL client:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y postgresql-client

# macOS
brew install postgresql

# Verify installation
psql --version
```

### Installation

## 6. Current Implementation Status

**Overall ADR-003 Completion: ~30%**

### Phase 1: Storage Layer Foundation ✅ Complete (100%)

The foundational storage layer is fully implemented and production-ready:

**Storage Adapters (All 5 Complete):**
- ✅ **Redis Adapter** - High-speed cache for L1/L2 tiers
- ✅ **PostgreSQL Adapter** - Relational storage for L1/L2 tiers
- ✅ **Qdrant Adapter** - Vector embeddings for L3 episodic memory
- ✅ **Neo4j Adapter** - Graph relationships for L3 episodic memory
- ✅ **Typesense Adapter** - Full-text search for L4 semantic memory

**Important Note**: Storage adapters are database clients, not memory tiers. They provide the storage infrastructure but do not implement the intelligent memory management logic specified in [ADR-003](docs/ADR/003-four-layers-memory.md).

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

### Phase 2: Memory Tiers & Lifecycle Engines 🚧 In Progress (~46%)

**Phase 2A: Memory Tier Storage Layer** (92% complete - 70/76 tests passing):

**Memory Tier Classes** (✅ Implemented, 🚧 6 tests failing):
- ✅ **L1: Active Context Tier** - Redis + PostgreSQL dual storage with turn windowing (18/18 tests ✅)
- ✅ **L2: Working Memory Tier** - CIAR-filtered fact storage with access tracking (17/17 tests ✅)
- 🚧 **L3: Episodic Memory Tier** - Qdrant + Neo4j dual-indexing with bi-temporal support (30+ tests, 3 failing)
- 🚧 **L4: Semantic Memory Tier** - Typesense full-text search with provenance tracking (5+ tests, 3 failing)

**Core Innovations** (✅ Implemented in Phase 2A):
- ✅ **CIAR Scoring System** - `(Certainty × Impact) × Age_Decay × Recency_Boost` (312 lines implemented)
- ✅ **Bi-Temporal Data Model** - `factValidFrom`, `factValidTo` for temporal reasoning
- ✅ **Hypergraph Simulation** - Episode nodes with entity relationships in Neo4j
- ✅ **Data Models** - `Fact`, `Episode`, `KnowledgeDocument` with Pydantic validation (341 lines)

**Known Issues (6 failing tests - blocking 100% Phase 2A):**
1. Episode model Pydantic validation (3 tests) - missing required field defaults
2. Context manager cleanup expectations (2 tests) - mock adapter interface
3. KnowledgeDocument validation (1 test) - missing required field

**Phase 2B: LLM Integration & Lifecycle Engines** (0% complete - NOT STARTED):

**Autonomous Lifecycle Engines** (❌ Not implemented - blocks Weeks 5-10):
- ❌ **Promotion Engine (L1→L2)** - LLM-based fact extraction + CIAR scoring
- ❌ **Consolidation Engine (L2→L3)** - Time-windowed clustering + LLM episode summarization
- ❌ **Distillation Engine (L3→L4)** - Multi-episode pattern mining + LLM knowledge synthesis

**LLM Infrastructure** (✅ Connectivity Complete, ❌ Production Integration Missing):
- ✅ **Multi-Provider Strategy** - 7 models across 3 providers (Gemini, Groq, Mistral AI)
  - Google Gemini: 2.5 Flash, 2.0 Flash, 2.5 Flash-Lite (3/3 tested ✅)
  - Groq: Llama 3.1 8B, GPT OSS 120B (2/2 tested ✅)
  - Mistral AI: Large, Small (2/2 tested ✅)
- ✅ **Zero Cost** - All providers offer generous free tiers (14,400+ req/day capacity)
- ✅ **Connectivity Verified** - Test scripts validate all 7 models working
- ✅ **Documentation Complete** - ADR-006 (775 lines) with rate limits, cost analysis, fallback chains
- ✅ **Dependencies Installed** - `google-genai`, `groq`, `mistralai` SDKs in requirements.txt
- ❌ **Production Client Missing** - `src/utils/llm_client.py` does NOT exist
- ❌ **Circuit Breaker Missing** - Resilience pattern not implemented
- ❌ **Fact Extractor Missing** - LLM-based extraction not implemented
- ❌ **Lifecycle Engines Missing** - `src/memory/engines/` directory does NOT exist

**Critical Blocker:** Without the multi-provider LLM client and lifecycle engines, the memory system is **storage-only** and cannot autonomously:
- Extract facts from conversations (Promotion Engine blocked)
- Summarize episodes from fact clusters (Consolidation Engine blocked)  
- Synthesize knowledge patterns (Distillation Engine blocked)

**Architecture Status:**
```
Phase 2A (Weeks 1-3): Memory Tier Storage ✅ 92% COMPLETE (70/76 tests)
                ↓
Phase 2B (Weeks 4-5): LLM Client + Promotion ❌ 0% (CRITICAL BLOCKER)
                ↓
Phase 2C (Weeks 6-8): Consolidation Engine ❌ BLOCKED (needs LLM)
                ↓
Phase 2D (Weeks 9-10): Distillation Engine ❌ BLOCKED (needs LLM)
```

**Quick Start Testing LLM Connectivity:**
```bash
# Test all providers at once
./scripts/test_llm_providers.py

# Or test individually
./scripts/test_gemini.py
./scripts/test_groq.py
./scripts/test_mistral.py
```

**Next Steps (Phase 2B - Critical Path):**
1. Fix 6 failing tests (1-2 days) - Complete Phase 2A to 100%
2. Implement `src/utils/llm_client.py` (3-5 days) - Multi-provider client with fallbacks
3. Implement `src/memory/engines/circuit_breaker.py` (1 day) - Resilience pattern
4. Implement `src/memory/fact_extractor.py` (2-3 days) - LLM extraction with fallback
5. Implement `src/memory/engines/promotion_engine.py` (3-5 days) - L1→L2 pipeline

**Timeline:** 12-18 days to unblock Phase 2C (Consolidation Engine)

**See**: 
- [ADR-006: Free-Tier LLM Provider Strategy](docs/ADR/006-free-tier-llm-strategy.md) for multi-provider architecture
- [LLM Provider Tests](docs/LLM_PROVIDER_TESTS.md) for connectivity testing guide
- [Phase 2 Action Plan](docs/reports/phase-2-action-plan.md) for week-by-week implementation details
- [DEVLOG Entry 2025-11-12](DEVLOG.md) for comprehensive LLM engine status analysis
- ~~[ADR-005: Multi-Tier LLM Provider Strategy](docs/ADR/005-multi-tier-llm-provider-strategy.md)~~ (Superseded - AgentRouter not accessible)

**Estimated Remaining Effort**: 4-6 weeks for Phase 2B-2D (LLM integration + lifecycle engines)

### Phase 3: Agent Integration ❌ Not Started (0%)

LangGraph agent implementation with full memory system integration:
- Multi-agent coordination patterns
- Personal vs. shared state management
- Real-time collaboration workspace
- Memory-augmented reasoning

### Phase 4: Evaluation Framework ❌ Not Started (0%)

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
```

### 3. Environment Bootstrap Checklist (Multi-Host Safe)

1. **Identify where you are executing.** Before running any project task, confirm the host type so path assumptions are correct:
  ```bash
  uname -a
  hostname
  pwd
  ```
  - macOS local checkout → expect `Darwin` and a path such as `/Users/<name>/Documents/code/mas-memory-layer`.
  - Remote Ubuntu over SSH → expect `Linux` plus `/home/<user>/code/mas-memory-layer`.
  - Local Ubuntu desktop/RDP → expect `Linux` with `/home/<user>/...` but no SSH hostname suffix.

2. **Create/refresh the virtual environment using a relative path** so the same instructions work on every host:
  ```bash
  python3 -m venv .venv
  ```

3. **Install primary dependencies explicitly via the venv interpreter.** Avoid `pip` from the system path.
  ```bash
  ./.venv/bin/pip install -r requirements.txt
  ```

4. **Install test and tooling dependencies whenever you plan to run any test suite.**
  ```bash
  ./.venv/bin/pip install -r requirements-test.txt
  ```

5. **Verify the interpreter being used by automation.** The command below must print the absolute path to `.venv/bin/python` on the current host.
  ```bash
  ./.venv/bin/python -c "import sys; print(sys.executable)"
  ```

6. **Run smoke validations before heavy workflows.**
  ```bash
  ./.venv/bin/python scripts/test_llm_providers.py --help
  ./scripts/run_smoke_tests.sh --summary
  ```

> **Why this sequence?** Contributors regularly switch between a remote Ubuntu VM, a macOS laptop, and containerised CI. Using relative paths plus the explicit interpreter commands prevents accidental invocation of a different Python installation that might live outside the repo.

For more detailed troubleshooting guidance, see [`docs/environment-guide.md`](docs/environment-guide.md).
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

**Note**: The unified memory tier interface is not yet implemented (Phase 2, 0% complete).

Once Phase 2 is complete, the system will provide intelligent memory management:

```python
# Future API (Phase 2 - Not Yet Implemented)
# memory = MemoryOrchestrator(
#     active_tier=ActiveContextTier(...),
#     working_tier=WorkingMemoryTier(...),
#     episodic_tier=EpisodicMemoryTier(...),
#     semantic_tier=SemanticMemoryTier(...),
#     promotion_engine=PromotionEngine(),
#     consolidation_engine=ConsolidationEngine(),
#     distillation_engine=DistillationEngine()
# )

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

## 9. Current Status & Roadmap

### What's Complete ✅

**Phase 1: Storage Foundation (100%)**
- Production-ready storage adapters for all 5 backends
- Comprehensive metrics and observability (A+ grade)
- Extensive test coverage (83% overall)
- Performance benchmarking suite
- Complete documentation

### What's Next 🚧

**Phase 2A: Memory Tier Classes (2-3 weeks)**
- Implement `ActiveContextTier`, `WorkingMemoryTier`, `EpisodicMemoryTier`, `SemanticMemoryTier`
- Add tier-specific logic and coordination

**Phase 2B: CIAR Scoring & Promotion (1-2 weeks)**
- Implement CIAR scoring algorithm (core research contribution)
- Build LLM-based fact extraction with circuit breaker fallback
- Create L1→L2 promotion engine

**Phase 2C: Consolidation Engine (2-3 weeks)**
- Time-windowed fact clustering
- LLM-based episode summarization
- Dual indexing (Qdrant + Neo4j)
- Bi-temporal property graph model

**Phase 2D: Distillation Engine (1-2 weeks)**
- Pattern mining across episodes
- LLM-based knowledge synthesis
- L3→L4 distillation automation

**Phase 2E: Memory Orchestrator (1 week)**
- Integrate all tiers and engines
- Unified query interface
- Lifecycle management

**Phase 3: Agent Integration (2-3 weeks)**
- LangGraph agent implementation
- Multi-agent coordination
- GoodAI LTM benchmark integration

**See [ADR-003 Architecture Review](docs/reports/adr-003-architecture-review.md)** for complete gap analysis and detailed implementation roadmap.

## 10. Contributing

Contributions and feedback are welcome. Please open an issue to discuss any proposed changes or enhancements.