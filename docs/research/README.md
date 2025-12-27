# Research Validation for Phase 3: Agent Integration Layer

**Date:** December 27, 2024  
**Status:** Research Complete — Critical Analysis & Decision Framework  
**Scope:** Validation of 5 critical architectural decisions for Phase 3 (Agent Integration Layer)

---

## Executive Summary

This directory contains five research reports (RT1-RT5) commissioned to validate critical design decisions for Phase 3 of the MAS Memory Layer project. The research was conducted by AI agents **without full project context**, necessitating careful analysis and interpretation against our novel four-tier memory architecture and CIAR-based significance scoring system.

**Key Finding:** All five research topics validate our Phase 3 architectural decisions with **strong empirical support**. However, the generic research must be adapted to our specific context: a **four-tier CIAR-driven memory system** (not a standard RAG), designed for **supply chain/logistics MAS** (not general-purpose agents), targeting **academic research publication** at AIMS 2025.

### Research Quality Assessment

| Report | Depth | Relevance | Actionability | Critical Gaps |
|--------|-------|-----------|---------------|---------------|
| **RT1: LangGraph** | ★★★★★ | ★★★★★ | ★★★★★ | Minimal — directly applicable |
| **RT2: Gemini Structured Output** | ★★★★★ | ★★★★☆ | ★★★★☆ | Lacks CIAR-specific calibration patterns |
| **RT3: Redis Namespace** | ★★★★★ | ★★★★★ | ★★★★★ | **Critical flaw identified in prototype** |
| **RT4: Context Injection** | ★★★★★ | ★★★★★ | ★★★★☆ | Conflates tiers (L2 vs L3) with different retrieval patterns |
| **RT5: CIAR Decision-Making** | ★★★★☆ | ★★★★★ | ★★★★☆ | Strong validation but lacks operational thresholds |

---

## Critical Analysis by Research Topic

### RT1: LangGraph Tool Integration — **VALIDATED & READY**

**Research Question:** Can our hybrid three-tier tool architecture (Unified + Granular + Feature-Specific) integrate seamlessly with LangGraph?

**Research Conclusion:** ✅ **Affirmative with caveats**. LangGraph's StateGraph and sub-graph composition directly support the proposed architecture.

#### Strengths of the Research
1. **Comprehensive technical depth**: 533 lines covering StateGraph reducers, InjectedState pattern, parallel execution, sub-graphs, circuit breakers, and async context management
2. **Production-oriented**: Addresses real-world concerns (ASGI context loss, connection pooling, retry policies)
3. **Provider-specific guidance**: Identifies Gemini Union type incompatibility (critical for our multi-provider strategy)

#### Critical Gaps for Our Project
1. **No CIAR-aware tool signatures**: Research focuses on generic tools, not memory retrieval tools with CIAR parameters
2. **Missing benchmark integration**: No discussion of how tools will interact with GoodAI LTM Benchmark scenarios
3. **Supply chain domain**: Generic agent patterns need adaptation to logistics workflows (route planning, shipment tracking, inventory queries)

#### Actionable Decisions

**✅ ADOPT: Hybrid Tool Architecture**
```python
# Unified Memory Interface (Phase 3)
class UnifiedMemorySystem:
    def get_context(self, query: str, agent_id: str) -> ContextBlock:
        """Auto-injected L2 working memory (Zep pattern)"""
    
    def search_memory(self, query: str, filters: CIARFilters) -> List[Fact]:
        """On-demand L3 episodic retrieval (Tool-based)"""
```

**✅ ADOPT: InjectedState Pattern**
```python
from typing import Annotated
from langgraph.types import InjectedState

@tool
def retrieve_facts(
    query: str,
    state: Annotated[dict, InjectedState]  # Hidden from LLM
) -> List[Fact]:
    agent_id = state["agent_id"]
    session_id = state["session_id"]
    # Namespaced retrieval using injected context
```

**✅ ADOPT: Sub-Graph Feature Isolation**
- Feature-specific tools (e.g., `calculate_shipment_eta`, `check_inventory_status`) isolated in sub-graphs
- Top-level supervisor routes to logistics domains (Procurement, Warehousing, Transportation)

**⚠️ CRITICAL: Async Context Management**
- **Mandate async tools** for all memory operations to preserve ASGI context
- Use `AsyncPostgresSaver` (not sync) for checkpointing
- Implement connection pooling with resilient reconnection logic

**❌ REJECT: Static Tool Binding**
- Dynamic tool selection based on agent context (research snippet 16-17)
- Load only relevant tools per sub-graph to avoid LLM confusion

---

### RT2: Gemini Structured Output — **VALIDATED WITH CAVEATS**

**Research Question:** Can we reliably extract CIAR-scored facts using Gemini's structured output mode?

**Research Conclusion:** ✅ **>95% reliability achievable** with "Reasoning-First" schema design, but requires adversarial reflection for confidence calibration.

#### Strengths of the Research
1. **Technical precision**: 292 lines detailing `response_schema`, constrained decoding, Pydantic V2 compatibility
2. **Performance analysis**: Gemini 1.5 Flash recommended for real-time extraction (cost-effective, low latency)
3. **Fallback hierarchy**: Native structured output → Tool-calling → OutputFixingParser

#### Critical Gaps for Our Project
1. **CIAR calibration methodology**: Research discusses generic confidence scores, not our specific CIAR formula:
   ```
   CIAR = (Certainty × Impact) × exp(-0.0231×days) × (1 + 0.1×accesses)
   ```
2. **L2 promotion thresholds**: No guidance on operationalizing the 0.6 threshold for L1→L2 fact promotion
3. **Batch vs. real-time**: Research conflates single-turn extraction with our lifecycle engine architecture

#### Actionable Decisions

**✅ ADOPT: Reasoning-First Schema**
```python
from pydantic import BaseModel, Field

class CIARFactExtraction(BaseModel):
    thought_process: str = Field(
        description="Analyze ambiguity, evidence quality, and temporal context BEFORE scoring"
    )
    facts: List[CIARFact]
    
class CIARFact(BaseModel):
    content: str
    evidence: str  # Direct quote from conversation
    certainty_reasoning: str  # Must precede certainty_score
    certainty_score: float = Field(ge=0.0, le=1.0)
    impact_score: int = Field(ge=1, le=10)
    temporal_context: str  # For Age calculation
```

**⚠️ Key Ordering Hack:** Use `propertyOrdering` in Vertex AI or manual schema manipulation to ensure `certainty_reasoning` generates before `certainty_score`.

**✅ ADOPT: Gemini 1.5 Flash for Promotion Engine**
- **Latency:** <0.5s for real-time L1→L2 promotion (acceptable for conversational flow)
- **Cost:** $0.075/1M input, $0.30/1M output (sustainable for high-volume fact extraction)
- **Context window:** 1M tokens (sufficient for 10-20 turn L1 window analysis)

**✅ ADOPT: Adversarial Reflection for Certainty**
- Inject adversarial prompt: *"List reasons this fact might be uncertain or ambiguous before scoring"*
- Mitigates overconfidence bias (research finding: models default to 0.9-1.0 without reflection)

**❌ DEFER: Gemini 1.5 Pro**
- Reserve for offline Consolidation Engine (L2→L3) and Distillation Engine (L3→L4)
- Batch processing where latency is non-critical

**⚠️ VALIDATE: Union Type Avoidance**
- Research identifies Gemini incompatibility with `Union[int, str]` types
- **Action:** Use distinct Pydantic fields or `oneOf` JSON schema (ADR update required)

---

### RT3: Redis Namespace Strategy — **VALIDATED BUT PROTOTYPE FLAWED**

**Research Question:** Is our `{scope}:{id}:{resource}` namespace optimal for concurrent agent writes?

**Research Conclusion:** ✅ **Structurally sound** with **mandatory Hash Tag modification**. ❌ **Optimistic locking (WATCH) rejected** in favor of Lua scripting.

#### Strengths of the Research
1. **451 lines of production-grade analysis**: Covers Redis Cluster slot distribution, Lua atomicity, RedisJSON path-level updates
2. **Concrete examples**: Shows exact failure modes (CROSSSLOT errors, retry storms)
3. **Production references**: Zep, Mem0, LangGraph checkpointing patterns

#### Critical Gaps for Our Project
1. **L1-L4 tier specificity**: Research treats "workspace" generically, not our four-tier memory hierarchy
2. **CIAR-aware keys**: No guidance on incorporating CIAR metadata into key design
3. **Lifecycle engine coordination**: Research focuses on collaborative workspace, not promotion/consolidation workflows

#### **CRITICAL FINDING: Prototype Code Flaw**

The research **explicitly rejects** the validation prototype approach in [spec-phase3-research-questions.md](../specs/spec-phase3-research-questions.md):

**Flawed Prototype (Lines 241-251 of RT3):**
```python
# User's prototype (INCORRECT)
async def agent_write(agent_id: str, value: str):
    state = await self.redis.get(workspace_key)  # NON-ATOMIC
    version = 0 if not state else int(state.get("version", 0))
    await asyncio.sleep(0.1)  # Artificial delay guarantees race
    success = await self.redis.set(..., nx=False)  # OVERWRITES
```

**Research Critique:**
1. No transactional scope (read and write are separate operations)
2. Missing `WATCH` command (not actually testing optimistic locking)
3. `nx=False` implements "Last Write Wins" (data loss guaranteed)

#### Actionable Decisions

**✅ ADOPT: Hash Tag Namespace**
```
# MANDATORY for Redis Cluster compatibility
{session:101}:l1:turns          # L1: Active Context
{session:101}:l2:facts          # L2: Working Memory  
{session:101}:l3:episodes       # L3: Episodic Memory
{session:101}:agent:A:scratchpad  # Agent-specific workspace
```

**Rationale:** Hash tags ensure physical colocation on same Redis node, enabling atomic multi-key operations.

**✅ ADOPT: Lua Scripting for State Transitions**

**Replace client-side WATCH with server-side Lua:**
```lua
-- Atomic L1→L2 Promotion
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
    return 0  -- Filtered
end
```

**Benefit:** Zero retry loops, serializable execution, 0% conflict rate.

**✅ ADOPT: Redis Streams for Lifecycle Coordination**
```python
# Promotion Engine publishes to stream
await redis.xadd(
    "{session:101}:lifecycle:events",
    {"event": "fact_promoted", "fact_id": "abc123", "ciar": 0.72}
)

# Consolidation Engine consumes as consumer group
messages = await redis.xreadgroup(
    "consolidation_workers", 
    "worker_1",
    {"{session:101}:lifecycle:events": ">"}
)
```

**Rationale:** Durable event sourcing (research finding: Pub/Sub loses messages if consumer is busy).

**❌ REJECT: Optimistic Locking (WATCH) for Shared State**
- Research finding: 90% retry rate under 10-agent concurrency
- Alternative: Lua scripting or RedisJSON path-level updates

**⚠️ REWRITE PROTOTYPE:** See research lines 272-317 for corrected validation code.

---

### RT4: Context Injection vs. Retrieval — **VALIDATED WITH TIER CONFUSION**

**Research Question:** Should L2 Working Memory be auto-injected or tool-retrieved?

**Research Conclusion:** ✅ **Hybrid architecture validated**: Auto-inject L2, tool-retrieve L3/L4.

#### Strengths of the Research
1. **417 lines of cognitive architecture theory**: Working memory models, prompt caching economics, Zep Context Block implementation
2. **Quantitative analysis**: 50-70% latency reduction with auto-injection vs. tool-based retrieval
3. **Production pattern**: Tool Message injection pattern to preserve cache integrity

#### Critical Gaps for Our Project
1. **Tier conflation**: Research treats L2/L3 generically. Our L2 (PostgreSQL facts) ≠ Zep's L2 (graph facts)
2. **CIAR filtering**: No discussion of how CIAR thresholds drive L2 auto-injection
3. **Lifecycle engine timing**: Research assumes static context; our L2 is **dynamically promoted** by Promotion Engine

#### **Conceptual Misalignment: Our L2 ≠ Zep's L2**

Research heavily references Zep's "Context Block" as L2:
- **Zep L2:** ~1000 tokens of graph-derived facts (high information density)
- **Our L2:** PostgreSQL table with thousands of CIAR-scored facts (requires filtering)

**Implication:** We cannot blindly auto-inject **all** L2 facts. We need a **CIAR-based L2 retrieval step** before injection.

#### Actionable Decisions

**✅ ADOPT: Hybrid Hierarchical Strategy**

| Tier | Strategy | Mechanism | Latency |
|------|----------|-----------|---------|
| **L4 Semantic** | Static Inject | System Prompt (Cached) | 0ms (cache hit) |
| **L3 Episodic** | On-Demand Retrieval | Tool: `search_episodes()` | 100-750ms |
| **L2 Working** | **Filtered Auto-Inject** | Context Block (CIAR ≥ 0.6) | <200ms |
| **L1 Active** | Rolling Inject | Conversation History | 0ms (native) |

**✅ ADOPT: Tool Message Injection Pattern**
```python
# CORRECT: Inject at tail to preserve cache
messages = [
    SystemMessage(content="You are a logistics agent..."),  # CACHED
    *conversation_history,  # CACHED
    ToolMessage(  # DYNAMIC (not cached)
        content=context_block,
        tool_call_id="context_injection"
    ),
    HumanMessage(content=user_query)  # DYNAMIC
]
```

**❌ REJECT: System Prompt Injection**
- Research finding: Invalidates cache on every context change (60-80% cost increase)

**✅ ADOPT: CIAR-Filtered L2 Retrieval**
```python
# Pre-LLM context assembly
l2_facts = await memory.l2_tier.retrieve(
    session_id=session_id,
    min_ciar_score=0.6,  # Promotion threshold
    max_age_days=7,      # Recency filter
    limit=50             # Token budget
)
context_block = format_context_block(l2_facts)
```

**⚠️ VALIDATE: Prompt Caching Economics**
- Research claims 90% savings with Anthropic caching (10% read cost)
- **Action:** Benchmark with Gemini 1.5 Flash caching to validate cost model for our workload

**✅ ADOPT: Decision Autonomy Principle**
- Research finding: Agents with auto-injected context make better decisions (fewer clarifying questions)
- **Implication:** Auto-inject user preferences, session context, recent facts (not entire L2)

---

### RT5: CIAR Decision-Making — **STRONG VALIDATION**

**Research Question:** Do CIAR-aware tools improve agent decision-making by 10-20%?

**Research Conclusion:** ✅ **Hypothesis exceeded**: 18.5-48% improvements observed across multiple dimensions.

#### Strengths of the Research
1. **315 lines of empirical validation**: Cites Zep benchmarks, Memory-R1 RL studies, CISC confidence-informed reasoning
2. **Quantitative evidence**: Performance gains mapped to each CIAR component
3. **Production implementations**: Zep Fact Ratings, Mem0 adaptive gating, LangGraph memory management

#### Critical Gaps for Our Project
1. **Operational thresholds**: Research validates CIAR **concept**, not our specific 0.6 L1→L2 promotion threshold
2. **Supply chain metrics**: Generic QA tasks, not logistics KPIs (route accuracy, ETA prediction, inventory recall)
3. **Tool design details**: No specification of `ciar_explain()` or `ciar_get_top_facts()` function signatures

#### **Performance Validation Summary**

| CIAR Component | Mechanism | Observed Gain | Source |
|----------------|-----------|---------------|--------|
| **Certainty** | Confidence-Informed Self-Consistency (CISC) | 40% path reduction | Research §2.2 |
| **Certainty** | Fine-Grained Confidence Estimation | 39.5% accuracy gain | Research §2.3 |
| **Impact** | Reinforcement Learning (Memory-R1) | 48% F1 improvement | Research §3.2 |
| **Impact** | Strategic Deletion (History-Based) | 10% task success gain | Research §3.3 |
| **Age** | Temporal Knowledge Graph (Zep Graphiti) | **18.5% accuracy gain** | Research §4.1 |
| **Recency** | Adaptive Retrieval Gating | 70-90% noise reduction | Research §5.1 |

**Conclusion:** Our 10-20% hypothesis is **conservative**. Literature supports **18-48%** improvements.

#### Actionable Decisions

**✅ ADOPT: CIAR-Aware Tool Signatures**

```python
from pydantic import BaseModel, Field
from typing import Optional

class CIARFilters(BaseModel):
    min_certainty: float = Field(default=0.7, ge=0.0, le=1.0)
    min_impact: int = Field(default=5, ge=1, le=10)
    max_age_days: Optional[int] = Field(default=30, ge=1)
    recency_boost: bool = Field(default=True)

@tool
def ciar_get_top_facts(
    query: str,
    filters: CIARFilters,
    limit: int = 10
) -> List[AnnotatedFact]:
    """
    Retrieves facts filtered by CIAR thresholds.
    
    Implements:
    1. Semantic search (cosine similarity)
    2. Impact filter (Zep "poignancy" pattern)
    3. Age/validity check (temporal grounding)
    4. Recency decay (exponential: e^(-λt))
    5. Certainty threshold (confidence calibration)
    """
```

**✅ ADOPT: CIAR Explanation Tool**

```python
class CIARExplanation(BaseModel):
    reasoning_paths: List[str]
    confidence_scores: List[float]
    aggregated_confidence: float
    verbal_explanation: str
    numeric_score: float  # For system logs

@tool
def ciar_explain(
    question: str,
    context: List[Fact],
    k_paths: int = 5  # CISC sampling
) -> CIARExplanation:
    """
    Confidence-Informed Self-Consistency (CISC) reasoning.
    
    Research finding: 40% reduction in reasoning paths needed
    for equivalent accuracy (compared to standard self-consistency).
    """
```

**✅ VALIDATE: CIAR Threshold Calibration**

Research suggests agents can **learn** optimal thresholds via RL (Memory-R1 pattern):
```python
# Future: Phase 4 optimization
class AdaptiveCIARPolicy:
    def __init__(self):
        self.l1_to_l2_threshold = 0.6  # Initial (ADR-004)
        self.l2_to_l3_threshold = 0.8  # Initial (to be validated)
    
    def update_from_feedback(self, task_success: bool, facts_used: List[Fact]):
        """Reinforcement learning to adjust thresholds based on task outcomes"""
```

**Action:** Defer RL-based calibration to Phase 4. Use fixed thresholds (ADR-004) for Phase 3.

**✅ ADOPT: Hybrid Numeric + Categorical Presentation**

Research finding: Different consumers need different formats:
- **System-level filtering:** Numeric (e.g., `min_ciar_score=0.75`)
- **Prompt-level reasoning:** Categorical (`<fact impact="high" certainty="medium">`)
- **User-facing output:** Verbal ("I'm fairly confident that...")

**Implication:** Tools should return structured objects with both representations:
```python
class AnnotatedFact(BaseModel):
    content: str
    ciar_score: float  # Numeric (0.0-1.0)
    impact_label: Literal["low", "medium", "high"]  # Categorical
    certainty_label: Literal["speculative", "probable", "certain"]
    explanation: Optional[str]  # Verbal
```

---

## Phase 3 Design Decisions: Final Recommendations

### Decision Matrix

| Topic | Research Validation | Recommendation | Risk Level | ADR Update Required |
|-------|---------------------|----------------|------------|---------------------|
| **Hybrid Tool Architecture** | ✅ Strong | ADOPT | Low | ADR-007 (create) |
| **LangGraph Sub-Graphs** | ✅ Strong | ADOPT | Low | ADR-007 (create) |
| **InjectedState Pattern** | ✅ Strong | ADOPT | Low | ADR-007 (create) |
| **Gemini 1.5 Flash** | ✅ Strong | ADOPT for Promotion Engine | Low | ADR-006 (update) |
| **Reasoning-First Schema** | ✅ Strong | ADOPT | Medium | ADR-006 (update) |
| **Hash Tag Namespace** | ✅ **Critical** | **MANDATE** | High (data loss if skipped) | ADR-003 (update) |
| **Lua Scripting** | ✅ Strong | ADOPT (reject WATCH) | Low | ADR-007 (create) |
| **Redis Streams** | ✅ Strong | ADOPT (reject Pub/Sub) | Low | ADR-007 (create) |
| **L2 Auto-Injection** | ✅ Strong | ADOPT with CIAR filtering | Medium | ADR-003 (update) |
| **Tool Message Injection** | ✅ Strong | ADOPT | Low | ADR-007 (create) |
| **CIAR-Aware Tools** | ✅ Strong | ADOPT | Low | ADR-004 (update) |
| **Optimistic Locking (WATCH)** | ❌ Rejected | **DO NOT IMPLEMENT** | N/A | N/A |

### Immediate Action Items

**Priority 1: Critical Safety (Week 1)**
1. ✅ **Rewrite namespace strategy** to use Hash Tags: `{scope:id}:resource`
2. ✅ **Implement Lua scripts** for L1→L2 promotion (reject prototype's WATCH approach)
3. ✅ **Validate Redis Cluster** slot distribution with hash-tagged keys

**Priority 2: Tool Architecture (Week 2-3)**
4. ✅ **Create ADR-007:** "LangGraph Integration Architecture" (tools, sub-graphs, state management)
5. ✅ **Implement Reasoning-First Pydantic schemas** for fact extraction
6. ✅ **Design CIAR-aware tool signatures** (see RT5 recommendations)

**Priority 3: Memory Interface (Week 4)**
7. ✅ **Implement UnifiedMemorySystem** with `get_context()` and `search_memory()` methods
8. ✅ **Implement L2 CIAR filtering** before auto-injection (not all L2 facts)
9. ✅ **Add Tool Message injection** pattern to context assembly pipeline

**Priority 4: Validation (Week 5-6)**
10. ⏳ **Benchmark Gemini 1.5 Flash** structured output reliability (target: >95%)
11. ⏳ **Benchmark prompt caching** cost savings with our workload
12. ⏳ **Validate CIAR thresholds** (0.6 for L1→L2) against GoodAI LTM scenarios

---

## Research Limitations & Future Work

### What the Research Did NOT Answer

1. **GoodAI LTM Benchmark Integration**
   - Research uses generic QA datasets (GSM8K, LongMemEval)
   - Need: Validation with 32k-120k token logistics conversations

2. **Supply Chain Domain Specificity**
   - Generic agent patterns (coding assistants, chatbots)
   - Need: Logistics-specific tool design (shipment tracking, route optimization)

3. **CIAR Threshold Operationalization**
   - Conceptual validation only
   - Need: Empirical calibration with real logistics data

4. **Multi-Agent Coordination**
   - Research focuses on single-agent memory
   - Need: Validation of namespace isolation with 5-10 concurrent agents

5. **Academic Contribution**
   - No discussion of novelty for AIMS 2025 submission
   - Need: Comparative analysis vs. standard RAG, full-context baselines

### Recommended Follow-On Research

**Phase 3B (Post-Implementation):**
- RT6: CIAR threshold calibration study (logistics domain)
- RT7: GoodAI LTM benchmark adaptation to four-tier architecture
- RT8: Multi-agent coordination stress testing (namespace collision rates)

**Phase 4 (Future):**
- RT9: Reinforcement learning for adaptive CIAR policies
- RT10: Comparative evaluation vs. Mem0/Zep architectures

---

## Researcher Feedback

**Strengths:**
- Exceptional depth and technical rigor across all five reports
- Production-oriented recommendations with concrete code examples
- Strong citation of recent literature (2024-2025 papers)

**Weaknesses:**
- Lacked project-specific context (expected, per brief)
- Generic agent assumptions (not multi-agent logistics)
- Some conceptual misalignment (e.g., L2 tier interpretation)

**Overall Assessment:** ⭐⭐⭐⭐⭐ (5/5)

The research provided **actionable, high-quality validation** that substantially de-risks Phase 3 implementation. The identification of the **Redis CROSSSLOT flaw** and **optimistic locking rejection** alone justifies the research investment. All five reports are recommended for integration into Phase 3 design.

---

## References

1. **RT1:** "Architectural Feasibility and Integration Strategy for Hybrid Tool Architectures in LangGraph" (533 lines)
2. **RT2:** "Engineering Reliable Memory Subsystems with LLM Structured Outputs" (292 lines)
3. **RT3:** "Evaluation of Redis Namespace Strategies for Isolated State Management" (451 lines)
4. **RT4:** "Cognitive Equilibrium in Autonomous Systems: Auto-Injected Context vs. On-Demand Retrieval" (417 lines)
5. **RT5:** "The Efficacy of CIAR Metadata in Enhancing Agentic Information Assessment" (315 lines)

**Total Research Volume:** 2,008 lines of technical analysis

---

**Document Owner:** Phase 3 Architect  
**Next Review:** Post-implementation validation (Week 6)  
**ADR Updates Required:** ADR-003, ADR-004, ADR-006, ADR-007 (new)
