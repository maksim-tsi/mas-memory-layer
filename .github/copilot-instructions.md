# MAS Memory Layer - AI Agent Instructions

## Architecture Overview

This is a **four-tier cognitive memory system** for Multi-Agent Systems (MAS), designed for supply chain/logistics applications. The project is 43% complete (Phase 1 done, Phase 2A 92% done).

**Critical Distinction**: Storage adapters ≠ Memory tiers. Adapters are database clients (complete). Tiers are intelligent memory managers (partially complete). Lifecycle engines automate information flow between tiers (not yet implemented).

### Four-Tier Memory Architecture (ADR-003)

```
L1: Active Context (Redis) → 10-20 recent turns, 24h TTL
L2: Working Memory (PostgreSQL) → Significant facts filtered by CIAR score
L3: Episodic Memory (Qdrant + Neo4j) → Consolidated episodes with dual indexing
L4: Semantic Memory (Typesense) → Distilled knowledge patterns
```

**Information Flow**: L1 raw turns → [Promotion Engine] → L2 facts → [Consolidation Engine] → L3 episodes → [Distillation Engine] → L4 knowledge

## Core Architectural Principles

This project is guided by five core principles. All new code and refactoring should adhere to these concepts:

**Conceptual Model**: The L1-L4 Tiers are the implementation of a two-layer conceptual model:
- **Operating Memory Layer (Redis)**: A high-speed, volatile workspace for agent collaboration (Personal Scratchpads, Shared Workspace)
- **Persistent Knowledge Layer (Specialized Databases)**: A long-term, durable archive for distilled knowledge (Vector, Graph, Search, Relational stores)

**Core Principles**:
1. **Computational State Persistence**: Memory is an active workspace for multi-step reasoning
2. **Collaborative Workspace**: Memory provides a shared, negotiable state for multiple agents
3. **Structured Reasoning for High-Stakes Reliability**: Enforce auditable reasoning schemas
4. **Promotion via Calculated Significance**: Information is promoted intelligently based on calculated importance (CIAR score)
5. **Archiving via Knowledge Distillation**: The system actively learns by distilling resolved events into persistent knowledge

## What's Complete ✅

- **Storage Adapters** (5): Redis, PostgreSQL, Qdrant, Neo4j, Typesense - all in `src/storage/`
- **Memory Tier Classes** (4): L1-L4 classes in `src/memory/tiers/` with dual-indexing for L3
- **Data Models**: `Fact`, `Episode`, `KnowledgeDocument` in `src/memory/models.py` (Pydantic)
- **CIAR Scorer**: Calculation logic in `src/memory/ciar_scorer.py` (Certainty × Impact × Age × Recency)
- **Metrics System**: Comprehensive observability in `src/storage/metrics/` (timing, throughput, percentiles)
- **LLM Connectivity**: 7 models tested (Gemini, Groq, Mistral) but not integrated
- **LLM Client**: `src/utils/llm_client.py` - multi-provider abstraction with fallback

## What's Missing ❌

- **Lifecycle Engines**: `src/memory/engines/` directory - promotion, consolidation, distillation
- **Fact Extraction**: LLM-based structured extraction from L1 turns
- **Autonomous Flow**: L1→L2→L3→L4 intelligent promotion based on CIAR thresholds

## CRITICAL: Python Environment & Execution

- **Python Version**: Python 3.12.3
- **Virtual Environment Path**: `/home/max/code/mas-memory-layer/.venv`
- **CRITICAL RULE**: You MUST NOT use the `source .venv/bin/activate` command. Your `run_in_terminal` tool operates in a stateless shell, and any environment activation will be lost on the very next command.
- **Host Detection**: Before running any command, execute the following to determine whether you are on the managed remote Ubuntu VM, a local macOS checkout, or a local Ubuntu/RDP session:
  ```bash
  uname -a
  hostname
  pwd
  ```
  - If the output shows `Linux` and a hostname such as `skz-dev-lv`, you are on the managed remote VM and must use the absolute paths below.
  - If the output shows `Darwin` (macOS) or a local Ubuntu hostname, you may use the relative `.venv` paths (e.g., `./.venv/bin/python`).
  - Always document the host context in worklogs/DEVLOG entries when it affects behaviour.
- **MANDATORY (Remote VM)**: When operating on the managed remote host, all Python, pip, or pytest commands MUST use the direct, absolute executable path to ensure the correct environment is used:
  - To run Python scripts: `/home/max/code/mas-memory-layer/.venv/bin/python ...`
  - To run tests (pytest): `/home/max/code/mas-memory-layer/.venv/bin/pytest ...`
  - To install packages: `/home/max/code/mas-memory-layer/.venv/bin/pip ...`
- **RECOMMENDED (Local environments)**: Use the equivalent relative commands (`./.venv/bin/python`, etc.) to keep paths portable. The relative commands map 1:1 to the absolute versions and prevent accidental use of a different interpreter.

## MANDATORY: Terminal Resiliency Protocol (Remote SSH)

  * **Pattern**: `<command> > /tmp/copilot.out 2>&1; cat /tmp/copilot.out`
  * The semicolon ensures the log is surfaced even if the primary command exits non-zero. See `docs/lessons-learned.md` (entry LL-20251115-01) for the incident summary.

## Path-Specific Instructions

Detailed implementation patterns are organized by directory:

- **Source Code** (`src/**/*.py`): See `.github/instructions/source.instructions.md`
  - Async-first architecture, dual storage/indexing patterns, CIAR scoring, BaseTier interface, Pydantic v2, exception hierarchy
- **Tests** (`tests/**/*.py`): See `.github/instructions/testing.instructions.md`
  - Pytest patterns, test markers, fixtures, test structure, coverage requirements
- **Documentation** (`docs/**/*.md`): See `.github/instructions/documentation.instructions.md`
  - Academic tone for AIMS 2025, DEVLOG format, ADR structure, technical specifications
- **Scripts** (`scripts/**/*.sh`): See `.github/instructions/scripts.instructions.md`
  - POSIX compliance, virtual environment handling, error handling, output formatting

## Development Workflow

**IMPORTANT**: All commands MUST follow the Terminal Resiliency Protocol (redirect-and-cat pattern).

### Running Tests
```bash
# All tests (pytest discovers tests/ directory)
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/ -v > /tmp/copilot.out 2>&1; cat /tmp/copilot.out

# Smoke tests (connectivity checks)
/home/max/code/mas-memory-layer/scripts/run_smoke_tests.sh > /tmp/copilot.out 2>&1; cat /tmp/copilot.out

# Specific storage adapter
/home/max/code/mas-memory-layer/scripts/run_redis_tests.sh > /tmp/copilot.out 2>&1; cat /tmp/copilot.out

# Memory integration tests
/home/max/code/mas-memory-layer/scripts/run_memory_integration_tests.sh > /tmp/copilot.out 2>&1; cat /tmp/copilot.out
```

Tests use `pytest` with `pytest-asyncio`. See `.github/instructions/testing.instructions.md` for complete testing guidelines.

### Running Benchmarks
```bash
# Storage performance benchmarks
/home/max/code/mas-memory-layer/.venv/bin/python scripts/run_storage_benchmark.py run --size 10000 > /tmp/copilot.out 2>&1; cat /tmp/copilot.out
/home/max/code/mas-memory-layer/.venv/bin/python scripts/run_storage_benchmark.py analyze > /tmp/copilot.out 2>&1; cat /tmp/copilot.out
```

### Database Setup
```bash
# PostgreSQL migrations
/home/max/code/mas-memory-layer/scripts/setup_database.sh > /tmp/copilot.out 2>&1; cat /tmp/copilot.out
# Applies migrations/001_active_context.sql
```

### Environment Setup
Copy `.env.example` to `.env` with:
- PostgreSQL: `DATA_NODE_IP`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- Neo4j: `DATA_NODE_IP`, `NEO4J_USER`, `NEO4J_PASSWORD`
- LLM APIs: `GOOGLE_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`
- Detailed host-detection and bootstrap steps live in `docs/environment-guide.md`; follow that guide before running commands.

## External Tool: Gemini CLI (Future Use)

- **Purpose**: For high-level, complex tasks, we will delegate to the `gemini` CLI. This tool is used for deep codebase analysis, multi-file refactoring planning, and architectural reviews.
- **Invocation Pattern**: You MUST invoke it non-interactively using the `-p` flag.
- **Context Syntax**: You MUST provide file and directory context using the `@` syntax inside the prompt string (e.g., `@src/memory/tiers/` or `@./`).
- **Execution**: All `gemini` commands MUST follow the MANDATORY: Terminal Resiliency Protocol.
- **Example Command**:
```bash
gemini -p "@./ Review the project architecture and suggest improvements for the L3 tier" > /tmp/copilot.out 2>&1; cat /tmp/copilot.out
```

## Critical Files & Directories

- **ADRs**: `docs/ADR/003-four-layers-memory.md` (architecture), `004-ciar-scoring-formula.md`, `006-free-tier-llm-strategy.md`
- **Status Docs**: `docs/reports/adr-003-architecture-review.md` (gap analysis), `DEVLOG.md` (progress tracking)
- **Lessons Register**: `docs/lessons-learned.md` (structured incident log with mitigations)
- **Data Models**: `src/memory/models.py` (Fact, Episode, KnowledgeDocument with Pydantic validation)
- **Metrics**: `src/storage/metrics/collector.py`, `aggregator.py`, `exporters.py`
- **Benchmarks**: `benchmarks/` directory with workload configs

## Common Tasks

### Adding a New Memory Tier
1. Inherit from `BaseTier` in `src/memory/tiers/base_tier.py`
2. Implement abstract methods: `initialize()`, `store()`, `retrieve()`, `health_check()`
3. Add tier-specific logic (e.g., turn windowing for L1, CIAR filtering for L2)
4. Create tests in `tests/memory/test_<tier_name>.py`

### Implementing Lifecycle Engines
Follow Phase 2B-2D plan in `DEVLOG.md`:
1. Create `src/memory/engines/` directory
2. Implement `PromotionEngine` (L1→L2 fact extraction with LLM)
3. Implement `ConsolidationEngine` (L2→L3 episode clustering)
4. Implement `DistillationEngine` (L3→L4 knowledge synthesis)
5. Add circuit breaker pattern for LLM resilience

### Adding Storage Metrics
Metrics auto-collect when enabled. Export formats:
```python
metrics = adapter.get_metrics()
metrics.export_json("results.json")
metrics.export_csv("results.csv")
metrics.export_prometheus()  # Gauge format
```

## Code Style & Testing

See path-specific instruction files for detailed guidelines:
- **Source code patterns**: `.github/instructions/source.instructions.md`
- **Testing patterns**: `.github/instructions/testing.instructions.md`
- **Documentation style**: `.github/instructions/documentation.instructions.md`
- **Script conventions**: `.github/instructions/scripts.instructions.md`

## Research Context

Submission target: **AIMS 2025 Conference**. System compares hybrid 4-tier architecture against:
1. Standard RAG baseline (single vector store)
2. Full-context baseline (pass entire history to LLM)

Benchmark: **GoodAI LTM Benchmark** for long-term memory evaluation (32k-120k token conversations). See `docs/uc-01.md`, `docs/sd-01.md`, `docs/dd-01.md` for experiment specs.

## Python Environment

- **Version**: Python 3.11+ (3.13 tested)
- **Dependencies**: `requirements.txt` (production), `requirements-test.txt` (testing)
- **Virtual Env**: `.venv/` (activate before running scripts)
- **Key Packages**: `pydantic==2.8.2`, `redis==5.0.7`, `psycopg[binary]>=3.2.0`, `qdrant-client==1.9.2`, `neo4j==5.22.0`
