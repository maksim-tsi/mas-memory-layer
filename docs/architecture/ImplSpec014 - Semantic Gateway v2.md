# Implementation Specification: YAAM Semantic Gateway v2 (RFC-014)

## 1. Schema Definitions

The following strictly enforced Pydantic V2 definitions will be added to `src/api/v2_schemas.py` to support the 4 new endpoints. These abstract away underlying storage schemas like vectors, CIAR scores, and raw Cypher queries.

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any

class L2SemanticFactRequest(BaseModel):
    session_id: str = Field(..., description="The shared session identifier")
    task_id: str = Field(..., description="Current task being executed")
    agent_id: str = Field(..., description="Agent invoking the action")
    action: Literal["store", "retrieve"] = Field(..., description="Action to perform")
    content: Optional[str] = Field(default=None, description="Fact content (required for store)")

class L3SemanticAssimilateRequest(BaseModel):
    session_id: str = Field(..., description="The shared session identifier")
    agent_id: str = Field(..., description="Agent triggering the knowledge assimilation")
    text_to_assimilate: str = Field(..., description="Natural language observation")
    domain_tags: List[str] = Field(default_factory=list, description="Associated domain tags")
    metadata: Dict[str, Any] = Field(..., description="Must contain trace_id for Phoenix")

class L3SemanticQueryRequest(BaseModel):
    agent_id: str = Field(..., description="Agent querying memory")
    nl_query: str = Field(..., description="Natural language query for semantic search")
    top_k: int = Field(default=3, ge=1)
    filters: Dict[str, Any] = Field(default_factory=dict, description="Optional filters like task_id")

class L4SemanticFinalizeRequest(BaseModel):
    task_id: str = Field(..., description="The completed task identifier")
    session_id: str = Field(..., description="The shared session identifier")
    title: str = Field(..., description="Title of the consensus finding")
    final_artifact: str = Field(..., description="The final verified content/output")
    consensus_metadata: Dict[str, Any] = Field(..., description="Votes, disagreements, logic map")
```

## 2. L1 vs L2 Clarification

*   **L1 (Private Agent Scratchpad):** Data in this tier corresponds to an agent's internal monologue or reasoning trace. It must be strictly partitioned by `agent_id` *and* `session_id`. An agent can only read/write to its own L1 partition, maintaining strict privacy.
*   **L2 (Shared Session Working Memory):** Data in this tier acts as a shared whiteboard. It is partitioned solely by `session_id`. Any agent participating in the given `session_id` can read or write facts here. The `agent_id` provided during a write is used strictly for **provenance tracking** (who stated the fact), not for read isolation.

## 3. Controller/Router Mapping

The current direct REST endpoints in `src/api/v2_router.py` will be adapted to function as "Semantic Gateways", masking the underlying tier complexities:

*   **`/v2/semantic/l2/facts`**: Replaces or wraps `/l2/facts`. The incoming `L2SemanticFactRequest` determines the path via the `action` field. `store` invokes `l2_tier.store()` with YAAM automatically applying default `ciar_score`, `certainty`, and `impact` heuristics. `retrieve` maps to `l2_tier.query_by_session()`.
*   **`/v2/semantic/l3/assimilate`**: Replaces the explicit `/l3/entities` endpoint (`EpisodeCreateRequest`). The Orchestrator simply sends raw text (`text_to_assimilate`). The Gateway invokes the Internal LLM Pipeline to parse it, generate the vector embeddings, identify entities, map edges, and finally passes the internally structured `EpisodeStoreInput` to `memory_system.l3_tier.store()`.
*   **`/v2/semantic/l3/query`**: A completely new route mapped to `l3_tier`. It accepts the `nl_query`, delegates to the Internal LLM Pipeline to generate Cypher/vector queries, searches Qdrant/Neo4j, and returns consolidated text facts with appended provenance data (`agent_id`, `session_id`).
*   **`/v2/semantic/l4/finalize`**: Replaces or wraps `/l4/documents`. Maps `final_artifact` to the underlying Typesense `content` argument and structures the `consensus_metadata` securely into the `KnowledgeDocument.metadata` dictionary before calling `memory_system.l4_tier.store()`.

## 4. Internal LLM Pipeline

The core mechanism of the Semantic Gateway v2 offloads generation. During L3 operations, YAAM implements the following intercepts *before* touching DB adapters:

1.  **Pipeline Intercept (Assimilate):** Instead of saving directly, YAAM hands `text_to_assimilate` to an internal prompt chain pointing to the configured LLM API (e.g. OpenRouter). It requests structured JSON output resolving Entities/Relationships and simultaneously requests vector embeddings.
2.  **Pipeline Intercept (Query):** YAAM uses a translation prompt providing the Neo4j schema bounds to generate a Cypher representation of `nl_query`, and additionally calculates query vectors for Qdrant hybrid search.
3.  **Trace Propagation:** The `trace_id` sent in `metadata` is injected directly into `_extract_parent_context()` and an active OTEL tracer `yaam.storage.llm_pipeline` span is instantiated to trace the LLM API latency within Phoenix.

## 5. Error Handling Strategy

Shifting reasoning upstream means YAAM becomes dependent on external LLM availability for memory operations.

*   **Failure Catching:** A dedicated try/except wrapping the LLM adapter calls (Embedding generation + ChatCompletion for Cypher) will catch provider timeouts, 503s, and rate limits.
*   **Translation to HTTP 502:** If the LLM throws an exception, the exception handler will format the provider's traceback into an error descriptor and trigger an explicit `HTTPException(status_code=502, detail="502 Bad Gateway: YAAM internal LLM pipeline failed - <Provider details>")`.
*   **Fail-Fast Constraint:** The system will NOT gracefully degrade to empty inserts; memory operations are fatal if the embedding/Cypher generator fails, ensuring the Orchestrator (TRA) immediately registers a retryable error at the gateway layer.
