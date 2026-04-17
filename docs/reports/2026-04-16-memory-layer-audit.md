# YAAM Memory Layer Audit (Last 12 Hours)

**Date:** 2026-04-17T05:58:11.674308+00:00
**Container:** `mas-memory-layer-mas-agent-1`
**Window:** `12h`

## 1. Container Log Mining

- Container state: `running restart=0 oom=false started=2026-04-16T14:56:56.860370952Z`
- Configured `POSTGRES_URL`: `postgresql://pgadmin:***@192.168.107.187:5432/mas_memory`
- Configured `QDRANT_URL`: `http://192.168.107.187:6333`
- Configured `NEO4J_URI`: `bolt://192.168.107.187:7687`

### Memory Endpoint Request Volume

- `/v2/memory/l2/facts`: **382** requests
- `/v2/memory/l3/query`: **169** requests
- `/v2/memory/l4/finalize`: **162** requests

### Memory Endpoint HTTP Statuses

- `/v2/memory/l3/query`: `200`=169
- `/v2/memory/l2/facts`: `200`=382
- `/v2/memory/l4/finalize`: `201`=162

### Error and Saturation Signals

- Matched error-like lines (sampled): **7**

```text
Provider 'gemini' failed: 
Provider 'gemini' failed: 
Provider 'gemini' failed: 
Provider 'gemini' failed: 
Provider 'gemini' failed: 
Provider 'gemini' failed: 
Provider 'gemini' failed: 
```

## 2. DBMS Statistics and Health Check

### PostgreSQL (L1/L2)

- Candidate L2/fact tables: **1**
- `working_memory`: last 12h = **208**, total = **748** (timestamp column: `created_at`)

### Qdrant (L3 Vectors)

- Collections discovered: **118**
- Non-zero point collections:
  - `episodes`: points = **310**, vectors = **0**, status = `green`
  - `perf_memory_perf`: points = **56**, vectors = **0**, status = `green`
  - `semantic_memory`: points = **30**, vectors = **0**, status = `green`
  - `winsim_episodes`: points = **4**, vectors = **0**, status = `green`
- Limitation: Qdrant collection metadata does not expose insertion timestamps by default.

### Neo4j (L3 Graph)

- Total nodes: **185**
- Total relationships: **5**
- 12h temporal-property counts (best effort):
  - Nodes by `created_at`: **0**
  - Nodes by `created_on`: **0**
  - Nodes by `timestamp`: **0**
  - Nodes by `inserted_at`: **0**
  - Nodes by `updated_at`: **0**
  - Relationships by `created_at`: **0**
  - Relationships by `created_on`: **0**
  - Relationships by `timestamp`: **0**
  - Relationships by `inserted_at`: **0**
  - Relationships by `updated_at`: **0**

## 3. Findings and Bottleneck Assessment

- The dominant failure signal in the sampled logs is upstream provider instability (`Provider 'gemini' failed`) rather than `/v2/memory/*` HTTP 5xx responses.
- Auto-Store traffic is high (`/v2/memory/l2/facts` = **382** requests in 12h), which increases pressure on downstream DB adapters and can amplify latency variance.
- Finalization calls are also frequent (`/v2/memory/l4/finalize` = **162** requests), suggesting sustained write activity across tiers during orchestration.
- PostgreSQL shows positive L2/fact ingestion in the last 12h, indicating writes are reaching the DB.

### Proposed Remediations

- Add bounded retries with jitter for upstream LLM provider calls; do not block memory finalization on provider transient failures.
- Introduce backpressure in Auto-Store path (e.g., queue + worker pool) to decouple tool completion latency from DB write latency.
- Verify and add indexes on frequently filtered timestamp/session keys in L2 fact tables.
- Tune connection pools explicitly for Postgres and Neo4j adapters based on concurrent task count.
- Add endpoint-level latency histograms for `/v2/memory/l2/facts` and `/v2/memory/l4/finalize` to detect saturation before stalls.

## 4. Method Notes

- Audit was executed via a repository script validated by unit tests before run.
- Where backend temporal metadata is unavailable, totals are reported with explicit limitations.
