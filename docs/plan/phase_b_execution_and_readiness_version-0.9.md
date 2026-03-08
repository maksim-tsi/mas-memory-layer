# Phase 5 Execution and Readiness (version-0.9)

Consolidated Phase 5 implementation, readiness, subset execution, and post-run improvement plans.

Sources:

---

# Phase 5 Implementation Plan: GoodAI LTM Benchmark Evaluation

**Version**: 2.0 (Updated: January 26, 2026)  
**Date**: January 3, 2026 (Original) | January 26, 2026 (Revised)  
**Duration**: 2-3 weeks (10% subset baseline first)  
**Status**: Implementation Starting | Subset Execution Strategy  
**Prerequisites**: ✅ Phase 4 Complete (574/586 tests passing, 0 failures)  
**Target**: AIMS 2025 Conference Paper Submission  
**Branch**: `dev-mas`

---

## Executive Summary

Phase 5 executes a rigorous quantitative evaluation of our four-tier hybrid memory architecture using the GoodAI LTM Benchmark. **This revised plan focuses on a 10% subset execution (32k span, prospective_memory + restaurant tests) to establish performance baselines before full-scale runs.** The subset approach validates system integration, measures vector/graph retrieval performance, and ensures database isolation strategies work under real workload.

### Core Deliverables (Revised)

1. **Three Agent Implementations**: `MemoryAgent` (full system), `RAGAgent` (standard baseline), `FullContextAgent` (naive baseline)
2. **Isolated FastAPI Wrappers**: Three separate services (ports 8080/8081/8082) with database-level session isolation
3. **Benchmark Integration**: GoodAI LTM Benchmark (separate venv) + custom agent interfaces with session ID prefixing
4. **10% Subset Baseline Results**: Performance bottleneck analysis, timing breakdown, memory accumulation patterns
5. **Decision Matrix**: Scale to full benchmark, optimize retrieval, or adjust architecture

### Key Metrics

| Metric Category | Measurements |
|-----------------|--------------|
| **Functional Correctness** | GoodAI LTM accuracy scores (0-10 scale) on prospective_memory + restaurant tests |
| **Operational Efficiency** | Adapter-level timing breakdown (LLM % vs L2 % vs L3-vector % vs L3-graph % vs L4 %) |
| **Resource Utilization** | Memory accumulation timeline, token consumption, database query counts |
| **System Performance** | Total latency per turn, P50/P95/P99 distributions, bottleneck identification |

---

## Current State Assessment

### What Exists (Phase 4 Deliverables)

| Component | Status | Location |
|-----------|--------|----------|
| **Storage Adapters** (5) | ✅ Complete | `src/storage/` |
| **Memory Tiers** (L1-L4) | ✅ Complete | `src/memory/tiers/` |
| **Lifecycle Engines** (3) | ✅ Complete | `src/memory/engines/` |
| **Agent Tools** | ✅ Complete | `src/agents/tools/` |
| **MASToolRuntime** | ✅ Complete | `src/agents/runtime.py` |
| **LLM Client** | ✅ Complete | `src/utils/llm_client.py` |
| **Gemini Structured Output** | ✅ Validated | `gemini-3-flash-preview` |
| **Test Suite** | ✅ 574 passed | All lifecycle paths verified |

### What's Missing (Phase 5 Scope)

| Component | Status | Target Location |
|-----------|--------|-----------------|
| **BaseAgent class** | ✅ Implemented | `src/agents/base_agent.py` |
| **MemoryAgent** (UC-01) | 🚧 Baseline implemented | `src/agents/memory_agent.py` |
| **RAGAgent** (UC-02) | 🚧 Baseline implemented | `src/agents/rag_agent.py` |
| **FullContextAgent** (UC-03) | 🚧 Baseline implemented | `src/agents/full_context_agent.py` |
| **LangGraph StateGraph wiring** | ❌ Not implemented | Agent classes above |
| **Agent Wrapper API** | 🚧 Baseline implemented | `src/evaluation/agent_wrapper.py` |
| **GoodAI Benchmark Integration** | 🚧 Partial (model interfaces registered) | `benchmarks/goodai-ltm-benchmark/model_interfaces/mas_agents.py` |
| **Instrumentation/Logging** | ❌ Not implemented | `src/evaluation/instrumentation.py` |
| **Experiment Automation** | ❌ Not implemented | `scripts/run_experiments.sh` |
| **Analysis Notebook** | ❌ Not implemented | `benchmarks/analysis/analyze_results.ipynb` |

### Model Configuration (Updated)

| Provider | Model ID | Use Case | Rate Limits |
|----------|----------|----------|-------------|
| **Gemini** | `gemini-2.5-flash-lite` | Primary model for all agents (subset baseline) | 4K RPM, 4M TPM, Unlimited RPD |
| **Groq** | `openai/gpt-oss-120b` | Future fallback (not used in subset) | 30 RPM, 200k TPM |

**Rationale**: Switched to `gemini-2.5-flash-lite` for Phase 5 due to significantly higher rate limits (4K RPM vs 10 RPM for gemini-3-flash-preview), enabling faster experimental iteration without quota exhaustion. Unlimited requests per day (RPD) removes daily quota concerns for subset execution.

---

## Architecture Overview (Revised: Isolated Services)

### Three Isolated FastAPI Services with Database-Level Session Isolation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              GoodAI LTM Benchmark Runner (Separate Venv)                    │
│                  benchmarks/.venv-benchmark/                                │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────────┐  │
│  │  mas-full    │  │   mas-rag    │  │   mas-full-context               │  │
│  │  (agent ifc) │  │  (agent ifc) │  │   (agent ifc)                    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┬───────────────────┘  │
│         │ Prefix:         │ Prefix:                  │ Prefix:              │
│         │ full:{id}       │ rag:{id}                 │ full_context:{id}    │
└─────────┼─────────────────┼──────────────────────────┼──────────────────────┘
          │                 │                          │
          ▼                 ▼                          ▼
   HTTP :8080        HTTP :8081                 HTTP :8082
┌─────────────────┐ ┌─────────────────┐ ┌──────────────────────────────────┐
│  Wrapper #1     │ │  Wrapper #2     │ │  Wrapper #3                      │
│  --agent full   │ │  --agent rag    │ │  --agent full_context            │
│  --port 8080    │ │  --port 8081    │ │  --port 8082                     │
│                 │ │                 │ │                                  │
│ GET /sessions   │ │ GET /sessions   │ │ GET /sessions                    │
│ GET /memory_st  │ │ GET /memory_st  │ │ GET /memory_st                   │
│                 │ │                 │ │                                  │
│ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌────────────────────────────┐   │
│ │MemoryAgent  │ │ │ │  RAGAgent   │ │ │ │  FullContextAgent          │   │
│ │(LangGraph)  │ │ │ │(Incremental)│ │ │ │  (Truncation)              │   │
│ └─────────────┘ │ │ └─────────────┘ │ │ └────────────────────────────┘   │
└────────┬────────┘ └────────┬────────┘ └───────────────┬──────────────────┘
         │                   │                           │
         ▼                   ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  Database Layer (Shared with Isolation)                     │
│                                                                             │
│  Redis: mas-{agent}:*     PostgreSQL: LOCK TABLE facts                     │
│  Qdrant: episodes_mas_full, episodes_mas_rag, episodes_mas_full_context   │
│  Neo4j: Redis distributed lock (LOCK neo4j:{session_id}, 30s TTL)         │
│  Typesense: Session filtering                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Database Isolation Strategy

| Layer | Isolation Mechanism | Purpose |
|-------|---------------------|---------|
| **Redis** | Key prefix `mas-{agent}:*` + namespace per agent | Prevent L1 cross-contamination |
| **PostgreSQL** | Table-level locks during writes (`LOCK TABLE facts IN SHARE ROW EXCLUSIVE MODE`) | Serialize writes, prevent race conditions |
| **Qdrant** | Separate collections per agent (`episodes_mas_full`, etc.) | Enable parallel indexing without contention |
| **Neo4j** | Redis distributed lock per session (`LOCK neo4j:{session_id}`, 30s TTL) | Coordinate graph writes across services |
| **Typesense** | Session ID filtering in queries | Logical isolation, shared collection |

### Data Flow Per Agent (Turn-by-Turn Accumulation)

**MemoryAgent (UC-01 - Full System)**:
1. Receive request with full history + current message (session_id: `full:{goodai_id}`)
2. Store current turn in L1 Active Context (Redis `mas-full:{session_id}:*`)
3. Query L2/L3/L4 for relevant knowledge using UnifiedMemorySystem
4. Synthesize context with LLM (`gemini-2.5-flash-lite`)
5. Generate response
6. Update personal state → trigger async L1→L2 promotion
7. Return response to GoodAI benchmark

**RAGAgent (UC-02 - Standard RAG)**:
1. Receive request with history + message (session_id: `rag:{goodai_id}`)
2. Index current turn into Qdrant collection `episodes_mas_rag`
3. Query same collection with message embedding (top_k=10)
4. Concatenate retrieved chunks with message
5. Generate response via LLM (stateless, no L2/L3/L4)
6. Return response to GoodAI benchmark

**FullContextAgent (UC-03 - Full Context)**:
1. Receive request with history + message (session_id: `full_context:{goodai_id}`)
2. Concatenate all history turns (no storage or retrieval)
3. Truncate if exceeds 120k tokens, log context overflow
4. Send full prompt to LLM
5. Generate response
6. Return response to GoodAI benchmark

---

## Phase 5 Subset: 10% Baseline Execution (Week 1-2)

### Subset Scope Definition

**Test Coverage**: 10% of GoodAI Benchmark v3.5, 32k memory span only

| Test Type | Selection Rationale | Expected Test Count |
|-----------|---------------------|---------------------|
| `prospective_memory` | Temporal fact recall - tests L2/L3 retrieval across time | ~10-15 test instances |
| `restaurant` | Multi-entity tracking - tests graph queries and fact consolidation | ~10-15 test instances |

**Why This Subset**:
- Covers two distinct memory challenges (temporal + multi-entity)
- Small enough to complete in hours vs days
- Representative of GoodAI's full benchmark diversity
- Sufficient to identify system bottlenecks (vector search, graph queries, LLM calls)

---

## Phase 5A: Infrastructure Setup (Days 1-2)

### W5A.1: GoodAI Benchmark Setup & Validation

**Objective**: Download, extract, and validate GoodAI benchmark repository in isolated environment.

**File**: `benchmarks/README.md`

**Tasks**:
- [ ] Download [goodai-ltm-benchmark-main.zip](https://github.com/GoodAI/goodai-ltm-benchmark/archive/refs/heads/main.zip) to `benchmarks/`
- [ ] Add `goodai-ltm-benchmark*` and `.venv-benchmark/` to `.gitignore`
- [ ] Extract to `benchmarks/goodai-ltm-benchmark/`
- [ ] Create isolated Python 3.10+ venv at `benchmarks/.venv-benchmark/`
- [ ] Install their `requirements.txt` in isolated venv
- [ ] Validate `prospective_memory.py` and `restaurant.py` exist in `benchmarks/goodai-ltm-benchmark/datasets/`
- [ ] Document setup process in `benchmarks/README.md`

**Acceptance Criteria**:
- [ ] GoodAI benchmark runs in isolated venv (test with their example config)
- [ ] No dependency conflicts with our project venv
- [ ] Selected test datasets present and loadable

**Deliverables**:
```
benchmarks/goodai-ltm-benchmark/       (extracted)
benchmarks/.venv-benchmark/            (isolated venv)
benchmarks/README.md                   (setup documentation)
.gitignore                             (updated)
```

---

### W5A.2: Update AGENTS.MD and Validate Dependencies

### W5A.2: Update AGENTS.MD and Validate Dependencies

**Objective**: Update project protocol to permit absolute paths and verify LLM/framework support.

**Files**: `AGENTS.MD`, `src/utils/llm_client.py`, `.env.example`

**Tasks**:
- [ ] Modify `AGENTS.MD` Protocol 8.1 to permit absolute paths for read-only tool operations
- [ ] Verify `gemini-2.5-flash-lite` model ID support in `src/utils/llm_client.py`
- [ ] Update `.env.example` with `GOOGLE_API_KEY` and model configuration (4K RPM, 4M TPM, Unlimited RPD)
- [ ] Verify LangGraph version in `requirements.txt` supports `StateGraph` API (>= 0.1.0)
- [ ] Document absolute path exception rationale in `AGENTS.MD`

**Acceptance Criteria**:
- [ ] `gemini-2.5-flash-lite` successfully initializes via LLM client
- [ ] LangGraph `StateGraph` imports without error
- [ ] `.env.example` documents all required keys and limits

**Deliverables**:
```
AGENTS.MD (Protocol 8.1 updated)
.env.example (updated with gemini-2.5-flash-lite config)
```

---

### W5A.3: GoodAI Config Validator

**Objective**: Implement strict JSON schema validator for benchmark configuration files.

**File**: `scripts/validate_goodai_config.py`

**Tasks**:
- [x] Create Pydantic model for GoodAI config schema (memory_span, test_types, etc.).
- [x] Implement strict validation (reject unknown fields).
- [x] Add CLI: `python scripts/validate_goodai_config.py <config.yaml>`.
- [x] Return exit code 0 (valid) or 1 (invalid) with detailed error messages.
- [ ] Integrate into `run_subset_experiments.sh` as pre-flight check.

**Acceptance Criteria**:
- [x] Validator catches typos and missing required fields.
- [x] Validator rejects configs with unknown test types.
- [x] Clear error messages point to specific validation failures.

**Deliverables**:
```
scripts/validate_goodai_config.py
tests/scripts/test_validate_goodai_config.py
```

---

## Phase 5B: Agent Implementation (Days 3-5)

### W5B.1: BaseAgent and Pydantic Models

**Objective**: Create abstract base class and request/response models with format coercion.

**Files**: `src/agents/base_agent.py`, `src/agents/models.py`

**Tasks**:
- [x] Define `BaseAgent` abstract class with lifecycle and health methods (implemented as `initialize`, `run_turn`, `health_check`, `cleanup_session`).
- [x] Define `RunTurnRequest(BaseModel)` with fields aligned to wrapper payloads (`session_id`, `role`, `content`, `turn_id`).
- [ ] Implement Pydantic validator for automatic format coercion:
  - Input: `{user: "...", assistant: "..."}` or `{role: "user", content: "..."}`
  - Output: Standardized `{role: "user", content: "..."}`
- [x] Define `RunTurnResponse(BaseModel)` with response fields (`session_id`, `role`, `content`, `turn_id`).
- [ ] Implement common instrumentation hooks (adapter-level timing)

**Acceptance Criteria**:
- [x] Abstract methods enforced via `BaseAgent` ABC (verified via class definition).
- [ ] Format coercion validator handles both input formats.
- [ ] Unit tests for base class and Pydantic models (10+ tests).

**Deliverables**:
```
src/agents/base_agent.py
src/agents/models.py
tests/agents/test_base_agent.py
tests/agents/test_models.py
```

---

### W5B.2: MemoryAgent with LangGraph StateGraph

**Objective**: Implement the full hybrid memory agent using LangGraph StateGraph with all four memory tiers.

**File**: `src/agents/memory_agent.py`

**Tasks**:
- [x] Create `MemoryAgent` class inheriting from `BaseAgent`.
- [ ] Implement LangGraph `StateGraph` with nodes:
  - `perceive`: Parse incoming message, load agent state from L1
  - `retrieve`: Query L2/L3/L4 via unified tools
  - `reason`: Synthesize context, generate response via LLM
  - `update`: Write to L1, trigger async promotion
  - `respond`: Format and return final response
- [ ] Wire existing tools from `src/agents/tools/`:
  - `store_conversation_turn` (L1)
  - `calculate_ciar_score`, `filter_by_ciar_threshold`
  - `query_working_memory`, `query_episodic_memory`, `query_semantic_memory`
  - `synthesize_knowledge`
- [ ] Implement `PersonalMemoryState` management (scratchpad, active_goals).
- [ ] Add circuit breaker for LLM/database failures.
- [x] Integrate with `UnifiedMemorySystem` via `get_context_block`.

**LangGraph Wiring**:
```python
from langgraph.graph import StateGraph, END

class MemoryAgent(BaseAgent):
    def __init__(self, memory_system: UnifiedMemorySystem, llm_client: LLMClient):
        self.memory = memory_system
        self.llm = llm_client
        self.graph = self._build_graph()
    
    def _build_graph(self) -> CompiledGraph:
        workflow = StateGraph(AgentState)
        
        workflow.add_node("perceive", self._perceive_node)
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("reason", self._reason_node)
        workflow.add_node("update", self._update_node)
        workflow.add_node("respond", self._respond_node)
        
        workflow.set_entry_point("perceive")
        workflow.add_edge("perceive", "retrieve")
        workflow.add_edge("retrieve", "reason")
        workflow.add_edge("reason", "update")
        workflow.add_edge("update", "respond")
        workflow.add_edge("respond", END)
        
        return workflow.compile()
```

**Acceptance Criteria**:
- [ ] Full PERCEIVE→RETRIEVE→REASON→UPDATE→RESPOND cycle works (LangGraph wiring pending).
- [ ] Integrates with all 4 memory tiers via UnifiedMemorySystem (currently L1/L2 only).
- [ ] Handles LLM failures gracefully (circuit breaker triggers).
- [ ] Adapter-level metrics collected for each storage operation.
- [ ] Unit tests (12+ tests) + integration test with mocked backends.

**Deliverables**:
```
src/agents/memory_agent.py
tests/agents/test_memory_agent.py
tests/integration/test_memory_agent_integration.py
```

---

### W5B.3: RAGAgent with Incremental Indexing

**Objective**: Implement the stateless RAG baseline with turn-by-turn Qdrant indexing.

**File**: `src/agents/rag_agent.py`

**Tasks**:
- [x] Create `RAGAgent` class inheriting from `BaseAgent`.
- [ ] Implement turn-by-turn flow:
  - Index current turn into `episodes_mas_rag` Qdrant collection
  - Generate embedding for current message
  - Query same collection (top_k=10, similarity threshold)
  - Concatenate retrieved chunks with message
  - Generate response via LLM
- [ ] No state management between turns (stateless).
- [ ] No L1/L2/L3/L4 Operating Memory usage.
- [ ] Add instrumentation for Qdrant indexing and query latency.

**Architectural Constraints**:
- No `PersonalMemoryState` (stateless)
- No async consolidation or promotion
- Single Qdrant collection per agent instance

**Acceptance Criteria**:
- [ ] Stateless operation verified (no state persists between calls).
- [ ] Single Qdrant index + query per turn (verified via logs).
- [ ] Response quality comparable to MemoryAgent on short contexts.
- [ ] Unit tests (8+ tests).

**Deliverables**:
```
src/agents/rag_agent.py
tests/agents/test_rag_agent.py
```

---

### W5B.4: FullContextAgent with Graceful Truncation

**Objective**: Implement the naive full-context baseline with history truncation at 120k tokens.

**File**: `src/agents/full_context_agent.py`

**Tasks**:
- [x] Create `FullContextAgent` class inheriting from `BaseAgent`.
- [ ] Implement full history concatenation from request.
- [ ] Add token counting (tiktoken or approximate).
- [ ] Implement graceful truncation at 120k tokens:
  - Keep most recent turns up to limit
  - Log context overflow with turn count
  - Return error response documenting limit exceeded (for 120k+ span tests)
- [ ] Add instrumentation for prompt size and token counts
- [ ] No storage or retrieval operations

**Architectural Constraints**:
- No retrieval or filtering (pass everything or truncate)
- No knowledge distillation
- Maximum token consumption per turn

**Acceptance Criteria**:
- [ ] Full history included in every prompt (up to 120k tokens).
- [ ] Handles context overflow gracefully (truncation with logging).
- [ ] Token count metrics accurate.
- [ ] Unit tests (6+ tests).

**Deliverables**:
```
src/agents/full_context_agent.py
tests/agents/test_full_context_agent.py
```

---

## Phase 5C: Wrapper Services (Days 6-8)

### W5C.1: FastAPI Wrapper with Database Isolation

**Objective**: Create isolated FastAPI service with startup DB checks, session tracking, and cleanup.

**File**: `src/evaluation/agent_wrapper.py`

**Tasks**:
- [x] Implement FastAPI application with CLI args:
  - `--agent-type {full|rag|full_context}`
  - `--port {8080|8081|8082}`
  - `--model gemini-2.5-flash-lite`
- [x] Implement lifespan context manager:
  - Pre-initialize UnifiedMemorySystem with agent-specific config (L1/L2 tiers configured).
  - Separate Qdrant collections: `episodes_mas_full`, `episodes_mas_rag`, `episodes_mas_full_context` (pending).
  - Redis key prefix: `mas-{agent}:*` (session prefixing implemented; Redis key prefixing pending).
  - Validate DB connectivity (Redis ping implemented; full multi-backend validation pending).
  - Fail fast with HTTP 500 and detailed error if any DB unavailable (partial).
- [ ] Implement database isolation mechanisms:
  - PostgreSQL: Table-level locks during writes (`LOCK TABLE facts IN SHARE ROW EXCLUSIVE MODE`).
  - Redis: Distributed locks for Neo4j operations (`LOCK neo4j:{session_id}`, 30s TTL, auto-renew).
  - Qdrant: Agent-specific collection routing.
- [x] Implement endpoints:
  - POST `/run_turn` (main processing endpoint)
  - GET `/sessions` (dynamic session discovery from storage layers)
  - GET `/memory_state?session_id={id}` (returns `{"session_id": "{agent}:{id}", "l1_turns": N, "l2_facts": M, "l3_episodes": K, "l4_docs": P}`)
  - GET `/health` (DB connectivity status)
- [x] Implement graceful shutdown:
  - Close DB connections (Redis, L1/L2 adapters).
  - Flush metrics (pending).
  - Clean up Redis locks (pending).
  - Target only active sessions from current run (partial via `/cleanup_force`).
- [x] Add structured logging (INFO level):
  - Request/response details
  - Adapter-level storage timing
  - Infrastructure errors as HTTP 500

**Acceptance Criteria**:
- [ ] Startup health checks prevent service start if DB unavailable (partial: Redis only).
- [x] All three agent types work with same wrapper code (agent factory pattern).
- [x] Session isolation verified with `redis_key_validator` assertions in integration tests.
- [ ] Instrumentation captures adapter-level timing.
- [x] Unit test suite passing (12+ tests, reports in `tests/reports/unit/`).
- [x] Integration test suite passing (Redis key validation, reports in `tests/reports/integration/`).

**Test Report Preservation**: Test reports are gitignored by default. After milestone executions,
manually copy the relevant XML/HTML reports to `docs/reports/test_runs/YYYYMMDD/` for archival.

**Deliverables**:
```
src/evaluation/agent_wrapper.py
src/evaluation/instrumentation.py
tests/evaluation/test_agent_wrapper.py
tests/evaluation/test_mas_agents.py
tests/integration/test_wrapper_agents_integration.py
scripts/run_wrapper_tests.sh
```

---

### W5C.2: GoodAI Agent Interfaces

**Objective**: Register custom agents in GoodAI's model_interfaces with session ID prefixing.

**File**: `benchmarks/goodai-ltm-benchmark/model_interfaces/mas_agents.py`

**Tasks**:
- [x] Implement GoodAI agent interface for `mas-full`:
  - HTTP POST to `http://localhost:8080/run_turn`
  - Prefix session_id: `full:{goodai_session_id}`
  - Handle HTTP errors gracefully
- [x] Implement interface for `mas-rag`:
  - HTTP POST to `http://localhost:8081/run_turn`
  - Prefix session_id: `rag:{goodai_session_id}`
- [x] Implement interface for `mas-full-context`:
  - HTTP POST to `http://localhost:8082/run_turn`
  - Prefix session_id: `full_context:{goodai_session_id}`
- [x] Register agents in GoodAI's agent registry.
- [x] Add retry logic with exponential backoff for transient HTTP errors.

**Acceptance Criteria**:
- [ ] GoodAI benchmark successfully calls all three agents (pending execution).
- [x] Session ID prefixing applied correctly.
- [x] Error messages from wrappers propagate to GoodAI logs.

**Deliverables**:
```
benchmarks/goodai-ltm-benchmark/model_interfaces/mas_agents.py
```

---

## Phase 5D: Execution Infrastructure (Days 9-10)

### W5D.1: Subset Config and Documentation

**Objective**: Create validated subset configuration and document integration.

**Files**: `benchmarks/goodai-ltm-benchmark/configs/mas_subset_32k.yaml`, `docs/integrations/goodai-benchmark-setup.md`

**Tasks**:
- [x] Create subset config (implemented as `benchmarks/goodai-ltm-benchmark/configurations/mas_subset_32k.yml`):
  ```yaml
  memory_span: 32000
  test_types:
    - prospective_memory
    - restaurant
  model: mas-full  # Will be overridden by -a flag
  ```
- [x] Validate config with `scripts/validate_goodai_config.py`.
- [x] Document in `docs/integrations/goodai-benchmark-setup.md`:
  - Setup instructions for GoodAI benchmark
  - HTTP API schema (`/run_turn`, `/sessions`, `/memory_state`)
  - Session ID prefixing convention
  - Result file mapping:
    - GoodAI output: `benchmarks/goodai-ltm-benchmark/data/tests/{benchmark}/results/{agent}/`
    - Our analysis input: `benchmarks/results/goodai_ltm/subset_baseline_YYYYMMDD/`
  - Debug endpoint usage
  - Cleanup verification procedure

**Acceptance Criteria**:
- [x] Config passes strict validation.
- [x] Documentation includes complete setup and troubleshooting guide.
- [x] Result path mapping clearly documented.

**Deliverables**:
```
benchmarks/goodai-ltm-benchmark/configurations/mas_subset_32k.yml
docs/integrations/goodai-benchmark-setup.md
```

---

### W5D.2: Orchestration Script with Cleanup Verification

**Objective**: Implement robust orchestration script for subset baseline execution.

**File**: `scripts/run_subset_experiments.sh`

**Tasks**:
- [ ] Verify W5C.1 tests pass via `scripts/run_wrapper_tests.sh` before orchestration.
- [ ] Implement parallel wrapper startup (3 services):
  ```bash
  .venv/bin/python src/evaluation/agent_wrapper.py --agent-type full --port 8080 &
  .venv/bin/python src/evaluation/agent_wrapper.py --agent-type rag --port 8081 &
  .venv/bin/python src/evaluation/agent_wrapper.py --agent-type full_context --port 8082 &
  ```
- [ ] Wait for all services to be healthy (check `/health` endpoints, 60s timeout)
- [ ] Execute runs serially (avoid quota exhaustion):
  ```bash
  cd benchmarks/.venv-benchmark
  source bin/activate
  
  for agent in mas-full mas-rag mas-full-context; do
    python -m goodai_ltm_benchmark.run -a $agent -c ../configs/mas_subset_32k.yaml
    verify_cleanup $agent  # Check /sessions returns empty []
    if [ $? -ne 0 ]; then
      force_cleanup $agent  # Call POST /cleanup_force?session_id=all
    fi
  done
  ```
- [ ] Implement cleanup verification function:
  - Call `GET /sessions` after each run
  - Expect empty list `[]`
  - If not empty, call `POST /cleanup_force?session_id=all`
  - Log cleanup status to `logs/subset_cleanup_{agent}_YYYYMMDD.log`
- [ ] Start background memory polling for each agent:
  ```bash
  .venv/bin/python scripts/poll_memory_state.py \
    --port {8080|8081|8082} \
    --output logs/{agent}_memory_timeline.jsonl \
    --error-log logs/{agent}_memory_polling_errors.log \
    --interval 10 &  # Poll every 10 turns
  ```
- [ ] Gracefully shutdown wrappers after all runs complete
- [ ] Copy GoodAI results to our benchmarks directory:
  ```bash
  cp -r benchmarks/goodai-ltm-benchmark/data/tests/{prospective_memory,restaurant}/results/mas-* \
    benchmarks/results/goodai_ltm/subset_baseline_$(date +%Y%m%d)/
  ```

**Acceptance Criteria**:
- [ ] All three wrappers start and pass health checks
- [ ] Runs execute serially with verified cleanup between agents
- [ ] Memory timeline logs capture L1-L4 accumulation
- [ ] Polling errors logged separately (don't fail runs)
- [ ] Results copied to timestamped directory

**Deliverables**:
```
scripts/run_subset_experiments.sh
scripts/poll_memory_state.py
```

---

## Phase 5E: Analysis and Reporting (Days 11-12)

### W5E.1: Results Analysis Notebook

**Objective**: Analyze subset baseline to identify bottlenecks before full-scale execution.

**File**: `benchmarks/analysis/analyze_subset_baseline.ipynb`

**Tasks**:
- [ ] Parse GoodAI JSON results:
  - `{agent}/prospective_memory/results.json` → accuracy, token usage
  - `{agent}/restaurant/results.json` → accuracy, token usage
- [ ] Calculate metrics per agent:
  - Correctness: % questions answered correctly
  - Token efficiency: tokens per turn
  - Latency: Average response time per turn
- [ ] Parse memory timeline logs:
  - Plot L1/L2/L3/L4 accumulation over turns
  - Identify which tiers lag behind conversation progress
- [ ] Parse adapter-level timing logs:
  - Identify slowest storage operations (writes, queries)
  - Histogram of operation latencies
- [ ] Identify top 3 bottlenecks:
  - Adapter-level (e.g., "L3 Qdrant writes take 200ms, blocking turn completion")
  - Tier-level (e.g., "L2 promotion lags 50 turns behind conversation")
  - LLM-level (e.g., "Gemini fact extraction averages 5s per turn")
- [ ] Generate comparison table:
  | Agent | Correctness | Tokens/Turn | Latency | Top Bottleneck |
  |-------|-------------|-------------|---------|----------------|
  | MAS Full | % | N | Ms | ... |
  | MAS RAG | % | N | Ms | ... |
  | MAS Full Context | % | N | Ms | ... |

**Acceptance Criteria**:
- [ ] All three agents' results parsed successfully
- [ ] Timing breakdown identifies specific slow operations
- [ ] Recommendations include 3+ actionable optimizations

**Deliverables**:
```
benchmarks/analysis/analyze_subset_baseline.ipynb
benchmarks/results/goodai_ltm/subset_baseline_YYYYMMDD/analysis_report.md
```

---

## Phase 5F: Baseline Execution and Validation (Days 13-14)

### W5F.1: Execute Subset Baseline

**Objective**: Run verified subset baseline and validate results format.

**Tasks**:
- [ ] Execute orchestration script:
  ```bash
  bash scripts/run_subset_experiments.sh
  ```
- [ ] Monitor execution:
  - Watch memory timeline logs for L1-L4 accumulation
  - Monitor adapter timing logs for slow operations
  - Check wrapper service logs for errors
- [ ] Verify result files structure:
  ```
  benchmarks/results/goodai_ltm/subset_baseline_YYYYMMDD/
  ├── mas-full/
  │   ├── prospective_memory/
  │   │   └── results.json
  │   └── restaurant/
  │       └── results.json
  ├── mas-rag/
  │   └── ...
  ├── mas-full-context/
  │   └── ...
  └── logs/
      ├── mas_full_memory_timeline.jsonl
      ├── mas_rag_memory_timeline.jsonl
      ├── mas_full_context_memory_timeline.jsonl
      └── subset_cleanup_*.log
  ```
- [ ] Run analysis notebook to generate initial report

**Acceptance Criteria**:
- [ ] All 3 agents × 2 test types complete successfully
- [ ] Memory timeline logs show expected L1→L2→L3→L4 promotion
- [ ] Results.json files parse correctly
- [ ] Analysis report identifies at least 2 optimization opportunities

**Deliverables**:
- Timestamped results directory with all JSON outputs
- Analysis report with bottleneck identification
- Updated DEVLOG.md with execution summary

---

## Risk Management

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Gemini 4K RPM quota exhausted** | Medium | High | Serial execution, exponential backoff, fallback to Groq |
| **Database contention between agents** | Medium | Medium | PostgreSQL table locks, Redis distributed locks, separate Qdrant collections |
| **Session ID collisions** | Low | High | Agent-specific prefixes (full:, rag:, full_context:) |
| **Memory promotion lag causes stale retrieval** | High | Medium | Background polling identifies lag, manual trigger endpoints added |
| **GoodAI benchmark incompatibility** | Low | High | Separate venv with Python 3.10+, HTTP boundary isolation |
| **Cleanup failure leaves DB dirty** | Medium | Medium | Explicit cleanup verification after each run, forced cleanup on failure |

---

## Success Criteria

### Phase 5 Success Metrics

1. **Baseline Validity**:
   - [ ] 3 agents × 2 test types execute without errors
   - [ ] Results.json files contain accuracy and token usage data
   - [ ] Memory timeline logs show L1-L4 accumulation patterns

2. **System Performance**:
   - [ ] Average turn latency < 10 seconds
   - [ ] Memory promotion lag < 20 turns
   - [ ] Database operations complete within SLA (L1: 10ms, L2: 100ms, L3: 500ms, L4: 1000ms)

3. **Bottleneck Identification**:
   - [ ] Analysis identifies top 3 slowest operations
   - [ ] Recommendations include specific code/config changes
   - [ ] Estimated impact quantified (e.g., "reducing L3 write latency by 50% would reduce turn latency by 2s")

4. **Reproducibility**:
   - [ ] Orchestration script runs idempotently
   - [ ] Results directory structure matches documented format
   - [ ] Analysis notebook produces report automatically

---

## Next Steps (Post-Phase 5)

1. **Optimization Cycle** (2-3 days):
   - Implement top 3 bottleneck fixes
   - Re-run subset baseline
   - Validate improvements quantitatively

2. **Full-Scale Execution Decision** (1 day):
   - Review subset baseline correctness vs. published GPT-4 results
   - If correctness within 10%: proceed with full 12-run execution (3 agents × 2 models × 2 spans)
   - If correctness below threshold: debug retrieval logic, re-run subset

3. **Paper Submission** (AIMS 2025 deadline: TBD):
   - Include subset baseline as proof-of-concept
   - Compare full-scale results against published baselines
   - Document architectural innovations (CIAR scoring, LangGraph state management, dual indexing)

---

## Appendix A: Detailed Implementation Specification (2026-01-27)

### Conservative Rate Limiting Strategy

**Per-Agent Rate Limits** (enforced locally per wrapper instance):
- **RPM**: 100 requests per minute (vs. 4,000 available from Gemini)
- **TPM**: 1,000,000 tokens per minute (vs. 4M available from Gemini)
- **Minimum Delay**: 600ms between turns (ensures < 100 RPM even with bursts)

**Rationale**: Conservative 40:1 safety margin provides protection against:
- Concurrent wrapper instances accidentally running in parallel
- Burst traffic during graph/vector operations
- Fair use policy triggers from aggressive quota usage

**Implementation** (`RateLimiter` class in `agent_wrapper.py`):
```python
class RateLimiter:
    def __init__(self, rpm: int = 100, tpm: int = 1_000_000, min_delay: float = 0.6):
        self.rpm = rpm
        self.tpm = tpm
        self.min_delay = min_delay
        self.request_times: List[datetime] = []
        self.token_usage: List[Tuple[datetime, int]] = []
        self.consecutive_429s = 0
        self.log_file = None  # Set in __init__ to logs/rate_limiter_{agent}_{timestamp}.jsonl
    
    async def wait_if_needed(self, estimated_tokens: int):
        """Enforce RPM/TPM limits with sliding window + min delay + circuit breaker."""
        # Remove stale entries (> 60s old)
        now = datetime.now()
        self.request_times = [t for t in self.request_times if (now - t).total_seconds() < 60]
        self.token_usage = [(t, tokens) for t, tokens in self.token_usage if (now - t).total_seconds() < 60]
        
        # Enforce minimum delay per turn (600ms)
        await asyncio.sleep(self.min_delay)
        
        # Check RPM limit
        if len(self.request_times) >= self.rpm:
            wait_time = 60 - (now - self.request_times[0]).total_seconds()
            await asyncio.sleep(max(0, wait_time))
        
        # Check TPM limit
        current_tpm = sum(tokens for _, tokens in self.token_usage)
        if current_tpm + estimated_tokens >= self.tpm:
            # Wait for sliding window to clear
            await asyncio.sleep(60)
        
        # Circuit breaker: After 3 consecutive 429s, pause for 60s
        if self.consecutive_429s >= 3:
            logger.warning("Circuit breaker triggered: 3 consecutive 429 errors, pausing 60s")
            await asyncio.sleep(60)
            self.consecutive_429s = 0
        
        # Log rate limiter state to JSONL file
        self._log_state(now, estimated_tokens, len(self.request_times), current_tpm)
        
        self.request_times.append(now)
        self.token_usage.append((now, estimated_tokens))
    
    def _log_state(self, timestamp: datetime, estimated_tokens: int, current_rpm: int, current_tpm: int):
        """Write rate limiter state to JSONL file."""
        if self.log_file:
            log_entry = {
                "timestamp": timestamp.isoformat(),
                "estimated_tokens": estimated_tokens,
                "current_rpm": current_rpm,
                "current_tpm": current_tpm,
                "delay_applied": self.min_delay,
                "circuit_breaker_active": self.consecutive_429s >= 3
            }
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
```

**Token Estimation Heuristic**:
```python
def _estimate_tokens(text: str) -> int:
    """Conservative heuristic: 4 chars per token (0.25 multiplier)."""
    return int(len(text) * 0.25)
```

**Logging Strategy**: File-based logging to `logs/rate_limiter_{agent_type}_{timestamp}.jsonl`:
- No Phoenix metrics export (reduces overhead)
- JSONL format for easy parsing and analysis
- Captures: timestamp, RPM/TPM usage, delays applied, circuit breaker triggers

---

### Phoenix Observability Configuration

**Separate Projects per Agent Type**:
- `mlm-mas-dev-full` (MemoryAgent)
- `mlm-mas-dev-rag` (RAGAgent)
- `mlm-mas-dev-full-context` (FullContextAgent)

**Implementation**:
1. **Wrapper CLI**: Add `--agent-type` argument to set `AGENT_TYPE` environment variable
2. **Observability Module** (`src/utils/observability.py`): Read `AGENT_TYPE` from env, set `PHOENIX_PROJECT_NAME=mlm-mas-dev-{agent_type}`
3. **Custom Span Attributes** (added to all LLM/embedding calls):
   - `agent.type`: Agent type (full/rag/full_context)
   - `agent.session_id`: Full session ID with prefix (e.g., `full:abc123`)
   - `agent.turn_id`: Turn number within session

**Environment Variables** (add to `.env`):
```bash
PHOENIX_COLLECTOR_ENDPOINT=http://192.168.107.172:6006/v1/traces
PHOENIX_PROJECT_NAME=mlm-mas-dev-full  # Set dynamically by wrapper based on --agent-type
AGENT_TYPE=full  # Set by wrapper CLI argument
```

**Cross-Project Queries**: Custom span attributes enable filtering across projects in Phoenix UI:
```
agent.type = "full" AND agent.session_id LIKE "full:%"
```

---

### Neo4j Distributed Lock with Auto-Renewal

**Problem**: Long-running graph operations (>30s) could exceed lock TTL and cause race conditions.

**Solution**: Lifetime background task renews locks every 10s while held.

**Implementation** (`Neo4jLockManager` in `src/storage/graph_adapter.py`):

```python
class Neo4jLockManager:
    def __init__(self, redis_client: redis.StrictRedis):
        self.redis = redis_client
        self.active_locks: Dict[str, float] = {}  # session_id -> acquire_time
        self.renewal_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()  # Protects active_locks dict
    
    async def start(self):
        """Start lifetime renewal background task."""
        self.renewal_task = asyncio.create_task(self._renewal_loop())
    
    async def stop(self):
        """Stop renewal task and release all locks."""
        if self.renewal_task:
            self.renewal_task.cancel()
            try:
                await self.renewal_task
            except asyncio.CancelledError:
                pass
        
        # Release all remaining locks
        async with self.lock:
            for session_id in list(self.active_locks.keys()):
                await self._release_internal(session_id)
    
    async def _renewal_loop(self):
        """Renew all active locks every 10 seconds."""
        while True:
            try:
                await asyncio.sleep(10)
                async with self.lock:
                    for session_id in list(self.active_locks.keys()):
                        lock_key = f"neo4j:{session_id}"
                        renewed = await self.redis.expire(lock_key, 30)
                        if not renewed:
                            logger.warning(f"Lock renewal failed for {session_id}, lock may have expired")
                            del self.active_locks[session_id]
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in lock renewal loop: {e}")
    
    async def acquire(self, session_id: str, timeout: int = 30) -> str:
        """Acquire Neo4j lock for session (30s TTL)."""
        lock_key = f"neo4j:{session_id}"
        acquired = await self.redis.set(lock_key, "1", nx=True, ex=timeout)
        if not acquired:
            raise LockAcquisitionError(f"Failed to acquire lock for {session_id}")
        
        async with self.lock:
            self.active_locks[session_id] = time.time()
        
        logger.info(f"Acquired Neo4j lock: {session_id}")
        return lock_key
    
    async def release(self, session_id: str):
        """Release Neo4j lock for session."""
        async with self.lock:
            await self._release_internal(session_id)
    
    async def _release_internal(self, session_id: str):
        """Internal release without lock (assumes caller holds self.lock)."""
        lock_key = f"neo4j:{session_id}"
        await self.redis.delete(lock_key)
        if session_id in self.active_locks:
            del self.active_locks[session_id]
        logger.info(f"Released Neo4j lock: {session_id}")
    
    @asynccontextmanager
    async def lock(self, session_id: str):
        """Context manager for Neo4j lock acquisition/release."""
        await self.acquire(session_id)
        try:
            yield
        finally:
            await self.release(session_id)
```

**Usage Pattern**:
```python
async with graph_adapter.lock_manager.lock(session_id):
    # Neo4j write operations here
    await graph_adapter.store_entity_relation(...)
```

**Integration Test** (`tests/integration/test_lock_renewal.py`):
```python
async def test_lock_renewal_prevents_expiration():
    """Verify lock remains valid after 35s (> 30s TTL)."""
    lock_manager = Neo4jLockManager(redis_client)
    await lock_manager.start()
    
    session_id = "test_long_operation"
    lock_key = f"neo4j:{session_id}"
    
    # Acquire lock
    await lock_manager.acquire(session_id)
    
    # Verify lock exists
    assert await redis_client.exists(lock_key) == 1
    
    # Sleep 35 seconds (longer than 30s TTL)
    await asyncio.sleep(35)
    
    # Verify lock still exists (renewed by background task)
    assert await redis_client.exists(lock_key) == 1
    
    # Release and verify deletion
    await lock_manager.release(session_id)
    assert await redis_client.exists(lock_key) == 0
    
    await lock_manager.stop()
```

---

### LangGraph StateGraph Implementation

**AgentState TypedDict** (create in `benchmarks/goodai-ltm-benchmark/agents/runtime.py`):

```python
from typing import TypedDict, Annotated, List, Optional
from langgraph.graph import add_messages

class AgentState(TypedDict):
    """State for LangGraph-based agents."""
    messages: Annotated[List[dict], add_messages]  # Reducer for parallel updates
    session_id: str
    turn_id: int
    
    # Memory tier content
    active_context: List[str]        # L1 recent turns
    working_facts: List[dict]        # L2 session facts
    episodic_chunks: List[str]       # L3 retrieved from Qdrant
    entity_graph: dict               # L3 retrieved from Neo4j
    semantic_knowledge: List[dict]   # L4 distilled patterns
    
    # Agent output
    response: str
    confidence: float
```

**MemoryAgent Graph Structure** (update in `benchmarks/goodai-ltm-benchmark/agents/memory_agent.py`):

```python
from langgraph.graph import StateGraph, END

class MemoryAgent(BaseAgent):
    def _build_graph(self) -> CompiledGraph:
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("perceive", self._perceive_node)
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("reason", self._reason_node)
        workflow.add_node("update", self._update_node)
        workflow.add_node("respond", self._respond_node)
        
        # Wire edges (linear pipeline)
        workflow.set_entry_point("perceive")
        workflow.add_edge("perceive", "retrieve")
        workflow.add_edge("retrieve", "reason")
        workflow.add_edge("reason", "update")
        workflow.add_edge("update", "respond")
        workflow.add_edge("respond", END)
        
        return workflow.compile()
    
    async def _perceive_node(self, state: AgentState) -> AgentState:
        """Load agent state from L1 and parse incoming message."""
        # Implementation: Query L1 for recent turns, populate active_context
        pass
    
    async def _retrieve_node(self, state: AgentState) -> AgentState:
        """Query L2/L3/L4 via UnifiedMemorySystem."""
        # Implementation: Call memory_system.retrieve_context(), populate working_facts/episodic_chunks/entity_graph
        pass
    
    async def _reason_node(self, state: AgentState) -> AgentState:
        """Synthesize context and generate response via LLM."""
        # Implementation: Call LLM with tools, generate response
        pass
    
    async def _update_node(self, state: AgentState) -> AgentState:
        """Write to L1 and trigger async promotion."""
        # Implementation: Store turn in L1, trigger PromotionEngine
        pass
    
    async def _respond_node(self, state: AgentState) -> AgentState:
        """Format final response."""
        # Implementation: Format response dict, return state
        pass
```

**Isolated Node Tests** (full state mocking in `tests/evaluation/test_memory_agent.py`):

```python
@pytest.fixture
def mock_agent_state():
    """Complete AgentState fixture with all fields populated."""
    return AgentState(
        messages=[{"role": "user", "content": "Test message"}],
        session_id="full:test123",
        turn_id=1,
        active_context=["Previous turn 1", "Previous turn 2"],
        working_facts=[{"fact": "User prefers morning meetings", "ciar": 0.8}],
        episodic_chunks=["Chunk from L3 Qdrant"],
        entity_graph={"user": {"name": "Alice", "role": "manager"}},
        semantic_knowledge=[{"pattern": "Meeting scheduling", "confidence": 0.9}],
        response="",
        confidence=0.0
    )

async def test_retrieve_node_populates_episodic_chunks(memory_agent, mock_agent_state):
    """Verify _retrieve_node adds episodic_chunks to state."""
    # Call retrieve node
    updated_state = await memory_agent._retrieve_node(mock_agent_state)
    
    # Verify episodic_chunks populated
    assert len(updated_state["episodic_chunks"]) > 0
    assert updated_state["entity_graph"] is not None
```

---

### Testing Strategy Summary

**Isolated Node Tests** (full state mocking):
- Test each LangGraph node independently with complete `AgentState` fixtures
- Verify state transformations (e.g., `_retrieve_node` populates `episodic_chunks`)
- Mock all external dependencies (UnifiedMemorySystem, LLMClient)
- Target: 12+ tests per agent for full node coverage

**Integration Tests**:
- Neo4j lock renewal: Long-running operation (35s) verifies lock remains valid
- Wrapper isolation: Redis key validation ensures session prefixes don't leak
- End-to-end: Single agent run with real backends validates full pipeline

**Test Infrastructure**:
- pytest-mock for fixture management
- pytest-html for timestamped reports
- pytest-asyncio for async test support
- Reports saved to `tests/reports/{unit,integration}/` with timestamps

---

## Appendix B: Key Implementation Decisions

### Decision Log

1. **10% Subset Approach** (2026-01-26):
   - **Rationale**: Full 12-run execution (30-60 hours) risks quota exhaustion and delays AIMS 2025 submission.
   - **Impact**: Subset (2 test types, 32k span) provides bottleneck identification in 3-5 hours while validating end-to-end workflow.

2. **gemini-2.5-flash-lite Selection** (2026-01-26):
   - **Rationale**: 4K RPM (vs. 10 RPM for gemini-3-flash-preview) allows serial execution without rate limit stalls.
   - **Impact**: Estimated 3-5 hour completion time vs. 30+ hours with frequent rate limit retries.

3. **Conservative Rate Limiting (100 RPM, 1M TPM)** (2026-01-27):
   - **Rationale**: 40:1 safety margin protects against concurrent instances, burst traffic, and fair use policy triggers.
   - **Impact**: 600ms minimum delay per turn ensures safe operation well under Gemini limits.

4. **Per-Turn Delay Enforcement** (2026-01-27):
   - **Rationale**: Proactive throttling prevents quota exhaustion vs. reactive circuit breaker approach.
   - **Impact**: Slower execution (10-20% overhead) but eliminates risk of rate limit failures mid-run.

5. **Conservative Token Heuristic (0.25 multiplier)** (2026-01-27):
   - **Rationale**: 4 chars/token is conservative (typical: 3-3.5), reduces risk of TPM limit violations.
   - **Impact**: Rate limiter may be overly cautious, but prevents underestimation errors.

6. **Neo4j Lock Renewal (Lifetime Task)** (2026-01-27):
   - **Rationale**: Long-running graph operations (>30s) would expire locks without renewal.
   - **Impact**: Background task renews every 10s, prevents race conditions on complex queries.

7. **Phoenix Separate Projects per Agent** (2026-01-27):
   - **Rationale**: Isolates traces by agent type for easier debugging and comparison.
   - **Impact**: Custom span attributes enable cross-project queries when needed.

8. **File-Based Rate Limiter Logging** (2026-01-27):
   - **Rationale**: Phoenix metrics export adds overhead; JSONL files are lightweight and sufficient.
   - **Impact**: Rate limiter state captured for post-execution analysis without runtime cost.

3. **Isolated FastAPI Services** (2026-01-26):
   - **Rationale**: Database contention risk with parallel agent execution.
   - **Impact**: Three services on separate ports (8080/8081/8082) enable future parallel execution while maintaining database isolation.

4. **Session ID Prefixing** (2026-01-26):
   - **Rationale**: GoodAI generates session IDs without agent context, risking collisions.
   - **Impact**: Prefix scheme (full:, rag:, full_context:) ensures uniqueness across agents.

5. **Cleanup Verification** (2026-01-26):
   - **Rationale**: Dirty database state from failed runs invalidates subsequent experiments.
   - **Impact**: Explicit `/sessions` check + forced cleanup ensures clean slate for each run.

6. **Background Memory Polling** (2026-01-26):
   - **Rationale**: Memory promotion lag is suspected bottleneck but not visible in GoodAI results.
   - **Impact**: Turn-by-turn L1-L4 snapshots enable lag diagnosis without blocking main execution.

---

## Appendix B: Environment Requirements

### Main Project Environment

```bash
# Python 3.12.3 required
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Verify LangGraph installed
python -c "import langgraph; print(langgraph.__version__)"

# Start services
python src/evaluation/agent_wrapper.py --agent-type full --port 8080
```

### GoodAI Benchmark Environment

```bash
# Python 3.10+ required
cd benchmarks
python3.10 -m venv .venv-benchmark
source .venv-benchmark/bin/activate

# Install GoodAI benchmark
cd goodai-ltm-benchmark
pip install -e .

# Verify installation
python -m goodai_ltm_benchmark.run --help
```

### Database Requirements

- **PostgreSQL**: 13+ (facts, episodes tables)
- **Redis**: 6+ (active context, distributed locks)
- **Qdrant**: 1.9+ (episodic memory, separate collections per agent)
- **Neo4j**: 5.22+ (knowledge graph)
- **Typesense**: 26+ (semantic search)

---

## Appendix C: Timeline Summary

| Phase | Days | Deliverables |
|-------|------|--------------|
| **5A: Infrastructure Setup** | 2 | GoodAI benchmark installed, AGENTS.MD updated, config validator |
| **5B: Agent Implementation** | 3 | BaseAgent, MemoryAgent, RAGAgent, FullContextAgent with 40+ tests |
| **5C: Wrapper Services** | 3 | FastAPI wrappers with isolation, GoodAI interfaces |
| **5D: Execution Infrastructure** | 2 | Orchestration script, configs, documentation |
| **5E: Analysis and Reporting** | 2 | Analysis notebook, bottleneck identification |
| **5F: Baseline Execution** | 2 | Subset baseline run, validation, initial report |
| **Total** | **14 days** | End-to-end 10% subset baseline with bottleneck analysis |

---

**END OF PHASE 5 IMPLEMENTATION PLAN v2.0**

**Objective**: Implement the stateless RAG baseline that uses only a single vector store.

**File**: `src/agents/rag_agent.py`

**Tasks**:
- [ ] Create `RAGAgent` class inheriting from `BaseAgent`
- [ ] Implement single-pass retrieval:
  - Query single Qdrant collection (pre-indexed with full history)
  - No state management between turns
  - No L1/L2 Operating Memory
- [ ] Configure retrieval parameters (top_k, similarity threshold)
- [ ] Implement prompt template for RAG context injection
- [ ] Add instrumentation for retrieval latency and result count

**Architectural Constraints**:
- No `PersonalMemoryState` (stateless)
- No async consolidation or promotion
- Single vector query per turn (no tiered retrieval)

**Acceptance Criteria**:
- [ ] Stateless operation verified (no state persists between calls)
- [ ] Single Qdrant query per turn (verified via logs)
- [ ] Response quality comparable to MemoryAgent on short contexts
- [ ] Unit tests (8+ tests)

**Deliverables**:
```
src/agents/rag_agent.py
tests/agents/test_rag_agent.py
```

---

### W5A.4: FullContextAgent Implementation (Naive Baseline)

**Objective**: Implement the naive full-context baseline that passes entire history to LLM.

**File**: `src/agents/full_context_agent.py`

**Tasks**:
- [ ] Create `FullContextAgent` class inheriting from `BaseAgent`
- [ ] Implement full history retrieval from Redis
- [ ] Concatenate all turns into single prompt
- [ ] Handle context window limits (truncation strategy)
- [ ] Add instrumentation for prompt size and token counts
- [ ] Implement graceful degradation when context exceeds limits

**Architectural Constraints**:
- No retrieval or filtering (pass everything)
- No knowledge distillation
- Maximum token consumption per turn

**Acceptance Criteria**:
- [ ] Full history included in every prompt (verified)
- [ ] Handles context overflow gracefully (truncation or error)
- [ ] Token count metrics accurate
- [ ] Unit tests (6+ tests)

**Deliverables**:
```
src/agents/full_context_agent.py
tests/agents/test_full_context_agent.py
```

---

### W5A.5: Agent Package Integration

**Objective**: Update `src/agents/__init__.py` and ensure all agents are properly exported.

**Tasks**:
- [ ] Update `src/agents/__init__.py` with all exports
- [ ] Create `AgentFactory` for configuration-based instantiation
- [ ] Add type hints and docstrings
- [ ] Verify LangGraph dependency works (`langgraph>=0.1.0` in requirements.txt)

**Deliverables**:
```
src/agents/__init__.py (updated)
src/agents/factory.py
```

---

## Phase 5B: Benchmark Infrastructure (Week 2-3)

### W5B.1: Agent Wrapper API

**Objective**: Create FastAPI server exposing `/run_turn` endpoint for GoodAI benchmark integration.

**File**: `src/evaluation/agent_wrapper.py`

**Tasks**:
- [ ] Create FastAPI application with `/run_turn` endpoint
- [ ] Implement request/response models matching GoodAI benchmark format:
  ```python
  class RunTurnRequest(BaseModel):
      history: List[Dict[str, str]]  # Previous turns
      message: str                    # Current user message
      session_id: str                 # Conversation identifier
  
  class RunTurnResponse(BaseModel):
      response: str                   # Agent's response
      metadata: Dict[str, Any]        # Instrumentation data
  ```
- [ ] Add CLI arguments for agent selection:
  - `--agent {full|rag|full_context}`
  - `--model {gemini|groq}`
  - `--port {default: 8080}`
- [ ] Implement graceful shutdown and health check endpoints
- [ ] Add CORS configuration for benchmark runner

**Acceptance Criteria**:
- [ ] All three agents accessible via same endpoint (config-based)
- [ ] Request/response format matches GoodAI benchmark
- [ ] Health check returns agent status and memory system health
- [ ] Unit tests for API endpoints (10+ tests)

**Deliverables**:
```
src/evaluation/agent_wrapper.py
src/evaluation/api_models.py
tests/evaluation/test_agent_wrapper.py
```

---

### W5B.2: Instrumentation & Logging

**Objective**: Implement structured logging for comprehensive metrics collection.

**File**: `src/evaluation/instrumentation.py`

**Tasks**:
- [ ] Create `InstrumentationLogger` class with JSONL output
- [ ] Capture per-turn metrics:
  ```python
  @dataclass
  class TurnMetrics:
      session_id: str
      turn_number: int
      agent_type: str
      model_name: str
      
      # Timing
      total_latency_ms: float
      retrieval_latency_ms: float
      llm_latency_ms: float
      update_latency_ms: float
      
      # Tokens
      prompt_tokens: int
      completion_tokens: int
      total_tokens: int
      
      # Memory system
      l1_hits: int
      l2_hits: int
      l3_hits: int
      l4_hits: int
      cache_hit_rate: float
      
      # Quality
      retrieval_count: int
      context_length: int
      
      timestamp: datetime
  ```
- [ ] Integrate with existing metrics system (`src/storage/metrics/`)
- [ ] Add log rotation and compression for long runs
- [ ] Create metrics aggregation utilities

**Acceptance Criteria**:
- [ ] All metrics captured for every turn
- [ ] JSONL format parseable by analysis notebook
- [ ] Log files organized by experiment run
- [ ] No performance impact >5% from instrumentation

**Deliverables**:
```
src/evaluation/instrumentation.py
src/evaluation/metrics_models.py
tests/evaluation/test_instrumentation.py
```

---

### W5B.3: Arize Phoenix Integration

**Objective**: Configure LLM call tracing via Arize Phoenix for debugging and analysis.

**Tasks**:
- [ ] Add Phoenix tracer initialization to agent wrapper
- [ ] Configure OTLP exporter to Phoenix server (`skz-dev-lv:6006`)
- [ ] Add trace context propagation through agent nodes
- [ ] Create dashboard queries for common debugging scenarios
- [ ] Document Phoenix usage in `docs/integrations/phoenix-setup.md`

**Environment Configuration**:
```bash
# Add to .env
PHOENIX_HOST=localhost
PHOENIX_PORT=6006
PHOENIX_GRPC_PORT=4317
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

**Acceptance Criteria**:
- [ ] All LLM calls visible in Phoenix UI
- [ ] Latency breakdown per agent node
- [ ] Token usage tracked per model
- [ ] Traces linkable to JSONL instrumentation logs

**Deliverables**:
```
src/evaluation/tracing.py
docs/integrations/phoenix-setup.md
```

---

### W5B.4: GoodAI LTM Benchmark Integration

**Objective**: Clone and configure the GoodAI LTM Benchmark to work with our agent wrapper.

**Tasks**:
- [ ] Clone `goodai-ltm-benchmark` repository to orchestrator node
- [ ] Create benchmark configuration files for our agents
- [ ] Implement dataset preprocessing (if needed)
- [ ] Create wrapper script for benchmark execution
- [ ] Validate benchmark can call our `/run_turn` endpoint

**Directory Structure**:
```
external/
└── goodai-ltm-benchmark/     # Cloned repository
    ├── run_benchmark.py
    ├── datasets/
    └── configs/
        ├── mas_full_system.yaml
        ├── mas_rag_baseline.yaml
        └── mas_full_context.yaml
```

**Acceptance Criteria**:
- [ ] Benchmark runner successfully calls agent wrapper
- [ ] At least one test scenario completes end-to-end
- [ ] Results written to expected output format
- [ ] Documentation for benchmark setup

**Deliverables**:
```
external/goodai-ltm-benchmark/ (cloned)
external/goodai-ltm-benchmark/configs/mas_*.yaml
docs/integrations/goodai-benchmark-setup.md
```

---

### W5B.5: End-to-End Dry Run

**Objective**: Validate complete pipeline with a short test before full benchmark execution.

**Tasks**:
- [ ] Run single short test (e.g., 10-turn conversation) with each agent
- [ ] Verify instrumentation captures all metrics
- [ ] Check Phoenix traces appear correctly
- [ ] Validate result files are written and parseable
- [ ] Fix any integration issues discovered

**Validation Checklist**:
- [ ] MemoryAgent: Full lifecycle (L1→L2→L3→L4) exercised
- [ ] RAGAgent: Single vector query verified
- [ ] FullContextAgent: Full history concatenation verified
- [ ] Metrics: All fields populated in JSONL
- [ ] Tracing: LLM calls visible in Phoenix
- [ ] Results: GoodAI benchmark output parseable

**Deliverables**:
```
benchmarks/results/goodai_ltm/dry_run/
├── full_system_gemini_dry_run/
├── rag_baseline_gemini_dry_run/
└── full_context_gemini_dry_run/
```

---

## Phase 5C: Experimental Execution (Week 3-5)

### W5C.1: Experiment Automation Script

**Objective**: Create shell script to automate all 12 experimental runs.

**File**: `scripts/run_experiments.sh`

**Tasks**:
- [ ] Create experiment configuration matrix:
  ```bash
  AGENTS=("full" "rag" "full_context")
  MODELS=("gemini-3-flash-preview" "openai/gpt-oss-120b")
  MEMORY_SPANS=("32k" "120k")
  ```
- [ ] Implement run loop with:
  - Agent wrapper startup with correct config
  - Benchmark execution
  - Result collection and archiving
  - Graceful cleanup between runs
- [ ] Add progress reporting and ETA estimation
- [ ] Implement resume capability (skip completed runs)
- [ ] Add resource monitoring (CPU, memory, disk)

**Script Structure**:
```bash
#!/bin/bash
# scripts/run_experiments.sh
#
# Usage: ./scripts/run_experiments.sh [--resume] [--dry-run]
#
# Executes all 12 experimental configurations for GoodAI LTM Benchmark

set -euo pipefail

# Configuration
RESULTS_DIR="benchmarks/results/goodai_ltm"
LOG_DIR="logs/experiments"
WRAPPER_PORT=8080

# Experiment matrix
declare -a AGENTS=("full" "rag" "full_context")
declare -a MODELS=("gemini-3-flash-preview" "openai/gpt-oss-120b")
declare -a SPANS=("32k" "120k")

run_experiment() {
    local agent=$1
    local model=$2
    local span=$3
    local run_id="${agent}_${model}_${span}_$(date +%Y%m%d_%H%M%S)"
    
    echo "[$(date)] Starting: $run_id"
    
    # Start agent wrapper
    # Run benchmark
    # Collect results
    # Cleanup
}

main() {
    for agent in "${AGENTS[@]}"; do
        for model in "${MODELS[@]}"; do
            for span in "${SPANS[@]}"; do
                run_experiment "$agent" "$model" "$span"
            done
        done
    done
}

main "$@"
```

**Acceptance Criteria**:
- [ ] All 12 configurations can run unattended
- [ ] Resume works correctly after interruption
- [ ] Results archived with consistent naming
- [ ] Resource usage logged throughout

**Deliverables**:
```
scripts/run_experiments.sh
scripts/lib/experiment_utils.sh
```

---

### W5C.2: Execute Full Benchmark Suite

**Objective**: Run all 12 experimental configurations and collect results.

**Experiment Matrix** (12 runs total):

| Run | Agent | Model | Memory Span | Est. Duration |
|-----|-------|-------|-------------|---------------|
| 1 | MemoryAgent | gemini-3-flash-preview | 32k | 2-4 hours |
| 2 | MemoryAgent | gemini-3-flash-preview | 120k | 4-8 hours |
| 3 | MemoryAgent | openai/gpt-oss-120b | 32k | 2-4 hours |
| 4 | MemoryAgent | openai/gpt-oss-120b | 120k | 4-8 hours |
| 5 | RAGAgent | gemini-3-flash-preview | 32k | 1-2 hours |
| 6 | RAGAgent | gemini-3-flash-preview | 120k | 2-4 hours |
| 7 | RAGAgent | openai/gpt-oss-120b | 32k | 1-2 hours |
| 8 | RAGAgent | openai/gpt-oss-120b | 120k | 2-4 hours |
| 9 | FullContextAgent | gemini-3-flash-preview | 32k | 1-2 hours |
| 10 | FullContextAgent | gemini-3-flash-preview | 120k | N/A (context limit) |
| 11 | FullContextAgent | openai/gpt-oss-120b | 32k | 1-2 hours |
| 12 | FullContextAgent | openai/gpt-oss-120b | 120k | N/A (context limit) |

**Note**: FullContextAgent at 120k tokens will likely hit context limits. Document this as expected behavior demonstrating why memory systems are necessary.

**Tasks**:
- [ ] Execute runs 1-4 (MemoryAgent, both models, both spans)
- [ ] Execute runs 5-8 (RAGAgent, both models, both spans)
- [ ] Execute runs 9-12 (FullContextAgent, note failures at 120k)
- [ ] Monitor system stability via `htop`, `docker stats`
- [ ] Capture any errors or anomalies in experiment log

**Monitoring Commands**:
```bash
# Resource monitoring
htop
docker stats

# Log tailing
tail -f logs/experiments/current_run.log

# Check Phoenix traces
open http://localhost:6006
```

**Deliverables**:
```
benchmarks/results/goodai_ltm/
├── full_gemini_32k_YYYYMMDD/
│   ├── benchmark_results.json
│   ├── instrumentation.jsonl
│   └── summary.md
├── full_gemini_120k_YYYYMMDD/
├── full_groq_32k_YYYYMMDD/
├── full_groq_120k_YYYYMMDD/
├── rag_gemini_32k_YYYYMMDD/
├── rag_gemini_120k_YYYYMMDD/
├── rag_groq_32k_YYYYMMDD/
├── rag_groq_120k_YYYYMMDD/
├── full_context_gemini_32k_YYYYMMDD/
├── full_context_gemini_120k_YYYYMMDD/  (expected failure)
├── full_context_groq_32k_YYYYMMDD/
└── full_context_groq_120k_YYYYMMDD/    (expected failure)
```

---

### W5C.3: Results Organization & Archiving

**Objective**: Organize raw results into structured archive for analysis.

**Tasks**:
- [ ] Validate all result files are complete and parseable
- [ ] Create consolidated results index (`results_index.json`)
- [ ] Generate per-run summary reports
- [ ] Archive raw instrumentation logs (compress if >100MB)
- [ ] Create git tag for reproducibility (`v0.5.0-benchmark-results`)

**Results Index Schema**:
```json
{
  "experiment_date": "2026-01-XX",
  "total_runs": 12,
  "completed_runs": 10,
  "failed_runs": 2,
  "runs": [
    {
      "run_id": "full_gemini_32k_20260115",
      "agent": "MemoryAgent",
      "model": "gemini-3-flash-preview",
      "memory_span": "32k",
      "status": "completed",
      "duration_hours": 3.5,
      "goodai_score": 0.85,
      "results_path": "benchmarks/results/goodai_ltm/full_gemini_32k_20260115/"
    }
  ]
}
```

**Deliverables**:
```
benchmarks/results/goodai_ltm/results_index.json
benchmarks/results/goodai_ltm/archive/  (compressed logs)
```

---

## Phase 5D: Analysis & Reporting (Week 5-6)

### W5D.1: Analysis Notebook Development

**Objective**: Create Jupyter notebook for parsing and analyzing benchmark results.

**File**: `benchmarks/analysis/analyze_results.ipynb`

**Tasks**:
- [ ] Load all result files from `results_index.json`
- [ ] Parse GoodAI LTM benchmark scores
- [ ] Parse instrumentation JSONL files
- [ ] Calculate aggregate statistics:
  - Mean, median, P50, P95, P99 for latency
  - Total token counts and costs
  - Cache hit rates per tier
- [ ] Generate comparison visualizations:
  - Bar charts: GoodAI scores by agent/model
  - Box plots: Latency distributions
  - Line charts: Token usage over conversation length
- [ ] Export tables in Markdown format for paper

**Notebook Sections**:
1. Data Loading & Validation
2. Functional Correctness Analysis (GoodAI Scores)
3. Operational Efficiency Analysis (Latency, Tokens)
4. Memory System Analysis (Cache Hits, Tier Usage)
5. Cost Analysis (Token costs per configuration)
6. Table Generation (Paper-ready Markdown)
7. Visualization Export (PNG/SVG for paper)

**Acceptance Criteria**:
- [ ] All 12 runs analyzed (or failures documented)
- [ ] Statistical significance tests for key comparisons
- [ ] Visualizations publication-quality
- [ ] Tables match paper format requirements

**Deliverables**:
```
benchmarks/analysis/analyze_results.ipynb
benchmarks/analysis/figures/
├── goodai_scores_comparison.png
├── latency_distribution.png
├── token_usage_by_span.png
└── cache_hit_rates.png
benchmarks/analysis/tables/
├── table1_functional_correctness.md
└── table2_operational_efficiency.md
```

---

### W5D.2: Generate Paper Tables

**Objective**: Create the two key result tables for the AIMS 2025 paper.

**Table 1: Functional Correctness (GoodAI LTM Scores)**

```markdown
| System | Model | 32k Tokens | 120k Tokens |
|--------|-------|------------|-------------|
| **Hybrid Memory (Full)** | gemini-3-flash-preview | X.XX | X.XX |
| **Hybrid Memory (Full)** | openai/gpt-oss-120b | X.XX | X.XX |
| Standard RAG Baseline | gemini-3-flash-preview | X.XX | X.XX |
| Standard RAG Baseline | openai/gpt-oss-120b | X.XX | X.XX |
| Full-Context Baseline | gemini-3-flash-preview | X.XX | N/A* |
| Full-Context Baseline | openai/gpt-oss-120b | X.XX | N/A* |

*Context window exceeded
```

**Table 2: Operational Efficiency**

```markdown
| System | Latency P95 (ms) | Tokens/Turn | L2 Cache Hit % | Cost/1k Turns |
|--------|------------------|-------------|----------------|---------------|
| **Hybrid Memory (Full)** | XXX | XXX | XX% | $X.XX |
| Standard RAG Baseline | XXX | XXX | N/A | $X.XX |
| Full-Context Baseline | XXX | XXX | N/A | $X.XX |
```

**Tasks**:
- [ ] Calculate all metrics from raw data
- [ ] Format tables per AIMS 2025 submission guidelines
- [ ] Add statistical confidence intervals where appropriate
- [ ] Write table captions and footnotes
- [ ] Export in both Markdown and LaTeX formats

**Deliverables**:
```
benchmarks/analysis/tables/table1_functional_correctness.md
benchmarks/analysis/tables/table1_functional_correctness.tex
benchmarks/analysis/tables/table2_operational_efficiency.md
benchmarks/analysis/tables/table2_operational_efficiency.tex
```

---

### W5D.3: Paper Revision Support

**Objective**: Provide all materials needed for AIMS 2025 paper revision.

**Tasks**:
- [ ] Write results section draft with quantitative findings
- [ ] Create figure captions for all visualizations
- [ ] Document experimental methodology for reproducibility section
- [ ] Prepare supplementary materials (extended tables, raw data access)
- [ ] Review against AIMS 2025 submission requirements

**Paper Sections to Update**:
1. **Abstract**: Add quantitative claims (e.g., "X% improvement over RAG baseline")
2. **Methodology**: Document benchmark setup and configurations
3. **Results**: Insert tables and figures
4. **Discussion**: Analyze why hybrid system outperforms baselines
5. **Conclusion**: Summarize empirical findings

**Deliverables**:
```
docs/paper/
├── results_section_draft.md
├── methodology_section_draft.md
├── figures/  (symlink to benchmarks/analysis/figures/)
└── supplementary/
    ├── extended_results.md
    └── reproducibility_guide.md
```

---

## Success Criteria

### Phase 5A (Agent Implementation)
- [ ] All three agent classes implemented and tested
- [ ] LangGraph StateGraph wiring functional
- [ ] 30+ new unit tests passing
- [ ] Integration tests with mocked backends passing

### Phase 5B (Benchmark Infrastructure)
- [ ] FastAPI wrapper responding to `/run_turn`
- [ ] GoodAI benchmark successfully calls wrapper
- [ ] Instrumentation captures all required metrics
- [ ] Phoenix traces visible for all LLM calls
- [ ] End-to-end dry run successful

### Phase 5C (Experimental Execution)
- [ ] At least 10 of 12 runs completed successfully
- [ ] 2 expected failures documented (FullContextAgent at 120k)
- [ ] All results archived with consistent structure
- [ ] No data loss or corruption

### Phase 5D (Analysis & Reporting)
- [ ] Analysis notebook runs end-to-end
- [ ] Both paper tables generated
- [ ] Statistical significance established for key claims
- [ ] Paper revision materials complete

### Overall Phase 5
- [ ] Hypothesis validated: Hybrid system matches or exceeds baselines on accuracy
- [ ] Hypothesis validated: Hybrid system significantly more efficient than Full-Context
- [ ] All code merged to `dev-mas` branch
- [ ] Documentation updated
- [ ] Results reproducible from archived data

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM API rate limits during benchmark | Medium | High | Use Groq as fallback, implement retry with exponential backoff |
| Context window exceeded (FullContextAgent 120k) | High | Low | Expected and documented; proves value of memory system |
| GoodAI benchmark format mismatch | Medium | Medium | Validate format in dry run; implement adapter if needed |
| Database performance under load | Low | Medium | Pre-warm caches; monitor via existing metrics system |
| LangGraph integration issues | Medium | High | Start with simple graph; add complexity incrementally |
| Insufficient result differentiation | Low | High | Ensure diverse test scenarios; analyze per-scenario breakdown |
| Phoenix tracing overhead | Low | Low | Make tracing optional via env var |
| Experiment duration exceeds estimate | Medium | Medium | Parallelize where possible; run overnight |

---

## Timeline Summary

```
Week 1 (Jan 6-10, 2026):
├── W5A.1: BaseAgent abstract class
├── W5A.2: MemoryAgent implementation (start)
└── W5A.3: RAGAgent implementation

Week 2 (Jan 13-17, 2026):
├── W5A.2: MemoryAgent implementation (complete)
├── W5A.4: FullContextAgent implementation
├── W5A.5: Agent package integration
└── W5B.1: Agent Wrapper API (start)

Week 3 (Jan 20-24, 2026):
├── W5B.1: Agent Wrapper API (complete)
├── W5B.2: Instrumentation & Logging
├── W5B.3: Arize Phoenix Integration
├── W5B.4: GoodAI Benchmark Integration
└── W5B.5: End-to-End Dry Run

Week 4 (Jan 27-31, 2026):
├── W5C.1: Experiment Automation Script
└── W5C.2: Execute runs 1-6 (MemoryAgent + RAGAgent with Gemini)

Week 5 (Feb 3-7, 2026):
├── W5C.2: Execute runs 7-12 (remaining configurations)
├── W5C.3: Results Organization & Archiving
└── W5D.1: Analysis Notebook Development (start)

Week 6 (Feb 10-14, 2026):
├── W5D.1: Analysis Notebook Development (complete)
├── W5D.2: Generate Paper Tables
└── W5D.3: Paper Revision Support

Milestone: Feb 14, 2026 - Phase 5 Complete, Paper Materials Ready
```

---

## References

### Specifications
- [UC-01: Full System Agent](../benchmark_use_cases.md)
- [UC-02: Standard RAG Baseline](../benchmark_use_cases.md)
- [UC-03: Full-Context Baseline](../benchmark_use_cases.md)
- [SD-01: Full System Sequence](../benchmark_sequence_diagrams.md)
- [SD-02: RAG Baseline Sequence](../benchmark_sequence_diagrams.md)
- [SD-03: Full-Context Sequence](../benchmark_sequence_diagrams.md)
- [Agent Framework Spec](../specs/spec-phase3-agent-integration.md)

### Architecture
- [ADR-003: Four-Tier Memory Architecture](../ADR/003-four-layers-memory.md)
- [ADR-004: CIAR Scoring Formula](../ADR/004-ciar-scoring-formula.md)
- [ADR-006: Free-Tier LLM Strategy](../ADR/006-free-tier-llm-strategy.md)

### Previous Plans

### External Resources
- [GoodAI LTM Benchmark](https://github.com/GoodAI/goodai-ltm-benchmark)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Arize Phoenix Documentation](https://docs.arize.com/phoenix/)

---

## Appendix A: File Deliverables Summary

### New Source Files
```
src/agents/
├── base_agent.py          # Abstract base class
├── models.py              # AgentInput, AgentOutput, AgentState
├── memory_agent.py        # Full system (UC-01)
├── rag_agent.py           # RAG baseline (UC-02)
├── full_context_agent.py  # Full-context baseline (UC-03)
├── factory.py             # Agent factory
└── __init__.py            # Updated exports

src/evaluation/
├── agent_wrapper.py       # FastAPI server
├── api_models.py          # Request/response models
├── instrumentation.py     # JSONL logging
├── metrics_models.py      # TurnMetrics dataclass
├── tracing.py             # Phoenix integration
└── benchmark_runner.py    # Benchmark orchestration
```

### New Test Files
```
tests/agents/
├── test_base_agent.py
├── test_memory_agent.py
├── test_rag_agent.py
└── test_full_context_agent.py

tests/evaluation/
├── test_agent_wrapper.py
└── test_instrumentation.py

tests/integration/
└── test_memory_agent_integration.py
```

### New Scripts
```
scripts/
├── run_experiments.sh
└── lib/experiment_utils.sh
```

### New Benchmark Files
```
benchmarks/
├── analysis/
│   ├── analyze_results.ipynb
│   ├── figures/
│   └── tables/
└── results/
    └── goodai_ltm/
        └── results_index.json
```

### New Documentation
```
docs/
├── integrations/
│   ├── phoenix-setup.md
│   └── goodai-benchmark-setup.md
└── paper/
    ├── results_section_draft.md
    ├── methodology_section_draft.md
    └── supplementary/
```

---

## Appendix B: Environment Requirements

### API Keys (in `.env`)
```bash
# LLM Providers
GOOGLE_API_KEY=xxx          # Gemini (NOT GEMINI_API_KEY)
GROQ_API_KEY=xxx            # Groq

# Observability
PHOENIX_HOST=localhost
PHOENIX_PORT=6006
PHOENIX_GRPC_PORT=4317

# Databases (existing)
DATA_NODE_IP=xxx
POSTGRES_USER=xxx
POSTGRES_PASSWORD=xxx
NEO4J_USER=xxx
NEO4J_PASSWORD=xxx
```

### Python Dependencies (already in requirements.txt)
```
langgraph>=0.1.0
langchain-core>=0.2.0
fastapi>=0.100.0
uvicorn>=0.23.0
```

### System Requirements
- Python 3.12.3+
- Docker (for Phoenix)
- 16GB+ RAM (for 120k token tests)
- Stable network to LLM APIs

---

*Document created: January 3, 2026*  
*Last updated: January 3, 2026*  
*Author: Development Team*

---


# Phase 5 Readiness Checklists (Graded)

**Date:** 2026-01-02  
**Purpose:** Provide a structured, graded readiness framework for Phase 5, aligned to the four-tier cognitive memory architecture and lifecycle engines. Grades: Green (meets bar), Amber (minor gaps), Red (blocking gaps). Each item lists required evidence and project-specific improvement guidance.

## 2026-01-03 Final Status - Phase 4 Complete ✅

**🟢 FULL TEST SUITE PASSING: 574/586 (0 failed)**

All Phase 4 integration hardening complete. Test suite fully green, all lifecycle paths verified.

### Test Results Summary (2026-01-03)
```bash
================== 574 passed, 12 skipped, 0 failed in 131.29s ==================

Integration Tests (4/4):
✅ test_l1_to_l2_promotion_with_ciar_filtering
✅ test_l2_to_l3_consolidation_with_episode_clustering (FIXED)
✅ test_l3_to_l4_distillation_with_knowledge_synthesis
✅ test_full_lifecycle_end_to_end

Storage Adapters (199/199):
✅ Redis: 32/32 | PostgreSQL: 24/24 | Qdrant: 46/46 | Neo4j: 53/53 | Typesense: 44/44

Memory Tiers (61/61):
✅ L1: 17/17 | L2: 12/12 | L3: 16/16 | L4: 16/16

Lifecycle Engines (59/59):
✅ Promotion: 10/10 | Consolidation: 9/9 | Distillation: 12/12
✅ FactExtractor: 4/4 | TopicSegmenter: 10/10 | KnowledgeSynthesizer: 14/14

Agent Tools (60/60):
✅ CIAR Tools: 16/16 | Tier Tools: 18/18 | Unified Tools: 26/26
```

### Critical Fix: Qdrant Scroll vs Search
- **Problem:** Test stored episodes successfully but failed to retrieve them with `search()` + filter
- **Root Cause:** Qdrant `search()` is vector-similarity-first; dummy query vector `[0.1]*768` had ~0 similarity to real embeddings, causing filter-based queries to return nothing
- **Solution:** Added `scroll()` method to `QdrantAdapter` for pure filter-based retrieval; updated test to use `scroll()` instead of `search()`
- **Full Report:** [docs/reports/qdrant-scroll-vs-search-debugging-2026-01-03.md](../reports/qdrant-scroll-vs-search-debugging-2026-01-03.md)

### Key Implementation Changes
| File | Change |
|------|--------|
| `src/storage/qdrant_adapter.py` | Added `scroll()` method for filter-only retrieval (76 lines) |
| `tests/integration/test_memory_lifecycle.py` | Changed Qdrant verification from `search()` to `scroll()` |
| `tests/storage/test_qdrant_adapter.py` | Updated backward compatibility test for session_id filter behavior |

### Design Guideline Established
- Use `search()` for semantic similarity queries ("find items similar to X")
- Use `scroll()` for metadata-based queries ("find all items matching session_id=Y")

---

## 2026-01-03 Status Update (Session 1)
- See daily report [docs/reports/preliminary_readiness_checks_version-0.7_upto10feb2026.md](../reports/preliminary_readiness_checks_version-0.7_upto10feb2026.md) and log entry in [DEVLOG.md](../../DEVLOG.md).
- ~~Current gap: end-to-end lifecycle test still fails due to zero L4 knowledge documents; distillation now forces processing with rule-based fallback but episode retrieval remains sparse in integration flow.~~
- ~~Next action: verify episodic retrieval and Typesense writes during distillation, then rerun full lifecycle test and update grading outcomes.~~
- **UPDATE:** All core lifecycle tests now pass. See Session 2 update above.

## 1. Architecture & ADR Alignment
- **Tier responsibilities and flow (L1–L4)** — Evidence: [docs/ADR/003-four-layers-memory.md](../ADR/003-four-layers-memory.md), [AGENTS.MD](../../AGENTS.MD), [docs/reports/adr-003-architecture-review.md](../reports/adr-003-architecture-review.md). Improvement: ensure diagrams and text reflect current engine code paths and dual-index commitments.
- **CIAR policy compliance** — Evidence: [docs/ADR/004-ciar-scoring-formula.md](../ADR/004-ciar-scoring-formula.md), [config/ciar_config.yaml](../../config/ciar_config.yaml), [src/memory/ciar_scorer.py](../../src/memory/ciar_scorer.py). Improvement: verify decay/recency parameters match ADR defaults per domain; record rationale in config comments.
- **Lifecycle engines coverage (promotion → consolidation → distillation)** — Evidence: [src/memory/engines/promotion_engine.py](../../src/memory/engines/promotion_engine.py), [src/memory/engines/consolidation_engine.py](../../src/memory/engines/consolidation_engine.py), [src/memory/engines/distillation_engine.py](../../src/memory/engines/distillation_engine.py), [docs/reports/adr-003-architecture-review.md](../reports/adr-003-architecture-review.md). Improvement: document retry/circuit-breaker thresholds and ensure tests exercise degradation paths.
- **Dual-index guarantees (L3 Qdrant + Neo4j; L4 Typesense)** — Evidence: [src/memory/tiers/episodic_memory_tier.py](../../src/memory/tiers/episodic_memory_tier.py), [src/memory/tiers/semantic_memory_tier.py](../../src/memory/tiers/semantic_memory_tier.py). Improvement: specify divergence detection and repair runbooks; add idempotent write checks.
- **Operating vs persistent layer boundaries** — Evidence: [src/memory/tiers/active_context_tier.py](../../src/memory/tiers/active_context_tier.py), [src/memory/tiers/working_memory_tier.py](../../src/memory/tiers/working_memory_tier.py). Improvement: confirm hot-path TTL/windowing constraints (10–20 turns, 24h TTL) are enforced and logged.

## 2. Implementation Depth
- **Tier behavior completeness** — Evidence: [src/memory/tiers/base_tier.py](../../src/memory/tiers/base_tier.py) plus concrete tiers above. Improvement: add edge-case handling (empty windows, backpressure) and metrics per method entry/exit.
- **Data contracts (Fact, Episode, KnowledgeDocument)** — Evidence: [src/memory/models.py](../../src/memory/models.py). Improvement: validate provenance fields persist across L2→L4; align required/optional fields with engine assumptions.
- **LLM orchestration and fallbacks** — Evidence: [src/utils/llm_client.py](../../src/utils/llm_client.py), [docs/llm_provider_guide.md](../llm_provider_guide.md), [docs/llm_provider_guide.md](../llm_provider_guide.md). Improvement: document routing by task (segmentation vs summarization vs scoring) and ensure GOOGLE_API_KEY usage is uniform.
- **Storage adapters and metrics** — Evidence: [src/storage/](../../src/storage), [docs/metrics_usage.md](../metrics_usage.md). Improvement: confirm metrics on errors/timeouts; document reconnection/backoff policies and pools per backend.

## 3. Testing Realism & Coverage
- **Unit vs integration breadth** — Evidence: [tests/memory/](../../tests/memory), [tests/storage/](../../tests/storage), [tests/utils/](../../tests/utils), [tests/integration/](../../tests/integration). Improvement: map each lifecycle path to at least one integration test; add failure-injection (backend unavailable, partial index writes).
- **Mocks vs real backends** — Evidence: skip markers in integration and LLM tests, [tests/integration/test_llmclient_real.py](../../tests/integration/test_llmclient_real.py), [tests/utils/test_gemini_structured_output.py](../../tests/utils/test_gemini_structured_output.py). Improvement: prioritize real-backend runs for critical paths under feature flags; retain mocks only for isolation.
- **Coverage posture** — Evidence: [htmlcov/status.json](../../htmlcov/status.json), [docs/llm_provider_guide.md](../llm_provider_guide.md). Improvement: raise coverage on lifecycle error branches, divergence repair, and retry/circuit-breaker logic.
- **Acceptance and performance tests** — Evidence: [benchmarks/README.md](../../benchmarks/README.md), [benchmarks/configs/](../../benchmarks/configs). Improvement: ensure latency gate (<2s p95 lifecycle) is enforced in automated checks with real backends.

## 4. Performance & Benchmarking
- **Latency/throughput SLAs** — Evidence: [docs/reports/adr-003-architecture-review.md](../reports/adr-003-architecture-review.md), [docs/metrics_usage.md](../metrics_usage.md). Improvement: run lifecycle benchmarks on Redis/Postgres/Qdrant/Neo4j/Typesense; capture p95/p99 plus queue depth.
- **Resource and configuration tuning** — Evidence: pooling/batching in [src/storage/](../../src/storage) and configs in [config/](../../config). Improvement: document recommended pool sizes, batch sizes, and load-shedding/backpressure behavior; add tests to validate defaults.
- **GoodAI LTM benchmark readiness** — Evidence: [docs/benchmark_use_cases.md](../benchmark_use_cases.md), [docs/research/](../research). Improvement: prepare reproducible scripts and baselines (standard RAG vs full-context) with fixed seeds and logging.

## 5. Documentation & Status Integrity
- **Status currency** — Evidence: [DEVLOG.md](../../DEVLOG.md), [docs/plan/](.), [docs/reports/adr-003-architecture-review.md](../reports/adr-003-architecture-review.md). Improvement: reconcile any “engines missing” statements with current code; record Phase 4 closure and pending gates.
- **Operational runbooks** — Evidence: [docs/environment-guide.md](../environment-guide.md), [docs/metrics_usage.md](../metrics_usage.md). Improvement: add runbooks for lifecycle failures, divergence repair, and LLM provider fallback behavior.
- **Config-to-ADR alignment** — Evidence: [config/ciar_config.yaml](../../config/ciar_config.yaml), [docs/ADR/004-ciar-scoring-formula.md](../ADR/004-ciar-scoring-formula.md). Improvement: include domain-specific CIAR overrides and rationale.
- **Risk register and lessons** — Evidence: [docs/lessons-learned.md](../lessons-learned.md). Improvement: log Phase 4 incidents (if any) with mitigations and links to code changes.

## 6. Governance & Safety
- **Error handling and circuit breakers** — Evidence: engine implementations and adapter error paths in [src/memory/engines/](../../src/memory/engines) and [src/storage/](../../src/storage). Improvement: confirm thresholds and retry budgets are implemented, documented, and covered by tests.
- **Provenance and auditability** — Evidence: lineage fields in [src/memory/models.py](../../src/memory/models.py) and writes in engine code. Improvement: add tests ensuring provenance survives L2→L4 promotions and reconciliations.
- **Data retention and TTLs** — Evidence: L1/L2 tier logic and configs. Improvement: validate TTL enforcement and retention policies match ADR and compliance notes; ensure metrics expose TTL expirations.

## Usage Guidance
- Assign Green/Amber/Red per item with a short note and link to evidence above. 
- For Amber/Red, add a one-line, project-specific improvement (e.g., “Run promotion→consolidation E2E against Redis/Postgres/Qdrant/Neo4j/Typesense and record p95 in metrics export”).
- Keep grading results in this document until we formalize a dedicated tracker; update after each validation cycle.

## Grading Automation Approach (Planned)
- **Script location:** Place readiness graders under `scripts/` (e.g., `scripts/grade_phase5_readiness.sh` plus optional `scripts/grade_phase5_readiness.py`). Document outputs into [docs/reports/preliminary_readiness_checks_version-0.7_upto10feb2026.md](../reports/preliminary_readiness_checks_version-0.7_upto10feb2026.md).
- **Interpreter choice:** On the managed host, scripts must call `/home/max/code/mas-memory-layer/.venv/bin/python` and `/home/max/code/mas-memory-layer/.venv/bin/pytest` directly (no activation). For portability, allow fallback to `./.venv/bin/python`/`./.venv/bin/pytest` when the absolute path is unavailable.
- **Environment loading:** Users run scripts in a shell that already exports variables from `.env`; the repo must not read or commit `.env`. In bash wrappers, note the pattern `set -a; source .env; set +a` is to be executed by users, not baked into committed code. Scripts should verify required variables (e.g., `GOOGLE_API_KEY`, backend connection settings) before running real-provider or real-backend checks.
- **Real vs mock runs:** Keep fast path (lint + unit/mocked tests) and real path (integration with Redis/Postgres/Qdrant/Neo4j/Typesense and real LLM providers). Gate real paths on env presence and skip markers; report clearly whether real backends were exercised.
- **Outputs:** Emit structured summaries (e.g., JSON or concise text) with status of lint, unit, integration, coverage (from `htmlcov/status.json`), and optional benchmarks (p95/p99). These outputs feed grading in [docs/reports/preliminary_readiness_checks_version-0.7_upto10feb2026.md](../reports/preliminary_readiness_checks_version-0.7_upto10feb2026.md).
- **Example invocations:**
	- Fast path: `./scripts/grade_phase5_readiness.sh --mode fast`
	- Full path with summary file: `./scripts/grade_phase5_readiness.sh --mode full --summary-out /tmp/phase5-readiness.json`
	- To skip real LLM/provider checks even if `GOOGLE_API_KEY` is set: add `--skip-llm`

---

## 2026-01-03 Implementation Session: Data Starvation Cascade Fix

### Root Cause Analysis

The `test_full_lifecycle_end_to_end` test fails due to a **data starvation cascade**:
1. Too few facts flow from L1→L2 (semantic weakness in test data)
2. Results in thin L3 episodes 
3. Produces zero L4 knowledge documents

Contributing factors identified:
- **Vector dimension mismatch**: QdrantAdapter defaults to 384, EpisodicMemoryTier expects 768, Gemini outputs 3072 by default
- **Low query limits**: `query_by_session()` defaults to 10 results (truncates during consolidation)
- **Weak test content**: Generic "Container arrived" messages don't trigger meaningful LLM fact extraction

### Completed Fixes (2026-01-03)

| Fix | File | Change |
|-----|------|--------|
| ✅ Vector dimension to 768 | `src/utils/providers.py` | Added `output_dimensionality=768` to `GeminiProvider.get_embedding()` |
| ✅ Fallback embedding aligned | `src/memory/engines/consolidation_engine.py` | Changed fallback from 1536 to 768 dims |
| ✅ L2 query limits increased | `src/memory/tiers/working_memory_tier.py` | `query_by_session()` and `query_by_type()` default limit: 10→100 |
| ✅ Rich test data | `tests/integration/test_memory_lifecycle.py` | New `SUPPLY_CHAIN_CONVERSATION_TEMPLATES` with realistic scenarios |
| ✅ Distillation logging | `src/memory/engines/distillation_engine.py` | Added INFO log in `_retrieve_episodes()` (pre/post filter counts) |
| ✅ L4 store confirmation | `src/memory/tiers/semantic_memory_tier.py` | Added INFO log confirming Typesense write with `knowledge_id` |

### Pending: Arize Phoenix Integration

#### Overview
Phoenix provides LLM call tracing for debugging embeddings, latencies, and token usage. Already deployed on `skz-dev-lv:6006`.

#### Environment Configuration

Add to `.env`:
```bash
# --- Arize Phoenix (LLM Observability) ---
PHOENIX_PORT=6006
PHOENIX_GRPC_PORT=4317
PHOENIX_COLLECTOR_ENDPOINT=http://${DEV_NODE_IP}:${PHOENIX_PORT}/v1/traces
PHOENIX_PROJECT_NAME=mlm-mas-dev
PHOENIX_URL=http://${DEV_NODE_IP}:${PHOENIX_PORT}
```

#### Project Naming Convention
| Environment | Project Name |
|-------------|--------------|
| Development | `mlm-mas-dev` |
| Testing | `mlm-mas-test` |
| Production | `mlm-mas-prod` |

#### Dependencies to Add (requirements.txt)
```txt
# --- Observability & Tracing (Arize Phoenix) ---
arize-phoenix>=4.0.0                              # Phoenix observability SDK
openinference-instrumentation-google-genai>=0.1.0 # Auto-instrumentation for Google GenAI
opentelemetry-exporter-otlp>=1.20.0               # OTLP exporter (HTTP/gRPC)
```

#### Connectivity Check Script

Create `scripts/check_phoenix_connectivity.sh`:
```bash
#!/usr/bin/env bash
# Verify Arize Phoenix connectivity
set -euo pipefail

PHOENIX_HOST="${DEV_NODE_IP:-192.168.107.172}"
PHOENIX_HTTP_PORT="${PHOENIX_PORT:-6006}"
PHOENIX_GRPC_PORT="${PHOENIX_GRPC_PORT:-4317}"

echo "=== Arize Phoenix Connectivity Check ==="
echo "Host: ${PHOENIX_HOST}"

# Check HTTP endpoint (UI + OTLP HTTP collector)
echo -n "HTTP (port ${PHOENIX_HTTP_PORT}): "
if curl -sf "http://${PHOENIX_HOST}:${PHOENIX_HTTP_PORT}" -o /dev/null 2>/dev/null; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Check gRPC endpoint
echo -n "gRPC (port ${PHOENIX_GRPC_PORT}): "
if nc -z "${PHOENIX_HOST}" "${PHOENIX_GRPC_PORT}" 2>/dev/null; then
    echo "✅ OK"
else
    echo "⚠️  Not reachable (may not be exposed)"
fi

echo ""
echo "=== Collector Endpoints ==="
echo "OTLP HTTP: http://${PHOENIX_HOST}:${PHOENIX_HTTP_PORT}/v1/traces"
echo "OTLP gRPC: ${PHOENIX_HOST}:${PHOENIX_GRPC_PORT}"
```

#### Instrumentation Code for llm_client.py

Replace Phoenix init in `src/utils/llm_client.py`:
```python
# Phoenix configuration constants
PHOENIX_DEFAULT_PROJECT = "mlm-mas-dev"
PHOENIX_SERVICE_NAME = "mas-memory-layer"

def _init_phoenix_instrumentation() -> None:
    """Initialize Phoenix/OpenTelemetry instrumentation if configured.
    
    Environment Variables:
        PHOENIX_COLLECTOR_ENDPOINT: OTLP collector URL (e.g., http://192.168.107.172:6006/v1/traces)
        PHOENIX_PROJECT_NAME: Project name for trace grouping (default: mlm-mas-dev)
    """
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
    if not endpoint:
        logger.debug(
            "PHOENIX_COLLECTOR_ENDPOINT not set; Phoenix instrumentation disabled. "
            "Set to http://<host>:6006/v1/traces to enable."
        )
        return
    
    project_name = os.environ.get("PHOENIX_PROJECT_NAME", PHOENIX_DEFAULT_PROJECT)
    
    try:
        from phoenix.otel import register
        
        tracer_provider = register(
            project_name=project_name,
            endpoint=endpoint,
            auto_instrument=True,
        )
        
        logger.info(
            "Phoenix instrumentation enabled: project=%s, endpoint=%s",
            project_name,
            endpoint
        )
        
        # Explicitly instrument Google GenAI
        try:
            from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
            if not GoogleGenAIInstrumentor().is_instrumented_by_opentelemetry:
                GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
                logger.info("Google GenAI instrumentation enabled (explicit)")
        except ImportError:
            logger.debug("openinference-instrumentation-google-genai not installed")
        except Exception as e:
            logger.warning("Failed to instrument Google GenAI: %s", e)
        
    except ImportError:
        logger.debug("arize-phoenix not installed; run 'pip install arize-phoenix'")
    except Exception as e:
        logger.warning("Failed to initialize Phoenix instrumentation: %s", e)

# Initialize at module load (idempotent)
_init_phoenix_instrumentation()
```

### Next Steps (Priority Order)

1. **Verify Phoenix Deployment**: Run connectivity check script against `skz-dev-lv:6006`
2. **Install Dependencies**: Add Phoenix packages to requirements.txt
3. **Update .env.example**: Add Phoenix configuration variables
4. **Finalize llm_client.py**: Update instrumentation code with project naming
5. **Run Full Lifecycle Test**: Verify data starvation fixes resolve the E2E test
6. **Observe in Phoenix UI**: Confirm embedding dimensions and LLM calls are traced

### Test Commands

```bash
# Run full lifecycle test
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/integration/test_memory_lifecycle.py::TestMemoryLifecycleFlow::test_full_lifecycle_end_to_end -v > /tmp/copilot.out 2>&1; cat /tmp/copilot.out

# Run all integration tests  
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/integration/ -v > /tmp/copilot.out 2>&1; cat /tmp/copilot.out

# Grade phase 5 readiness
./scripts/grade_phase5_readiness.sh --mode full > /tmp/copilot.out 2>&1; cat /tmp/copilot.out
```

---


# Phase 5 Subset Experiment Execution Specification (32k Baseline)

**Date:** January 27, 2026  
**Scope:** GoodAI LTM Benchmark subset (prospective_memory + restaurant, 32k span)  
**Primary Goal:** Execute the 10% baseline run with deterministic cleanup, reproducible logs, and traceable outputs.

---

## 1. Objective

This document provides a step-by-step execution specification for the Phase 5 subset baseline experiment. It is designed to allow a cold start on the next session without re-deriving the operational steps. The specification prioritizes deterministic startup, serial execution (to avoid quota exhaustion), verified cleanup, and reproducible artifact collection.

---

## 2. Pre-Run Readiness Checklist

1. **Environment**
   - Confirm Python venv exists: `.venv/` at repository root.
   - Confirm GoodAI benchmark venv exists: `benchmarks/.venv-benchmark/`.
   - Confirm required environment variables in `.env`:
     - `REDIS_URL`, `POSTGRES_URL`
     - `GOOGLE_API_KEY` (required for Gemini)
     - Any backend connectivity variables used in test fixtures.

2. **Repository State**
   - Confirm wrapper code and GoodAI model interfaces are present.
   - Confirm subset configuration file exists:
     - `benchmarks/goodai-ltm-benchmark/configurations/mas_subset_32k.yml`.
   - Confirm orchestration and polling utilities exist:
     - `scripts/run_subset_experiments.sh`
     - `scripts/poll_memory_state.py`

3. **Tests**
   - Run wrapper tests before execution:
     - `scripts/run_wrapper_tests.sh` (this is already enforced inside the orchestration script).

---

## 3. Step-by-Step Execution Specification

### Step 1 — Verify wrapper services can start

**Goal:** Ensure all three wrapper services start and pass `/health` within 60 seconds.

**Action:** Start wrappers via the orchestration script (see Step 3). The script performs:
- Wrapper startup on ports 8080/8081/8082
- Health checks with a 60-second timeout

**Expected Outcome:**
- `/health` returns status `ok` for all three wrappers.

---

### Step 2 — Enable memory polling

**Goal:** Record L1/L2/L3/L4 counts per session during benchmark execution.

**Action:** The orchestration script launches `scripts/poll_memory_state.py` for each wrapper, emitting:
- `logs/mas_full_memory_timeline.jsonl`
- `logs/mas_rag_memory_timeline.jsonl`
- `logs/mas_full_context_memory_timeline.jsonl`

**Expected Outcome:**
- Timeline logs are continuously appended and survive wrapper restarts.

---

### Step 3 — Execute subset benchmark runs (serial)

**Goal:** Run GoodAI benchmark sequentially to avoid rate-limit collisions.

**Action:** The orchestration script runs:
- `mas-full`
- `mas-rag`
- `mas-full-context`

Each run uses:
- `benchmarks/goodai-ltm-benchmark/configurations/mas_subset_32k.yml`

**Expected Outcome:**
- GoodAI outputs appear under:
  - `benchmarks/goodai-ltm-benchmark/data/tests/prospective_memory/results/mas-*`
  - `benchmarks/goodai-ltm-benchmark/data/tests/restaurant/results/mas-*`

---

### Step 4 — Verify cleanup between runs

**Goal:** Ensure session state is cleared after each agent run.

**Action:** The orchestration script calls `/sessions` after each run:
- If sessions are non-empty, it calls `/cleanup_force?session_id=all`.
- Cleanup status is logged to:
  - `logs/subset_cleanup_{agent}_YYYYMMDD.log`

**Expected Outcome:**
- Each agent run ends with a clean session list.

---

### Step 5 — Copy results into stable archive

**Goal:** Preserve result artifacts for analysis.

**Action:** The orchestration script copies results into:
- `benchmarks/results/goodai_ltm/subset_baseline_YYYYMMDD/`
- Copies memory timeline logs and cleanup logs into a `logs/` subdirectory.

**Expected Outcome:**
- Timestamped archive exists with per-agent results and operational logs.

---

### Step 6 — Terminate services cleanly

**Goal:** Prevent orphaned wrapper or polling processes.

**Action:** The orchestration script terminates all wrapper and polling PIDs on exit.

**Expected Outcome:**
- No residual wrapper processes remain on ports 8080/8081/8082.

---

## 4. Expected Output Structure

```
benchmarks/results/goodai_ltm/subset_baseline_YYYYMMDD/
├── mas-full/
│   ├── prospective_memory/
│   │   └── results.json
│   └── restaurant/
│       └── results.json
├── mas-rag/
│   └── ...
├── mas-full-context/
│   └── ...
└── logs/
    ├── mas_full_memory_timeline.jsonl
    ├── mas_rag_memory_timeline.jsonl
    ├── mas_full_context_memory_timeline.jsonl
    └── subset_cleanup_*.log
```

---

## 5. Current Readiness Summary (as of 2026-01-27)

**Implemented and Ready:**
- Wrapper services and agent interfaces (full/rag/full_context) with session prefixing.
- Rate limiting, Phoenix tracing separation, and wrapper endpoints (`/run_turn`, `/sessions`, `/memory_state`, `/health`).
- Database isolation mechanisms:
  - PostgreSQL table-level locks for L2 writes.
  - Redis-backed Neo4j lock with auto-renewal.
- Orchestration utilities:
  - `scripts/run_subset_experiments.sh`
  - `scripts/poll_memory_state.py`
- Subset configuration:
  - `benchmarks/goodai-ltm-benchmark/configurations/mas_subset_32k.yml`

**Pending After Subset Execution:**
- Instrumentation module for adapter-level timing (`src/evaluation/instrumentation.py`).
- Subset execution run artifacts and analysis report.

---

## 6. Next Session Starting Point

**Run the subset execution directly via:**
- `scripts/run_subset_experiments.sh`

This script performs all startup checks, launches wrappers, runs the GoodAI subset, verifies cleanup, and archives results.

---

## 7. Notes and Constraints

- Execution should remain serial to protect quota limits.
- Ensure `GOOGLE_API_KEY` is set via `.env`; do not use `GEMINI_API_KEY`.
- Do not use `source .venv/bin/activate` for any scripted execution paths; the orchestration uses explicit paths.

---

## 9. Native Gemini Migration Plan (Subset Run)

### 9.1 Objectives

The subset experiment will use the native Google Gemini client with `gemini-2.5-flash-lite`, replacing the litellm abstraction. The integration must preserve benchmark behavior while enforcing a conservative context budget of 96k tokens per call to maintain throughput under a 4M TPM limit with parallel execution.

### 9.2 Implementation Steps

1. **Validate native Gemini client**
  - Execute a direct `GeminiProvider` call using `gemini-2.5-flash-lite`.
  - Confirm response text, model name, and usage metadata are returned.

2. **Replace litellm in benchmark runtime**
  - Implement `ask_gemini()` in `benchmarks/goodai-ltm-benchmark/utils/llm.py` using `google-genai`.
  - Provide a `GeminiContextWindowExceededError` exception to mirror the prior overflow behavior.

3. **Enforce context budget**
  - Set a default budget of 96k tokens per call.
  - Allow overrides via `MAS_GEMINI_MAX_CONTEXT_TOKENS` for controlled experiments.

4. **Usage-metadata cost accounting**
  - Derive cost estimates from `usage_metadata` when available.
  - Log token counts and usage metadata at debug level for traceability.

5. **Update benchmark call sites**
  - Replace all `ask_llm` invocations with `ask_gemini` across datasets and model interfaces.
  - Standardize the model to `gemini-2.5-flash-lite` for the planned subset run.

6. **Documentation update**
  - Update the GoodAI benchmark README to reflect native Gemini usage, token limits, and required environment variables.

### 9.3 Expected Outcomes

- The subset run executes without litellm dependencies.
- Token budgets are enforced prior to request dispatch.
- Usage metadata is captured for cost and throughput analysis.
- The benchmark documentation reflects the native Gemini integration.

### 9.4 Validation Status

The native Gemini client has been validated with `gemini-2.5-flash-lite` on 2026-01-28 using `scripts/test_gemini_flash_lite.py`. The test returned a non-empty response and usage metadata, confirming compatibility with the benchmark integration path.

---

## 8. Traceability References

- Wrapper: [src/evaluation/agent_wrapper.py](../../src/evaluation/agent_wrapper.py)
- Orchestration: [scripts/run_subset_experiments.sh](../../scripts/run_subset_experiments.sh)
- Polling: [scripts/poll_memory_state.py](../../scripts/poll_memory_state.py)
- Config: [benchmarks/goodai-ltm-benchmark/configurations/mas_subset_32k.yml](../../benchmarks/goodai-ltm-benchmark/configurations/mas_subset_32k.yml)
- GoodAI interfaces: [benchmarks/goodai-ltm-benchmark/model_interfaces/mas_agents.py](../../benchmarks/goodai-ltm-benchmark/model_interfaces/mas_agents.py)

---


# Phase 5 — Post-Subset Run: Visibility & Reliability Improvements
Date: 2026-01-29

## Implementation Status (as of 2026-02-05)
- Status: Not implemented.
- No runner or CLI changes landed; no JSONL metrics, watchdog, or progress UX present.

## Purpose
Document the agreed plan and decisions to improve visibility, progress reporting, and stuck-run detection for Phase 5 of the GoodAI LTM benchmark work. This is a planning artifact only; no runner or functional changes will be applied in this ticket.

## Problem Statement
During the first subset run, a researcher manually interrupted the job after ~9 hours because there was no clear progress visibility; logs showed health checks and minimal activity rather than ongoing processing. Without actionable visibility and stuck-run detection, researchers cannot determine whether the system is processing or stuck.

## Goals
- Provide real-time progress feedback during benchmark runs (CLI-friendly, headless-safe).
- Record per-turn timing data (LLM call duration, memory operation duration, orchestration time).
- Detect and alert on stuck runs (configurable threshold), providing diagnostics and optional automated cleanup.
- Keep instrumentation lightweight and opt-in for runs that need high visibility.

## Agreed Decisions
- Progress reporting library: **tqdm** (lightweight, headless-friendly). ✅
- Default stuck timeout: **15 minutes** (configurable via `--stuck-timeout` or env `MAS_BENCH_STUCK_TIMEOUT_MINUTES`). ✅
- CLI verbosity: support `--verbose` (detailed per-turn logging) and `--quiet` (errors-only); respect `LOG_LEVEL` env var as fallback. ✅
- Per-turn metrics: record JSONL `turn_metrics` lines with fields such as: `timestamp`, `session_id`, `turn_index`, `llm_ms`, `storage_ms`, `tokens_in`, `tokens_out`, `status`.
- Run termination behavior: upon stuck timeout, write a `run_error.json` summarizing last known state and optionally raise an alert (implementation subject to infra decisions).

## Implementation Outline (high-level)
> NOTE: This file is a plan only. Do not modify runner code as part of this ticket.

1. **CLI Changes**
   - Add `--stuck-timeout MINUTES` and `--progress [tqdm|none]` flags to `run_benchmarks.py`/runner CLI.
   - Implement `--verbose` and `--quiet` flags. CLI overrides `LOG_LEVEL` env var.

2. **Progress UX**
   - Add `tqdm` progress bar for overall test progress and nested bars for batch processing where applicable.
   - Use `tqdm.write()` for log lines to avoid progress UI corruption.

3. **Per-turn Instrumentation**
   - Wrap LLM calls (the central `ask_gemini` or equivalent interface) with a timer and log `llm_ms`.
   - Wrap memory adapter calls (L1/L2/L3/L4 interactions) with timers and log `storage_ms` per adapter.
   - Emit a `turn_metrics.jsonl` entry per turn with fields: `timestamp`, `session_id`, `turn_id`, `role`, `llm_ms`, `storage_ms`, `tokens_in`, `tokens_out`, `error`.

4. **Stuck Detection & Alerts**
   - A background monitor checks `last_event_timestamp` and compares with `--stuck-timeout`.
   - On timeout, persist `run_error.json` (diagnostics) and optionally attempt to stop the run gracefully.

5. **Run Summary**
   - Extend `runstats.json` to include `turn_metrics_summary` with p50/p95/p99 for `llm_ms` and `storage_ms` and total `turns` and `events`.

## Verification Criteria
- Developer and researcher can run a subset and see `tqdm` progress output on the console (or no UI in `--progress none` mode).
- `turn_metrics.jsonl` contains per-turn timing for at least 95% of turns in a test run.
- A simulated stuck-run (pause processing for > 15 minutes) triggers `run_error.json` and writes diagnostic info.
- `runstats.json` includes the new summary fields.

## Rollout Plan & Prioritization
- Phase 5.1 (Design & Tests): Implement per-turn timers as instrumentation-only (non-invasive), add unit tests for metric emission.
- Phase 5.2 (CLI UX): Integrate `tqdm` progress bars, CLI flags, and documentation updates.
- Phase 5.3 (Diagnostics): Implement stuck detection, `run_error.json`, and run-summary enhancements.

## Risks & Mitigations
- **Overhead:** Instrumentation may add small overhead. Mitigation: Make per-turn timing optional behind `--verbose` and set sampling defaults.
- **Log Volume:** `turn_metrics.jsonl` can be large; mitigation: compress/rotate logs and provide sampling options.

## Owners & Next Steps
- Owner: Benchmark engineering lead (please assign)
- Next step: Create a small spike PR that adds per-turn timers with tests and a README example (no changes performed in this task).

---

*This document captures decisions agreed during analysis and planning (2026-01-29). Implementation is to be performed in a subsequent development task.*

---


# First Run Preparation and Execution Plan (2026-02-07)

**Purpose:** Provide a structured plan for the initial GoodAI LTM benchmark execution with Web UI progress tracking and three-agent comparison (full multi-layer, RAG-only, and full-context baseline).

## 0. Decision Log (2026-02-07)

- The first run prioritizes end-to-end validation over performance baselines.
- Two isolated Poetry environments are mandatory and will not be merged.
- The pre-flight gate uses `scripts/grade_phase5_readiness.sh --mode fast` before any benchmark execution.
- Adapter-level `raise AssertionError("Unreachable")` statements are retained only where they remain inside method bodies to satisfy mypy control-flow analysis; class-level instances were removed to avoid import-time failures.
- Environment activation via `source .venv/bin/activate` is not used; commands must call the absolute venv executable paths on the remote host.

## 0.1 Implementation Tracker

1. Re-run the pre-flight gate after the adapter fixes are validated.
2. Confirm Web UI frontend build assets or use the dev server with API proxy.
3. Start wrapper services for `mas-full`, `mas-rag`, and `mas-full-context` on ports 8080-8082.
4. Execute the single-test configuration and validate run metadata, progress, and logs.
5. Record the run artifacts and proceed to the subset configuration if the single run succeeds.

## 1. Scope and Assumptions

- The run validates end-to-end integration rather than performance baselines.
- Two isolated Poetry environments are required and must remain separate:
  - MAS Memory Layer: repository root.
  - GoodAI LTM Benchmark: benchmarks/goodai-ltm-benchmark/.
- Backend services are expected to be running before execution.
- The remote host requires absolute virtual environment paths.

## 2. Preparation Checklist

### 2.1 Environment Setup (Poetry)

1. **MAS Memory Layer environment**
   - Navigate to the repository root.
   - Run `poetry install --with test,dev`.

2. **GoodAI Benchmark environment**
   - Navigate to benchmarks/goodai-ltm-benchmark/.
   - Run `poetry install`.

### 2.2 Environment Variables

Confirm the following environment variables are available via the repository .env:
- GOOGLE_API_KEY (required for Gemini; do not use GEMINI_API_KEY)
- DATA_NODE_IP, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
- NEO4J_USER, NEO4J_PASSWORD

### 2.3 Backend Services

Verify services are reachable and healthy:
- Redis
- PostgreSQL
- Qdrant
- Neo4j
- Typesense

### 2.4 Web UI Build

- Navigate to benchmarks/goodai-ltm-benchmark/webui/frontend.
- Run `npm install` and `npm run build` for production assets.
- If development mode is preferred, run `npm run dev` and rely on the API proxy to port 8005.

## 3. Execution Plan

### 3.1 Start MAS Wrapper Services

Start three wrapper processes (one per agent):
- Full multi-layer agent on port 8080
- RAG-only agent on port 8081
- Full-context baseline on port 8082

### 3.2 Start Web UI Backend

- Run the Web UI backend server at benchmarks/goodai-ltm-benchmark/webui/server.py.
- Confirm the server detects run metadata and exposes API endpoints.

### 3.3 Run Validation Test (Single)

- Execute a single-test configuration to validate the pipeline:
  - benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml
- Confirm that:
  - run metadata is created
  - turn_metrics.jsonl is populated
  - Web UI progress endpoints respond

### 3.4 Run Subset Test (Primary First Run)

- Execute the subset configuration for initial evaluation:
  - benchmarks/goodai-ltm-benchmark/configurations/mas_subset_32k.yml
- Run three agent variants in sequence:
  1. mas-full
  2. mas-rag
  3. mas-full-context

## 4. Validation Criteria

1. Wrapper endpoints return healthy status.
2. Runs complete without timeout and write run_meta.json and runstats.json.
3. Web UI displays runs and progress metrics.
4. Logs and result artifacts are persisted under benchmarks/results/.

## 5. Failure Handling

- If a run stalls, inspect run_error.json and turn_metrics.jsonl.
- Validate backend connectivity and memory store health.
- Confirm GOOGLE_API_KEY is present when LLM calls are enabled.

## 6. Post-Run Artifacts

- Results directory: benchmarks/results/goodai_ltm/
- Web UI logs: benchmarks/goodai-ltm-benchmark/webui/logs/
- Wrapper logs: logs/

## 7. References

- GoodAI setup: docs/integrations/goodai-benchmark-setup.md
- Web UI backend: benchmarks/goodai-ltm-benchmark/webui/server.py
- Wrapper service: src/evaluation/agent_wrapper.py
- Orchestration script: scripts/run_subset_experiments.sh

---


# Lightweight Benchmarking Setup & Improvement Plan

**Date**: October 21, 2025  
**Status**: 🔄 Planning  
**Priority**: High  
**Related**: [ADR-002](../ADR/002-storage-performance-benchmarking.md), [storage-benchmark-implementation.md](../reports/storage-benchmark-implementation.md)

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

