# Phase 3 Implementation Plan: Agent Integration Layer

**Version**: 1.0  
**Date**: December 27, 2025  
**Duration**: 6 weeks  
**Status**: Ready for Implementation  
**Prerequisites**: Phase 2 Complete (441/445 tests, 86% coverage)  
**Research Validation**: Complete — See [docs/research/README.md](../research/README.md)

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
- [ ] All session-related keys share same Hash Tag
- [ ] Unit tests verify slot colocation (CRC16 check)
- [ ] Integration test with Redis Cluster mode

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

## Week 3: CIAR Tools & Granular Access

### W3.1: CIAR Feature Tools (P0)

**Objective**: Implement CIAR-aware tools with Reasoning-First schemas (RT-02, RT-05).

**Tasks**:
- [ ] Implement `ciar_calculate()` tool
- [ ] Implement `ciar_get_top_facts()` with CIAR filtering
- [ ] Implement `ciar_explain()` with multi-format output
- [ ] Create `CIARFactExtraction` Reasoning-First schema
- [ ] Add adversarial reflection prompting for certainty calibration

**Deliverables**:
```
src/agents/tools/ciar_tools.py
src/agents/schemas/ciar_schemas.py
tests/agents/tools/test_ciar_tools.py
```

**Key Implementation** (Reasoning-First):
```python
class CIARFact(BaseModel):
    content: str
    evidence: str
    certainty_reasoning: str  # MUST generate BEFORE certainty_score
    certainty_score: float = Field(ge=0.0, le=1.0)
    impact_score: int = Field(ge=1, le=10)
```

**Acceptance Criteria**:
- [ ] Schema field ordering enforces reasoning-first
- [ ] Certainty calibration with adversarial reflection
- [ ] Multi-format output (numeric + categorical + verbal)

---

### W3.2: Granular Tier Tools (P1)

**Objective**: Implement per-tier access tools for fine-grained control.

**Tasks**:
- [ ] Implement L1 tools: `l1_get_recent_turns()`, `l1_append_turn()`
- [ ] Implement L2 tools: `l2_search_facts()`, `l2_store_fact()`, `l2_get_by_ciar()`
- [ ] Implement L3 tools: `l3_search_episodes()`, `l3_query_graph()`
- [ ] Implement L4 tools: `l4_search_knowledge()`, `l4_get_by_type()`
- [ ] Write unit tests for all tools

**Deliverables**:
```
src/agents/tools/tier_tools.py
tests/agents/tools/test_tier_tools.py
```

**Acceptance Criteria**:
- [ ] All tools follow LangChain conventions
- [ ] Proper namespace isolation per tool
- [ ] Error handling with graceful degradation

---

### W3.3: Synthesis Tools (P1)

**Objective**: Implement knowledge synthesis and fact extraction tools.

**Tasks**:
- [ ] Implement `synthesize_knowledge()` tool
- [ ] Implement `extract_facts()` tool with CIAR scoring
- [ ] Implement `consolidate_session()` manual trigger
- [ ] Add caching for synthesis results

**Deliverables**:
```
src/agents/tools/synthesis_tools.py
tests/agents/tools/test_synthesis_tools.py
```

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
