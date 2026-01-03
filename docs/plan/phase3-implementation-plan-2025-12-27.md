# Phase 3 Implementation Plan: Agent Integration Layer

**Version**: 1.3  
**Date**: December 28, 2025 (Updated)  
**Duration**: 6 weeks  
**Status**: Week 1 Complete | Week 2 Complete | Week 3 Complete  
**Prerequisites**: ✅ Phase 2 Complete (441/445 tests, 86% coverage)  
**Research Validation**: ✅ Complete — See [docs/research/README.md](../research/README.md)  
**Week 1 Status**: ✅ Complete (Dec 28, 2025) — Redis infrastructure implemented  
**Week 2 Status**: ✅ Complete (Dec 28, 2025) — UnifiedMemorySystem enhanced, agent tools created (47/47 tests passing)  
**Week 3 Status**: ✅ Complete (Dec 28, 2025) — CIAR tools, tier tools, synthesis tools, integration test infrastructure (6/6 connectivity tests passing)

---

## ✅ PRE-PHASE 3 PREREQUISITE COMPLETED: Architectural Flow Correction

**Status**: ✅ COMPLETE (December 28, 2025)  
**Priority**: P0 (WAS BLOCKER)  
**Actual Duration**: 1 day  
**Completed By**: Core Team

### Background

During ADR-003 architecture review (December 28, 2025), a critical mismatch was identified between the **documented architecture** (ADR-003) and the **current implementation** of the Promotion Engine (L1→L2 flow).

**Architecture Decision (ADR-003, Updated Dec 28, 2025)**:
- **L1**: Raw buffer (no pre-processing)
- **L2 Promotion**: Batch processing with compression & topic segmentation via Fast Inference LLMs (Groq/Gemini)

**Current Implementation Gap**:
- `PromotionEngine` retrieves ALL turns (no batch threshold)
- `FactExtractor` extracts individual facts (not topic segments)
- No compression or segmentation logic
- Wrong granularity for CIAR scoring

### Required Changes

#### 1. Update PromotionEngine Architecture
**File**: `src/memory/engines/promotion_engine.py`

**Changes Required**:
- [ ] Add **batch threshold trigger** (e.g., process when L1 buffer reaches 10-20 turns)
- [ ] Replace `FactExtractor` with `TopicSegmenter` (new component)
- [ ] Single API call to Fast Inference LLM for batch compression + segmentation
- [ ] Score **topic segments** (not individual facts) using CIAR
- [ ] Store segments in L2 as structured summaries

**Reference Documents**:
- [ADR-003: L2 Procedure](../ADR/003-four-layers-memory.md#l2-working-memory-significance-filtered-store) (Lines 42-45)
- [ADR-006: Fast Inference LLM Strategy](../ADR/006-free-tier-llm-strategy.md) (Groq Llama-3.3-70b, Gemini Flash)

#### 2. Create TopicSegmenter Component
**File**: `src/memory/engines/topic_segmenter.py` (NEW)

**Implementation**:
```python
class TopicSegmenter:
    """
    Segments and compresses batches of raw turns into coherent topics.
    
    Process:
    1. Receive batch of raw turns from L1 (e.g., 10-20 messages)
    2. Single LLM call to Fast Inference model (Groq/Gemini)
    3. Output: List of topic segments with:
       - content: Compressed summary of the topic
       - certainty: Confidence in the segment (0.0-1.0)
       - impact: Estimated significance (0.0-1.0)
       - turn_range: [start_idx, end_idx]
    """
    
    async def segment_batch(self, turns: List[Dict], metadata: Dict) -> List[TopicSegment]:
        """Single API call for compression + segmentation."""
        pass
```

**Acceptance Criteria**:
- [ ] Single LLM call per batch (not per turn)
- [ ] Output format compatible with CIAR scoring
- [ ] Compression reduces token count by 30-50%
- [ ] Segments are coherent and non-overlapping

#### 3. Update L2 Data Model
**File**: `src/memory/models.py`

**Changes Required**:
- [ ] Rename `Fact` → `TopicSegment` OR extend `Fact` to support segment metadata
- [ ] Add fields: `turn_range`, `compression_ratio`, `segment_index`
- [ ] Ensure compatibility with CIAR scorer

**Reference**: [ADR-004: CIAR Scoring Formula](../ADR/004-ciar-scoring-formula.md) (scoring interface requirements)

#### 4. Update Tests
**Files**: 
- `tests/memory/test_promotion_engine.py`
- `tests/memory/test_topic_segmenter.py` (NEW)

**Changes Required**:
- [ ] Test batch threshold triggering
- [ ] Test single API call to LLM
- [ ] Test segment compression and scoring
- [ ] Test L2 storage of segments

#### 5. Documentation Updates
**Files**:
- `docs/sd-02.md` (System Design for L1→L2 flow)
- `docs/dd-02.md` (Design Document for Promotion Engine)

**Changes Required**:
- [ ] Update flow diagrams to show batch processing
- [ ] Document `TopicSegmenter` component
- [ ] Update sequence diagrams for L1→L2 promotion

### Implementation Timeline

```
Day 1-2: Create TopicSegmenter + update PromotionEngine
Day 3:   Update data models and CIAR interface
Day 4:   Write tests and validate with real LLMs
Day 5:   Update documentation and merge
```

### Success Criteria

- [ ] All tests pass (unit + integration)
- [ ] `PromotionEngine` uses batch processing with threshold
- [ ] Single LLM call per batch (verified via logs)
- [ ] CIAR scoring operates on topic segments
- [ ] Documentation aligned with implementation

### Rollout Strategy

1. **Create feature branch**: `fix/adr-003-promotion-flow`
2. **Implement changes** with TDD (tests first)
3. **Validate** with smoke tests against Groq/Gemini
4. **Code review** with ADR-003 as checklist
5. **Merge** before Phase 3 Week 1 begins

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing tests | Run full test suite after each change |
| LLM API rate limits | Use mocked LLM for unit tests, real LLM for integration |
| CIAR scorer compatibility | Maintain backward compatibility with `Fact` model |
| Timeline slip | If >5 days, split into Phase 3.0 (parallel with W1) |

---

## Executive Summary

Phase 3 transforms the MAS Memory Layer from standalone infrastructure into a production-ready agent framework. This plan incorporates **validated research findings** from RT1-RT5, ensuring the implementation follows proven patterns and avoids identified pitfalls.

### Key Research-Driven Changes

| Finding | Impact | Implementation Change |
|---------|--------|-----------------------|
| **RT-03: Hash Tags MANDATORY** | Critical | All Redis keys must use `{scope:id}:resource` format |
| **RT-03: Lua > WATCH** | High | Replace optimistic locking with Lua scripts |
| **RT-03: Streams > Pub/Sub** | High | Use Redis Streams for lifecycle coordination |
| **RT-02: Reasoning-First** | Medium | Schema field ordering for constrained decoding |
| **RT-04: Tool Message Injection** | Medium | Context Block at tail, not in system prompt |
| **RT-05: CIAR Validated** | Confirmed | 18-48% improvement (exceeds hypothesis) |

---

## Week 1: Foundation & Critical Infrastructure

### W1.1: Namespace Manager with Hash Tags (P0 — CRITICAL)

**Objective**: Implement Redis key management with mandatory Hash Tags for Cluster compatibility.

**Tasks**:
- [ ] Create `src/memory/namespace.py`
- [ ] Implement `NamespaceManager` with Hash Tag patterns
- [ ] Create directory index keys for efficient lookups
- [ ] Add Redis Streams key patterns for lifecycle events
- [ ] Write unit tests for namespace generation

**Deliverables**:
```
src/memory/namespace.py
tests/memory/test_namespace.py
```

**Key Implementation** (Hash Tags):
```python
class NamespaceManager:
    @staticmethod
    def l1_turns(session_id: str) -> str:
        return f"{{session:{session_id}}}:turns"  # Hash Tag in braces
    
    @staticmethod
    def personal_state(agent_id: str, session_id: str) -> str:
        return f"{{session:{session_id}}}:agent:{agent_id}:state"
```

**Acceptance Criteria**:
- [x] All session-related keys share same Hash Tag
- [x] Unit tests verify slot colocation (CRC16 check)
- [x] Integration test with Redis Cluster mode

**Status**: ✅ Complete (Dec 28, 2025)

---

## Week 2: Enhanced UnifiedMemorySystem & Agent Tools (COMPLETE ✅)

**Objective**: Integrate tier classes with lifecycle engines and create foundational agent tools using ToolRuntime pattern.

### W2.1: Enhanced UnifiedMemorySystem (P0 — COMPLETE ✅)

**Status**: ✅ Complete (Dec 28, 2025)  
**Files Modified**: `memory_system.py`

**Deliverables**:
- [x] Refactored constructor to inject L1-L4 tier instances
- [x] Injected lifecycle engines (PromotionEngine, ConsolidationEngine, DistillationEngine)
- [x] Implemented `run_promotion_cycle(session_id)` delegating to PromotionEngine
- [x] Implemented `run_consolidation_cycle(session_id)` delegating to ConsolidationEngine
- [x] Implemented `run_distillation_cycle(session_id)` delegating to DistillationEngine
- [x] Implemented `query_memory()` with hybrid L2/L3/L4 search and configurable weights
- [x] Implemented `get_context_block()` returning ContextBlock model
- [x] All methods async for ASGI compatibility

**Key Features**:
- **Hybrid Query**: Min-max normalization per tier, weighted scoring, unified result schema
- **Context Assembly**: Recent L1 turns + CIAR-filtered L2 facts with token estimation
- **Backward Compatibility**: All tier/engine parameters optional
- **Error Handling**: Graceful degradation with informative error messages

**Test Coverage**: Integrated with existing `tests/memory/test_memory_system.py`

### W2.2: MAS Runtime Framework (P0 — COMPLETE ✅)

**Status**: ✅ Complete (Dec 28, 2025)  
**Files Created**: 
- `src/agents/runtime.py` (310 lines)
- `src/agents/__init__.py`
- `tests/agents/test_runtime.py` (26 tests)

**Deliverables**:
- [x] `MASContext` dataclass for immutable configuration
- [x] `MASToolRuntime` wrapper with 20+ helper methods
- [x] Context access methods (session_id, user_id, agent_id, organization_id)
- [x] State access methods (state values, messages)
- [x] Store access methods (async get/put)
- [x] Streaming methods (updates, status)
- [x] Comprehensive test suite (26/26 tests passing)

**Test Results**:
```
tests/agents/test_runtime.py::TestMASContext ............ 2 passed
tests/agents/test_runtime.py::TestMASToolRuntime ...... 24 passed
```

### W2.3: Data Models (P0 — COMPLETE ✅)

**Status**: ✅ Complete (Dec 28, 2025)  
**Files Modified**: `src/memory/models.py`

**Deliverables**:
- [x] `ContextBlock` model with prompt formatting methods
- [x] `SearchWeights` model with validation (sum-to-1.0)
- [x] Token estimation logic (character-based heuristic)
- [x] Export statements for new models

**Features**:
- ContextBlock includes: recent_turns, significant_facts, episode_summaries, knowledge_snippets
- `to_prompt_string()` method for LLM injection (structured or text format)
- `estimate_token_count()` using 4.0 chars/token heuristic
- SearchWeights custom validator ensures L2+L3+L4 weights = 1.0

### W2.4: Unified Agent Tools (P0 — COMPLETE ✅)

**Status**: ✅ Complete (Dec 28, 2025)  
**Files Created**:
- `src/agents/tools/__init__.py`
- `src/agents/tools/unified_tools.py` (460 lines)
- `tests/agents/tools/__init__.py`
- `tests/agents/tools/test_unified_tools.py` (21 tests)

**Deliverables**:
- [x] `memory_query` tool (cross-tier semantic search)
- [x] `get_context_block` tool (context assembly)
- [x] `memory_store` tool (content storage with tier routing)
- [x] All tools use `@tool` decorator from `langchain_core`
- [x] All tools use `runtime: ToolRuntime` parameter (hidden from LLM)
- [x] Pydantic input schemas for all tools
- [x] Comprehensive test suite (21/21 tests passing)

**Test Results**:
```
tests/agents/tools/test_unified_tools.py::TestToolInputSchemas ..... 6 passed
tests/agents/tools/test_unified_tools.py::TestToolFunctionSignatures  3 passed
tests/agents/tools/test_unified_tools.py::TestToolMetadata ........ 9 passed
tests/agents/tools/test_unified_tools.py::TestMemoryQueryTool ...... 1 passed
tests/agents/tools/test_unified_tools.py::TestGetContextBlockTool . 1 passed
tests/agents/tools/test_unified_tools.py::TestMemoryStoreTool ...... 1 passed
```

**Tool Capabilities**:
- `memory_query`: Hybrid search with weight normalization, streaming status updates
- `get_context_block`: Dual output formats (structured summary or text prompt)
- `memory_store`: Auto-tier selection based on content length

### W2 Summary

**Total Implementation**:
- **New Files**: 7 (runtime + tools + tests)
- **Modified Files**: 2 (memory_system.py, models.py)
- **Lines of Code**: ~1,100 (production) + ~400 (tests)
- **Test Coverage**: 47/47 tests passing (100%)

**Key Achievements**:
1. Successfully integrated all four memory tiers with lifecycle engines
2. Implemented hybrid query with configurable weighting and normalization
3. Created reusable ToolRuntime wrapper for all future agent tools
4. Established pattern for LangChain-compatible tool development
5. Comprehensive test coverage with async support

**Architectural Validation**:
- ✅ ToolRuntime pattern adopted per ADR-007
- ✅ Async-first for ASGI compatibility
- ✅ Pydantic v2 validation throughout
- ✅ Error handling returns LLM-consumable strings
- ✅ Backward compatibility maintained for gradual migration

**Next Steps (Week 3)**:
- CIAR-specific tools for score calculation and filtering
- Tier-specific tools for granular memory access
- Knowledge synthesis tool for L4 distillation
- Tool integration tests with mocked backends

---

### W1.2: Lua Scripts for Atomic Operations (P0 — CRITICAL)

**Objective**: Replace client-side WATCH with server-side Lua for atomic state transitions.

**Tasks**:
- [ ] Create `src/memory/lua/` directory
- [ ] Implement `atomic_promotion.lua` (L1→L2 with CIAR filter)
- [ ] Implement `workspace_update.lua` (version-checked merge)
- [ ] Implement `smart_append.lua` (append-only patterns)
- [ ] Create Python `LuaScriptManager` for script loading
- [ ] Write integration tests with real Redis

**Deliverables**:
```
src/memory/lua/atomic_promotion.lua
src/memory/lua/workspace_update.lua
src/memory/lua/smart_append.lua
src/memory/lua_manager.py
tests/memory/test_lua_scripts.py
```

**Acceptance Criteria**:
- [ ] Zero retry loops under concurrent load
- [ ] 50-agent concurrent write test passes
- [ ] Scripts pre-loaded via SCRIPT LOAD for performance

---

### W1.3: Redis Streams for Lifecycle Coordination (P1)

**Objective**: Replace Pub/Sub with durable Streams for lifecycle event sourcing.

**Tasks**:
- [ ] Implement `LifecycleEventStream` class
- [ ] Add consumer group management
- [ ] Implement event publishing for promotion/consolidation/distillation
- [ ] Add dead letter handling for failed events
- [ ] Write integration tests

**Deliverables**:
```
src/memory/lifecycle_stream.py
tests/memory/test_lifecycle_stream.py
```

**Acceptance Criteria**:
- [ ] Events persist even if consumer offline
- [ ] Consumer groups handle parallel workers
- [ ] Pending entry list (PEL) cleanup implemented

---

## Week 2: Memory System Enhancement

### W2.1: Enhanced UnifiedMemorySystem (P0)

**Objective**: Integrate tier classes with lifecycle engines via single facade.

**Tasks**:
- [ ] Refactor `memory_system.py` to import tier classes
- [ ] Add lifecycle engine injection via constructor
- [ ] Implement `run_promotion_cycle()` with Lua script backend
- [ ] Implement `run_consolidation_cycle()` with Streams coordination
- [ ] Implement `run_distillation_cycle()`
- [ ] Add `query_memory()` for cross-tier search
- [ ] Implement CIAR-filtered L2 retrieval (RT-04)

**Deliverables**:
```
memory_system.py (enhanced)
tests/test_memory_system.py (expanded)
```

**Key Implementation** (CIAR-filtered L2):
```python
async def get_context_block(
    self,
    session_id: str,
    min_ciar: float = 0.6,
    l2_limit: int = 10
) -> ContextBlock:
    """
    Assemble context block with CIAR filtering (RT-04).
    
    Does NOT auto-inject all L2 facts — only those above threshold.
    """
    l2_facts = await self.l2_tier.retrieve(
        session_id=session_id,
        min_ciar_score=min_ciar,
        limit=l2_limit
    )
    return ContextBlock(l2_facts=l2_facts, ...)
```

**Acceptance Criteria**:
- [ ] All tier classes accessible via unified interface
- [ ] Lifecycle engines triggered correctly
- [ ] Cross-tier query merges results properly
- [ ] CIAR filtering reduces L2 injection volume

---

### W2.2: Tool Implementation — Unified Tools (P0)

**Objective**: Create high-level memory tools for agent consumption.

**Tasks**:
- [ ] Create `src/agents/tools/` directory structure
- [ ] Implement `memory_query()` tool
- [ ] Implement `get_context_block()` tool
- [ ] Implement `memory_store()` tool with auto-routing
- [ ] Add InjectedState pattern for session context (RT-01)

**Deliverables**:
```
src/agents/__init__.py
src/agents/tools/__init__.py
src/agents/tools/unified_tools.py
tests/agents/tools/test_unified_tools.py
```

**Key Implementation** (InjectedState):
```python
from typing import Annotated
from langgraph.prebuilt import InjectedState

@tool
async def memory_query(
    query: str,
    state: Annotated[dict, InjectedState]  # Hidden from LLM
) -> dict:
    session_id = state["session_id"]  # Auto-injected
    agent_id = state["agent_id"]
    # Namespaced retrieval using injected context
```

**Acceptance Criteria**:
- [ ] Tools use LangChain `@tool` decorator
- [ ] Pydantic schemas for all tool inputs
- [ ] InjectedState hides technical IDs from LLM

---

## Week 3: CIAR Tools & Granular Access (COMPLETE ✅)

**Objective**: Implement CIAR-aware tools, tier-specific retrieval tools, and integration test infrastructure.

**Status**: ✅ Complete (Dec 28-29, 2025)  
**Bonus**: Gemini native structured output implementation

### W3.1: CIAR Feature Tools (P0 — COMPLETE ✅)

**Status**: ✅ Complete (Dec 28, 2025)  
**Files Created**:
- `src/agents/tools/ciar_tools.py` (350 lines)
- `tests/agents/tools/test_ciar_tools.py` (300 lines, 16 tests)

**Deliverables**:
- [x] `ciar_calculate()` tool with component breakdown (certainty, impact, age, recency)
- [x] `ciar_filter()` tool for batch filtering by threshold
- [x] `ciar_explain()` tool with human-readable explanations
- [x] Pydantic input schemas for all tools
- [x] Unit tests covering schemas, metadata, and functionality

**Tool Capabilities**:
- `ciar_calculate`: Returns JSON with final_score, components, promotability verdict
- `ciar_filter`: Batch filters facts with pass_rate statistics
- `ciar_explain`: Human-readable breakdown with formula explanations

**Test Results**:
```
tests/agents/tools/test_ciar_tools.py .................. 16 passed
```

---

### W3.2: Granular Tier Tools (P1 — COMPLETE ✅)

**Status**: ✅ Complete (Dec 28, 2025)  
**Files Created**:
- `src/agents/tools/tier_tools.py` (460 lines)
- `src/memory/graph_templates.py` (450 lines)
- `migrations/002_l2_tsvector_index.sql` (40 lines)

**Deliverables**:
- [x] `l2_search_facts()` tool using PostgreSQL tsvector full-text search
- [x] `l3_query_graph()` tool with template-based Cypher queries
- [x] `l3_search_episodes()` tool placeholder (vector search in Week 4)
- [x] `l4_search_knowledge()` tool wrapping Typesense search
- [x] Graph query templates (6 logistics-focused templates)
- [x] PostgreSQL tsvector migration with GIN index

**Graph Templates Implemented**:
| Template | Purpose | Parameters |
|----------|---------|------------|
| `get_container_journey` | Track container movements | `container_id` |
| `get_shipment_parties` | Find all parties in shipment | `shipment_id` |
| `find_delay_causes` | Identify delay patterns | `shipment_id` |
| `get_document_flow` | Trace document relationships | `document_id` |
| `get_related_episodes` | Find episodes by entity | `entity_id`, `entity_type` |
| `get_entity_timeline` | Temporal history of entity | `entity_id`, `limit` |

**Key Architectural Decisions**:
- **tsvector 'simple' config**: No stemming for exact SKU/container/error code matching
- **Template-based Cypher**: Prevents injection attacks, enforces temporal validity (`factValidTo IS NULL`)
- **Parameter injection**: Uses `$param` syntax for safe query execution

---

### W3.3: Synthesis Tools (P1 — COMPLETE ✅)

**Status**: ✅ Complete (Dec 28, 2025)  
**Files Created**:
- `src/agents/tools/synthesis_tools.py` (140 lines)

**Deliverables**:
- [x] `synthesize_knowledge()` tool wrapping KnowledgeSynthesizer
- [x] Conflict detection and reporting
- [x] Cache hit status tracking
- [x] Source provenance in results

**Tool Capabilities**:
- Synthesizes knowledge from L4 semantic memory
- Returns: synthesized_text, sources, conflicts, cache_hit status
- Graceful error handling for LLM failures

---

### W3.4: Integration Test Infrastructure (P0 — COMPLETE ✅)

**Status**: ✅ Complete (Dec 28, 2025)  
**Files Created/Modified**:
- `tests/integration/conftest.py` (updated with real adapter fixtures)
- `tests/integration/test_connectivity.py` (new, 6 tests)

**Deliverables**:
- [x] `verify_l2_schema()` fixture for fail-fast schema verification
- [x] 5 adapter fixtures connecting to live 3-node cluster:
  - `redis_adapter` → Node 1 (192.168.107.172:6379)
  - `postgres_adapter` → Node 2 (192.168.107.187:5432)
  - `neo4j_adapter` → Node 2 (192.168.107.187:7687)
  - `qdrant_adapter` → Node 2 (192.168.107.187:6333)
  - `typesense_adapter` → Node 2 (192.168.107.187:8108)
- [x] Surgical cleanup fixtures using `test_session_id` namespace isolation
- [x] Combined `full_cleanup` fixture for lifecycle tests
- [x] Migration 002 applied to live PostgreSQL cluster

**Connectivity Test Results**:
```
tests/integration/test_connectivity.py::test_l2_schema_verification PASSED
tests/integration/test_connectivity.py::test_redis_connectivity PASSED
tests/integration/test_connectivity.py::test_postgres_connectivity PASSED
tests/integration/test_connectivity.py::test_neo4j_connectivity PASSED
tests/integration/test_connectivity.py::test_qdrant_connectivity PASSED
tests/integration/test_connectivity.py::test_typesense_connectivity PASSED
============================== 6 passed in 0.80s ===============================
```

**Key Infrastructure Details**:
- **3-Node Research Cluster**: All 5 storage backends validated
- **Schema Verification**: Fail-fast with actionable `psql` command if migration missing
- **Namespace Isolation**: UUID-based `test_session_id` prevents test collisions

---

### W3 Summary

**Completion Date**: December 28-29, 2025  
**Status**: ✅ COMPLETE + BONUS

**Total Implementation**:
- **New Files**: 12 (8 planned + 4 bonus schemas/engines)
- **Modified Files**: 8 (3 planned + 5 bonus LLM/engine updates)
- **Lines of Code**: ~2,600 (production) + ~600 (tests)
- **Test Coverage**: All connectivity tests passing (6/6) + fact extraction validated

**Key Achievements (Planned)**:
1. Full CIAR tool suite for score manipulation and explanation
2. Tier-specific retrieval tools for L2/L3/L4
3. Template-based Cypher queries with temporal safety
4. PostgreSQL tsvector search for L2 keyword retrieval
5. Live cluster integration test infrastructure
6. Migration 002 deployed to production PostgreSQL

**Bonus Achievements (Unplanned)**:
7. **Gemini Native Structured Output** — Eliminated JSON truncation errors
   - Created `src/memory/schemas/` with native `types.Schema` definitions
   - Enhanced `GeminiProvider` with `system_instruction` + `response_schema` support
   - Refactored `FactExtractor` and `TopicSegmenter` to use structured output
   - Added model-to-provider routing in `LLMClient` (prevents Gemini→Groq misrouting)
   - Validated with real supply chain document (7 facts extracted, zero errors)
   - **Impact**: Resolves critical blocker for Phase 2B-2D lifecycle engines

**Architectural Validation**:
- ✅ tsvector 'simple' config for exact matching (no stemming)
- ✅ Template-based Cypher prevents injection attacks
- ✅ Fail-fast schema verification pattern
- ✅ Namespace isolation for safe integration testing
- ✅ All 5 storage adapters confirmed functional
- ✅ **Native structured output eliminates JSON parsing failures**
- ✅ **Model routing ensures correct provider selection**

**Documentation Updated**:
- DEVLOG.md (2025-12-29 entry)
- docs/lessons-learned.md (LL-20251229-01)
- examples/gemini_structured_output_test.md
- GEMINI.MD, AGENTS.MD, .github/copilot-instructions.md
- docs/ADR/006-free-tier-llm-strategy.md

**Next Steps (Week 4)**:
- BaseAgent interface with tool binding
- MemoryAgent implementation (UC-01)
- L3 vector search completion (`l3_search_episodes`)
- Full lifecycle integration tests (L1→L2→L3→L4)

---

## Week 4: Agent Framework

### W4.1: BaseAgent Interface (P0)

**Objective**: Create abstract agent interface with tool binding capabilities.

**Tasks**:
- [ ] Create `src/agents/base_agent.py`
- [ ] Define `AgentInput` and `AgentOutput` Pydantic models
- [ ] Implement abstract `process_turn()` method
- [ ] Implement `retrieve_context()` method
- [ ] Add `health_check()` method
- [ ] Implement tool binding via LangChain

**Deliverables**:
```
src/agents/base_agent.py
tests/agents/test_base_agent.py
```

**Acceptance Criteria**:
- [ ] Abstract class with clear contract
- [ ] Tool binding mechanism documented
- [ ] Health check includes all dependencies

---

### W4.2: MemoryAgent — UC-01 (P0)

**Objective**: Implement full hybrid memory agent using all four tiers.

**Tasks**:
- [ ] Implement `MemoryAgent` class
- [ ] Integrate all tool categories (unified + granular + CIAR)
- [ ] Implement Tool Message context injection (RT-04)
- [ ] Add background promotion trigger (async)
- [ ] Write comprehensive unit tests

**Deliverables**:
```
src/agents/memory_agent.py
tests/agents/test_memory_agent.py
```

**Key Implementation** (Tool Message Injection):
```python
async def _assemble_messages(self, input: AgentInput) -> List[BaseMessage]:
    messages = [
        SystemMessage(content=self.system_prompt),  # Cached
        *self._format_history(input.conversation_history),  # Cached
        ToolMessage(  # Dynamic - NOT cached
            content=await self._get_context_block(input.session_id),
            tool_call_id="context_injection"
        ),
        HumanMessage(content=input.current_message)  # Dynamic
    ]
    return messages
```

**Acceptance Criteria**:
- [ ] Uses all four tiers (L1-L4)
- [ ] CIAR-filtered L2 auto-injection
- [ ] Tool Message injection preserves cache
- [ ] Metadata includes tier access counts

---

### W4.3: Baseline Agents — UC-02, UC-03 (P0)

**Objective**: Implement comparison baseline agents.

**Tasks**:
- [ ] Implement `RAGAgent` (single vector store)
- [ ] Implement `FullContextAgent` (naive full history)
- [ ] Ensure identical LLM configuration across variants
- [ ] Write unit tests

**Deliverables**:
```
src/agents/rag_agent.py
src/agents/full_context_agent.py
tests/agents/test_rag_agent.py
tests/agents/test_full_context_agent.py
```

**Acceptance Criteria**:
- [ ] RAGAgent uses only Qdrant (no tiered memory)
- [ ] FullContextAgent passes entire history (no retrieval)
- [ ] Both maintain same prompt template as MemoryAgent

---

## Week 5: LangGraph Orchestration & API

### W5.1: LangGraph Orchestrator (P0)

**Objective**: Implement multi-agent state graph with LangGraph.

**Tasks**:
- [ ] Add `langgraph` to requirements.txt
- [ ] Create `src/agents/orchestrator.py`
- [ ] Implement `AgentState` TypedDict with state schema
- [ ] Build state graph with nodes: load_state → retrieve_context → agent → save_state
- [ ] Implement state reducers for message accumulation (RT-01)
- [ ] Add circuit breaker pattern for tool failures
- [ ] Write integration tests

**Deliverables**:
```
src/agents/orchestrator.py
tests/agents/test_orchestrator.py
```

**Key Implementation** (State Reducers):
```python
from typing import Annotated
import operator

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]  # Reducer: append, not overwrite
    session_id: str
    context: List[Dict[str, Any]]
    response: Optional[str]
```

**Acceptance Criteria**:
- [ ] State graph compiles without errors
- [ ] Async invoke works correctly
- [ ] Circuit breaker triggers after 3 failures
- [ ] State persists across invocations

---

### W5.2: Agent Wrapper API (P0)

**Objective**: Implement FastAPI endpoint for benchmark runner integration.

**Tasks**:
- [ ] Create `src/api/` directory structure
- [ ] Implement FastAPI app with `/run_turn` POST endpoint
- [ ] Implement `/health` GET endpoint
- [ ] Add startup/shutdown lifecycle hooks
- [ ] Implement agent_type routing (memory/rag/full_context)
- [ ] Add request/response logging
- [ ] Write API tests with TestClient

**Deliverables**:
```
src/api/__init__.py
src/api/agent_wrapper.py
tests/api/test_agent_wrapper.py
```

**Acceptance Criteria**:
- [ ] `/run_turn` accepts benchmark runner format
- [ ] `/health` reports all dependency status
- [ ] Request validation with Pydantic
- [ ] Proper error responses (4xx, 5xx)

---

## Week 6: Integration Testing & Documentation

### W6.1: End-to-End Integration Tests (P0)

**Objective**: Validate complete agent flows with real/mocked storage.

**Tasks**:
- [ ] Create `tests/integration/` directory
- [ ] Implement `test_e2e_memory_agent.py` with mocked storage
- [ ] Implement `test_e2e_real_storage.py` (optional, requires all backends)
- [ ] Test multi-turn conversation scenarios
- [ ] Test state persistence across sessions
- [ ] Test graceful degradation (tier unavailable)
- [ ] Benchmark latency for critical paths

**Deliverables**:
```
tests/integration/test_e2e_agents.py
tests/integration/test_e2e_real_storage.py
tests/integration/conftest.py
```

**Acceptance Criteria**:
- [ ] 10-turn conversation test passes
- [ ] State persists after API restart
- [ ] Graceful degradation logs correctly
- [ ] Latency within acceptable bounds

---

### W6.2: Documentation & Cleanup (P1)

**Objective**: Update documentation with Phase 3 completion details.

**Tasks**:
- [ ] Update project README.md with agent usage examples
- [ ] Update DEVLOG.md with Phase 3 completion entry
- [ ] Create `docs/agents-quickstart.md` guide
- [ ] Generate coverage report (target: ≥80%)
- [ ] Run full test suite and verify all pass
- [ ] Create ADR-007 for LangGraph integration decisions

**Deliverables**:
```
README.md (updated)
DEVLOG.md (updated)
docs/agents-quickstart.md (new)
docs/ADR/007-langgraph-integration.md (new)
```

**Acceptance Criteria**:
- [ ] README includes agent API examples
- [ ] Coverage report shows ≥80%
- [ ] All 500+ tests pass
- [ ] ADR-007 documents key decisions

---

## Success Criteria Summary

### Acceptance Gates

| Gate | Criteria | Target |
|------|----------|--------|
| **AG-01** | All three agent variants implemented | MemoryAgent, RAGAgent, FullContextAgent |
| **AG-02** | UnifiedMemorySystem integrates tiers + engines | Cross-tier query working |
| **AG-03** | `/run_turn` API operational | Integration tests pass |
| **AG-04** | Test coverage ≥80% | pytest-cov report |
| **AG-05** | LangGraph orchestrator state management | State persistence tests |
| **AG-06** | Hash Tag namespace validated | Redis Cluster tests |
| **AG-07** | Lua scripts atomic under concurrency | 50-agent stress test |

### Definition of Done

Phase 3 is complete when:
1. ✅ `src/agents/` package contains all agent implementations
2. ✅ `src/api/` package contains Agent Wrapper API
3. ✅ Hash Tag namespaces prevent CROSSSLOT errors
4. ✅ Lua scripts replace WATCH-based locking
5. ✅ Redis Streams coordinate lifecycle events
6. ✅ Tool Message injection preserves prompt cache
7. ✅ CIAR tools use Reasoning-First schemas
8. ✅ All acceptance gates pass
9. ✅ Coverage ≥80%
10. ✅ DEVLOG updated with Phase 3 completion

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LangGraph API changes | Low | Medium | Pin version in requirements.txt |
| Redis Cluster Hash Slot issues | Medium | **Critical** | W1.1 integration tests validate early |
| Gemini rate limits | Medium | Medium | Use mocks for unit tests, circuit breaker for integration |
| Lua script complexity | Low | Medium | Start with simple scripts, add complexity incrementally |
| Context window overflow | Low | Low | CIAR filtering limits injection volume |

---

## Dependencies

### New Python Packages

```txt
# requirements.txt additions
langgraph>=0.1.0
langchain-core>=0.2.0
fastapi>=0.100.0
uvicorn>=0.23.0
```

### Infrastructure Requirements

- Redis 7.0+ (for Redis Streams consumer groups)
- All Phase 1-2 storage backends operational
- Gemini API key (or alternative LLM provider)

---

## Timeline Summary

| Week | Focus | Key Deliverables |
|------|-------|------------------|
| **W1** | Foundation | Namespace + Lua + Streams |
| **W2** | Memory System | UnifiedMemorySystem + Unified Tools |
| **W3** | CIAR & Tools | CIAR Tools + Tier Tools + Synthesis |
| **W4** | Agents | BaseAgent + MemoryAgent + Baselines |
| **W5** | Orchestration | LangGraph + API |
| **W6** | Integration | E2E Tests + Documentation |

---

## References

- [Phase 3 Specification v2.0](../specs/spec-phase3-agent-integration.md)
- [Research Validation README](../research/README.md)
- [ADR-003: Four-Tier Architecture](../ADR/003-four-layers-memory.md)
- [ADR-004: CIAR Scoring Formula](../ADR/004-ciar-scoring-formula.md)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

---

**Document Owner**: Phase 3 Implementation Lead  
**Review Schedule**: Weekly checkpoint every Monday
