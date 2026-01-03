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
