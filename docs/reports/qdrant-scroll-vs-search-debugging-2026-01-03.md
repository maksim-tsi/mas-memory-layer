# Qdrant Scroll vs Search Debugging Report

**Date:** 2026-01-03  
**Author:** GitHub Copilot (Claude Opus 4.5)  
**Status:** Resolved  
**Related Module:** `src/storage/qdrant_adapter.py`, `src/memory/tiers/episodic_memory_tier.py`  
**Related Test:** `tests/integration/test_memory_lifecycle.py::TestMemoryLifecycleFlow::test_l2_to_l3_consolidation_with_episode_clustering`

---

## 1. Executive Summary

A persistent test failure in the L2→L3 consolidation test was traced to a **fundamental misunderstanding of Qdrant's search semantics**. The test stored episodes with real embeddings but searched using dummy vectors, causing filter-based queries to return zero results despite data being correctly persisted. The fix was to add a `scroll()` method to `QdrantAdapter` for pure filter-based retrieval.

---

## 2. Problem Definition

### 2.1 Affected Functionality
- **Module:** L3 Episodic Memory Tier (`src/memory/tiers/episodic_memory_tier.py`)
- **Storage Adapter:** Qdrant Vector Store (`src/storage/qdrant_adapter.py`)
- **Lifecycle Engine:** Consolidation Engine (`src/memory/engines/consolidation_engine.py`)

### 2.2 Symptom
The test `test_l2_to_l3_consolidation_with_episode_clustering` would:
1. Successfully consolidate L2 facts into an L3 episode
2. Store the episode in Qdrant with `status=COMPLETED`
3. Fail assertion: `AssertionError: No episodes found in Qdrant`

### 2.3 Intermittent Behavior
- Test **passed** immediately after recreating the Qdrant collection from scratch
- Test **failed** on subsequent runs with accumulated test data
- This pattern suggested the issue was related to data accumulation, not storage

---

## 3. Information Collected

### 3.1 Debug Instrumentation Added

We added comprehensive debug logging to trace the data flow:

**In `QdrantAdapter.store()`:**
```python
print(f"DEBUG QdrantAdapter.store(): collection={collection_name}, point_id={point_id}, vector_len={len(vector)}")
print(f"DEBUG QdrantAdapter.store(): qdrant_response={update_result}")
```

**In `EpisodicMemoryTier._store_in_qdrant()`:**
```python
print(f"DEBUG L3._store_in_qdrant(): qdrant_adapter_id={qdrant_id}, url={qdrant_url}")
print(f"DEBUG L3._store_in_qdrant(): point_id={point_id}, session_id={session_id}, collection={collection}")
```

**In test file (5-step checkpoint system):**
- STEP 0: Point count BEFORE consolidation
- STEP 1: Adapter identity verification (same object?)
- STEP 2: Point count AFTER consolidation (delta calculation)
- STEP 4: Scroll all points, identify our session

### 3.2 Critical Debug Output (Final Run Before Fix)

```
DEBUG STEP0: Points BEFORE consolidation = 8
DEBUG QdrantAdapter.store(): qdrant_response=operation_id=9 status=<UpdateStatus.COMPLETED: 'completed'>
DEBUG STEP2: Collection 'episodes' points_count=9 (was 8 before)
DEBUG STEP2: Points ADDED = 1
DEBUG STEP4: Scroll found 9 points
DEBUG STEP4: Point[7] id=d7daecdd-..., session_id=test-404e796a94fc <-- OUR SESSION
DEBUG STEP4: Found our session (test-404e796a94fc): True

DEBUG QdrantAdapter.search(): filter=should=[FieldCondition(key='session_id', match=MatchValue(value='test-404e796a94fc')...)], limit=10
DEBUG QdrantAdapter.search(): raw_results=0   ← ZERO RESULTS WITH FILTER!

DEBUG QdrantAdapter.search(): filter=None, limit=10
DEBUG QdrantAdapter.search(): raw_results=1
DEBUG: Result[0] session_id=test-908732c7ca20, score=0.0019205483  ← WRONG SESSION!
```

### 3.3 Key Observations

1. **Storage worked perfectly:** `status=COMPLETED`, point count increased by 1
2. **Our session exists:** Scroll explicitly found `session_id=test-404e796a94fc` at Point[7]
3. **Filtered search returned 0:** Despite our data existing
4. **Unfiltered search returned wrong session:** With similarity score ~0.002 (nearly orthogonal)

---

## 4. Root Cause Analysis

### 4.1 The Fundamental Issue

**Qdrant's `search()` is vector-similarity-first, even with filters.**

The search algorithm:
1. Finds the N most similar vectors to the query vector
2. THEN applies filters to those results
3. Returns filtered subset

### 4.2 Why The Test Failed

The test code was:
```python
qdrant_results = await qdrant_adapter.search({
    'vector': [0.1] * 768,  # DUMMY VECTOR - all 0.1 values
    'filter': {'session_id': test_session_id},
    'limit': 10,
})
```

**Problem:** The dummy vector `[0.1, 0.1, ..., 0.1]` has ~0 cosine similarity to real Gemini embeddings:
- Unfiltered search returned the most similar point with score `0.0019` (essentially random)
- Our session's point wasn't even in the top-10 by similarity
- When the filter was applied to those top-10, our session wasn't among them → 0 results

### 4.3 Why Collection Recreation Worked

When the collection was empty/freshly created:
- Our test episode was the ONLY point
- ANY similarity search would return it (it's the only option)
- Filter then matched it → test passed

With accumulated data from previous test runs:
- 8+ old points competed for top-10 slots
- Old points might be more "similar" to the dummy vector by random chance
- Our session's point got crowded out → filter returned nothing

---

## 5. Solution Implemented

### 5.1 Added `scroll()` Method to QdrantAdapter

**File:** `src/storage/qdrant_adapter.py`

```python
async def scroll(
    self,
    filter_dict: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    with_payload: bool = True,
    with_vectors: bool = False,
    collection_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Scroll through points using filter-only retrieval (no vector similarity).
    
    Unlike search(), scroll() retrieves points purely based on filter criteria
    without requiring a query vector or vector similarity comparison. This is
    useful for retrieving all points matching a session_id or other metadata.
    """
```

### 5.2 Updated Test to Use Scroll

**File:** `tests/integration/test_memory_lifecycle.py`

```python
# OLD (broken): Vector similarity + filter
qdrant_results = await qdrant_adapter.search({
    'vector': [0.1] * l3_tier.vector_size,
    'filter': {'session_id': test_session_id},
    'limit': 10,
})

# NEW (correct): Pure filter-based retrieval
qdrant_results = await qdrant_adapter.scroll(
    filter_dict={'session_id': test_session_id},
    limit=10,
    collection_name=l3_tier.collection_name,
)
```

### 5.3 Why This Works

| Aspect | `search()` | `scroll()` |
|--------|-----------|-----------|
| Requires query vector | Yes | No |
| Uses vector similarity | Yes (primary) | No |
| Filter application | Post-similarity | Primary |
| Use case | "Find similar to X" | "Find all matching Y" |

For session-based retrieval where we want **all episodes for a session** (regardless of embedding similarity), `scroll()` is the correct API.

---

## 6. Verification

### 6.1 Test Results After Fix

```bash
$ pytest test_l2_to_l3_consolidation_with_episode_clustering -v
# Run 1: PASSED (9.12s)
# Run 2: PASSED (9.23s)  
# Run 3: PASSED (8.10s)
```

### 6.2 Full Lifecycle Test Suite

```bash
$ pytest tests/integration/test_memory_lifecycle.py -v
# Results: 4 passed, 6 skipped in 62.87s
```

All core lifecycle tests now pass consistently.

---

## 7. Lessons Learned

### 7.1 New Entry for lessons-learned.md

| Date | Incident ID | Environment | Symptom | Root Cause | Mitigation | Status |
|------|-------------|-------------|---------|------------|------------|--------|
| 2026-01-03 | LL-20260103-01 | Remote Ubuntu VM + Qdrant | Test `test_l2_to_l3_consolidation_with_episode_clustering` fails with "No episodes found in Qdrant" despite successful store operation | Qdrant `search()` is vector-similarity-first; using dummy query vector `[0.1]*768` with filters returned 0 results because real embeddings aren't similar to the dummy | Added `scroll()` method to QdrantAdapter for pure filter-based retrieval; use `scroll()` when retrieving by metadata (session_id) rather than semantic similarity | Adopted |

### 7.2 Design Guidelines

1. **Know Your Query Semantics:**
   - Use `search()` for "find items semantically similar to X"
   - Use `scroll()` for "find all items matching filter Y"

2. **Test Data Isolation:**
   - Tests with accumulated data behave differently than tests on empty collections
   - Consider adding cleanup fixtures that remove test data by session_id

3. **Debug Checkpoints:**
   - The 5-step checkpoint pattern (before/after counts, scroll verification) was effective
   - Can be reused for similar storage debugging

4. **Vector Similarity Scores:**
   - Scores near 0 indicate vectors are nearly orthogonal (unrelated)
   - Gemini embeddings for real text are not similar to uniform dummy vectors

---

## 8. Files Changed

| File | Change Type | Description |
|------|------------|-------------|
| `src/storage/qdrant_adapter.py` | Added method | New `scroll()` method for filter-only retrieval |
| `tests/integration/test_memory_lifecycle.py` | Modified | Changed Qdrant verification from `search()` to `scroll()` |
| `docs/reports/qdrant-scroll-vs-search-debugging-2026-01-03.md` | Created | This report |
| `docs/plan/phase5-readiness-checklist-2026-01-02.md` | Updated | Added debugging session documentation |
| `docs/lessons-learned.md` | Updated | Added incident LL-20260103-01 |

---

## 9. Related Documentation

- [ADR-003: Four Layers Memory](../ADR/003-four-layers-memory.md) - L3 dual-indexing architecture
- [Qdrant Scroll API](https://qdrant.tech/documentation/concepts/search/#scroll-through-all-points) - Official documentation
- [Phase 5 Readiness Checklist](../plan/phase5-readiness-checklist-2026-01-02.md) - Overall readiness tracking
