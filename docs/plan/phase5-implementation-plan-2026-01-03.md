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

## Appendix A: Key Implementation Decisions

### Decision Log

1. **10% Subset Approach** (2026-01-26):
   - **Rationale**: Full 12-run execution (30-60 hours) risks quota exhaustion and delays AIMS 2025 submission.
   - **Impact**: Subset (2 test types, 32k span) provides bottleneck identification in 3-5 hours while validating end-to-end workflow.

2. **gemini-2.5-flash-lite Selection** (2026-01-26):
   - **Rationale**: 4K RPM (vs. 10 RPM for gemini-3-flash-preview) allows serial execution without rate limit stalls.
   - **Impact**: Estimated 3-5 hour completion time vs. 30+ hours with frequent rate limit retries.

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
- [UC-01: Full System Agent](../uc-01.md)
- [UC-02: Standard RAG Baseline](../uc-02.md)
- [UC-03: Full-Context Baseline](../uc-03.md)
- [SD-01: Full System Sequence](../sd-01.md)
- [SD-02: RAG Baseline Sequence](../sd-02.md)
- [SD-03: Full-Context Sequence](../sd-03.md)
- [Agent Framework Spec](../specs/spec-phase3-agent-integration.md)

### Architecture
- [ADR-003: Four-Tier Memory Architecture](../ADR/003-four-layers-memory.md)
- [ADR-004: CIAR Scoring Formula](../ADR/004-ciar-scoring-formula.md)
- [ADR-006: Free-Tier LLM Strategy](../ADR/006-free-tier-llm-strategy.md)

### Previous Plans
- [Phase 3 Implementation Plan](phase3-implementation-plan-2025-12-27.md)
- [Phase 5 Readiness Checklist](phase5-readiness-checklist-2026-01-02.md)
- [Original Implementation Plan](implementation-plan-19102025.md)

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
