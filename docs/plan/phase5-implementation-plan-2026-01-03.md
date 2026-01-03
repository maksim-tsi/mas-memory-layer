# Phase 5 Implementation Plan: GoodAI LTM Benchmark Evaluation

**Version**: 1.0  
**Date**: January 3, 2026  
**Duration**: 6 weeks  
**Status**: Planning Complete | Implementation Not Started  
**Prerequisites**: ✅ Phase 4 Complete (574/586 tests passing, 0 failures)  
**Target**: AIMS 2025 Conference Paper Submission  
**Branch**: `dev-mas`

---

## Executive Summary

Phase 5 executes a rigorous quantitative evaluation of our four-tier hybrid memory architecture using the GoodAI LTM Benchmark. This phase will generate the empirical results required for the AIMS 2025 paper submission, comparing our full system against two baseline configurations across long-conversation scenarios (32k-120k tokens).

### Core Deliverables

1. **Three Agent Implementations**: `MemoryAgent` (full system), `RAGAgent` (standard baseline), `FullContextAgent` (naive baseline)
2. **Benchmark Integration**: FastAPI wrapper + GoodAI LTM Benchmark runner
3. **Experimental Results**: 12 benchmark runs with comprehensive instrumentation
4. **Paper-Ready Tables**: Functional correctness scores + operational efficiency metrics

### Key Metrics

| Metric Category | Measurements |
|-----------------|--------------|
| **Functional Correctness** | GoodAI LTM accuracy scores (32k, 120k token spans) |
| **Operational Efficiency** | Latency P50/P95/P99, token cost per turn, cache hit rates |
| **Resource Utilization** | Memory usage, database query counts, LLM API calls |

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
| **BaseAgent class** | ❌ Not implemented | `src/agents/base_agent.py` |
| **MemoryAgent** (UC-01) | ❌ Not implemented | `src/agents/memory_agent.py` |
| **RAGAgent** (UC-02) | ❌ Not implemented | `src/agents/rag_agent.py` |
| **FullContextAgent** (UC-03) | ❌ Not implemented | `src/agents/full_context_agent.py` |
| **LangGraph StateGraph wiring** | ❌ Not implemented | Agent classes above |
| **Agent Wrapper API** | ❌ Not implemented | `src/evaluation/agent_wrapper.py` |
| **GoodAI Benchmark Integration** | ❌ Not implemented | `src/evaluation/benchmark_runner.py` |
| **Instrumentation/Logging** | ❌ Not implemented | `src/evaluation/instrumentation.py` |
| **Experiment Automation** | ❌ Not implemented | `scripts/run_experiments.sh` |
| **Analysis Notebook** | ❌ Not implemented | `benchmarks/analysis/analyze_results.ipynb` |

### Model Configuration

| Provider | Model ID | Use Case |
|----------|----------|----------|
| **Gemini** | `gemini-3-flash-preview` | Primary inference, structured output, embeddings |
| **Groq** | `openai/gpt-oss-120b` | Fast inference, batch processing, fallback |

---

## Architecture Overview

### Three Experimental Configurations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GoodAI LTM Benchmark Runner                          │
│                    (External: goodai-ltm-benchmark repo)                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ HTTP POST /run_turn
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Agent Wrapper API (FastAPI)                         │
│                      src/evaluation/agent_wrapper.py                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │  config=full    │  │  config=rag     │  │  config=full_context        │  │
│  └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────┘  │
└───────────┼────────────────────┼──────────────────────────┼─────────────────┘
            │                    │                          │
            ▼                    ▼                          ▼
┌───────────────────┐  ┌─────────────────┐  ┌──────────────────────────────────┐
│   MemoryAgent     │  │    RAGAgent     │  │      FullContextAgent            │
│   (Full System)   │  │  (RAG Baseline) │  │      (Naive Baseline)            │
│                   │  │                 │  │                                  │
│  ┌─────────────┐  │  │  ┌───────────┐  │  │  ┌────────────────────────────┐  │
│  │ LangGraph   │  │  │  │ Single    │  │  │  │ Full History               │  │
│  │ StateGraph  │  │  │  │ Vector    │  │  │  │ Concatenation              │  │
│  │             │  │  │  │ Query     │  │  │  │                            │  │
│  │ ┌─────────┐ │  │  │  └─────┬─────┘  │  │  └──────────────┬─────────────┘  │
│  │ │PERCEIVE │ │  │  │        │        │  │                 │                │
│  │ │RETRIEVE │ │  │  │        ▼        │  │                 ▼                │
│  │ │REASON   │ │  │  │   ┌────────┐    │  │          ┌────────────┐          │
│  │ │UPDATE   │ │  │  │   │ Qdrant │    │  │          │   Redis    │          │
│  │ │RESPOND  │ │  │  │   │(single)│    │  │          │ (history)  │          │
│  │ └─────────┘ │  │  │   └────────┘    │  │          └────────────┘          │
│  └──────┬──────┘  │  │                 │  │                                  │
│         │         │  │                 │  │                                  │
│         ▼         │  │                 │  │                                  │
│  ┌─────────────┐  │  │                 │  │                                  │
│  │ Unified     │  │  │                 │  │                                  │
│  │ Memory      │  │  │                 │  │                                  │
│  │ System      │  │  │                 │  │                                  │
│  │             │  │  │                 │  │                                  │
│  │ L1→L2→L3→L4│  │  │                 │  │                                  │
│  └─────────────┘  │  │                 │  │                                  │
└───────────────────┘  └─────────────────┘  └──────────────────────────────────┘
```

### Data Flow Per Agent

**MemoryAgent (UC-01 - Full System)**:
1. Load personal state from Operating Memory (Redis L1)
2. Query L2 for recent working memory (PostgreSQL)
3. Query L3/L4 for relevant knowledge (Qdrant + Neo4j + Typesense)
4. Synthesize context with LLM (`gemini-3-flash-preview`)
5. Generate response
6. Update personal state → trigger async promotion engine

**RAGAgent (UC-02 - Standard RAG)**:
1. Query single Qdrant collection with current message
2. Concatenate retrieved chunks with message
3. Generate response via LLM (stateless, no memory management)

**FullContextAgent (UC-03 - Full Context)**:
1. Retrieve entire conversation history from Redis
2. Concatenate full history with current message
3. Send massive prompt to LLM (no filtering, no summarization)

---

## Phase 5A: Agent Implementation (Week 1-2)

### W5A.1: BaseAgent Abstract Class

**Objective**: Create the abstract base class that all agents inherit from, defining the common interface.

**File**: `src/agents/base_agent.py`

**Tasks**:
- [ ] Define `BaseAgent` abstract class with:
  - `async process_turn(message: str, history: List[Dict]) -> str`
  - `async retrieve_context(query: str) -> Dict[str, Any]`
  - `async update_state(response: str) -> None`
  - `get_metrics() -> Dict[str, Any]`
- [ ] Define `AgentInput` and `AgentOutput` Pydantic models
- [ ] Define `AgentState` TypedDict for LangGraph state management
- [ ] Implement common instrumentation hooks (timing, token counting)
- [ ] Add health check method for dependency verification

**Acceptance Criteria**:
- [ ] Abstract methods enforced (TypeError on direct instantiation)
- [ ] Pydantic models validate input/output schemas
- [ ] Unit tests for base class behavior (8+ tests)

**Deliverables**:
```
src/agents/base_agent.py
src/agents/models.py (AgentInput, AgentOutput, AgentState)
tests/agents/test_base_agent.py
```

---

### W5A.2: MemoryAgent Implementation (Full System)

**Objective**: Implement the full hybrid memory agent using LangGraph StateGraph with all four memory tiers.

**File**: `src/agents/memory_agent.py`

**Tasks**:
- [ ] Create `MemoryAgent` class inheriting from `BaseAgent`
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
- [ ] Implement `PersonalMemoryState` management (scratchpad, active_goals)
- [ ] Add circuit breaker for LLM/database failures
- [ ] Integrate with `UnifiedMemorySystem` from `src/memory/unified_memory_system.py`

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
- [ ] Full PERCEIVE→RETRIEVE→REASON→UPDATE→RESPOND cycle works
- [ ] Integrates with all 4 memory tiers
- [ ] Handles LLM failures gracefully (circuit breaker triggers)
- [ ] Metrics collected for each node (latency, tokens)
- [ ] Unit tests (12+ tests) + integration test with mocked backends

**Deliverables**:
```
src/agents/memory_agent.py
tests/agents/test_memory_agent.py
tests/integration/test_memory_agent_integration.py
```

---

### W5A.3: RAGAgent Implementation (Standard RAG Baseline)

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
