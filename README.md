# A Hybrid, Multi-Layered Memory System for Advanced Multi-Agent Systems

This repository contains the source code and architectural documentation for a novel, multi-layered memory architecture designed to enable state-of-the-art performance in Multi-Agent Systems (MAS) for complex decision support, with a specific focus on logistics and supply chain management.

This work is being developed in preparation for a submission to the **AIMS 2025 (Artificial Intelligence Models and Systems) Conference**.

---

## 🚀 **Current Status: Phase 2 Complete | Phase 3 Week 3 Complete — Agent Tools + Integration Tests Ready**

**Overall ADR-003 Completion:** Functional implementation ~95% (tiers + lifecycle engines + Redis infrastructure + agent tools + integration test infrastructure complete); Phase 3 Week 4-6 in progress.

**Phase 1 (Storage Adapters):** ✅ 100% Complete — 143/143 tests passing  
**Phase 2 (Memory Tiers + Lifecycle Engines):** ✅ Complete — 441/445 tests passing (86% coverage)  
**Phase 3 Week 1 (Redis Infrastructure):** ✅ Complete — NamespaceManager, Lua scripts, Lifecycle Streams, Recovery triggers  
**Phase 3 Week 2 (UnifiedMemorySystem + Agent Tools):** ✅ Complete — Enhanced memory system, MASToolRuntime, unified tools (47/47 tests passing)  
**Phase 3 Week 3 (CIAR Tools + Tier Tools + Integration):** ✅ Complete — CIAR tools, tier-specific tools, synthesis tool, integration test infrastructure (6/6 connectivity tests passing)  
**Phase 3 Week 4-6 (Agent Framework + LangGraph):** 🚧 In Progress — BaseAgent, MemoryAgent, LangGraph orchestration

**Acceptance Criteria (Readiness Gates):**
- Coverage ≥80% per component and overall
- <2s p95 latency for lifecycle batches (promotion/consolidation/distillation) at current stage
- Real-storage end-to-end validation across Redis, PostgreSQL, Qdrant, Neo4j, Typesense
- Gemini API connectivity re-test after key refresh

**What's Complete**: 
- ✅ Storage infrastructure (5 database adapters, metrics, benchmarks)
- ✅ Memory tier classes (L1–L4 with dual-indexing, bi-temporal model)
- ✅ CIAR scoring system (calculation logic + agent tools)
- ✅ Data models (Fact, Episode, KnowledgeDocument, ContextBlock, SearchWeights)
- ✅ Multi-provider LLM client with provider wrappers and demos
- ✅ Lifecycle engines (Promotion, Consolidation, Distillation) + Knowledge Synthesizer
- ✅ Phase 3 research validation (5 research topics validated)
- ✅ **Phase 3 Week 1**: Redis infrastructure (NamespaceManager with Hash Tags, Lua scripts, Lifecycle Streams, Recovery triggers)
- ✅ **Phase 3 Week 2**: Enhanced UnifiedMemorySystem (hybrid query, lifecycle orchestration), MASToolRuntime wrapper, unified agent tools (memory_query, get_context_block, memory_store)
- ✅ **Phase 3 Week 3**: CIAR tools (calculate, filter, explain), tier-specific tools (L2 tsvector search, L3 template-based Cypher, L4 Typesense), knowledge synthesis tool, integration test infrastructure with live cluster connectivity

**What's Next**: 
- 🚧 **Phase 3 Week 4**: BaseAgent interface + MemoryAgent (UC-01)
- 🔧 **Phase 3 Week 5**: RAGAgent + FullContextAgent variants
- 🔧 **Phase 3 Week 6**: LangGraph orchestration + FastAPI wrapper + E2E integration tests
- 🚧 Full lifecycle integration tests (L1→L4) with real LLM calls + GoodAI benchmark runs

**See**: 
- [Phase 3 Specification v2.0](docs/specs/spec-phase3-agent-integration.md) for validated architecture
- [Phase 3 Implementation Plan](docs/plan/phase3-implementation-plan-2025-12-27.md) for 6-week roadmap
- [Research Validation](docs/research/README.md) for RT1-RT5 findings
- [ADR-003 Architecture Review](docs/reports/adr-003-architecture-review.md) for gap analysis

### 2025-12-28 — Changelog (Phase 3 Week 3 Complete)
- **CIAR Agent Tools**: Implemented 3 CIAR tools (`ciar_calculate`, `ciar_filter`, `ciar_explain`) with Pydantic schemas and comprehensive unit tests.
- **Tier-Specific Tools**: Created `l2_search_facts` (PostgreSQL tsvector), `l3_query_graph` (template-based Cypher), `l4_search_knowledge` (Typesense) for granular tier access.
- **Graph Query Templates**: 6 logistics-focused Neo4j templates with temporal validity enforcement (`factValidTo IS NULL`).
- **PostgreSQL Migration 002**: Applied tsvector column + GIN index to live cluster; schema verification fixture for fail-fast testing.
- **Integration Test Infrastructure**: 5 adapter fixtures connecting to 3-node research cluster, surgical cleanup with namespace isolation, all 6 connectivity tests passing.
- **Knowledge Synthesis Tool**: `synthesize_knowledge` wrapping KnowledgeSynthesizer with conflict detection.

### 2025-12-28 — Changelog (Phase 3 Week 2 Complete)
- **Enhanced UnifiedMemorySystem**: Refactored to inject L1-L4 tiers + lifecycle engines; added hybrid `query_memory()` with configurable weights, `get_context_block()` for prompt assembly, and lifecycle cycle methods.
- **MAS Runtime Framework**: Created `MASToolRuntime` wrapper around LangChain's ToolRuntime with 20+ helpers for session/user/context access; implemented `MASContext` dataclass for immutable configuration.
- **Unified Agent Tools**: Implemented 3 LangChain-compatible tools (`memory_query`, `get_context_block`, `memory_store`) using `@tool` decorator with ToolRuntime parameter (hidden from LLM per ADR-007).
- **Data Models**: Added `ContextBlock` (prompt context assembly), `SearchWeights` (hybrid search config with validation).
- **Comprehensive Tests**: 47/47 tests passing (26 runtime tests + 21 tool tests) covering all new components.

### 2025-12-27 — Changelog (Status Alignment)
- Implemented Promotion, Consolidation, and Distillation engines with Knowledge Synthesizer; 396/396 tests passing.
- Aligned specs and DEVLOG with Pydantic v2 models and lifecycle workflows.
- Added domain configuration for container logistics; metrics timers updated for manual control.

### Next Validation Checklist (Mandatory Before Release)
- Run full L1→L4 pipeline against real backends (Redis, PostgreSQL, Qdrant, Neo4j, Typesense) with metrics enabled.
- Measure lifecycle batches against <200ms p95 target; capture metrics export for evidence.
- Confirm coverage ≥80% overall and per component (storage + memory + engines); regenerate htmlcov.
- Refresh Gemini API key and re-run provider connectivity scripts; record outcomes in [docs/LLM_PROVIDER_TEST_RESULTS.md](docs/LLM_PROVIDER_TEST_RESULTS.md).

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

**Current Status**: Storage adapters, memory tiers, and lifecycle engines are implemented with tests passing; readiness is gated by performance/coverage targets and real-storage end-to-end validation (see [ADR-003 Review](docs/reports/adr-003-architecture-review.md)).

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

**Overall ADR-003 Completion:** Functional implementation ~80%; readiness gated by acceptance criteria (coverage, performance, real-storage E2E).

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

### Phase 2: Memory Tiers & Lifecycle Engines ✅ Implemented (Validation Pending)

**Memory Tiers & Engines:**
- ✅ **L1: Active Context Tier** — Redis + PostgreSQL dual storage with turn windowing
- ✅ **L2: Working Memory Tier** — CIAR-filtered fact storage with access tracking
- ✅ **L3: Episodic Memory Tier** — Qdrant + Neo4j dual-indexing with bi-temporal support
- ✅ **L4: Semantic Memory Tier** — Typesense full-text search with provenance tracking
- ✅ **Lifecycle Engines:** Promotion (L1→L2), Consolidation (L2→L3), Distillation (L3→L4), Knowledge Synthesizer (query-time)
- ✅ **Testing:** 396/396 tests passing across tiers and engines (see [DEVLOG 2025-12-27](DEVLOG.md#2025-12-27---phase-2d-distillation-engine--knowledge-synthesizer-completion-))

**Core Innovations:**
- CIAR Scoring System `(Certainty × Impact) × Age_Decay × Recency_Boost`
- Bi-Temporal Data Model (`factValidFrom`, `factValidTo`)
- Dual indexing: Qdrant vectors + Neo4j graph linkage
- Metadata-first knowledge synthesis with conflict transparency and TTL caching

**Pending Validation (Readiness Gates):**
- Coverage confirmation to ≥80% per component and overall (htmlcov shows remaining adapter gaps)
- <2s p95 lifecycle batch latency measured against real storage backends (current stage target)
- Full L1→L4 end-to-end pipeline on Redis/PostgreSQL/Qdrant/Neo4j/Typesense
- Gemini API key refresh and connectivity re-test (see [LLM Provider Results](docs/LLM_PROVIDER_TEST_RESULTS.md))

**LLM Infrastructure:**
- Multi-provider `LLMClient` with Gemini, Groq, and Mistral providers; connectivity scripts in `scripts/test_*`. Gemini currently blocked by API key validity; Groq/Mistral passing.

**See**: 
- [ADR-006: Free-Tier LLM Provider Strategy](docs/ADR/006-free-tier-llm-strategy.md)
- [Phase 2 Engine Plan](docs/plan/implementation-plan-2025-12-27-phase2-engines.md)
- [LLM Provider Test Results](docs/LLM_PROVIDER_TEST_RESULTS.md)

### Phase 3: Agent Integration 🔬 Research Validated (Ready for Implementation)

LangGraph agent implementation with full memory system integration:
- ✅ **Research Validated**: 5 critical architectural decisions validated (RT1-RT5)
- 🚀 **Implementation Plan**: 6-week roadmap with weekly deliverables
- 🔧 Hash Tag namespaces for Redis Cluster compatibility
- 🔧 Lua scripts for atomic state transitions (replacing WATCH)
- 🔧 CIAR-aware tools with Reasoning-First schemas
- 🔧 Tool Message injection for context block delivery
- 🔧 FastAPI agent wrapper for benchmark integration

**Key Validated Decisions:**
- Redis: Hash Tags MANDATORY (`{scope:id}:resource`) — CROSSSLOT prevention
- Concurrency: Lua scripts over WATCH-based optimistic locking
- Context: Tool Message injection (not system prompt) for cache preservation
- CIAR: Reasoning-First schemas for constrained decoding

**Documentation:**
- [Phase 3 Specification v2.0](docs/specs/spec-phase3-agent-integration.md)
- [Phase 3 Implementation Plan](docs/plan/phase3-implementation-plan-2025-12-27.md)
- [Research Validation](docs/research/README.md)

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

**Phase 2: Memory Tiers + Lifecycle Engines (100%)**
- Memory tier classes (L1–L4 with dual-indexing, bi-temporal model)
- CIAR scoring system (calculation logic)
- Data models (Fact, Episode, KnowledgeDocument)
- Lifecycle engines: Promotion, Consolidation, Distillation
- Knowledge Synthesizer for L3→L4 distillation
- 441/445 tests passing (86% coverage)

**Phase 3 Research: Validated (100%)**
- RT1: LangGraph tool injection patterns → InjectedState, state reducers
- RT2: Gemini structured output → Reasoning-First schemas
- RT3: Redis namespace isolation → Hash Tags MANDATORY
- RT4: Hybrid memory context injection → Tool Message pattern
- RT5: CIAR decision-making impact → 18-48% improvement validated

### What's Next 🚧

**Phase 3: Agent Integration (6 weeks)**
- Week 1: Namespace Manager + Lua Scripts + Redis Streams
- Week 2: Enhanced UnifiedMemorySystem + Unified Tools
- Week 3: CIAR Tools + Granular Tier Tools + Synthesis Tools
- Week 4: BaseAgent + MemoryAgent + Baseline Agents
- Week 5: LangGraph Orchestrator + FastAPI Agent Wrapper
- Week 6: End-to-End Integration Tests + Documentation

**Phase 4: Evaluation Framework (2-3 weeks)**
- GoodAI LTM Benchmark integration
- Full hybrid system evaluation
- Baseline comparisons (RAG, full-context)
- Performance metrics and analysis

**See [Phase 3 Implementation Plan](docs/plan/phase3-implementation-plan-2025-12-27.md)** for detailed week-by-week breakdown.

## 10. Contributing

Contributions and feedback are welcome. Please open an issue to discuss any proposed changes or enhancements.