# RFC: Endpoint for External Episode Consolidation (LTM Handoff)

**Date:** March 14, 2026
**From:** Cognitive Sandwich Team
**To:** YAAM Core Team
**Status:** Proposed

## 1. Context and Motivation

As part of the decoupling strategy for Phase 3, external cognitive architectures (like the `scm-cognitive-sandwich`) will manage their own ephemeral Working Memory (L1) during active reasoning loops using local state checkpointers.

Once an execution episode concludes (e.g., the LangGraph finishes its solver-repair loop), the external system needs a way to hand off the complete episodic state to YAAM for Long-Term Memory (L2-L4) processing, such as fact extraction, lineage auditing, and semantic indexing.

## 2. Proposed API Contract

We request a new endpoint on the YAAM API Wall to accept these final episode payloads.

**Endpoint:** `POST /v1/memory/episode/consolidate`

**Expected Headers:**

* `traceparent`: Standard W3C Trace Context (e.g., `00-<trace_id>-<span_id>-01`). This is critical. The API Wall must extract this header and use it as the parent context for all internal OpenTelemetry spans generated during the consolidation process.

**Expected Request Payload (JSON):**

```json
{
  "session_id": "string (Matches external thread_id)",
  "agent_id": "string (e.g., 'sandwich-orchestrator')",
  "final_state": {
    "prompt": "...",
    "drafts": [...],
    "solver_iis_logs": [...],
    "final_routing_parameters": {...}
  },
  "metadata": {
    "status": "success | infeasible | timeout",
    "duration_seconds": 14.5,
    "solver_attempts": 3
  }
}

```

## 3. Required YAAM Behavior

When this endpoint is hit, YAAM should:

1. Return a `202 Accepted` or `200 OK` quickly (offloading the heavy extraction to a background task or lifecycle stream).
2. **Bypass L1 Cache:** The system should recognize this is a *completed* historical episode and NOT write it into the active L1 Redis cache. (e.g., automatically apply `skip_l1_write = true`).
3. Route the `final_state` payload through the `EpisodicMemoryTier` (L2) and trigger the `consolidation_engine` / `fact_extractor` to populate Qdrant/Neo4j.

## 4. Next Steps

Please review this RFC. If the payload structure and tracing requirements align with current YAAM capabilities, please create an Implementation Plan to add this route to `src/server.py` and the corresponding handler in `UnifiedMemorySystem`.