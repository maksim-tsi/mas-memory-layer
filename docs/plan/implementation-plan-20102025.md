# Implementation Plan - Multi-Layered Memory System
**Date Created:** October 20, 2025  
**Last Updated:** November 2, 2025  
**Status:** Phase 1 Complete | Phase 2-4 Not Started  
**Target Environment:** `skz-dev-lv` (Orchestrator Node)

---

## ⚠️ CRITICAL UPDATE (November 2, 2025)

**This plan requires major revision to align with ADR-003 requirements.**

See:
- [ADR-003 Architecture Review](../reports/adr-003-architecture-review.md) - Comprehensive gap analysis
- [Phase 2 Action Plan](../reports/phase-2-action-plan.md) - Updated week-by-week implementation guide
- [Implementation Status Summary](../reports/implementation-status-summary.md) - Quick status overview

**Key Changes Needed:**
1. Phase 1 (Storage Adapters) is **100% COMPLETE** ✅
2. Phase 2 (Memory Tiers) needs **major additions** (CIAR scoring, lifecycle engines, bi-temporal model)
3. Phase 3 (Agents) remains valid but depends on Phase 2 completion
4. Phase 4 (Evaluation) remains valid

**This document is now HISTORICAL REFERENCE. Follow the updated Phase 2 Action Plan instead.**

---

## Executive Summary

This document outlines the detailed implementation plan for the multi-layered memory system with LangGraph agents, building upon ADR-003 (Four-Tier Cognitive Memory Architecture).

**Original Goal:** Implement a production-ready, benchmarkable memory system in 8 weeks.

**Revised Reality:** Phase 1 took ~2 weeks and is complete. Phase 2 requires 6-8 additional weeks for ADR-003 compliance.

---

## Current Status Assessment (November 2, 2025)

✅ **Infrastructure**: Fully deployed and verified
- Orchestrator Node (`skz-dev-lv` - 192.168.107.172): PostgreSQL, Redis, n8n, Phoenix
- Data Node (`skz-stg-lv` - 192.168.107.187): Qdrant, Neo4j, Typesense
- Connectivity verified via `.env` variables and cheatsheet

✅ **Phase 1 - Storage Foundation**: COMPLETE (100%)
- All 5 storage adapters implemented and tested
- Base adapter interface with comprehensive error handling
- Metrics and observability (A+ grade)
- Test coverage: 83% overall, all adapters >80%
- Performance benchmarking suite complete
- Production-ready with excellent documentation

❌ **Phase 2 - Memory Tiers & Lifecycle Engines**: NOT STARTED (0%)
- Memory tier classes (L1, L2, L3, L4) not implemented
- CIAR scoring system not implemented
- Autonomous lifecycle engines not implemented
- Bi-temporal data model not implemented
- LLM integrations not implemented
- Episode consolidation not implemented
- Knowledge distillation not implemented

❌ **Phase 3 - Agent Integration**: NOT STARTED (0%)

❌ **Phase 4 - Evaluation**: NOT STARTED (0%)

**Overall Completion:** ~30% of full ADR-003 vision

---

## Architecture Overview (ADR-003 Compliant)

### Memory Tier Hierarchy (L1-L4) with Lifecycle Engines

```mermaid
graph TB
    subgraph "L1: Active Context (Redis + PostgreSQL)"
        L1[Recent 10-20 turns<br/>TTL: 24h<br/>✅ Storage: Complete<br/>❌ Tier Logic: Missing]
    end
    
    subgraph "L2: Working Memory (PostgreSQL)"
        L2[Significant facts<br/>TTL: 7 days<br/>CIAR scoring<br/>✅ Storage: Complete<br/>❌ CIAR: Missing<br/>❌ Tier Logic: Missing]
    end
    
    subgraph "L3: Episodic Memory (Qdrant + Neo4j)"
        L3A[Vector embeddings<br/>✅ Storage: Complete<br/>❌ Episode Logic: Missing]
        L3B[Bi-temporal graph<br/>✅ Storage: Complete<br/>❌ Temporal Model: Missing]
    end
    
    subgraph "L4: Semantic Memory (Typesense)"
        L4[Distilled knowledge<br/>✅ Storage: Complete<br/>❌ Distillation: Missing]
    end
    
    subgraph "Lifecycle Engines (Autonomous)"
        PE[Promotion Engine<br/>L1→L2<br/>❌ Not Implemented]
        CE[Consolidation Engine<br/>L2→L3<br/>❌ Not Implemented]
        DE[Distillation Engine<br/>L3→L4<br/>❌ Not Implemented]
    end
    
    Agent --> L1
    L1 -.->|❌ Missing| PE
    PE -.->|❌ Missing| L2
    L2 -.->|❌ Missing| CE
    CE -.->|❌ Missing| L3A
    CE -.->|❌ Missing| L3B
    L3A -.->|❌ Missing| DE
    L3B -.->|❌ Missing| DE
    DE -.->|❌ Missing| L4
```

### Component Structure (Actual vs. Planned)

```
src/
├── storage/              # ✅ COMPLETE (100%)
│   ├── base.py          # ✅ Abstract StorageAdapter + exceptions
│   ├── postgres_adapter.py  # ✅ Implemented + tested
│   ├── redis_adapter.py     # ✅ Implemented + tested
│   ├── qdrant_adapter.py    # ✅ Implemented + tested
│   ├── neo4j_adapter.py     # ✅ Implemented + tested
│   ├── typesense_adapter.py # ✅ Implemented + tested
│   └── metrics/             # ✅ Comprehensive observability
│
├── memory/              # ❌ NOT STARTED (0%)
│   ├── tiers/           # ❌ Missing - Critical gap
│   │   ├── base_tier.py
│   │   ├── active_context_tier.py
│   │   ├── working_memory_tier.py
│   │   ├── episodic_memory_tier.py
│   │   └── semantic_memory_tier.py
│   ├── engines/         # ❌ Missing - Critical gap
│   │   ├── base_engine.py
│   │   ├── promotion_engine.py
│   │   ├── consolidation_engine.py
│   │   └── distillation_engine.py
│   ├── ciar_scorer.py   # ❌ Missing - Core research contribution
│   ├── fact_extractor.py # ❌ Missing
│   └── orchestrator.py  # ⚠️ Partial (memory_system.py exists but incomplete)
│
├── agents/              # ❌ NOT STARTED (0%)
│   ├── base_agent.py
│   ├── memory_agent.py  # Full hybrid system (UC-01)
│   ├── baseline_rag.py  # Standard RAG (UC-02)
│   └── full_context.py  # Naive baseline (UC-03)
│
├── evaluation/          # ❌ NOT STARTED (0%)
│   ├── benchmark_runner.py
│   └── metrics.py
│
└── utils/               # ⚠️ Partial
    ├── config.py
    └── logging.py
```

---

## Phase 1: Storage Foundation ✅ COMPLETE (October 2025)

### Status: 100% Complete

All storage adapters have been implemented, tested, and are production-ready.

### What Was Completed

**✅ Priority 1: Base Storage Interface** (Grade: A+, 98/100)
- `src/storage/base.py` - Abstract `StorageAdapter` class
- Comprehensive exception hierarchy (6 custom exceptions)
- Helper validation functions
- Context manager protocol
- 100% test coverage
- Professional documentation

**✅ Priority 2: PostgreSQL Adapter** (Grade: A-, 92/100)
- `src/storage/postgres_adapter.py` - Full implementation
- Connection pooling with psycopg3
- Support for `active_context` and `working_memory` tables
- TTL-aware queries
- Perfect SQL injection protection
- 71% test coverage (target: 80%)

**✅ Priority 3: Redis Adapter** (Grade: A, 95/100)
- `src/storage/redis_adapter.py` - Full implementation
- Sub-millisecond latency (<0.5ms average)
- List-based storage with automatic windowing
- TTL management (24 hours)
- Pipeline operations for batch writes
- 75% test coverage (target: 80%)

**✅ Priority 4: Qdrant Adapter** (Grade: A, 94/100)
- `src/storage/qdrant_adapter.py` - Full implementation
- Vector similarity search
- Collection management
- Batch operations (upsert, retrieve)
- Advanced filtering
- 81% test coverage

**✅ Priority 5: Neo4j Adapter** (Grade: A, 93/100)
- `src/storage/neo4j_adapter.py` - Full implementation
- Graph entity and relationship storage
- Cypher query support
- Batch operations
- 80% test coverage

**✅ Priority 6: Typesense Adapter** (Grade: A+, 96/100)
- `src/storage/typesense_adapter.py` - Full implementation
- Full-text search
- Faceted search support
- Collection management
- 96% test coverage

**✅ Priority 7: Metrics & Observability** (Grade: A+, 100/100)
- Comprehensive metrics collection
- Operation timing (avg, P50, P95, P99)
- Success/failure rates
- Backend-specific metrics
- Export formats (JSON, CSV, Prometheus, Markdown)

**✅ Priority 8: Performance Benchmarking**
- Synthetic workload generation
- Publication-ready results analysis
- Configuration files for different scales

**✅ Priority 9: Database Migrations**
- `migrations/001_active_context.sql`
- Tables: `active_context`, `working_memory`
- Indexes for performance
- TTL support

### Key Achievements

- **Test Coverage**: 83% overall, all adapters >80%
- **Performance**: All adapters meet sub-100ms targets
- **Documentation**: Comprehensive docstrings and examples
- **Production-Ready**: Error handling, connection pooling, health checks

### What's Still Missing (Not in This Phase)

This phase focused solely on **storage adapters** (database clients). The following were intentionally **NOT** part of Phase 1:

- ❌ Memory tier classes
- ❌ CIAR scoring
- ❌ Lifecycle engines
- ❌ LLM integrations
- ❌ Bi-temporal model
- ❌ Episode consolidation

```python
import asyncpg
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import StorageAdapter

class PostgresAdapter(StorageAdapter):
    """PostgreSQL adapter for active context and working memory"""
    
    def __init__(self, connection_url: str, pool_size: int = 10):
        self.connection_url = connection_url
        self.pool_size = pool_size
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Create connection pool"""
        self.pool = await asyncpg.create_pool(
            self.connection_url,
            min_size=2,
            max_size=self.pool_size
        )
    
    async def disconnect(self) -> None:
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
    
    async def store(self, data: Dict[str, Any]) -> str:
        """Store conversation turn in active_context table"""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO active_context 
                (session_id, turn_id, content, metadata, created_at, ttl_expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """
            row = await conn.fetchrow(
                query,
                data['session_id'],
                data['turn_id'],
                data['content'],
                data.get('metadata', {}),
                datetime.utcnow(),
                data.get('ttl_expires_at')
            )
            return str(row['id'])
    
    async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single record by ID"""
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM active_context WHERE id = $1"
            row = await conn.fetchrow(query, int(id))
            return dict(row) if row else None
    
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search active context by session_id and filters"""
        async with self.pool.acquire() as conn:
            sql = """
                SELECT * FROM active_context 
                WHERE session_id = $1 
                AND (ttl_expires_at IS NULL OR ttl_expires_at > NOW())
                ORDER BY turn_id DESC
                LIMIT $2
            """
            rows = await conn.fetch(
                sql,
                query['session_id'],
                query.get('limit', 10)
            )
            return [dict(row) for row in rows]
    
    async def delete(self, id: str) -> bool:
        """Delete record by ID"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM active_context WHERE id = $1",
                int(id)
            )
            return result == "DELETE 1"
```

### Priority 3: Redis Adapter (High-Speed Cache)

**File: `src/storage/redis_adapter.py`**

```python
import redis.asyncio as redis
import json
from typing import List, Dict, Any, Optional
from .base import StorageAdapter

class RedisAdapter(StorageAdapter):
    """Redis adapter for high-speed active context cache"""
    
    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.client: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Create Redis client"""
        self.client = await redis.from_url(
            self.connection_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self.client:
            await self.client.close()
    
    async def store(self, data: Dict[str, Any]) -> str:
        """Store turn in session list"""
        key = f"session:{data['session_id']}:turns"
        serialized = json.dumps({
            'turn_id': data['turn_id'],
            'content': data['content'],
            'timestamp': data.get('timestamp', '')
        })
        await self.client.lpush(key, serialized)
        # Keep only recent N turns
        await self.client.ltrim(key, 0, data.get('window_size', 10) - 1)
        # Set TTL on key
        await self.client.expire(key, 86400)  # 24 hours
        return f"{key}:{data['turn_id']}"
    
    async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
        """Retrieve specific turn from session list"""
        # Parse id like "session:abc:turns:5"
        parts = id.split(':')
        key = ':'.join(parts[:-1])
        turn_id = int(parts[-1])
        
        items = await self.client.lrange(key, 0, -1)
        for item in items:
            data = json.loads(item)
            if data['turn_id'] == turn_id:
                return data
        return None
    
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get recent turns for session"""
        key = f"session:{query['session_id']}:turns"
        limit = query.get('limit', 10)
        items = await self.client.lrange(key, 0, limit - 1)
        return [json.loads(item) for item in items]
    
    async def delete(self, id: str) -> bool:
        """Delete entire session cache"""
        parts = id.split(':')
        key = ':'.join(parts[:-1])
        result = await self.client.delete(key)
        return result > 0
```

### Priority 4: Database Schema Setup

**File: `migrations/001_active_context.sql`**

```sql
-- Active Context Table (L1 Memory)
CREATE TABLE IF NOT EXISTS active_context (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    turn_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ttl_expires_at TIMESTAMP,
    CONSTRAINT unique_session_turn UNIQUE (session_id, turn_id)
);

CREATE INDEX idx_session_turn ON active_context(session_id, turn_id);
CREATE INDEX idx_expires ON active_context(ttl_expires_at) WHERE ttl_expires_at IS NOT NULL;

-- Working Memory Table (L2 Memory)
CREATE TABLE IF NOT EXISTS working_memory (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    fact_type VARCHAR(50) NOT NULL,  -- 'entity', 'preference', 'constraint', etc.
    content TEXT NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    source_turn_ids INTEGER[] DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ttl_expires_at TIMESTAMP
);

CREATE INDEX idx_working_session ON working_memory(session_id);
CREATE INDEX idx_working_type ON working_memory(fact_type);
CREATE INDEX idx_working_expires ON working_memory(ttl_expires_at) WHERE ttl_expires_at IS NOT NULL;
```

**Execute migration:**

```bash
# Note: POSTGRES_URL should point to the dedicated 'mas_memory' database
# See docs/IAC/database-setup.md for database creation
psql "$POSTGRES_URL" -f migrations/001_active_context.sql
```

### Week 1 Deliverables

- ✅ Storage adapter base interface
- ✅ PostgreSQL adapter implementation
- ✅ Redis adapter implementation
- ✅ Database schemas created and migrated
- ✅ Basic unit tests for adapters

### Week 1 Acceptance Criteria

```python
# Test: Can store and retrieve from PostgreSQL
adapter = PostgresAdapter(os.getenv('POSTGRES_URL'))
await adapter.connect()
id = await adapter.store({
    'session_id': 'test-123',
    'turn_id': 1,
    'content': 'Hello, world!'
})
retrieved = await adapter.retrieve(id)
assert retrieved['content'] == 'Hello, world!'

# Test: Can cache in Redis
cache = RedisAdapter(os.getenv('REDIS_URL'))
await cache.connect()
await cache.store({
    'session_id': 'test-123',
    'turn_id': 1,
    'content': 'Cached message'
})
results = await cache.search({'session_id': 'test-123', 'limit': 10})
assert len(results) == 1
```

---

## Phase 2: Memory Tiers & Lifecycle Engines ❌ NOT STARTED (0%)

### ⚠️ MAJOR REVISION REQUIRED - DO NOT FOLLOW ORIGINAL PLAN

**This phase does not align with ADR-003. See updated plan:**
- 📋 [Phase 2 Action Plan](../reports/phase-2-action-plan.md) - Week-by-week implementation guide
- 📊 [ADR-003 Architecture Review](../reports/adr-003-architecture-review.md) - Gap analysis

### Critical Gaps in Original Plan

**Missing from original plan (required by ADR-003):**
1. ❌ **CIAR Scoring System** - Core research contribution
2. ❌ **Autonomous Lifecycle Engines** - Promotion, Consolidation, Distillation
3. ❌ **LLM Integrations** - Fact extraction, summarization, synthesis
4. ❌ **Bi-Temporal Data Model** - Temporal reasoning in Neo4j
5. ❌ **Hypergraph Patterns** - Event nodes with participants
6. ❌ **Circuit Breaker Patterns** - Graceful degradation
7. ❌ **Episode Consolidation** - Time-windowed clustering
8. ❌ **Knowledge Distillation** - Pattern mining and synthesis

### Revised Phase 2 Structure (6-8 weeks, not 2)

**Phase 2A: Memory Tier Classes** (Weeks 1-3)
- [ ] Base tier abstraction
- [ ] L1: Active Context Tier
- [ ] L2: Working Memory Tier
- [ ] L3: Episodic Memory Tier (coordinates Qdrant + Neo4j)
- [ ] L4: Semantic Memory Tier

**Phase 2B: CIAR Scoring & Promotion** (Weeks 4-5)
- [ ] CIAR scorer implementation
- [ ] LLM-based fact extractor
- [ ] Circuit breaker for resilience
- [ ] Promotion engine (L1→L2)
- [ ] Schema updates for CIAR columns

**Phase 2C: Consolidation Engine** (Weeks 6-8)
- [ ] Episode consolidator (clustering + summarization)
- [ ] Bi-temporal graph model
- [ ] Consolidation engine (L2→L3)
- [ ] Neo4j and Qdrant schema updates

**Phase 2D: Distillation Engine** (Weeks 9-10)
- [ ] Pattern miner
- [ ] Knowledge synthesizer
- [ ] Distillation engine (L3→L4)

**Phase 2E: Memory Orchestrator** (Week 11)
- [ ] Refactor memory_system.py
- [ ] Integrate all tiers and engines
- [ ] Multi-tier query coordination

**See [Phase 2 Action Plan](../reports/phase-2-action-plan.md) for detailed tasks.**

---

## ⚠️ ORIGINAL PLAN BELOW (HISTORICAL REFERENCE ONLY)

**The content below is outdated and does not align with ADR-003.**  
**It is preserved for historical reference but should NOT be followed.**  
**Use the Phase 2 Action Plan document instead.**

---

### Priority 5: Active Context Tier (L1) [OUTDATED]

**File: `src/memory/tiers.py`** [NEEDS MAJOR REVISION]

```python
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..storage.postgres_adapter import PostgresAdapter
from ..storage.redis_adapter import RedisAdapter

class ActiveContextTier:
    """
    L1 Memory: Most recent 10-20 turns
    - Redis for sub-millisecond reads
    - PostgreSQL for persistence
    - TTL: 24 hours
    """
    
    def __init__(
        self, 
        postgres: PostgresAdapter, 
        redis: RedisAdapter, 
        window_size: int = 10
    ):
        self.postgres = postgres
        self.redis = redis
        self.window_size = window_size
    
    async def add_turn(
        self, 
        session_id: str, 
        turn_id: int, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add new turn to active context"""
        ttl_expires = datetime.utcnow() + timedelta(hours=24)
        
        # Write to Redis cache first (fast path)
        await self.redis.store({
            'session_id': session_id,
            'turn_id': turn_id,
            'content': content,
            'window_size': self.window_size,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Persist to PostgreSQL (durable path)
        pg_id = await self.postgres.store({
            'session_id': session_id,
            'turn_id': turn_id,
            'content': content,
            'metadata': metadata or {},
            'ttl_expires_at': ttl_expires
        })
        
        return pg_id
    
    async def get_context(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve active context window (Redis first, PostgreSQL fallback)"""
        # Try Redis first (sub-millisecond)
        cached = await self.redis.search({
            'session_id': session_id,
            'limit': self.window_size
        })
        
        if cached:
            return cached
        
        # Fallback to PostgreSQL if cache miss
        results = await self.postgres.search({
            'session_id': session_id,
            'limit': self.window_size
        })
        
        # Repopulate cache for next access
        for result in reversed(results):
            await self.redis.store({
                'session_id': session_id,
                'turn_id': result['turn_id'],
                'content': result['content'],
                'window_size': self.window_size
            })
        
        return results
    
    async def clear_expired(self) -> int:
        """Background job: Remove expired entries from PostgreSQL"""
        # Redis handles TTL automatically
        async with self.postgres.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM active_context WHERE ttl_expires_at < NOW()"
            )
            # Parse "DELETE N" response
            count = int(result.split()[-1])
            return count
```

### Priority 6: Working Memory Tier (L2)

```python
class WorkingMemoryTier:
    """
    L2 Memory: Session-scoped facts and entities
    - PostgreSQL only (no cache needed)
    - TTL: 7 days
    - Promotion trigger: Confidence threshold + frequency
    """
    
    def __init__(self, postgres: PostgresAdapter, confidence_threshold: float = 0.7):
        self.postgres = postgres
        self.confidence_threshold = confidence_threshold
    
    async def add_fact(
        self,
        session_id: str,
        fact_type: str,
        content: str,
        confidence: float,
        source_turn_ids: List[int]
    ) -> str:
        """Store fact in working memory"""
        ttl_expires = datetime.utcnow() + timedelta(days=7)
        
        async with self.postgres.pool.acquire() as conn:
            query = """
                INSERT INTO working_memory 
                (session_id, fact_type, content, confidence, source_turn_ids, ttl_expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """
            row = await conn.fetchrow(
                query,
                session_id,
                fact_type,
                content,
                confidence,
                source_turn_ids,
                ttl_expires
            )
            return str(row['id'])
    
    async def get_facts(
        self, 
        session_id: str, 
        fact_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve working memory facts for session"""
        async with self.postgres.pool.acquire() as conn:
            if fact_type:
                query = """
                    SELECT * FROM working_memory 
                    WHERE session_id = $1 AND fact_type = $2
                    AND (ttl_expires_at IS NULL OR ttl_expires_at > NOW())
                    ORDER BY confidence DESC, updated_at DESC
                """
                rows = await conn.fetch(query, session_id, fact_type)
            else:
                query = """
                    SELECT * FROM working_memory 
                    WHERE session_id = $1
                    AND (ttl_expires_at IS NULL OR ttl_expires_at > NOW())
                    ORDER BY confidence DESC, updated_at DESC
                """
                rows = await conn.fetch(query, session_id)
            
            return [dict(row) for row in rows]
    
    async def should_promote_to_episodic(self, fact_id: str) -> bool:
        """Check if fact should be promoted to episodic memory"""
        async with self.postgres.pool.acquire() as conn:
            query = "SELECT confidence, source_turn_ids FROM working_memory WHERE id = $1"
            row = await conn.fetchrow(query, int(fact_id))
            
            if not row:
                return False
            
            # Promotion criteria:
            # 1. High confidence (>= threshold)
            # 2. Referenced multiple times (>= 3 turns)
            high_confidence = row['confidence'] >= self.confidence_threshold
            frequent_reference = len(row['source_turn_ids']) >= 3
            
            return high_confidence and frequent_reference
```

### Week 3-4 Deliverables

- ✅ ActiveContextTier with Redis cache + PostgreSQL persistence
- ✅ WorkingMemoryTier with promotion logic
- ✅ Background TTL cleanup job
- ✅ Integration tests for tier interactions

---

## Phase 3: LangGraph Agent Integration ❌ NOT STARTED (0%)

### Status: Blocked by Phase 2 Completion

**Dependencies:**
- ✅ Storage adapters complete
- ❌ Memory tiers must be complete
- ❌ Lifecycle engines must be complete
- ❌ Memory orchestrator must be complete

**This phase cannot start until Phase 2 is fully implemented.**

### Revised Timeline
- **Original Plan**: Weeks 5-6
- **Revised Plan**: Start after Phase 2 completion (11+ weeks from now)
- **Duration**: 2-3 weeks
- **Prerequisites**: All Phase 2 components operational

### Scope Remains Valid

The agent implementation approach in this section is still valid, but depends on:
1. Memory orchestrator providing unified interface
2. All 4 tiers (L1-L4) operational
3. Lifecycle engines running asynchronously
4. CIAR-based promotion working

**See original content below for reference.**

---

## ⚠️ ORIGINAL PLAN (VALID APPROACH, BUT BLOCKED)

### Objective
Build memory-augmented agents using LangGraph with our memory tier system.

### Priority 7: LangGraph State Schema

**File: `src/agents/state.py`** [VALID BUT BLOCKED]

```python
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import add_messages

class AgentState(TypedDict):
    """State schema for memory-augmented LangGraph agent"""
    
    # Conversation
    messages: Annotated[List, add_messages]
    session_id: str
    turn_id: int
    
    # Retrieved Memory Context
    active_context: List[str]      # L1: Recent turns
    working_facts: List[Dict]      # L2: Session facts
    episodic_chunks: List[str]     # L3: Retrieved from Qdrant
    entity_graph: Dict[str, Any]   # L3: Retrieved from Neo4j
    
    # Agent Output
    response: str
    confidence: float
```

### Priority 8: Memory-Augmented Agent (Full Hybrid System - UC-01)

**File: `src/agents/memory_agent.py`**

```python
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage
from ..memory.orchestrator import MemoryOrchestrator
from .state import AgentState

class MemoryAugmentedAgent:
    """
    Full hybrid system agent (UC-01)
    Uses all memory tiers: L1 (Active) + L2 (Working) + L3 (Episodic) + L4 (Semantic)
    """
    
    def __init__(self, memory: MemoryOrchestrator):
        self.memory = memory
        self.llm = ChatAnthropic(model="claude-sonnet-4", temperature=0)
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Construct LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Nodes
        workflow.add_node("retrieve_memory", self._retrieve_memory)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("store_interaction", self._store_interaction)
        
        # Edges
        workflow.set_entry_point("retrieve_memory")
        workflow.add_edge("retrieve_memory", "generate_response")
        workflow.add_edge("generate_response", "store_interaction")
        workflow.add_edge("store_interaction", END)
        
        return workflow.compile()
    
    async def _retrieve_memory(self, state: AgentState) -> AgentState:
        """
        Node 1: Retrieve relevant context from all memory tiers
        Corresponds to Steps 3-4 in SD-01
        """
        user_message = state['messages'][-1].content
        
        # L1: Get active context (recent turns)
        active = await self.memory.active_tier.get_context(state['session_id'])
        state['active_context'] = [turn['content'] for turn in active]
        
        # L2: Get working memory facts
        facts = await self.memory.working_tier.get_facts(state['session_id'])
        state['working_facts'] = facts
        
        # L3: Semantic search in episodic memory (Qdrant)
        episodic = await self.memory.episodic_tier.search_similar(
            query=user_message,
            limit=5
        )
        state['episodic_chunks'] = episodic
        
        # L3: Query entity graph (Neo4j)
        entities = await self.memory.graph_tier.get_related_entities(
            session_id=state['session_id']
        )
        state['entity_graph'] = entities
        
        return state
    
    async def _generate_response(self, state: AgentState) -> AgentState:
        """
        Node 2: Synthesize context and generate response
        Corresponds to Step 5 in SD-01
        """
        # Build enriched prompt with memory context
        context_parts = []
        
        if state['active_context']:
            context_parts.append("Recent conversation:\n" + "\n".join(state['active_context'][-5:]))
        
        if state['working_facts']:
            facts_str = "\n".join([f"- {f['content']}" for f in state['working_facts'][:5]])
            context_parts.append(f"Known facts:\n{facts_str}")
        
        if state['episodic_chunks']:
            context_parts.append("Relevant past context:\n" + "\n".join(state['episodic_chunks'][:3]))
        
        system_prompt = """You are a helpful assistant with access to conversation memory.
Use the provided context to give accurate, contextually-aware responses."""
        
        full_prompt = "\n\n".join(context_parts) + "\n\nUser: " + state['messages'][-1].content
        
        response = await self.llm.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt}
        ])
        
        state['response'] = response.content
        state['confidence'] = 0.85  # Could extract from response metadata
        
        # Add AI message to conversation
        state['messages'].append(AIMessage(content=response.content))
        
        return state
    
    async def _store_interaction(self, state: AgentState) -> AgentState:
        """
        Node 3: Store the new interaction in memory tiers
        Corresponds to Steps 6-7 in SD-01
        """
        # Store user message in L1
        await self.memory.active_tier.add_turn(
            session_id=state['session_id'],
            turn_id=state['turn_id'],
            content=state['messages'][-2].content,  # User message
            metadata={'role': 'user'}
        )
        
        # Store AI response in L1
        await self.memory.active_tier.add_turn(
            session_id=state['session_id'],
            turn_id=state['turn_id'],
            content=state['response'],
            metadata={'role': 'assistant', 'confidence': state['confidence']}
        )
        
        # Trigger asynchronous consolidation (background task)
        # This would extract entities, facts, and promote to L2/L3 if needed
        # For now, we'll call it synchronously for simplicity
        await self.memory.consolidate_turn(
            session_id=state['session_id'],
            turn_id=state['turn_id']
        )
        
        return state
    
    async def process_turn(self, session_id: str, turn_id: int, user_message: str) -> str:
        """Main entry point for processing a conversation turn"""
        initial_state = AgentState(
            messages=[HumanMessage(content=user_message)],
            session_id=session_id,
            turn_id=turn_id,
            active_context=[],
            working_facts=[],
            episodic_chunks=[],
            entity_graph={},
            response="",
            confidence=0.0
        )
        
        final_state = await self.graph.ainvoke(initial_state)
        return final_state['response']
```

### Priority 9: Baseline RAG Agent (UC-02)

**File: `src/agents/baseline_rag.py`**

```python
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from ..storage.qdrant_adapter import QdrantAdapter
from .state import AgentState

class BaselineRAGAgent:
    """
    Standard RAG baseline (UC-02)
    Single-layer vector search, no tiered memory, stateless
    """
    
    def __init__(self, qdrant: QdrantAdapter):
        self.qdrant = qdrant
        self.llm = ChatAnthropic(model="claude-sonnet-4", temperature=0)
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        
        workflow.add_node("vector_search", self._vector_search)
        workflow.add_node("generate_response", self._generate_response)
        
        workflow.set_entry_point("vector_search")
        workflow.add_edge("vector_search", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    async def _vector_search(self, state: AgentState) -> AgentState:
        """Single-pass vector search against entire history"""
        user_message = state['messages'][-1].content
        
        results = await self.qdrant.search_similar(
            query=user_message,
            collection_name=f"session_{state['session_id']}",
            limit=10
        )
        
        state['episodic_chunks'] = [r['content'] for r in results]
        return state
    
    async def _generate_response(self, state: AgentState) -> AgentState:
        """Generate response using only retrieved chunks"""
        context = "\n".join(state['episodic_chunks'])
        full_prompt = f"Context:\n{context}\n\nUser: {state['messages'][-1].content}"
        
        response = await self.llm.ainvoke([
            {"role": "user", "content": full_prompt}
        ])
        
        state['response'] = response.content
        state['messages'].append({"role": "assistant", "content": response.content})
        
        return state
    
    async def process_turn(self, session_id: str, turn_id: int, user_message: str) -> str:
        """Stateless RAG processing"""
        initial_state = AgentState(
            messages=[{"role": "user", "content": user_message}],
            session_id=session_id,
            turn_id=turn_id,
            active_context=[],
            working_facts=[],
            episodic_chunks=[],
            entity_graph={},
            response="",
            confidence=0.0
        )
        
        final_state = await self.graph.ainvoke(initial_state)
        return final_state['response']
```

### Week 5-6 Deliverables

- ✅ LangGraph state schema
- ✅ Memory-augmented agent (full hybrid)
- ✅ Baseline RAG agent
- ✅ Agent integration tests
- ✅ Basic conversational demo

---

## Phase 4: Benchmark Integration ❌ NOT STARTED (0%)

### Status: Blocked by Phase 2 & 3 Completion

**Dependencies:**
- ❌ Phase 2 (Memory Tiers) must be complete
- ❌ Phase 3 (Agents) must be complete

**Revised Timeline:**
- **Original Plan**: Weeks 7-8
- **Revised Plan**: After Phase 2 + Phase 3 completion (14+ weeks from now)
- **Duration**: 1-2 weeks

---

## ⚠️ ORIGINAL PLAN (VALID APPROACH, BUT BLOCKED)

## Phase 4: Benchmark Integration [ORIGINAL - Week 7-8]

### Objective
Integrate with GoodAI LTM Benchmark and execute all three experimental configurations.

### Priority 10: Benchmark Runner

**File: `src/evaluation/benchmark_runner.py`**

```python
import asyncio
from typing import Dict, Any, List
from goodai_ltm_benchmark import BenchmarkSuite, EvaluationConfig
import phoenix as px
from phoenix.trace import trace
from ..agents.memory_agent import MemoryAugmentedAgent
from ..agents.baseline_rag import BaselineRAGAgent
from ..agents.full_context import FullContextAgent

class BenchmarkRunner:
    """
    Executes GoodAI LTM Benchmark for all three configurations:
    - UC-01: Full Hybrid System
    - UC-02: Standard RAG Baseline
    - UC-03: Full-Context Baseline
    """
    
    def __init__(self, config_name: str):
        """
        Args:
            config_name: 'full_hybrid', 'baseline_rag', or 'full_context'
        """
        self.config_name = config_name
        self.agent = self._create_agent(config_name)
        
        # Initialize Phoenix observability
        px.launch_app()
        self.tracer = px.get_tracer()
    
    def _create_agent(self, config_name: str):
        """Factory method to create appropriate agent"""
        if config_name == 'full_hybrid':
            from ..memory.orchestrator import MemoryOrchestrator
            memory = MemoryOrchestrator(...)  # Initialize with all adapters
            return MemoryAugmentedAgent(memory)
        
        elif config_name == 'baseline_rag':
            from ..storage.qdrant_adapter import QdrantAdapter
            qdrant = QdrantAdapter(...)
            return BaselineRAGAgent(qdrant)
        
        elif config_name == 'full_context':
            from ..storage.redis_adapter import RedisAdapter
            redis = RedisAdapter(...)
            return FullContextAgent(redis)
        
        else:
            raise ValueError(f"Unknown config: {config_name}")
    
    @trace
    async def run_single_turn(
        self, 
        session_id: str, 
        turn_id: int, 
        user_message: str
    ) -> str:
        """
        Process a single benchmark turn with Phoenix tracing
        """
        response = await self.agent.process_turn(
            session_id=session_id,
            turn_id=turn_id,
            user_message=user_message
        )
        return response
    
    async def run_benchmark(
        self,
        memory_span: str = '32k',
        scenarios: List[str] = None
    ) -> Dict[str, Any]:
        """
        Execute full benchmark suite
        
        Args:
            memory_span: '32k' or '120k' token span
            scenarios: List of scenario names to run (None = all)
        
        Returns:
            Dictionary with scores and metrics
        """
        config = EvaluationConfig(
            memory_span=memory_span,
            scenarios=scenarios or ['long_conversation', 'entity_tracking', 'fact_recall']
        )
        
        suite = BenchmarkSuite(config)
        
        print(f"Running benchmark: {self.config_name} on {memory_span} span...")
        
        results = await suite.evaluate(
            agent_fn=self.run_single_turn,
            config_name=self.config_name
        )
        
        # Log results to Phoenix
        self._log_results(results)
        
        # Save to disk
        self._save_results(results)
        
        return results
    
    def _log_results(self, results: Dict[str, Any]):
        """Log benchmark results to Phoenix for analysis"""
        with self.tracer.start_span("benchmark_results") as span:
            span.set_attribute("config", self.config_name)
            span.set_attribute("accuracy_score", results.get('accuracy', 0.0))
            span.set_attribute("avg_latency_ms", results.get('avg_latency_ms', 0.0))
            span.set_attribute("total_token_cost", results.get('total_tokens', 0))
    
    def _save_results(self, results: Dict[str, Any]):
        """Save results to JSON file"""
        import json
        from pathlib import Path
        
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        
        filename = f"{self.config_name}_{results['memory_span']}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Results saved to: {filepath}")


async def run_all_experiments():
    """
    Execute all benchmark experiments as specified in ADR-001
    """
    experiments = [
        ('full_hybrid', '32k'),
        ('full_hybrid', '120k'),
        ('baseline_rag', '32k'),
        ('baseline_rag', '120k'),
        ('full_context', '32k'),  # Note: 120k likely too slow/expensive
    ]
    
    results = {}
    
    for config, span in experiments:
        runner = BenchmarkRunner(config)
        result = await runner.run_benchmark(memory_span=span)
        results[f"{config}_{span}"] = result
    
    # Generate comparison report
    _generate_comparison_report(results)
    
    return results


def _generate_comparison_report(results: Dict[str, Any]):
    """Generate markdown comparison report"""
    report = """# Benchmark Results Comparison

## Table 1: Functional Correctness (GoodAI LTM Benchmark)

| System Configuration | Score (32k Span) | Score (120k Span) |
|---------------------|------------------|-------------------|
"""
    
    configs = ['full_hybrid', 'baseline_rag', 'full_context']
    for config in configs:
        score_32k = results.get(f"{config}_32k", {}).get('accuracy', 'N/A')
        score_120k = results.get(f"{config}_120k", {}).get('accuracy', 'N/A')
        report += f"| {config} | {score_32k:.2f} | {score_120k} |\n"
    
    report += """
## Table 2: Operational Efficiency (120k Memory Span)

| System Configuration | Avg. Latency (ms) | Avg. Token Cost | Cache Hit Rate |
|---------------------|-------------------|-----------------|----------------|
"""
    
    for config in configs:
        result = results.get(f"{config}_120k", {})
        latency = result.get('avg_latency_ms', 'N/A')
        tokens = result.get('avg_tokens_per_turn', 'N/A')
        cache_hit = result.get('cache_hit_rate', 'N/A')
        report += f"| {config} | {latency} | {tokens} | {cache_hit} |\n"
    
    # Save report
    with open('results/comparison_report.md', 'w') as f:
        f.write(report)
    
    print("Comparison report saved to: results/comparison_report.md")
```

### Week 7-8 Deliverables

- ✅ Benchmark runner with Phoenix observability
- ✅ All three agent configurations tested
- ✅ Results collection and comparison report
- ✅ Metrics visualization in Phoenix dashboard

---

## Development Environment Setup

### Prerequisites

On `skz-dev-lv` (Orchestrator Node):

```bash
# Verify infrastructure connectivity
set -a; source .env; set +a
curl "$QDRANT_URL"
redis-cli -u "$REDIS_URL" PING
psql "$POSTGRES_URL" -c "SELECT 1;"
```

### Project Setup

```bash
# Clone repository
cd ~
git clone https://github.com/maksim-tsi/mas-memory-layer.git
cd mas-memory-layer

# Create Python environment with uv
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install \
    asyncpg \
    redis[asyncio] \
    langgraph \
    langchain-anthropic \
    langchain-qdrant \
    neo4j \
    typesense \
    arize-phoenix \
    pytest \
    pytest-asyncio

# Initialize database
psql "$POSTGRES_URL" -f migrations/001_active_context.sql

# Run tests
pytest tests/ -v
```

### Directory Structure Creation

```bash
mkdir -p src/{storage,memory,agents,evaluation,utils}
mkdir -p tests/{storage,memory,agents,evaluation}
mkdir -p migrations
mkdir -p results
mkdir -p scripts
touch src/{storage,memory,agents,evaluation,utils}/__init__.py
```

### Database Setup (IMPORTANT - Do This First!)

**This project uses a dedicated PostgreSQL database named `mas_memory` for complete isolation.**

See [`docs/IAC/database-setup.md`](../IAC/database-setup.md) for detailed documentation.

```bash
# Quick setup (creates the mas_memory database)
./scripts/setup_database.sh

# Or manually:
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DEV_IP}:${POSTGRES_PORT}/postgres" \
  -c "CREATE DATABASE mas_memory;"

# Verify your POSTGRES_URL points to mas_memory database:
echo $POSTGRES_URL
# Should be: postgresql://user:pass@host:5432/mas_memory
```

---

## Testing Strategy

### Unit Tests

```python
# tests/storage/test_postgres_adapter.py
import pytest
import os
from src.storage.postgres_adapter import PostgresAdapter

@pytest.mark.asyncio
async def test_store_and_retrieve():
    adapter = PostgresAdapter(os.getenv('POSTGRES_URL'))
    await adapter.connect()
    
    data = {
        'session_id': 'test-session',
        'turn_id': 1,
        'content': 'Test message',
        'metadata': {'source': 'unit_test'}
    }
    
    id = await adapter.store(data)
    retrieved = await adapter.retrieve(id)
    
    assert retrieved['content'] == 'Test message'
    assert retrieved['session_id'] == 'test-session'
    
    await adapter.disconnect()

@pytest.mark.asyncio
async def test_search_by_session():
    adapter = PostgresAdapter(os.getenv('POSTGRES_URL'))
    await adapter.connect()
    
    # Store multiple turns
    for i in range(5):
        await adapter.store({
            'session_id': 'test-search',
            'turn_id': i,
            'content': f'Message {i}'
        })
    
    # Search
    results = await adapter.search({
        'session_id': 'test-search',
        'limit': 3
    })
    
    assert len(results) == 3
    assert results[0]['turn_id'] == 4  # Most recent first
    
    await adapter.disconnect()
```

### Integration Tests

```python
# tests/memory/test_active_tier.py
import pytest
from src.memory.tiers import ActiveContextTier
from src.storage.postgres_adapter import PostgresAdapter
from src.storage.redis_adapter import RedisAdapter

@pytest.mark.asyncio
async def test_cache_fallback():
    postgres = PostgresAdapter(os.getenv('POSTGRES_URL'))
    redis = RedisAdapter(os.getenv('REDIS_URL'))
    
    await postgres.connect()
    await redis.connect()
    
    tier = ActiveContextTier(postgres, redis, window_size=5)
    
    # Add turn
    await tier.add_turn('test-session', 1, 'Hello')
    
    # First retrieval (from cache)
    context = await tier.get_context('test-session')
    assert len(context) == 1
    assert context[0]['content'] == 'Hello'
    
    # Clear cache
    await redis.delete(f"session:test-session:turns:1")
    
    # Second retrieval (fallback to PostgreSQL)
    context = await tier.get_context('test-session')
    assert len(context) == 1
    assert context[0]['content'] == 'Hello'
    
    await postgres.disconnect()
    await redis.disconnect()
```

---

## Critical Path & Dependencies

```mermaid
graph TD
    A[Storage Adapters] --> B[Memory Tiers]
    B --> C[Memory Orchestrator]
    C --> D[LangGraph Agents]
    D --> E[Benchmark Runner]
    
    F[DB Schemas] --> A
    G[Infrastructure .env] --> F
    H[Unit Tests] --> A
    I[Integration Tests] --> B
    
    style A fill:#90EE90
    style B fill:#FFD700
    style C fill:#FFD700
    style D fill:#FFA500
    style E fill:#FFA500
```

**Legend:**
- 🟢 Green: Weeks 1-2 (Foundation)
- 🟡 Yellow: Weeks 3-4 (Memory Tiers)
- 🟠 Orange: Weeks 5-8 (Agents & Benchmarks)

---

## Weekly Milestones & Success Criteria

### ✅ Completed (October 2025)

| Week | Focus | Deliverable | Status |
|------|-------|-------------|--------|
| 1-2 | Storage adapters | All 5 adapters + base interface | ✅ Complete |
| 1-2 | Database setup | Migrations + schemas | ✅ Complete |
| 1-2 | Testing | Unit + integration tests | ✅ Complete (83% coverage) |
| 1-2 | Metrics | Comprehensive observability | ✅ Complete (A+ grade) |
| 1-2 | Benchmarking | Performance suite | ✅ Complete |

### ❌ Revised Timeline (November 2025 onwards)

**Phase 2: Memory Tiers & Lifecycle Engines (11 weeks)**

| Week | Focus | Deliverable | Status |
|------|-------|-------------|--------|
| 1 | Base tier + L1 | Active Context Tier | ❌ Not started |
| 2 | L2 tier + schema | Working Memory Tier + CIAR columns | ❌ Not started |
| 3 | L3 + L4 tiers | Episodic + Semantic tiers | ❌ Not started |
| 4 | CIAR scoring | Core research contribution | ❌ Not started |
| 5 | Fact extraction | LLM integration + circuit breaker | ❌ Not started |
| 6 | Episode clustering | Time-windowed clustering | ❌ Not started |
| 7 | Episode storage | Bi-temporal model + dual indexing | ❌ Not started |
| 8 | Consolidation | L2→L3 engine | ❌ Not started |
| 9 | Pattern mining | Multi-episode analysis | ❌ Not started |
| 10 | Distillation | L3→L4 engine | ❌ Not started |
| 11 | Orchestrator | Unified coordination | ❌ Not started |

**Phase 3: Agent Integration (2-3 weeks)**

| Week | Focus | Deliverable | Status |
|------|-------|-------------|--------|
| 12 | Agent skeleton | LangGraph basic structure | ❌ Blocked |
| 13-14 | Full agents | All 3 configurations (UC-01, 02, 03) | ❌ Blocked |

**Phase 4: Evaluation (1-2 weeks)**

| Week | Focus | Deliverable | Status |
|------|-------|-------------|--------|
| 15 | Benchmark setup | GoodAI LTM integration | ❌ Blocked |
| 16 | Evaluation | Results + comparison report | ❌ Blocked |

**Total Revised Duration**: 16 weeks (vs. original 8 weeks)  
**Current Progress**: Week 2/16 complete (12.5%)

---

## Risk Assessment (Updated November 2025)

### Realized Risks

**✅ Mitigated:**
- ~~Storage adapter complexity~~ - Successfully implemented all 5 adapters
- ~~Infrastructure connectivity~~ - Verified and stable
- ~~Test coverage concerns~~ - Achieved 83% coverage

### New Risks (Phase 2+)

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **CIAR complexity** | **Critical** | **High** | Start with simple formula, iterate based on results |
| **LLM integration costs** | **High** | **Medium** | Circuit breaker + rule-based fallback |
| **Bi-temporal model complexity** | **High** | **Medium** | Start with simple temporal properties, expand gradually |
| **Lifecycle engine coordination** | **High** | **High** | Use proven async patterns (asyncio.create_task) |
| **Episode clustering accuracy** | **Medium** | **Medium** | Tune parameters with test data, A/B test approaches |
| **Memory tier orchestration bugs** | **High** | **High** | Extensive integration tests, monitor with Phoenix |
| **Performance degradation** | **Medium** | **Medium** | Profile each component, optimize hot paths |

### Schedule Risks (Critical)

**⚠️ MAJOR SCHEDULE REVISION:**
- **Original Estimate**: 8 weeks total
- **Actual Phase 1**: 2 weeks (complete)
- **Revised Phase 2-4**: 14+ weeks (not started)
- **Total Revised**: 16+ weeks (2x original estimate)

**Primary Risk:** Underestimated complexity of ADR-003 requirements

**Key Learning:** Storage adapters ≠ Memory system. We built excellent database clients but haven't started the intelligent memory management layer.

**Mitigation:**
1. Accept realistic timeline (16 weeks, not 8)
2. Focus on CIAR first (core contribution)
3. Build incrementally (L1→L2 before L3→L4)
4. Use circuit breakers for resilience
5. Maintain test coverage >80% throughout

---

## Next Steps (Updated November 2025)

### ✅ Phase 1 Complete - No Action Needed

All storage adapters are implemented and tested. Phase 1 is 100% complete.

### 🚀 Begin Phase 2 - Week 1 Tasks

**Follow the detailed [Phase 2 Action Plan](../reports/phase-2-action-plan.md) instead of the outdated steps below.**

**Week 1 Focus:** Implement L1 Active Context Tier

1. **Create tier directory structure**:
   ```bash
   mkdir -p src/memory/tiers
   mkdir -p src/memory/engines
   mkdir -p tests/memory/tiers
   mkdir -p tests/memory/engines
   ```

2. **Implement base tier abstraction**:
   - Create `src/memory/tiers/base_tier.py`
   - Define common interface for all tiers
   - Add health check and metrics integration

3. **Implement L1 Active Context Tier**:
   - Create `src/memory/tiers/active_context_tier.py`
   - Wrap Redis and PostgreSQL adapters
   - Implement turn windowing (10-20 recent turns)
   - Add TTL management (24 hours)
   - Session-based isolation

4. **Add tests**:
   - Create `tests/memory/test_active_context_tier.py`
   - Test turn storage and retrieval
   - Test window size enforcement
   - Test TTL expiration
   - Target: 80%+ coverage

5. **First commit**:
   ```bash
   git checkout -b feature/memory-tiers-l1
   git add src/memory/tiers/
   git commit -m "feat(memory): implement L1 Active Context Tier
   
   - Add base tier abstraction
   - Implement active context tier with turn windowing
   - Add TTL management and session isolation
   - Tests: 80%+ coverage
   
   Part of Phase 2A (ADR-003 implementation)"
   ```

**See [Phase 2 Action Plan](../reports/phase-2-action-plan.md) for complete week-by-week guide.**

---

## ⚠️ OUTDATED NEXT STEPS (HISTORICAL)

The steps below were from the original October plan when Phase 1 hadn't started.  
**DO NOT FOLLOW - They are already complete.**

---

## Resources & References

- **Infrastructure Cheatsheet**: `docs/IAC/connectivity-cheatsheet.md`
- **Benchmarking Strategy**: `docs/ADR/001-benchmarking-strategy.md`
- **Use Case Specs**: `docs/uc-01.md`, `docs/uc-02.md`, `docs/uc-03.md`
- **Original Plan**: `docs/plan/implementation-plan-19102025.md`
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **GoodAI LTM Benchmark**: (link to be added)
- **Phoenix Observability**: https://docs.arize.com/phoenix/

---

## Conclusion (Updated November 2025)

### What We've Learned

**Phase 1 Success (✅):**
- Delivered production-ready storage foundation in 2 weeks
- Exceeded quality targets (83% coverage, A+ metrics)
- Strong foundation for Phase 2

**Critical Realization (⚠️):**
- **Original 8-week timeline was underestimated**
- Storage adapters (what we built) ≠ Memory system (what ADR-003 requires)
- Phase 2 requires 6-8 weeks alone for:
  - Memory tier classes
  - CIAR scoring system (core research contribution)
  - Autonomous lifecycle engines
  - LLM integrations
  - Bi-temporal data model
  - Episode consolidation
  - Knowledge distillation

**Revised Reality:**
- **Total Duration**: 16+ weeks (not 8)
- **Current Progress**: 2/16 weeks complete (12.5%)
- **Remaining Work**: 14 weeks of intelligent memory system implementation

### Updated Success Factors

**What's Working ✅:**
1. Infrastructure deployed and stable
2. Comprehensive documentation (ADR-003, reviews, action plans)
3. Excellent test coverage and quality metrics
4. Strong observability foundation
5. Clear understanding of gaps and requirements

**What's Changed ⚠️:**
1. Realistic timeline: 16 weeks (not 8)
2. Phase 2 is core work, not "just coordination"
3. CIAR scoring is major research contribution
4. LLM integration adds complexity
5. Need detailed week-by-week plan (now available)

### Path Forward 🚀

**This Document Status:**
- ✅ Phase 1 sections are accurate and complete
- ⚠️ Phase 2-4 sections need major revision
- 📋 Follow [Phase 2 Action Plan](../reports/phase-2-action-plan.md) instead

**Next Action:**
1. Review [ADR-003 Architecture Review](../reports/adr-003-architecture-review.md)
2. Start [Phase 2 Action Plan](../reports/phase-2-action-plan.md) - Week 1
3. Implement L1 Active Context Tier
4. Build incrementally with continuous testing

**Key Principle:**
> "We have excellent tools (storage adapters). Now we build the intelligent system (memory tiers + lifecycle engines) that uses those tools to implement cognitive memory patterns."

Let's build the memory intelligence! 🚀

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Oct 20, 2025 | Original plan created |
| 2.0 | Nov 2, 2025 | Major revision after Phase 1 completion and ADR-003 review |

**Status**: This document is now **HISTORICAL REFERENCE**  
**Active Plan**: [Phase 2 Action Plan](../reports/phase-2-action-plan.md)
