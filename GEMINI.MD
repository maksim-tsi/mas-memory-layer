# Project: MAS Memory Layer - Four-Tier Cognitive Memory System

## Project Overview

This is a **four-tier cognitive memory system** for Multi-Agent Systems (MAS), designed for supply chain/logistics applications. The project implements a hierarchical memory architecture with intelligent information flow between tiers, optimized for high-stakes, multi-agent collaboration scenarios.

**For current implementation status**, refer to `DEVLOG.md` for phase-by-phase progress tracking.

### Four-Tier Memory Architecture (ADR-003)

```
L1: Active Context (Redis) → 10-20 recent turns, 24h TTL
L2: Working Memory (PostgreSQL) → Significant facts filtered by CIAR score
L3: Episodic Memory (Qdrant + Neo4j) → Consolidated episodes with dual indexing
L4: Semantic Memory (Typesense) → Distilled knowledge patterns
```

**Information Flow**: L1 raw turns → [Promotion Engine] → L2 facts → [Consolidation Engine] → L3 episodes → [Distillation Engine] → L4 knowledge

## Core Architectural Principles

All development work must adhere to these five principles:

1. **Computational State Persistence**: Memory is an active workspace for multi-step reasoning
2. **Collaborative Workspace**: Memory provides a shared, negotiable state for multiple agents
3. **Structured Reasoning for High-Stakes Reliability**: Enforce auditable reasoning schemas
4. **Promotion via Calculated Significance**: Information is promoted intelligently based on CIAR score (Certainty × Impact × Age × Recency)
5. **Archiving via Knowledge Distillation**: The system actively learns by distilling resolved events into persistent knowledge

## General Instructions

### Critical Distinction
- **Storage Adapters** (in `src/storage/`) = Database clients for L1-L4 tiers
- **Memory Tiers** (in `src/memory/tiers/`) = Intelligent memory managers with CIAR-based promotion logic
- **Lifecycle Engines** (planned in `src/memory/engines/`) = Autonomous information flow between tiers

**Implementation status**: Check `DEVLOG.md` for the latest completion percentages and active development phases.

### When Working on Code
- Follow async-first architecture - all I/O operations must be async
- Use Pydantic v2 for all data models and validation
- Implement comprehensive error handling with custom exception hierarchy
- Add metrics collection for observability (timing, throughput, percentiles)
- Write tests for all new functionality (pytest + pytest-asyncio)
- Update relevant ADRs and documentation when changing architecture

### Documentation Style
- **ADRs** (Architecture Decision Records): Use academic tone, suitable for AIMS 2025 conference submission
- **DEVLOG.MD**: Use structured format with phases, weeks, and completion percentages
- **Technical Specs**: Include implementation details, API signatures, and test coverage targets

## Technology Stack

**Language**: Python 3.12.3  
**Virtual Environment**: `/home/max/code/mas-memory-layer/.venv`  
**Key Dependencies**:
- `pydantic==2.8.2` - Data validation and models
- `redis==5.0.7` - L1 Active Context storage
- `psycopg[binary]>=3.2.0` - L2 Working Memory storage
- `qdrant-client==1.9.2` - L3 vector indexing
- `neo4j==5.22.0` - L3 graph indexing
- `typesense>=1.0.0` - L4 semantic search

**Testing**: `pytest`, `pytest-asyncio`

## Python Execution Protocol

**CRITICAL**: You are operating on a remote Ubuntu machine (skz-dev-lv) via SSH. Always use absolute paths to executables:

```bash
# Correct - Use absolute paths
/home/max/code/mas-memory-layer/.venv/bin/python script.py
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/
/home/max/code/mas-memory-layer/.venv/bin/pip install package

# WRONG - Do NOT use these
source .venv/bin/activate  # Shell state is lost between commands
python script.py           # May use wrong interpreter
```

**Terminal Output Capture**: When running commands, use redirect-and-cat pattern for reliability:
```bash
command > /tmp/gemini.out 2>&1; cat /tmp/gemini.out
```
The semicolon ensures logs are displayed even if the command exits non-zero. See `docs/lessons-learned.md` (entry LL-20251115-01) for context.

## Multi-Host Development Guidance

Multiple contributors alternate between a remote Ubuntu VM, local macOS laptops, and local Ubuntu desktops. Follow this checklist before executing any command:

1. **Probe the environment** – run `uname -a`, `hostname`, and `pwd` to determine whether you are on macOS (`Darwin`), remote Ubuntu (hostnames such as `skz-dev-lv`), or a local Ubuntu session.
2. **Prefer relative interpreter paths** (`./.venv/bin/python`, `./scripts/...`) whenever you are on macOS or a self-managed Ubuntu machine. This keeps instructions portable and prevents accidental writes to system Python installations.
3. **Use the absolute paths shown above only when you are attached to the managed remote VM** that enforces `/home/max/code/mas-memory-layer/.venv/bin/...`.
4. **Document the host context** in commit messages or DEVLOG entries when environment-specific behaviour (e.g., missing packages) occurs.

See [`docs/environment-guide.md`](docs/environment-guide.md) for the full detection and bootstrap procedure.

Maintain the structured incident log in [`docs/lessons-learned.md`](docs/lessons-learned.md) whenever a workflow issue or mitigation is discovered. Reference the relevant entry ID when updating instructions or DEVLOG notes.

## Coding Style

### Python Code Style
- Use **async/await** for all I/O operations
- **Type hints** are mandatory for all function signatures
- Prefer **composition over inheritance**
- Use **descriptive variable names** (no single-letter variables except in list comprehensions)
- Maximum line length: **100 characters**
- Imports: Group by stdlib, third-party, local (separated by blank lines)

### Error Handling
Use the custom exception hierarchy in `src/storage/base.py`:
- `StorageError` - Base exception
- `StorageConnectionError` - Connection failures
- `StorageTimeoutError` - Operation timeouts
- `StorageDataError` - Data validation errors
- `StorageQueryError` - Query execution errors

### Data Models
- All models must inherit from `pydantic.BaseModel`
- Use `Field(...)` for validation constraints
- Include docstrings for all model fields
- Example:
```python
from pydantic import BaseModel, Field

class Fact(BaseModel):
    """A significant piece of information promoted from L1 to L2."""
    fact_id: str = Field(..., description="Unique identifier")
    content: str = Field(..., min_length=1)
    ciar_score: float = Field(..., ge=0.0, le=1.0)
```

### Testing Guidelines
- Test file structure: `tests/<module>/test_<filename>.py`
- Use pytest fixtures from `tests/fixtures.py` for database connections
- Mark tests appropriately: `@pytest.mark.asyncio`, `@pytest.mark.smoke`, `@pytest.mark.integration`
- Target: >90% code coverage per module
- All storage adapter tests must include: connectivity, CRUD operations, error handling, edge cases

## Project Structure

```
src/
├── storage/              # Storage adapters for database connectivity
│   ├── base.py          # Base adapter + exception hierarchy
│   ├── redis_adapter.py # L1 Active Context
│   ├── postgres_adapter.py # L2 Working Memory
│   ├── qdrant_adapter.py   # L3 Vector indexing
│   ├── neo4j_adapter.py    # L3 Graph indexing
│   └── typesense_adapter.py # L4 Semantic search
│
├── memory/              # Memory tier implementations
│   ├── models.py        # Pydantic models (Fact, Episode, KnowledgeDocument)
│   ├── ciar_scorer.py   # CIAR scoring algorithm
│   └── tiers/          # Memory tier classes
│       ├── base_tier.py
│       ├── active_context_tier.py    # L1
│       ├── working_memory_tier.py    # L2
│       ├── episodic_memory_tier.py   # L3
│       └── semantic_memory_tier.py   # L4
│
└── utils/               # Shared utilities
    └── llm_client.py    # Multi-provider LLM client

tests/
├── storage/             # Adapter tests
├── memory/              # Memory tier tests
└── fixtures.py          # Shared test fixtures

**Test status**: Run `/home/max/code/mas-memory-layer/.venv/bin/pytest tests/ -v` for current results, or check `DEVLOG.md` for latest coverage reports.

docs/
├── ADR/                 # Architecture Decision Records
│   ├── 003-four-layers-memory.md
│   ├── 004-ciar-scoring-formula.md
│   ├── 005-multi-tier-llm-provider-strategy.md
│   └── 006-free-tier-llm-strategy.md
├── plan/                # Implementation plans
└── reports/             # Status reports and reviews
```

## Implementation Status

**Current Status**: Refer to `DEVLOG.md` for the latest phase-by-phase progress tracking, completion percentages, and active development work.

**Architecture Components**:
- **Storage Layer**: Redis, PostgreSQL, Qdrant, Neo4j, Typesense adapters
- **Memory Tiers**: L1-L4 tier classes with CIAR-based filtering
- **Data Models**: `Fact`, `Episode`, `KnowledgeDocument` (Pydantic v2)
- **CIAR Scorer**: Significance calculation (Certainty × Impact × Age × Recency)
- **Metrics System**: Observability with timing, throughput, percentiles
- **Lifecycle Engines**: Promotion, consolidation, distillation (see `DEVLOG.md` for status)
- **LLM Integration**: Multi-provider client for fact extraction (see `DEVLOG.md` for status)

**Gap Analysis**: See `docs/reports/adr-003-architecture-review.md` for architectural completeness review.

## Common Development Tasks

### Running Tests
```bash
# All tests
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/ -v

# Specific test category
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/storage/ -v
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/memory/ -v

# Smoke tests (connectivity checks)
/home/max/code/mas-memory-layer/scripts/run_smoke_tests.sh

# With coverage
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/ --cov=src --cov-report=html
```

### Running Benchmarks
```bash
/home/max/code/mas-memory-layer/.venv/bin/python scripts/run_storage_benchmark.py run --size 10000
/home/max/code/mas-memory-layer/.venv/bin/python scripts/run_storage_benchmark.py analyze
```

### Database Setup
```bash
# PostgreSQL migrations
/home/max/code/mas-memory-layer/scripts/setup_database.sh
```

### Environment Setup
Configuration in `.env` (NOT tracked in git):
- PostgreSQL: `DATA_NODE_IP`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- Neo4j: `DATA_NODE_IP`, `NEO4J_USER`, `NEO4J_PASSWORD`
- LLM APIs: `GOOGLE_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`

Reference `.env.example` for required variables (uses placeholder values only).

## Research Context

**Submission Target**: AIMS 2025 Conference  
**Research Question**: Can a four-tier hybrid memory architecture outperform standard RAG and full-context baselines?

**Benchmark**: GoodAI LTM Benchmark (32k-120k token conversations)

**Baselines**:
1. Standard RAG (single vector store)
2. Full-context (pass entire history to LLM)

See `docs/uc-01.md`, `docs/sd-01.md`, `docs/dd-01.md` for experiment specifications.

## Key Files & Documentation

**Critical ADRs**:
- `docs/ADR/003-four-layers-memory.md` - Core architecture
- `docs/ADR/004-ciar-scoring-formula.md` - CIAR scoring specification
- `docs/ADR/006-free-tier-llm-strategy.md` - Multi-provider LLM strategy

**Status Tracking**:
- `DEVLOG.md` - Phase-by-phase progress tracking
- `docs/reports/adr-003-architecture-review.md` - Gap analysis
- `docs/plan/llm-provider-implementation-plan-12112025.md` - Phase 2B plan

**Data Models**:
- `src/memory/models.py` - Fact, Episode, KnowledgeDocument (Pydantic)

**Metrics**:
- `src/storage/metrics/collector.py` - Metric collection
- `src/storage/metrics/aggregator.py` - Aggregation logic
- `src/storage/metrics/exporters.py` - JSON/CSV/Prometheus export

## Path-Specific Instructions

Detailed implementation patterns are in `.github/instructions/`:
- `source.instructions.md` - Source code patterns for `src/**/*.py`
- `testing.instructions.md` - Testing patterns for `tests/**/*.py`
- `documentation.instructions.md` - Documentation style for `docs/**/*.md`
- `scripts.instructions.md` - Shell script conventions for `scripts/**/*.sh`

**Note**: Additional AI assistant instructions are in `AGENTS.MD` and `.github/copilot-instructions.md`.

## Gemini Structured Output (Validated 2025-12-29)

### Working Implementation
Gemini's native structured output using `types.Schema` format is validated and working. See `tests/utils/test_gemini_structured_output.py` and `examples/gemini_structured_output_test.md` for complete examples.

**Key Requirements**:
1. **Environment Variable**: Use `GOOGLE_API_KEY` from `.env` (not `GEMINI_API_KEY`)
2. **Native Schema Format**: Use `genai.types.Schema` with `types.Type.OBJECT/ARRAY/STRING/NUMBER`
3. **System Instructions**: Pass as list of `types.Part.from_text()` in `GenerateContentConfig`
4. **Response Format**: Set `response_mime_type="application/json"` with `response_schema` parameter
5. **Model**: Use `gemini-3-flash-preview` (64K output tokens) as default

**Working Code Pattern**:
```python
from google import genai
from google.genai import types
import os

client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

# Define schema using native types
response_schema = types.Schema(
    type=types.Type.OBJECT,
    required=["facts"],
    properties={
        "facts": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                required=["content", "type", "category", "certainty", "impact"],
                properties={
                    "content": types.Schema(type=types.Type.STRING),
                    "type": types.Schema(
                        type=types.Type.STRING,
                        enum=["preference", "constraint", "entity", "mention", "relationship", "event"]
                    ),
                    # ... more properties
                }
            )
        )
    }
)

# System instruction as Parts
system_instruction = [
    types.Part.from_text(text="You are an expert fact extractor...")
]

# Configure with structured output
config = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=response_schema,
    system_instruction=system_instruction,
    temperature=0.0
)

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
    config=config
)
```

**Important Notes**:
- `ThinkingConfig` does NOT support `thinking_level` parameter (only `include_thoughts: bool`)
- Pydantic models remain compatible for other providers (OpenAI, Groq)
- Native `types.Schema` format is required for Gemini - do not use Pydantic's `model_json_schema()`
- Test validates 9 facts extracted from supply chain conversation with proper schema adherence
- See `tests/utils/test_gemini_structured_output.py` for complete working examples

## Security Rules

**NEVER commit**:
- `.env` files with real credentials
- API keys, passwords, or tokens
- Private IP addresses (use placeholders like `192.168.1.100` in `.env.example`)

**Protected Files** (Read-Only unless explicitly instructed):
- `.env`, `.env.example`
- `.gitignore`
- `requirements.txt`, `requirements-test.txt`
- `.github/` directory
- `AGENTS.MD`, `GEMINI.MD`

## Branch Strategy

- `main` - Production-ready releases
- `dev` - Active development branch
- `dev-tests` - Testing and experimental features
- `dev-mas` - MAS-specific features

Always create feature branches from `dev` and merge back via pull requests.

## Import Guidelines

When suggesting imports or file modifications, you can use the `@file.md` syntax to reference context from other files:

```markdown
@docs/ADR/003-four-layers-memory.md
@src/memory/models.py
@.github/instructions/source.instructions.md
```

This helps provide additional context without repeating large blocks of documentation.
