# Phase 2 Specification: Memory Tier Layer

**Document Version**: 1.0  
**Date**: October 22, 2025  
**Status**: Draft - Ready for Population  
**Target Completion**: Week 3-4  
**Branch**: `dev-mas`

---

## Executive Summary

[To be populated]

**Objective**: Build intelligent memory tier controllers that orchestrate storage adapters and implement information lifecycle management (promotion, consolidation, distillation).

---

## Prerequisites

### Phase 1 Completion Status ✅
- All storage adapters implemented and tested
- Infrastructure services operational
- Metrics and observability in place

### Development Environment
- Python 3.13.5
- Virtual environment: `.venv/`
- Dependencies: [To be specified]
- Configuration: `.env` file with service credentials

**Status**: [To be verified]

---

## Architecture Overview

### Memory Tier Hierarchy (L1-L4)

The memory tier architecture implements a hierarchical, human-inspired memory system with four distinct layers, each optimized for specific access patterns, retention periods, and cognitive functions.

```mermaid
graph TB
    subgraph Agent["Agent Layer (Phase 3)"]
        AGT[LangGraph Agent]
    end
    
    subgraph Orchestrator["Memory Orchestrator"]
        ORCH[UnifiedMemorySystem]
    end
    
    subgraph L1["L1: Active Context Tier"]
        L1R[(Redis Cache)]
        L1P[(PostgreSQL Backup)]
        L1R -.fallback.-> L1P
    end
    
    subgraph L2["L2: Working Memory Tier"]
        L2P[(PostgreSQL)]
    end
    
    subgraph L3["L3: Episodic Memory Tier"]
        L3V[(Qdrant Vectors)]
        L3G[(Neo4j Graph)]
    end
    
    subgraph L4["L4: Semantic Memory Tier"]
        L4T[(Typesense Search)]
    end
    
    subgraph Lifecycle["Information Lifecycle Engine"]
        PROM[Promotion Logic<br/>L1 → L2]
        CONS[Consolidation Logic<br/>L2 → L3]
        DIST[Distillation Logic<br/>L3 → L4]
    end
    
    AGT --> ORCH
    ORCH --> L1
    ORCH --> L2
    ORCH --> L3
    ORCH --> L4
    
    L1 -->|"Confidence ≥ 0.7<br/>Frequency ≥ 2"| PROM
    PROM --> L2
    
    L2 -->|"Significance Score ≥ 0.8<br/>Cross-session value"| CONS
    CONS --> L3
    
    L3 -->|"Pattern extraction<br/>Knowledge distillation"| DIST
    DIST --> L4
    
    style L1 fill:#90EE90
    style L2 fill:#87CEEB
    style L3 fill:#DDA0DD
    style L4 fill:#F0E68C
    style Lifecycle fill:#FFE4B5
    style Orchestrator fill:#FFB6C1
```

**Key Characteristics by Tier:**

| Tier | Storage | Scope | TTL | Latency | Purpose |
|------|---------|-------|-----|---------|---------|
| **L1** | Redis + PostgreSQL | 10-20 recent turns | 24h | <0.1ms | Immediate context |
| **L2** | PostgreSQL | Session facts | 7 days | <5ms | Working knowledge |
| **L3** | Qdrant + Neo4j | Cross-session | Permanent | <50ms | Long-term memory |
| **L4** | Typesense | Domain knowledge | Permanent | <30ms | Distilled wisdom |

### Conceptual Data Flow

```mermaid
sequenceDiagram
    participant Agent
    participant Orchestrator
    participant L1 as L1 (Active)
    participant L2 as L2 (Working)
    participant L3 as L3 (Episodic)
    participant L4 as L4 (Semantic)
    participant Lifecycle
    
    Agent->>Orchestrator: add_turn(session, turn, content)
    Orchestrator->>L1: store_turn()
    L1-->>Orchestrator: turn_id
    
    Note over Lifecycle: Background processing
    Lifecycle->>L1: analyze_turn()
    L1-->>Lifecycle: turn_data
    Lifecycle->>Lifecycle: calculate_significance()
    
    alt High confidence fact detected
        Lifecycle->>L2: promote_fact()
        Note over L2: Extract entity,<br/>store preference
    end
    
    Agent->>Orchestrator: get_context(session)
    Orchestrator->>L1: get_recent_turns()
    L1-->>Orchestrator: [turns]
    Orchestrator->>L2: get_session_facts()
    L2-->>Orchestrator: [facts]
    Orchestrator-->>Agent: MemoryContext
    
    Note over Lifecycle: Periodic consolidation
    Lifecycle->>L2: get_high_value_facts()
    L2-->>Lifecycle: [facts]
    Lifecycle->>L3: consolidate_to_episodic()
    Lifecycle->>L4: distill_patterns()
```

### Directory Structure

```
src/
├── storage/              # ✅ Phase 1 Complete
│   ├── __init__.py
│   ├── base.py
│   ├── redis_adapter.py
│   ├── qdrant_adapter.py
│   ├── neo4j_adapter.py
│   └── typesense_adapter.py
├── memory/              # 🎯 Phase 2 - THIS PHASE
│   ├── __init__.py
│   ├── base_tier.py          # Abstract tier interface
│   ├── active_context_tier.py    # L1: Recent turns
│   ├── working_memory_tier.py    # L2: Session facts
│   ├── episodic_memory_tier.py   # L3: Long-term experience
│   ├── semantic_memory_tier.py   # L4: Distilled knowledge
│   ├── orchestrator.py           # Unified memory system
│   └── lifecycle/
│       ├── __init__.py
│       ├── promotion.py          # L1 → L2 promotion logic
│       ├── consolidation.py      # L2 → L3 consolidation
│       └── distillation.py       # L3 → L4 distillation
├── agents/              # Phase 3
├── evaluation/          # Phase 4
└── utils/
    ├── __init__.py
    ├── config.py
    └── logging.py

migrations/
├── 001_active_context.sql    # ✅ Phase 1
├── 002_working_memory.sql    # 🎯 Phase 2
└── README.md

tests/
├── storage/             # ✅ Phase 1 Complete
├── memory/              # 🎯 Phase 2 - THIS PHASE
│   ├── __init__.py
│   ├── test_active_context_tier.py
│   ├── test_working_memory_tier.py
│   ├── test_episodic_memory_tier.py
│   ├── test_semantic_memory_tier.py
│   ├── test_orchestrator.py
│   └── test_lifecycle_logic.py
└── integration/
    └── test_tier_integration.py
```

### Component Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent (Phase 3)                               │
│  - LangGraph workflows                                           │
│  - Stateful reasoning                                            │
│  - Memory-augmented processing                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Memory Orchestrator (Priority 9)                    │
│  - Unified API for all memory operations                        │
│  - Intelligent tier routing                                     │
│  - Lifecycle coordination                                       │
│  - Error handling and fallback logic                            │
└─┬───────────┬─────────────┬──────────────┬────────────────────┬┘
  │           │             │              │                    │
  ▼           ▼             ▼              ▼                    ▼
┌────┐     ┌─────┐      ┌──────┐      ┌──────┐            ┌──────┐
│ L1 │     │ L2  │      │  L3  │      │  L4  │            │Cycle │
│Tier│     │Tier │      │ Tier │      │ Tier │            │Logic │
└─┬──┘     └──┬──┘      └──┬───┘      └──┬───┘            └───┬──┘
  │           │             │              │                    │
  ▼           ▼             ▼              ▼                    │
┌────────────────────────────────────────────────┐              │
│         Storage Adapters (Phase 1)             │              │
│  - Redis    - PostgreSQL                       │              │
│  - Qdrant   - Neo4j      - Typesense          │              │
└────────────────────────────────────────────────┘              │
                                                                 │
              ┌──────────────────────────────────────────────────┘
              │
              ▼
    ┌─────────────────────┐
    │ Information         │
    │ Lifecycle Engine    │
    │ - Promotion        │
    │ - Consolidation    │
    │ - Distillation     │
    └─────────────────────┘
```

### Tier Characteristics Deep Dive

#### L1: Active Context Tier
**Cognitive Model**: Short-term working memory / Attention span  
**Implementation**: `ActiveContextTier` class

- **Primary Storage**: Redis (in-memory, <0.1ms access)
- **Backup Storage**: PostgreSQL (durability, recovery)
- **Data Structure**: Sliding window of recent conversation turns
- **Key Operations**:
  - `add_turn()`: Append new turn to context window
  - `get_context()`: Retrieve recent N turns (cache-first, fallback to DB)
  - `clear_expired()`: Background TTL cleanup
- **Automatic Behaviors**:
  - Auto-eviction of oldest turns when window exceeds size limit
  - Redis key expiration after 24h
  - PostgreSQL TTL-based cleanup via cron job
  - Cache repopulation on miss from PostgreSQL

#### L2: Working Memory Tier
**Cognitive Model**: Session-scoped declarative memory  
**Implementation**: `WorkingMemoryTier` class

- **Storage**: PostgreSQL only (structured queries, ACID guarantees)
- **Data Structure**: Structured facts with type, confidence, provenance
- **Fact Types**:
  - `entity`: Named entities (people, places, organizations)
  - `preference`: User or agent preferences
  - `constraint`: Business rules, requirements
  - `goal`: Objectives and targets
  - `metric`: Quantitative measurements
- **Key Operations**:
  - `add_fact()`: Store new fact with metadata
  - `get_facts()`: Query by session, type, confidence
  - `update_confidence()`: Adjust fact confidence based on reinforcement
  - `merge_facts()`: Combine duplicate/related facts
- **Promotion from L1**: Triggered by lifecycle engine when:
  - Entity extraction identifies named entities
  - Repeated mentions increase confidence score
  - Explicit preferences stated by user

#### L3: Episodic Memory Tier
**Cognitive Model**: Long-term episodic memory (specific experiences)  
**Implementation**: `EpisodicMemoryTier` class

- **Storage**: Dual-backend approach
  - **Qdrant**: Vector embeddings for semantic similarity search
  - **Neo4j**: Entity relationship graph for causal/temporal reasoning
- **Data Structure**:
  - Qdrant: Embedded conversation chunks with metadata
  - Neo4j: `(Entity)-[RELATIONSHIP]->(Entity)` graph
- **Key Operations**:
  - `search_similar()`: Vector similarity search in Qdrant
  - `query_graph()`: Cypher queries for entity relationships
  - `add_episode()`: Store new episodic memory
  - `link_entities()`: Create or strengthen graph edges
- **Consolidation from L2**: Triggered when:
  - Facts have cross-session relevance
  - Entity relationships emerge
  - Patterns repeat across multiple sessions

#### L4: Semantic Memory Tier
**Cognitive Model**: Long-term semantic memory (general knowledge)  
**Implementation**: `SemanticMemoryTier` class

- **Storage**: Typesense (full-text search, faceted search)
- **Data Structure**: Distilled knowledge documents with rich metadata
- **Document Types**:
  - `pattern`: Learned behavioral patterns
  - `rule`: Domain rules and policies
  - `metric_summary`: Aggregated statistics
  - `insight`: Strategic insights
- **Key Operations**:
  - `search()`: Full-text and faceted search
  - `add_knowledge()`: Store distilled insight
  - `update_knowledge()`: Merge new learnings with existing
- **Distillation from L3**: Triggered when:
  - Patterns emerge from episodic data
  - Statistical significance in aggregated metrics
  - Manual curation by specialized agents

### Information Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> L1_Raw: User/Agent Turn
    
    L1_Raw --> L1_Analyzed: Background Analysis
    L1_Analyzed --> L1_Expired: TTL > 24h
    L1_Analyzed --> L2_Candidate: Promotion Criteria Met
    L1_Expired --> [*]
    
    L2_Candidate --> L2_Fact: Extract & Structure
    L2_Fact --> L2_Reinforced: Repeated Mention
    L2_Fact --> L2_Expired: TTL > 7d AND Low Confidence
    L2_Reinforced --> L3_Candidate: Consolidation Criteria Met
    L2_Expired --> [*]
    
    L3_Candidate --> L3_Episode: Embed & Graph
    L3_Episode --> L3_Pattern: Pattern Detection
    L3_Pattern --> L4_Candidate: Distillation Criteria Met
    
    L4_Candidate --> L4_Knowledge: Generalize & Index
    L4_Knowledge --> L4_Updated: New Evidence
    L4_Updated --> L4_Knowledge
    
    note right of L2_Fact
        Confidence Score
        Source Provenance
        Fact Type
    end note
    
    note right of L3_Episode
        Vector Embedding
        Graph Relationships
        Temporal Context
    end note
    
    note right of L4_Knowledge
        Domain Knowledge
        Operational Rules
        Strategic Insights
    end note
```

### Significance Scoring (CIAR Framework)

The lifecycle engine uses a multi-factor scoring system to determine promotion/consolidation:

**Formula:**
```
Significance = (Certainty × 0.3) + (Impact × 0.3) + (Age_Factor × 0.2) + (Recency × 0.2)
```

**Components:**
- **Certainty (C)**: 0.0-1.0, based on:
  - Explicit vs. inferred information
  - Source reliability
  - Contradiction detection
  
- **Impact (I)**: 0.0-1.0, based on:
  - Business criticality
  - Task relevance
  - Decision influence

- **Age_Factor (A)**: 0.0-1.0, based on:
  - Time since first mention
  - Frequency of mention
  - Temporal decay function

- **Recency (R)**: 0.0-1.0, based on:
  - Last access time
  - Recent usage count
  - Context freshness

**Thresholds:**
- **L1 → L2 Promotion**: Significance ≥ 0.70
- **L2 → L3 Consolidation**: Significance ≥ 0.80
- **L3 → L4 Distillation**: Pattern confidence ≥ 0.85

---

## Design Principles

### 1. Tier Autonomy

**Principle**: Each memory tier operates as an independent, self-contained module with minimal coupling to other tiers.

**Key Requirements:**

- **Isolated Storage Contracts**: Each tier owns its storage adapter instances and manages its own connection lifecycle
  - L1 owns Redis + PostgreSQL adapters
  - L2 owns PostgreSQL adapter (separate instance/connection pool)
  - L3 owns Qdrant + Neo4j adapters
  - L4 owns Typesense adapter

- **Independent Operations**: Tiers can function independently even if other tiers are unavailable
  ```python
  # L1 should work even if L2/L3/L4 are down
  context = await active_tier.get_context(session_id)
  # L2 should work even if L3/L4 are down
  facts = await working_tier.get_facts(session_id)
  ```

- **Self-Contained State Management**: Each tier maintains its own internal state
  - No shared global state between tiers
  - Each tier tracks its own metrics (cache hits, latency, errors)
  - Configuration is tier-specific and isolated

- **Clear Interface Boundaries**: Tiers communicate only through well-defined interfaces
  - Use abstract `BaseTier` interface for polymorphism
  - No direct method calls between tier implementations
  - Orchestrator is the only component that composes multiple tiers

- **Single Responsibility**: Each tier has one clear purpose
  - L1: Manage recent conversation window
  - L2: Extract and store session facts
  - L3: Maintain long-term experiential knowledge
  - L4: Curate distilled domain knowledge

**Benefits:**
- Easier testing (can test each tier in isolation)
- Simpler debugging (failures are localized)
- Flexible deployment (can scale tiers independently)
- Incremental development (implement tiers in any order after base interface)

**Anti-Patterns to Avoid:**
- ❌ L1 directly calling L2 methods
- ❌ Shared database connection pools across tiers
- ❌ Tiers modifying each other's data directly
- ❌ Global state variables shared between tiers

---

### 2. Information Lifecycle Management

**Principle**: Information flows through tiers based on calculated significance, not arbitrary rules. The lifecycle engine makes intelligent, data-driven decisions about promotion, consolidation, and distillation.

**Core Lifecycle Stages:**

1. **Ingestion (L1 Entry)**
   - All new information enters at L1 (Active Context)
   - Raw, unprocessed conversation turns
   - No filtering or validation at entry
   - Timestamp and provenance automatically tracked

2. **Promotion (L1 → L2)**
   - **Trigger**: Background analysis after each turn
   - **Criteria**: CIAR score ≥ 0.70 OR explicit entity/preference detection
   - **Process**:
     ```python
     # Pseudo-code
     for turn in recent_turns:
         score = calculate_ciar_score(turn)
         if score >= 0.70:
             fact = extract_fact(turn)
             await working_tier.add_fact(fact)
     ```
   - **Frequency**: Asynchronous, triggered after each turn (non-blocking)

3. **Consolidation (L2 → L3)**
   - **Trigger**: Scheduled batch job (hourly or daily)
   - **Criteria**: CIAR score ≥ 0.80 AND cross-session relevance
   - **Process**:
     - Identify high-value facts from L2
     - Embed facts as vectors → Qdrant
     - Extract entity relationships → Neo4j
     - Mark facts as "consolidated" (keep in L2 for TTL)
   - **Frequency**: Periodic background job

4. **Distillation (L3 → L4)**
   - **Trigger**: Manual or periodic pattern analysis
   - **Criteria**: Pattern confidence ≥ 0.85 OR statistical significance
   - **Process**:
     - Aggregate similar episodes from L3
     - Extract common patterns
     - Generalize to domain knowledge
     - Store as searchable documents in L4
   - **Frequency**: Daily batch job or on-demand

**Lifecycle Decision Logic:**

```python
async def should_promote_to_l2(turn_data: Dict) -> bool:
    """Determine if a turn should be promoted from L1 to L2"""
    ciar = calculate_ciar_score(turn_data)
    has_entities = detect_entities(turn_data.content)
    is_preference = is_user_preference(turn_data.content)
    
    return (
        ciar >= 0.70 or
        len(has_entities) > 0 or
        is_preference
    )

async def should_consolidate_to_l3(fact: Dict) -> bool:
    """Determine if a fact should be consolidated from L2 to L3"""
    ciar = calculate_ciar_score(fact)
    age_days = (datetime.now() - fact.created_at).days
    cross_session = fact.mentioned_in_sessions > 1
    
    return (
        ciar >= 0.80 and
        age_days >= 1 and
        cross_session
    )
```

**State Tracking:**
- Each piece of information has lifecycle metadata:
  - `lifecycle_stage`: "l1_raw" | "l2_fact" | "l3_episode" | "l4_knowledge"
  - `promoted_at`: Timestamp of last promotion
  - `ciar_score`: Current significance score
  - `promotion_history`: Audit trail of tier transitions

**Idempotency Guarantees:**
- Promotion operations are idempotent (can be retried safely)
- Facts are deduplicated before insertion into L2
- Consolidation checks for existing embeddings/graph nodes

---

### 3. Graceful Degradation

**Principle**: The system continues to function with reduced capabilities when components fail, rather than failing completely. Each tier has fallback strategies and the orchestrator handles failures transparently.

**Tier-Level Degradation Strategies:**

**L1 (Active Context):**
```python
async def get_context(self, session_id: str) -> List[Dict]:
    """L1 with Redis → PostgreSQL fallback"""
    try:
        # Try Redis first (primary)
        context = await self.redis.search({'session_id': session_id})
        if context:
            self.metrics.record('l1_cache_hit')
            return context
    except RedisConnectionError:
        self.logger.warning("Redis unavailable, falling back to PostgreSQL")
        self.metrics.record('l1_cache_miss_redis_down')
    
    # Fallback to PostgreSQL
    try:
        context = await self.postgres.search({'session_id': session_id})
        # Repopulate Redis when it comes back
        self._schedule_cache_repopulation(session_id, context)
        return context
    except PostgresConnectionError:
        self.logger.error("Both Redis and PostgreSQL unavailable")
        self.metrics.record('l1_total_failure')
        return []  # Return empty rather than raise
```

**L2 (Working Memory):**
```python
async def get_facts(self, session_id: str) -> List[Dict]:
    """L2 with graceful empty return on failure"""
    try:
        return await self.postgres.search({
            'session_id': session_id,
            'table': 'working_memory'
        })
    except PostgresConnectionError:
        self.logger.error(f"L2 unavailable for session {session_id}")
        self.metrics.record('l2_query_failure')
        # Don't raise - return empty list so agent can continue
        return []
```

**L3 (Episodic Memory):**
```python
async def search_memory(self, query: str) -> List[Dict]:
    """L3 with partial results on component failure"""
    results = []
    
    # Try Qdrant for vector search
    try:
        vector_results = await self.qdrant.search_similar(query)
        results.extend(vector_results)
        self.metrics.record('l3_qdrant_success')
    except QdrantConnectionError:
        self.logger.warning("Qdrant unavailable, skipping vector search")
        self.metrics.record('l3_qdrant_failure')
        # Continue without vector results
    
    # Try Neo4j for graph results
    try:
        graph_results = await self.neo4j.query_graph(query)
        results.extend(graph_results)
        self.metrics.record('l3_neo4j_success')
    except Neo4jConnectionError:
        self.logger.warning("Neo4j unavailable, skipping graph search")
        self.metrics.record('l3_neo4j_failure')
        # Continue without graph results
    
    # Return whatever we got (even if partial)
    return results
```

**Orchestrator-Level Degradation:**
```python
async def get_context(self, session_id: str) -> MemoryContext:
    """Orchestrator assembles context from available tiers"""
    context = MemoryContext()
    
    # Try each tier, continue on failure
    try:
        context.active_turns = await self.l1.get_context(session_id)
    except Exception as e:
        self.logger.warning(f"L1 failed: {e}")
        context.active_turns = []
    
    try:
        context.session_facts = await self.l2.get_facts(session_id)
    except Exception as e:
        self.logger.warning(f"L2 failed: {e}")
        context.session_facts = []
    
    try:
        context.episodic_memory = await self.l3.search_memory(query)
    except Exception as e:
        self.logger.warning(f"L3 failed: {e}")
        context.episodic_memory = []
    
    # Return partial context - agent can work with what's available
    return context
```

**Failure Modes & Responses:**

| Failure Scenario | System Response | User Impact |
|------------------|-----------------|-------------|
| Redis down | Use PostgreSQL for L1 | Slightly higher latency (~5ms vs 0.1ms) |
| PostgreSQL down | L1 cache-only, L2 empty | No session facts, limited context |
| Qdrant down | Skip vector search in L3 | No semantic similarity, graph still works |
| Neo4j down | Skip graph search in L3 | No entity relationships, vectors still work |
| Typesense down | L4 unavailable | No distilled knowledge, L1-L3 still work |
| All of L3/L4 down | Operate on L1+L2 only | Recent context + session facts only |

**Recovery Strategies:**
- **Circuit Breaker Pattern**: Temporarily disable failed components, retry periodically
- **Health Checks**: Each tier exposes `health()` method for monitoring
- **Automatic Retry**: Failed operations retry with exponential backoff
- **Queue Buffering**: Lifecycle operations buffer to queue during outages

---

### 4. Observability

**Principle**: Every operation in the memory tier system is instrumented for monitoring, debugging, and performance optimization. Comprehensive metrics, logs, and traces provide full visibility into system behavior.

**Metrics Collection (via existing Phase 1 infrastructure):**

Each tier tracks standard metrics using the established metrics system:

```python
# Example from ActiveContextTier
class ActiveContextTier(BaseTier):
    def __init__(self, redis, postgres):
        super().__init__()
        self.metrics = MetricsCollector(component="active_context_tier")
        # ... initialization
    
    async def get_context(self, session_id: str):
        start_time = time.time()
        try:
            result = await self._fetch_context(session_id)
            
            # Record success metrics
            self.metrics.record_operation(
                operation="get_context",
                duration_ms=(time.time() - start_time) * 1000,
                success=True,
                metadata={'session_id': session_id, 'result_count': len(result)}
            )
            return result
        except Exception as e:
            # Record failure metrics
            self.metrics.record_operation(
                operation="get_context",
                duration_ms=(time.time() - start_time) * 1000,
                success=False,
                error_type=type(e).__name__
            )
            raise
```

**Tier-Specific Metrics:**

**L1 Metrics:**
- `l1.cache.hit_rate`: Percentage of Redis cache hits
- `l1.cache.miss_rate`: Percentage requiring PostgreSQL fallback
- `l1.window.size`: Current number of turns in window
- `l1.ttl.expirations`: Count of TTL-based evictions
- `l1.latency.redis_p50/p95/p99`: Redis read latency percentiles
- `l1.latency.postgres_p50/p95/p99`: PostgreSQL fallback latency

**L2 Metrics:**
- `l2.facts.total`: Total facts stored per session
- `l2.facts.by_type`: Count by fact type (entity, preference, etc.)
- `l2.promotions.count`: Number of promotions from L1
- `l2.promotions.rate`: Promotions per minute
- `l2.confidence.avg`: Average confidence score of facts
- `l2.ttl.expirations`: Count of expired facts

**L3 Metrics:**
- `l3.embeddings.count`: Total vectors in Qdrant
- `l3.graph.nodes`: Total nodes in Neo4j
- `l3.graph.relationships`: Total edges in Neo4j
- `l3.consolidations.count`: L2→L3 consolidations
- `l3.search.latency`: Vector search latency
- `l3.query.latency`: Graph query latency

**L4 Metrics:**
- `l4.documents.count`: Total knowledge documents
- `l4.distillations.count`: L3→L4 distillations
- `l4.search.queries`: Search query count
- `l4.search.latency`: Search latency

**Lifecycle Metrics:**
- `lifecycle.promotions.triggered`: L1→L2 promotions attempted
- `lifecycle.promotions.success`: Successful promotions
- `lifecycle.consolidations.triggered`: L2→L3 consolidations attempted
- `lifecycle.consolidations.success`: Successful consolidations
- `lifecycle.ciar_scores.distribution`: Histogram of CIAR scores

**Structured Logging:**

```python
import logging
import json

logger = logging.getLogger(__name__)

# Structured log format
def log_tier_operation(tier: str, operation: str, **kwargs):
    logger.info(json.dumps({
        'timestamp': datetime.utcnow().isoformat(),
        'tier': tier,
        'operation': operation,
        'session_id': kwargs.get('session_id'),
        'duration_ms': kwargs.get('duration_ms'),
        'success': kwargs.get('success', True),
        'metadata': kwargs.get('metadata', {})
    }))

# Usage in tier
await self.add_turn(session_id, turn_id, content)
log_tier_operation(
    tier='L1',
    operation='add_turn',
    session_id=session_id,
    turn_id=turn_id,
    duration_ms=12.3,
    metadata={'content_length': len(content)}
)
```

**Distributed Tracing:**

Integrate with OpenTelemetry for cross-tier tracing:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class MemoryOrchestrator:
    async def get_context(self, session_id: str):
        with tracer.start_as_current_span("orchestrator.get_context") as span:
            span.set_attribute("session_id", session_id)
            
            # L1 retrieval (creates child span)
            with tracer.start_as_current_span("l1.get_context"):
                l1_data = await self.l1.get_context(session_id)
                span.set_attribute("l1.result_count", len(l1_data))
            
            # L2 retrieval (creates child span)
            with tracer.start_as_current_span("l2.get_facts"):
                l2_data = await self.l2.get_facts(session_id)
                span.set_attribute("l2.fact_count", len(l2_data))
            
            return MemoryContext(active=l1_data, facts=l2_data)
```

**Health Check Endpoints:**

Each tier exposes health status:

```python
class BaseTier(ABC):
    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        """Return health status of this tier"""
        pass

# Implementation example
class ActiveContextTier(BaseTier):
    async def health(self) -> Dict[str, Any]:
        health_status = {
            'tier': 'L1',
            'status': 'healthy',
            'components': {}
        }
        
        # Check Redis
        try:
            await self.redis.client.ping()
            health_status['components']['redis'] = 'healthy'
        except Exception as e:
            health_status['components']['redis'] = f'unhealthy: {e}'
            health_status['status'] = 'degraded'
        
        # Check PostgreSQL
        try:
            await self.postgres.pool.fetchval('SELECT 1')
            health_status['components']['postgresql'] = 'healthy'
        except Exception as e:
            health_status['components']['postgresql'] = f'unhealthy: {e}'
            health_status['status'] = 'degraded'
        
        return health_status
```

**Dashboards & Alerts:**

Recommended monitoring setup:
- **Grafana Dashboard**: Visualize all tier metrics in real-time
- **Alert Rules**:
  - L1 cache hit rate < 80% → Warning
  - Any tier latency P95 > 2× baseline → Warning
  - Lifecycle promotion failures > 5% → Alert
  - Any tier health status = 'unhealthy' → Critical

---

### 5. Testability

**Principle**: Every component in the memory tier system is designed to be easily testable in isolation and integration. Tests should be fast, reliable, and provide confidence in system behavior.

**Test Pyramid Structure:**

```
           ╱╲
          ╱  ╲
         ╱ E2E ╲         10% - End-to-end (full system)
        ╱────────╲
       ╱          ╲
      ╱ Integration╲     30% - Integration (tier + storage)
     ╱──────────────╲
    ╱                ╲
   ╱   Unit Tests     ╲  60% - Unit (tier logic only)
  ╱────────────────────╲
```

**Unit Test Design:**

Each tier should be testable with mocked storage adapters:

```python
# tests/memory/test_active_context_tier.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.memory.active_context_tier import ActiveContextTier

@pytest.fixture
def mock_redis():
    """Mock Redis adapter"""
    mock = AsyncMock()
    mock.search.return_value = [
        {'turn_id': 1, 'content': 'Hello'},
        {'turn_id': 2, 'content': 'World'}
    ]
    return mock

@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL adapter"""
    mock = AsyncMock()
    return mock

@pytest.fixture
def active_tier(mock_redis, mock_postgres):
    """ActiveContextTier with mocked dependencies"""
    return ActiveContextTier(
        redis=mock_redis,
        postgres=mock_postgres,
        window_size=10
    )

@pytest.mark.asyncio
async def test_get_context_cache_hit(active_tier, mock_redis):
    """Test L1 retrieval with Redis cache hit"""
    result = await active_tier.get_context(session_id='test-123')
    
    # Verify Redis was called
    mock_redis.search.assert_called_once_with({'session_id': 'test-123'})
    
    # Verify result
    assert len(result) == 2
    assert result[0]['content'] == 'Hello'

@pytest.mark.asyncio
async def test_get_context_cache_miss(active_tier, mock_redis, mock_postgres):
    """Test L1 retrieval with Redis miss, PostgreSQL fallback"""
    # Simulate Redis cache miss
    mock_redis.search.return_value = []
    mock_postgres.search.return_value = [
        {'turn_id': 1, 'content': 'From DB'}
    ]
    
    result = await active_tier.get_context(session_id='test-123')
    
    # Verify fallback to PostgreSQL
    mock_postgres.search.assert_called_once()
    assert result[0]['content'] == 'From DB'
```

**Integration Test Design:**

Test tiers with real storage adapters in test environment:

```python
# tests/memory/test_tier_integration.py
import pytest
from src.memory.active_context_tier import ActiveContextTier
from src.storage.redis_adapter import RedisAdapter
from src.storage.postgres_adapter import PostgresAdapter

@pytest.fixture
async def real_active_tier():
    """ActiveContextTier with real storage adapters in test env"""
    redis = RedisAdapter(os.getenv('TEST_REDIS_URL'))
    postgres = PostgresAdapter(os.getenv('TEST_POSTGRES_URL'))
    
    await redis.connect()
    await postgres.connect()
    
    tier = ActiveContextTier(redis, postgres, window_size=5)
    
    yield tier
    
    # Cleanup
    await redis.disconnect()
    await postgres.disconnect()

@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_lifecycle_l1_to_l2(real_active_tier):
    """Test complete promotion flow from L1 to L2"""
    session_id = f"test-{uuid.uuid4()}"
    
    # Add turns to L1
    await real_active_tier.add_turn(session_id, 1, "User prefers Hamburg")
    await real_active_tier.add_turn(session_id, 2, "Confirm Hamburg port")
    
    # Trigger promotion logic
    from src.memory.lifecycle.promotion import PromotionEngine
    promoter = PromotionEngine(l1=real_active_tier, l2=real_working_tier)
    promoted_facts = await promoter.analyze_session(session_id)
    
    # Verify fact was promoted to L2
    assert len(promoted_facts) > 0
    assert 'Hamburg' in promoted_facts[0]['content']
```

**Test Fixtures & Factories:**

```python
# tests/fixtures.py
from datetime import datetime, timedelta

def create_test_turn(turn_id: int, content: str, **kwargs):
    """Factory for creating test turn data"""
    return {
        'turn_id': turn_id,
        'content': content,
        'session_id': kwargs.get('session_id', 'test-session'),
        'created_at': kwargs.get('created_at', datetime.utcnow()),
        'metadata': kwargs.get('metadata', {})
    }

def create_test_fact(fact_type: str, content: str, **kwargs):
    """Factory for creating test fact data"""
    return {
        'fact_type': fact_type,
        'content': content,
        'confidence': kwargs.get('confidence', 0.85),
        'session_id': kwargs.get('session_id', 'test-session'),
        'source_turn_ids': kwargs.get('source_turn_ids', [1]),
        'created_at': kwargs.get('created_at', datetime.utcnow())
    }
```

**Test Data Management:**

```python
# Separate test database
TEST_POSTGRES_URL = "postgresql://test:test@localhost:5432/mas_memory_test"

# Cleanup strategy
@pytest.fixture(scope="function", autouse=True)
async def cleanup_test_data():
    """Clean up test data after each test"""
    yield
    # Cleanup runs after test
    async with asyncpg.create_pool(TEST_POSTGRES_URL) as pool:
        async with pool.acquire() as conn:
            await conn.execute("TRUNCATE active_context CASCADE")
            await conn.execute("TRUNCATE working_memory CASCADE")
```

**Property-Based Testing:**

Use Hypothesis for property-based tests:

```python
from hypothesis import given, strategies as st

@given(
    session_id=st.text(min_size=1, max_size=50),
    turn_count=st.integers(min_value=1, max_value=100)
)
@pytest.mark.asyncio
async def test_l1_window_size_property(active_tier, session_id, turn_count):
    """Property: L1 window never exceeds configured size"""
    window_size = active_tier.window_size
    
    # Add many turns
    for i in range(turn_count):
        await active_tier.add_turn(session_id, i, f"Turn {i}")
    
    # Retrieve context
    context = await active_tier.get_context(session_id)
    
    # Property: result should never exceed window size
    assert len(context) <= window_size
```

**Performance Testing:**

```python
@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_l1_read_latency(active_tier, benchmark):
    """Benchmark L1 read latency"""
    session_id = "bench-session"
    
    # Setup
    await active_tier.add_turn(session_id, 1, "Test content")
    
    # Benchmark
    result = await benchmark.pedantic(
        active_tier.get_context,
        args=(session_id,),
        rounds=100
    )
    
    # Assert performance target
    assert benchmark.stats['mean'] < 0.005  # < 5ms average
```

**Test Coverage Requirements:**

- **Minimum Coverage**: 80% for all tier implementations
- **Critical Path Coverage**: 100% for lifecycle logic (promotion/consolidation)
- **Edge Case Coverage**: Explicit tests for:
  - Empty results
  - TTL expiration boundary conditions
  - Cache miss scenarios
  - Concurrent access patterns
  - Network failures and retries

**Continuous Testing:**

```yaml
# .github/workflows/test.yml
name: Phase 2 Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7
        ports:
          - 6379:6379
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: mas_memory_test
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v3
      - name: Run Unit Tests
        run: pytest tests/memory -m "not integration" -v
      - name: Run Integration Tests
        run: pytest tests/memory -m integration -v
      - name: Coverage Report
        run: pytest --cov=src/memory --cov-report=xml
```

---

## Implementation Priorities

### Overview

| Priority | Component | Time | Status | Dependencies |
|----------|-----------|------|--------|--------------|
| **0** | Schema & Migrations | 1-2h | Not Started | Phase 1 Complete |
| **1** | Base Tier Interface | 2-3h | Not Started | Priority 0 |
| **2** | L1: Active Context Tier | 4-5h | Not Started | Priority 1 |
| **3** | L2: Working Memory Tier | 4-5h | Not Started | Priority 1 |
| **4** | L3: Episodic Memory Tier | 5-6h | Not Started | Priority 1 |
| **5** | L4: Semantic Memory Tier | 3-4h | Not Started | Priority 1 |
| **6** | Promotion Logic (L1→L2) | 3-4h | Not Started | Priorities 2,3 |
| **7** | Consolidation Logic (L2→L3) | 4-5h | Not Started | Priorities 3,4 |
| **8** | Distillation Logic (L3→L4) | 4-5h | Not Started | Priorities 4,5 |
| **9** | Memory Orchestrator | 5-6h | Not Started | Priorities 2-5 |
| **10** | Unit Tests | 6-8h | Not Started | All above |
| **11** | Integration Tests | 4-5h | Not Started | Priority 10 |

**Total Estimated Time**: 45-57 hours (~1.5-2 weeks)

**Legend**: ✅ Complete | 🔄 In Progress | ⚠️ Blocked | ❌ Not Started

---

## Priority 0: Database Schema & Migrations

**Estimated Time**: 1-2 hours  
**Status**: Not Started  
**Dependencies**: Phase 1 Complete

### Objective

Create PostgreSQL database schemas to support the Phase 2 memory tier system, specifically:
1. Enhance the existing `active_context` table (L1) with lifecycle metadata
2. Define the `working_memory` table (L2) for session-scoped facts
3. Create supporting tables for lifecycle tracking and analytics
4. Add indexes for efficient querying patterns
5. Verify schema integrity and compatibility with Phase 1

**Note**: The basic `active_context` and `working_memory` tables already exist from Phase 1 (`migrations/001_active_context.sql`). This migration extends them with Phase 2-specific features.

---

### Database Schema Requirements

#### Schema: `working_memory` Table (L2)

**Purpose**: Store structured facts extracted from conversation turns with provenance tracking and confidence scoring.

**Table Definition**:
```sql
CREATE TABLE IF NOT EXISTS working_memory (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Session Context
    session_id VARCHAR(255) NOT NULL,
    
    -- Fact Classification
    fact_type VARCHAR(50) NOT NULL,  -- 'entity', 'preference', 'constraint', 'goal', 'metric'
    
    -- Fact Content
    content TEXT NOT NULL,
    
    -- Lifecycle Metadata
    confidence FLOAT NOT NULL DEFAULT 0.85,  -- 0.0-1.0
    ciar_score FLOAT,  -- Calculated significance score
    lifecycle_stage VARCHAR(20) DEFAULT 'l2_fact',  -- 'l2_fact', 'l2_reinforced', 'l3_candidate'
    
    -- Provenance Tracking
    source_turn_ids INTEGER[] DEFAULT '{}',  -- Array of turn IDs that support this fact
    promoted_from_l1_at TIMESTAMP,  -- When promoted from L1
    consolidated_to_l3_at TIMESTAMP,  -- When consolidated to L3 (NULL if not yet)
    
    -- Metadata
    metadata JSONB DEFAULT '{}',  -- Additional structured data
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_accessed_at TIMESTAMP,  -- For recency calculation
    
    -- TTL Management
    ttl_expires_at TIMESTAMP,  -- 7 days from creation by default
    
    -- Constraints
    CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CHECK (ciar_score IS NULL OR (ciar_score >= 0.0 AND ciar_score <= 1.0))
);
```

**Fact Types**:
- `entity`: Named entities (people, vessels, ports, organizations)
- `preference`: User or agent preferences
- `constraint`: Business rules, requirements, restrictions
- `goal`: Objectives, targets, desired outcomes
- `metric`: Quantitative measurements, KPIs

**Example Row**:
```json
{
  "id": 42,
  "session_id": "session-abc-123",
  "fact_type": "preference",
  "content": "User prefers Hamburg port for European shipments",
  "confidence": 0.92,
  "ciar_score": 0.78,
  "lifecycle_stage": "l2_reinforced",
  "source_turn_ids": [5, 12, 18],
  "promoted_from_l1_at": "2025-10-22T10:15:00Z",
  "consolidated_to_l3_at": null,
  "metadata": {"port_code": "DEHAM", "region": "Europe"},
  "created_at": "2025-10-22T10:15:00Z",
  "updated_at": "2025-10-22T14:30:00Z",
  "last_accessed_at": "2025-10-22T15:00:00Z",
  "ttl_expires_at": "2025-10-29T10:15:00Z"
}
```

---

#### Schema: `lifecycle_events` Table

**Purpose**: Audit trail for all promotion, consolidation, and distillation events.

**Table Definition**:
```sql
CREATE TABLE IF NOT EXISTS lifecycle_events (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    
    -- Event Classification
    event_type VARCHAR(20) NOT NULL,  -- 'promotion', 'consolidation', 'distillation'
    source_tier VARCHAR(10) NOT NULL,  -- 'L1', 'L2', 'L3'
    target_tier VARCHAR(10) NOT NULL,  -- 'L2', 'L3', 'L4'
    
    -- Source Reference
    source_table VARCHAR(50),  -- 'active_context', 'working_memory', etc.
    source_id INTEGER,
    
    -- Target Reference
    target_table VARCHAR(50),
    target_id INTEGER,
    
    -- Decision Metadata
    ciar_score FLOAT,
    confidence FLOAT,
    decision_reason TEXT,  -- Human-readable explanation
    decision_metadata JSONB DEFAULT '{}',  -- Structured decision factors
    
    -- Context
    session_id VARCHAR(255),
    
    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Performance Tracking
    processing_duration_ms INTEGER,  -- How long the lifecycle operation took
    
    -- Constraints
    CHECK (event_type IN ('promotion', 'consolidation', 'distillation')),
    CHECK (source_tier IN ('L1', 'L2', 'L3')),
    CHECK (target_tier IN ('L2', 'L3', 'L4'))
);
```

**Purpose**: Provides full audit trail and enables analytics on lifecycle behavior.

---

#### Schema: Additional Indexes

**Performance Indexes**:

```sql
-- Working Memory Indexes
CREATE INDEX idx_working_session ON working_memory(session_id);
CREATE INDEX idx_working_type ON working_memory(fact_type);
CREATE INDEX idx_working_stage ON working_memory(lifecycle_stage);
CREATE INDEX idx_working_confidence ON working_memory(confidence DESC);
CREATE INDEX idx_working_ciar ON working_memory(ciar_score DESC) WHERE ciar_score IS NOT NULL;
CREATE INDEX idx_working_expires ON working_memory(ttl_expires_at) WHERE ttl_expires_at IS NOT NULL;
CREATE INDEX idx_working_updated ON working_memory(updated_at DESC);

-- Composite Indexes for common query patterns
CREATE INDEX idx_working_session_type ON working_memory(session_id, fact_type);
CREATE INDEX idx_working_session_confidence ON working_memory(session_id, confidence DESC);
CREATE INDEX idx_working_consolidation_candidates ON working_memory(ciar_score DESC, lifecycle_stage) 
    WHERE consolidated_to_l3_at IS NULL AND ciar_score >= 0.80;

-- GIN index for JSONB metadata queries
CREATE INDEX idx_working_metadata ON working_memory USING GIN (metadata);

-- GIN index for array queries (source_turn_ids)
CREATE INDEX idx_working_source_turns ON working_memory USING GIN (source_turn_ids);

-- Lifecycle Events Indexes
CREATE INDEX idx_lifecycle_event_type ON lifecycle_events(event_type);
CREATE INDEX idx_lifecycle_session ON lifecycle_events(session_id);
CREATE INDEX idx_lifecycle_source ON lifecycle_events(source_tier, source_table, source_id);
CREATE INDEX idx_lifecycle_target ON lifecycle_events(target_tier, target_table, target_id);
CREATE INDEX idx_lifecycle_created ON lifecycle_events(created_at DESC);

-- Composite index for analytics
CREATE INDEX idx_lifecycle_type_created ON lifecycle_events(event_type, created_at DESC);
```

**Index Rationale**:
- `idx_working_session`: Fast lookup of all facts for a session
- `idx_working_session_type`: Filter facts by session and type
- `idx_working_consolidation_candidates`: Efficient query for L2→L3 candidates
- `idx_working_metadata`: Enable fast JSONB queries
- `idx_working_source_turns`: Support reverse lookup from turn to facts

---

#### Schema: Enhanced Active Context (L1)

**Extension to Existing Table**:

```sql
-- Add Phase 2 columns to active_context (if not exists)
DO $$ 
BEGIN
    -- Add lifecycle_stage column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'active_context' AND column_name = 'lifecycle_stage'
    ) THEN
        ALTER TABLE active_context ADD COLUMN lifecycle_stage VARCHAR(20) DEFAULT 'l1_raw';
    END IF;
    
    -- Add ciar_score column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'active_context' AND column_name = 'ciar_score'
    ) THEN
        ALTER TABLE active_context ADD COLUMN ciar_score FLOAT;
    END IF;
    
    -- Add promoted_to_l2_at column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'active_context' AND column_name = 'promoted_to_l2_at'
    ) THEN
        ALTER TABLE active_context ADD COLUMN promoted_to_l2_at TIMESTAMP;
    END IF;
END $$;

-- Add index for lifecycle queries
CREATE INDEX IF NOT EXISTS idx_active_lifecycle ON active_context(lifecycle_stage);
CREATE INDEX IF NOT EXISTS idx_active_promotion_candidates ON active_context(ciar_score DESC) 
    WHERE promoted_to_l2_at IS NULL AND ciar_score >= 0.70;
```

---

### Migration Files

#### File: `migrations/002_working_memory.sql`

```sql
-- ============================================================================
-- Migration 002: Phase 2 Memory Tier Enhancements
-- ============================================================================
-- Description: Extends Phase 1 schema with Phase 2 lifecycle tracking
-- Author: [TBD]
-- Date: 2025-10-22
-- Dependencies: 001_active_context.sql (Phase 1)
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. Enhance Active Context Table (L1)
-- ============================================================================

-- Add Phase 2 lifecycle columns to active_context
ALTER TABLE active_context 
    ADD COLUMN IF NOT EXISTS lifecycle_stage VARCHAR(20) DEFAULT 'l1_raw',
    ADD COLUMN IF NOT EXISTS ciar_score FLOAT,
    ADD COLUMN IF NOT EXISTS promoted_to_l2_at TIMESTAMP;

-- Add constraints
ALTER TABLE active_context 
    ADD CONSTRAINT IF NOT EXISTS check_ciar_score 
    CHECK (ciar_score IS NULL OR (ciar_score >= 0.0 AND ciar_score <= 1.0));

-- Add lifecycle indexes
CREATE INDEX IF NOT EXISTS idx_active_lifecycle ON active_context(lifecycle_stage);
CREATE INDEX IF NOT EXISTS idx_active_ciar ON active_context(ciar_score DESC) 
    WHERE ciar_score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_active_promotion_candidates ON active_context(ciar_score DESC) 
    WHERE promoted_to_l2_at IS NULL AND ciar_score >= 0.70;

COMMENT ON COLUMN active_context.lifecycle_stage IS 'L1 lifecycle stage: l1_raw, l1_analyzed, l2_candidate';
COMMENT ON COLUMN active_context.ciar_score IS 'Calculated CIAR significance score (0.0-1.0)';
COMMENT ON COLUMN active_context.promoted_to_l2_at IS 'Timestamp when promoted to L2 (NULL if not promoted)';

-- ============================================================================
-- 2. Create Working Memory Table (L2)
-- ============================================================================

-- Note: Basic table created in 001_active_context.sql, extend it here
ALTER TABLE working_memory
    ADD COLUMN IF NOT EXISTS ciar_score FLOAT,
    ADD COLUMN IF NOT EXISTS lifecycle_stage VARCHAR(20) DEFAULT 'l2_fact',
    ADD COLUMN IF NOT EXISTS promoted_from_l1_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS consolidated_to_l3_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS last_accessed_at TIMESTAMP;

-- Add constraints
ALTER TABLE working_memory 
    ADD CONSTRAINT IF NOT EXISTS check_confidence 
    CHECK (confidence >= 0.0 AND confidence <= 1.0);

ALTER TABLE working_memory 
    ADD CONSTRAINT IF NOT EXISTS check_ciar_score_wm 
    CHECK (ciar_score IS NULL OR (ciar_score >= 0.0 AND ciar_score <= 1.0));

ALTER TABLE working_memory
    ADD CONSTRAINT IF NOT EXISTS check_lifecycle_stage
    CHECK (lifecycle_stage IN ('l2_fact', 'l2_reinforced', 'l3_candidate'));

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_working_stage ON working_memory(lifecycle_stage);
CREATE INDEX IF NOT EXISTS idx_working_confidence ON working_memory(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_working_ciar ON working_memory(ciar_score DESC) 
    WHERE ciar_score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_working_updated ON working_memory(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_working_session_type ON working_memory(session_id, fact_type);
CREATE INDEX IF NOT EXISTS idx_working_session_confidence ON working_memory(session_id, confidence DESC);
CREATE INDEX IF NOT EXISTS idx_working_consolidation_candidates ON working_memory(ciar_score DESC, lifecycle_stage) 
    WHERE consolidated_to_l3_at IS NULL AND ciar_score >= 0.80;
CREATE INDEX IF NOT EXISTS idx_working_metadata ON working_memory USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_working_source_turns ON working_memory USING GIN (source_turn_ids);
CREATE INDEX IF NOT EXISTS idx_working_last_accessed ON working_memory(last_accessed_at) 
    WHERE last_accessed_at IS NOT NULL;

-- Add comments
COMMENT ON COLUMN working_memory.ciar_score IS 'Calculated CIAR significance score (0.0-1.0)';
COMMENT ON COLUMN working_memory.lifecycle_stage IS 'L2 lifecycle stage: l2_fact, l2_reinforced, l3_candidate';
COMMENT ON COLUMN working_memory.promoted_from_l1_at IS 'Timestamp when promoted from L1';
COMMENT ON COLUMN working_memory.consolidated_to_l3_at IS 'Timestamp when consolidated to L3 (NULL if not yet)';
COMMENT ON COLUMN working_memory.last_accessed_at IS 'Last access time for recency calculation';

-- ============================================================================
-- 3. Create Lifecycle Events Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS lifecycle_events (
    id SERIAL PRIMARY KEY,
    
    -- Event Classification
    event_type VARCHAR(20) NOT NULL,
    source_tier VARCHAR(10) NOT NULL,
    target_tier VARCHAR(10) NOT NULL,
    
    -- Source Reference
    source_table VARCHAR(50),
    source_id INTEGER,
    
    -- Target Reference
    target_table VARCHAR(50),
    target_id INTEGER,
    
    -- Decision Metadata
    ciar_score FLOAT,
    confidence FLOAT,
    decision_reason TEXT,
    decision_metadata JSONB DEFAULT '{}',
    
    -- Context
    session_id VARCHAR(255),
    
    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Performance Tracking
    processing_duration_ms INTEGER,
    
    -- Constraints
    CONSTRAINT check_event_type CHECK (event_type IN ('promotion', 'consolidation', 'distillation')),
    CONSTRAINT check_source_tier CHECK (source_tier IN ('L1', 'L2', 'L3')),
    CONSTRAINT check_target_tier CHECK (target_tier IN ('L2', 'L3', 'L4'))
);

-- Lifecycle events indexes
CREATE INDEX idx_lifecycle_event_type ON lifecycle_events(event_type);
CREATE INDEX idx_lifecycle_session ON lifecycle_events(session_id);
CREATE INDEX idx_lifecycle_source ON lifecycle_events(source_tier, source_table, source_id);
CREATE INDEX idx_lifecycle_target ON lifecycle_events(target_tier, target_table, target_id);
CREATE INDEX idx_lifecycle_created ON lifecycle_events(created_at DESC);
CREATE INDEX idx_lifecycle_type_created ON lifecycle_events(event_type, created_at DESC);
CREATE INDEX idx_lifecycle_metadata ON lifecycle_events USING GIN (decision_metadata);

COMMENT ON TABLE lifecycle_events IS 'Audit trail for all promotion, consolidation, and distillation events';
COMMENT ON COLUMN lifecycle_events.event_type IS 'Type of lifecycle event: promotion, consolidation, distillation';
COMMENT ON COLUMN lifecycle_events.decision_reason IS 'Human-readable explanation of why the event occurred';
COMMENT ON COLUMN lifecycle_events.processing_duration_ms IS 'Processing time in milliseconds';

-- ============================================================================
-- 4. Create Utility Functions
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for working_memory
DROP TRIGGER IF EXISTS update_working_memory_updated_at ON working_memory;
CREATE TRIGGER update_working_memory_updated_at
    BEFORE UPDATE ON working_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate default TTL expiration
CREATE OR REPLACE FUNCTION set_default_ttl_expires_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ttl_expires_at IS NULL THEN
        NEW.ttl_expires_at = NOW() + INTERVAL '7 days';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for working_memory TTL
DROP TRIGGER IF EXISTS set_working_memory_ttl ON working_memory;
CREATE TRIGGER set_working_memory_ttl
    BEFORE INSERT ON working_memory
    FOR EACH ROW
    EXECUTE FUNCTION set_default_ttl_expires_at();

-- ============================================================================
-- 5. Create Views for Common Queries
-- ============================================================================

-- View: High-value facts ready for consolidation
CREATE OR REPLACE VIEW v_consolidation_candidates AS
SELECT 
    id,
    session_id,
    fact_type,
    content,
    confidence,
    ciar_score,
    source_turn_ids,
    created_at,
    updated_at,
    EXTRACT(EPOCH FROM (NOW() - created_at))/86400 AS age_days,
    array_length(source_turn_ids, 1) AS mention_count
FROM working_memory
WHERE 
    consolidated_to_l3_at IS NULL
    AND ciar_score >= 0.80
    AND lifecycle_stage IN ('l2_reinforced', 'l3_candidate')
ORDER BY ciar_score DESC, updated_at DESC;

COMMENT ON VIEW v_consolidation_candidates IS 'Facts ready for L2→L3 consolidation';

-- View: Lifecycle event statistics
CREATE OR REPLACE VIEW v_lifecycle_stats AS
SELECT 
    event_type,
    source_tier,
    target_tier,
    COUNT(*) AS event_count,
    AVG(processing_duration_ms) AS avg_duration_ms,
    MIN(created_at) AS first_event_at,
    MAX(created_at) AS last_event_at
FROM lifecycle_events
GROUP BY event_type, source_tier, target_tier
ORDER BY event_type, source_tier, target_tier;

COMMENT ON VIEW v_lifecycle_stats IS 'Aggregated lifecycle event statistics';

-- ============================================================================
-- 6. Verification
-- ============================================================================

-- Verify tables exist
DO $$
DECLARE
    missing_tables TEXT[];
BEGIN
    SELECT ARRAY_AGG(table_name) INTO missing_tables
    FROM (VALUES 
        ('active_context'),
        ('working_memory'),
        ('lifecycle_events')
    ) AS required(table_name)
    WHERE NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = required.table_name
    );
    
    IF missing_tables IS NOT NULL THEN
        RAISE EXCEPTION 'Missing required tables: %', array_to_string(missing_tables, ', ');
    END IF;
    
    RAISE NOTICE 'All required tables verified';
END $$;

COMMIT;

-- ============================================================================
-- Migration Complete
-- ============================================================================
```

---

### Verification Steps

#### 1. Pre-Migration Checks

```bash
# Verify Phase 1 migration was applied
psql $POSTGRES_URL -c "SELECT COUNT(*) FROM active_context;"
psql $POSTGRES_URL -c "SELECT COUNT(*) FROM working_memory;"

# Backup database before migration
pg_dump $POSTGRES_URL > backup_before_002_$(date +%Y%m%d_%H%M%S).sql
```

#### 2. Apply Migration

```bash
# Apply migration
psql $POSTGRES_URL -f migrations/002_working_memory.sql

# Check for errors
if [ $? -eq 0 ]; then
    echo "✅ Migration 002 applied successfully"
else
    echo "❌ Migration 002 failed"
    exit 1
fi
```

#### 3. Post-Migration Verification

**Verify Table Structure**:
```sql
-- Check active_context columns
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'active_context' 
ORDER BY ordinal_position;

-- Expected new columns:
-- lifecycle_stage, ciar_score, promoted_to_l2_at

-- Check working_memory columns
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'working_memory' 
ORDER BY ordinal_position;

-- Expected new columns:
-- ciar_score, lifecycle_stage, promoted_from_l1_at, consolidated_to_l3_at, last_accessed_at

-- Check lifecycle_events exists
SELECT COUNT(*) FROM lifecycle_events;
```

**Verify Indexes**:
```sql
-- List all indexes on working_memory
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'working_memory' 
ORDER BY indexname;

-- Should include: idx_working_stage, idx_working_confidence, idx_working_ciar, etc.

-- List all indexes on lifecycle_events
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'lifecycle_events' 
ORDER BY indexname;
```

**Verify Constraints**:
```sql
-- Check constraints on working_memory
SELECT conname, contype, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'working_memory'::regclass;

-- Expected: check_confidence, check_ciar_score_wm, check_lifecycle_stage
```

**Verify Functions and Triggers**:
```sql
-- Check triggers
SELECT trigger_name, event_manipulation, action_statement 
FROM information_schema.triggers 
WHERE event_object_table = 'working_memory';

-- Expected: update_working_memory_updated_at, set_working_memory_ttl
```

**Verify Views**:
```sql
-- Check views exist and are queryable
SELECT * FROM v_consolidation_candidates LIMIT 5;
SELECT * FROM v_lifecycle_stats;
```

#### 4. Functional Tests

**Test Data Insertion**:
```sql
-- Test inserting a fact into working_memory
INSERT INTO working_memory (
    session_id, fact_type, content, confidence, source_turn_ids
) VALUES (
    'test-session-001', 
    'preference', 
    'Test fact content',
    0.85,
    ARRAY[1, 2, 3]
);

-- Verify TTL was auto-set
SELECT id, ttl_expires_at, ttl_expires_at - created_at AS ttl_duration 
FROM working_memory 
WHERE session_id = 'test-session-001';

-- Expected: ttl_duration should be ~7 days
```

**Test Lifecycle Event Logging**:
```sql
-- Insert test lifecycle event
INSERT INTO lifecycle_events (
    event_type, source_tier, target_tier, 
    session_id, ciar_score, decision_reason
) VALUES (
    'promotion', 'L1', 'L2',
    'test-session-001', 0.75, 'Test promotion event'
);

-- Verify insertion
SELECT * FROM lifecycle_events WHERE session_id = 'test-session-001';
```

**Test Query Performance**:
```sql
-- Benchmark consolidation candidate query
EXPLAIN ANALYZE
SELECT * FROM v_consolidation_candidates LIMIT 10;

-- Expected: Should use idx_working_consolidation_candidates index
-- Execution time should be < 5ms for small datasets
```

#### 5. Cleanup Test Data

```sql
-- Remove test data
DELETE FROM working_memory WHERE session_id = 'test-session-001';
DELETE FROM lifecycle_events WHERE session_id = 'test-session-001';
```

#### 6. Documentation Update

```bash
# Update migration README
cat >> migrations/README.md << EOF

## Migration 002: Phase 2 Memory Tier Enhancements

**Applied**: $(date)
**Status**: ✅ Complete
**Tables Modified**: active_context, working_memory
**Tables Created**: lifecycle_events
**Views Created**: v_consolidation_candidates, v_lifecycle_stats

See migrations/002_working_memory.sql for details.
EOF
```

---

### Rollback Procedure (if needed)

```sql
-- migrations/002_rollback.sql
BEGIN;

-- Drop Phase 2 additions (in reverse order)
DROP VIEW IF EXISTS v_lifecycle_stats;
DROP VIEW IF EXISTS v_consolidation_candidates;

DROP TRIGGER IF EXISTS set_working_memory_ttl ON working_memory;
DROP TRIGGER IF EXISTS update_working_memory_updated_at ON working_memory;

DROP FUNCTION IF EXISTS set_default_ttl_expires_at();
DROP FUNCTION IF EXISTS update_updated_at_column();

DROP TABLE IF EXISTS lifecycle_events;

-- Remove Phase 2 columns from working_memory
ALTER TABLE working_memory
    DROP COLUMN IF EXISTS last_accessed_at,
    DROP COLUMN IF EXISTS consolidated_to_l3_at,
    DROP COLUMN IF EXISTS promoted_from_l1_at,
    DROP COLUMN IF EXISTS lifecycle_stage,
    DROP COLUMN IF EXISTS ciar_score;

-- Remove Phase 2 columns from active_context
ALTER TABLE active_context
    DROP COLUMN IF EXISTS promoted_to_l2_at,
    DROP COLUMN IF EXISTS ciar_score,
    DROP COLUMN IF EXISTS lifecycle_stage;

COMMIT;
```

---

### Success Criteria

- [ ] Migration executes without errors
- [ ] All tables have expected columns
- [ ] All indexes are created
- [ ] All constraints are applied
- [ ] Triggers fire correctly (test with INSERT/UPDATE)
- [ ] Views return data correctly
- [ ] Query performance meets targets (<5ms for indexed queries)
- [ ] Rollback script tested and verified
- [ ] Documentation updated

---

## Priority 1: Base Tier Interface

**Estimated Time**: 2-3 hours  
**Status**: Not Started  
**Dependencies**: Priority 0

### Objective

Define an abstract base interface (`BaseTier`) that all memory tier implementations must inherit from. This interface establishes a common contract for tier operations, ensuring:

1. **Uniform API**: All tiers expose the same core methods
2. **Polymorphism**: The orchestrator can treat all tiers uniformly
3. **Testability**: Mock implementations can substitute real tiers in tests
4. **Extensibility**: New tiers can be added without modifying existing code
5. **Type Safety**: Clear method signatures with type hints

The base interface is the foundation for the entire memory tier system, enabling tier autonomy while maintaining compositional flexibility.

---

### Interface Definition

#### File: `src/memory/base_tier.py`

```python
"""
Base Tier Interface - Abstract contract for all memory tier implementations
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
import logging


# ============================================================================
# Type Definitions
# ============================================================================

class TierLevel(Enum):
    """Memory tier levels"""
    L1_ACTIVE_CONTEXT = "L1"
    L2_WORKING_MEMORY = "L2"
    L3_EPISODIC_MEMORY = "L3"
    L4_SEMANTIC_MEMORY = "L4"


class HealthStatus(Enum):
    """Health status of a tier or component"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class LifecycleStage(Enum):
    """Lifecycle stages for information progression"""
    L1_RAW = "l1_raw"
    L1_ANALYZED = "l1_analyzed"
    L2_CANDIDATE = "l2_candidate"
    L2_FACT = "l2_fact"
    L2_REINFORCED = "l2_reinforced"
    L3_CANDIDATE = "l3_candidate"
    L3_EPISODE = "l3_episode"
    L4_CANDIDATE = "l4_candidate"
    L4_KNOWLEDGE = "l4_knowledge"


# ============================================================================
# Data Models
# ============================================================================

class TierMetadata:
    """Metadata about a memory tier"""
    def __init__(
        self,
        tier_level: TierLevel,
        name: str,
        description: str,
        storage_backends: List[str],
        ttl_seconds: Optional[int] = None,
        capacity_limit: Optional[int] = None
    ):
        self.tier_level = tier_level
        self.name = name
        self.description = description
        self.storage_backends = storage_backends
        self.ttl_seconds = ttl_seconds
        self.capacity_limit = capacity_limit


class HealthReport:
    """Health status report for a tier"""
    def __init__(
        self,
        tier_level: TierLevel,
        overall_status: HealthStatus,
        components: Dict[str, HealthStatus],
        metrics: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.tier_level = tier_level
        self.overall_status = overall_status
        self.components = components
        self.metrics = metrics or {}
        self.errors = errors or []
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'tier_level': self.tier_level.value,
            'overall_status': self.overall_status.value,
            'components': {k: v.value for k, v in self.components.items()},
            'metrics': self.metrics,
            'errors': self.errors,
            'timestamp': self.timestamp.isoformat()
        }


class QueryOptions:
    """Options for querying a memory tier"""
    def __init__(
        self,
        limit: int = 10,
        offset: int = 0,
        include_metadata: bool = True,
        include_scores: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ):
        self.limit = limit
        self.offset = offset
        self.include_metadata = include_metadata
        self.include_scores = include_scores
        self.filters = filters or {}
        self.sort_by = sort_by
        self.sort_order = sort_order


# ============================================================================
# Base Tier Interface
# ============================================================================

class BaseTier(ABC):
    """
    Abstract base class for all memory tier implementations.
    
    All tier classes (L1-L4) must inherit from this interface and implement
    all abstract methods. This ensures a uniform API across all tiers.
    
    Design Principles:
    - Each tier is self-contained and manages its own storage adapters
    - Tiers expose async methods for I/O operations
    - Health checks are mandatory for observability
    - Metrics collection is built-in
    - Error handling follows graceful degradation pattern
    """

    def __init__(self, tier_metadata: TierMetadata):
        """
        Initialize base tier.
        
        Args:
            tier_metadata: Metadata describing this tier
        """
        self.metadata = tier_metadata
        self.logger = logging.getLogger(f"{__name__}.{tier_metadata.name}")
        self._connected = False
        
        # Metrics will be initialized by subclasses
        self.metrics = None

    # ========================================================================
    # Connection Lifecycle (MANDATORY)
    # ========================================================================

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connections to all storage backends.
        
        Must be called before any other operations.
        Should be idempotent (safe to call multiple times).
        
        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close all storage backend connections.
        
        Should be called during shutdown.
        Should be idempotent and never raise exceptions.
        """
        pass

    @abstractmethod
    async def health(self) -> HealthReport:
        """
        Check health status of this tier and all storage backends.
        
        Returns:
            HealthReport with status of all components
            
        Example:
            report = await tier.health()
            if report.overall_status != HealthStatus.HEALTHY:
                logger.warning(f"Tier unhealthy: {report.errors}")
        """
        pass

    # ========================================================================
    # Core CRUD Operations (MANDATORY)
    # ========================================================================

    @abstractmethod
    async def store(
        self, 
        session_id: str, 
        data: Dict[str, Any],
        **kwargs
    ) -> str:
        """
        Store data in this tier.
        
        Args:
            session_id: Session identifier for scoping
            data: Data to store (structure varies by tier)
            **kwargs: Tier-specific options
            
        Returns:
            Unique identifier for the stored data
            
        Raises:
            ValueError: If data is invalid
            StorageError: If storage operation fails
            
        Example:
            item_id = await tier.store(
                session_id="session-123",
                data={"content": "User prefers Hamburg", "type": "preference"}
            )
        """
        pass

    @abstractmethod
    async def retrieve(
        self, 
        session_id: str, 
        item_id: Optional[str] = None,
        options: Optional[QueryOptions] = None
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Retrieve data from this tier.
        
        Args:
            session_id: Session identifier for scoping
            item_id: Specific item ID to retrieve (None = all for session)
            options: Query options (limit, filters, etc.)
            
        Returns:
            Single item if item_id provided, otherwise list of items
            
        Raises:
            NotFoundError: If item_id specified but not found
            StorageError: If retrieval fails
            
        Example:
            # Get all items for session
            items = await tier.retrieve(session_id="session-123")
            
            # Get specific item
            item = await tier.retrieve(
                session_id="session-123", 
                item_id="item-456"
            )
            
            # Get filtered items
            items = await tier.retrieve(
                session_id="session-123",
                options=QueryOptions(limit=5, filters={"type": "preference"})
            )
        """
        pass

    @abstractmethod
    async def update(
        self, 
        session_id: str, 
        item_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update existing data in this tier.
        
        Args:
            session_id: Session identifier for scoping
            item_id: Unique identifier of item to update
            updates: Fields to update (partial update supported)
            
        Returns:
            True if updated, False if item not found
            
        Raises:
            StorageError: If update fails
            
        Example:
            success = await tier.update(
                session_id="session-123",
                item_id="item-456",
                updates={"confidence": 0.95, "last_accessed_at": datetime.utcnow()}
            )
        """
        pass

    @abstractmethod
    async def delete(
        self, 
        session_id: str, 
        item_id: Optional[str] = None
    ) -> int:
        """
        Delete data from this tier.
        
        Args:
            session_id: Session identifier for scoping
            item_id: Specific item to delete (None = all for session)
            
        Returns:
            Number of items deleted
            
        Raises:
            StorageError: If deletion fails
            
        Example:
            # Delete specific item
            count = await tier.delete(session_id="session-123", item_id="item-456")
            
            # Delete all items for session
            count = await tier.delete(session_id="session-123")
        """
        pass

    # ========================================================================
    # Tier-Specific Search (OPTIONAL - override if tier supports search)
    # ========================================================================

    async def search(
        self, 
        query: str, 
        session_id: Optional[str] = None,
        options: Optional[QueryOptions] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for data in this tier.
        
        Not all tiers support search. Override in subclasses that do.
        
        Args:
            query: Search query (format varies by tier)
            session_id: Optional session scoping
            options: Query options
            
        Returns:
            List of matching items
            
        Raises:
            NotImplementedError: If tier doesn't support search
            
        Example:
            # L3 semantic search
            results = await l3_tier.search(
                query="Hamburg port preferences",
                options=QueryOptions(limit=5)
            )
        """
        raise NotImplementedError(f"{self.metadata.name} does not support search")

    # ========================================================================
    # Lifecycle Management (OPTIONAL - override if tier participates)
    # ========================================================================

    async def get_promotion_candidates(
        self, 
        session_id: str,
        threshold: float = 0.70
    ) -> List[Dict[str, Any]]:
        """
        Get items eligible for promotion to next tier.
        
        Override in tiers that support promotion (L1, L2, L3).
        
        Args:
            session_id: Session identifier
            threshold: CIAR score threshold for promotion
            
        Returns:
            List of items ready for promotion
            
        Example:
            candidates = await l1_tier.get_promotion_candidates(
                session_id="session-123",
                threshold=0.70
            )
        """
        raise NotImplementedError(f"{self.metadata.name} does not support promotion")

    async def mark_promoted(
        self, 
        session_id: str, 
        item_id: str, 
        target_tier: TierLevel
    ) -> bool:
        """
        Mark an item as promoted to the next tier.
        
        Args:
            session_id: Session identifier
            item_id: Item that was promoted
            target_tier: Tier it was promoted to
            
        Returns:
            True if marked successfully
        """
        raise NotImplementedError(f"{self.metadata.name} does not support promotion marking")

    # ========================================================================
    # TTL Management (OPTIONAL - override if tier uses TTL)
    # ========================================================================

    async def cleanup_expired(self, batch_size: int = 100) -> int:
        """
        Remove expired items based on TTL.
        
        Override in tiers that use TTL (L1, L2).
        
        Args:
            batch_size: Number of items to clean per batch
            
        Returns:
            Number of items cleaned up
            
        Example:
            # Background task
            while True:
                cleaned = await tier.cleanup_expired()
                await asyncio.sleep(60)  # Clean every minute
        """
        raise NotImplementedError(f"{self.metadata.name} does not support TTL cleanup")

    # ========================================================================
    # Utility Methods (PROVIDED - common to all tiers)
    # ========================================================================

    def is_connected(self) -> bool:
        """Check if tier is connected to storage backends"""
        return self._connected

    def get_metadata(self) -> TierMetadata:
        """Get tier metadata"""
        return self.metadata

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"tier={self.metadata.tier_level.value} "
            f"connected={self._connected}>"
        )


# ============================================================================
# Exceptions
# ============================================================================

class TierError(Exception):
    """Base exception for tier operations"""
    pass


class ConnectionError(TierError):
    """Raised when connection to storage fails"""
    pass


class StorageError(TierError):
    """Raised when storage operation fails"""
    pass


class NotFoundError(TierError):
    """Raised when requested item not found"""
    pass


class ValidationError(TierError):
    """Raised when data validation fails"""
    pass
```

---

### Design Considerations

#### 1. **Interface Completeness vs. Flexibility**

**Decision**: Define a comprehensive interface with both mandatory and optional methods.

**Rationale**:
- **Mandatory methods** (`connect`, `disconnect`, `health`, `store`, `retrieve`, `update`, `delete`): Every tier must implement these for the orchestrator to function.
- **Optional methods** (`search`, `get_promotion_candidates`, `cleanup_expired`): Not all tiers need these capabilities.

**Implementation Pattern**:
```python
# Mandatory - all tiers must implement
@abstractmethod
async def store(self, session_id: str, data: Dict[str, Any]) -> str:
    pass

# Optional - raise NotImplementedError if not supported
async def search(self, query: str) -> List[Dict[str, Any]]:
    raise NotImplementedError(f"{self.metadata.name} does not support search")
```

**Benefits**:
- Clear contract for essential operations
- Flexibility for tier-specific features
- Orchestrator can check `hasattr()` or catch `NotImplementedError` for optional features

---

#### 2. **Async-First Design**

**Decision**: All I/O methods are async (use `async def`).

**Rationale**:
- Storage operations involve network I/O (Redis, PostgreSQL, Qdrant, Neo4j)
- Async enables non-blocking concurrent operations
- Better resource utilization under load

**Example Usage**:
```python
# Orchestrator can parallelize tier queries
async def get_context(self, session_id: str):
    # Run L1 and L2 queries concurrently
    l1_data, l2_data = await asyncio.gather(
        self.l1.retrieve(session_id),
        self.l2.retrieve(session_id)
    )
    return MemoryContext(active=l1_data, facts=l2_data)
```

**Trade-off**: Increases code complexity (async/await syntax), but essential for performance.

---

#### 3. **Health Checks as First-Class Citizens**

**Decision**: Every tier must implement `health()` method returning structured `HealthReport`.

**Rationale**:
- Enables proactive monitoring and alerting
- Supports graceful degradation (orchestrator can skip unhealthy tiers)
- Provides debugging information during failures

**Health Check Implementation Example**:
```python
async def health(self) -> HealthReport:
    components = {}
    errors = []
    
    # Check Redis
    try:
        await self.redis.client.ping()
        components['redis'] = HealthStatus.HEALTHY
    except Exception as e:
        components['redis'] = HealthStatus.UNHEALTHY
        errors.append(f"Redis error: {e}")
    
    # Check PostgreSQL
    try:
        await self.postgres.pool.fetchval('SELECT 1')
        components['postgresql'] = HealthStatus.HEALTHY
    except Exception as e:
        components['postgresql'] = HealthStatus.UNHEALTHY
        errors.append(f"PostgreSQL error: {e}")
    
    # Determine overall status
    if all(s == HealthStatus.HEALTHY for s in components.values()):
        overall = HealthStatus.HEALTHY
    elif any(s == HealthStatus.UNHEALTHY for s in components.values()):
        overall = HealthStatus.DEGRADED
    else:
        overall = HealthStatus.UNHEALTHY
    
    return HealthReport(
        tier_level=self.metadata.tier_level,
        overall_status=overall,
        components=components,
        errors=errors
    )
```

---

#### 4. **Session-Scoped Operations**

**Decision**: All CRUD operations require `session_id` parameter.

**Rationale**:
- Memory is inherently session-scoped (conversations happen in sessions)
- Prevents accidental cross-session data leakage
- Enables efficient session-based cleanup and queries

**Pattern**:
```python
# Always scope by session
await tier.store(session_id="abc-123", data={...})
await tier.retrieve(session_id="abc-123")

# Session ID is part of every query
await tier.search(query="Hamburg", session_id="abc-123")
```

**Exception**: L4 (Semantic Memory) may have session-agnostic knowledge, but still accepts `session_id` for provenance tracking.

---

#### 5. **Type Hints for Safety**

**Decision**: Use comprehensive type hints with `typing` module.

**Benefits**:
- Compile-time type checking with mypy
- Better IDE autocomplete and inline documentation
- Catches type errors early

**Example**:
```python
from typing import Dict, List, Any, Optional, Union

async def retrieve(
    self, 
    session_id: str,  # Required string
    item_id: Optional[str] = None,  # Optional string
    options: Optional[QueryOptions] = None  # Optional custom type
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:  # Returns dict or list
    pass
```

**Trade-off**: More verbose code, but significantly improves maintainability.

---

#### 6. **Metadata-Driven Configuration**

**Decision**: Each tier is initialized with `TierMetadata` describing its characteristics.

**Rationale**:
- Centralizes tier configuration
- Enables runtime introspection (orchestrator can query tier capabilities)
- Supports dynamic tier registration

**Example**:
```python
# L1 initialization
l1_metadata = TierMetadata(
    tier_level=TierLevel.L1_ACTIVE_CONTEXT,
    name="ActiveContextTier",
    description="Recent conversation turns",
    storage_backends=["Redis", "PostgreSQL"],
    ttl_seconds=86400,  # 24 hours
    capacity_limit=20   # Max 20 turns
)

l1_tier = ActiveContextTier(
    metadata=l1_metadata,
    redis=redis_adapter,
    postgres=postgres_adapter
)

# Orchestrator can query
if l1_tier.metadata.ttl_seconds:
    print(f"L1 has TTL: {l1_tier.metadata.ttl_seconds}s")
```

---

#### 7. **Error Handling Strategy**

**Decision**: Define custom exception hierarchy rooted at `TierError`.

**Exception Types**:
- `ConnectionError`: Storage backend connection failed
- `StorageError`: Read/write operation failed
- `NotFoundError`: Requested item doesn't exist
- `ValidationError`: Data failed validation

**Usage Pattern**:
```python
from src.memory.base_tier import NotFoundError, StorageError

try:
    item = await tier.retrieve(session_id="abc", item_id="123")
except NotFoundError:
    # Handle missing item gracefully
    logger.warning("Item not found, using default")
    item = default_item
except StorageError as e:
    # Storage issue - may need to retry or degrade
    logger.error(f"Storage error: {e}")
    self.metrics.record('tier_storage_error')
    raise
```

**Benefits**:
- Callers can distinguish error types
- Enables targeted error handling (retry on `StorageError`, return empty on `NotFoundError`)
- Supports graceful degradation pattern

---

#### 8. **QueryOptions Pattern**

**Decision**: Use structured `QueryOptions` object instead of many keyword arguments.

**Benefits**:
- Cleaner method signatures
- Easy to extend with new options
- Provides defaults for common use cases

**Example**:
```python
# Instead of this (unreadable):
await tier.retrieve(
    session_id="abc", 
    limit=10, 
    offset=0, 
    include_metadata=True,
    include_scores=False,
    filters={"type": "preference"},
    sort_by="confidence",
    sort_order="desc"
)

# Use this (clean):
options = QueryOptions(
    limit=10,
    filters={"type": "preference"},
    sort_by="confidence"
)
await tier.retrieve(session_id="abc", options=options)
```

---

#### 9. **Idempotency Guarantees**

**Decision**: `connect()` and `disconnect()` must be idempotent.

**Rationale**:
- Safe to call multiple times without side effects
- Simplifies error recovery (can retry connection)
- Prevents resource leaks

**Implementation Pattern**:
```python
async def connect(self) -> None:
    if self._connected:
        self.logger.debug("Already connected, skipping")
        return
    
    # Establish connections
    await self.redis.connect()
    await self.postgres.connect()
    
    self._connected = True
    self.logger.info("Connected successfully")

async def disconnect(self) -> None:
    if not self._connected:
        return
    
    # Close connections (never raise)
    try:
        await self.redis.disconnect()
    except Exception as e:
        self.logger.warning(f"Error disconnecting Redis: {e}")
    
    try:
        await self.postgres.disconnect()
    except Exception as e:
        self.logger.warning(f"Error disconnecting PostgreSQL: {e}")
    
    self._connected = False
```

---

#### 10. **Testing Strategy for Base Interface**

**Approach**: Use abstract test class that validates interface compliance.

```python
# tests/memory/test_base_tier_interface.py
import pytest
from abc import ABC
from src.memory.base_tier import BaseTier, TierMetadata, TierLevel

class BaseTierInterfaceTest(ABC):
    """
    Abstract test class that validates any BaseTier implementation.
    
    All tier test classes should inherit from this to ensure compliance.
    """
    
    @pytest.fixture
    @abstractmethod
    def tier(self):
        """Subclasses must provide a tier instance"""
        pass
    
    @pytest.mark.asyncio
    async def test_connect_is_idempotent(self, tier):
        """Verify connect() can be called multiple times"""
        await tier.connect()
        await tier.connect()  # Should not raise
        assert tier.is_connected()
    
    @pytest.mark.asyncio
    async def test_health_returns_valid_report(self, tier):
        """Verify health() returns HealthReport"""
        await tier.connect()
        report = await tier.health()
        assert report.tier_level == tier.metadata.tier_level
        assert report.overall_status is not None
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, tier):
        """Verify basic store/retrieve cycle"""
        await tier.connect()
        
        item_id = await tier.store(
            session_id="test-session",
            data={"content": "test"}
        )
        
        retrieved = await tier.retrieve(
            session_id="test-session",
            item_id=item_id
        )
        
        assert retrieved['content'] == "test"
    
    # ... more interface tests

# tests/memory/test_active_context_tier.py
class TestActiveContextTier(BaseTierInterfaceTest):
    """L1 tier tests - inherits interface compliance tests"""
    
    @pytest.fixture
    def tier(self, mock_redis, mock_postgres):
        metadata = TierMetadata(
            tier_level=TierLevel.L1_ACTIVE_CONTEXT,
            name="ActiveContextTier",
            storage_backends=["Redis", "PostgreSQL"],
            ttl_seconds=86400
        )
        return ActiveContextTier(
            metadata=metadata,
            redis=mock_redis,
            postgres=mock_postgres
        )
    
    # Tier-specific tests here
```

**Benefits**:
- All tiers automatically tested for interface compliance
- Prevents regressions when modifying interface
- Ensures polymorphism works correctly

---

### Implementation Checklist

**File Creation**:
- [ ] Create `src/memory/__init__.py` (package init)
- [ ] Create `src/memory/base_tier.py` with full interface definition
- [ ] Create `tests/memory/test_base_tier_interface.py` with abstract test class

**Code Quality**:
- [ ] All abstract methods have docstrings
- [ ] Type hints on all method signatures
- [ ] Custom exceptions defined
- [ ] Enums for tier levels, health status, lifecycle stages

**Documentation**:
- [ ] Interface docstrings explain purpose of each method
- [ ] Examples provided in docstrings
- [ ] Design rationale documented (this section)

**Validation**:
- [ ] Code passes mypy type checking
- [ ] Abstract test class validates interface contract
- [ ] Linting passes (flake8, black)

---

### Next Steps

After completing Priority 1:

1. **Priority 2**: Implement `ActiveContextTier` (L1) using this interface
2. **Priority 3**: Implement `WorkingMemoryTier` (L2) using this interface
3. **Validate**: Each tier implementation passes `BaseTierInterfaceTest`
4. **Refine**: Adjust interface based on implementation learnings

**Success Criteria**:
- ✅ `BaseTier` abstract class defined
- ✅ All mandatory methods declared with `@abstractmethod`
- ✅ Optional methods have default `NotImplementedError` implementations
- ✅ Type hints comprehensive
- ✅ Custom exceptions defined
- ✅ Abstract test class created
- ✅ Documentation complete

---

## Priority 2: L1 - Active Context Tier

**Estimated Time**: 4-5 hours  
**Status**: Not Started  
**Dependencies**: Priority 1

### Objective

Implement the **Active Context Tier (L1)** which manages the recent conversation window - the most immediately relevant information for ongoing interactions. L1 serves as:

1. **Fast Access Layer**: Sub-millisecond retrieval of recent conversation turns via Redis
2. **Conversation Window Manager**: Maintains sliding window of 10-20 most recent turns
3. **Durability Guarantee**: PostgreSQL backup ensures no data loss on Redis failure
4. **Promotion Source**: Identifies high-value turns for promotion to L2 (Working Memory)

**Key Design Goals**:
- Prioritize read latency (<0.1ms for cache hits)
- Graceful degradation (Redis → PostgreSQL fallback)
- Automatic window management (FIFO eviction)
- TTL-based cleanup (24-hour expiration)
- CIAR scoring for promotion candidates

---

### Tier Characteristics

| Characteristic | Value | Rationale |
|----------------|-------|-----------|
| **Storage** | Redis (primary) + PostgreSQL (backup) | Redis for speed, PostgreSQL for durability |
| **Window Size** | 10-20 recent turns | Balances context richness with noise reduction |
| **TTL** | 24 hours | Long enough for same-day recall, short enough to prevent bloat |
| **Performance Target** | <0.1ms for Redis reads | Near-instant context retrieval for real-time agents |
| **Cache Hit Rate Target** | >95% | Most requests should hit Redis cache |
| **Fallback Latency** | <5ms for PostgreSQL | Acceptable degradation when Redis unavailable |
| **Data Structure** | Ordered list (FIFO queue) | Maintains temporal order of conversation |

---

### Implementation Requirements

#### File: `src/memory/active_context_tier.py`

```python
"""
Active Context Tier (L1) - Recent conversation window management

This tier maintains the most recent 10-20 conversation turns in a sliding window,
with Redis as primary storage for fast access and PostgreSQL as backup for durability.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

from src.memory.base_tier import (
    BaseTier,
    TierMetadata,
    TierLevel,
    HealthStatus,
    HealthReport,
    QueryOptions,
    LifecycleStage,
    ConnectionError,
    StorageError,
    NotFoundError,
    ValidationError
)
from src.storage.redis_adapter import RedisAdapter
from src.storage.postgres_adapter import PostgresAdapter
from src.utils.metrics import MetricsCollector


# ============================================================================
# Constants
# ============================================================================

DEFAULT_WINDOW_SIZE = 20
DEFAULT_TTL_SECONDS = 86400  # 24 hours
REDIS_KEY_PREFIX = "active_context"
POSTGRES_TABLE = "active_context"

# CIAR scoring weights (for promotion candidates)
CIAR_WEIGHTS = {
    'certainty': 0.3,
    'impact': 0.3,
    'age_factor': 0.2,
    'recency': 0.2
}
PROMOTION_THRESHOLD = 0.70


# ============================================================================
# Data Models
# ============================================================================

class TurnData:
    """Represents a single conversation turn"""
    
    def __init__(
        self,
        turn_id: int,
        session_id: str,
        role: str,  # 'user' or 'assistant'
        content: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        lifecycle_stage: str = "l1_raw",
        ciar_score: Optional[float] = None
    ):
        self.turn_id = turn_id
        self.session_id = session_id
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}
        self.lifecycle_stage = lifecycle_stage
        self.ciar_score = ciar_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'turn_id': self.turn_id,
            'session_id': self.session_id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'lifecycle_stage': self.lifecycle_stage,
            'ciar_score': self.ciar_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TurnData':
        """Create from dictionary"""
        return cls(
            turn_id=data['turn_id'],
            session_id=data['session_id'],
            role=data['role'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {}),
            lifecycle_stage=data.get('lifecycle_stage', 'l1_raw'),
            ciar_score=data.get('ciar_score')
        )


# ============================================================================
# Active Context Tier Implementation
# ============================================================================

class ActiveContextTier(BaseTier):
    """
    L1 (Active Context) tier implementation.
    
    Manages a sliding window of recent conversation turns with:
    - Redis primary storage for fast access
    - PostgreSQL backup for durability
    - Automatic window size management
    - TTL-based expiration
    - CIAR scoring for promotion candidates
    """
    
    def __init__(
        self,
        redis: RedisAdapter,
        postgres: PostgresAdapter,
        window_size: int = DEFAULT_WINDOW_SIZE,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        metadata: Optional[TierMetadata] = None
    ):
        """
        Initialize Active Context Tier.
        
        Args:
            redis: Redis adapter for primary storage
            postgres: PostgreSQL adapter for backup storage
            window_size: Maximum number of turns to keep in window
            ttl_seconds: Time-to-live for turns (seconds)
            metadata: Tier metadata (auto-generated if None)
        """
        # Create metadata if not provided
        if metadata is None:
            metadata = TierMetadata(
                tier_level=TierLevel.L1_ACTIVE_CONTEXT,
                name="ActiveContextTier",
                description="Recent conversation window (L1)",
                storage_backends=["Redis", "PostgreSQL"],
                ttl_seconds=ttl_seconds,
                capacity_limit=window_size
            )
        
        super().__init__(metadata)
        
        # Storage adapters
        self.redis = redis
        self.postgres = postgres
        
        # Configuration
        self.window_size = window_size
        self.ttl_seconds = ttl_seconds
        
        # Metrics
        self.metrics = MetricsCollector(component="active_context_tier")
        
        # Internal state
        self._redis_available = False
    
    # ========================================================================
    # Connection Lifecycle
    # ========================================================================
    
    async def connect(self) -> None:
        """Establish connections to Redis and PostgreSQL"""
        if self._connected:
            self.logger.debug("Already connected, skipping")
            return
        
        try:
            # Connect to Redis
            await self.redis.connect()
            self._redis_available = True
            self.logger.info("Redis connected")
        except Exception as e:
            self.logger.warning(f"Redis connection failed: {e}")
            self._redis_available = False
        
        try:
            # Connect to PostgreSQL
            await self.postgres.connect()
            self.logger.info("PostgreSQL connected")
        except Exception as e:
            self.logger.error(f"PostgreSQL connection failed: {e}")
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")
        
        self._connected = True
        self.logger.info(f"Active Context Tier connected (Redis: {self._redis_available})")
    
    async def disconnect(self) -> None:
        """Close connections to Redis and PostgreSQL"""
        if not self._connected:
            return
        
        # Disconnect Redis (never raise)
        try:
            await self.redis.disconnect()
        except Exception as e:
            self.logger.warning(f"Error disconnecting Redis: {e}")
        
        # Disconnect PostgreSQL (never raise)
        try:
            await self.postgres.disconnect()
        except Exception as e:
            self.logger.warning(f"Error disconnecting PostgreSQL: {e}")
        
        self._connected = False
        self._redis_available = False
        self.logger.info("Active Context Tier disconnected")
    
    async def health(self) -> HealthReport:
        """Check health of Redis and PostgreSQL"""
        components = {}
        errors = []
        
        # Check Redis
        try:
            await self.redis.health()
            components['redis'] = HealthStatus.HEALTHY
            self._redis_available = True
        except Exception as e:
            components['redis'] = HealthStatus.UNHEALTHY
            errors.append(f"Redis unhealthy: {e}")
            self._redis_available = False
        
        # Check PostgreSQL
        try:
            await self.postgres.health()
            components['postgresql'] = HealthStatus.HEALTHY
        except Exception as e:
            components['postgresql'] = HealthStatus.UNHEALTHY
            errors.append(f"PostgreSQL unhealthy: {e}")
        
        # Determine overall status
        if all(s == HealthStatus.HEALTHY for s in components.values()):
            overall = HealthStatus.HEALTHY
        elif components.get('postgresql') == HealthStatus.UNHEALTHY:
            overall = HealthStatus.UNHEALTHY  # PostgreSQL is critical
        else:
            overall = HealthStatus.DEGRADED  # Redis down but PostgreSQL up
        
        return HealthReport(
            tier_level=self.metadata.tier_level,
            overall_status=overall,
            components=components,
            metrics={
                'redis_available': self._redis_available,
                'window_size': self.window_size,
                'ttl_seconds': self.ttl_seconds
            },
            errors=errors
        )
    
    # ========================================================================
    # Core CRUD Operations
    # ========================================================================
    
    async def store(
        self,
        session_id: str,
        data: Dict[str, Any],
        **kwargs
    ) -> str:
        """
        Store a new turn in active context.
        
        Args:
            session_id: Session identifier
            data: Turn data (must include turn_id, role, content)
            **kwargs: Additional options
            
        Returns:
            Turn ID as string
            
        Raises:
            ValidationError: If required fields missing
            StorageError: If storage fails
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate required fields
            required = ['turn_id', 'role', 'content']
            missing = [f for f in required if f not in data]
            if missing:
                raise ValidationError(f"Missing required fields: {missing}")
            
            # Create TurnData object
            turn = TurnData(
                turn_id=data['turn_id'],
                session_id=session_id,
                role=data['role'],
                content=data['content'],
                metadata=data.get('metadata', {}),
                timestamp=data.get('timestamp')
            )
            
            # Store in PostgreSQL first (durability)
            await self._store_postgres(turn)
            
            # Store in Redis (performance)
            if self._redis_available:
                await self._store_redis(turn)
            
            # Enforce window size limit
            await self._enforce_window_size(session_id)
            
            # Record metrics
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self.metrics.record('l1.store.success', 1)
            self.metrics.record('l1.store.latency_ms', duration_ms)
            
            self.logger.debug(
                f"Stored turn {turn.turn_id} for session {session_id} "
                f"(duration: {duration_ms:.2f}ms)"
            )
            
            return str(turn.turn_id)
            
        except ValidationError:
            self.metrics.record('l1.store.validation_error', 1)
            raise
        except Exception as e:
            self.metrics.record('l1.store.error', 1)
            self.logger.error(f"Failed to store turn: {e}")
            raise StorageError(f"Failed to store turn: {e}")
    
    async def retrieve(
        self,
        session_id: str,
        item_id: Optional[str] = None,
        options: Optional[QueryOptions] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve turns from active context.
        
        Args:
            session_id: Session identifier
            item_id: Specific turn_id to retrieve (None = all in window)
            options: Query options
            
        Returns:
            List of turn dictionaries (or single item list if item_id provided)
            
        Raises:
            NotFoundError: If item_id specified but not found
            StorageError: If retrieval fails
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Try Redis first (fast path)
            if self._redis_available:
                try:
                    result = await self._retrieve_redis(session_id, item_id, options)
                    
                    # Record cache hit
                    duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                    self.metrics.record('l1.retrieve.cache_hit', 1)
                    self.metrics.record('l1.retrieve.latency_ms', duration_ms)
                    
                    return result
                    
                except Exception as e:
                    self.logger.warning(f"Redis retrieval failed: {e}, falling back to PostgreSQL")
                    self.metrics.record('l1.retrieve.cache_miss', 1)
            
            # Fallback to PostgreSQL
            result = await self._retrieve_postgres(session_id, item_id, options)
            
            # Record fallback
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self.metrics.record('l1.retrieve.postgres_fallback', 1)
            self.metrics.record('l1.retrieve.latency_ms', duration_ms)
            
            # Repopulate Redis cache if available
            if self._redis_available and result:
                asyncio.create_task(self._repopulate_cache(session_id, result))
            
            return result
            
        except NotFoundError:
            self.metrics.record('l1.retrieve.not_found', 1)
            raise
        except Exception as e:
            self.metrics.record('l1.retrieve.error', 1)
            self.logger.error(f"Failed to retrieve turns: {e}")
            raise StorageError(f"Failed to retrieve turns: {e}")
    
    async def update(
        self,
        session_id: str,
        item_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update a turn in active context.
        
        Args:
            session_id: Session identifier
            item_id: Turn ID to update
            updates: Fields to update (e.g., lifecycle_stage, ciar_score)
            
        Returns:
            True if updated, False if not found
        """
        try:
            # Update PostgreSQL
            pg_updated = await self._update_postgres(session_id, item_id, updates)
            
            if not pg_updated:
                return False
            
            # Update Redis if available
            if self._redis_available:
                await self._update_redis(session_id, item_id, updates)
            
            self.metrics.record('l1.update.success', 1)
            return True
            
        except Exception as e:
            self.metrics.record('l1.update.error', 1)
            self.logger.error(f"Failed to update turn {item_id}: {e}")
            raise StorageError(f"Failed to update turn: {e}")
    
    async def delete(
        self,
        session_id: str,
        item_id: Optional[str] = None
    ) -> int:
        """
        Delete turn(s) from active context.
        
        Args:
            session_id: Session identifier
            item_id: Specific turn to delete (None = all for session)
            
        Returns:
            Number of turns deleted
        """
        try:
            # Delete from PostgreSQL
            pg_count = await self._delete_postgres(session_id, item_id)
            
            # Delete from Redis
            if self._redis_available:
                await self._delete_redis(session_id, item_id)
            
            self.metrics.record('l1.delete.success', 1)
            self.metrics.record('l1.delete.count', pg_count)
            
            return pg_count
            
        except Exception as e:
            self.metrics.record('l1.delete.error', 1)
            self.logger.error(f"Failed to delete turns: {e}")
            raise StorageError(f"Failed to delete turns: {e}")
    
    # ========================================================================
    # Lifecycle Management
    # ========================================================================
    
    async def get_promotion_candidates(
        self,
        session_id: str,
        threshold: float = PROMOTION_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Get turns eligible for promotion to L2.
        
        Promotion criteria:
        - CIAR score >= threshold (0.70 default)
        - Not yet promoted (promoted_to_l2_at IS NULL)
        - Contains extractable entities or preferences
        
        Args:
            session_id: Session identifier
            threshold: Minimum CIAR score for promotion
            
        Returns:
            List of turn dictionaries ready for promotion
        """
        try:
            # Query PostgreSQL for promotion candidates
            query = f"""
                SELECT * FROM {POSTGRES_TABLE}
                WHERE session_id = $1
                  AND promoted_to_l2_at IS NULL
                  AND (
                      ciar_score >= $2
                      OR lifecycle_stage = 'l2_candidate'
                  )
                ORDER BY ciar_score DESC NULLS LAST, turn_id DESC
            """
            
            rows = await self.postgres.pool.fetch(query, session_id, threshold)
            
            candidates = [dict(row) for row in rows]
            
            self.metrics.record('l1.promotion_candidates.count', len(candidates))
            
            return candidates
            
        except Exception as e:
            self.logger.error(f"Failed to get promotion candidates: {e}")
            raise StorageError(f"Failed to get promotion candidates: {e}")
    
    async def mark_promoted(
        self,
        session_id: str,
        item_id: str,
        target_tier: TierLevel
    ) -> bool:
        """
        Mark a turn as promoted to L2.
        
        Args:
            session_id: Session identifier
            item_id: Turn ID that was promoted
            target_tier: Should be L2
            
        Returns:
            True if marked successfully
        """
        if target_tier != TierLevel.L2_WORKING_MEMORY:
            raise ValueError(f"L1 can only promote to L2, got {target_tier}")
        
        updates = {
            'promoted_to_l2_at': datetime.utcnow(),
            'lifecycle_stage': 'l2_candidate'
        }
        
        return await self.update(session_id, item_id, updates)
    
    # ========================================================================
    # TTL Management
    # ========================================================================
    
    async def cleanup_expired(self, batch_size: int = 100) -> int:
        """
        Remove expired turns based on TTL.
        
        Args:
            batch_size: Number of turns to clean per batch
            
        Returns:
            Number of turns deleted
        """
        try:
            # Calculate expiration cutoff
            cutoff = datetime.utcnow() - timedelta(seconds=self.ttl_seconds)
            
            # Delete from PostgreSQL
            query = f"""
                DELETE FROM {POSTGRES_TABLE}
                WHERE timestamp < $1
                  AND ctid IN (
                      SELECT ctid FROM {POSTGRES_TABLE}
                      WHERE timestamp < $1
                      LIMIT $2
                  )
                RETURNING session_id, turn_id
            """
            
            deleted = await self.postgres.pool.fetch(query, cutoff, batch_size)
            count = len(deleted)
            
            # Delete from Redis (if available)
            if self._redis_available and deleted:
                for row in deleted:
                    try:
                        await self._delete_redis(row['session_id'], str(row['turn_id']))
                    except Exception as e:
                        self.logger.warning(f"Failed to delete from Redis: {e}")
            
            self.metrics.record('l1.cleanup.expired_count', count)
            self.logger.info(f"Cleaned up {count} expired turns")
            
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired turns: {e}")
            raise StorageError(f"Failed to cleanup expired: {e}")
    
    # ========================================================================
    # Private Helper Methods - Redis Operations
    # ========================================================================
    
    async def _store_redis(self, turn: TurnData) -> None:
        """Store turn in Redis"""
        key = self._redis_key(turn.session_id)
        
        # Add to sorted set (sorted by turn_id)
        await self.redis.client.zadd(
            key,
            {json.dumps(turn.to_dict()): turn.turn_id}
        )
        
        # Set TTL on key
        await self.redis.client.expire(key, self.ttl_seconds)
    
    async def _retrieve_redis(
        self,
        session_id: str,
        item_id: Optional[str] = None,
        options: Optional[QueryOptions] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve turns from Redis"""
        key = self._redis_key(session_id)
        
        if item_id:
            # Get specific turn
            members = await self.redis.client.zrangebyscore(
                key, int(item_id), int(item_id)
            )
            if not members:
                raise NotFoundError(f"Turn {item_id} not found in session {session_id}")
            result = [json.loads(members[0])]
        else:
            # Get all turns in window (most recent first)
            limit = options.limit if options else self.window_size
            members = await self.redis.client.zrevrange(key, 0, limit - 1)
            result = [json.loads(m) for m in members]
        
        return result
    
    async def _update_redis(
        self,
        session_id: str,
        item_id: str,
        updates: Dict[str, Any]
    ) -> None:
        """Update turn in Redis"""
        # Get current turn
        turns = await self._retrieve_redis(session_id, item_id)
        if not turns:
            return
        
        turn_data = turns[0]
        turn_data.update(updates)
        
        # Re-store with updates
        key = self._redis_key(session_id)
        await self.redis.client.zadd(
            key,
            {json.dumps(turn_data): int(item_id)}
        )
    
    async def _delete_redis(
        self,
        session_id: str,
        item_id: Optional[str] = None
    ) -> None:
        """Delete turn(s) from Redis"""
        key = self._redis_key(session_id)
        
        if item_id:
            # Delete specific turn
            await self.redis.client.zremrangebyscore(key, int(item_id), int(item_id))
        else:
            # Delete all for session
            await self.redis.client.delete(key)
    
    def _redis_key(self, session_id: str) -> str:
        """Generate Redis key for session"""
        return f"{REDIS_KEY_PREFIX}:{session_id}"
    
    # ========================================================================
    # Private Helper Methods - PostgreSQL Operations
    # ========================================================================
    
    async def _store_postgres(self, turn: TurnData) -> None:
        """Store turn in PostgreSQL"""
        query = f"""
            INSERT INTO {POSTGRES_TABLE} (
                turn_id, session_id, role, content, timestamp,
                metadata, lifecycle_stage, ciar_score
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (session_id, turn_id)
            DO UPDATE SET
                content = EXCLUDED.content,
                metadata = EXCLUDED.metadata,
                lifecycle_stage = EXCLUDED.lifecycle_stage,
                ciar_score = EXCLUDED.ciar_score
        """
        
        await self.postgres.pool.execute(
            query,
            turn.turn_id,
            turn.session_id,
            turn.role,
            turn.content,
            turn.timestamp,
            json.dumps(turn.metadata),
            turn.lifecycle_stage,
            turn.ciar_score
        )
    
    async def _retrieve_postgres(
        self,
        session_id: str,
        item_id: Optional[str] = None,
        options: Optional[QueryOptions] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve turns from PostgreSQL"""
        if item_id:
            query = f"""
                SELECT * FROM {POSTGRES_TABLE}
                WHERE session_id = $1 AND turn_id = $2
            """
            rows = await self.postgres.pool.fetch(query, session_id, int(item_id))
            
            if not rows:
                raise NotFoundError(f"Turn {item_id} not found in session {session_id}")
        else:
            limit = options.limit if options else self.window_size
            query = f"""
                SELECT * FROM {POSTGRES_TABLE}
                WHERE session_id = $1
                ORDER BY turn_id DESC
                LIMIT $2
            """
            rows = await self.postgres.pool.fetch(query, session_id, limit)
        
        return [dict(row) for row in rows]
    
    async def _update_postgres(
        self,
        session_id: str,
        item_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update turn in PostgreSQL"""
        # Build dynamic UPDATE query
        set_clauses = []
        params = [session_id, int(item_id)]
        param_idx = 3
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ${param_idx}")
            params.append(value)
            param_idx += 1
        
        query = f"""
            UPDATE {POSTGRES_TABLE}
            SET {', '.join(set_clauses)}
            WHERE session_id = $1 AND turn_id = $2
        """
        
        result = await self.postgres.pool.execute(query, *params)
        
        # Check if any rows affected
        return result.split()[-1] != '0'
    
    async def _delete_postgres(
        self,
        session_id: str,
        item_id: Optional[str] = None
    ) -> int:
        """Delete turn(s) from PostgreSQL"""
        if item_id:
            query = f"""
                DELETE FROM {POSTGRES_TABLE}
                WHERE session_id = $1 AND turn_id = $2
            """
            result = await self.postgres.pool.execute(query, session_id, int(item_id))
        else:
            query = f"""
                DELETE FROM {POSTGRES_TABLE}
                WHERE session_id = $1
            """
            result = await self.postgres.pool.execute(query, session_id)
        
        # Extract count from result
        return int(result.split()[-1])
    
    # ========================================================================
    # Private Helper Methods - Cache Management
    # ========================================================================
    
    async def _enforce_window_size(self, session_id: str) -> None:
        """Enforce window size limit by removing oldest turns"""
        # Only enforce on PostgreSQL (source of truth)
        query = f"""
            DELETE FROM {POSTGRES_TABLE}
            WHERE session_id = $1
              AND turn_id NOT IN (
                  SELECT turn_id FROM {POSTGRES_TABLE}
                  WHERE session_id = $1
                  ORDER BY turn_id DESC
                  LIMIT $2
              )
        """
        
        await self.postgres.pool.execute(query, session_id, self.window_size)
        
        # Also enforce on Redis
        if self._redis_available:
            key = self._redis_key(session_id)
            # Keep only most recent window_size items
            await self.redis.client.zremrangebyrank(key, 0, -(self.window_size + 1))
    
    async def _repopulate_cache(
        self,
        session_id: str,
        turns: List[Dict[str, Any]]
    ) -> None:
        """Repopulate Redis cache from PostgreSQL data (background task)"""
        try:
            key = self._redis_key(session_id)
            
            # Clear existing cache
            await self.redis.client.delete(key)
            
            # Add all turns
            for turn_dict in turns:
                await self.redis.client.zadd(
                    key,
                    {json.dumps(turn_dict): turn_dict['turn_id']}
                )
            
            # Set TTL
            await self.redis.client.expire(key, self.ttl_seconds)
            
            self.metrics.record('l1.cache.repopulated', 1)
            self.logger.debug(f"Repopulated cache for session {session_id}")
            
        except Exception as e:
            self.logger.warning(f"Failed to repopulate cache: {e}")
```

---

### Key Methods

#### 1. `store(session_id, data)` - Add Turn to Context

**Purpose**: Store a new conversation turn in the active context window.

**Flow**:
```
1. Validate required fields (turn_id, role, content)
2. Create TurnData object
3. Store in PostgreSQL first (durability guarantee)
4. Store in Redis second (performance cache)
5. Enforce window size limit (remove oldest if > 20 turns)
6. Record metrics (latency, success/failure)
```

**Example Usage**:
```python
turn_id = await l1_tier.store(
    session_id="session-abc-123",
    data={
        'turn_id': 42,
        'role': 'user',
        'content': 'What are the shipping rates to Hamburg?',
        'metadata': {'intent': 'query', 'location': 'Hamburg'}
    }
)
```

**Performance**: <5ms (includes PostgreSQL write + Redis write)

---

#### 2. `retrieve(session_id, item_id=None, options=None)` - Get Context

**Purpose**: Retrieve conversation turns from active context.

**Cache Strategy**:
```
1. Try Redis first (fast path, <0.1ms)
   ├─ Cache hit → Return immediately
   └─ Cache miss → Continue to step 2

2. Fallback to PostgreSQL (slower, <5ms)
   ├─ Return data
   └─ Async repopulate Redis cache (background)

3. Record metrics (cache hit rate, latency)
```

**Example Usage**:
```python
# Get all turns in window (most recent first)
turns = await l1_tier.retrieve(session_id="session-abc-123")
# Returns: [turn_42, turn_41, turn_40, ...]

# Get specific turn
turn = await l1_tier.retrieve(
    session_id="session-abc-123",
    item_id="42"
)
# Returns: [turn_42]

# Get limited window
recent_turns = await l1_tier.retrieve(
    session_id="session-abc-123",
    options=QueryOptions(limit=5)
)
# Returns: 5 most recent turns
```

**Performance**: 
- Redis hit: <0.1ms (95% of requests)
- PostgreSQL fallback: <5ms (5% of requests)

---

#### 3. `update(session_id, item_id, updates)` - Update Turn Metadata

**Purpose**: Update lifecycle metadata (CIAR scores, lifecycle stage) on existing turns.

**Example Usage**:
```python
# Mark turn as analyzed with CIAR score
success = await l1_tier.update(
    session_id="session-abc-123",
    item_id="42",
    updates={
        'lifecycle_stage': 'l1_analyzed',
        'ciar_score': 0.78
    }
)
```

**Use Cases**:
- CIAR scoring after turn analysis
- Marking turns as promotion candidates
- Updating lifecycle stage

---

#### 4. `get_promotion_candidates(session_id, threshold=0.70)` - Find High-Value Turns

**Purpose**: Identify turns eligible for promotion to L2 (Working Memory).

**Criteria**:
- CIAR score ≥ 0.70 (default threshold)
- Not yet promoted (`promoted_to_l2_at IS NULL`)
- Contains extractable entities, preferences, or constraints

**Example Usage**:
```python
candidates = await l1_tier.get_promotion_candidates(
    session_id="session-abc-123",
    threshold=0.70
)

# Returns list of turns ready for promotion:
# [
#   {
#     'turn_id': 42,
#     'content': 'I prefer Hamburg port for European shipments',
#     'ciar_score': 0.85,
#     'lifecycle_stage': 'l1_analyzed'
#   },
#   ...
# ]
```

**Integration Point**: Called by Promotion Engine (Priority 6) to find turns to promote.

---

#### 5. `mark_promoted(session_id, item_id, target_tier)` - Track Promotion

**Purpose**: Mark a turn as promoted to L2, preventing duplicate promotions.

**Example Usage**:
```python
# After successfully promoting to L2
await l1_tier.mark_promoted(
    session_id="session-abc-123",
    item_id="42",
    target_tier=TierLevel.L2_WORKING_MEMORY
)

# Updates:
# - promoted_to_l2_at = NOW()
# - lifecycle_stage = 'l2_candidate'
```

---

#### 6. `cleanup_expired(batch_size=100)` - TTL Management

**Purpose**: Remove turns older than 24 hours to prevent unbounded growth.

**Example Usage**:
```python
# Background cleanup task
async def ttl_cleanup_worker():
    while True:
        count = await l1_tier.cleanup_expired(batch_size=100)
        if count > 0:
            logger.info(f"Cleaned up {count} expired turns")
        await asyncio.sleep(3600)  # Run every hour
```

**Batching**: Processes 100 turns at a time to avoid long-running transactions.

---

### Cache Strategy

#### Two-Tier Caching Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Application                         │
└────┬────────────────────────────────────────────┬───────┘
     │                                             │
     │ retrieve()                                  │ store()
     ▼                                             ▼
┌─────────────────────┐                  ┌─────────────────┐
│   Redis (L1 Cache)  │                  │  PostgreSQL     │
│   - Sorted Set      │◄─────sync────────│  (Source of     │
│   - TTL: 24h        │   (repopulate)   │   Truth)        │
│   - <0.1ms reads    │                  │  - Durable      │
└─────────────────────┘                  └─────────────────┘
     │ cache miss                              │
     └──────────────────┐                      │
                        ▼                      ▼
                   Fallback to             Store here
                   PostgreSQL              first
```

#### Cache Coherence Strategy

**Write Path (store)**:
```
1. Write to PostgreSQL first (source of truth)
2. Write to Redis second (best-effort cache)
3. If Redis write fails → Log warning, continue (PostgreSQL has data)
```

**Read Path (retrieve)**:
```
1. Check Redis (fast)
   ├─ Hit → Return immediately (latency: <0.1ms)
   └─ Miss → Go to step 2

2. Query PostgreSQL (fallback)
   ├─ Return data (latency: <5ms)
   └─ Async repopulate Redis (background task)

3. Future reads hit Redis cache
```

**Update Path**:
```
1. Update PostgreSQL
2. Update Redis (invalidate-on-write)
3. Both stay in sync
```

**Delete Path**:
```
1. Delete from PostgreSQL
2. Delete from Redis
3. Cache invalidated
```

#### Cache Invalidation Rules

**When to Invalidate**:
- Turn updated (CIAR score changed, lifecycle stage updated)
- Turn deleted
- Window size exceeded (oldest turns evicted)
- TTL expired (24 hours)

**How to Invalidate**:
- **Lazy Invalidation**: Let TTL expire (24 hours)
- **Active Invalidation**: Delete key on update/delete
- **Cache Warm-up**: Repopulate on PostgreSQL fallback

#### Redis Data Structure Choice

**Sorted Set (`ZSET`)** used for active context:

**Why Sorted Set?**
- Maintains temporal order (sorted by `turn_id`)
- Efficient range queries (`ZREVRANGE` for most recent N turns)
- Automatic deduplication (turn_id as score ensures uniqueness)
- Built-in ranking (`ZRANK` for turn position in window)

**Operations**:
```redis
# Add turn (score = turn_id)
ZADD active_context:session-123 42 '{"turn_id": 42, "content": "..."}'

# Get 10 most recent turns
ZREVRANGE active_context:session-123 0 9

# Get specific turn
ZRANGEBYSCORE active_context:session-123 42 42

# Remove oldest turns (keep only 20)
ZREMRANGEBYRANK active_context:session-123 0 -21

# Set TTL
EXPIRE active_context:session-123 86400
```

#### Cache Hit Rate Optimization

**Target**: >95% cache hit rate

**Strategies**:
1. **Proactive Cache Warming**: Repopulate Redis on miss (background task)
2. **Session Affinity**: Route requests for same session to same worker
3. **TTL Tuning**: 24-hour TTL balances freshness vs. hit rate
4. **Predictive Prefetch**: Pre-load cache when session starts

**Monitoring**:
```python
# Track cache hit rate
cache_hits = self.metrics.get('l1.retrieve.cache_hit')
cache_misses = self.metrics.get('l1.retrieve.cache_miss')
hit_rate = cache_hits / (cache_hits + cache_misses)

if hit_rate < 0.95:
    logger.warning(f"Cache hit rate below target: {hit_rate:.2%}")
```

---

### Design Patterns Used

#### 1. **Write-Through Cache**
- Writes go to both PostgreSQL and Redis
- Ensures cache coherence
- Tolerates Redis failures

#### 2. **Cache-Aside (Lazy Loading)**
- Read from cache first
- On miss, load from database and populate cache
- Reduces cache memory usage

#### 3. **Time-Based Eviction (TTL)**
- Automatic cleanup after 24 hours
- Prevents unbounded growth
- Reduces manual cache management

#### 4. **Circuit Breaker Pattern**
- Redis failures don't crash system
- Automatic fallback to PostgreSQL
- `_redis_available` flag tracks Redis health

#### 5. **Sliding Window**
- FIFO eviction of oldest turns
- Maintains fixed window size (10-20 turns)
- Prevents memory bloat

---

### Error Handling

**Redis Failures**:
```python
# Graceful degradation
if self._redis_available:
    try:
        await self._store_redis(turn)
    except Exception as e:
        self.logger.warning(f"Redis store failed: {e}, continuing with PostgreSQL")
        self._redis_available = False
```

**PostgreSQL Failures**:
```python
# Critical - must raise
try:
    await self._store_postgres(turn)
except Exception as e:
    self.logger.error(f"PostgreSQL store failed: {e}")
    raise StorageError(f"Cannot store turn: {e}")
```

**Validation Errors**:
```python
# Fail fast on invalid data
if 'turn_id' not in data:
    raise ValidationError("Missing required field: turn_id")
```

---

### Testing Strategy

**Unit Tests** (with mocked storage):
```python
@pytest.fixture
def mock_redis():
    return AsyncMock(spec=RedisAdapter)

@pytest.fixture
def mock_postgres():
    return AsyncMock(spec=PostgresAdapter)

@pytest.mark.asyncio
async def test_store_with_redis_failure(l1_tier, mock_redis, mock_postgres):
    """Test graceful degradation when Redis fails"""
    mock_redis.client.zadd.side_effect = ConnectionError("Redis down")
    
    # Should still succeed via PostgreSQL
    turn_id = await l1_tier.store(
        session_id="test",
        data={'turn_id': 1, 'role': 'user', 'content': 'test'}
    )
    
    assert turn_id == "1"
    mock_postgres.pool.execute.assert_called_once()
```

**Integration Tests** (with real storage):
```python
@pytest.mark.integration
async def test_cache_repopulation(real_l1_tier):
    """Test cache repopulates on PostgreSQL fallback"""
    session_id = "test-session"
    
    # Store turn (goes to both Redis + PostgreSQL)
    await real_l1_tier.store(session_id, {'turn_id': 1, 'role': 'user', 'content': 'hi'})
    
    # Clear Redis cache
    await real_l1_tier.redis.client.delete(f"active_context:{session_id}")
    
    # Retrieve (should fallback to PostgreSQL)
    turns = await real_l1_tier.retrieve(session_id)
    assert len(turns) == 1
    
    # Wait for cache repopulation
    await asyncio.sleep(0.1)
    
    # Next read should hit cache
    turns = await real_l1_tier.retrieve(session_id)
    # Verify Redis was used (check metrics)
```

---

### Performance Benchmarks

**Expected Latencies**:
- `store()`: 3-5ms (PostgreSQL write + Redis write)
- `retrieve()` (cache hit): <0.1ms
- `retrieve()` (cache miss): <5ms
- `update()`: 2-4ms
- `cleanup_expired()`: <50ms per 100 turns

**Throughput Targets**:
- 1000+ writes/sec per session
- 10,000+ reads/sec (Redis cache)
- 500+ reads/sec (PostgreSQL fallback)

---

### Success Criteria

- [ ] All `BaseTier` abstract methods implemented
- [ ] Redis primary + PostgreSQL backup functional
- [ ] Cache hit rate >95% in production
- [ ] Read latency <0.1ms for cache hits
- [ ] Window size enforcement works (max 20 turns)
- [ ] TTL cleanup removes expired turns
- [ ] Graceful degradation on Redis failure
- [ ] CIAR scoring integrated
- [ ] Promotion candidates identified correctly
- [ ] Unit tests pass (>80% coverage)
- [ ] Integration tests pass

---

## Priority 3: L2 - Working Memory Tier

**Estimated Time**: 4-5 hours  
**Status**: Not Started  
**Dependencies**: Priority 1

### Objective

Implement the **Working Memory Tier (L2)** which maintains session-scoped structured facts extracted from conversation turns. L2 serves as:

1. **Fact Repository**: Stores structured, typed facts (entities, preferences, constraints, goals, metrics)
2. **Session Context Manager**: Maintains relevant facts for current session (7-day TTL)
3. **Deduplication Engine**: Merges similar/duplicate facts to reduce noise
4. **Consolidation Source**: Identifies high-value facts for promotion to L3 (Episodic Memory)

**Key Design Goals**:
- Structured fact storage with type safety
- Efficient querying by type, confidence, session
- Automatic fact merging and deduplication
- CIAR scoring for consolidation candidates
- Cross-session relevance detection

---

### Tier Characteristics

| Characteristic | Value | Rationale |
|----------------|-------|-----------|
| **Storage** | PostgreSQL only | ACID guarantees, complex queries, JSONB support |
| **Scope** | Session-scoped facts | Relevant to current conversation context |
| **TTL** | 7 days | Balances session continuity with cleanup |
| **Performance Target** | <5ms for indexed queries | Local database, optimized indexes |
| **Fact Types** | 5 types (entity, preference, constraint, goal, metric) | Covers common conversation information |
| **Confidence Range** | 0.0 - 1.0 | Supports uncertain/inferred facts |
| **Deduplication** | Content-based matching | Prevents fact explosion |
| **Data Structure** | Relational rows with JSONB metadata | Flexible yet structured |

---

### Implementation Requirements

#### File: `src/memory/working_memory_tier.py`

```python
"""
Working Memory Tier (L2) - Session-scoped fact management

This tier maintains structured facts extracted from conversation turns, including
entities, preferences, constraints, goals, and metrics. Facts have confidence scores,
provenance tracking, and lifecycle metadata for consolidation to L3.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
import json
import hashlib

from src.memory.base_tier import (
    BaseTier,
    TierMetadata,
    TierLevel,
    HealthStatus,
    HealthReport,
    QueryOptions,
    LifecycleStage,
    ConnectionError,
    StorageError,
    NotFoundError,
    ValidationError
)
from src.storage.postgres_adapter import PostgresAdapter
from src.utils.metrics import MetricsCollector


# ============================================================================
# Constants
# ============================================================================

POSTGRES_TABLE = "working_memory"
LIFECYCLE_EVENTS_TABLE = "lifecycle_events"
DEFAULT_TTL_DAYS = 7
DEFAULT_CONFIDENCE = 0.85
CONSOLIDATION_THRESHOLD = 0.80
DEDUPLICATION_SIMILARITY_THRESHOLD = 0.90


# ============================================================================
# Enums and Type Definitions
# ============================================================================

class FactType:
    """Fact type constants"""
    ENTITY = "entity"           # Named entities (people, places, vessels, orgs)
    PREFERENCE = "preference"   # User or agent preferences
    CONSTRAINT = "constraint"   # Business rules, requirements, restrictions
    GOAL = "goal"              # Objectives, targets, desired outcomes
    METRIC = "metric"          # Quantitative measurements, KPIs
    
    @classmethod
    def all_types(cls) -> List[str]:
        """Get all valid fact types"""
        return [cls.ENTITY, cls.PREFERENCE, cls.CONSTRAINT, cls.GOAL, cls.METRIC]
    
    @classmethod
    def validate(cls, fact_type: str) -> bool:
        """Validate fact type"""
        return fact_type in cls.all_types()


# ============================================================================
# Data Models
# ============================================================================

class Fact:
    """Represents a structured fact in working memory"""
    
    def __init__(
        self,
        fact_id: Optional[int],
        session_id: str,
        fact_type: str,
        content: str,
        confidence: float = DEFAULT_CONFIDENCE,
        source_turn_ids: Optional[List[int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        lifecycle_stage: str = "l2_fact",
        ciar_score: Optional[float] = None,
        created_at: Optional[datetime] = None,
        promoted_from_l1_at: Optional[datetime] = None,
        consolidated_to_l3_at: Optional[datetime] = None
    ):
        self.fact_id = fact_id
        self.session_id = session_id
        self.fact_type = fact_type
        self.content = content
        self.confidence = confidence
        self.source_turn_ids = source_turn_ids or []
        self.metadata = metadata or {}
        self.lifecycle_stage = lifecycle_stage
        self.ciar_score = ciar_score
        self.created_at = created_at or datetime.utcnow()
        self.promoted_from_l1_at = promoted_from_l1_at
        self.consolidated_to_l3_at = consolidated_to_l3_at
        
        # Validate
        if not FactType.validate(fact_type):
            raise ValidationError(f"Invalid fact type: {fact_type}")
        if not (0.0 <= confidence <= 1.0):
            raise ValidationError(f"Confidence must be 0.0-1.0, got {confidence}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'fact_id': self.fact_id,
            'session_id': self.session_id,
            'fact_type': self.fact_type,
            'content': self.content,
            'confidence': self.confidence,
            'source_turn_ids': self.source_turn_ids,
            'metadata': self.metadata,
            'lifecycle_stage': self.lifecycle_stage,
            'ciar_score': self.ciar_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'promoted_from_l1_at': self.promoted_from_l1_at.isoformat() if self.promoted_from_l1_at else None,
            'consolidated_to_l3_at': self.consolidated_to_l3_at.isoformat() if self.consolidated_to_l3_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Fact':
        """Create from dictionary"""
        return cls(
            fact_id=data.get('id') or data.get('fact_id'),
            session_id=data['session_id'],
            fact_type=data['fact_type'],
            content=data['content'],
            confidence=data.get('confidence', DEFAULT_CONFIDENCE),
            source_turn_ids=data.get('source_turn_ids', []),
            metadata=data.get('metadata', {}),
            lifecycle_stage=data.get('lifecycle_stage', 'l2_fact'),
            ciar_score=data.get('ciar_score'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            promoted_from_l1_at=datetime.fromisoformat(data['promoted_from_l1_at']) if data.get('promoted_from_l1_at') else None,
            consolidated_to_l3_at=datetime.fromisoformat(data['consolidated_to_l3_at']) if data.get('consolidated_to_l3_at') else None
        )
    
    def content_hash(self) -> str:
        """Generate hash of content for deduplication"""
        normalized = self.content.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()


# ============================================================================
# Working Memory Tier Implementation
# ============================================================================

class WorkingMemoryTier(BaseTier):
    """
    L2 (Working Memory) tier implementation.
    
    Manages session-scoped structured facts with:
    - PostgreSQL storage for ACID guarantees
    - Typed facts (entity, preference, constraint, goal, metric)
    - Confidence scoring and provenance tracking
    - Automatic deduplication and fact merging
    - CIAR scoring for consolidation candidates
    - 7-day TTL for session cleanup
    """
    
    def __init__(
        self,
        postgres: PostgresAdapter,
        ttl_days: int = DEFAULT_TTL_DAYS,
        metadata: Optional[TierMetadata] = None
    ):
        """
        Initialize Working Memory Tier.
        
        Args:
            postgres: PostgreSQL adapter for storage
            ttl_days: Time-to-live for facts (days)
            metadata: Tier metadata (auto-generated if None)
        """
        # Create metadata if not provided
        if metadata is None:
            metadata = TierMetadata(
                tier_level=TierLevel.L2_WORKING_MEMORY,
                name="WorkingMemoryTier",
                description="Session-scoped facts (L2)",
                storage_backends=["PostgreSQL"],
                ttl_seconds=ttl_days * 86400
            )
        
        super().__init__(metadata)
        
        # Storage adapter
        self.postgres = postgres
        
        # Configuration
        self.ttl_days = ttl_days
        
        # Metrics
        self.metrics = MetricsCollector(component="working_memory_tier")
    
    # ========================================================================
    # Connection Lifecycle
    # ========================================================================
    
    async def connect(self) -> None:
        """Establish connection to PostgreSQL"""
        if self._connected:
            self.logger.debug("Already connected, skipping")
            return
        
        try:
            await self.postgres.connect()
            self._connected = True
            self.logger.info("Working Memory Tier connected")
        except Exception as e:
            self.logger.error(f"PostgreSQL connection failed: {e}")
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")
    
    async def disconnect(self) -> None:
        """Close connection to PostgreSQL"""
        if not self._connected:
            return
        
        try:
            await self.postgres.disconnect()
        except Exception as e:
            self.logger.warning(f"Error disconnecting PostgreSQL: {e}")
        
        self._connected = False
        self.logger.info("Working Memory Tier disconnected")
    
    async def health(self) -> HealthReport:
        """Check health of PostgreSQL"""
        components = {}
        errors = []
        
        try:
            await self.postgres.health()
            components['postgresql'] = HealthStatus.HEALTHY
        except Exception as e:
            components['postgresql'] = HealthStatus.UNHEALTHY
            errors.append(f"PostgreSQL unhealthy: {e}")
        
        overall = HealthStatus.HEALTHY if not errors else HealthStatus.UNHEALTHY
        
        return HealthReport(
            tier_level=self.metadata.tier_level,
            overall_status=overall,
            components=components,
            metrics={
                'ttl_days': self.ttl_days,
                'fact_types': FactType.all_types()
            },
            errors=errors
        )
    
    # ========================================================================
    # Core CRUD Operations
    # ========================================================================
    
    async def store(
        self,
        session_id: str,
        data: Dict[str, Any],
        **kwargs
    ) -> str:
        """
        Store a fact in working memory.
        
        Args:
            session_id: Session identifier
            data: Fact data (must include fact_type, content)
            **kwargs: Additional options
                - deduplicate: bool (default True) - Check for duplicates
                - merge_on_conflict: bool (default True) - Merge with existing
            
        Returns:
            Fact ID as string
            
        Raises:
            ValidationError: If required fields missing or invalid
            StorageError: If storage fails
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate required fields
            required = ['fact_type', 'content']
            missing = [f for f in required if f not in data]
            if missing:
                raise ValidationError(f"Missing required fields: {missing}")
            
            # Create Fact object
            fact = Fact(
                fact_id=None,  # Auto-generated
                session_id=session_id,
                fact_type=data['fact_type'],
                content=data['content'],
                confidence=data.get('confidence', DEFAULT_CONFIDENCE),
                source_turn_ids=data.get('source_turn_ids', []),
                metadata=data.get('metadata', {}),
                promoted_from_l1_at=data.get('promoted_from_l1_at')
            )
            
            # Deduplication check
            deduplicate = kwargs.get('deduplicate', True)
            merge_on_conflict = kwargs.get('merge_on_conflict', True)
            
            if deduplicate:
                existing = await self._find_similar_fact(fact)
                if existing and merge_on_conflict:
                    # Merge with existing fact
                    merged_id = await self._merge_facts(existing, fact)
                    
                    self.metrics.record('l2.store.deduplicated', 1)
                    self.logger.debug(f"Merged fact with existing {merged_id}")
                    
                    return str(merged_id)
            
            # Insert new fact
            fact_id = await self._insert_fact(fact)
            
            # Record metrics
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self.metrics.record('l2.store.success', 1)
            self.metrics.record('l2.store.latency_ms', duration_ms)
            self.metrics.record(f'l2.store.type.{fact.fact_type}', 1)
            
            self.logger.debug(
                f"Stored fact {fact_id} (type: {fact.fact_type}) "
                f"for session {session_id} (duration: {duration_ms:.2f}ms)"
            )
            
            return str(fact_id)
            
        except ValidationError:
            self.metrics.record('l2.store.validation_error', 1)
            raise
        except Exception as e:
            self.metrics.record('l2.store.error', 1)
            self.logger.error(f"Failed to store fact: {e}")
            raise StorageError(f"Failed to store fact: {e}")
    
    async def retrieve(
        self,
        session_id: str,
        item_id: Optional[str] = None,
        options: Optional[QueryOptions] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve facts from working memory.
        
        Args:
            session_id: Session identifier
            item_id: Specific fact_id to retrieve (None = all for session)
            options: Query options (filters by type, confidence, etc.)
            
        Returns:
            List of fact dictionaries
            
        Raises:
            NotFoundError: If item_id specified but not found
            StorageError: If retrieval fails
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            if item_id:
                # Get specific fact
                query = f"""
                    SELECT * FROM {POSTGRES_TABLE}
                    WHERE session_id = $1 AND id = $2
                """
                rows = await self.postgres.pool.fetch(query, session_id, int(item_id))
                
                if not rows:
                    raise NotFoundError(f"Fact {item_id} not found in session {session_id}")
                
                result = [dict(rows[0])]
            else:
                # Get facts for session with optional filters
                query, params = self._build_query(session_id, options)
                rows = await self.postgres.pool.fetch(query, *params)
                result = [dict(row) for row in rows]
            
            # Record metrics
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self.metrics.record('l2.retrieve.success', 1)
            self.metrics.record('l2.retrieve.latency_ms', duration_ms)
            self.metrics.record('l2.retrieve.count', len(result))
            
            return result
            
        except NotFoundError:
            self.metrics.record('l2.retrieve.not_found', 1)
            raise
        except Exception as e:
            self.metrics.record('l2.retrieve.error', 1)
            self.logger.error(f"Failed to retrieve facts: {e}")
            raise StorageError(f"Failed to retrieve facts: {e}")
    
    async def update(
        self,
        session_id: str,
        item_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update a fact in working memory.
        
        Args:
            session_id: Session identifier
            item_id: Fact ID to update
            updates: Fields to update (e.g., confidence, lifecycle_stage, ciar_score)
            
        Returns:
            True if updated, False if not found
        """
        try:
            # Build dynamic UPDATE query
            set_clauses = []
            params = [session_id, int(item_id)]
            param_idx = 3
            
            # Add updated_at automatically
            updates['updated_at'] = datetime.utcnow()
            
            for key, value in updates.items():
                if key == 'source_turn_ids':
                    # Array type needs special handling
                    set_clauses.append(f"{key} = ${param_idx}")
                    params.append(value)
                elif key == 'metadata':
                    # JSONB type
                    set_clauses.append(f"{key} = ${param_idx}::jsonb")
                    params.append(json.dumps(value))
                else:
                    set_clauses.append(f"{key} = ${param_idx}")
                    params.append(value)
                param_idx += 1
            
            query = f"""
                UPDATE {POSTGRES_TABLE}
                SET {', '.join(set_clauses)}
                WHERE session_id = $1 AND id = $2
            """
            
            result = await self.postgres.pool.execute(query, *params)
            
            # Check if any rows affected
            updated = result.split()[-1] != '0'
            
            if updated:
                self.metrics.record('l2.update.success', 1)
            else:
                self.metrics.record('l2.update.not_found', 1)
            
            return updated
            
        except Exception as e:
            self.metrics.record('l2.update.error', 1)
            self.logger.error(f"Failed to update fact {item_id}: {e}")
            raise StorageError(f"Failed to update fact: {e}")
    
    async def delete(
        self,
        session_id: str,
        item_id: Optional[str] = None
    ) -> int:
        """
        Delete fact(s) from working memory.
        
        Args:
            session_id: Session identifier
            item_id: Specific fact to delete (None = all for session)
            
        Returns:
            Number of facts deleted
        """
        try:
            if item_id:
                query = f"""
                    DELETE FROM {POSTGRES_TABLE}
                    WHERE session_id = $1 AND id = $2
                """
                result = await self.postgres.pool.execute(query, session_id, int(item_id))
            else:
                query = f"""
                    DELETE FROM {POSTGRES_TABLE}
                    WHERE session_id = $1
                """
                result = await self.postgres.pool.execute(query, session_id)
            
            # Extract count from result
            count = int(result.split()[-1])
            
            self.metrics.record('l2.delete.success', 1)
            self.metrics.record('l2.delete.count', count)
            
            return count
            
        except Exception as e:
            self.metrics.record('l2.delete.error', 1)
            self.logger.error(f"Failed to delete facts: {e}")
            raise StorageError(f"Failed to delete facts: {e}")
    
    # ========================================================================
    # Lifecycle Management
    # ========================================================================
    
    async def get_promotion_candidates(
        self,
        session_id: str,
        threshold: float = CONSOLIDATION_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Get facts eligible for consolidation to L3.
        
        Consolidation criteria:
        - CIAR score >= threshold (0.80 default)
        - Not yet consolidated (consolidated_to_l3_at IS NULL)
        - Lifecycle stage is 'l2_reinforced' or 'l3_candidate'
        - Age > 1 day (facts have had time to be reinforced)
        
        Args:
            session_id: Session identifier
            threshold: Minimum CIAR score for consolidation
            
        Returns:
            List of fact dictionaries ready for consolidation
        """
        try:
            # Query for consolidation candidates
            query = f"""
                SELECT * FROM {POSTGRES_TABLE}
                WHERE session_id = $1
                  AND consolidated_to_l3_at IS NULL
                  AND (
                      ciar_score >= $2
                      OR lifecycle_stage IN ('l2_reinforced', 'l3_candidate')
                  )
                  AND created_at < NOW() - INTERVAL '1 day'
                ORDER BY ciar_score DESC NULLS LAST, confidence DESC, created_at ASC
            """
            
            rows = await self.postgres.pool.fetch(query, session_id, threshold)
            
            candidates = [dict(row) for row in rows]
            
            self.metrics.record('l2.consolidation_candidates.count', len(candidates))
            
            return candidates
            
        except Exception as e:
            self.logger.error(f"Failed to get consolidation candidates: {e}")
            raise StorageError(f"Failed to get consolidation candidates: {e}")
    
    async def mark_promoted(
        self,
        session_id: str,
        item_id: str,
        target_tier: TierLevel
    ) -> bool:
        """
        Mark a fact as consolidated to L3.
        
        Args:
            session_id: Session identifier
            item_id: Fact ID that was consolidated
            target_tier: Should be L3
            
        Returns:
            True if marked successfully
        """
        if target_tier != TierLevel.L3_EPISODIC_MEMORY:
            raise ValueError(f"L2 can only consolidate to L3, got {target_tier}")
        
        updates = {
            'consolidated_to_l3_at': datetime.utcnow(),
            'lifecycle_stage': 'l3_candidate'
        }
        
        return await self.update(session_id, item_id, updates)
    
    # ========================================================================
    # TTL Management
    # ========================================================================
    
    async def cleanup_expired(self, batch_size: int = 100) -> int:
        """
        Remove expired facts based on TTL.
        
        Args:
            batch_size: Number of facts to clean per batch
            
        Returns:
            Number of facts deleted
        """
        try:
            # Calculate expiration cutoff
            cutoff = datetime.utcnow() - timedelta(days=self.ttl_days)
            
            # Delete expired facts
            query = f"""
                DELETE FROM {POSTGRES_TABLE}
                WHERE ttl_expires_at < $1
                  AND ctid IN (
                      SELECT ctid FROM {POSTGRES_TABLE}
                      WHERE ttl_expires_at < $1
                      LIMIT $2
                  )
                RETURNING id, session_id, fact_type
            """
            
            deleted = await self.postgres.pool.fetch(query, cutoff, batch_size)
            count = len(deleted)
            
            self.metrics.record('l2.cleanup.expired_count', count)
            self.logger.info(f"Cleaned up {count} expired facts")
            
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired facts: {e}")
            raise StorageError(f"Failed to cleanup expired: {e}")
    
    # ========================================================================
    # L2-Specific Methods
    # ========================================================================
    
    async def get_facts_by_type(
        self,
        session_id: str,
        fact_type: str,
        min_confidence: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Get facts filtered by type and minimum confidence.
        
        Args:
            session_id: Session identifier
            fact_type: Fact type to filter (entity, preference, etc.)
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of matching facts
        """
        options = QueryOptions(
            filters={'fact_type': fact_type},
            sort_by='confidence',
            sort_order='desc'
        )
        
        facts = await self.retrieve(session_id, options=options)
        
        # Filter by confidence
        return [f for f in facts if f.get('confidence', 0) >= min_confidence]
    
    async def reinforce_fact(
        self,
        session_id: str,
        fact_id: int,
        additional_turn_id: int,
        confidence_boost: float = 0.05
    ) -> bool:
        """
        Reinforce an existing fact with additional evidence.
        
        Args:
            session_id: Session identifier
            fact_id: Fact to reinforce
            additional_turn_id: Turn ID that reinforces this fact
            confidence_boost: Amount to increase confidence (capped at 1.0)
            
        Returns:
            True if reinforced successfully
        """
        try:
            # Get current fact
            facts = await self.retrieve(session_id, item_id=str(fact_id))
            if not facts:
                return False
            
            fact_data = facts[0]
            
            # Update source_turn_ids (add new turn)
            source_turn_ids = fact_data.get('source_turn_ids', [])
            if additional_turn_id not in source_turn_ids:
                source_turn_ids.append(additional_turn_id)
            
            # Boost confidence (cap at 1.0)
            new_confidence = min(1.0, fact_data.get('confidence', 0.85) + confidence_boost)
            
            # Update lifecycle stage if reinforced enough
            lifecycle_stage = 'l2_reinforced' if len(source_turn_ids) >= 2 else 'l2_fact'
            
            # Update fact
            updated = await self.update(
                session_id,
                str(fact_id),
                {
                    'source_turn_ids': source_turn_ids,
                    'confidence': new_confidence,
                    'lifecycle_stage': lifecycle_stage,
                    'last_accessed_at': datetime.utcnow()
                }
            )
            
            if updated:
                self.metrics.record('l2.reinforce.success', 1)
                self.logger.debug(
                    f"Reinforced fact {fact_id}: confidence {new_confidence:.2f}, "
                    f"{len(source_turn_ids)} source turns"
                )
            
            return updated
            
        except Exception as e:
            self.metrics.record('l2.reinforce.error', 1)
            self.logger.error(f"Failed to reinforce fact {fact_id}: {e}")
            raise StorageError(f"Failed to reinforce fact: {e}")
    
    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for a session's working memory.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with fact counts by type, avg confidence, etc.
        """
        try:
            query = f"""
                SELECT 
                    fact_type,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence,
                    MAX(ciar_score) as max_ciar,
                    COUNT(CASE WHEN lifecycle_stage = 'l2_reinforced' THEN 1 END) as reinforced_count
                FROM {POSTGRES_TABLE}
                WHERE session_id = $1
                GROUP BY fact_type
            """
            
            rows = await self.postgres.pool.fetch(query, session_id)
            
            summary = {
                'session_id': session_id,
                'total_facts': sum(row['count'] for row in rows),
                'by_type': {
                    row['fact_type']: {
                        'count': row['count'],
                        'avg_confidence': float(row['avg_confidence']),
                        'max_ciar': float(row['max_ciar']) if row['max_ciar'] else None,
                        'reinforced_count': row['reinforced_count']
                    }
                    for row in rows
                }
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get session summary: {e}")
            raise StorageError(f"Failed to get session summary: {e}")
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    async def _insert_fact(self, fact: Fact) -> int:
        """Insert a new fact into PostgreSQL"""
        query = f"""
            INSERT INTO {POSTGRES_TABLE} (
                session_id, fact_type, content, confidence,
                source_turn_ids, metadata, lifecycle_stage, ciar_score,
                promoted_from_l1_at
            ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9)
            RETURNING id
        """
        
        row = await self.postgres.pool.fetchrow(
            query,
            fact.session_id,
            fact.fact_type,
            fact.content,
            fact.confidence,
            fact.source_turn_ids,
            json.dumps(fact.metadata),
            fact.lifecycle_stage,
            fact.ciar_score,
            fact.promoted_from_l1_at
        )
        
        return row['id']
    
    async def _find_similar_fact(self, fact: Fact) -> Optional[Dict[str, Any]]:
        """Find existing fact with similar content"""
        # Simple content-based matching (can be enhanced with semantic similarity)
        query = f"""
            SELECT * FROM {POSTGRES_TABLE}
            WHERE session_id = $1
              AND fact_type = $2
              AND LOWER(content) = LOWER($3)
            LIMIT 1
        """
        
        row = await self.postgres.pool.fetchrow(
            query,
            fact.session_id,
            fact.fact_type,
            fact.content.strip()
        )
        
        return dict(row) if row else None
    
    async def _merge_facts(self, existing: Dict[str, Any], new_fact: Fact) -> int:
        """Merge new fact with existing fact"""
        # Combine source_turn_ids
        existing_turns = set(existing.get('source_turn_ids', []))
        new_turns = set(new_fact.source_turn_ids)
        merged_turns = list(existing_turns | new_turns)
        
        # Take higher confidence
        merged_confidence = max(existing.get('confidence', 0), new_fact.confidence)
        
        # Merge metadata
        merged_metadata = {**existing.get('metadata', {}), **new_fact.metadata}
        
        # Update lifecycle stage if reinforced
        lifecycle_stage = 'l2_reinforced' if len(merged_turns) >= 2 else existing.get('lifecycle_stage', 'l2_fact')
        
        # Update existing fact
        await self.update(
            existing['session_id'],
            str(existing['id']),
            {
                'source_turn_ids': merged_turns,
                'confidence': merged_confidence,
                'metadata': merged_metadata,
                'lifecycle_stage': lifecycle_stage,
                'last_accessed_at': datetime.utcnow()
            }
        )
        
        return existing['id']
    
    def _build_query(
        self,
        session_id: str,
        options: Optional[QueryOptions]
    ) -> tuple[str, list]:
        """Build SELECT query with filters"""
        params = [session_id]
        param_idx = 2
        
        where_clauses = ["session_id = $1"]
        
        if options and options.filters:
            for key, value in options.filters.items():
                if key == 'fact_type':
                    where_clauses.append(f"fact_type = ${param_idx}")
                    params.append(value)
                    param_idx += 1
                elif key == 'lifecycle_stage':
                    where_clauses.append(f"lifecycle_stage = ${param_idx}")
                    params.append(value)
                    param_idx += 1
                elif key == 'min_confidence':
                    where_clauses.append(f"confidence >= ${param_idx}")
                    params.append(value)
                    param_idx += 1
        
        # Build ORDER BY
        order_by = "created_at DESC"
        if options and options.sort_by:
            order_direction = options.sort_order.upper() if options.sort_order else "DESC"
            order_by = f"{options.sort_by} {order_direction}"
        
        # Build LIMIT
        limit = options.limit if options else 100
        
        query = f"""
            SELECT * FROM {POSTGRES_TABLE}
            WHERE {' AND '.join(where_clauses)}
            ORDER BY {order_by}
            LIMIT {limit}
        """
        
        return query, params
```

---

### Key Methods

#### 1. `store(session_id, data, deduplicate=True)` - Add Fact

**Purpose**: Store a structured fact in working memory with automatic deduplication.

**Fact Structure**:
```python
{
    'fact_type': 'preference',  # entity | preference | constraint | goal | metric
    'content': 'User prefers Hamburg port for European shipments',
    'confidence': 0.92,  # 0.0-1.0
    'source_turn_ids': [5, 12, 18],  # Provenance tracking
    'metadata': {
        'port_code': 'DEHAM',
        'region': 'Europe',
        'extracted_by': 'entity_extractor_v2'
    }
}
```

**Deduplication Flow**:
```
1. Normalize content (lowercase, strip whitespace)
2. Search for existing fact with same type + content
3. If found:
   ├─ Merge source_turn_ids (union of old + new)
   ├─ Take higher confidence score
   ├─ Merge metadata (new overwrites old)
   └─ Update lifecycle_stage to 'l2_reinforced'
4. If not found:
   └─ Insert as new fact
```

**Example Usage**:
```python
# Store new preference fact
fact_id = await l2_tier.store(
    session_id="session-abc-123",
    data={
        'fact_type': FactType.PREFERENCE,
        'content': 'User prefers Hamburg port for European shipments',
        'confidence': 0.92,
        'source_turn_ids': [42],
        'metadata': {'port_code': 'DEHAM'}
    }
)

# Automatic deduplication - merges with existing
fact_id = await l2_tier.store(
    session_id="session-abc-123",
    data={
        'fact_type': FactType.PREFERENCE,
        'content': 'user prefers Hamburg port for European shipments',  # Same (case-insensitive)
        'confidence': 0.85,
        'source_turn_ids': [58]
    },
    deduplicate=True  # Default
)
# Returns existing fact_id with merged source_turn_ids: [42, 58]
```

---

#### 2. `retrieve(session_id, item_id=None, options=None)` - Get Facts

**Purpose**: Retrieve facts with flexible filtering by type, confidence, lifecycle stage.

**Query Options**:
```python
QueryOptions(
    limit=50,
    filters={
        'fact_type': 'preference',
        'min_confidence': 0.85,
        'lifecycle_stage': 'l2_reinforced'
    },
    sort_by='confidence',
    sort_order='desc'
)
```

**Example Usage**:
```python
# Get all facts for session
all_facts = await l2_tier.retrieve(session_id="session-abc-123")

# Get specific fact
fact = await l2_tier.retrieve(
    session_id="session-abc-123",
    item_id="42"
)

# Get high-confidence preferences
preferences = await l2_tier.retrieve(
    session_id="session-abc-123",
    options=QueryOptions(
        filters={
            'fact_type': 'preference',
            'min_confidence': 0.90
        },
        sort_by='confidence',
        sort_order='desc'
    )
)
```

---

#### 3. `get_facts_by_type(session_id, fact_type, min_confidence)` - Type Filter

**Purpose**: Convenience method for filtering facts by type.

**Example Usage**:
```python
# Get all entities
entities = await l2_tier.get_facts_by_type(
    session_id="session-abc-123",
    fact_type=FactType.ENTITY,
    min_confidence=0.80
)

# Get constraints
constraints = await l2_tier.get_facts_by_type(
    session_id="session-abc-123",
    fact_type=FactType.CONSTRAINT,
    min_confidence=0.85
)
```

---

#### 4. `reinforce_fact(session_id, fact_id, turn_id, boost=0.05)` - Strengthen Evidence

**Purpose**: Reinforce existing fact when mentioned again in conversation.

**Reinforcement Logic**:
```
1. Add turn_id to source_turn_ids (if not already present)
2. Boost confidence by 0.05 (or custom amount), capped at 1.0
3. Update lifecycle_stage to 'l2_reinforced' if >= 2 source turns
4. Update last_accessed_at for recency tracking
```

**Example Usage**:
```python
# User mentions Hamburg preference again in turn 58
await l2_tier.reinforce_fact(
    session_id="session-abc-123",
    fact_id=42,
    additional_turn_id=58,
    confidence_boost=0.05
)

# Result:
# - source_turn_ids: [42] → [42, 58]
# - confidence: 0.92 → 0.97
# - lifecycle_stage: 'l2_fact' → 'l2_reinforced'
```

---

#### 5. `get_promotion_candidates(session_id, threshold=0.80)` - Find High-Value Facts

**Purpose**: Identify facts eligible for consolidation to L3 (Episodic Memory).

**Consolidation Criteria**:
- CIAR score ≥ 0.80 (default threshold)
- Not yet consolidated (`consolidated_to_l3_at IS NULL`)
- Lifecycle stage is `l2_reinforced` or `l3_candidate`
- Age > 1 day (facts have been reinforced over time)

**Example Usage**:
```python
candidates = await l2_tier.get_promotion_candidates(
    session_id="session-abc-123",
    threshold=0.80
)

# Returns facts ready for L3:
# [
#   {
#     'id': 42,
#     'fact_type': 'preference',
#     'content': 'User prefers Hamburg port for European shipments',
#     'confidence': 0.97,
#     'ciar_score': 0.85,
#     'lifecycle_stage': 'l2_reinforced',
#     'source_turn_ids': [5, 12, 18, 24]
#   },
#   ...
# ]
```

**Integration Point**: Called by Consolidation Engine (Priority 7).

---

#### 6. `get_session_summary(session_id)` - Analytics

**Purpose**: Get overview of session's working memory (fact counts, confidence stats).

**Example Usage**:
```python
summary = await l2_tier.get_session_summary("session-abc-123")

# Returns:
# {
#   'session_id': 'session-abc-123',
#   'total_facts': 28,
#   'by_type': {
#     'entity': {
#       'count': 12,
#       'avg_confidence': 0.88,
#       'max_ciar': 0.82,
#       'reinforced_count': 5
#     },
#     'preference': {
#       'count': 8,
#       'avg_confidence': 0.91,
#       'max_ciar': 0.87,
#       'reinforced_count': 6
#     },
#     'constraint': {
#       'count': 5,
#       'avg_confidence': 0.85,
#       'max_ciar': 0.78,
#       'reinforced_count': 2
#     },
#     ...
#   }
# }
```

---

### Fact Types

#### 1. **Entity** (`FactType.ENTITY`)

**Purpose**: Named entities extracted from conversation.

**Examples**:
```python
# Person
{'fact_type': 'entity', 'content': 'John Smith', 'metadata': {'type': 'person', 'role': 'customer'}}

# Vessel
{'fact_type': 'entity', 'content': 'MV Hamburg Express', 'metadata': {'type': 'vessel', 'imo': '9876543'}}

# Port
{'fact_type': 'entity', 'content': 'Port of Hamburg', 'metadata': {'type': 'port', 'code': 'DEHAM'}}

# Organization
{'fact_type': 'entity', 'content': 'Maersk Line', 'metadata': {'type': 'organization', 'industry': 'shipping'}}
```

**Metadata Fields**:
- `type`: Entity subtype (person, vessel, port, organization, location)
- `code`: Official identifier (port code, IMO number, etc.)
- `aliases`: Alternative names

---

#### 2. **Preference** (`FactType.PREFERENCE`)

**Purpose**: User or agent preferences and inclinations.

**Examples**:
```python
# Port preference
{'fact_type': 'preference', 'content': 'User prefers Hamburg port for European shipments', 'confidence': 0.92}

# Communication preference
{'fact_type': 'preference', 'content': 'User wants daily email updates', 'confidence': 0.88}

# Service level preference
{'fact_type': 'preference', 'content': 'Customer prefers express shipping over cost optimization', 'confidence': 0.85}
```

**Metadata Fields**:
- `category`: Type of preference (port, communication, service, etc.)
- `strength`: How strongly expressed (weak/moderate/strong)
- `context`: When this preference applies

---

#### 3. **Constraint** (`FactType.CONSTRAINT`)

**Purpose**: Business rules, requirements, restrictions.

**Examples**:
```python
# Regulatory constraint
{'fact_type': 'constraint', 'content': 'Hazardous materials require special permits for EU ports', 'confidence': 1.0}

# Budget constraint
{'fact_type': 'constraint', 'content': 'Shipping budget cannot exceed $50,000 per quarter', 'confidence': 0.95}

# Time constraint
{'fact_type': 'constraint', 'content': 'Delivery must arrive before December 15th', 'confidence': 0.90}
```

**Metadata Fields**:
- `constraint_type`: Type (regulatory, budget, time, capacity, etc.)
- `hard_constraint`: Boolean (can it be violated?)
- `expiry`: When constraint no longer applies

---

#### 4. **Goal** (`FactType.GOAL`)

**Purpose**: Objectives, targets, desired outcomes.

**Examples**:
```python
# Business goal
{'fact_type': 'goal', 'content': 'Reduce shipping costs by 15% this quarter', 'confidence': 0.93}

# Operational goal
{'fact_type': 'goal', 'content': 'Achieve 98% on-time delivery rate', 'confidence': 0.91}

# Project goal
{'fact_type': 'goal', 'content': 'Complete warehouse relocation by Q2 2026', 'confidence': 0.89}
```

**Metadata Fields**:
- `goal_type`: Type (cost, quality, time, customer satisfaction)
- `target_value`: Quantitative target (if applicable)
- `deadline`: When goal should be achieved

---

#### 5. **Metric** (`FactType.METRIC`)

**Purpose**: Quantitative measurements, KPIs, statistics.

**Examples**:
```python
# Performance metric
{'fact_type': 'metric', 'content': 'Current on-time delivery rate: 94.2%', 'confidence': 0.98}

# Cost metric
{'fact_type': 'metric', 'content': 'Average shipping cost per container: $3,245', 'confidence': 0.96}

# Volume metric
{'fact_type': 'metric', 'content': 'Monthly container volume: 1,250 TEU', 'confidence': 0.95}
```

**Metadata Fields**:
- `metric_name`: Name of metric
- `value`: Numeric value
- `unit`: Unit of measurement
- `timestamp`: When measurement was taken

---

### Deduplication Strategy

**Content Normalization**:
```python
# Original content variations
"User prefers Hamburg port for European shipments"
"user prefers Hamburg port for European shipments"  # Case variation
"User prefers Hamburg port for European shipments  "  # Trailing space

# All normalize to:
"user prefers hamburg port for european shipments"  # Lowercase + stripped

# Content hash for matching:
MD5("user prefers hamburg port for european shipments") → Same hash → Duplicate detected
```

**Merge Strategy**:
```python
# Existing fact
{
    'id': 42,
    'content': 'User prefers Hamburg port',
    'confidence': 0.85,
    'source_turn_ids': [10, 15],
    'metadata': {'port_code': 'DEHAM'}
}

# New (duplicate) fact
{
    'content': 'user prefers Hamburg port',  # Same content
    'confidence': 0.92,  # Higher confidence
    'source_turn_ids': [23],
    'metadata': {'region': 'Europe'}  # Additional metadata
}

# Merged result
{
    'id': 42,  # Same ID (updated, not inserted)
    'content': 'User prefers Hamburg port',
    'confidence': 0.92,  # Max of old/new
    'source_turn_ids': [10, 15, 23],  # Union
    'metadata': {
        'port_code': 'DEHAM',  # Preserved
        'region': 'Europe'  # Added
    },
    'lifecycle_stage': 'l2_reinforced'  # Upgraded (>= 2 sources)
}
```

**Future Enhancement**: Semantic similarity for near-duplicates.

---

### Testing Strategy

**Unit Tests**:
```python
@pytest.mark.asyncio
async def test_deduplication(l2_tier):
    """Test fact deduplication"""
    session_id = "test-session"
    
    # Store first fact
    id1 = await l2_tier.store(session_id, {
        'fact_type': 'preference',
        'content': 'User prefers Hamburg',
        'confidence': 0.85,
        'source_turn_ids': [10]
    })
    
    # Store duplicate (case-insensitive match)
    id2 = await l2_tier.store(session_id, {
        'fact_type': 'preference',
        'content': 'user prefers Hamburg',  # Same content, different case
        'confidence': 0.90,
        'source_turn_ids': [20]
    })
    
    # Should return same ID (merged, not duplicated)
    assert id1 == id2
    
    # Verify merged properties
    fact = await l2_tier.retrieve(session_id, item_id=id1)
    assert fact[0]['confidence'] == 0.90  # Higher confidence
    assert set(fact[0]['source_turn_ids']) == {10, 20}  # Merged sources
    assert fact[0]['lifecycle_stage'] == 'l2_reinforced'  # Upgraded

@pytest.mark.asyncio
async def test_fact_reinforcement(l2_tier):
    """Test fact reinforcement"""
    session_id = "test-session"
    
    # Store fact
    fact_id = await l2_tier.store(session_id, {
        'fact_type': 'preference',
        'content': 'Hamburg preference',
        'confidence': 0.85,
        'source_turn_ids': [10]
    })
    
    # Reinforce
    await l2_tier.reinforce_fact(
        session_id, int(fact_id), additional_turn_id=20, confidence_boost=0.05
    )
    
    # Verify
    fact = await l2_tier.retrieve(session_id, item_id=fact_id)
    assert fact[0]['confidence'] == 0.90  # 0.85 + 0.05
    assert 20 in fact[0]['source_turn_ids']
```

---

### Performance Benchmarks

**Expected Latencies**:
- `store()`: <5ms (with deduplication check)
- `retrieve()`: <3ms (indexed queries)
- `get_facts_by_type()`: <5ms
- `reinforce_fact()`: <8ms (read + update)
- `get_session_summary()`: <10ms (aggregation query)

**Throughput Targets**:
- 500+ fact insertions/sec
- 2000+ fact retrievals/sec
- 100+ concurrent sessions

---

### Success Criteria

- [ ] All `BaseTier` abstract methods implemented
- [ ] 5 fact types supported (entity, preference, constraint, goal, metric)
- [ ] Deduplication prevents duplicate facts
- [ ] Fact reinforcement increases confidence
- [ ] Consolidation candidates identified correctly
- [ ] TTL cleanup removes expired facts
- [ ] Session summary provides analytics
- [ ] PostgreSQL indexes optimized
- [ ] Unit tests pass (>80% coverage)
- [ ] Integration tests pass

---

## Priority 4: L3 - Episodic Memory Tier

**Estimated Time**: 5-6 hours  
**Status**: Not Started  
**Dependencies**: Priority 1

### Objective

Implement the **Episodic Memory Tier (L3)** which maintains permanent, cross-session experiential knowledge combining semantic search and graph traversal. L3 serves as:

1. **Experience Repository**: Stores consolidated episodes from working memory facts
2. **Semantic Search Engine**: Qdrant vector search for similarity-based retrieval
3. **Relationship Graph**: Neo4j graph for entity relationships and temporal chains
4. **Long-Term Memory**: Permanent storage with no TTL expiration
5. **Pattern Detection**: Identifies recurring patterns across sessions

**Key Design Goals**:
- Dual-backend architecture (Qdrant vectors + Neo4j graph)
- Semantic similarity search (<50ms)
- Graph traversal for entity relationships
- Cross-session episode linking
- Hybrid retrieval (vector + graph)
- Episode versioning and updates

---

### Tier Characteristics

| Characteristic | Value | Rationale |
|----------------|-------|-----------|
| **Storage** | Qdrant (vectors) + Neo4j (graph) | Semantic search + relationship traversal |
| **Scope** | Cross-session, permanent | Long-term experiential knowledge |
| **TTL** | None (permanent) | Episodic memories persist indefinitely |
| **Performance Target** | <50ms for vector search, <100ms for graph traversal | Network latency, optimized queries |
| **Episode Types** | Consolidated facts from L2 | Multi-fact episodes with context |
| **Embedding Model** | sentence-transformers (768-dim) | Balance accuracy vs. performance |
| **Graph Schema** | Entity nodes + relationship edges | Flexible schema for evolving data |
| **Consistency** | Eventual consistency | Separate Qdrant/Neo4j writes |
| **Versioning** | Episode version tracking | Support updates to existing episodes |

---

### Implementation Requirements

#### File: `src/memory/episodic_memory_tier.py`

```python
"""
Episodic Memory Tier (L3) - Permanent cross-session experiential memory

This tier maintains long-term episodes consolidated from working memory, with:
- Qdrant vector storage for semantic similarity search
- Neo4j graph storage for entity relationships and temporal chains
- Hybrid retrieval combining vector search and graph traversal
- Episode versioning and updates
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
import json
import hashlib
from sentence_transformers import SentenceTransformer

from src.memory.base_tier import (
    BaseTier,
    TierMetadata,
    TierLevel,
    HealthStatus,
    HealthReport,
    QueryOptions,
    LifecycleStage,
    ConnectionError,
    StorageError,
    NotFoundError,
    ValidationError
)
from src.storage.qdrant_adapter import QdrantAdapter
from src.storage.neo4j_adapter import Neo4jAdapter
from src.utils.metrics import MetricsCollector


# ============================================================================
# Constants
# ============================================================================

QDRANT_COLLECTION = "episodic_memory"
VECTOR_DIMENSIONS = 768  # sentence-transformers/all-mpnet-base-v2
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
DEFAULT_SIMILARITY_THRESHOLD = 0.75
DEFAULT_TOP_K = 10
NEO4J_EPISODE_LABEL = "Episode"
NEO4J_ENTITY_LABEL = "Entity"
NEO4J_SESSION_LABEL = "Session"


# ============================================================================
# Enums and Type Definitions
# ============================================================================

class EpisodeType:
    """Episode type constants"""
    SINGLE_FACT = "single_fact"           # Single consolidated fact
    MULTI_FACT = "multi_fact"             # Multiple related facts
    CONVERSATION = "conversation"         # Conversation thread
    DECISION = "decision"                 # Decision-making episode
    PROBLEM_SOLVING = "problem_solving"   # Problem resolution episode
    
    @classmethod
    def all_types(cls) -> List[str]:
        """Get all valid episode types"""
        return [cls.SINGLE_FACT, cls.MULTI_FACT, cls.CONVERSATION, 
                cls.DECISION, cls.PROBLEM_SOLVING]


# ============================================================================
# Data Models
# ============================================================================

class Episode:
    """Represents an episodic memory"""
    
    def __init__(
        self,
        episode_id: Optional[str],
        session_ids: List[str],
        episode_type: str,
        summary: str,
        content: str,
        facts: List[Dict[str, Any]],
        entities: List[str],
        timestamp: datetime,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        version: int = 1,
        ciar_score: Optional[float] = None,
        distilled_to_l4_at: Optional[datetime] = None
    ):
        self.episode_id = episode_id or self._generate_id()
        self.session_ids = session_ids
        self.episode_type = episode_type
        self.summary = summary
        self.content = content
        self.facts = facts
        self.entities = entities
        self.timestamp = timestamp
        self.embedding = embedding
        self.metadata = metadata or {}
        self.version = version
        self.ciar_score = ciar_score
        self.distilled_to_l4_at = distilled_to_l4_at
        
        # Validate
        if episode_type not in EpisodeType.all_types():
            raise ValidationError(f"Invalid episode type: {episode_type}")
        if not session_ids:
            raise ValidationError("At least one session_id required")
    
    def _generate_id(self) -> str:
        """Generate unique episode ID"""
        content_hash = hashlib.sha256(
            f"{self.summary}:{self.timestamp.isoformat()}".encode()
        ).hexdigest()[:16]
        return f"ep_{content_hash}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'episode_id': self.episode_id,
            'session_ids': self.session_ids,
            'episode_type': self.episode_type,
            'summary': self.summary,
            'content': self.content,
            'facts': self.facts,
            'entities': self.entities,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'version': self.version,
            'ciar_score': self.ciar_score,
            'distilled_to_l4_at': self.distilled_to_l4_at.isoformat() if self.distilled_to_l4_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], embedding: Optional[List[float]] = None) -> 'Episode':
        """Create from dictionary"""
        return cls(
            episode_id=data['episode_id'],
            session_ids=data['session_ids'],
            episode_type=data['episode_type'],
            summary=data['summary'],
            content=data['content'],
            facts=data.get('facts', []),
            entities=data.get('entities', []),
            timestamp=datetime.fromisoformat(data['timestamp']),
            embedding=embedding,
            metadata=data.get('metadata', {}),
            version=data.get('version', 1),
            ciar_score=data.get('ciar_score'),
            distilled_to_l4_at=datetime.fromisoformat(data['distilled_to_l4_at']) if data.get('distilled_to_l4_at') else None
        )


# ============================================================================
# Episodic Memory Tier Implementation
# ============================================================================

class EpisodicMemoryTier(BaseTier):
    """
    L3 (Episodic Memory) tier implementation.
    
    Manages permanent cross-session episodes with:
    - Qdrant vector storage for semantic search
    - Neo4j graph storage for entity relationships
    - Hybrid retrieval (vector + graph)
    - Episode versioning and updates
    - Entity linking and temporal chains
    """
    
    def __init__(
        self,
        qdrant: QdrantAdapter,
        neo4j: Neo4jAdapter,
        embedding_model: Optional[str] = EMBEDDING_MODEL,
        metadata: Optional[TierMetadata] = None
    ):
        """
        Initialize Episodic Memory Tier.
        
        Args:
            qdrant: Qdrant adapter for vector storage
            neo4j: Neo4j adapter for graph storage
            embedding_model: Sentence transformer model name
            metadata: Tier metadata (auto-generated if None)
        """
        # Create metadata if not provided
        if metadata is None:
            metadata = TierMetadata(
                tier_level=TierLevel.L3_EPISODIC_MEMORY,
                name="Episodic Memory",
                storage_backend=["qdrant", "neo4j"],
                supports_search=True,
                supports_lifecycle=True
            )
        
        super().__init__(metadata)
        
        # Storage adapters
        self.qdrant = qdrant
        self.neo4j = neo4j
        
        # Embedding model
        self.embedding_model_name = embedding_model
        self._embedding_model = None  # Lazy loaded
        
        # Metrics
        self.metrics = MetricsCollector(component="episodic_memory_tier")
    
    # ========================================================================
    # Connection Lifecycle
    # ========================================================================
    
    async def connect(self) -> None:
        """Establish connections to Qdrant and Neo4j"""
        if self._connected:
            self.logger.debug("Already connected, skipping")
            return
        
        try:
            # Connect to both backends
            await self.qdrant.connect()
            await self.neo4j.connect()
            
            # Ensure collection exists in Qdrant
            await self._ensure_collection()
            
            # Load embedding model (CPU-only for now)
            self._load_embedding_model()
            
            self._connected = True
            self.logger.info("Episodic Memory Tier connected")
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            raise ConnectionError(f"Failed to connect: {e}")
    
    async def disconnect(self) -> None:
        """Close connections to Qdrant and Neo4j"""
        if not self._connected:
            return
        
        errors = []
        
        try:
            await self.qdrant.disconnect()
        except Exception as e:
            errors.append(f"Qdrant disconnect error: {e}")
        
        try:
            await self.neo4j.disconnect()
        except Exception as e:
            errors.append(f"Neo4j disconnect error: {e}")
        
        if errors:
            self.logger.warning(f"Disconnect errors: {', '.join(errors)}")
        
        self._connected = False
        self.logger.info("Episodic Memory Tier disconnected")
    
    async def health(self) -> HealthReport:
        """Check health of Qdrant and Neo4j"""
        components = {}
        errors = []
        
        # Check Qdrant
        try:
            await self.qdrant.health()
            components['qdrant'] = HealthStatus.HEALTHY
        except Exception as e:
            components['qdrant'] = HealthStatus.UNHEALTHY
            errors.append(f"Qdrant unhealthy: {e}")
        
        # Check Neo4j
        try:
            await self.neo4j.health()
            components['neo4j'] = HealthStatus.HEALTHY
        except Exception as e:
            components['neo4j'] = HealthStatus.UNHEALTHY
            errors.append(f"Neo4j unhealthy: {e}")
        
        # Overall health (degraded if one backend down)
        if len(errors) == 2:
            overall = HealthStatus.UNHEALTHY
        elif len(errors) == 1:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY
        
        return HealthReport(
            tier_level=self.metadata.tier_level,
            status=overall,
            components=components,
            timestamp=datetime.utcnow(),
            details={'embedding_model': self.embedding_model_name},
            errors=errors
        )
    
    # ========================================================================
    # Core CRUD Operations
    # ========================================================================
    
    async def store(
        self,
        session_id: str,
        data: Dict[str, Any],
        **kwargs
    ) -> str:
        """
        Store an episode in episodic memory.
        
        Args:
            session_id: Primary session identifier (episodes can span multiple sessions)
            data: Episode data with required fields:
                - summary: Brief episode description
                - content: Full episode content
                - facts: List of consolidated facts
                - entities: List of entity names
                - episode_type: Type of episode
                - session_ids: List of all session IDs (optional, defaults to [session_id])
            
        Returns:
            Episode ID as string
            
        Raises:
            ValidationError: If required fields missing
            StorageError: If storage fails
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate required fields
            required = ['summary', 'content', 'facts', 'entities', 'episode_type']
            missing = [f for f in required if f not in data]
            if missing:
                raise ValidationError(f"Missing required fields: {missing}")
            
            # Create episode
            episode = Episode(
                episode_id=data.get('episode_id'),
                session_ids=data.get('session_ids', [session_id]),
                episode_type=data['episode_type'],
                summary=data['summary'],
                content=data['content'],
                facts=data['facts'],
                entities=data['entities'],
                timestamp=datetime.utcnow(),
                metadata=data.get('metadata', {}),
                ciar_score=data.get('ciar_score')
            )
            
            # Generate embedding
            episode.embedding = self._generate_embedding(episode.content)
            
            # Store in both backends (eventual consistency)
            await asyncio.gather(
                self._store_qdrant(episode),
                self._store_neo4j(episode)
            )
            
            # Record metrics
            latency = asyncio.get_event_loop().time() - start_time
            self.metrics.record('l3.store.latency_ms', latency * 1000)
            self.metrics.record('l3.store.success', 1)
            
            self.logger.info(f"Stored episode {episode.episode_id}")
            
            return episode.episode_id
            
        except ValidationError:
            self.metrics.record('l3.store.validation_error', 1)
            raise
        except Exception as e:
            self.metrics.record('l3.store.error', 1)
            self.logger.error(f"Failed to store episode: {e}")
            raise StorageError(f"Failed to store episode: {e}")
    
    async def retrieve(
        self,
        session_id: str,
        item_id: Optional[str] = None,
        options: Optional[QueryOptions] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve episodes from episodic memory.
        
        Args:
            session_id: Session identifier (filters by session)
            item_id: Specific episode ID to retrieve
            options: Query options (semantic search query, filters, limit)
            
        Returns:
            List of episode dictionaries
            
        Raises:
            NotFoundError: If item_id specified but not found
            StorageError: If retrieval fails
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            if item_id:
                # Retrieve specific episode
                episode = await self._retrieve_by_id(item_id)
                if not episode:
                    raise NotFoundError(f"Episode {item_id} not found")
                result = [episode]
            
            elif options and options.filters and 'semantic_query' in options.filters:
                # Semantic search (Qdrant)
                query = options.filters['semantic_query']
                limit = options.limit or DEFAULT_TOP_K
                result = await self._semantic_search(query, session_id, limit)
            
            else:
                # Get all episodes for session (Neo4j)
                result = await self._retrieve_by_session(session_id, options)
            
            # Record metrics
            latency = asyncio.get_event_loop().time() - start_time
            self.metrics.record('l3.retrieve.latency_ms', latency * 1000)
            self.metrics.record('l3.retrieve.success', 1)
            self.metrics.record('l3.retrieve.count', len(result))
            
            return result
            
        except NotFoundError:
            self.metrics.record('l3.retrieve.not_found', 1)
            raise
        except Exception as e:
            self.metrics.record('l3.retrieve.error', 1)
            self.logger.error(f"Failed to retrieve episodes: {e}")
            raise StorageError(f"Failed to retrieve episodes: {e}")
    
    async def update(
        self,
        session_id: str,
        item_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update an episode (creates new version).
        
        Args:
            session_id: Session identifier
            item_id: Episode ID to update
            updates: Fields to update (summary, content, metadata, ciar_score)
            
        Returns:
            True if updated successfully
        """
        try:
            # Retrieve current episode
            episodes = await self.retrieve(session_id, item_id=item_id)
            if not episodes:
                return False
            
            current = episodes[0]
            
            # Increment version
            new_version = current.get('version', 1) + 1
            
            # Apply updates
            updated_data = {**current, **updates, 'version': new_version}
            
            # If content changed, regenerate embedding
            if 'content' in updates:
                updated_data['embedding'] = self._generate_embedding(updates['content'])
            
            # Create updated episode
            episode = Episode.from_dict(updated_data, embedding=updated_data.get('embedding'))
            
            # Store updated version in both backends
            await asyncio.gather(
                self._update_qdrant(episode),
                self._update_neo4j(episode)
            )
            
            self.metrics.record('l3.update.success', 1)
            self.logger.info(f"Updated episode {item_id} to version {new_version}")
            
            return True
            
        except Exception as e:
            self.metrics.record('l3.update.error', 1)
            self.logger.error(f"Failed to update episode {item_id}: {e}")
            raise StorageError(f"Failed to update episode: {e}")
    
    async def delete(
        self,
        session_id: str,
        item_id: Optional[str] = None
    ) -> int:
        """
        Delete episode(s) from episodic memory.
        
        Args:
            session_id: Session identifier
            item_id: Specific episode to delete (None = all for session)
            
        Returns:
            Number of episodes deleted
        """
        try:
            if item_id:
                # Delete specific episode
                await asyncio.gather(
                    self._delete_qdrant(item_id),
                    self._delete_neo4j(item_id)
                )
                count = 1
            else:
                # Delete all episodes for session
                episodes = await self._retrieve_by_session(session_id, None)
                episode_ids = [ep['episode_id'] for ep in episodes]
                
                await asyncio.gather(
                    *[self._delete_qdrant(ep_id) for ep_id in episode_ids],
                    *[self._delete_neo4j(ep_id) for ep_id in episode_ids]
                )
                count = len(episode_ids)
            
            self.metrics.record('l3.delete.success', 1)
            self.metrics.record('l3.delete.count', count)
            
            return count
            
        except Exception as e:
            self.metrics.record('l3.delete.error', 1)
            self.logger.error(f"Failed to delete episodes: {e}")
            raise StorageError(f"Failed to delete episodes: {e}")
    
    # ========================================================================
    # Lifecycle Management
    # ========================================================================
    
    async def get_promotion_candidates(
        self,
        session_id: str,
        threshold: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        Get episodes eligible for distillation to L4.
        
        Distillation criteria:
        - CIAR score >= threshold (0.85 default)
        - Not yet distilled (distilled_to_l4_at IS NULL)
        - Age > 7 days (episodes have been reinforced)
        - Referenced by multiple sessions (cross-session patterns)
        
        Args:
            session_id: Session identifier (can return cross-session candidates)
            threshold: Minimum CIAR score for distillation
            
        Returns:
            List of episode dictionaries ready for distillation
        """
        try:
            # Query Neo4j for distillation candidates
            cypher = """
            MATCH (ep:Episode)
            WHERE ep.ciar_score >= $threshold
              AND ep.distilled_to_l4_at IS NULL
              AND duration.between(ep.timestamp, datetime()).days > 7
            OPTIONAL MATCH (ep)-[:MENTIONED_IN]->(s:Session)
            WITH ep, count(DISTINCT s) as session_count
            WHERE session_count > 1  // Cross-session pattern
            RETURN ep, session_count
            ORDER BY ep.ciar_score DESC, session_count DESC
            """
            
            results = await self.neo4j.run_query(cypher, {'threshold': threshold})
            
            candidates = []
            for record in results:
                ep_data = dict(record['ep'])
                ep_data['cross_session_count'] = record['session_count']
                candidates.append(ep_data)
            
            self.metrics.record('l3.distillation_candidates.count', len(candidates))
            
            return candidates
            
        except Exception as e:
            self.logger.error(f"Failed to get distillation candidates: {e}")
            raise StorageError(f"Failed to get distillation candidates: {e}")
    
    async def mark_promoted(
        self,
        session_id: str,
        item_id: str,
        target_tier: TierLevel
    ) -> bool:
        """
        Mark an episode as distilled to L4.
        
        Args:
            session_id: Session identifier
            item_id: Episode ID that was distilled
            target_tier: Should be L4
            
        Returns:
            True if marked successfully
        """
        if target_tier != TierLevel.L4_SEMANTIC_MEMORY:
            raise ValueError(f"L3 can only distill to L4, got {target_tier}")
        
        updates = {
            'distilled_to_l4_at': datetime.utcnow()
        }
        
        return await self.update(session_id, item_id, updates)
    
    # ========================================================================
    # L3-Specific Methods
    # ========================================================================
    
    async def semantic_search(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: int = DEFAULT_TOP_K,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for similar episodes.
        
        Args:
            query: Natural language query
            session_id: Optional session filter
            limit: Maximum results to return
            similarity_threshold: Minimum similarity score (0.0-1.0)
            
        Returns:
            List of episodes with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            
            # Search Qdrant
            filter_conditions = {}
            if session_id:
                filter_conditions['session_ids'] = {'$in': [session_id]}
            
            results = await self.qdrant.search(
                collection_name=QDRANT_COLLECTION,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=similarity_threshold,
                query_filter=filter_conditions if filter_conditions else None
            )
            
            # Format results
            episodes = []
            for result in results:
                episode_data = result.payload
                episode_data['similarity_score'] = result.score
                episodes.append(episode_data)
            
            self.metrics.record('l3.semantic_search.results', len(episodes))
            
            return episodes
            
        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}")
            raise StorageError(f"Semantic search failed: {e}")
    
    async def get_related_episodes(
        self,
        episode_id: str,
        relationship_types: Optional[List[str]] = None,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get episodes related through graph relationships.
        
        Args:
            episode_id: Starting episode ID
            relationship_types: Types of relationships to follow (None = all)
            max_depth: Maximum graph traversal depth
            
        Returns:
            List of related episodes with relationship paths
        """
        try:
            # Build Cypher query for graph traversal
            rel_filter = ""
            if relationship_types:
                rel_types = "|".join(relationship_types)
                rel_filter = f":{rel_types}"
            
            cypher = f"""
            MATCH path = (start:Episode {{episode_id: $episode_id}})
                         -[r{rel_filter}*1..{max_depth}]-
                         (related:Episode)
            WHERE related.episode_id <> $episode_id
            RETURN related, relationships(path) as rels, length(path) as distance
            ORDER BY distance ASC, related.timestamp DESC
            """
            
            results = await self.neo4j.run_query(cypher, {'episode_id': episode_id})
            
            related_episodes = []
            for record in results:
                ep_data = dict(record['related'])
                ep_data['relationship_path'] = [dict(r) for r in record['rels']]
                ep_data['graph_distance'] = record['distance']
                related_episodes.append(ep_data)
            
            self.metrics.record('l3.related_episodes.count', len(related_episodes))
            
            return related_episodes
            
        except Exception as e:
            self.logger.error(f"Failed to get related episodes: {e}")
            raise StorageError(f"Failed to get related episodes: {e}")
    
    async def get_entity_timeline(
        self,
        entity_name: str,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get temporal sequence of episodes mentioning an entity.
        
        Args:
            entity_name: Entity name to track
            session_id: Optional session filter
            
        Returns:
            List of episodes in chronological order
        """
        try:
            # Query Neo4j for entity timeline
            session_filter = ""
            params = {'entity': entity_name}
            
            if session_id:
                session_filter = "AND $session_id IN ep.session_ids"
                params['session_id'] = session_id
            
            cypher = f"""
            MATCH (entity:Entity {{name: $entity}})
            MATCH (entity)<-[:MENTIONS]-(ep:Episode)
            WHERE 1=1 {session_filter}
            RETURN ep
            ORDER BY ep.timestamp ASC
            """
            
            results = await self.neo4j.run_query(cypher, params)
            
            timeline = [dict(record['ep']) for record in results]
            
            self.metrics.record('l3.entity_timeline.episodes', len(timeline))
            
            return timeline
            
        except Exception as e:
            self.logger.error(f"Failed to get entity timeline: {e}")
            raise StorageError(f"Failed to get entity timeline: {e}")
    
    async def hybrid_search(
        self,
        query: str,
        session_id: Optional[str] = None,
        entity_filter: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining semantic search + graph filtering.
        
        Args:
            query: Natural language query
            session_id: Optional session filter
            entity_filter: Optional list of entities to filter by
            limit: Maximum results to return
            
        Returns:
            List of episodes ranked by combined score
        """
        try:
            # Step 1: Semantic search (Qdrant)
            semantic_results = await self.semantic_search(
                query, session_id, limit=limit * 2  # Get more candidates
            )
            
            if not entity_filter:
                return semantic_results[:limit]
            
            # Step 2: Graph filtering (Neo4j)
            episode_ids = [ep['episode_id'] for ep in semantic_results]
            
            cypher = """
            MATCH (ep:Episode)
            WHERE ep.episode_id IN $episode_ids
              AND any(entity IN $entities WHERE entity IN ep.entities)
            RETURN ep.episode_id as episode_id
            """
            
            graph_results = await self.neo4j.run_query(cypher, {
                'episode_ids': episode_ids,
                'entities': entity_filter
            })
            
            graph_filtered_ids = {record['episode_id'] for record in graph_results}
            
            # Step 3: Combine and rank
            hybrid_results = [
                ep for ep in semantic_results 
                if ep['episode_id'] in graph_filtered_ids
            ][:limit]
            
            self.metrics.record('l3.hybrid_search.results', len(hybrid_results))
            
            return hybrid_results
            
        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            raise StorageError(f"Hybrid search failed: {e}")
    
    # ========================================================================
    # Private Helper Methods - Qdrant Operations
    # ========================================================================
    
    async def _ensure_collection(self) -> None:
        """Ensure Qdrant collection exists"""
        try:
            await self.qdrant.create_collection(
                collection_name=QDRANT_COLLECTION,
                vector_size=VECTOR_DIMENSIONS,
                distance="Cosine"
            )
        except Exception as e:
            # Collection may already exist
            self.logger.debug(f"Collection setup: {e}")
    
    async def _store_qdrant(self, episode: Episode) -> None:
        """Store episode in Qdrant"""
        point = {
            'id': episode.episode_id,
            'vector': episode.embedding,
            'payload': episode.to_dict()
        }
        
        await self.qdrant.upsert(
            collection_name=QDRANT_COLLECTION,
            points=[point]
        )
    
    async def _update_qdrant(self, episode: Episode) -> None:
        """Update episode in Qdrant (same as store)"""
        await self._store_qdrant(episode)
    
    async def _delete_qdrant(self, episode_id: str) -> None:
        """Delete episode from Qdrant"""
        await self.qdrant.delete(
            collection_name=QDRANT_COLLECTION,
            point_ids=[episode_id]
        )
    
    async def _semantic_search(
        self,
        query: str,
        session_id: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform semantic search"""
        return await self.semantic_search(query, session_id, limit)
    
    # ========================================================================
    # Private Helper Methods - Neo4j Operations
    # ========================================================================
    
    async def _store_neo4j(self, episode: Episode) -> None:
        """Store episode in Neo4j with entity relationships"""
        # Create episode node
        cypher = """
        MERGE (ep:Episode {episode_id: $episode_id})
        SET ep.session_ids = $session_ids,
            ep.episode_type = $episode_type,
            ep.summary = $summary,
            ep.content = $content,
            ep.timestamp = datetime($timestamp),
            ep.version = $version,
            ep.ciar_score = $ciar_score,
            ep.metadata = $metadata
        
        // Link to sessions
        WITH ep
        UNWIND $session_ids as session_id
        MERGE (s:Session {session_id: session_id})
        MERGE (ep)-[:MENTIONED_IN]->(s)
        
        // Link to entities
        WITH ep
        UNWIND $entities as entity_name
        MERGE (e:Entity {name: entity_name})
        MERGE (ep)-[:MENTIONS]->(e)
        """
        
        await self.neo4j.run_query(cypher, {
            'episode_id': episode.episode_id,
            'session_ids': episode.session_ids,
            'episode_type': episode.episode_type,
            'summary': episode.summary,
            'content': episode.content,
            'timestamp': episode.timestamp.isoformat(),
            'version': episode.version,
            'ciar_score': episode.ciar_score,
            'metadata': json.dumps(episode.metadata),
            'entities': episode.entities
        })
    
    async def _update_neo4j(self, episode: Episode) -> None:
        """Update episode in Neo4j (same as store due to MERGE)"""
        await self._store_neo4j(episode)
    
    async def _delete_neo4j(self, episode_id: str) -> None:
        """Delete episode from Neo4j"""
        cypher = """
        MATCH (ep:Episode {episode_id: $episode_id})
        DETACH DELETE ep
        """
        await self.neo4j.run_query(cypher, {'episode_id': episode_id})
    
    async def _retrieve_by_id(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve episode by ID from Qdrant"""
        results = await self.qdrant.retrieve(
            collection_name=QDRANT_COLLECTION,
            ids=[episode_id]
        )
        
        if not results:
            return None
        
        return results[0].payload
    
    async def _retrieve_by_session(
        self,
        session_id: str,
        options: Optional[QueryOptions]
    ) -> List[Dict[str, Any]]:
        """Retrieve episodes for session from Neo4j"""
        limit = options.limit if options else 100
        
        cypher = """
        MATCH (ep:Episode)
        WHERE $session_id IN ep.session_ids
        RETURN ep
        ORDER BY ep.timestamp DESC
        LIMIT $limit
        """
        
        results = await self.neo4j.run_query(cypher, {
            'session_id': session_id,
            'limit': limit
        })
        
        return [dict(record['ep']) for record in results]
    
    # ========================================================================
    # Private Helper Methods - Embeddings
    # ========================================================================
    
    def _load_embedding_model(self) -> None:
        """Load sentence transformer model"""
        try:
            self._embedding_model = SentenceTransformer(self.embedding_model_name)
            self.logger.info(f"Loaded embedding model: {self.embedding_model_name}")
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            raise ConnectionError(f"Failed to load embedding model: {e}")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if not self._embedding_model:
            raise RuntimeError("Embedding model not loaded")
        
        embedding = self._embedding_model.encode(text, show_progress_bar=False)
        return embedding.tolist()
```

---

### Key Methods

#### 1. `store(session_id, data)` - Add Episode

**Purpose**: Store a consolidated episode in long-term memory with vector embedding and graph relationships.

**Episode Structure**:
```python
{
    'episode_type': 'multi_fact',
    'summary': 'User port preference established',
    'content': 'User consistently prefers Hamburg port for European shipments due to efficiency and cost. Mentioned in 4 conversations over 3 weeks.',
    'facts': [
        {'id': 42, 'type': 'preference', 'content': 'Hamburg port preference'},
        {'id': 58, 'type': 'entity', 'content': 'Port of Hamburg'}
    ],
    'entities': ['Hamburg', 'Port of Hamburg', 'Europe'],
    'session_ids': ['session-123', 'session-456'],
    'metadata': {
        'consolidation_date': '2025-10-22',
        'source_tier': 'L2',
        'fact_count': 2
    },
    'ciar_score': 0.88
}
```

**Example Usage**:
```python
# Store consolidated episode
episode_id = await l3_tier.store(
    session_id="session-123",
    data={
        'episode_type': EpisodeType.MULTI_FACT,
        'summary': 'User port preference established',
        'content': 'User consistently prefers Hamburg port...',
        'facts': [...],
        'entities': ['Hamburg', 'Port of Hamburg'],
        'session_ids': ['session-123', 'session-456'],
        'ciar_score': 0.88
    }
)
# Returns: "ep_a1b2c3d4e5f6g7h8"
```

**Dual Storage**:
- **Qdrant**: Stores episode with 768-dim embedding for semantic search
- **Neo4j**: Creates Episode node with relationships to Session and Entity nodes

---

#### 2. `semantic_search(query, session_id=None, limit=10)` - Find Similar Episodes

**Purpose**: Search for episodes semantically similar to a natural language query.

**Example Usage**:
```python
# Search for shipping-related episodes
results = await l3_tier.semantic_search(
    query="What are the user's preferences for European shipping routes?",
    session_id="session-123",  # Optional filter
    limit=5,
    similarity_threshold=0.75
)

# Returns:
# [
#   {
#     'episode_id': 'ep_abc123',
#     'summary': 'User port preference established',
#     'content': '...',
#     'similarity_score': 0.92,
#     'entities': ['Hamburg', 'Europe'],
#     'timestamp': '2025-10-15T14:30:00Z'
#   },
#   ...
# ]
```

**Performance**: <50ms (Qdrant vector search)

---

#### 3. `get_related_episodes(episode_id, relationship_types, depth)` - Graph Traversal

**Purpose**: Find episodes related through graph relationships (entity connections, temporal chains).

**Relationship Types**:
- `MENTIONS`: Episode mentions same entity
- `FOLLOWS`: Temporal sequence (episode B follows episode A)
- `CONTRADICTS`: Conflicting information
- `REFINES`: Episode refines/clarifies earlier episode
- `RELATED_TO`: General relationship

**Example Usage**:
```python
# Find episodes related to Hamburg preference episode
related = await l3_tier.get_related_episodes(
    episode_id="ep_abc123",
    relationship_types=['MENTIONS', 'FOLLOWS'],
    max_depth=2
)

# Returns episodes connected through entity mentions or temporal chains:
# [
#   {
#     'episode_id': 'ep_def456',
#     'summary': 'Hamburg port congestion issue',
#     'graph_distance': 1,
#     'relationship_path': [
#       {'type': 'MENTIONS', 'entity': 'Hamburg'}
#     ]
#   },
#   ...
# ]
```

**Performance**: <100ms (Neo4j graph traversal)

---

#### 4. `get_entity_timeline(entity_name, session_id=None)` - Temporal Entity Tracking

**Purpose**: Get chronological sequence of episodes mentioning a specific entity.

**Example Usage**:
```python
# Track Hamburg mentions across sessions
timeline = await l3_tier.get_entity_timeline(
    entity_name="Hamburg",
    session_id=None  # Cross-session
)

# Returns episodes in temporal order:
# [
#   {
#     'episode_id': 'ep_111',
#     'timestamp': '2025-09-01T10:00:00Z',
#     'summary': 'First mention of Hamburg port'
#   },
#   {
#     'episode_id': 'ep_222',
#     'timestamp': '2025-09-15T14:30:00Z',
#     'summary': 'Hamburg preference established'
#   },
#   ...
# ]
```

**Use Case**: Understand how knowledge about an entity evolved over time.

---

#### 5. `hybrid_search(query, session_id, entity_filter, limit)` - Combined Semantic + Graph

**Purpose**: Combine semantic search (Qdrant) with graph filtering (Neo4j) for precision.

**Example Usage**:
```python
# Find episodes about European shipping mentioning Hamburg or Rotterdam
results = await l3_tier.hybrid_search(
    query="European shipping efficiency",
    session_id="session-123",
    entity_filter=["Hamburg", "Rotterdam"],
    limit=10
)

# Returns episodes that:
# 1. Are semantically similar to query (Qdrant)
# 2. Mention Hamburg or Rotterdam (Neo4j filter)
```

**Performance**: <150ms (Qdrant search + Neo4j filter)

---

#### 6. `get_promotion_candidates(session_id, threshold=0.85)` - Find Distillation Candidates

**Purpose**: Identify episodes eligible for distillation to L4 (Semantic Memory).

**Distillation Criteria**:
- CIAR score ≥ 0.85 (high significance)
- Cross-session pattern (mentioned in 2+ sessions)
- Age > 7 days (reinforced over time)
- Not yet distilled

**Example Usage**:
```python
candidates = await l3_tier.get_promotion_candidates(
    session_id="session-123",
    threshold=0.85
)

# Returns episodes ready for L4 distillation:
# [
#   {
#     'episode_id': 'ep_abc123',
#     'summary': 'Hamburg port preference pattern',
#     'ciar_score': 0.92,
#     'cross_session_count': 5,  # Mentioned in 5 sessions
#     'timestamp': '2025-09-01T10:00:00Z'
#   },
#   ...
# ]
```

**Integration Point**: Called by Distillation Engine (Priority 8).

---

### Vector Storage Strategy (Qdrant)

#### Why Qdrant?

**Advantages**:
- High-performance approximate nearest neighbor (ANN) search
- Native support for filtering (session_id, metadata)
- Horizontal scalability
- Production-ready with persistence

#### Embedding Model

**Model**: `sentence-transformers/all-mpnet-base-v2`
- **Dimensions**: 768
- **Performance**: ~50ms inference on CPU
- **Quality**: State-of-the-art semantic understanding

**Alternative**: `text-embedding-ada-002` (OpenAI) for higher quality (requires API calls)

#### Collection Schema

```python
{
    'collection_name': 'episodic_memory',
    'vector_config': {
        'size': 768,
        'distance': 'Cosine'
    },
    'payload_schema': {
        'episode_id': 'keyword',
        'session_ids': 'keyword[]',
        'episode_type': 'keyword',
        'summary': 'text',
        'content': 'text',
        'entities': 'keyword[]',
        'timestamp': 'datetime',
        'ciar_score': 'float',
        'metadata': 'json'
    }
}
```

#### Search Strategies

**1. Semantic Similarity Search**:
```python
# Find episodes similar to query
results = qdrant.search(
    collection_name="episodic_memory",
    query_vector=embed("Hamburg port efficiency"),
    limit=10,
    score_threshold=0.75
)
```

**2. Filtered Search**:
```python
# Search within specific session
results = qdrant.search(
    collection_name="episodic_memory",
    query_vector=embed("shipping preferences"),
    limit=10,
    query_filter={
        'session_ids': {'$in': ['session-123']}
    }
)
```

**3. Multi-Filter Search**:
```python
# Search by entity and episode type
results = qdrant.search(
    collection_name="episodic_memory",
    query_vector=embed("decision making"),
    limit=10,
    query_filter={
        'episode_type': 'decision',
        'entities': {'$contains': 'Hamburg'}
    }
)
```

#### Performance Optimization

**Indexing**:
- HNSW (Hierarchical Navigable Small World) index for ANN
- M=16 (graph degree), ef_construct=100 (build-time accuracy)
- Quantization for memory efficiency (optional)

**Batching**:
- Batch upserts for bulk imports
- Async operations for concurrency

---

### Graph Storage Strategy (Neo4j)

#### Why Neo4j?

**Advantages**:
- Expressive graph queries (Cypher)
- Efficient relationship traversal
- ACID transactions
- Flexible schema evolution

#### Graph Schema

**Node Types**:
```cypher
// Episode node
(:Episode {
    episode_id: STRING,
    session_ids: LIST<STRING>,
    episode_type: STRING,
    summary: STRING,
    content: TEXT,
    timestamp: DATETIME,
    version: INTEGER,
    ciar_score: FLOAT,
    metadata: JSON
})

// Entity node
(:Entity {
    name: STRING,
    entity_type: STRING,  // person, port, vessel, organization
    first_mentioned: DATETIME,
    mention_count: INTEGER
})

// Session node
(:Session {
    session_id: STRING,
    created_at: DATETIME,
    user_id: STRING
})
```

**Relationship Types**:
```cypher
// Episode mentions entity
(Episode)-[:MENTIONS]->(Entity)

// Episode part of session
(Episode)-[:MENTIONED_IN]->(Session)

// Temporal chain
(Episode)-[:FOLLOWS {time_gap_hours: FLOAT}]->(Episode)

// Cross-references
(Episode)-[:REFINES]->(Episode)
(Episode)-[:CONTRADICTS]->(Episode)
(Episode)-[:RELATED_TO {similarity: FLOAT}]->(Episode)
```

#### Graph Queries

**1. Entity Timeline**:
```cypher
// Get all episodes mentioning Hamburg, chronologically
MATCH (entity:Entity {name: 'Hamburg'})
MATCH (entity)<-[:MENTIONS]-(ep:Episode)
RETURN ep
ORDER BY ep.timestamp ASC
```

**2. Cross-Session Patterns**:
```cypher
// Find episodes mentioned in multiple sessions
MATCH (ep:Episode)-[:MENTIONED_IN]->(s:Session)
WITH ep, collect(DISTINCT s.session_id) as sessions
WHERE size(sessions) > 1
RETURN ep, sessions
ORDER BY size(sessions) DESC
```

**3. Entity Co-occurrence**:
```cypher
// Find entities frequently mentioned together
MATCH (e1:Entity)<-[:MENTIONS]-(ep:Episode)-[:MENTIONS]->(e2:Entity)
WHERE e1.name < e2.name  // Avoid duplicates
WITH e1.name as entity1, e2.name as entity2, count(ep) as co_occurrence
WHERE co_occurrence > 2
RETURN entity1, entity2, co_occurrence
ORDER BY co_occurrence DESC
```

**4. Episode Evolution**:
```cypher
// Find episode refinement chain
MATCH path = (start:Episode)-[:REFINES*1..5]->(end:Episode)
WHERE start.episode_id = 'ep_abc123'
RETURN path
ORDER BY length(path) DESC
```

#### Indexing

**Performance Indexes**:
```cypher
// Episode lookups
CREATE INDEX episode_id_idx FOR (ep:Episode) ON (ep.episode_id);
CREATE INDEX episode_timestamp_idx FOR (ep:Episode) ON (ep.timestamp);
CREATE INDEX episode_ciar_idx FOR (ep:Episode) ON (ep.ciar_score);

// Entity lookups
CREATE INDEX entity_name_idx FOR (e:Entity) ON (e.name);

// Session lookups
CREATE INDEX session_id_idx FOR (s:Session) ON (s.session_id);
```

**Full-Text Search**:
```cypher
// Enable full-text search on episode content
CREATE FULLTEXT INDEX episode_content_idx
FOR (ep:Episode)
ON EACH [ep.summary, ep.content];
```

---

### Dual-Backend Consistency

#### Eventual Consistency Model

**Write Path**:
```
1. Generate embedding for episode content
2. Write to Qdrant (vector + payload) - async
3. Write to Neo4j (graph nodes + relationships) - async
4. Both writes succeed → Return episode_id
5. One write fails → Log error, continue (eventual consistency)
```

**Rationale**:
- Qdrant and Neo4j are independent systems
- Strict consistency would require distributed transactions (complex, slow)
- Eventual consistency acceptable for memory system

#### Consistency Checks

**Background Reconciliation**:
```python
async def reconcile_backends():
    """Ensure Qdrant and Neo4j are in sync"""
    # Get all episode IDs from Neo4j
    neo4j_ids = await neo4j.get_all_episode_ids()
    
    # Get all episode IDs from Qdrant
    qdrant_ids = await qdrant.get_all_episode_ids()
    
    # Find discrepancies
    missing_in_qdrant = neo4j_ids - qdrant_ids
    missing_in_neo4j = qdrant_ids - neo4j_ids
    
    # Re-sync missing episodes
    for episode_id in missing_in_qdrant:
        await sync_to_qdrant(episode_id)
    
    for episode_id in missing_in_neo4j:
        await sync_to_neo4j(episode_id)
```

**Run every 24 hours** to catch any sync failures.

---

### Testing Strategy

**Unit Tests**:
```python
@pytest.mark.asyncio
async def test_store_episode(l3_tier):
    """Test episode storage in both backends"""
    episode_data = {
        'episode_type': 'multi_fact',
        'summary': 'Test episode',
        'content': 'Test content for embedding',
        'facts': [{'id': 1, 'content': 'fact1'}],
        'entities': ['Hamburg'],
        'session_ids': ['session-1']
    }
    
    episode_id = await l3_tier.store("session-1", episode_data)
    
    # Verify stored in Qdrant
    qdrant_result = await l3_tier.qdrant.retrieve(
        collection_name=QDRANT_COLLECTION,
        ids=[episode_id]
    )
    assert len(qdrant_result) == 1
    
    # Verify stored in Neo4j
    neo4j_result = await l3_tier.neo4j.run_query(
        "MATCH (ep:Episode {episode_id: $id}) RETURN ep",
        {'id': episode_id}
    )
    assert len(neo4j_result) == 1

@pytest.mark.asyncio
async def test_semantic_search(l3_tier):
    """Test semantic search functionality"""
    # Store test episodes
    await l3_tier.store("session-1", {
        'episode_type': 'multi_fact',
        'summary': 'Hamburg port preference',
        'content': 'User prefers Hamburg port for European shipping',
        'facts': [],
        'entities': ['Hamburg'],
        'session_ids': ['session-1']
    })
    
    # Search for similar content
    results = await l3_tier.semantic_search(
        query="European port preferences",
        limit=5
    )
    
    assert len(results) > 0
    assert results[0]['similarity_score'] > 0.7
```

**Integration Tests**:
```python
@pytest.mark.integration
async def test_hybrid_search(real_l3_tier):
    """Test hybrid search with real backends"""
    # Setup test data
    episode_id = await real_l3_tier.store("session-1", {
        'episode_type': 'multi_fact',
        'summary': 'Port efficiency comparison',
        'content': 'Hamburg and Rotterdam are most efficient European ports',
        'facts': [],
        'entities': ['Hamburg', 'Rotterdam', 'Europe'],
        'session_ids': ['session-1']
    })
    
    # Wait for consistency
    await asyncio.sleep(0.5)
    
    # Hybrid search
    results = await real_l3_tier.hybrid_search(
        query="efficient ports",
        entity_filter=['Hamburg'],
        limit=10
    )
    
    # Verify results contain episode
    episode_ids = [r['episode_id'] for r in results]
    assert episode_id in episode_ids
```

---

### Performance Benchmarks

**Expected Latencies**:
- `store()`: 30-50ms (embedding generation + dual write)
- `semantic_search()`: 20-50ms (Qdrant ANN search)
- `get_related_episodes()`: 50-100ms (Neo4j graph traversal)
- `get_entity_timeline()`: 30-70ms (Neo4j temporal query)
- `hybrid_search()`: 80-150ms (Qdrant search + Neo4j filter)

**Throughput Targets**:
- 100+ episode insertions/sec
- 500+ semantic searches/sec
- 200+ graph traversals/sec

**Scalability**:
- Qdrant: Horizontal scaling via sharding
- Neo4j: Causal clustering for read replicas
- Embedding generation: GPU acceleration (optional)

---

### Success Criteria

- [ ] All `BaseTier` abstract methods implemented
- [ ] Dual storage (Qdrant + Neo4j) operational
- [ ] Semantic search <50ms latency
- [ ] Graph traversal <100ms latency
- [ ] Hybrid search functional
- [ ] Entity timeline tracking works
- [ ] Episode versioning supported
- [ ] Cross-session pattern detection
- [ ] Consistency reconciliation process
- [ ] Unit tests pass (>80% coverage)
- [ ] Integration tests pass with real backends

---

## Priority 5: L4 - Semantic Memory Tier

**Estimated Time**: 3-4 hours  
**Status**: Not Started  
**Dependencies**: Priority 1

### Objective
[To be populated]

### Tier Characteristics
- **Storage**: Typesense
- **Scope**: Distilled knowledge, permanent
- **Access Pattern**: Full-text search
- **Content**: Generalized patterns and operational knowledge

### Implementation Requirements

#### File: `src/memory/semantic_memory_tier.py`
[To be populated]

### Key Methods
[To be populated]

### Knowledge Types
[To be populated]

---

## Priority 6: Promotion Logic (L1 → L2)

**Estimated Time**: 3-4 hours  
**Status**: Not Started  
**Dependencies**: Priorities 2, 3

### Objective
[To be populated]

### Promotion Criteria
[To be populated]

### Implementation Requirements

#### File: `src/memory/lifecycle/promotion.py`
[To be populated]

### Promotion Algorithm
[To be populated]

---

## Priority 7: Consolidation Logic (L2 → L3)

**Estimated Time**: 4-5 hours  
**Status**: Not Started  
**Dependencies**: Priorities 3, 4

### Objective
[To be populated]

### Consolidation Criteria
[To be populated]

### Implementation Requirements

#### File: `src/memory/lifecycle/consolidation.py`
[To be populated]

### Consolidation Algorithm
[To be populated]

---

## Priority 8: Distillation Logic (L3 → L4)

**Estimated Time**: 4-5 hours  
**Status**: Not Started  
**Dependencies**: Priorities 4, 5

### Objective
[To be populated]

### Distillation Criteria
[To be populated]

### Implementation Requirements

#### File: `src/memory/lifecycle/distillation.py`
[To be populated]

### Distillation Algorithm
[To be populated]

---

## Priority 9: Memory Orchestrator

**Estimated Time**: 5-6 hours  
**Status**: Not Started  
**Dependencies**: Priorities 2, 3, 4, 5

### Objective
[To be populated]

### Orchestrator Responsibilities
[To be populated]

### Implementation Requirements

#### File: `src/memory/orchestrator.py`
[To be populated]

### API Design
[To be populated]

### Tier Coordination
[To be populated]

---

## Priority 10: Unit Tests

**Estimated Time**: 6-8 hours  
**Status**: Not Started  
**Dependencies**: All implementation priorities

### Objective
[To be populated]

### Test Coverage Requirements
[To be populated]

### Test Files Structure
[To be populated]

---

## Priority 11: Integration Tests

**Estimated Time**: 4-5 hours  
**Status**: Not Started  
**Dependencies**: Priority 10

### Objective
[To be populated]

### Integration Test Scenarios
[To be populated]

### Test Environment Requirements
[To be populated]

---

## Data Models

### PersonalMemoryState
[To be populated - reference DD-01.md]

### SharedWorkspaceState
[To be populated - reference DD-01.md]

### MemoryContext
[To be populated]

---

## API Specifications

### Memory Orchestrator API

#### Method: `get_context(session_id, turn_id)`
[To be populated]

#### Method: `add_turn(session_id, turn_id, content)`
[To be populated]

#### Method: `query_memory(query, tiers)`
[To be populated]

#### Method: `update_state(session_id, state)`
[To be populated]

---

## Performance Requirements

### Latency Targets

| Operation | Target | Rationale |
|-----------|--------|-----------|
| L1 Read (Redis) | <0.1ms | Local cache access |
| L2 Read (PostgreSQL) | <5ms | Local database query |
| L3 Read (Qdrant/Neo4j) | <50ms | Network + vector search |
| L4 Read (Typesense) | <30ms | Network + full-text search |
| Promotion (L1→L2) | Async | Background task |
| Consolidation (L2→L3) | Async | Background task |

### Throughput Requirements
[To be populated]

### Memory Usage Constraints
[To be populated]

---

## Error Handling & Edge Cases

### Cache Miss Scenarios
[To be populated]

### Promotion Failures
[To be populated]

### Network Partition Handling
[To be populated]

### TTL Expiration Edge Cases
[To be populated]

---

## Observability & Instrumentation

### Metrics to Track
[To be populated]

### Logging Requirements
[To be populated]

### Tracing Strategy
[To be populated]

---

## Testing Strategy

### Unit Test Approach
[To be populated]

### Integration Test Approach
[To be populated]

### Performance Test Scenarios
[To be populated]

---

## Acceptance Criteria

### Phase 2 Complete Definition

**Must Have:**
- [ ] All 4 memory tiers implemented and tested
- [ ] Memory orchestrator operational
- [ ] Promotion logic (L1→L2) functional
- [ ] Consolidation logic (L2→L3) functional
- [ ] Database migrations applied
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Documentation complete

**Should Have:**
- [ ] Distillation logic (L3→L4) functional
- [ ] Performance benchmarks run
- [ ] Observability metrics integrated
- [ ] Error handling robust

**Nice to Have:**
- [ ] Advanced promotion heuristics
- [ ] Adaptive TTL management
- [ ] Automatic tier rebalancing

---

## Dependencies on Phase 1

### Required from Phase 1
- [x] Redis adapter with metrics
- [x] PostgreSQL adapter operational
- [x] Qdrant adapter functional
- [x] Neo4j adapter functional
- [x] Typesense adapter functional
- [x] Base storage interface defined
- [x] Configuration management
- [x] Logging infrastructure

### Phase 1 Gaps (if any)
[To be identified during implementation]

---

## Phase 3 Preview

### What Phase 3 Will Need from Phase 2
- Memory orchestrator with stable API
- Working tier system with observable metrics
- Lifecycle management operational
- Test fixtures for agent development

### Interface Contracts for Phase 3
[To be defined]

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Promotion logic complexity | High | Medium | [To be populated] |
| Multi-tier coordination bugs | High | High | [To be populated] |
| Performance bottlenecks | Medium | Medium | [To be populated] |
| TTL management edge cases | Medium | Medium | [To be populated] |

### Schedule Risks
[To be populated]

---

## Implementation Guidelines

### Development Workflow
[To be populated]

### Code Review Checklist
[To be populated]

### Testing Workflow
[To be populated]

---

## Next Steps After Phase 2

**Phase 3: LangGraph Agent Integration (Week 5-6)**
- Implement memory-augmented agents
- Build agent state management
- Integrate with memory orchestrator
- Create benchmark adapters

See `docs/plan/implementation-plan-20102025.md` for full roadmap.

---

## Appendix

### References
- Phase 1 Specification: `docs/specs/spec-phase1-storage-layer.md`
- Implementation Plan: `docs/plan/implementation-plan-20102025.md`
- Use Case UC-01: `docs/uc-01.md`
- Data Dictionary DD-01: `docs/dd-01.md`
- Sequence Diagram SD-01: `docs/sd-01.md`

### Glossary
- **L1/Active Context**: Recent conversation turns (10-20 turns, 24h TTL)
- **L2/Working Memory**: Session-scoped facts (7 day TTL)
- **L3/Episodic Memory**: Long-term experiential knowledge (permanent)
- **L4/Semantic Memory**: Distilled general knowledge (permanent)
- **Promotion**: Moving information from L1 to L2
- **Consolidation**: Moving information from L2 to L3
- **Distillation**: Extracting patterns from L3 to L4
- **CIAR**: Certainty, Impact, Age, Recency (significance scoring)
- **EPDL**: Event Promotion and Distillation Logic

### Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-22 | [TBD] | Initial draft structure created |

---

**Document Status**: Draft Structure - Ready for Population  
**Next Review**: After Priority 0-1 implementation begins  
**Approval Required**: Technical Lead + Architecture Review

---

*End of Phase 2 Specification Document*
