# Phase 2/3 Engineering Plans (version-0.9)

Consolidated Phase 2 engines, Phase 3 integration, refactoring, and mypy remediation plans.

Sources:

---

# Phase 2 Lifecycle Engines Implementation Plan

**Date**: 2025-12-27
**Status**: In Progress
**Reference Spec**: [spec-phase2-memory-tiers.md](../specs/spec-phase2-memory-tiers.md)

## Overview

This plan details the implementation steps for the **Lifecycle Engines** (Phase 2B-2D) of the MAS Memory Layer. These engines are responsible for the autonomous flow of information between memory tiers, transforming raw context into structured facts, episodes, and distilled knowledge.

The implementation follows the architecture defined in **ADR-003** and the **Phase 2 Specification**.

---

## Prerequisites

- [x] **Update Documentation**: Update `.github/copilot-instructions.md` to reflect that `LLM Client` is implemented (currently marked as missing).
- [x] **Engine Foundation**: Create `src/memory/engines/` directory.

---

## Phase 2B: Promotion Engine (L1 → L2)

**Objective**: Automate the extraction of significant facts from Active Context (L1) and promote them to Working Memory (L2).

**Spec Reference**: `spec-phase2-memory-tiers.md` > "Lifecycle Engines: Autonomous Memory Management" > "1. Promotion (L1→L2)"

### Tasks

1.  **Base Engine Interface**
    *   **File**: `src/memory/engines/base_engine.py`
    *   **Requirements**:
        *   [x] Abstract `BaseEngine` class.
        *   [x] Standard methods: `process()`, `health_check()`, `get_metrics()`.
        *   [x] Async/await pattern for non-blocking operations.

2.  **Fact Extractor**
    *   **File**: `src/memory/engines/fact_extractor.py`
    *   **Requirements**:
        *   [x] Use `LLMClient` to process raw text turns.
        *   [x] Implement structured output parsing (JSON/Pydantic) to create `Fact` objects.
        *   [x] **Resilience**: Implement Circuit Breaker pattern (fallback to rule-based extraction on LLM failure).

3.  **Promotion Engine Logic**
    *   **File**: `src/memory/engines/promotion_engine.py`
    *   **Requirements**:
        *   [x] Poll `ActiveContextTier` for recent turns (batch processing).
        *   [x] Invoke `FactExtractor`.
        *   [x] Score facts using existing `CIARScorer`.
        *   [x] Filter based on `promotion_threshold` (default 0.6).
        *   [x] Store qualifying facts in `WorkingMemoryTier`.

---

## Phase 2C: Consolidation Engine (L2 → L3)

**Objective**: Cluster related facts from Working Memory (L2) into coherent Episodes and store them in Episodic Memory (L3).

**Spec Reference**: `spec-phase2-memory-tiers.md` > "Lifecycle Engines: Autonomous Memory Management" > "2. Consolidation (L2→L3)"

### Tasks

1.  **Episode Clustering**
    *   **Logic**: Group facts by time windows (e.g., 24h) and semantic similarity.
    *   **File**: `src/memory/engines/consolidation_engine.py` (or helper module).
    *   **Status**: [x] Complete

2.  **Consolidation Engine Logic**
    *   **File**: `src/memory/engines/consolidation_engine.py`
    *   **Requirements**:
        *   [x] Retrieve facts from `WorkingMemoryTier`.
        *   [x] Use `LLMClient` to generate episode summaries and narratives.
        *   [x] **Dual-Write**: Store `Episode` objects in `EpisodicMemoryTier` (handles both Qdrant and Neo4j storage).
        *   [x] **Resilience**: Handle partial failures (e.g., Vector store success but Graph store failure).

---

## Phase 2D: Distillation Engine (L3 → L4)

**Objective**: Create domain-specific knowledge documents from episodes and provide query-time synthesis to preserve agent context windows.

**Spec Reference**: `spec-phase2-memory-tiers.md` > "Lifecycle Engines: Autonomous Memory Management" > "3. Distillation (L3→L4)"

**Architecture Decision**: Query-time synthesis rather than background processing to optimize agent context usage, not database size.

### Tasks

1.  **Domain Configuration**
    *   **File**: `config/domains/container_logistics.yaml`
    *   **Requirements**:
        *   [x] Define metadata schema (terminal_id, port_code, shipping_line, container_type, trade_lane, region, customer_id, vessel_id).
        *   [x] Specify matching rules for metadata-first filtering.
        *   [x] Document domain-specific knowledge types.

2.  **Distillation Engine Logic**
    *   **File**: `src/memory/engines/distillation_engine.py`
    *   **Requirements**:
        *   [x] Trigger on episode count threshold (default 5 episodes).
        *   [x] Generate all knowledge types (summaries, insights, patterns, recommendations, rules).
        *   [x] Extract rich metadata from episodes (domain-specific fields).
        *   [x] Store in `SemanticMemoryTier` (Typesense) with full metadata.
        *   [x] **No Deduplication**: Allow multiple knowledge documents for different contexts.
        *   [x] **Provenance**: Link each document to source Episode IDs.

3.  **Knowledge Synthesizer**
    *   **File**: `src/memory/engines/knowledge_synthesizer.py`
    *   **Requirements**:
        *   [x] **Metadata-First Filtering**: Filter L4 documents by domain metadata before similarity comparison.
        *   [x] **Cosine Similarity**: Compute similarity within filtered groups (threshold 0.85).
        *   [x] **Query-Context Synthesis**: Use LLM to combine relevant knowledge with agent query context.
        *   [x] **Conflict Transparency**: Surface conflicting information to agent rather than hiding it.
        *   [x] **Short-TTL Caching**: Cache synthesized results for 1 hour to reduce LLM calls.
        *   [x] **Performance**: Target <200ms for metadata filtering + similarity search.

4.  **Test Fixture Alignment (Pydantic V2 Compatibility)**
    *   **Context**: Data models recently updated to Pydantic V2 requirements
    *   **Files**: `tests/memory/test_distillation_engine.py`, `tests/memory/test_knowledge_synthesizer.py`
    *   **Requirements**:
        *   [x] **Episode Fixtures**: Update `sample_episodes` fixture to match Pydantic V2 Episode model schema
            *   Replace `start_time`/`end_time` with `time_window_start`/`time_window_end`
            *   Convert `entities` from List[str] to List[Dict] with proper entity structure
            *   Add required fields: `fact_valid_from`, `source_observation_timestamp`
        *   [x] **KnowledgeDocument Fixtures**: Already aligned with Pydantic V2 schema
            *   Uses `knowledge_id` (not `doc_id`)
            *   Uses `source_episode_ids` (not `source_episodes`)
            *   Stores `key_points` in metadata dict
        *   [x] **MetricsCollector API**: Update metrics timing calls
            *   Added `start_timer` and `stop_timer` to `MetricsCollector` to support manual control
            *   Updated `OperationTimer` to support manual start/stop
            *   Fixed `KnowledgeSynthesizer` to await async `stop_timer` calls
        *   [x] **Mock Provider**: Ensure `BaseProvider` mocks include required `.name` attribute
        *   [x] **Run Full Test Suite**: Verify all 26 Phase 2D tests pass (12 distillation + 14 synthesizer)

---

## Implementation Status

### Phase 2B: Promotion Engine ✅ COMPLETE
- BaseEngine, FactExtractor, PromotionEngine implemented
- 18 tests passing (100%)
- Integration with CIAR scoring verified

### Phase 2C: Consolidation Engine ✅ COMPLETE  
- ConsolidationEngine with time-based clustering implemented
- GeminiProvider embedding support (gemini-embedding-001, 768 dimensions)
- 6 test documents created (2 .md, 2 .txt, 2 .html, all 1000+ words)
- Dual-write to Qdrant (vector) + Neo4j (graph) verified

### Phase 2D: Distillation Engine ✅ COMPLETE
- ✅ DistillationEngine implementation (450 lines)
- ✅ KnowledgeSynthesizer implementation (500 lines)
- ✅ Container logistics domain configuration (172 lines YAML)
- ✅ 26 comprehensive tests written (12 distillation + 14 synthesizer)
- ✅ Query-time synthesis architecture
- ✅ Metadata-first filtering logic
- ✅ Conflict detection and transparency
- ✅ 1-hour TTL caching
- ✅ Test fixture alignment with Pydantic V2 models
- ✅ MetricsCollector API corrections
- **Current Test Status**: 26/26 passing (100%)

---

## Testing Strategy

For each engine:
1.  **Unit Tests**: Mock `LLMClient` and Storage Tiers to verify logic flow and error handling.
2.  **Integration Tests**: Run with real (test) database instances to verify data persistence.
3.  **Resilience Tests**: Simulate LLM timeouts and storage failures to verify Circuit Breaker and Fallback mechanisms.

### Pydantic V2 Compatibility Notes

The project recently migrated to Pydantic V2 (v2.8.2), which introduced breaking changes:
- Field aliases and serialization behavior changed
- Stricter type validation (e.g., List[str] vs List[Dict])
- DateTime handling requires explicit timezone awareness
- Validator syntax changed from `@validator` to `@field_validator`

**Impact on Phase 2D**: Test fixtures created before full Pydantic V2 alignment need updates to match model schemas. The core engine logic is unaffected as it uses Pydantic models correctly.

**Resolution Path**: Update test fixtures to use current model field names and types as defined in `src/memory/models.py`.

---


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
- `docs/benchmark_sequence_diagrams.md` (System Design for L1→L2 flow)
- `docs/benchmark_data_dictionary.md` (Design Document for Promotion Engine)

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

---


# Phase 2E: Generic BaseTier Refactoring — Implementation Guide

**Version:** 2.0 (Updated 2026-02-04)  
**Status:** In Progress (~85% Complete)  
**Estimated Remaining Effort:** 4-8 hours  

---

## Executive Summary

This document guides the completion of Phase 2E: converting the memory tier system to use
fully type-safe generic interfaces. The refactoring ensures **compile-time type safety**
via mypy, **API symmetry** between `store()` and `retrieve()`, and alignment with the
**"Reasoning-First" schema pattern** from our research.

### Current State (as of 2026-02-04)

| Component | Status | Notes |
|-----------|--------|-------|
| `BaseTier[TModel]` generic definition | ✅ Complete | Uses Python 3.12+ `class BaseTier[TModel: BaseModel]` |
| `TurnData` model for L1 | ✅ Complete | Exists in `models.py` with all fields |
| All tiers use generics | ✅ Complete | L1=`TurnData`, L2=`Fact`, L3=`Episode`, L4=`KnowledgeDocument` |
| `retrieve()` returns typed `T` | ✅ Complete | All tiers return model instances |
| `query()` returns `list[T]` | ✅ Complete | All tiers return typed lists |
| `store()` accepts `TModel` | ⚠️ **INCOMPLETE** | Still declares `dict[str, Any]` |
| Engine callers updated | ⚠️ **INCOMPLETE** | Engines call `.model_dump()` before storing |
| Test type assertions | ⚠️ **INCOMPLETE** | Need `isinstance()` checks |

### Remaining Work

1. **Update `store()` signature** to accept `TModel | dict[str, Any]` with deprecation
2. **Migrate engine callers** to pass models directly instead of `.model_dump()`
3. **Add type safety assertions** to tests
4. **Handle L3 special case** with `EpisodeStoreInput` model
5. **Run mypy strict checks** and resolve all errors

---

## Research Foundation

This plan is based on two research reports:

- [`refactoring_memory_tiers_research_analysis.md`](../research/refactoring_memory_tiers_research_analysis.md)
- [`refactoring_memory_tiers_2_type_safe.md`](../research/refactoring_memory_tiers_2_type_safe.md)

### Key Research Findings

| Finding | Recommendation | Source |
|---------|---------------|--------|
| "Stringly typed" bottleneck | Eliminate `dict[str, Any]` at tier boundaries | Section 1.3 |
| Silent failures from dict keys | Use Pydantic models for compile-time checks | Section 1.3 |
| Generic signature | `store(data: T) -> str` and `retrieve(str) -> T` | Section 3.1 |
| L1 model gap | Create `TurnData(BaseModel)` | Section 5.1 |
| Rollout order | Bottom-up: L4 → L3 → L2 → L1 | Section 5.2 |
| Performance | Pydantic v2 validation <0.1ms; negligible | Table 2 |

---

## Implementation Phases

### Phase 2E.1: Update `store()` Signature ⬅️ **START HERE**

**Goal:** Change `store()` to accept typed models while maintaining backward compatibility.

#### Step 1: Update `BaseTier.store()` Abstract Method

**File:** `src/memory/tiers/base_tier.py`

**Current (line ~105):**
```python
@abstractmethod
async def store(self, data: dict[str, Any]) -> str:
```

**Target:**
```python
@abstractmethod
async def store(self, data: TModel | dict[str, Any]) -> str:
    """
    Store data in this tier.

    Args:
        data: Pydantic model instance or dict (deprecated).
            Passing dict is deprecated and will emit a warning.
            Use the tier's model type directly:
            - L1: TurnData
            - L2: Fact
            - L3: Episode (or EpisodeStoreInput for full payload)
            - L4: KnowledgeDocument

    Returns:
        Unique identifier for stored data

    Raises:
        TierOperationError: If storage operation fails
        ValidationError: If dict data fails model validation
    """
    pass
```

**Mypy Considerations:**
- `TModel` is a type parameter, so `TModel | dict[str, Any]` works correctly
- Each concrete tier will have specific union: `Fact | dict[str, Any]`, etc.
- Use `isinstance(data, dict)` for runtime dispatch

#### Step 2: Update Each Tier's `store()` Implementation

Apply this pattern to all 4 tiers:

```python
import warnings
from pydantic import ValidationError

async def store(self, data: TModel | dict[str, Any]) -> str:
    """Store data with model validation."""
    # Convert dict to model with deprecation warning
    if isinstance(data, dict):
        warnings.warn(
            f"Passing dict to {self.__class__.__name__}.store() is deprecated. "
            f"Use {TModel.__name__} model directly.",
            DeprecationWarning,
            stacklevel=2
        )
        try:
            data = TModel.model_validate(data)
        except ValidationError as e:
            raise TierOperationError(f"Data validation failed: {e}") from e
    
    # Now data is guaranteed to be TModel
    # ... rest of implementation using data.field_name ...
```

**Files to Update:**
1. `src/memory/tiers/semantic_memory_tier.py` (line ~50) — **Start here (lowest risk)**
2. `src/memory/tiers/episodic_memory_tier.py` (line ~74)
3. `src/memory/tiers/working_memory_tier.py` (line ~127)
4. `src/memory/tiers/active_context_tier.py` (line ~113) — **Do last (performance-critical)**

#### Step 3: Create `EpisodeStoreInput` Model for L3

L3's `store()` currently accepts a complex dict with episode + embedding + entities.
Create a dedicated input model:

**File:** `src/memory/models.py`

```python
class EpisodeStoreInput(BaseModel):
    """
    Input model for L3 EpisodicMemoryTier.store() operation.
    
    Encapsulates the Episode model plus vector embedding and entity data
    required for dual-index storage (Qdrant + Neo4j).
    """
    episode: Episode
    embedding: list[float] = Field(..., min_length=1)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    
    @field_validator("embedding")
    @classmethod
    def validate_embedding_dimension(cls, v: list[float]) -> list[float]:
        """Ensure embedding has reasonable dimensions."""
        if len(v) < 64 or len(v) > 4096:
            raise ValueError(f"Embedding dimension {len(v)} outside valid range [64, 4096]")
        return v
```

Then update L3 tier: `class EpisodicMemoryTier(BaseTier[Episode])` but `store()` accepts
`EpisodeStoreInput | dict[str, Any]`.

**Note:** This is a deviation from pure generic symmetry, documented as intentional for
the dual-index architecture. The `retrieve()` returns `Episode`, not `EpisodeStoreInput`.

---

### Phase 2E.2: Migrate Engine Callers

**Goal:** Update engines to pass models directly instead of calling `.model_dump()`.

#### Current Pattern (to be deprecated):
```python
# promotion_engine.py line ~254
await self.l2.store(fact.model_dump())
```

#### Target Pattern:
```python
# Pass model directly - no .model_dump() needed
await self.l2.store(fact)
```

**Files to Update:**

| File | Line | Current | Target |
|------|------|---------|--------|
| `promotion_engine.py` | ~254 | `self.l2.store(fact.model_dump())` | `self.l2.store(fact)` |
| `promotion_engine.py` | ~284 | `self.l2.store(fallback_fact.model_dump())` | `self.l2.store(fallback_fact)` |
| `consolidation_engine.py` | ~284 | `self.l3.store({...})` | `self.l3.store(EpisodeStoreInput(...))` |
| `consolidation_engine.py` | ~361 | `self.l3.store({...})` | `self.l3.store(EpisodeStoreInput(...))` |
| `distillation_engine.py` | ~204 | `self.semantic_tier.store(doc)` | ✅ Already correct |

---

### Phase 2E.3: Update Agent/Tool Callers

**Goal:** Ensure all tool implementations use models.

**Files to Review:**

| File | Current Pattern | Action |
|------|-----------------|--------|
| `src/agents/tools/unified_tools.py` | `l1_tier.store(session_id, turn_data)` | Verify `turn_data` is `TurnData` |
| `src/evaluation/agent_wrapper.py` | `l1_tier.store(...)` | Update to pass `TurnData` model |

---

### Phase 2E.4: Update Tests

**Goal:** Add explicit type assertions and update dict-passing tests.

#### Pattern for Type Safety Assertions:

```python
import pytest
from src.memory.models import Fact, TurnData, Episode, KnowledgeDocument

async def test_retrieve_returns_typed_model(tier):
    """Verify retrieve() returns correct model type."""
    stored_id = await tier.store(valid_model_instance)
    result = await tier.retrieve(stored_id)
    
    assert result is not None
    assert isinstance(result, ExpectedModelType)  # <-- Add this assertion
    assert result.field_name == expected_value
```

#### Test Files to Update:

| File | Updates Needed |
|------|---------------|
| `tests/memory/test_active_context_tier.py` | Add `isinstance(result, TurnData)` checks |
| `tests/memory/test_working_memory_tier.py` | Add `isinstance(result, Fact)` checks |
| `tests/memory/test_episodic_memory_tier.py` | Add `isinstance(result, Episode)` checks |
| `tests/memory/test_semantic_memory_tier.py` | Add `isinstance(result, KnowledgeDocument)` checks |
| `tests/memory/engines/test_promotion_engine.py` | Update to pass `Fact` models |
| `tests/memory/engines/test_consolidation_engine.py` | Update to pass `EpisodeStoreInput` |

#### Handling Deprecation Warnings in Tests:

For tests that intentionally pass dicts (to verify backward compatibility):

```python
import warnings

def test_store_accepts_dict_with_deprecation_warning(tier):
    """Verify dict input works but emits deprecation warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        await tier.store({"field": "value", ...})
        
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message).lower()
```

---

### Phase 2E.5: Mypy Strict Compliance

**Goal:** Ensure all changes pass `mypy --strict` checks.

#### Critical Mypy Patterns for This Refactoring:

1. **Generic Type Parameter Access:**
   ```python
   # Problem: Can't access TModel.__name__ in generic class
   # Solution: Use self.__class__.__orig_bases__ or pass model class explicitly
   
   class BaseTier[TModel: BaseModel](ABC):
       model_class: type[TModel]  # Store explicit reference
       
       def __init__(self, model_class: type[TModel], ...):
           self.model_class = model_class
   ```

2. **Union Type Narrowing:**
   ```python
   async def store(self, data: TModel | dict[str, Any]) -> str:
       if isinstance(data, dict):
           # mypy knows: data is dict[str, Any] here
           data = self.model_class.model_validate(data)
       # mypy knows: data is TModel here
       return data.some_field  # OK
   ```

3. **Avoiding `Any` Leakage:**
   ```python
   # Bad: dict[str, Any] leaks Any into operations
   content = data["content"]  # type: Any
   
   # Good: Model access is typed
   content = data.content  # type: str
   ```

4. **Pydantic ValidationError Import:**
   ```python
   from pydantic import ValidationError  # Not from pydantic.error_wrappers
   ```

#### Mypy Commands to Validate:

```bash
# Check specific tier files
/home/max/code/mas-memory-layer/.venv/bin/python -m mypy \
    src/memory/tiers/base_tier.py \
    src/memory/tiers/semantic_memory_tier.py \
    --strict

# Check all memory module
/home/max/code/mas-memory-layer/.venv/bin/python -m mypy \
    src/memory/ \
    --strict
```

---

## Rollout Order (Bottom-Up)

Execute phases in this order to minimize risk:

| Order | Tier | Risk Level | Rationale |
|-------|------|------------|-----------|
| 1 | L4 SemanticMemoryTier | 🟢 Low | Lowest volume, simplest structure |
| 2 | L2 WorkingMemoryTier | 🟢 Low | Already returns `Fact` models |
| 3 | L3 EpisodicMemoryTier | 🟡 Medium | Dual-index complexity; needs `EpisodeStoreInput` |
| 4 | L1 ActiveContextTier | 🟡 Medium | Performance-critical hot path |
| 5 | Engines | 🟢 Low | Mechanical updates after tiers done |
| 6 | Tests | 🟢 Low | Incremental with each tier |

---

## Verification Checklist

After completing each phase, verify:

- [ ] `mypy --strict` passes for modified files
- [ ] All existing tests pass: `pytest tests/ -v`
- [ ] Deprecation warnings emit correctly for dict input
- [ ] `isinstance()` assertions added to key tests
- [ ] No `Any` type leakage in public method signatures

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| L1 performance regression | Low | High | 500ms SLA acceptable; `model_construct()` if needed |
| L3 dual-index breakage | Medium | High | Careful review; preserve existing dict→model logic |
| Test churn | High | Low | Automate with search-replace patterns |
| Mypy generic edge cases | Medium | Medium | Reference Pydantic v2 mypy plugin docs |

---

## Definition of Done

Phase 2E is complete when:

1. ✅ All tier `store()` methods accept `TModel | dict[str, Any]`
2. ✅ Deprecation warnings emit for dict input
3. ✅ All engines pass models directly (no `.model_dump()`)
4. ✅ Tests include `isinstance()` type assertions
5. ✅ `mypy --strict` passes for entire `src/memory/` module
6. ✅ All 574+ tests pass
7. ✅ DEVLOG.md updated with completion entry

---

## Appendix: File Inventory

### Files Requiring Modification

| File | Changes |
|------|---------|
| `src/memory/tiers/base_tier.py` | Update `store()` signature and docstring |
| `src/memory/tiers/active_context_tier.py` | Update `store()` implementation |
| `src/memory/tiers/working_memory_tier.py` | Update `store()` implementation |
| `src/memory/tiers/episodic_memory_tier.py` | Update `store()`, handle `EpisodeStoreInput` |
| `src/memory/tiers/semantic_memory_tier.py` | Update `store()` implementation |
| `src/memory/models.py` | Add `EpisodeStoreInput` model |
| `src/memory/engines/promotion_engine.py` | Remove `.model_dump()` calls |
| `src/memory/engines/consolidation_engine.py` | Use `EpisodeStoreInput` |
| `tests/memory/test_*.py` | Add type assertions |

### Files Requiring Review Only

| File | Reason |
|------|--------|
| `src/agents/tools/unified_tools.py` | Verify model usage |
| `src/evaluation/agent_wrapper.py` | Verify model usage |
| `.github/instructions/source.instructions.md` | Update `store()` example |

---

## References

- [ADR-003: Four-Layer Memory Architecture](../ADR/003-four-layers-memory.md)
- [Research: Type-Safe Memory Tiers](../research/refactoring_memory_tiers_2_type_safe.md)
- [Pydantic v2 Mypy Plugin](https://docs.pydantic.dev/latest/integrations/mypy/)
- [Python 3.12 Generic Syntax (PEP 695)](https://peps.python.org/pep-0695/)

---


# Mypy Type Error Remediation Plan

**Date:** 2026-02-04  
**Status:** Completed  
**Initial Errors:** 119 across 13 files  
**Current Errors:** 0 (all resolved)
**Estimated Remaining Effort:** 0 hours  

## Progress Summary

### Completed Fixes (Phase 1)
| Category | Files Fixed | Errors Resolved |
|----------|-------------|-----------------|
| Dict Variance (Mapping) | `base_tier.py` | 4 |
| JSONEncodeError typo | `redis_adapter.py` | 1 |
| Unused type:ignore | `postgres_adapter.py` | 5 |
| Engine Stats Typing | `promotion_engine.py`, `consolidation_engine.py` | 12 |
| Redis Proxy Methods | `redis_adapter.py` | 5 |
| **Total Phase 1** | **5 files** | **~47 errors** |

### Remaining Issues (Phase 2)
1.  **Missing Return Statements** - 21 errors (Adapter abstract methods or loose typing)
2.  **Unused Type Ignores** - 3 errors (Config fix resolved these)

## Implementation Strategy (Option A)

The remediation will **extend adapter APIs** to match existing tier usage. This avoids large-scale tier refactoring while preserving the current adapter query dictionary pattern. New adapter methods will be added as explicit, typed wrappers where tiers currently depend on non-existent signatures.

## Batch Plan and Progress Tracking

### Batch Overview

| Batch | Scope | Primary Files | Status |
|-------|-------|---------------|--------|
| 1 | Postgres adapter methods | `src/storage/postgres_adapter.py` | Complete |
| 2 | Typesense adapter methods | `src/storage/typesense_adapter.py` | Complete |
| 3 | Qdrant adapter signature enhancements | `src/storage/qdrant_adapter.py` | Complete |
| 4 | Redis/Neo4j type fixes | `src/storage/redis_adapter.py`, `src/storage/neo4j_adapter.py` | Complete |
| 5 | Tier alignment to new adapters | `src/memory/tiers/*` | Complete |
| 6 | Engine and model typing fixes | `src/memory/engines/*`, `src/memory/models.py`, `src/memory/ciar_scorer.py` | Complete |
| 7 | Per-module mypy override | `pyproject.toml` | Revised & Verified |
| 8 | Final Cleanup & Config Hardening | Adapters & Engines | Pending |

### Batch 1: Postgres Adapter Methods
**Goal:** Implement `execute()`, `update()`, and `delete_by_filters()` (or equivalent) to match tier usage; add `order_by` support to `query()`.

**Checklist:**
- [x] Add `execute(sql: str, *params: Any) -> list[dict[str, Any]]`
- [x] Add `update(table: str, filters: dict[str, Any], data: dict[str, Any]) -> bool`
- [x] Add `delete_by_filters(table: str, filters: dict[str, Any]) -> bool`
- [x] Extend `query()` with `order_by: str | None`
- [x] Fix tuple assignment type mismatch (line ~569)
- [x] Commit: `feat(storage): add postgres adapter CRUD methods`

### Batch 2: Typesense Adapter Methods
**Goal:** Implement document-level wrappers and a keyword-args search overload to match tier usage.

**Checklist:**
- [x] Add `get_document(collection_name: str, document_id: str) -> dict[str, Any] | None`
- [x] Add `update_document(collection_name: str, document_id: str, document: dict[str, Any]) -> bool`
- [x] Add `delete_document(collection_name: str, document_id: str) -> bool`
- [x] Add keyword-args `search()` overload returning raw response with `hits`
- [x] Fix return typing at lines ~180, ~207, ~209
- [x] Commit: `feat(storage): add typesense adapter document methods`

### Batch 3: Qdrant Adapter Signature Enhancements
**Goal:** Accept both dict-style and keyword-args search/delete calls, with correct filter typing.

**Checklist:**
- [x] Update `search()` to accept kwargs and map to dict query
- [x] Update `delete()` to accept `collection_name` and `point_ids`
- [x] Fix filter union typing at lines ~527-529, ~563
- [x] Fix results list typing at lines ~682-687
- [x] Commit: `feat(storage): enhance qdrant adapter search/delete signatures`

### Batch 4: Redis and Neo4j Type Fixes
**Goal:** Resolve awaitable union types and optional attribute access patterns.

**Checklist:**
- [x] Add explicit casts on Redis await results (e.g., `int(await ...)`, `bool(...)`)
- [x] Ensure `self.client` and `self.driver` null guards before access
- [x] Commit: `fix(storage): redis/neo4j type annotations`

### Batch 5: Tier Alignment
**Goal:** Align tier calls to new adapter methods without altering domain logic.

**Checklist:**
- [x] Update `working_memory_tier.py` to use new Postgres adapter methods
- [x] Update `semantic_memory_tier.py` to use new Typesense adapter methods
- [x] Update `episodic_memory_tier.py` to use updated Qdrant adapter methods
- [x] Update `active_context_tier.py` to use Postgres delete wrapper
- [x] Commit: `fix(memory): align tier calls with adapter methods`

### Batch 6: Engines and Models
**Goal:** Correct typing for LLM responses, optional tier access, and remove stale ignores.

**Checklist:**
- [x] Add explicit `llm_client` type annotations
- [x] Add null guards for optional tier attributes
- [x] Fix `LLMResponse` usage (use `.content` or equivalent)
- [x] Fix `models.py` validator return type
- [x] Remove unused `# type: ignore` comments
- [x] Commit: `fix(memory): engine and model type annotations`

### Batch 7: Per-Module Mypy Override
**Goal:** Resolve `AssertionError: Cannot find module for google` via per-module override.

**Checklist:**
- [x] Add `[[tool.mypy.overrides]]` for `module = "google.*"` with `ignore_errors = true`
- [x] Add `namespace_packages = true` and `explicit_package_bases = true` to `[tool.mypy]`
- [x] Add manual cache clearing step to workflows
- [x] Commit: `chore: harden mypy config for namespace packages`

### Batch 8: Final Cleanup & Config Hardening
**Goal:** Fix missing return statements in adapters and remove now-redundant type ignores.

**Checklist:**
- [x] Fix `Missing return statement` in `RedisAdapter` (Added unreachable assertions)
- [x] Fix `Missing return statement` in `Neo4jAdapter` (Added unreachable assertions)
- [x] Fix `Missing return statement` in `TypesenseAdapter` (Added unreachable assertions)
- [x] Fix `Missing return statement` in `QdrantAdapter` (Added unreachable assertions)
- [x] Remove unused `type: ignore` in `ciar_scorer.py`
- [x] Remove unused `type: ignore` in `knowledge_synthesizer.py`
- [x] Remove unused `type: ignore` in `distillation_engine.py`

---

## Error Categorization

### Category 1: Redis Async Return Type Ambiguity (25 errors)
**Files:** `src/storage/redis_adapter.py`  
**Root Cause:** Redis async client returns `Awaitable[T] | T` union types that mypy cannot narrow without explicit handling.

**Error Patterns:**
- `[misc]` Incompatible types in "await" (actual type "Awaitable[int] | int", expected type "Awaitable[Any]")
- `[no-any-return]` Returning Any from function declared to return "bool"
- `[union-attr]` Item "None" of "Redis | None" has no attribute "lrange"

**Fix Strategy:**
1. Add explicit null checks before accessing `self.client` methods
2. Use `cast()` or explicit type narrowing for await results
3. Wrap return values: `return bool(result)` instead of raw `return result`

**Example Fix:**
```python
# Before (error: Returning Any from function declared to return "bool")
return await self.client.exists(key)

# After (explicit cast)
result = await self.client.exists(key)
return bool(result)
```

---

### Category 2: BaseTier Return Type Override Mismatch (8 errors)
**Files:** `active_context_tier.py`, `working_memory_tier.py`, `episodic_memory_tier.py`, `semantic_memory_tier.py`  
**Root Cause:** Tier implementations return domain models (`Fact`, `Episode`, `KnowledgeDocument`) instead of `dict[str, Any]` as declared in `BaseTier`.

**Error Pattern:**
- `[override]` Return type "Coroutine[Any, Any, Fact | None]" of "retrieve" incompatible with return type "Coroutine[Any, Any, dict[str, Any] | None]" in supertype

**Fix Strategy:**
Refactor `BaseTier` to use generics:
```python
from typing import TypeVar, Generic

T = TypeVar("T", bound=dict[str, Any])

class BaseTier(ABC, Generic[T]):
    @abstractmethod
    async def retrieve(self, identifier: str) -> T | None:
        pass
```

Or, keep dict returns and have tiers call `.model_dump()` internally:
```python
async def retrieve(self, identifier: str) -> dict[str, Any] | None:
    fact = await self._retrieve_fact(identifier)
    return fact.model_dump() if fact else None
```

**Decision:** Option 2 (dict returns) maintains API stability. Each tier should convert domain objects to dicts at the boundary.

---

### Category 3: Adapter Method Signature Mismatch (18 errors)
**Files:** `semantic_memory_tier.py`, `episodic_memory_tier.py`, `working_memory_tier.py`  
**Root Cause:** Tier code calls adapter methods with incorrect signatures. Adapters use `query: dict[str, Any]` pattern but tiers call with kwargs like `collection_name=`, `query_by=`, `limit=`.

**Error Patterns:**
- `[call-arg]` Unexpected keyword argument "collection_name" for "search" of "QdrantAdapter"
- `[call-arg]` Unexpected keyword argument "filters" for "delete" of "PostgresAdapter"
- `[arg-type]` Argument "query" to "search" has incompatible type "str"; expected "dict[str, Any]"

**Fix Strategy:**
Align tier calls with adapter signatures:
```python
# Before (error: unexpected keyword args)
await self.qdrant.search(
    collection_name=self.collection_name,
    query_vector=embedding,
    limit=limit,
    filter_dict=filters,
)

# After (use dict query structure)
query = {
    "collection_name": self.collection_name,
    "query_vector": embedding,
    "limit": limit,
    "filter_dict": filters,
}
await self.qdrant.search(query)
```

**Alternative:** Extend adapter signatures to accept both patterns with overloaded methods.

---

### Category 4: Missing Adapter Methods (8 errors)
**Files:** `semantic_memory_tier.py`, `working_memory_tier.py`  
**Root Cause:** Tier code calls adapter methods that don't exist.

**Error Pattern:**
- `[attr-defined]` "TypesenseAdapter" has no attribute "get_document"
- `[attr-defined]` "TypesenseAdapter" has no attribute "update_document"
- `[attr-defined]` "PostgresAdapter" has no attribute "execute"
- `[attr-defined]` "PostgresAdapter" has no attribute "update"

**Fix Strategy:**
1. Add missing methods to adapters, OR
2. Replace with existing adapter API calls

**Decision:** Add wrapper methods to adapters for domain-specific operations. This keeps tier code clean while maintaining adapter encapsulation.

---

### Category 5: Dict Variance Issues (4 errors)
**Files:** `working_memory_tier.py`, `semantic_memory_tier.py`  
**Root Cause:** `dict` is invariant in value type, but code passes `dict[str, PostgresAdapter]` where `dict[str, StorageAdapter]` expected.

**Error Pattern:**
- `[arg-type]` Argument 1 to "__init__" of "BaseTier" has incompatible type "dict[str, PostgresAdapter]"; expected "dict[str, StorageAdapter]"
- Note: "dict" is invariant -- see mypy docs

**Fix Strategy:**
Use `Mapping` (covariant) instead of `dict` in BaseTier signature:
```python
from collections.abc import Mapping

class BaseTier(ABC):
    def __init__(
        self,
        storage_adapters: Mapping[str, StorageAdapter],  # Changed from dict
        ...
    ):
```

---

### Category 6: Qdrant Filter Type Mismatch (7 errors)
**Files:** `src/storage/qdrant_adapter.py`  
**Root Cause:** Building `Filter` with `list[FieldCondition]` but Qdrant SDK expects broader union type.

**Error Pattern:**
- `[arg-type]` Argument "must" to "Filter" has incompatible type "list[FieldCondition] | None"; expected "list[FieldCondition | IsEmptyCondition | ...] | None"

**Fix Strategy:**
Annotate filter lists with the correct union type:
```python
from qdrant_client.http.models import FieldCondition, IsEmptyCondition, IsNullCondition, HasIdCondition, NestedCondition, Filter

FilterConditionType = FieldCondition | IsEmptyCondition | IsNullCondition | HasIdCondition | NestedCondition | Filter

must_conditions: list[FilterConditionType] | None = [...]
```

---

### Category 7: Engine Counter Type Issues (12 errors)
**Files:** `promotion_engine.py`, `consolidation_engine.py`  
**Root Cause:** Stats dict values are `object` type, not `int`. Arithmetic operations fail.

**Error Pattern:**
- `[operator]` Unsupported operand types for + ("object" and "int")

**Fix Strategy:**
Add explicit type annotations for stats dicts:
```python
stats: dict[str, int | str] = {
    "turns_retrieved": 0,
    "segments_created": 0,
    ...
}
```

---

### Category 8: LLM Client Type Issues (8 errors)
**Files:** `knowledge_synthesizer.py`, `distillation_engine.py`  
**Root Cause:** `llm_client` attribute type cannot be determined; `LLMResponse` access patterns incorrect.

**Error Patterns:**
- `[has-type]` Cannot determine type of "llm_client"
- `[attr-defined]` "LLMResponse" has no attribute "strip"
- `[no-any-return]` Returning Any from function

**Fix Strategy:**
1. Add explicit type annotation for `llm_client` attribute
2. Access `.content` or correct attribute on `LLMResponse`

---

### Category 9: Null Safety Issues (12 errors)
**Files:** `distillation_engine.py`, `episodic_memory_tier.py`, `neo4j_adapter.py`  
**Root Cause:** Accessing methods on `T | None` without null checks.

**Error Patterns:**
- `[union-attr]` Item "None" of "EpisodicMemoryTier | None" has no attribute "query"
- `[union-attr]` Item "None" of "AsyncDriver | None" has no attribute "session"

**Fix Strategy:**
Add null guards:
```python
if self.l3 is not None:
    await self.l3.query(...)
```

---

### Category 10: Miscellaneous (7 errors)
- Unused `type: ignore` comments in `postgres_adapter.py`
- `yaml` import-untyped errors
- Tuple assignment type mismatch
- `json.JSONEncodeError` typo (should be `JSONDecodeError`)

---

## Implementation Order

| Priority | Category | Files | Est. Time | Risk |
|----------|----------|-------|-----------|------|
| 1 | Cat 5: Dict Variance | `base_tier.py` | 15 min | Low |
| 2 | Cat 7: Counter Types | `promotion_engine.py`, `consolidation_engine.py` | 30 min | Low |
| 3 | Cat 1: Redis Async | `redis_adapter.py` | 45 min | Medium |
| 4 | Cat 9: Null Safety | Multiple | 30 min | Low |
| 5 | Cat 10: Misc | Multiple | 20 min | Low |
| 6 | Cat 6: Qdrant Filters | `qdrant_adapter.py` | 30 min | Medium |
| 7 | Cat 3: Signature Mismatch | Tiers | 60 min | High |
| 8 | Cat 4: Missing Methods | Adapters | 45 min | High |
| 9 | Cat 8: LLM Client | Engines | 30 min | Medium |
| 10 | Cat 2: BaseTier Generics | All tiers | 45 min | High |

---

## Guidelines for Future Development

### G1: Redis Async Pattern
Always explicitly type and narrow Redis return values:
```python
result: int = int(await self.client.exists(key))
```

### G2: Null Checks Before Access
Never access optional attributes without guards:
```python
if self.client is None:
    raise StorageConnectionError("Not connected")
```

### G3: Adapter Method Signatures
All adapter `search()`, `delete()`, `update()` methods accept `dict[str, Any]` query parameter. Tiers MUST construct query dicts, not pass kwargs.

### G4: Use Mapping for Covariance
When accepting adapter collections, use `Mapping[str, StorageAdapter]` not `dict[str, StorageAdapter]`.

### G5: Stats Dict Typing
Always annotate stats/counter dicts:
```python
stats: dict[str, int] = {"count": 0}
stats["count"] += 1  # Now type-safe
```

### G6: Domain Object Boundaries
Tiers return `dict[str, Any]` at API boundaries. Use `.model_dump()` for Pydantic models.

### G7: LLM Response Handling
Access `LLMResponse.content` not the response object directly:
```python
response = await self.llm_client.generate(prompt)
text = response.content  # Not response.strip()
```

---

## Verification Checklist

After all fixes:
- [ ] `mypy src/memory src/storage --namespace-packages --ignore-missing-imports` reports 0 errors
- [ ] `ruff check .` passes
- [ ] `pytest tests/ -v -m "not llm_real"` all pass
- [ ] Pre-commit hook succeeds
- [ ] Guidelines added to `.github/instructions/source.instructions.md`

---

## Related Documents

- [ADR-003: Four-Layer Memory Architecture](../ADR/003-four-layers-memory.md)
- [Lessons Learned Register](../lessons-learned.md)
- [Source Code Instructions](../../.github/instructions/source.instructions.md)

---


# Benchmark Package Mypy Cleanup Plan

**Created:** 2026-02-04  
**Status:** Planned  
**Estimated Effort:** 6-7 hours  
**Scope:** 129 mypy errors across 23 files in `benchmarks/`

---

## Executive Summary

This plan addresses making the `benchmarks/` package mypy-compliant while integrating
with the existing pre-commit workflow. The approach uses **minimal stubs** for external
dependencies, **lenient overrides** for benchmark code, and **strict typing at boundary
objects** to ensure AIMS 2025 research reproducibility.

### Related Documentation

- **Visibility Improvements:** [`benchmarks/goodai-ltm-benchmark/docs/improvement-plan.md`](../../benchmarks/goodai-ltm-benchmark/docs/improvement-plan.md)

---

## Error Distribution Summary

| Error Category | Count | Priority |
|----------------|-------|----------|
| `= None` dataclass defaults | ~20 | P1 |
| `import-untyped` | ~30 | P2 |
| Missing return annotations | ~40 | P3 |
| `union-attr` (null access) | ~15 | P4 |
| Misc (assignment, var-annotated) | ~24 | P5 |
| **Total** | **~129** | |

---

## Architectural Decisions

### Decision 1: Stubs vs. Ignores for `goodai-ltm`

**Decision:** Create minimal stub files in `stubs/goodai/`

**Rationale:**
- Prevents "ignore-rot" where future changes go unverified
- Enables IDE autocomplete for `LTMAgent`, `RetrievedMemory`, etc.
- Catches API drift if `goodai-ltm` library changes
- Only ~4 stub files needed for actual usage surface

**Alternative Rejected:** Per-import `# type: ignore` across 23 files would be harder to maintain.

### Decision 2: Strictness Level

**Decision:** Lenient overrides for benchmarks, strict for boundary objects

**Rationale:**
- Benchmark runner code can use lenient rules (`disallow_untyped_defs = false`)
- **Boundary objects** (code transforming `src/` models like `Fact`, `Episode`) must remain strict
- Critical for AIMS 2025 reproducibility—prevents "silent data corruption" where benchmarks test malformed data

**Strict Boundary Files:**
- `benchmarks/goodai-ltm-benchmark/model_interfaces/mas_memory_adapters.py`
- Any code importing from `src/memory/models.py`

### Decision 3: CI Integration

**Decision:** Single `pyproject.toml` config with per-module overrides

**Rationale:**
- Avoids configuration drift between local and CI environments
- One `mypy .` command validates entire repo
- Pre-commit hook needs no special flags
- Per-module sections apply appropriate strictness automatically

---

## Implementation Phases

### Phase 1: Foundation (30 minutes)

#### 1.1 Install Type Stub Packages

Add to `requirements-test.txt`:
```
types-click
types-PyYAML
types-requests
```

*Status: ✅ Partially complete (`types-PyYAML` installed)*

#### 1.2 Update pyproject.toml

Add benchmark-specific mypy configuration:

```toml
[[tool.mypy.overrides]]
module = "benchmarks.*"
disallow_untyped_defs = false
warn_return_any = false
ignore_missing_imports = true

# Strict for boundary objects (MAS model transformations)
[[tool.mypy.overrides]]
module = "benchmarks.goodai-ltm-benchmark.model_interfaces.mas_memory_adapters"
disallow_untyped_defs = true
warn_return_any = true
```

Add stubs path:
```toml
[tool.mypy]
mypy_path = "stubs"
```

---

### Phase 2: Create goodai-ltm Stubs (1 hour)

Create minimal stub files covering actual usage:

```
stubs/
├── goodai/
│   ├── __init__.pyi
│   ├── helpers/
│   │   ├── __init__.pyi
│   │   └── json_helper.pyi
│   └── ltm/
│       ├── __init__.pyi
│       ├── agent.pyi
│       └── mem/
│           ├── __init__.pyi
│           └── base.pyi
```

#### Stub Content Examples

**`stubs/goodai/ltm/agent.pyi`:**
```python
from typing import Any
from enum import Enum

class LTMAgentVariant(Enum):
    QA_HNSW = "qa_hnsw"
    QA_ST = "qa_st"
    # Add variants as needed

class LTMAgent:
    def __init__(self, variant: LTMAgentVariant, **kwargs: Any) -> None: ...
    def reply(self, message: str) -> str: ...
    def reset(self) -> None: ...
```

**`stubs/goodai/helpers/json_helper.pyi`:**
```python
from typing import Any

def sanitize_and_parse_json(text: str) -> Any: ...
```

---

### Phase 3: Fix Dataclass Defaults (30 minutes)

Change `field: Type = None` → `field: Type | None = None`

#### Files and Locations

| File | Lines | Fields |
|------|-------|--------|
| `dataset_interfaces/interface.py` | 69, 114, 124, 274, 277, 323 | `filler_response`, `expected_responses`, `random`, `action`, `dataset_generator` |
| `reporting/results.py` | 22-23 | `tokens`, `characters` |
| `model_interfaces/llm_interface.py` | 22-23 | `max_prompt_size`, `model` |
| `runner/scheduler.py` | 64-65 | `master_log`, `progress_dialog` |
| `model_interfaces/model.py` | 15-21 | Various fields |

#### Pattern

```python
# BEFORE
@dataclass
class TestExample:
    filler_response: str = None  # Error!

# AFTER
@dataclass
class TestExample:
    filler_response: str | None = None  # Correct
```

---

### Phase 4: Add Import Ignores (45 minutes)

Add `# type: ignore[import-untyped]` for stubless packages:

| Package | Files Affected |
|---------|----------------|
| `pystache` | `datasets/*.py` (locations, shopping, etc.) |
| `tiktoken` | `utils/llm.py`, `model_interfaces/gemini_interface.py` |
| `time_machine` | `runner/scheduler.py` |
| `termcolor` | `utils/ui.py` |
| `faker` | `datasets/*.py` |

#### Pattern

```python
import pystache  # type: ignore[import-untyped]
from faker import Faker  # type: ignore[import-untyped]
```

---

### Phase 5: Add Return Type Annotations (2-3 hours)

Priority order:

#### 5.1 Utility Functions (`utils/files.py`)

```python
# BEFORE
def gather_testdef_files(run_name: str = "*", dataset_name: str = "*"):
    return glob(...)

# AFTER
def gather_testdef_files(run_name: str = "*", dataset_name: str = "*") -> list[str]:
    return glob(...)
```

#### 5.2 ChatSession Methods (`model_interfaces/`)

All `reply()`, `reset()`, `get_stats()` methods across:
- `llm_interface.py`
- `gemini_interface.py`
- `huggingface_interface.py`
- `base_ltm_agent.py`

#### 5.3 Scheduler Methods (`runner/scheduler.py`)

- `run_tests() -> None`
- `run_single_test() -> TestResult`
- `_setup_logging() -> None`

---

### Phase 6: Add Null Guards (1 hour)

Insert assertions or conditionals for optional attribute access:

#### Pattern A: Assertion (for known-initialized state)

```python
# scheduler.py
def run_tests(self) -> None:
    assert self.master_log is not None, "master_log must be initialized before run"
    self.master_log.load()
```

#### Pattern B: Conditional (for truly optional)

```python
if self.progress_dialog is not None:
    self.progress_dialog.update(progress)
```

#### Files

| File | Attributes |
|------|------------|
| `runner/scheduler.py` | `master_log`, `progress_dialog` |
| `dataset_interfaces/interface.py` | `action`, `dataset_generator` |

---

### Phase 7: Validate Boundary Objects (30 minutes)

Ensure strict typing in MAS model adapters:

**File:** `benchmarks/goodai-ltm-benchmark/model_interfaces/mas_memory_adapters.py`

Verify:
- All functions have explicit return types
- All parameters are typed
- `Fact`, `Episode`, `KnowledgeDocument` imports are used correctly
- No `Any` types for MAS model transformations

---

## Integration with Visibility Improvements

The visibility improvements from [`improvement-plan.md`](../../benchmarks/goodai-ltm-benchmark/docs/improvement-plan.md)
should be implemented with mypy compliance from the start:

| Visibility Feature | Mypy Consideration |
|--------------------|--------------------|
| `tqdm` progress reporting | `tqdm` has type stubs—no issues |
| `turn_metrics.jsonl` output | Use `TypedDict` for metric records |
| Watchdog with `run_error.json` | Type the diagnostic dict structure |
| Grafana dashboard template | JSON only—no Python typing needed |
| Phoenix trace alignment | OpenTelemetry has stubs—verify imports |

### Recommended Metric TypedDict

```python
from typing import TypedDict

class TurnMetric(TypedDict):
    timestamp: str
    test_id: str
    turn_id: int
    llm_ms: float
    storage_ms: float
    total_ms: float
    tokens_in: int
    tokens_out: int
    status: str  # "success" | "error"
```

---

## Validation Checklist

- [ ] `mypy benchmarks/` passes with zero errors
- [ ] Pre-commit hook passes on benchmark files
- [ ] IDE autocomplete works for `goodai-ltm` classes
- [ ] `mas_memory_adapters.py` passes strict mypy checks
- [ ] No `# type: ignore` without specific error code
- [ ] Type stubs cover all used `goodai-ltm` APIs

---

## Effort Summary

| Phase | Task | Time |
|-------|------|------|
| 1 | Foundation (stubs install, pyproject.toml) | 30 min |
| 2 | Create `stubs/goodai/` | 1 hour |
| 3 | Fix dataclass defaults | 30 min |
| 4 | Add import ignores | 45 min |
| 5 | Return type annotations | 2-3 hours |
| 6 | Null guards | 1 hour |
| 7 | Validate boundary objects | 30 min |
| **Total** | | **6-7 hours** |

---

## References

- [Mypy Per-Module Configuration](https://mypy.readthedocs.io/en/stable/config_file.html#per-module-and-global-options)
- [PEP 561: Distributing and Packaging Type Information](https://peps.python.org/pep-0561/)
- [Pydantic v2 Mypy Integration](https://docs.pydantic.dev/latest/integrations/mypy/)
- [Visibility Improvement Plan](../../benchmarks/goodai-ltm-benchmark/docs/improvement-plan.md)

