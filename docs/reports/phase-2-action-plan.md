# Phase 2 Implementation Action Plan

**Created**: November 2, 2025  
**Target**: Complete ADR-003 Memory Tiers & Lifecycle Engines  
**Current Status**: Phase 1 Complete (30%) | Phase 2 Not Started (0%)  
**Estimated Duration**: 6-8 weeks

---

## Overview

This plan breaks down Phase 2 (Memory Intelligence) into concrete, actionable sprints with clear deliverables and acceptance criteria.

**Goal**: Transform storage adapters into an intelligent four-tier memory system with autonomous lifecycle engines.

---

## Phase 2A: Memory Tier Classes (Weeks 1-3)

### Week 1: L1 Active Context Tier

**Deliverable**: Working L1 tier with turn windowing

**Tasks**:
1. Create `src/memory/tiers/base_tier.py`
   - Abstract base class for all tiers
   - Common interface (store, retrieve, query)
   - Health check and metrics integration

2. Create `src/memory/tiers/active_context_tier.py`
   - Wrap Redis and PostgreSQL adapters
   - Implement turn windowing (keep 10-20 recent)
   - TTL management (24 hours)
   - Session-based isolation

3. Add tests: `tests/memory/test_active_context_tier.py`
   - Turn storage and retrieval
   - Window size enforcement
   - TTL expiration
   - Session isolation

**Acceptance Criteria**:
- [ ] Tier stores conversation turns
- [ ] Automatically limits to N recent turns
- [ ] TTL expires old sessions
- [ ] 80%+ test coverage
- [ ] Performance: <5ms average latency

---

### Week 2: L2 Working Memory Tier

**Deliverable**: Working L2 tier with fact storage

**Tasks**:
1. Update PostgreSQL schema
   ```sql
   -- migrations/002_working_memory_ciar.sql
   ALTER TABLE working_memory 
   ADD COLUMN ciar_score FLOAT DEFAULT 0.0,
   ADD COLUMN certainty FLOAT DEFAULT 0.0,
   ADD COLUMN impact FLOAT DEFAULT 0.0,
   ADD COLUMN age_decay FLOAT DEFAULT 1.0,
   ADD COLUMN recency_boost FLOAT DEFAULT 1.0,
   ADD COLUMN source_uri VARCHAR(500),
   ADD COLUMN last_accessed TIMESTAMP DEFAULT NOW(),
   ADD COLUMN access_count INTEGER DEFAULT 0;
   
   CREATE INDEX idx_ciar_score ON working_memory(ciar_score DESC);
   CREATE INDEX idx_session_ciar ON working_memory(session_id, ciar_score DESC);
   ```

2. Create `src/memory/tiers/working_memory_tier.py`
   - Wrap PostgreSQL adapter
   - Store facts with CIAR metadata
   - Query by session and CIAR threshold
   - Track access counts
   - Update recency on access

3. Add tests: `tests/memory/test_working_memory_tier.py`
   - Fact storage with CIAR data
   - Query by threshold
   - Recency tracking
   - Access count updates

**Acceptance Criteria**:
- [ ] Stores facts with CIAR metadata
- [ ] Queries by CIAR threshold
- [ ] Tracks access patterns
- [ ] Schema migration runs successfully
- [ ] 80%+ test coverage

---

### Week 3: L3 & L4 Tiers

**Deliverable**: L3 episodic and L4 semantic tiers

**L3: Episodic Memory Tier**

1. Update Neo4j schema for bi-temporal model
   ```cypher
   // migrations/003_bitemporal_graph.cypher
   CREATE CONSTRAINT fact_valid_from IF NOT EXISTS
   FOR ()-[r:RELATES_TO]-()
   REQUIRE r.factValidFrom IS NOT NULL;
   
   CREATE INDEX entity_temporal IF NOT EXISTS
   FOR (n:Entity)
   ON (n.factValidFrom, n.factValidTo);
   ```

2. Create `src/memory/tiers/episodic_memory_tier.py`
   - Coordinate Qdrant + Neo4j adapters
   - Dual-index episodes (vector + graph)
   - Store bi-temporal properties
   - Link Qdrant payloads to Neo4j nodes

3. Add tests: `tests/memory/test_episodic_memory_tier.py`

**L4: Semantic Memory Tier**

1. Update Typesense schema
   ```typescript
   // Knowledge document schema
   {
     "name": "knowledge_base",
     "fields": [
       {"name": "knowledge_id", "type": "string"},
       {"name": "content", "type": "string"},
       {"name": "confidence_score", "type": "float"},
       {"name": "source_episodes", "type": "string[]"},
       {"name": "provenance_links", "type": "string[]"}
     ]
   }
   ```

2. Create `src/memory/tiers/semantic_memory_tier.py`
   - Wrap Typesense adapter
   - Store knowledge documents
   - Track provenance to L3 episodes

3. Add tests: `tests/memory/test_semantic_memory_tier.py`

**Acceptance Criteria**:
- [ ] L3 dual-indexes episodes
- [ ] Bi-temporal properties working
- [ ] L4 stores knowledge with provenance
- [ ] Tests passing
- [ ] 80%+ coverage

---

## Phase 2B: CIAR Scoring & Promotion (Weeks 4-5)

### Week 4: CIAR Scoring System

**Deliverable**: Working CIAR calculator

**Tasks**:
1. Create `src/memory/ciar_scorer.py`
   ```python
   class CIARScorer:
       def calculate(self, fact: Dict) -> float:
           """Calculate CIAR score"""
           certainty = self._calculate_certainty(fact)
           impact = self._calculate_impact(fact)
           age_decay = self._calculate_age_decay(fact)
           recency_boost = self._calculate_recency(fact)
           return (certainty * impact) * age_decay * recency_boost
       
       def _calculate_certainty(self, fact: Dict) -> float:
           """Extract from LLM metadata or use heuristics"""
           
       def _calculate_impact(self, fact: Dict) -> float:
           """Classify: preferences (high) vs mentions (low)"""
           
       def _calculate_age_decay(self, fact: Dict) -> float:
           """Exponential decay: exp(-lambda * age_days)"""
           
       def _calculate_recency_boost(self, fact: Dict) -> float:
           """Boost based on access count"""
   ```

2. Add configuration
   ```python
   # config/ciar_config.yaml
   ciar:
     threshold: 0.6
     age_decay_lambda: 0.1
     recency_boost_factor: 0.05
     certainty_default: 0.7
     impact_weights:
       preference: 0.9
       constraint: 0.8
       entity: 0.6
       mention: 0.3
   ```

3. Add tests: `tests/memory/test_ciar_scorer.py`
   - Score calculation
   - Component calculations
   - Threshold checks
   - Edge cases

**Acceptance Criteria**:
- [ ] Calculates all CIAR components
- [ ] Formula: `(C × I) × AD × RB`
- [ ] Configurable parameters
- [ ] 100% test coverage
- [ ] Documented with examples

---

### Week 5: Fact Extraction & Promotion

**Deliverable**: L1→L2 promotion working

**Tasks**:
1. Create `src/memory/fact_extractor.py`
   ```python
   class FactExtractor:
       def __init__(self, llm_client, circuit_breaker):
           self.llm = llm_client
           self.circuit_breaker = circuit_breaker
       
       async def extract_facts(self, turns: List[Dict]) -> List[Dict]:
           """Extract facts from conversation turns"""
           try:
               if self.circuit_breaker.is_open():
                   return await self._rule_based_extraction(turns)
               
               facts = await self._llm_extraction(turns)
               self.circuit_breaker.record_success()
               return facts
           
           except Exception as e:
               self.circuit_breaker.record_failure()
               return await self._rule_based_extraction(turns)
       
       async def _llm_extraction(self, turns: List[Dict]) -> List[Dict]:
           """Use LLM to extract structured facts"""
       
       async def _rule_based_extraction(self, turns: List[Dict]) -> List[Dict]:
           """Fallback: simple regex/NER extraction"""
   ```

2. Create `src/memory/engines/circuit_breaker.py`
   ```python
   class CircuitBreaker:
       def __init__(self, failure_threshold=5, timeout=60):
           self.failure_count = 0
           self.failure_threshold = failure_threshold
           self.timeout = timeout
           self.state = "closed"  # closed, open, half_open
           self.last_failure_time = None
       
       def is_open(self) -> bool:
           """Check if circuit is open (failures exceeded)"""
       
       def record_success(self):
           """Reset failure count on success"""
       
       def record_failure(self):
           """Increment failures, open circuit if threshold hit"""
   ```

3. Create `src/memory/engines/promotion_engine.py`
   ```python
   class PromotionEngine:
       def __init__(self, l1_tier, l2_tier, extractor, scorer):
           self.l1 = l1_tier
           self.l2 = l2_tier
           self.extractor = extractor
           self.scorer = scorer
       
       async def run(self):
           """Background task: promote L1→L2"""
           while True:
               await self._process_sessions()
               await asyncio.sleep(60)  # Run every minute
       
       async def _process_sessions(self):
           """Process all active sessions"""
           sessions = await self.l1.get_active_sessions()
           
           for session_id in sessions:
               turns = await self.l1.get_recent_turns(session_id, limit=5)
               facts = await self.extractor.extract_facts(turns)
               
               for fact in facts:
                   ciar_score = self.scorer.calculate(fact)
                   
                   if ciar_score > 0.6:  # Threshold
                       await self.l2.store_fact({
                           **fact,
                           'ciar_score': ciar_score,
                           'session_id': session_id
                       })
   ```

4. Add tests:
   - `tests/memory/test_fact_extractor.py`
   - `tests/memory/test_circuit_breaker.py`
   - `tests/memory/test_promotion_engine.py`

**Acceptance Criteria**:
- [ ] Extracts facts from turns
- [ ] Calculates CIAR scores
- [ ] Promotes if score > threshold
- [ ] Circuit breaker works
- [ ] Runs asynchronously
- [ ] 80%+ coverage

---

## Phase 2C: Consolidation Engine (Weeks 6-8)

### Week 6: Episode Clustering

**Deliverable**: Time-windowed fact clustering

**Tasks**:
1. Create `src/memory/episode_consolidator.py`
   ```python
   class EpisodeConsolidator:
       def __init__(self, l2_tier, l3_tier, llm_client):
           self.l2 = l2_tier
           self.l3 = l3_tier
           self.llm = llm_client
       
       async def cluster_facts(
           self, 
           session_id: str,
           time_window_hours: int = 24
       ) -> List[List[Dict]]:
           """Cluster facts by time and semantic similarity"""
           facts = await self.l2.get_facts_in_window(
               session_id, 
               hours=time_window_hours
           )
           
           # Time-based clustering
           clusters = self._cluster_by_time(facts, gap_minutes=60)
           
           # Optional: Further cluster by topic
           clusters = self._refine_by_topic(clusters)
           
           return clusters
       
       def _cluster_by_time(self, facts, gap_minutes):
           """Group facts with <N minute gaps"""
       
       def _refine_by_topic(self, clusters):
           """Optional: split large clusters by topic"""
   ```

2. Add tests: `tests/memory/test_episode_consolidator.py`

**Acceptance Criteria**:
- [ ] Clusters facts by time windows
- [ ] Handles gap-based splitting
- [ ] Configurable parameters
- [ ] Tests passing

---

### Week 7: Episode Summarization & Dual Indexing

**Deliverable**: LLM-based episode summaries + dual storage

**Tasks**:
1. Add summarization to `EpisodeConsolidator`
   ```python
   async def summarize_cluster(self, cluster: List[Dict]) -> str:
       """Generate narrative summary of fact cluster"""
       prompt = f"""
       Summarize the following facts into a coherent narrative:
       
       Facts:
       {self._format_facts(cluster)}
       
       Generate a concise summary that captures the key information.
       """
       
       summary = await self.llm.generate(prompt)
       return summary
   ```

2. Add dual indexing
   ```python
   async def store_episode(
       self, 
       cluster: List[Dict],
       summary: str,
       session_id: str
   ) -> Dict:
       """Store episode in both Qdrant and Neo4j"""
       episode_id = f"ep_{uuid.uuid4().hex}"
       
       # 1. Create Neo4j event node
       neo4j_node_id = await self.l3.neo4j.create_event_node({
           'episode_id': episode_id,
           'summary': summary,
           'factValidFrom': cluster[0]['timestamp'],
           'factValidTo': cluster[-1]['timestamp'],
           'sourceType': 'consolidation'
       })
       
       # 2. Store in Qdrant with Neo4j link
       await self.l3.qdrant.store({
           'content': summary,
           'metadata': {
               'episode_id': episode_id,
               'neo4j_node_id': neo4j_node_id,
               'source_facts': [f['id'] for f in cluster],
               'session_id': session_id
           }
       })
       
       return {'episode_id': episode_id, 'neo4j_node_id': neo4j_node_id}
   ```

3. Add tests

**Acceptance Criteria**:
- [ ] Generates episode summaries
- [ ] Stores in both Qdrant and Neo4j
- [ ] Links maintained
- [ ] Bi-temporal properties set
- [ ] Tests passing

---

### Week 8: Consolidation Engine

**Deliverable**: Asynchronous L2→L3 consolidation

**Tasks**:
1. Create `src/memory/engines/consolidation_engine.py`
   ```python
   class ConsolidationEngine:
       def __init__(self, consolidator, config):
           self.consolidator = consolidator
           self.config = config
       
       async def run(self):
           """Background task: consolidate L2→L3"""
           while True:
               await self._consolidate_sessions()
               await asyncio.sleep(3600)  # Hourly
       
       async def _consolidate_sessions(self):
           """Process all sessions needing consolidation"""
           sessions = await self._get_sessions_needing_consolidation()
           
           for session_id in sessions:
               try:
                   clusters = await self.consolidator.cluster_facts(session_id)
                   
                   for cluster in clusters:
                       summary = await self.consolidator.summarize_cluster(cluster)
                       await self.consolidator.store_episode(
                           cluster, summary, session_id
                       )
               
               except Exception as e:
                   logger.error(f"Consolidation failed for {session_id}: {e}")
   ```

2. Add health monitoring
3. Add tests

**Acceptance Criteria**:
- [ ] Runs asynchronously
- [ ] Non-blocking
- [ ] Error handling
- [ ] Metrics collection
- [ ] Tests passing

---

## Phase 2D: Distillation Engine (Weeks 9-10)

### Week 9: Pattern Mining

**Deliverable**: Multi-episode pattern detection

**Tasks**:
1. Create `src/memory/pattern_miner.py`
   ```python
   class PatternMiner:
       async def find_patterns(
           self, 
           episodes: List[Dict],
           min_occurrences: int = 3
       ) -> List[Dict]:
           """Detect recurring patterns across episodes"""
           
           # 1. Extract entities/themes from episodes
           themes = await self._extract_themes(episodes)
           
           # 2. Find recurring themes
           patterns = self._find_recurring(themes, min_occurrences)
           
           # 3. Score pattern significance
           scored = self._score_patterns(patterns)
           
           return scored
   ```

2. Add tests

---

### Week 10: Knowledge Synthesis & Distillation Engine

**Deliverable**: L3→L4 knowledge distillation

**Tasks**:
1. Create `src/memory/knowledge_distiller.py`
   ```python
   class KnowledgeDistiller:
       async def synthesize_knowledge(
           self, 
           pattern: Dict,
           source_episodes: List[str]
       ) -> Dict:
           """Generate generalized knowledge from pattern"""
           prompt = f"""
           Based on these recurring patterns:
           {pattern}
           
           Generate a generalized knowledge statement with confidence.
           """
           
           knowledge = await self.llm.generate(prompt)
           
           return {
               'content': knowledge,
               'confidence': self._calculate_confidence(pattern),
               'source_episodes': source_episodes,
               'provenance_links': source_episodes
           }
   ```

2. Create `src/memory/engines/distillation_engine.py`
   ```python
   class DistillationEngine:
       async def run(self):
           """Background task: distill L3→L4"""
           while True:
               await self._distill_knowledge()
               await asyncio.sleep(86400)  # Daily
   ```

3. Add tests

**Acceptance Criteria**:
- [ ] Mines patterns from episodes
- [ ] Synthesizes knowledge
- [ ] Stores in L4 with provenance
- [ ] Runs asynchronously
- [ ] Tests passing

---

## Phase 2E: Memory Orchestrator (Week 11)

**Deliverable**: Unified system coordination

**Tasks**:
1. Refactor `memory_system.py` → `memory_orchestrator.py`
2. Integrate all tiers
3. Add engine lifecycle management
4. Add multi-tier query coordination
5. Add health aggregation
6. Add tests

**Acceptance Criteria**:
- [ ] Single unified interface
- [ ] Manages all 4 tiers
- [ ] Coordinates 3 engines
- [ ] Health checks
- [ ] Metrics aggregation
- [ ] Tests passing

---

## Success Metrics

### Technical Metrics
- [ ] All tier classes implemented
- [ ] All engines implemented
- [ ] CIAR scoring working
- [ ] L1→L2→L3→L4 flow complete
- [ ] 80%+ test coverage
- [ ] <100ms query latency (L1)
- [ ] Async engines non-blocking

### Functionality Metrics
- [ ] Stores conversation turns (L1)
- [ ] Promotes significant facts (L2)
- [ ] Consolidates episodes (L3)
- [ ] Distills knowledge (L4)
- [ ] Circuit breakers working
- [ ] Bi-temporal model working

### Documentation
- [ ] All classes documented
- [ ] Architecture diagrams updated
- [ ] README reflects reality
- [ ] Migration guides complete

---

## Risk Management

### High-Risk Items
1. **LLM Integration** - External dependency
   - Mitigation: Circuit breaker + fallback
2. **Async Coordination** - Complex concurrency
   - Mitigation: Use proven patterns (asyncio tasks)
3. **Bi-Temporal Model** - Novel implementation
   - Mitigation: Start simple, iterate

### Blocked Items
- Need LLM API access for fact extraction
- Need production database instances for testing

---

## Next Steps

**Week 1 Starts**: Implement L1 Active Context Tier  
**File**: `src/memory/tiers/active_context_tier.py`  
**Tests**: `tests/memory/test_active_context_tier.py`

**First Commit Message**:
```
feat(memory): implement L1 Active Context Tier

- Add base tier abstraction
- Implement active context tier with turn windowing
- Add TTL management and session isolation
- Tests: 80%+ coverage

Part of Phase 2A (ADR-003 implementation)
```

---

**Ready to begin? Start with Week 1!**
