# Phase 7: Integration Testing Plan

**Document Version:** 1.0  
**Date:** October 22, 2025  
**Status:** Ready for Implementation  
**Branch:** `dev-tests`  
**Estimated Time:** 6-8 hours

---

## Executive Summary

Phase 7 focuses on implementing comprehensive integration tests that verify multi-adapter workflows, error recovery scenarios, data consistency, and performance under realistic conditions. This document provides detailed API analysis for each adapter to ensure correct integration test implementation.

**Current Status:**
- ✅ All 5 storage adapters have >80% unit test coverage
- ✅ Overall storage coverage: 83%
- ✅ 245 unit tests passing (100% success rate)
- ⏳ Integration tests: 0 tests (to be implemented)

**Goal:** Add 18-25 integration tests covering multi-adapter scenarios.

---

## Storage Adapter API Reference

### 1. RedisAdapter API

**Purpose:** L1/L2 cache for conversation turns and session data

**Configuration:**
```python
config = {
    'host': '192.168.107.172',
    'port': 6379,
    'db': 0,  # Use different DB for tests
    'decode_responses': True
}
```

**Data Format:**
```python
# Required fields for store()
{
    'session_id': str,    # Session identifier
    'turn_id': int,       # Turn number (sequential)
    'content': str,       # Turn content/message
    'metadata': dict      # Optional: additional data
}

# Returns: "session:{session_id}:turns:{turn_id}"
# Example: "session:abc123:turns:1"
```

**Key Methods:**
- `store(data: Dict)` → `str` (returns composite key)
- `retrieve(record_id: str)` → `Optional[Dict]`
- `search(query: Dict)` → `List[Dict]` (search by session_id)
- `delete(record_id: str)` → `bool`
- `store_batch(items: List[Dict])` → `List[str]`

**Search Query Format:**
```python
query = {
    'session_id': 'abc123',  # Required
    'limit': 10              # Optional, default 10
}
```

**Notes:**
- Auto-generates turn_id if not provided
- Implements TTL (24 hours default)
- Uses Redis lists (LPUSH/LRANGE) for conversation history
- Window size configurable (default: 50 turns)

---

### 2. PostgresAdapter API

**Purpose:** Relational storage for structured data and metadata

**Configuration:**
```python
config = {
    'url': 'postgresql://user:password@host:port/database',
    'table': 'active_context',  # Optional, default: 'active_context'
    'pool_size': 10,            # Optional
    'min_size': 2               # Optional
}
```

**Data Format:**
```python
# Required field
{
    'id': str,  # Must be provided or auto-generated
    # ... any additional fields
}

# Schema-flexible: stores arbitrary JSON columns
# Primary key: 'id' column
```

**Key Methods:**
- `store(data: Dict)` → `str` (returns ID)
- `retrieve(id: str)` → `Optional[Dict]`
- `search(query: Dict)` → `List[Dict]`
- `delete(id: str)` → `bool`
- `store_batch(items: List[Dict])` → `List[str]`

**Search Query Format:**
```python
query = {
    'session_id': 'abc123',    # Filter by field
    'limit': 10,               # Optional
    'order_by': 'created_at'   # Optional
}
```

**Notes:**
- Uses asyncpg connection pool
- Supports JSON columns for flexible data
- Auto-generates UUID if 'id' not provided
- Table must exist (see migrations/)

---

### 3. QdrantAdapter API

**Purpose:** Vector similarity search for semantic memory

**Configuration:**
```python
config = {
    'url': 'http://192.168.107.187:6333',
    'collection_name': 'episodic_memory',
    'vector_size': 384,      # Must match embedding model
    'distance': 'Cosine'     # or 'Euclid', 'Dot'
}
```

**Data Format:**
```python
# Required fields for store()
{
    'vector': List[float],    # Embedding vector (length = vector_size)
    'content': str,           # Text content
    'payload': dict           # Optional: metadata
}

# Returns: str (point UUID)
```

**Key Methods:**
- `store(data: Dict)` → `str` (returns point ID)
- `retrieve(id: str)` → `Optional[Dict]`
- `search(query: Dict)` → `List[Dict]` (vector similarity)
- `delete(id: str)` → `bool`
- `store_batch(items: List[Dict])` → `List[str]`

**Search Query Format:**
```python
query = {
    'vector': [0.1, 0.2, ...],  # Query vector (required)
    'limit': 10,                # Optional, default 10
    'score_threshold': 0.7,     # Optional: min similarity
    'filter': {                 # Optional: metadata filter
        'must': [
            {'key': 'category', 'match': {'value': 'operations'}}
        ]
    }
}
```

**Filter Format (Advanced):**
```python
{
    'must': [dict],      # AND conditions
    'should': [dict],    # OR conditions
    'must_not': [dict]   # NOT conditions
}
```

**Notes:**
- Requires embedding generation (not handled by adapter)
- Creates collection automatically on connect
- Supports complex filtering on payload fields
- Returns results with similarity scores

---

### 4. Neo4jAdapter API

**Purpose:** Graph relationships for semantic networks

**Configuration:**
```python
config = {
    'url': 'bolt://192.168.107.187:7687',
    'username': 'neo4j',
    'password': 'your_password',
    'database': 'neo4j'  # Optional, default: 'neo4j'
}
```

**Data Format:**
```python
# For storing nodes
{
    'id': str,              # Node ID
    'label': str,           # Node type/label
    'properties': dict      # Node properties
}

# For relationships (via search)
query = {
    'source_id': 'node1',
    'target_id': 'node2',
    'relationship_type': 'RELATED_TO',
    'properties': dict      # Optional
}
```

**Key Methods:**
- `store(data: Dict)` → `str` (stores/updates node)
- `retrieve(id: str)` → `Optional[Dict]`
- `search(query: Dict)` → `List[Dict]` (Cypher query)
- `delete(id: str)` → `bool`
- `create_relationship(source, target, type, props)` → `bool`

**Search Query Format:**
```python
# Find nodes
query = {
    'label': 'Agent',       # Optional: node label
    'properties': {         # Optional: property filters
        'status': 'active'
    },
    'limit': 10
}

# Custom Cypher
query = {
    'cypher': 'MATCH (n:Agent) WHERE n.status = $status RETURN n',
    'parameters': {'status': 'active'}
}
```

**Notes:**
- Supports native Cypher queries
- Handles node creation and relationship management
- Auto-generates IDs if not provided
- Supports graph traversal queries

---

### 5. TypesenseAdapter API

**Purpose:** Full-text search with typo tolerance

**Configuration:**
```python
config = {
    'url': 'http://192.168.107.187:8108',
    'api_key': 'xyz',
    'collection_name': 'documents',
    'schema': {              # Optional: auto-creates if not exists
        'name': 'documents',
        'fields': [
            {'name': 'id', 'type': 'string'},
            {'name': 'content', 'type': 'string'},
            {'name': 'category', 'type': 'string', 'facet': True}
        ]
    }
}
```

**Data Format:**
```python
# Must match schema
{
    'id': str,         # Optional: auto-generated if not provided
    'content': str,    # Searchable text
    'category': str,   # Facetable field
    # ... other schema fields
}
```

**Key Methods:**
- `store(data: Dict)` → `str` (returns document ID)
- `retrieve(id: str)` → `Optional[Dict]`
- `search(query: Dict)` → `List[Dict]` (full-text search)
- `delete(id: str)` → `bool`
- `store_batch(items: List[Dict])` → `List[str]`

**Search Query Format:**
```python
query = {
    'q': 'port congestion',      # Search query (required)
    'query_by': 'content',       # Fields to search (required)
    'filter_by': 'category:ops', # Optional: filter
    'limit': 10,                 # Optional, default 10
    'sort_by': 'created_at:desc' # Optional
}
```

**Notes:**
- Typo-tolerant by default
- Supports faceted search
- Fast full-text search with ranking
- Schema must be defined at creation

---

## Integration Test Categories

### Category 1: Multi-Adapter Workflows (6-8 tests)

**Goal:** Verify adapters work together in realistic scenarios

#### Test 1.1: Cache-Write-Through Pattern
```python
async def test_cache_write_through_redis_postgres():
    """
    Scenario: Store conversation in Redis, metadata in Postgres
    
    Flow:
    1. User message arrives → store in Redis (fast cache)
    2. Extract metadata → store in Postgres (durable)
    3. Retrieve from Redis for active session
    4. Fall back to Postgres if Redis expires
    """
```

**Adapters:** Redis + Postgres  
**Time:** 20 minutes

#### Test 1.2: Vector Search with Metadata Enrichment
```python
async def test_vector_search_with_postgres_metadata():
    """
    Scenario: Semantic search enriched with structured data
    
    Flow:
    1. Generate embeddings → store in Qdrant
    2. Store metadata (title, author, etc.) → Postgres
    3. Perform vector search → get relevant doc IDs
    4. Enrich results with metadata from Postgres
    """
```

**Adapters:** Qdrant + Postgres  
**Time:** 30 minutes

#### Test 1.3: Full-Text Search with Graph Relations
```python
async def test_fulltext_search_with_graph_enrichment():
    """
    Scenario: Document search enriched with relationships
    
    Flow:
    1. Index documents in Typesense
    2. Store entity relationships in Neo4j
    3. Search documents by text
    4. Enrich with related entities from graph
    """
```

**Adapters:** Typesense + Neo4j  
**Time:** 30 minutes

#### Test 1.4: Multi-Layer Memory Retrieval
```python
async def test_multi_layer_memory_retrieval():
    """
    Scenario: Retrieve from multiple tiers
    
    Flow:
    1. Check Redis (L1 - active context)
    2. Check Postgres (L2 - recent sessions)
    3. Check Qdrant (L3 - semantic search)
    4. Combine results with relevance scoring
    """
```

**Adapters:** Redis + Postgres + Qdrant  
**Time:** 40 minutes

#### Test 1.5: Batch Operations Coordination
```python
async def test_coordinated_batch_operations():
    """
    Scenario: Batch store across multiple adapters
    
    Flow:
    1. Batch store 100 items in Postgres
    2. Generate embeddings → batch store in Qdrant
    3. Index content → batch store in Typesense
    4. Verify consistency across all stores
    """
```

**Adapters:** Postgres + Qdrant + Typesense  
**Time:** 40 minutes

#### Test 1.6: Cascade Delete Coordination
```python
async def test_cascade_delete_across_adapters():
    """
    Scenario: Delete data from all related stores
    
    Flow:
    1. Store in Redis, Postgres, Qdrant
    2. Trigger delete by ID
    3. Verify removed from all adapters
    4. Check orphaned references don't exist
    """
```

**Adapters:** Redis + Postgres + Qdrant  
**Time:** 30 minutes

**Subtotal:** 6 tests, ~3 hours

---

### Category 2: Error Recovery (5-6 tests)

**Goal:** Verify graceful failure and recovery

#### Test 2.1: Connection Failure Recovery
```python
async def test_reconnection_after_network_failure():
    """
    Scenario: Adapter recovers from connection loss
    
    Flow:
    1. Establish connection
    2. Simulate disconnect
    3. Attempt operation → reconnect automatically
    4. Verify operation succeeds after reconnect
    """
```

**Adapters:** Redis, Postgres (separate tests)  
**Time:** 30 minutes

#### Test 2.2: Graceful Degradation
```python
async def test_graceful_degradation_cache_failure():
    """
    Scenario: System continues when cache fails
    
    Flow:
    1. Store in Redis + Postgres
    2. Disconnect Redis
    3. Retrieve from Postgres (fallback)
    4. System continues without cache
    """
```

**Adapters:** Redis + Postgres  
**Time:** 30 minutes

#### Test 2.3: Timeout Handling
```python
async def test_operation_timeout_handling():
    """
    Scenario: Operations respect timeout limits
    
    Flow:
    1. Configure short timeout
    2. Perform slow operation
    3. Verify timeout exception raised
    4. Verify partial state handled correctly
    """
```

**Adapters:** All adapters (health checks)  
**Time:** 30 minutes

#### Test 2.4: Concurrent Operations Isolation
```python
async def test_concurrent_operations_dont_interfere():
    """
    Scenario: Parallel operations are isolated
    
    Flow:
    1. Launch 10 concurrent store operations
    2. Each with unique data
    3. Verify all complete successfully
    4. Verify no data corruption/mixing
    """
```

**Adapters:** Postgres + Redis  
**Time:** 30 minutes

#### Test 2.5: Partial Batch Failure Handling
```python
async def test_partial_batch_failure_recovery():
    """
    Scenario: Handle failures in batch operations
    
    Flow:
    1. Submit batch with mix of valid/invalid items
    2. Track which succeed vs fail
    3. Verify successful items stored
    4. Verify failed items reported correctly
    """
```

**Adapters:** Postgres, Qdrant  
**Time:** 30 minutes

**Subtotal:** 5 tests, ~2.5 hours

---

### Category 3: Data Consistency (4-5 tests)

**Goal:** Verify data integrity across adapters

#### Test 3.1: Cache Coherence
```python
async def test_cache_invalidation_on_update():
    """
    Scenario: Cache invalidates when source updates
    
    Flow:
    1. Store in Redis + Postgres
    2. Update in Postgres
    3. Verify Redis cache invalidated
    4. Next read fetches fresh data
    """
```

**Adapters:** Redis + Postgres  
**Time:** 30 minutes

#### Test 3.2: Cross-Adapter Data Integrity
```python
async def test_data_consistency_after_batch_operations():
    """
    Scenario: Batch operations maintain consistency
    
    Flow:
    1. Batch store 50 items in Postgres
    2. Generate embeddings → store in Qdrant
    3. Verify same item count in both
    4. Verify IDs match between adapters
    """
```

**Adapters:** Postgres + Qdrant  
**Time:** 40 minutes

#### Test 3.3: Transaction-Like Behavior
```python
async def test_rollback_on_partial_failure():
    """
    Scenario: Clean up on multi-adapter failure
    
    Flow:
    1. Store in Postgres (succeeds)
    2. Store in Qdrant (fails)
    3. Roll back Postgres changes
    4. Verify clean state (no partial data)
    """
```

**Adapters:** Postgres + Qdrant  
**Time:** 40 minutes

#### Test 3.4: Idempotency Verification
```python
async def test_idempotent_operations():
    """
    Scenario: Same operation twice = same result
    
    Flow:
    1. Store item with ID
    2. Store same item again (upsert)
    3. Verify only one copy exists
    4. Verify data matches latest
    """
```

**Adapters:** All adapters  
**Time:** 30 minutes

**Subtotal:** 4 tests, ~2.5 hours

---

### Category 4: Performance & Stress (3-4 tests)

**Goal:** Verify performance under realistic load

#### Test 4.1: Concurrent Read/Write Load
```python
async def test_concurrent_read_write_performance():
    """
    Scenario: System handles mixed load
    
    Flow:
    1. 10 concurrent writers
    2. 20 concurrent readers
    3. Run for 30 seconds
    4. Verify all operations succeed
    5. Measure throughput and latency
    """
```

**Adapters:** Redis + Postgres  
**Time:** 40 minutes

#### Test 4.2: Large Batch Processing
```python
async def test_large_batch_performance():
    """
    Scenario: Process large batches efficiently
    
    Flow:
    1. Generate 1000 items
    2. Batch store in Postgres (100 at a time)
    3. Batch index in Typesense
    4. Verify completion time < threshold
    """
```

**Adapters:** Postgres + Typesense  
**Time:** 30 minutes

#### Test 4.3: Memory Usage Under Load
```python
async def test_memory_footprint_during_operations():
    """
    Scenario: Monitor memory usage
    
    Flow:
    1. Baseline memory measurement
    2. Perform 1000 operations
    3. Measure peak memory
    4. Verify no memory leaks
    """
```

**Adapters:** All adapters  
**Time:** 40 minutes

**Subtotal:** 3 tests, ~2 hours

---

## Implementation Plan

### Phase 7.1: Setup & Infrastructure (1 hour)

1. **Create test fixtures module**
   - `tests/integration/fixtures.py`
   - Shared adapter fixtures with proper configs
   - Cleanup utilities
   - Test data generators

2. **Create helper utilities**
   - `tests/integration/helpers.py`
   - Embedding generation mock
   - Data consistency checkers
   - Performance measurement tools

3. **Update conftest.py**
   - Add integration test markers
   - Configure test database/collections
   - Setup teardown automation

### Phase 7.2: Multi-Adapter Workflows (3 hours)

- Implement 6 workflow tests
- Focus on realistic use cases
- Document each scenario

### Phase 7.3: Error Recovery (2.5 hours)

- Implement 5 error recovery tests
- Test connection failures
- Test timeout scenarios

### Phase 7.4: Data Consistency (2.5 hours)

- Implement 4 consistency tests
- Verify cache coherence
- Test batch integrity

### Phase 7.5: Performance (Optional, 2 hours)

- Implement 3 performance tests
- Measure under load
- Document benchmarks

**Total Estimated Time:** 6-11 hours (core: 6-8 hours)

---

## Test Data Requirements

### Sample Embedding Generator
```python
def generate_test_embedding(text: str, size: int = 384) -> List[float]:
    """
    Generate deterministic test embedding.
    
    Note: For production, use actual embedding model.
    For tests, use reproducible mock.
    """
    import hashlib
    import struct
    
    # Hash text to get deterministic seed
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
    import random
    random.seed(seed)
    
    # Generate normalized vector
    vector = [random.random() for _ in range(size)]
    magnitude = sum(x**2 for x in vector) ** 0.5
    return [x / magnitude for x in vector]
```

### Sample Data Generators
```python
def generate_conversation_turn(session_id: str, turn_id: int) -> dict:
    """Generate test conversation turn for Redis."""
    return {
        'session_id': session_id,
        'turn_id': turn_id,
        'content': f'Test message {turn_id} for session {session_id}',
        'metadata': {'role': 'user', 'timestamp': datetime.now().isoformat()}
    }

def generate_metadata_record(doc_id: str) -> dict:
    """Generate test metadata for Postgres."""
    return {
        'id': doc_id,
        'title': f'Document {doc_id}',
        'author': 'test_agent',
        'category': 'test',
        'created_at': datetime.now().isoformat()
    }

def generate_vector_point(doc_id: str, content: str) -> dict:
    """Generate test vector point for Qdrant."""
    return {
        'vector': generate_test_embedding(content),
        'content': content,
        'payload': {'doc_id': doc_id, 'source': 'test'}
    }
```

---

## Success Criteria

### Quantitative Metrics
- ✅ **18-25 integration tests** implemented
- ✅ **100% pass rate** on integration test suite
- ✅ **All adapters tested** in multi-adapter scenarios
- ✅ **<5 second average** test execution time per test
- ✅ **Proper cleanup** (no test data pollution)

### Qualitative Metrics
- ✅ Tests demonstrate **realistic workflows**
- ✅ Error scenarios **well-documented**
- ✅ Tests are **maintainable** and **readable**
- ✅ Fixtures are **reusable** across tests
- ✅ Documentation explains **what/why/how**

---

## Known Challenges & Solutions

### Challenge 1: Test Data Cleanup
**Problem:** Integration tests create real data in databases  
**Solution:** 
- Use unique IDs (UUID) for each test run
- Implement teardown fixtures that delete test data
- Use separate databases/collections for tests
- Document cleanup procedures

### Challenge 2: Embedding Generation
**Problem:** Real embedding models are slow/expensive  
**Solution:**
- Use deterministic mock embeddings for tests
- Hash-based generation for reproducibility
- Document that production needs real embeddings

### Challenge 3: Test Isolation
**Problem:** Tests may interfere with each other  
**Solution:**
- Use unique session IDs per test
- Parallel-safe fixtures
- Cleanup between tests
- Use separate DB numbers for Redis

### Challenge 4: External Service Dependencies
**Problem:** Tests require all services running  
**Solution:**
- Skip tests if services unavailable (pytest markers)
- Document service requirements in README
- Provide docker-compose for local testing
- CI/CD environment setup documentation

### Challenge 5: Performance Test Variability
**Problem:** Performance tests may be flaky  
**Solution:**
- Use relative thresholds (not absolute)
- Multiple runs and averaging
- Mark as slow tests (separate execution)
- Focus on correctness over speed

---

## Next Steps

1. **Review this plan** with team
2. **Set up test infrastructure** (fixtures, helpers)
3. **Implement Category 1** (Multi-Adapter Workflows) - highest priority
4. **Implement Category 2** (Error Recovery)
5. **Implement Category 3** (Data Consistency)
6. **Optional: Category 4** (Performance)
7. **Document results** in DEVLOG
8. **Update README** with integration test instructions

---

## Appendix: Quick Reference

### Running Integration Tests
```bash
# All integration tests
pytest tests/integration/ -v

# Specific category
pytest tests/integration/test_multi_adapter_workflows.py -v

# With coverage
pytest tests/integration/ --cov=src --cov-report=term-missing

# Skip slow tests
pytest tests/integration/ -m "not slow"
```

### Test Markers
```python
@pytest.mark.integration        # All integration tests
@pytest.mark.slow               # Long-running tests
@pytest.mark.requires_qdrant    # Requires Qdrant service
@pytest.mark.requires_neo4j     # Requires Neo4j service
```

### Environment Variables
```bash
# Required for integration tests
export REDIS_HOST=192.168.107.172
export POSTGRES_URL=postgresql://mas_user:pwd@192.168.107.172:5432/mas_memory
export QDRANT_URL=http://192.168.107.187:6333
export NEO4J_URL=bolt://192.168.107.187:7687
export TYPESENSE_URL=http://192.168.107.187:8108
export TYPESENSE_API_KEY=xyz
```

---

**Document Complete**  
**Next Action:** Begin Phase 7.1 (Setup & Infrastructure)  
**Estimated Completion:** 1-2 days with focused effort
