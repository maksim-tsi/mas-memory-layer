# Implementation Plan - Multi-Layered Memory System
**Date:** October 20, 2025  
**Status:** Ready to Begin Development  
**Target Environment:** `skz-dev-lv` (Orchestrator Node)

---

## Executive Summary

This document outlines the detailed implementation plan for the multi-layered memory system with LangGraph agents, building upon the architectural decisions documented in ADR-001 and the infrastructure deployed on our home lab.

**Goal:** Implement a production-ready, benchmarkable memory system in 8 weeks, culminating in quantitative results from the GoodAI LTM Benchmark to validate our hybrid architecture.

---

## Current Status Assessment

✅ **Infrastructure**: Fully deployed and verified
- Orchestrator Node (`skz-dev-lv` - 192.168.107.172): PostgreSQL, Redis, n8n, Phoenix
- Data Node (`skz-stg-lv` - 192.168.107.187): Qdrant, Neo4j, Typesense
- Connectivity verified via `.env` variables and cheatsheet

✅ **Planning**: Comprehensive documentation complete
- Implementation plan (original 19/10/2025)
- ADR-001 (benchmarking strategy)
- Use cases (UC-01, UC-02, UC-03)
- Sequence diagrams (SD-01, SD-02, SD-03)
- Data dictionaries (DD-01, DD-02, DD-03)

⚠️ **Code**: Not yet implemented - **START HERE**

---

## Architecture Overview

### Memory Tier Hierarchy (L1-L4)

```mermaid
graph TB
    subgraph "L1: Active Context (PostgreSQL + Redis)"
        L1[Recent 10-20 turns<br/>TTL: 24h]
    end
    
    subgraph "L2: Working Memory (PostgreSQL)"
        L2[Session-scoped facts<br/>TTL: 7 days]
    end
    
    subgraph "L3: Episodic Memory (Qdrant + Neo4j)"
        L3A[Vector embeddings]
        L3B[Entity graph]
    end
    
    subgraph "L4: Semantic Memory (Typesense)"
        L4[Distilled knowledge<br/>Permanent]
    end
    
    Agent --> L1
    L1 -->|Promote| L2
    L2 -->|Consolidate| L3A
    L2 -->|Extract entities| L3B
    L3A -->|Distill| L4
    L3B -->|Distill| L4
```

### Component Structure

```
src/
├── storage/              # Storage adapters (one per backend)
│   ├── base.py          # Abstract StorageAdapter interface
│   ├── postgres_adapter.py
│   ├── redis_adapter.py
│   ├── qdrant_adapter.py
│   ├── neo4j_adapter.py
│   └── typesense_adapter.py
├── memory/              # Memory tier controllers
│   ├── tiers.py         # ActiveContextTier, WorkingMemoryTier, etc.
│   └── orchestrator.py  # Unified MemoryOrchestrator
├── agents/              # LangGraph agent implementations
│   ├── base_agent.py    # Shared agent utilities
│   ├── memory_agent.py  # Full hybrid system (UC-01)
│   ├── baseline_rag.py  # Standard RAG (UC-02)
│   └── full_context.py  # Naive baseline (UC-03)
├── evaluation/          # Benchmark runners
│   ├── benchmark_runner.py
│   └── metrics.py
└── utils/
    ├── config.py
    └── logging.py
```

---

## Phase 1: Foundation (Week 1-2) - **START HERE**

### Objective
Establish storage layer abstractions and connect to infrastructure services.

### Priority 1: Core Data Models & Base Interfaces

Create the abstract storage adapter interface:

**File: `src/storage/base.py`**

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

class StorageAdapter(ABC):
    """Base interface for all storage backends"""
    
    @abstractmethod
    async def connect(self) -> None:
        """Initialize connection to storage backend"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection gracefully"""
        pass
    
    @abstractmethod
    async def store(self, data: Dict[str, Any]) -> str:
        """Store data and return unique ID"""
        pass
    
    @abstractmethod
    async def retrieve(self, id: str) -> Optional[Dict[str, Any]]:
        """Retrieve data by ID, return None if not found"""
        pass
    
    @abstractmethod
    async def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search with filters and return matching records"""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete record by ID, return success status"""
        pass
```

### Priority 2: PostgreSQL Adapter (Active Context Store)

**File: `src/storage/postgres_adapter.py`**

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

## Phase 2: Memory Tiers (Week 3-4)

### Objective
Build tier controllers that orchestrate storage adapters and implement promotion logic.

### Priority 5: Active Context Tier (L1)

**File: `src/memory/tiers.py`**

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

## Phase 3: LangGraph Agent Integration (Week 5-6)

### Objective
Build memory-augmented agents using LangGraph with our memory tier system.

### Priority 7: LangGraph State Schema

**File: `src/agents/state.py`**

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

## Phase 4: Benchmark Integration (Week 7-8)

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
touch src/{storage,memory,agents,evaluation,utils}/__init__.py
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

| Week | Focus | Deliverable | Success Metric |
|------|-------|-------------|----------------|
| 1 | Storage adapters | PostgreSQL + Redis adapters | Tests pass, can store/retrieve |
| 2 | Database setup | Schemas migrated | Tables exist, data persists |
| 3 | Active tier | L1 memory tier | Cache hit rate > 90% |
| 4 | Working tier | L2 memory tier | Promotion logic works |
| 5 | Agent skeleton | LangGraph basic agent | Can respond to simple queries |
| 6 | Memory integration | Full agent with tiers | Retrieves from all tiers |
| 7 | Benchmark setup | Runner + UC-01 | Can execute one full test |
| 8 | Full evaluation | All 3 configs tested | Comparison report generated |

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LangGraph complexity | High | Medium | Start with linear graph, add complexity incrementally |
| Multi-tier orchestration bugs | High | High | Extensive integration tests, monitor with Phoenix |
| Benchmark integration issues | Medium | Medium | Mock benchmark early, test with small dataset first |
| Performance bottlenecks | Medium | Low | Profile with Phoenix, optimize hot paths |
| Infrastructure connectivity | High | Low | Already verified; keep cheatsheet handy |

### Schedule Risks

- **Risk:** Qdrant/Neo4j adapters take longer than expected
- **Mitigation:** Start with 2-tier system (L1 + L2 only), add L3 later if needed

- **Risk:** Benchmark doesn't work with our agent interface
- **Mitigation:** Create adapter wrapper early, test with synthetic data

---

## Next Steps (This Week)

1. **SSH into `skz-dev-lv`**:
   ```bash
   ssh max@192.168.107.172
   ```

2. **Clone repository and set up environment**:
   ```bash
   cd ~
   git clone https://github.com/maksim-tsi/mas-memory-layer.git
   cd mas-memory-layer
   source .env  # Load infrastructure variables
   ```

3. **Create project structure**:
   ```bash
   mkdir -p src/{storage,memory,agents,evaluation,utils}
   mkdir -p tests/{storage,memory,agents,evaluation}
   mkdir -p migrations results
   ```

4. **Install dependencies**:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install asyncpg redis langgraph langchain-anthropic pytest pytest-asyncio
   ```

5. **Create first files**:
   - `src/storage/base.py` (abstract interface)
   - `src/storage/postgres_adapter.py` (implementation)
   - `migrations/001_active_context.sql` (schema)
   - `tests/storage/test_postgres_adapter.py` (unit tests)

6. **Run database migration**:
   ```bash
   psql "$POSTGRES_URL" -f migrations/001_active_context.sql
   ```

7. **Write and run first test**:
   ```bash
   pytest tests/storage/test_postgres_adapter.py -v
   ```

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

## Conclusion

This plan provides a clear, incremental path from storage adapters to a fully benchmarked memory system. By following the phased approach and weekly milestones, we'll deliver quantitative validation of our hybrid architecture within 8 weeks.

**Key Success Factors:**
1. ✅ Infrastructure already deployed and verified
2. ✅ Comprehensive documentation and ADRs in place
3. ✅ Incremental development with continuous testing
4. ✅ Phoenix observability for real-time debugging
5. ✅ Clear acceptance criteria for each milestone

Let's build this! 🚀
