# YAAM v2 Connection Policy: Correct Integration Patterns

**Status:** Reference Implementation  
**Last Updated:** April 17, 2026  
**Scope:** Multi-tier memory gateway integration, distributed tracing, and reliability protocols

---

## Table of Contents

1. [L1 Policy: Optional in MAS_V2_MODE](#l1-policy-optional-in-mas_v2_mode)
2. [L3 Reliability: Dual-Index Payload Requirements](#l3-reliability-dual-index-payload-requirements)
3. [Retry & Timeout Logic: httpx Configuration](#retry--timeout-logic-httpx-configuration)
4. [Environment Checklist](#environment-checklist)
5. [Integration Workflow](#integration-workflow)
6. [Troubleshooting and Cross-Node Debugging](#troubleshooting-and-cross-node-debugging)

---

## L1 Policy: Optional in MAS_V2_MODE

### Why L1 is Optional

In **MAS_V2_MODE**, L1 (Active Context tier) is **optional** because **LangGraph state management supersedes it**. The v2 gateway returns `HTTP 501 NOT_IMPLEMENTED` when L1 is not configured, signaling that clients must provide conversation context via the graph state instead of relying on server-side session storage.

```python
# From src/api/v2_router.py::create_turn()
if not state.l1_tier:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="L1 Active Context tier is not configured in the current YAAM environment.",
    )
```

### Operational Implications

- **Traditional Mode** (L1 enabled): The server manages turn history in Redis + PostgreSQL. Clients post turns; the server maintains the session window.
- **MAS_V2_MODE** (L1 optional): The client or orchestrator (LangGraph, etc.) manages turn history in graph state. The server is stateless with respect to L1.

### When to Enable L1

Enable L1 only if your integration requires:
1. **Server-side session persistence** across agent restarts
2. **Automatic TTL-based cleanup** of old turns (24-hour window by default)
3. **Cross-agent session sharing** without explicit graph state synchronization

### When to Disable L1

Disable L1 if:
1. Your orchestrator (LangGraph) maintains all state explicitly
2. You prefer stateless API semantics
3. You want minimal memory footprint on the YAAM server

### L1 Configuration (Optional)

If L1 is enabled, the following environment variables are required:

```bash
# Redis for L1 hot cache
REDIS_URL=redis://<YOUR_DEV_NODE_IP>:6379

# PostgreSQL for L1 persistent backup
POSTGRES_URL=postgresql://yaam_user:your-password@<YOUR_DEV_NODE_IP>:5432/yaam_db

# L1 configuration (optional, defaults shown)
# L1_WINDOW_SIZE=20                # Max turns per session
# L1_TTL_HOURS=24                  # TTL in hours
```

---

## L3 Reliability: Dual-Index Payload Requirements

### Architecture

L3 (Episodic Memory) uses **dual indexing** for reliability and querying flexibility:
- **Qdrant**: Vector embeddings for semantic similarity search
- **Neo4j**: Graph structure for relationship traversal and temporal reasoning

Both indices must stay synchronized. If either fails, the `/v2/memory/l3/assimilate` endpoint returns `HTTP 502 BAD_GATEWAY`.

### L3/Assimilate Endpoint Payload Contract

**POST** `/v2/memory/l3/assimilate`

#### Required Headers

```http
Content-Type: application/json
traceparent: <W3C_TRACE_ID>  # ✅ MANDATORY for Phoenix cross-node debugging
```

The `traceparent` header must conform to the [W3C Trace Context](https://www.w3.org/TR/trace-context/) standard:

```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
             └─────────────────────────────────────────────────────┘
             Format: 00-<trace-id>-<parent-id>-<trace-flags>
```

**Why**: Phoenix Arize uses the `traceparent` header to correlate requests across distributed nodes, enabling end-to-end tracing of fact assimilation pipelines.

#### Request Body

```json
{
  "session_id": "session-abc123",
  "agent_id": "agent-001",
  "text_to_assimilate": "User prefers asynchronous communication on weekends.",
  "domain_tags": ["preferences", "communication_style"],
  "metadata": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | ✅ Yes | Unique session identifier for context isolation |
| `agent_id` | string | ✅ Yes | ID of the agent invoking assimilation |
| `text_to_assimilate` | string | ✅ Yes | Natural language observation to embed and graph-encode |
| `domain_tags` | array[string] | ❌ No | Domain/category labels (e.g., `["logistics", "inventory"]`) |
| `metadata` | object | ❌ No | Custom metadata (e.g., `{"source": "user_feedback"}`) |

#### Response on Success (201)

```json
{
  "status": "success",
  "episode_id": "ep-a1b2c3d4"
}
```

#### Response on Failure (502)

```json
{
  "detail": "502 Bad Gateway: YAAM internal LLM pipeline failed - <error details>"
}
```

### L3 Payload Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Request received with traceparent header                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. LLM embeddings: Generate vector for text_to_assimilate       │
│    - Model: text-embedding-004 (default)                        │
│    - Dimension: 768                                             │
│    - Fallback: If LLM fails → 502 BAD_GATEWAY                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. LLM entity extraction: Parse text into graph entities        │
│    - Prompt: "Extract structured graph entities from: ..."      │
│    - Output: Entity list with types (e.g., "Person", "Concept")│
│    - Fallback: If LLM fails → 502 BAD_GATEWAY                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Create Episode model with metadata                           │
│    - Episode ID: auto-generated (ep-<hex8>)                     │
│    - Timestamps: fact_valid_from, time_window_start, etc.       │
│    - Topics: from domain_tags parameter                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Dual indexing (transactions are NOT atomic!)                 │
│                                                                 │
│    a) Store in Qdrant:                                          │
│       - Point ID: auto-generated UUID                           │
│       - Vector: embedding from step 2                           │
│       - Payload: episode_id, session_id, metadata               │
│                                                                 │
│    b) Store in Neo4j:                                           │
│       - Create `:Episode` node                                  │
│       - Create `:Entity` nodes                                  │
│       - Create `:CONTAINS` relationships                        │
│       - Properties: bi-temporal (factValidFrom, sourceObsTime)  │
│                                                                 │
│    ⚠️  WARNING: If (a) succeeds but (b) fails, data is orphaned│
│    in Qdrant. Implement compensating logic if strong            │
│    consistency is required.                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. Return episode_id and close request with traceparent context │
│    - Phoenix Arize captures the full trace                      │
└─────────────────────────────────────────────────────────────────┘
```

### Embedding Dimensions

The current production REST/MCP runtime uses OpenRouter API embeddings via
`qwen/qwen3-embedding-8b`. The active L3 Qdrant collection is
`episodes_qwen_v2` and must be initialized with **4096 dimensions**:

```bash
OPENROUTER_EMBEDDING_MODEL=qwen/qwen3-embedding-8b
EMBEDDING_DIMENSIONS=4096
MAS_L3_COLLECTION=episodes_qwen_v2
```

The legacy local SentenceTransformer/Torch embedding path is optional and not part of the
production image. Install it only for offline experiments with `poetry install --with local-embeddings`.

Mismatch between requested embedding size and collection size → `StorageDataError`.

---

## Retry & Timeout Logic: httpx Configuration

### Timeout Strategy

YAAM v2 implements **cascading timeouts** for different operation classes:

#### LLM Provider Timeouts (Task-Level)

| Provider | Default Timeout | Use Case |
|----------|-----------------|----------|
| OpenRouter | 45s | General-purpose LLM (Grok, Claude, etc.) |
| Groq | 30s | Fast inference (Llama-3.3-70b) |
| Mistral | 30s | Fast inference |
| Gemini | 30s | Embeddings + fast generation |

Configuration in `src/llm/client.py`:

```python
provider_configs=[
    ProviderConfig(name="openrouter", timeout=45.0, priority=0),
    ProviderConfig(name="groq", timeout=30.0, priority=1),
    ProviderConfig(name="mistral", timeout=30.0, priority=2),
    ProviderConfig(name="gemini", timeout=30.0, priority=3),
]
```

**Behavior**: If a provider times out, the client automatically falls back to the next provider in priority order.

#### Storage Adapter Timeouts (Connection-Level)

| Storage | Operation | Timeout | Notes |
|---------|-----------|---------|-------|
| Qdrant | Vector search | Implicit ≤ 30s | Depends on collection size |
| Neo4j | Graph traversal | Implicit ≤ 60s | Lock-based concurrency |
| Qdrant + Neo4j (L3) | Dual index store | Implicit ≤ 120s | Heavy writes with LLM calls |

#### Recommended httpx Configuration for Client Integration

If you are calling YAAM v2 from an external service via httpx, configure:

```python
import httpx

# For /v2/memory/l3/assimilate (heavy Neo4j + Qdrant + LLM calls)
async with httpx.AsyncClient(timeout=120.0) as client:
    response = await client.post(
        "http://<YOUR_DEV_NODE_IP>:8000/v2/memory/l3/assimilate",
        json={
            "session_id": "session-xyz",
            "agent_id": "agent-001",
            "text_to_assimilate": "...",
            "domain_tags": []
        },
        headers={
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        }
    )

# For /v2/memory/l2/facts (faster, PostgreSQL-only)
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.post(
        "http://<YOUR_DEV_NODE_IP>:8000/v2/memory/l2/facts",
        json={
            "session_id": "session-xyz",
            "agent_id": "agent-001",
            "action": "store",
            "content": "..."
        }
    )

# For /v2/memory/l1/turns (fastest, Redis-backed)
async with httpx.AsyncClient(timeout=5.0) as client:
    response = await client.post(
        "http://<YOUR_DEV_NODE_IP>:8000/v2/memory/l1/turns",
        json={
            "session_id": "session-xyz",
            "turn_id": "turn-001",
            "role": "user",
            "content": "..."
        }
    )
```

### Retry Logic

**DO NOT implement client-side retries for HTTP 501/502 errors.**

- **501 NOT_IMPLEMENTED**: Tier not configured. Retrying won't help; fix configuration.
- **502 BAD_GATEWAY**: LLM provider or storage backend failed. Retrying may help transiently, but **first verify**:
  1. LLM provider (OpenRouter, Groq, etc.) is accessible
  2. Qdrant server is running
  3. Neo4j server is running

**DO implement retries for transient network errors** (connection timeouts, temporary unavailability):

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def assimilate_with_retry(session_id: str, text: str):
    async with httpx.AsyncClient(timeout=120.0) as client:
        return await client.post(
            "http://<YOUR_DEV_NODE_IP>:8000/v2/memory/l3/assimilate",
            json={"session_id": session_id, "text_to_assimilate": text, "domain_tags": []}
        )
```

---

## Environment Checklist

### Level 1: Mandatory (All modes)

These variables **MUST** be set for any YAAM v2 integration to succeed.

```bash
# ===== Redis (L1 + Distributed Locking) =====
export REDIS_URL="redis://<YOUR_DEV_NODE_IP>:6379"

# ===== PostgreSQL (L1 backup + L2) =====
export POSTGRES_URL="postgresql://yaam_user:your-db-password@<YOUR_DEV_NODE_IP>:5432/yaam_db"

# ===== Qdrant (L3 vectors) =====
export QDRANT_URL="http://<YOUR_DEV_NODE_IP>:6333"

# ===== Neo4j (L3 graph) =====
export NEO4J_URI="neo4j://<YOUR_DEV_NODE_IP>:7687"

# ===== Typesense (L4) =====
export TYPESENSE_URL="http://<YOUR_DEV_NODE_IP>:8108"

# ===== LLM Provider Keys (at least ONE) =====
export OPENROUTER_API_KEY="your-openrouter-key"
# OR:
export GOOGLE_API_KEY="your-google-genai-key"
# OR:
export GROQ_API_KEY="your-groq-key"
# OR:
export MISTRAL_API_KEY="your-mistral-key"
```

### Level 2: Optional (Neo4j + Qdrant tuning)

```bash
# ===== Neo4j Credentials (if non-default) =====
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your-neo4j-password"
export NEO4J_DATABASE="neo4j"

# ===== Qdrant (if secured) =====
export QDRANT_API_KEY="your-qdrant-api-key"

# ===== Typesense Credentials =====
export TYPESENSE_API_KEY="your-typesense-api-key"

# ===== Embedding Configuration =====
export OPENROUTER_EMBEDDING_MODEL="qwen/qwen3-embedding-8b"
export EMBEDDING_DIMENSIONS="4096"  # Must match Qdrant collection
export MAS_L3_COLLECTION="episodes_qwen_v2"

# ===== L1 Configuration (if enabled) =====
export L1_WINDOW_SIZE="20"
export L1_TTL_HOURS="24"
```

### Level 3: Observability (Phoenix Tracing)

```bash
# ===== Phoenix Collector Endpoint =====
export PHOENIX_COLLECTOR_ENDPOINT="http://<YOUR_DEV_NODE_IP>:6006/v1/traces"

# ===== Phoenix Project Name (optional; auto-generated if not set) =====
export PHOENIX_PROJECT_NAME="mas-integration-test"

# ===== Agent Type (optional; used in project name if Phoenix not set) =====
export AGENT_TYPE="memory-agent"
```

### Level 4: Performance & Reliability (Advanced)

```bash
# ===== LLM Provider Fallback Priority =====
# (Internally prioritized as: OpenRouter → Groq → Mistral → Gemini)
# No env var needed; configure in code via LLMClient.from_env()

# ===== Neo4j Lock TTL (default: 30 seconds) =====
# Controlled internally; adjust if experiencing lock contention
export NEO4J_LOCK_TTL_SECONDS="30"

# ===== Promotion Task Timeout (default: no timeout) =====
export MAS_PROMOTION_TIMEOUT_S="600"  # 10 minutes

# ===== V2 Mode Activation =====
export MAS_V2_MODE="true"  # Default; set explicitly to enable dual-indexing behavior
```

### Verification Script

Run this after setting environment variables to validate the handshake:

```bash
#!/bin/bash

echo "=== YAAM v2 Environment Validation ==="

# Check mandatory vars
for var in REDIS_URL POSTGRES_URL QDRANT_URL NEO4J_URI TYPESENSE_URL; do
    if [ -z "$(eval echo \$$var)" ]; then
        echo "❌ MISSING: $var"
        exit 1
    else
        echo "✅ SET: $var"
    fi
done

# Check at least one LLM provider key
if [ -z "$OPENROUTER_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ] && \
   [ -z "$GROQ_API_KEY" ] && [ -z "$MISTRAL_API_KEY" ]; then
    echo "❌ MISSING: At least one LLM provider key"
    exit 1
else
    echo "✅ At least one LLM provider key set"
fi

# Optional: Check Phoenix
if [ -z "$PHOENIX_COLLECTOR_ENDPOINT" ]; then
    echo "⚠️  OPTIONAL: PHOENIX_COLLECTOR_ENDPOINT not set (tracing disabled)"
else
    echo "✅ OPTIONAL: Phoenix tracing enabled"
fi

echo ""
echo "=== All mandatory checks passed! ==="
```

---

## Integration Workflow

### Step 1: Initialize Storage Adapters

```python
from src.storage.redis_adapter import RedisAdapter
from src.storage.postgres_adapter import PostgresAdapter
from src.storage.qdrant_adapter import QdrantAdapter
from src.storage.neo4j_adapter import Neo4jAdapter
from src.storage.typesense_adapter import TypesenseAdapter

# Initialize adapters with environment configuration
redis_adapter = RedisAdapter({"url": os.environ["REDIS_URL"]})
postgres_adapter = PostgresAdapter({"url": os.environ["POSTGRES_URL"]})
qdrant_adapter = QdrantAdapter({"url": os.environ["QDRANT_URL"], "vector_size": 768})
neo4j_adapter = Neo4jAdapter({
    "uri": os.environ["NEO4J_URI"],
    "user": os.environ.get("NEO4J_USER", "neo4j"),
    "password": os.environ.get("NEO4J_PASSWORD", "your-password"),
    "lock_redis_url": os.environ["REDIS_URL"]
})
typesense_adapter = TypesenseAdapter({"url": os.environ["TYPESENSE_URL"]})
```

### Step 2: Initialize Tiers

```python
from src.memory.tiers import (
    ActiveContextTier,
    WorkingMemoryTier,
    EpisodicMemoryTier,
    SemanticMemoryTier
)

# Optional: L1
l1_tier = None  # or ActiveContextTier(...) if enabled

# Required: L2
l2_tier = WorkingMemoryTier(postgres_adapter=postgres_adapter)

# Required: L3
l3_tier = EpisodicMemoryTier(qdrant_adapter=qdrant_adapter, neo4j_adapter=neo4j_adapter)

# Optional: L4
l4_tier = SemanticMemoryTier(typesense_adapter=typesense_adapter)

# Initialize
if l1_tier:
    await l1_tier.initialize()
await l2_tier.initialize()
await l3_tier.initialize()
if l4_tier:
    await l4_tier.initialize()
```

### Step 3: Initialize Unified Memory System

```python
from src.memory.unified_memory_system import UnifiedMemorySystem
from src.llm.client import LLMClient

llm_client = LLMClient.from_env()

memory_system = UnifiedMemorySystem(
    l1_tier=l1_tier,
    l2_tier=l2_tier,
    l3_tier=l3_tier,
    l4_tier=l4_tier,
    llm_client=llm_client
)
```

### Step 4: Create FastAPI App with AgentWrapperState

```python
from fastapi import FastAPI
from src.evaluation.agent_wrapper import AgentWrapperState

app = FastAPI()

# Attach state to app for v2_router
state = AgentWrapperState(
    agent=...,  # Your agent instance
    memory_system=memory_system,
    l1_tier=l1_tier,
    l2_tier=l2_tier,
    redis_client=redis.from_url(os.environ["REDIS_URL"]),
    agent_type="memory",
    agent_variant="baseline",
    session_prefix="session",
    rate_limiter=...,
)

@app.on_event("startup")
async def startup():
    app.state.wrapper = state

# Include v2 router
from src.api import v2_router
app.include_router(v2_router.router)
```

### Step 5: Make L3/Assimilate Calls with Traceparent

```python
import httpx
import uuid

# Generate W3C traceparent header
trace_id = uuid.uuid4().hex
parent_id = uuid.uuid4().hex[:16]
traceparent = f"00-{trace_id}-{parent_id}-01"

async with httpx.AsyncClient(timeout=120.0) as client:
    response = await client.post(
        "http://localhost:8000/v2/memory/l3/assimilate",
        json={
            "session_id": "session-001",
            "agent_id": "agent-001",
            "text_to_assimilate": "User prefers async communication.",
            "domain_tags": ["preferences"]
        },
        headers={"traceparent": traceparent}
    )
    episode_id = response.json()["episode_id"]
    print(f"Assimilated episode: {episode_id}")
```

---

## Troubleshooting and Cross-Node Debugging

### Issue: HTTP 501 on L1/L2/L3 Endpoints

**Symptom**: All memory tier requests return `HTTP 501 NOT_IMPLEMENTED`.

**Cause**: The corresponding tier was not initialized or the `AgentWrapperState` was not attached to `app.state.wrapper`.

**Fix**:
```python
# Verify in startup:
print(f"L1 tier: {app.state.wrapper.l1_tier}")
print(f"L2 tier: {app.state.wrapper.l2_tier}")
print(f"L3 tier: {app.state.wrapper.memory_system.l3_tier}")
```

### Issue: HTTP 502 on L3/Assimilate

**Symptom**: `/v2/memory/l3/assimilate` returns `502 Bad Gateway`.

**Causes** (in order of likelihood):
1. **LLM provider unreachable** – Check `OPENROUTER_API_KEY`, `GOOGLE_API_KEY`, etc.
2. **Qdrant unavailable** – Verify `QDRANT_URL` is reachable: `curl -X GET http://<IP>:6333/health`
3. **Neo4j unavailable** – Verify `NEO4J_URI` is reachable: `neo4j-shell --uri bolt://<IP>:7687 "RETURN 1"`

**Debug**: Check server logs for exception trace:
```
logger.exception("LLM Provider failed during assimilation")
```

### Issue: Orphaned Data in Qdrant but Missing in Neo4j

**Symptom**: `/v2/memory/l3/query` returns results, but graph traversal fails.

**Cause**: During dual indexing, Qdrant write succeeded but Neo4j write failed. Transactions are **not atomic**.

**Mitigation**:
1. Implement a reconciliation job that compares Qdrant points with Neo4j nodes
2. Log both indices separately and use `traceparent` to correlate logs across nodes

### Cross-Node Debugging with Phoenix Arize

**Setup**:
1. Deploy Phoenix Arize collector on accessible node (e.g., `<YOUR_DEV_NODE_IP>:6006`)
2. Set `PHOENIX_COLLECTOR_ENDPOINT="http://<YOUR_DEV_NODE_IP>:6006/v1/traces"`
3. Send requests with `traceparent` header (see Integration Workflow, Step 5)

**Phoenix Dashboard**:
1. Open `http://<YOUR_DEV_NODE_IP>:6006` in browser
2. Navigate to **Traces** → filter by project name (e.g., `mas-integration-test`)
3. Click on a trace to see full call chain:
   - LLM provider latency
   - Qdrant indexing latency
   - Neo4j write latency
   - Lock contention

**Example Trace Span Hierarchy**:
```
[Trace ID: 0af7651916cd43dd8448eb211c80319c]
├─ [POST /v2/memory/l3/assimilate] 120ms
│  ├─ [yaam.gateway.v2.assimilate] 118ms
│  │  ├─ [LLM::get_embedding] 45ms (Gemini text-embedding-004)
│  │  ├─ [LLM::generate] 30ms (entity extraction prompt)
│  │  ├─ [Qdrant::store] 20ms (point insertion)
│  │  └─ [Neo4j::store] 23ms (Cypher MERGE)
```

### Validating Dual Indexing Consistency

**Check Qdrant**:
```python
from src.storage.qdrant_adapter import QdrantAdapter

adapter = QdrantAdapter({"url": "http://<YOUR_DEV_NODE_IP>:6333"})
await adapter.connect()
points = await adapter.search({"vector": [0.1] * 768, "limit": 5})
print(f"Qdrant has {len(points)} points")
```

**Check Neo4j**:
```python
from src.storage.neo4j_adapter import Neo4jAdapter

adapter = Neo4jAdapter({"uri": "neo4j://<YOUR_DEV_NODE_IP>:7687"})
await adapter.connect()
episodes = await adapter.query("MATCH (e:Episode) RETURN COUNT(e) AS count")
print(f"Neo4j has {episodes[0]['count']} episodes")
```

**Reconcile**:
- If counts differ significantly, investigate the failed L3 requests in Phoenix traces
- Use `traceparent` values to correlate Qdrant writes with Neo4j writes

---

## Summary

| Component | Status | Key Requirement |
|-----------|--------|-----------------|
| **L1 (Optional)** | 501 if not configured | Enable only if server-side session mgmt needed |
| **L2 (Required)** | 501 if not initialized | PostgreSQL adapter must be ready |
| **L3 (Required)** | 502 if LLM/storage fails | Dual indexing (Qdrant + Neo4j) must succeed |
| **L4 (Optional)** | 501 if not configured | Typesense for long-term knowledge |
| **Tracing** | Optional but recommended | Set `traceparent` header in all requests |
| **Timeout** | Per-tier | L3 assimilate: 120s (LLM + dual-index) |
| **Secrets** | Protected | Never log API keys; use placeholder values in docs |

---

## References

- [ADR-003: Four-Tier Memory Architecture](../ADR/003-four-layers-memory.md)
- [ADR-007: LangGraph Integration](../ADR/007-agent-integration-layer.md)
- [W3C Trace Context Specification](https://www.w3.org/TR/trace-context/)
- [Arize Phoenix Observability](https://phoenix.arize.com/)
- [OpenTelemetry Python Instrumentation](https://opentelemetry.io/docs/instrumentation/python/)
