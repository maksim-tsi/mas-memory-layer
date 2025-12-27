# Phase 3 Specification: Agent Integration Layer

**Document Version**: 2.0  
**Date**: December 27, 2025  
**Last Updated**: December 27, 2025  
**Status**: Research Validated — Ready for Implementation  
**Target Completion**: 6 weeks  
**Branch**: `dev-mas`  
**Prerequisites**: Phase 2 Complete (Lifecycle Engines)

> **v2.0 Changes**: Incorporates validated research findings from RT1-RT5. See [Research Validation](../research/README.md) for critical analysis. Key updates: Hash Tag namespaces (MANDATORY), Lua scripting for state transitions, Reasoning-First schemas, Tool Message injection pattern.

---

## 1. Executive Summary

Phase 3 builds the **Agent Integration Layer** that consumes the four-tier memory infrastructure established in Phases 1 and 2. This layer delivers LangGraph-based multi-agent orchestration, three agent variants for benchmark comparison (hybrid memory, RAG baseline, full-context baseline), and an HTTP API wrapper for GoodAI LTM benchmark integration.

### Phase 3 Objective

Transform the memory system from a standalone infrastructure into a production-ready agent framework where AI agents naturally consume and contribute to the hierarchical memory architecture.

### Research Context

This is a **novel research project** for AIMS 2025 Conference. While we reference production systems like Zep and Mem0 for patterns, our approach is distinct:
- **Novel CIAR-based significance scoring** exposed to agents for reasoning
- **Four-tier hierarchical architecture** vs. flat memory stores
- **Hybrid tool design**: Both unified interface AND granular per-tier/feature tools
- **Experimental validation** through GoodAI LTM Benchmark comparison

### Key Deliverables

| Deliverable | Description | Priority |
|-------------|-------------|----------|
| **Memory Tool Interface** | Unified + granular tools for agent-memory interaction | P0 |
| **Enhanced UnifiedMemorySystem** | Integrate tier classes with lifecycle engines | P0 |
| **Agent Framework** | BaseAgent + three variant implementations | P0 |
| **LangGraph Orchestration** | Multi-agent state graph coordination | P0 |
| **Agent Wrapper API** | FastAPI `/run_turn` endpoint for benchmarks | P0 |
| **Namespace Strategy** | Multi-agent memory isolation and sharing | P0 |
| **Integration Tests** | End-to-end agent tests with real/mocked storage | P1 |

---

## 2. Foundation: Phase 1-2 Achievements

Phase 3 builds upon a substantial foundation. This section documents what has been completed and proven stable.

### 2.1 Phase 1: Storage Adapters (100% Complete)

**Objective**: Establish reliable database connectivity for all five storage backends.

| Component | Location | Tests | Status |
|-----------|----------|-------|--------|
| Redis Adapter | `src/storage/redis_adapter.py` | 25+ | ✅ |
| PostgreSQL Adapter | `src/storage/postgres_adapter.py` | 30+ | ✅ |
| Qdrant Adapter | `src/storage/qdrant_adapter.py` | 25+ | ✅ |
| Neo4j Adapter | `src/storage/neo4j_adapter.py` | 30+ | ✅ |
| Typesense Adapter | `src/storage/typesense_adapter.py` | 20+ | ✅ |
| Metrics System | `src/storage/metrics/` | 15+ | ✅ |

**Total**: 143/143 tests passing

**Key Capabilities Established**:
- Async-first architecture with connection pooling
- Comprehensive metrics collection (timing, throughput, percentiles)
- Health check endpoints for all backends
- Standardized adapter interface via `BaseAdapter`

### 2.2 Phase 2A: Memory Tier Classes (100% Complete)

**Objective**: Create intelligent tier managers that wrap storage adapters with domain logic.

| Tier | Storage | Class | Purpose |
|------|---------|-------|---------|
| L1 | Redis | `ActiveContextTier` | 10-20 recent turns, 24h TTL |
| L2 | PostgreSQL | `WorkingMemoryTier` | Significant facts filtered by CIAR |
| L3 | Qdrant + Neo4j | `EpisodicMemoryTier` | Consolidated episodes with dual-indexing |
| L4 | Typesense | `SemanticMemoryTier` | Distilled knowledge patterns |

**Data Models** (`src/memory/models.py`):
- `Fact` - L2 working memory unit with CIAR scoring
- `Episode` - L3 consolidated experience with bi-temporal properties
- `KnowledgeDocument` - L4 distilled knowledge with provenance tracking
- Query models: `FactQuery`, `EpisodeQuery`, `KnowledgeQuery`

**Key Achievement**: Full bi-temporal data model per ADR-003 requirements.

### 2.3 Phase 2B: Promotion Engine (100% Complete)

**Objective**: Automate L1→L2 fact extraction with CIAR-based significance filtering.

| Component | Location | Function |
|-----------|----------|----------|
| `FactExtractor` | `src/memory/engines/fact_extractor.py` | LLM-based fact extraction with circuit breaker fallback |
| `PromotionEngine` | `src/memory/engines/promotion_engine.py` | Orchestrates L1→L2 pipeline |

**CIAR Formula** (ADR-004):
```
CIAR = (Certainty × Impact) × exp(-λ×days) × (1 + α×access_count)
```
- λ = 0.0231 (30-day half-life)
- α = 0.1 (10% boost per access)
- Promotion threshold: 0.6 (configurable)

**Pipeline Flow**:
1. Retrieve unprocessed turns from L1 (Redis)
2. Extract candidate facts via LLM (Gemini/Groq)
3. Calculate CIAR score for each fact
4. Filter facts above threshold (default 0.6)
5. Store significant facts in L2 (PostgreSQL)

### 2.4 Phase 2C: Consolidation Engine (100% Complete)

**Objective**: Cluster L2 facts into L3 episodes with dual-indexing.

| Component | Location | Function |
|-----------|----------|----------|
| `ConsolidationEngine` | `src/memory/engines/consolidation_engine.py` | Time-based clustering + LLM summarization |

**Consolidation Logic**:
1. Cluster facts by time window (configurable, default 24h)
2. Generate episode summary via LLM
3. Create embeddings (Gemini embedding-001)
4. Dual-write: Qdrant (vector) + Neo4j (graph)

**Key Achievement**: Hybrid retrieval model enabling both semantic similarity search and entity-centric graph traversal.

### 2.5 Phase 2D: Distillation Engine & Knowledge Synthesizer (100% Complete)

**Objective**: Extract generalized knowledge from episodes and provide query-time synthesis.

| Component | Location | Function |
|-----------|----------|----------|
| `DistillationEngine` | `src/memory/engines/distillation_engine.py` | L3→L4 knowledge creation |
| `KnowledgeSynthesizer` | `src/memory/engines/knowledge_synthesizer.py` | Query-time retrieval and synthesis |

**Knowledge Types**:
- `summary` - Episode aggregations
- `insight` - Derived observations
- `pattern` - Recurring behaviors
- `recommendation` - Suggested actions
- `rule` - Business rules/constraints

**Synthesis Features**:
- Metadata-first filtering before similarity search
- Conflict detection and transparency
- 1-hour TTL caching for efficiency

### 2.6 Overall Phase 2 Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Tests Passing | 441/445 | 100% | ✅ (4 skipped) |
| Code Coverage | 86% | ≥80% | ✅ |
| LLM Connectivity | Gemini, Groq, Mistral | 3+ providers | ✅ |
| Engine Tests | 44+ | Full coverage | ✅ |

---

## 3. Phase 3 Goals

### 3.1 Primary Goals

1. **Memory-Integrated Agents**: Create agents that naturally consume L1-L4 tiers through the `UnifiedMemorySystem` interface.

2. **Three Agent Variants**: Implement the experimental configurations defined in UC-01, UC-02, UC-03:
   - **MemoryAgent** (UC-01): Full hybrid system using all tiers
   - **RAGAgent** (UC-02): Standard RAG baseline using single vector store
   - **FullContextAgent** (UC-03): Naive full-context baseline

3. **Multi-Agent Coordination**: Enable LangGraph-based orchestration with shared/personal state management.

4. **Benchmark Integration**: Expose HTTP API for GoodAI LTM benchmark runner.

### 3.2 Non-Goals (Deferred to Phase 4)

- GoodAI LTM benchmark dataset integration
- Benchmark runner implementation
- Evaluation metrics and scoring
- Performance optimization for latency targets (accepted as-is)
- Production deployment configuration

---

## 4. High-Level Architecture

### 4.1 System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                     Benchmark Runner (Phase 4)                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Agent Wrapper API (FastAPI)                    │
│                        POST /run_turn                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LangGraph Orchestrator                         │
│         ┌─────────────┬─────────────┬─────────────┐             │
│         │ MemoryAgent │  RAGAgent   │FullContext  │             │
│         │   (UC-01)   │   (UC-02)   │   (UC-03)   │             │
│         └──────┬──────┴──────┬──────┴──────┬──────┘             │
└────────────────┼─────────────┼─────────────┼────────────────────┘
                 │             │             │
                 ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│               UnifiedMemorySystem (Enhanced)                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Operating Memory (Redis)                     │   │
│  │   PersonalMemoryState │ SharedWorkspaceState │ Pub/Sub   │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Memory Tiers (L1-L4)                         │   │
│  │   L1: ActiveContext → L2: WorkingMemory →                │   │
│  │   L3: EpisodicMemory → L4: SemanticMemory                │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Lifecycle Engines                            │   │
│  │   PromotionEngine │ ConsolidationEngine │ DistillationEng│   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Storage Layer (Phase 1)                      │
│   Redis │ PostgreSQL │ Qdrant │ Neo4j │ Typesense              │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Component Relationships

```
src/
├── agents/                           # NEW in Phase 3
│   ├── __init__.py
│   ├── base_agent.py                # BaseAgent interface
│   ├── memory_agent.py              # UC-01: Full hybrid system
│   ├── rag_agent.py                 # UC-02: Standard RAG baseline
│   ├── full_context_agent.py        # UC-03: Full-context baseline
│   └── orchestrator.py              # LangGraph multi-agent orchestrator
├── api/                              # NEW in Phase 3
│   ├── __init__.py
│   └── agent_wrapper.py             # FastAPI /run_turn endpoint
├── memory/
│   ├── models.py                    # Pydantic models (existing)
│   ├── ciar_scorer.py              # CIAR calculation (existing)
│   ├── tiers/                       # Memory tier classes (existing)
│   │   ├── active_context_tier.py
│   │   ├── working_memory_tier.py
│   │   ├── episodic_memory_tier.py
│   │   └── semantic_memory_tier.py
│   └── engines/                     # Lifecycle engines (existing)
│       ├── promotion_engine.py
│       ├── consolidation_engine.py
│       ├── distillation_engine.py
│       └── knowledge_synthesizer.py
├── storage/                         # Storage adapters (existing)
└── utils/                           # Utilities (existing)
    └── llm_client.py               # Multi-provider LLM abstraction
```

---

## 5. Detailed Design

### 5.1 Enhanced UnifiedMemorySystem

**Current State**: `memory_system.py` at project root handles Operating Memory (Redis) and delegates to `KnowledgeStoreManager` for queries.

**Enhancement Required**: Integrate tier classes from `src/memory/tiers/` with lifecycle engines from `src/memory/engines/`.

```python
class UnifiedMemorySystem(HybridMemorySystem):
    """Enhanced memory system integrating all tiers and engines."""
    
    def __init__(
        self,
        redis_client: redis.StrictRedis,
        knowledge_manager: KnowledgeStoreManager,
        # NEW: Tier instances
        l1_tier: ActiveContextTier,
        l2_tier: WorkingMemoryTier,
        l3_tier: EpisodicMemoryTier,
        l4_tier: SemanticMemoryTier,
        # NEW: Engine instances (optional for baseline configs)
        promotion_engine: Optional[PromotionEngine] = None,
        consolidation_engine: Optional[ConsolidationEngine] = None,
        distillation_engine: Optional[DistillationEngine] = None,
    ):
        ...
    
    # NEW: Lifecycle trigger methods
    async def run_promotion_cycle(self, session_id: str) -> List[Fact]:
        """Trigger L1→L2 promotion for a session."""
        ...
    
    async def run_consolidation_cycle(self, session_id: str) -> List[Episode]:
        """Trigger L2→L3 consolidation for a session."""
        ...
    
    async def run_distillation_cycle(self, session_id: str) -> List[KnowledgeDocument]:
        """Trigger L3→L4 distillation for a session."""
        ...
    
    # NEW: Unified query across tiers
    async def query_memory(
        self,
        query_text: str,
        tiers: List[Literal["l1", "l2", "l3", "l4"]] = ["l2", "l3", "l4"],
        top_k: int = 10,
    ) -> Dict[str, List[Any]]:
        """Query multiple tiers and merge results."""
        ...
```

### 5.2 Agent Framework

#### 5.2.1 BaseAgent Interface

```python
# src/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel

class AgentInput(BaseModel):
    """Input to agent from benchmark runner."""
    conversation_history: List[Dict[str, str]]  # [{"role": "user/assistant", "content": "..."}]
    current_message: str
    session_id: str
    turn_number: int

class AgentOutput(BaseModel):
    """Output from agent to benchmark runner."""
    response: str
    metadata: Dict[str, Any] = {}  # Reasoning traces, memory accesses, etc.

class BaseAgent(ABC):
    """Abstract base for all agent implementations."""
    
    def __init__(self, memory_system: UnifiedMemorySystem, llm_client: LLMClient):
        self.memory = memory_system
        self.llm = llm_client
    
    @abstractmethod
    async def process_turn(self, input: AgentInput) -> AgentOutput:
        """Process a single conversation turn."""
        ...
    
    @abstractmethod
    async def retrieve_context(self, query: str, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve relevant context from memory."""
        ...
    
    async def health_check(self) -> Dict[str, bool]:
        """Check agent and dependency health."""
        ...
```

#### 5.2.2 MemoryAgent (UC-01: Full Hybrid System)

The primary agent using all four memory tiers.

```python
# src/agents/memory_agent.py
class MemoryAgent(BaseAgent):
    """
    Full hybrid memory agent (UC-01).
    
    Uses all four tiers:
    - L1 for recent turns (implicit via conversation_history)
    - L2 for significant facts (PersonalMemoryState.scratchpad)
    - L3 for episode retrieval (semantic + graph queries)
    - L4 for distilled knowledge (pattern matching)
    """
    
    async def process_turn(self, input: AgentInput) -> AgentOutput:
        """
        Pipeline:
        1. Load personal state from Operating Memory
        2. Query L3/L4 for relevant knowledge
        3. Synthesize context with current message
        4. Generate response via LLM
        5. Update personal state
        6. (Async) Trigger promotion engine for new turn
        """
        # Step 1: Retrieve internal state
        personal_state = self.memory.get_personal_state(f"agent_{input.session_id}")
        
        # Step 2: Query persistent knowledge
        l3_results = await self.memory.query_knowledge(
            store_type="vector",
            query_text=input.current_message,
            top_k=5
        )
        l4_results = await self.memory.l4_tier.search(
            query_text=input.current_message,
            limit=3
        )
        
        # Step 3: Synthesize context
        context = self._build_context(
            conversation=input.conversation_history[-10:],  # L1-like window
            scratchpad=personal_state.scratchpad,  # L2-like working memory
            episodes=l3_results,  # L3 episodes
            knowledge=l4_results  # L4 knowledge
        )
        
        # Step 4: Generate response
        response = await self.llm.generate(
            prompt=self._format_prompt(context, input.current_message)
        )
        
        # Step 5: Update state
        personal_state.scratchpad["last_response"] = response.text
        self.memory.update_personal_state(personal_state)
        
        # Step 6: Background promotion (non-blocking)
        asyncio.create_task(
            self.memory.run_promotion_cycle(input.session_id)
        )
        
        return AgentOutput(
            response=response.text,
            metadata={
                "l3_context_count": len(l3_results),
                "l4_context_count": len(l4_results),
            }
        )
```

#### 5.2.3 RAGAgent (UC-02: Standard RAG Baseline)

Simple single-vector-store agent for comparison.

```python
# src/agents/rag_agent.py
class RAGAgent(BaseAgent):
    """
    Standard RAG baseline agent (UC-02).
    
    - Stateless: No personal memory between turns
    - Single retrieval: Query only Qdrant vector store
    - No tiered memory: All history indexed in one collection
    """
    
    async def process_turn(self, input: AgentInput) -> AgentOutput:
        """
        Simplified pipeline:
        1. Query single vector store with current message
        2. Concatenate retrieved chunks with message
        3. Generate response
        (No state management)
        """
        # Single-pass retrieval
        chunks = await self.memory.query_knowledge(
            store_type="vector",
            query_text=input.current_message,
            top_k=10
        )
        
        # Direct synthesis
        context = "\n".join([c["content"] for c in chunks])
        response = await self.llm.generate(
            prompt=f"Context:\n{context}\n\nUser: {input.current_message}\nAssistant:"
        )
        
        return AgentOutput(
            response=response.text,
            metadata={"chunks_retrieved": len(chunks)}
        )
```

#### 5.2.4 FullContextAgent (UC-03: Full-Context Baseline)

Naive approach passing entire history to LLM.

```python
# src/agents/full_context_agent.py
class FullContextAgent(BaseAgent):
    """
    Full-context baseline agent (UC-03).
    
    - No retrieval: Entire conversation history in prompt
    - No memory system: History stored as single Redis list
    - Maximum tokens: Tests LLM context window limits
    """
    
    async def process_turn(self, input: AgentInput) -> AgentOutput:
        """
        Naive pipeline:
        1. Concatenate entire conversation history
        2. Append current message
        3. Send full context to LLM
        (No retrieval, no filtering)
        """
        # Build massive context
        full_history = "\n".join([
            f"{turn['role'].capitalize()}: {turn['content']}"
            for turn in input.conversation_history
        ])
        
        # Direct generation with full history
        response = await self.llm.generate(
            prompt=f"{full_history}\nUser: {input.current_message}\nAssistant:"
        )
        
        return AgentOutput(
            response=response.text,
            metadata={
                "context_turns": len(input.conversation_history),
                "estimated_tokens": len(full_history.split()) * 1.3
            }
        )
```

### 5.3 LangGraph Orchestrator

Multi-agent coordination using LangGraph state graphs.

```python
# src/agents/orchestrator.py
from langgraph.graph import StateGraph, END
from typing import TypedDict

class AgentState(TypedDict):
    """Shared state across agent nodes."""
    session_id: str
    input: AgentInput
    personal_state: PersonalMemoryState
    shared_state: Optional[SharedWorkspaceState]
    context: List[Dict[str, Any]]
    response: Optional[str]
    
class AgentOrchestrator:
    """
    LangGraph-based multi-agent orchestrator.
    
    Manages:
    - Personal memory states per agent
    - Shared workspace for multi-agent collaboration
    - State transitions and routing
    """
    
    def __init__(self, memory_system: UnifiedMemorySystem, agents: Dict[str, BaseAgent]):
        self.memory = memory_system
        self.agents = agents
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph state machine."""
        graph = StateGraph(AgentState)
        
        # Node definitions
        graph.add_node("load_state", self._load_state)
        graph.add_node("retrieve_context", self._retrieve_context)
        graph.add_node("planner", self._run_planner)
        graph.add_node("save_state", self._save_state)
        
        # Edge definitions
        graph.add_edge("load_state", "retrieve_context")
        graph.add_edge("retrieve_context", "planner")
        graph.add_edge("planner", "save_state")
        graph.add_edge("save_state", END)
        
        graph.set_entry_point("load_state")
        return graph.compile()
    
    async def process(self, input: AgentInput, agent_type: str = "memory") -> AgentOutput:
        """Route to appropriate agent and process turn."""
        initial_state = AgentState(
            session_id=input.session_id,
            input=input,
            personal_state=None,
            shared_state=None,
            context=[],
            response=None
        )
        
        result = await self.graph.ainvoke(initial_state)
        return AgentOutput(response=result["response"])
```

### 5.4 Agent Wrapper API

FastAPI endpoint for benchmark runner integration.

```python
# src/api/agent_wrapper.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Literal

app = FastAPI(title="MAS Memory Layer Agent API", version="1.0.0")

class RunTurnRequest(BaseModel):
    """Request format from benchmark runner."""
    conversation_history: List[Dict[str, str]]
    current_message: str
    session_id: str
    turn_number: int
    agent_type: Literal["memory", "rag", "full_context"] = "memory"

class RunTurnResponse(BaseModel):
    """Response format to benchmark runner."""
    response: str
    metadata: Dict[str, Any] = {}

@app.post("/run_turn", response_model=RunTurnResponse)
async def run_turn(request: RunTurnRequest) -> RunTurnResponse:
    """
    Process a single conversation turn.
    
    Endpoint for GoodAI LTM Benchmark runner integration.
    Routes to appropriate agent based on agent_type parameter.
    """
    agent_input = AgentInput(
        conversation_history=request.conversation_history,
        current_message=request.current_message,
        session_id=request.session_id,
        turn_number=request.turn_number
    )
    
    agent = orchestrator.agents[request.agent_type]
    output = await agent.process_turn(agent_input)
    
    return RunTurnResponse(
        response=output.response,
        metadata=output.metadata
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agents": list(orchestrator.agents.keys())}
```

### 5.5 Memory Interface & Tool Design

This section defines how agents interact with the memory system. Our approach is **novel**: we provide BOTH a unified interface AND granular per-tier/feature tools, enabling agents to reason about memory at multiple abstraction levels.

#### 5.5.1 Latency-Based Storage Strategy

| Tier | Storage | Latency Class | Use Case |
|------|---------|---------------|----------|
| L1 | Redis | **Critical** (<10ms) | Real-time context, personal state, pub/sub |
| L2 | PostgreSQL | **Medium** (10-100ms) | Fact storage, CIAR queries, structured data |
| L3 | Qdrant + Neo4j | **Relaxed** (100ms-1s) | Episode retrieval, semantic search, graph traversal |
| L4 | Typesense | **Relaxed** (100ms-500ms) | Knowledge search, full-text queries |

**Design Implication**: Latency-critical operations (state load/save) use Redis exclusively. Agents can tolerate higher latency for knowledge retrieval (L3/L4).

#### 5.5.2 Tool Architecture: Unified + Granular

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEMORY TOOL INTERFACE                        │
├─────────────────────────────────────────────────────────────────┤
│  UNIFIED INTERFACE (High-Level Abstraction)                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ memory_query()      - Cross-tier semantic search        │   │
│  │ memory_store()      - Store with automatic tier routing │   │
│  │ get_context_block() - Assembled context for prompts     │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  GRANULAR TIER TOOLS (Per-Layer Access)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ L1: l1_get_recent_turns(), l1_append_turn()             │   │
│  │ L2: l2_search_facts(), l2_store_fact(), l2_get_by_ciar()│   │
│  │ L3: l3_search_episodes(), l3_query_graph()              │   │
│  │ L4: l4_search_knowledge(), l4_get_by_type()             │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  FEATURE TOOLS (Critical Capabilities)                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ciar_calculate()     - Compute CIAR score for content   │   │
│  │ ciar_explain()       - Explain CIAR score breakdown     │   │
│  │ ciar_get_top_facts() - Get highest-significance facts   │   │
│  │ synthesize_knowledge() - Query-time synthesis           │   │
│  │ extract_facts()      - Explicit fact extraction         │   │
│  │ consolidate_session() - Trigger L2→L3 consolidation     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.5.3 Tool Implementation Path

Tools will be implemented in a new `src/agents/tools/` directory:

```
src/agents/tools/
├── __init__.py
├── unified_tools.py       # memory_query(), get_context_block(), memory_store()
├── tier_tools.py          # L1-L4 granular access tools
├── ciar_tools.py          # CIAR calculation, explanation, analysis
└── synthesis_tools.py     # Knowledge synthesis, fact extraction
```

**Key Design Principle**: All tools use LangChain's `@tool` decorator with Pydantic input schemas for cross-LLM compatibility (Gemini, OpenAI, Anthropic).

#### 5.5.4 Example Tool Definitions

```python
# src/agents/tools/unified_tools.py
from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class MemoryQueryInput(BaseModel):    
    query: str = Field(description="Natural language query for memory search")
    tiers: List[Literal["L1", "L2", "L3", "L4"]] = Field(
        default=["L2", "L3", "L4"],
        description="Memory tiers to search"
    )
    top_k: int = Field(default=10, ge=1, le=50)
    min_ciar: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Minimum CIAR score filter (L2 only)"
    )

@tool(args_schema=MemoryQueryInput)
async def memory_query(
    query: str,
    tiers: List[str] = ["L2", "L3", "L4"],
    top_k: int = 10,
    min_ciar: Optional[float] = None
) -> dict:
    """
    Search across multiple memory tiers for relevant information.
    
    Returns results with tier attribution for provenance reasoning.
    Combines facts (L2), episodes (L3), and knowledge (L4).
    """
    ...

# src/agents/tools/ciar_tools.py
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class CIARFilters(BaseModel):
    """CIAR-aware filtering for fact retrieval (RT-05 validated)."""
    min_certainty: float = Field(default=0.7, ge=0.0, le=1.0)
    min_impact: int = Field(default=5, ge=1, le=10)
    max_age_days: Optional[int] = Field(default=30, ge=1)
    recency_boost: bool = Field(default=True)

class CIARFactExtraction(BaseModel):
    """
    Reasoning-First schema for fact extraction (RT-02 validated).
    
    CRITICAL: Field ordering matters for constrained decoding.
    thought_process MUST generate before certainty_score.
    """
    thought_process: str = Field(
        description="Step-by-step analysis of ambiguity, evidence quality, "
        "and temporal context BEFORE assigning scores"
    )
    facts: List["CIARFact"]

class CIARFact(BaseModel):
    """Single fact with CIAR scoring (RT-02 + RT-05 validated)."""
    content: str = Field(description="The atomic fact extracted")
    evidence: str = Field(description="Direct quote or reference supporting the fact")
    certainty_reasoning: str = Field(
        description="Reasoning for certainty score - MUST precede certainty_score"
    )
    certainty_score: float = Field(ge=0.0, le=1.0, description="0.0-1.0 confidence")
    impact_score: int = Field(ge=1, le=10, description="1-10 significance")
    temporal_context: str = Field(description="Age analysis relative to conversation")

@tool
async def ciar_calculate(
    content: str,
    certainty: float,
    impact: float,
    days_old: int = 0,
    access_count: int = 0
) -> dict:
    """
    Calculate CIAR significance score for information.
    
    Formula: CIAR = (Certainty × Impact) × exp(-0.0231×days) × (1 + 0.1×accesses)
    
    Research validation (RT-05): 18-48% improvement in agent decision quality.
    """
    ...

@tool
async def ciar_get_top_facts(
    query: str,
    filters: CIARFilters,
    limit: int = 10
) -> List[dict]:
    """
    Retrieve facts filtered by CIAR thresholds (RT-05 validated).
    
    Pipeline:
    1. Semantic search (cosine similarity)
    2. Impact filter (Zep "poignancy" pattern)
    3. Age/validity check (temporal grounding)
    4. Recency decay (exponential: e^(-λt))
    5. Certainty threshold (confidence calibration)
    
    Research finding: 70-90% noise reduction with CIAR filtering.
    """
    ...

@tool
async def ciar_explain(fact_id: str) -> dict:
    """
    Get detailed CIAR breakdown for an existing fact.
    
    Returns component scores (certainty, impact, age_decay, recency_boost)
    with BOTH numeric values AND verbal explanations for transparency.
    
    Output format (RT-05 validated):
    - Numeric: For system-level filtering and routing
    - Categorical: For prompt-level reasoning (high/medium/low)
    - Verbal: For user-facing explanations
    """
    ...
```

### 5.6 Namespace Strategy for Concurrent Agents

Multi-agent systems require careful memory isolation and sharing. Our namespace strategy balances agent autonomy with collaborative knowledge sharing.

#### 5.6.1 Namespace Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    NAMESPACE HIERARCHY                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  GLOBAL (Cross-User)                                           │
│  └── domain:{domain_id}:knowledge      (L4 shared knowledge)   │
│                                                                 │
│  USER SCOPE (Shared Across Sessions)                           │
│  └── user:{user_id}                                            │
│      ├── facts        (L2 - user's accumulated facts)          │
│      ├── episodes     (L3 - user's experience history)         │
│      └── preferences  (L4 - user-specific knowledge)           │
│                                                                 │
│  SESSION SCOPE (Single Conversation)                           │
│  └── session:{session_id}                                      │
│      ├── turns        (L1 - conversation buffer)               │
│      └── workspace    (Shared workspace for multi-agent)       │
│                                                                 │
│  AGENT SCOPE (Agent-Private)                                   │
│  └── agent:{agent_id}:session:{session_id}                     │
│      ├── state        (PersonalMemoryState)                    │
│      ├── scratchpad   (Working notes)                          │
│      └── candidates   (Promotion candidates)                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.6.2 Redis Key Patterns (Hash Tagged)

```python
# src/memory/namespace.py
class NamespaceManager:
    """
    Manages namespaced keys for multi-agent memory isolation.
    
    CRITICAL: All keys sharing atomic operations MUST use the same
    Hash Tag to ensure Redis Cluster colocation.
    """
    
    # L1: Active Context (Session-scoped with Hash Tag)
    @staticmethod
    def l1_turns(session_id: str) -> str:
        return f"{{session:{session_id}}}:turns"
    
    @staticmethod
    def l1_turn_metadata(session_id: str) -> str:
        return f"{{session:{session_id}}}:turn_meta"
    
    # Operating Memory: Personal State (Agent+Session-scoped, same Hash Tag)
    @staticmethod
    def personal_state(agent_id: str, session_id: str) -> str:
        return f"{{session:{session_id}}}:agent:{agent_id}:state"
    
    @staticmethod
    def agent_scratchpad(agent_id: str, session_id: str) -> str:
        return f"{{session:{session_id}}}:agent:{agent_id}:scratchpad"
    
    # Operating Memory: Shared Workspace (Session-scoped, same Hash Tag)
    @staticmethod
    def shared_workspace(session_id: str, workspace_id: str) -> str:
        return f"{{session:{session_id}}}:workspace:{workspace_id}"
    
    # Lifecycle Events (Redis Streams for durable coordination - RT-03)
    @staticmethod
    def lifecycle_stream(session_id: str) -> str:
        return f"{{session:{session_id}}}:lifecycle:events"
    
    # Directory indexes for efficient lookups (RT-03 recommendation)
    @staticmethod
    def session_agents_index(session_id: str) -> str:
        return f"{{session:{session_id}}}:directory:agents"
```

#### 5.6.2.1 Lua Scripts for Atomic State Transitions (RT-03)

> **Rejected Approach**: Client-side WATCH-based optimistic locking causes "retry storms" under concurrent agent load (90% failure rate observed in research).

```lua
-- lua/atomic_promotion.lua
-- Atomic L1→L2 fact promotion with CIAR filtering
local l1_key = KEYS[1]
local l2_key = KEYS[2]
local fact_json = ARGV[1]
local ciar_threshold = tonumber(ARGV[2])

local fact = cjson.decode(fact_json)
if fact.ciar_score >= ciar_threshold then
    redis.call('SADD', l2_key, fact_json)
    redis.call('LREM', l1_key, 1, fact_json)
    return 1  -- Promoted
else
    return 0  -- Filtered (below threshold)
end
```

```lua
-- lua/workspace_update.lua
-- Atomic workspace update with version check
local key = KEYS[1]
local agent_id = ARGV[1]
local update_json = ARGV[2]
local expected_version = tonumber(ARGV[3])

local raw = redis.call('GET', key)
local state = {}
if raw then
    state = cjson.decode(raw)
else
    state = {version=0, updates={}}
end

-- Version check for optimistic concurrency
if expected_version and state.version ~= expected_version then
    return cjson.encode({success=false, error="VERSION_MISMATCH", current=state.version})
end

-- Append update (smart merge, not overwrite)
table.insert(state.updates, {agent=agent_id, data=cjson.decode(update_json), ts=redis.call('TIME')[1]})
state.version = state.version + 1
state.last_updated_by = agent_id

redis.call('SET', key, cjson.encode(state))
return cjson.encode({success=true, version=state.version})
```

#### 5.6.3 PostgreSQL Namespace (L2)

```sql
-- L2 facts include user_id and session_id for scoping
CREATE TABLE significant_facts (
    fact_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,           -- User scope
    session_id VARCHAR(64) NOT NULL,        -- Session scope
    agent_id VARCHAR(64),                   -- Which agent extracted it
    content TEXT NOT NULL,
    ciar_score FLOAT NOT NULL,
    -- ... other columns ...
    
    -- Indexes for namespace queries
    INDEX idx_user_facts (user_id, ciar_score DESC),
    INDEX idx_session_facts (session_id, extracted_at DESC),
    INDEX idx_agent_facts (agent_id, session_id)
);
```

#### 5.6.4 Access Control Matrix

| Resource | MemoryAgent | RAGAgent | FullContextAgent | ConsolidationAgent |
|----------|-------------|----------|------------------|--------------------|
| L1 turns (own session) | Read/Write | Read | Read | Read |
| L2 facts (user scope) | Read/Write | Read | - | Read |
| L3 episodes (user scope) | Read | Read | - | Read/Write |
| L4 knowledge (domain) | Read | Read | - | Read |
| Personal state (own) | Read/Write | - | - | Read/Write |
| Shared workspace | Read/Write | - | - | Read |

#### 5.6.5 Conflict Resolution Strategy (Updated per RT-03)

When multiple agents modify shared state:

1. **❌ ~~Optimistic Locking (WATCH)~~**: REJECTED - causes 90% retry rate under concurrency
2. **✅ Lua Scripting (Server-Side Atomicity)**: Serializable execution, 0% conflict rate
3. **✅ Smart Merge**: Append-only patterns for accumulated data (facts, updates)
4. **✅ Redis Streams**: Durable event sourcing for lifecycle coordination

```python
class SharedWorkspaceState(BaseModel):
    workspace_id: str
    version: int = 0  # For optimistic checks in Lua script
    last_modified_by: str  # agent_id
    last_updated: datetime
    updates: List[Dict[str, Any]] = []  # Append-only history
    
    # NOTE: Version increments happen atomically in Lua script,
    # NOT via Python increment_version() method.
```

#### 5.6.6 Redis Streams for Lifecycle Coordination (RT-03)

> **Rejected Approach**: Redis Pub/Sub is fire-and-forget (messages lost if consumer busy).

```python
# Producer: Promotion Engine publishes to stream
await redis.xadd(
    "{session:101}:lifecycle:events",
    {"event": "fact_promoted", "fact_id": "abc123", "ciar_score": "0.72"}
)

# Consumer: Consolidation Engine reads as consumer group
messages = await redis.xreadgroup(
    groupname="consolidation_workers",
    consumername="worker_1",
    streams={"{session:101}:lifecycle:events": ">"}
)
```

---

## 6. Requirements

### 6.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | UnifiedMemorySystem must integrate all four tier classes | P0 |
| FR-02 | UnifiedMemorySystem must provide methods to trigger lifecycle engines | P0 |
| FR-03 | Memory Tool Interface must provide unified + granular access | P0 |
| FR-04 | CIAR tools must expose significance scoring to agents | P0 |
| FR-05 | Namespace strategy must isolate agent-private state | P0 |
| FR-06 | BaseAgent must define standard interface for all agent types | P0 |
| FR-07 | MemoryAgent must use all four tiers (L1-L4) per UC-01 | P0 |
| FR-08 | RAGAgent must use only vector store per UC-02 | P0 |
| FR-09 | FullContextAgent must pass entire history per UC-03 | P0 |
| FR-10 | AgentOrchestrator must manage personal/shared state via LangGraph | P0 |
| FR-11 | Agent Wrapper API must expose `/run_turn` POST endpoint | P0 |
| FR-12 | Agent Wrapper API must support agent_type routing | P1 |
| FR-13 | All agents must return response + metadata | P1 |

### 6.2 Non-Functional Requirements

| ID | Requirement | Notes |
|----|-------------|-------|
| NFR-01 | Async-first architecture | All agent methods must be async |
| NFR-02 | Non-blocking lifecycle triggers | Background task for promotion/consolidation |
| NFR-03 | Pydantic v2 models | Consistent with Phase 1-2 |
| NFR-04 | Test coverage ≥80% | Per project standards |
| NFR-05 | Type hints on all public methods | mypy compatible |

### 6.3 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `langgraph` | ≥0.1.0 | Multi-agent state graph orchestration |
| `langchain-core` | ≥0.2.0 | LangGraph dependency |
| `fastapi` | ≥0.100.0 | Agent Wrapper API |
| `uvicorn` | ≥0.23.0 | ASGI server |

---

## 7. Implementation Plan

### 7.1 Phase 3A: Memory Tool Interface & UnifiedMemorySystem Enhancement (Week 1-2)

**Tasks**:
1. Create `src/agents/tools/` directory structure
2. Implement `NamespaceManager` in `src/memory/namespace.py`
3. Refactor `memory_system.py` to import and integrate tier classes
4. Add lifecycle engine injection via constructor
5. Implement `run_promotion_cycle()`, `run_consolidation_cycle()`, `run_distillation_cycle()`
6. Implement `query_memory()` for cross-tier queries
7. Implement unified tools (`memory_query`, `get_context_block`, `memory_store`)
8. Unit tests for enhanced UnifiedMemorySystem and tools

**Deliverables**:
- `src/memory/namespace.py`
- `src/agents/tools/unified_tools.py`
- Enhanced `memory_system.py`
- Tests in `tests/test_memory_system.py` and `tests/agents/tools/`

### 7.2 Phase 3B: Granular Tools & Agent Framework (Week 2-4)

**Tasks**:
1. Implement granular tier tools (`tier_tools.py`)
2. Implement CIAR feature tools (`ciar_tools.py`)
3. Implement synthesis tools (`synthesis_tools.py`)
4. Create `src/agents/` directory structure
5. Implement `BaseAgent` abstract class with tool binding
6. Implement `MemoryAgent` (UC-01) with full tool access
7. Implement `RAGAgent` (UC-02) with limited tools
8. Implement `FullContextAgent` (UC-03) without tools
9. Unit tests for all tools and agent classes

**Deliverables**:
- `src/agents/tools/tier_tools.py`
- `src/agents/tools/ciar_tools.py`
- `src/agents/tools/synthesis_tools.py`
- `src/agents/base_agent.py`
- `src/agents/memory_agent.py`
- `src/agents/rag_agent.py`
- `src/agents/full_context_agent.py`
- Tests in `tests/agents/` and `tests/agents/tools/`

### 7.3 Phase 3C: LangGraph Orchestration (Week 4-5)

**Tasks**:
1. Add `langgraph` dependency to requirements
2. Implement `AgentOrchestrator` with state graph
3. Define state transitions for single-agent flow
4. (Optional) Define multi-agent collaboration patterns
5. Integration tests for orchestrator

**Deliverables**:
- `src/agents/orchestrator.py`
- Tests in `tests/agents/test_orchestrator.py`

### 7.4 Phase 3D: Agent Wrapper API (Week 5-6)

**Tasks**:
1. Create `src/api/` directory structure
2. Implement FastAPI application with `/run_turn` endpoint
3. Implement `/health` endpoint
4. Add startup/shutdown hooks for memory system initialization
5. API tests with TestClient

**Deliverables**:
- `src/api/agent_wrapper.py`
- `src/api/__init__.py`
- Tests in `tests/api/`

### 7.5 Phase 3E: Integration Testing (Week 6-8)

**Tasks**:
1. End-to-end tests with mocked storage
2. End-to-end tests with real storage backends (optional)
3. Multi-turn conversation tests
4. State persistence tests
5. Documentation updates

**Deliverables**:
- `tests/integration/test_e2e_agents.py`
- Updated `README.md` with agent usage examples

---

## 8. Success Criteria

### 8.1 Acceptance Gates

| Gate | Criteria | Validation Method |
|------|----------|-------------------|
| AG-01 | All three agent variants implemented and tested | pytest reports |
| AG-02 | UnifiedMemorySystem integrates all tiers + engines | Unit tests |
| AG-03 | `/run_turn` API endpoint operational | Integration tests |
| AG-04 | Test coverage ≥80% for Phase 3 code | pytest-cov |
| AG-05 | LangGraph orchestrator manages state correctly | State transition tests |

### 8.2 Definition of Done

Phase 3 is complete when:
1. ✅ `src/agents/` package contains all agent implementations
2. ✅ `src/api/` package contains Agent Wrapper API
3. ✅ Enhanced `UnifiedMemorySystem` passes all integration tests
4. ✅ All acceptance gates pass
5. ✅ DEVLOG updated with Phase 3 completion entry

---

## 9. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LangGraph API changes | Medium | Low | Pin version, monitor releases |
| LLM rate limits during agent testing | Medium | Medium | Use mocks for unit tests, circuit breaker for integration |
| Memory system integration complexity | High | Medium | Incremental integration, comprehensive tests |
| Performance regressions | Low | Low | Accepted as-is per project decision |

---

## 10. Open Questions & Research Topics

This section tracks decisions requiring team input and topics requiring deeper research before implementation. See companion document [Phase 3 Research Questions](spec-phase3-research-questions.md) for detailed research plan.

### 10.1 Resolved Decisions

| Question | Decision | Rationale |
|----------|----------|-----------||
| Latency targets | Accepted as-is | Distributed system with Qdrant/Neo4j cannot meet <100ms |
| CIAR exposure to agents | Yes, via dedicated tools | Enables transparent reasoning about significance |
| Tool granularity | Both unified + granular | Flexibility for different agent reasoning patterns |
| Benchmark dataset | Deferred to Phase 4 | Focus Phase 3 on agent framework |

### 10.2 Open Questions Requiring Team Input

#### OQ-01: Shared Workspace Scope
**Question**: Should Phase 3 implement full multi-agent collaboration (SharedWorkspaceState) or just single-agent flows?

**Options**:
- A) Full implementation with pub/sub coordination
- B) Basic shared state without real-time sync
- C) Defer to Phase 4

**Recommendation**: Option B - implement SharedWorkspaceState but without complex pub/sub patterns initially.

#### OQ-02: Background Consolidation Trigger
**Question**: When should L2→L3 consolidation run?

**Options**:
- A) After each turn (async background task)
- B) End of session
- C) Time-based (every N minutes)
- D) Threshold-based (when L2 fact count > N)

**Recommendation**: Option D with fallback to B - consolidate when facts accumulate, ensure consolidation on session end.

#### OQ-03: API Authentication
**Question**: Should Agent Wrapper API include authentication?

**Options**:
- A) No auth (rely on network security)
- B) API key authentication
- C) JWT tokens

**Recommendation**: Option B for Phase 3 - simple API keys, defer JWT to production deployment.

#### OQ-04: Partial Failure Handling
**Question**: How should agents handle partial memory system failures?

**Example**: L3 (Qdrant) unavailable but L1/L2 working.

**Options**:
- A) Fail fast - return error to benchmark
- B) Graceful degradation - continue with available tiers
- C) Fallback to full-context mode

**Recommendation**: Option B with degradation logging for observability.

#### OQ-05: Context Block Template — RESOLVED ✅
**Question**: What should the default context block template contain?

**Decision (RT-04 Validated)**: Use **Tool Message Injection** pattern to preserve prompt cache. Context Block injected at tail of message history, NOT in system prompt.

**Implementation Pattern** (RT-04):
```python
# CORRECT: Tool Message injection preserves cache
messages = [
    SystemMessage(content=system_prompt),  # CACHED (static)
    *conversation_history,                  # CACHED (grows slowly)
    ToolMessage(                           # DYNAMIC (not cached)
        content=context_block,
        tool_call_id="context_injection"
    ),
    HumanMessage(content=user_query)       # DYNAMIC
]
```

**Context Block Template** (with CIAR scores for transparent reasoning):
```xml
<CONTEXT injected_at="tool_message" ciar_filtered="true">
  <L1_RECENT_TURNS count="5">
    <!-- Immediate conversation context -->
  </L1_RECENT_TURNS>
  <L2_WORKING_MEMORY count="10" min_ciar="0.6">
    <!-- CIAR-filtered facts only (not all L2) -->
    <FACT ciar="0.85" certainty="high" impact="8" type="preference">
      User prefers async communication
    </FACT>
  </L2_WORKING_MEMORY>
  <L3_EPISODES count="3" retrieval="on_demand">
    <!-- Retrieved via tool call, not auto-injected -->
  </L3_EPISODES>
  <L4_KNOWLEDGE count="2" retrieval="on_demand">
    <!-- Retrieved via tool call, not auto-injected -->
  </L4_KNOWLEDGE>
</CONTEXT>
```

**Key Research Findings Applied**:
1. ✅ CIAR scores included (RT-05: 18-48% decision quality improvement)
2. ✅ L2 CIAR-filtered (RT-04: not all L2 facts, only ≥0.6 threshold)
3. ✅ L3/L4 on-demand (RT-04: tool retrieval, not auto-injection)
4. ✅ Tool Message position (RT-04: preserves prompt cache, 60-80% cost savings)

### 10.3 Research Topics — VALIDATED ✅

All five research topics have been validated. See [Research Validation README](../research/README.md) for critical analysis and detailed findings.

| Topic | Status | Key Finding | Impact |
|-------|--------|-------------|--------|
| **RT-01**: LangGraph Tool Integration | ✅ Validated | Hybrid architecture fully supported via StateGraph, InjectedState, sub-graphs | ADOPT as designed |
| **RT-02**: Gemini Structured Output | ✅ Validated | >95% reliability with Reasoning-First schemas | ADOPT with schema modifications |
| **RT-03**: Redis Namespace Strategy | ✅ Validated | **CRITICAL**: Hash Tags mandatory, Lua scripting required | MANDATORY namespace update |
| **RT-04**: Context Injection vs Retrieval | ✅ Validated | Hybrid L2 auto-inject + L3/L4 tool retrieval optimal | ADOPT Tool Message injection |
| **RT-05**: CIAR Decision-Making | ✅ Validated | 18-48% improvements observed (exceeds 10-20% hypothesis) | Strong validation for CIAR tools |

**Critical Architecture Updates from Research:**

1. **Namespace Strategy (RT-03)**: Use `{scope:id}:resource` Hash Tags for Redis Cluster compatibility
2. **State Transitions (RT-03)**: Replace WATCH-based optimistic locking with Lua scripting
3. **Coordination (RT-03)**: Use Redis Streams instead of Pub/Sub for durable event sourcing
4. **Context Injection (RT-04)**: Use Tool Message injection pattern to preserve prompt cache
5. **Schema Design (RT-02)**: Reasoning-First Pydantic schemas with certainty_reasoning before certainty_score
6. **L2 Auto-Injection (RT-04)**: CIAR-filtered retrieval before injection (not all L2 facts)

### 10.4 Novel Research Contributions

These aspects represent novel contributions for AIMS 2025 paper:

1. **CIAR-Based Significance Scoring**: Interpretable, tunable metric for memory promotion
2. **Four-Tier Hierarchical Architecture**: Cognitive-inspired separation of concerns
3. **Hybrid Tool Interface**: Both unified and granular access patterns
4. **Agent-Exposed Memory Reasoning**: Tools that enable reasoning about memory significance
5. **Bi-Temporal Episodic Model**: Full temporal tracking for fact validity and observation time

---

## 11. References

- [ADR-003: Four-Tier Memory Architecture](docs/ADR/003-four-layers-memory.md)
- [ADR-004: CIAR Scoring Formula](docs/ADR/004-ciar-scoring-formula.md)
- [UC-01: GoodAI LTM Benchmark (Full System)](docs/uc-01.md)
- [UC-02: Standard RAG Baseline](docs/uc-02.md)
- [UC-03: Full-Context Baseline](docs/uc-03.md)
- [Phase 2 Specification](docs/specs/spec-phase2-memory-tiers.md)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
