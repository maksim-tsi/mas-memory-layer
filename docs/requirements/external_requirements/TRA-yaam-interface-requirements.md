# TRA YAAM Interface Requirements

**System:** TRA / agentic-scm-tra26  
**Owner:** agentic-scm-tra26 maintainers  
**Date:** 2026-05-24  
**Status:** Draft  
**Primary contact:** TBD  

## 1. System Overview

TRA (`agentic-scm-tra26`) is a Supply Chain Management evaluation harness for
comparing naive LLM baselines with an agentic SCM multi-agent system. The
agentic path is implemented as a LangGraph workflow with Planner, Executor, and
Finalizer nodes. The Executor is constrained to deterministic Pydantic-typed SCM
tools from `tools.ACTIVE_TOOLS`; benchmark inputs live in `data/benchmark/`, and
runtime artifacts are written under `outputs/`.

YAAM is already used as a best-effort memory substrate through the Semantic
Gateway v2 REST interface. The Planner queries L3 semantic memory before
planning, the Executor writes successful deterministic tool outputs to L2
working memory, and the Finalizer reads L2 facts and writes final answers to L4.
All YAAM calls should preserve W3C `traceparent` so Phoenix traces can connect
TRA reasoning spans with YAAM memory spans.

## 2. Integration Goals

- Retrieve relevant historical SCM context before the Planner commits to a
  tool-execution plan. This reduces repeated context discovery and helps
  benchmark runs benefit from prior validated episodes.
- Store every successful deterministic SCM tool output in L2 working memory via
  runtime-managed writes. This is required because a prior evidence-drop
  investigation showed prompt-only memory persistence was insufficient.
- Retrieve L2 facts during final synthesis so the Finalizer can build an
  Evidence Table from verified tool outputs rather than model recollection.
- Persist final answers and Evidence Table metadata to L4 for replay, audit,
  search, and later benchmark analysis.
- Inspect provenance, CIAR explanations, and evidence metadata when debugging
  failed or suspicious benchmark runs.
- Preserve benchmark reproducibility by using stable logical task/session scope
  while keeping runtime outputs outside immutable benchmark data.

## 3. Expected Interface

| Interface | Required? | Purpose | Notes |
|---|---:|---|---|
| API Wall `/v1/chat/completions` | No | Not a memory integration target for TRA. | TRA calls OpenRouter separately for model inference. |
| REST v2 `/v2/memory/...` | Yes | MVP interface for L2 store/retrieve, L3 query/assimilate, and L4 finalize. | Current client uses `YAAM_SEMANTIC_GATEWAY_URL`. |
| MCP tools/resources/prompts | Yes | Future MCP-capable agent/evaluator hosts should inspect and invoke memory operations without TRA-specific HTTP client code. | MCP should expose read tools broadly and mutating tools only with allowlisting. |
| LangChain tools | No | TRA memory writes are runtime-owned, not LLM-selected tools. | Exposing memory mutation as model-callable tools caused evidence reliability risk. |
| Direct library calls | No | TRA should not couple to YAAM stores directly. | YAAM should own embeddings, graph extraction, indexing, and storage routing. |

## 4. Required Capabilities

| Capability | Tier | Read/Write/Lifecycle | Required for MVP? | Example input | Expected output | Justification / scenario |
|---|---|---|---:|---|---|---|
| Query semantic historical context before planning | Unified | Read | Yes | `{"session_id":"sc_ra_001","agent_id":"tra-scm-planner","nl_query":"Kraljic supply risk task...","top_k":3}` | Ranked L3 results with text, score, source tier/id, timestamp, and provenance. | Planner already calls `query_l3_semantic`; see Scenario 1. |
| Store deterministic tool output as a working-memory fact | Raw | Write | Yes | `{"session_id":"sc_ra_001","task_id":"sc_ra_001","agent_id":"tra-scm-executor","action":"store","content":"Tool kraljic_matrix__... returned: {...}"}` | Stored fact acknowledgement with fact id, source tier, scope ids, and timestamp. | Runtime auto-store prevents evidence drops after tool execution; see Scenario 2. |
| Retrieve L2 facts for final synthesis | Raw/Unified | Read | Yes | `{"session_id":"sc_ra_001","task_id":"sc_ra_001","agent_id":"tra-scm-finalizer","action":"retrieve"}` | List of scoped L2 facts or `{ "results": [...] }`, including provenance. | Finalizer needs verified facts for citations and Evidence Tables; see Scenario 3. |
| Finalize benchmark answer and Evidence Table metadata | Raw | Write/Lifecycle | Yes | `{"session_id":"sc_ra_001","task_id":"sc_ra_001","title":"Consensus Report: sc_ra_001","final_artifact":"...","consensus_metadata":{"evidence_table":[...]}}` | L4 artifact id, stored title, scope ids, timestamp, and provenance. | Completed answers must be replayable and searchable without mutating benchmark data; see Scenario 4. |
| Explain retrieval and CIAR decisions for audit | Agentic | Read | No | `{"session_id":"sc_ra_001","fact_id":"fact_123","include_components":true}` | CIAR component scores, final score, suppression/supersession status, and explanation. | Debuggers need to distinguish retrieval, memory-policy, and synthesis failures; see Scenario 5. |
| Assemble evidence context across L2/L3/L4 | Unified | Read | No | `{"session_id":"sc_ra_001","task_id":"sc_ra_001","query":"facts supporting final answer"}` | Evidence bundle grouped by tier with citations and retrieval explanation. | Future MCP hosts need a read-only audit bundle for suspicious runs; see Scenarios 3 and 5. |

## 5. Use Case Scenarios

### Scenario 1: Planner Retrieves Historical SCM Context

**Trigger:** An AgenticGraph benchmark task starts and the Planner receives
`scenario_context` plus `agent_prompt`.

**Caller:** `tra-scm-planner` in `src/agentic/nodes/planner.py`.

**YAAM interface:** REST v2 `POST /v2/memory/l3/query`; future MCP equivalent
`yaam.memory.query` or `yaam.memory.get_context`.

**Input example:**

```json
{
  "session_id": "sc_ra_001",
  "agent_id": "tra-scm-planner",
  "nl_query": "Supplier has high profit impact and high supply risk. Classify and recommend strategy.",
  "top_k": 3,
  "filters": {}
}
```

**Expected YAAM behavior:** Search L3 semantic memory without requiring TRA to
generate embeddings or graph queries. Return relevant prior SCM episodes,
facts, or knowledge artifacts with provenance and retrieval scores.

**Expected response shape:**

```json
{
  "results": [
    {
      "content": "High profit impact and high supply risk maps to strategic item...",
      "score": 0.91,
      "source_tier": "L3",
      "source_id": "episode_123",
      "provenance": {
        "session_id": "prior_task",
        "agent_id": "tra-scm-finalizer",
        "created_at": "2026-05-24T10:00:00Z"
      }
    }
  ]
}
```

**Failure handling:** Connection failures, 501, and 502 should return an empty
context result so the Planner can continue without YAAM. Contract errors such
as 422 should surface as integration failures.

**Trace/audit expectations:** Request includes W3C `traceparent`; YAAM spans
link to the active Phoenix `scm.eval.task` trace and record `session_id`,
`agent_id`, query text hash, result count, and latency.

**Justification:** Planner currently calls `query_l3_semantic` before the LLM
planning step. L3 retrieval is needed to inject prior validated context without
letting TRA depend on YAAM internals.

### Scenario 2: Executor Stores Deterministic Tool Output In L2

**Trigger:** A deterministic SCM tool returns successfully inside the Executor
tool wrapper.

**Caller:** `tra-scm-executor` in `src/agentic/nodes/executor.py`.

**YAAM interface:** REST v2 `POST /v2/memory/l2/facts`; future MCP equivalent
`yaam.l2.store_fact`.

**Input example:**

```json
{
  "session_id": "sc_ra_001",
  "task_id": "sc_ra_001",
  "agent_id": "tra-scm-executor",
  "action": "store",
  "content": "Tool kraljic_matrix__kraljic_supply_matrix_classification returned: {\"item_classification\":\"strategic\",\"procurement_strategy\":\"Risk mitigation through long-term partnerships\",\"profit_impact\":\"high\",\"supply_risk\":\"high\"}"
}
```

**Expected YAAM behavior:** Store the fact in L2 under the exact task/session
scope, preserve the producing agent, and return an acknowledgement with a fact
identifier.

**Expected response shape:**

```json
{
  "fact_id": "fact_456",
  "source_tier": "L2",
  "session_id": "sc_ra_001",
  "task_id": "sc_ra_001",
  "agent_id": "tra-scm-executor",
  "created_at": "2026-05-24T10:01:00Z"
}
```

**Failure handling:** YAAM write failures must not alter the deterministic tool
output returned to the model. Connection failures, 501, and 502 are logged as
warnings and treated as degraded memory persistence. 4xx schema mismatches
should fail fast during integration testing.

**Trace/audit expectations:** Request includes `traceparent`; YAAM records the
tool alias, fact content hash, logical task/session scope, producing agent, and
write outcome.

**Justification:** Prior evidence-drop analysis showed that relying on a model
to call a memory tool caused missing L2 evidence. Current runtime-managed
auto-store makes L2 persistence deterministic after successful tool execution.

### Scenario 3: Finalizer Retrieves L2 Facts For Evidence Table

**Trigger:** Executor emits `FINAL_EXECUTION_DONE:` and the graph routes to the
Finalizer.

**Caller:** `tra-scm-finalizer` in `src/agentic/nodes/finalizer.py`.

**YAAM interface:** REST v2 `POST /v2/memory/l2/facts`; future MCP equivalent
`yaam.memory.get_context` or `yaam.memory.query`.

**Input example:**

```json
{
  "session_id": "sc_ra_001",
  "task_id": "sc_ra_001",
  "agent_id": "tra-scm-finalizer",
  "action": "retrieve"
}
```

**Expected YAAM behavior:** Return only facts scoped to the logical task/session
unless explicitly configured otherwise. Include enough provenance for the
Finalizer to label evidence rows accurately.

**Expected response shape:**

```json
{
  "results": [
    {
      "fact_id": "fact_456",
      "content": "Tool kraljic_matrix__... returned: {...}",
      "source_tier": "L2",
      "agent_id": "tra-scm-executor",
      "task_id": "sc_ra_001",
      "created_at": "2026-05-24T10:01:00Z"
    }
  ]
}
```

**Failure handling:** Empty or unavailable L2 should return an empty list, not a
malformed response. The Finalizer should continue and state when no citations
are available.

**Trace/audit expectations:** Request includes `traceparent`; YAAM records
result count, filter/scope ids, and latency.

**Justification:** The Finalizer prompt requires evidence rows to come only from
tool outputs, YAAM L2 facts, or L3 context. L2 retrieval closes the
retrieval-reasoning gap by giving final synthesis verified intermediate facts.

### Scenario 4: Finalizer Stores Final Answer And Evidence Metadata In L4

**Trigger:** Finalizer produces a structured `FinalSynthesis` with
`evidence_table` and `final_answer`.

**Caller:** `tra-scm-finalizer`.

**YAAM interface:** REST v2 `POST /v2/memory/l4/finalize`; future MCP equivalent
`yaam.l4.finalize_artifact`.

**Input example:**

```json
{
  "session_id": "sc_ra_001",
  "task_id": "sc_ra_001",
  "title": "Consensus Report: sc_ra_001",
  "final_artifact": "The supplier is classified as strategic because...",
  "consensus_metadata": {
    "agent_id": "tra-scm-finalizer",
    "evidence_table": [
      {
        "fact": "Kraljic classification = strategic",
        "source": "Tool:kraljic_matrix__kraljic_supply_matrix_classification"
      }
    ]
  }
}
```

**Expected YAAM behavior:** Persist the final artifact and metadata in L4 for
search, replay, and cross-run analysis.

**Expected response shape:**

```json
{
  "artifact_id": "l4_artifact_789",
  "source_tier": "L4",
  "session_id": "sc_ra_001",
  "task_id": "sc_ra_001",
  "title": "Consensus Report: sc_ra_001",
  "created_at": "2026-05-24T10:02:00Z"
}
```

**Failure handling:** L4 persistence is important for audit but should not
change the already produced final answer. Contract errors should be visible in
test/debug paths.

**Trace/audit expectations:** Request includes `traceparent`; YAAM records final
artifact id, content hash, evidence count, scope ids, and producing agent.

**Justification:** L4 finalization makes completed benchmark outputs available
for later search and review while preserving immutable benchmark inputs.

### Scenario 5: Debugger Inspects Provenance, Evidence, And CIAR Decisions

**Trigger:** A benchmark run fails, produces an uncited answer, or shows
suspicious evidence selection.

**Caller:** Benchmark/debug tooling, human operator, or future MCP-capable
agent host.

**YAAM interface:** MCP resources and read-only MCP tools; REST fallback if MCP
is unavailable.

**Input example:**

```json
{
  "session_id": "sc_ra_001",
  "task_id": "sc_ra_001",
  "include_tiers": ["L2", "L3", "L4"],
  "include_ciar": true,
  "include_suppressed": true
}
```

**Expected YAAM behavior:** Return an audit bundle showing which facts were
retrieved, stored, promoted, suppressed, or superseded; explain CIAR decisions
without mutating memory.

**Expected response shape:**

```json
{
  "session_id": "sc_ra_001",
  "facts": [],
  "artifacts": [],
  "ciar": [
    {
      "source_id": "fact_456",
      "certainty": 0.98,
      "impact": 0.75,
      "age_decay": 0.99,
      "final_score": 0.72,
      "explanation": "Recent deterministic tool output with direct task relevance."
    }
  ]
}
```

**Failure handling:** Debug reads should return partial results with explicit
per-tier errors when some backends are unavailable.

**Trace/audit expectations:** YAAM should audit who requested inspection, which
scope was inspected, whether suppressed evidence was included, and whether any
privileged fields were withheld.

**Justification:** TRA uses Phoenix traces and debug JSONL to diagnose benchmark
behavior. Memory-side provenance and CIAR explanations are needed to determine
whether a bad answer came from missing retrieval, wrong evidence promotion, or
model synthesis failure.

## 6. MCP Expectations

Complete this section if the system expects to use MCP.

### 6.1 Tool Requirements

| Proposed tool | Required? | Read/Write/Lifecycle | Required input fields | Required output fields |
|---|---:|---|---|---|
| `yaam.memory.query` | Yes | Read | `session_id`, `agent_id`, `query`, optional `task_id`, `top_k`, `filters` | `results`, `source_tier`, `source_id`, `score`, `provenance` |
| `yaam.memory.get_context` | Yes | Read | `session_id`, optional `task_id`, `agent_id`, `include_tiers` | Context bundle grouped by tier, retrieval explanation, evidence ids |
| `yaam.l2.store_fact` | Yes | Write | `session_id`, `task_id`, `agent_id`, `content`, optional metadata | `fact_id`, `source_tier`, `created_at`, scope ids |
| `yaam.ciar.explain` | Yes | Read | `source_id` or `session_id`/`task_id`, optional `include_components` | CIAR components, final score, explanation, suppression/supersession status |
| `yaam.evidence.table` | Yes | Read/Agentic | `session_id`, `task_id`, optional `include_tiers`, `include_ciar` | Evidence rows, source ids, source tiers, confidence/CIAR metadata |
| `yaam.l4.finalize_artifact` | Yes | Write/Lifecycle | `session_id`, `task_id`, `title`, `final_artifact`, `consensus_metadata` | `artifact_id`, `source_tier`, `created_at`, scope ids |

Mutating MCP tools must be allowlisted for TRA runtime identities. General
agent hosts should default to read-only MCP access.

### 6.2 Resource Requirements

| Proposed resource | Required? | Access scope | Notes |
|---|---:|---|---|
| `yaam://sessions/{session_id}/context` | Yes | Session | Needed for debug and finalizer-style context inspection. |
| `yaam://sessions/{session_id}/facts` | Yes | Session | Read-only view of L2 facts for a logical task/session. |
| `yaam://facts/{fact_id}` | Yes | Fact | Needed for evidence citation and provenance inspection. |
| `yaam://health` | Yes | Service | Needed by benchmark runners to distinguish memory outage from model/tool failure. |
| `yaam://config/ciar` | Yes | Service | Read-only visibility into CIAR policy used for audit. |
| `yaam://artifacts/{artifact_id}` | Yes | Artifact | Needed to inspect L4 final answers and metadata. |

### 6.3 Prompt Requirements

| Proposed prompt | Required? | Purpose | Expected variables |
|---|---:|---|---|
| `yaam.prompt.evidence_table` | Yes | Convert retrieved facts into an audit-friendly Evidence Table. | `session_id`, `task_id`, `facts`, `retrieved_context` |
| `yaam.prompt.memory_inspection` | Yes | Summarize memory contents for benchmark debugging. | `session_id`, `task_id`, `include_tiers` |
| `yaam.prompt.ciar_explanation` | Yes | Explain why memory items were selected, suppressed, or promoted. | `source_id`, `ciar_components` |
| `yaam.prompt.contradiction_review` | No | Useful later for cross-run contradiction analysis. | `session_id`, `candidate_fact`, `related_facts` |

## 7. Data And Scope Requirements

- Mandatory identifiers for current TRA calls: `session_id`, `agent_id`.
- Mandatory identifiers for task-scoped L2/L4 operations: `session_id`,
  `task_id`, `agent_id`.
- TRA currently uses `task_id` as the logical YAAM `session_id` and `task_id`.
  LangGraph `thread_id` is generated per invocation to avoid checkpoint
  contamination and must not replace logical YAAM task/session scope.
- Producing agents should use stable ids such as `tra-scm-planner`,
  `tra-scm-executor`, and `tra-scm-finalizer`.
- `tenant_id` and `user_id` are not modeled in this repo. YAAM should support
  them as optional future identifiers and must not require them for current TRA
  MVP calls.
- L2 facts are shared across TRA nodes within the same logical task/session.
  They should not leak across unrelated benchmark tasks unless an explicit
  cross-session query is requested.
- L3/L4 may support cross-session retrieval for historical context, but results
  must include provenance so benchmark analysis can distinguish same-task facts
  from prior-run knowledge.
- Retention expectations: L2 should remain available for benchmark replay and
  debug; L3/L4 should be persistent. TRA runtime artifacts still belong under
  `outputs/`, not in `data/benchmark/`.

## 8. Provenance, Evidence, And CIAR Requirements

Responses should include source tier, source id, timestamp, producing agent,
logical `session_id`, and `task_id` when applicable. For retrieved L3/L4 items,
YAAM should include the original producing session/agent where available.

CIAR metadata is required for audit and debugging, but TRA should treat CIAR as
read/explain-only. Responses should expose certainty, impact, age decay, recency
boost, final score, and a concise explanation when requested. Suppressed or
superseded evidence should be hidden in ordinary Planner/Finalizer retrieval but
available to privileged debug/audit reads.

TRA needs Evidence Table support because benchmark analysis depends on knowing
which facts grounded the final answer. Example Evidence Table shape:

| Evidence id | Fact | Source tier | Source id | Producing agent | CIAR score |
|---|---|---|---|---|---:|
| E1 | Kraljic classification = strategic | L2 | fact_456 | tra-scm-executor | 0.72 |
| E2 | Strategic items require risk mitigation through partnerships | L3 | episode_123 | tra-scm-finalizer | 0.68 |

## 9. Security And Permission Requirements

- Planner access should be read-only for L3/context retrieval.
- Finalizer access should allow L2 reads and L4 finalization writes.
- Executor access should allow L2 fact writes only through runtime-owned code,
  not arbitrary LLM-selected tools.
- MCP write and lifecycle tools must require explicit allowlisting for TRA
  runtime identities.
- General MCP resources should default to read-only and must not expose secrets,
  environment variables, provider API keys, raw `.env` contents, or unrelated
  tenant/user data.
- YAAM must preserve benchmark isolation: no memory operation may write into
  `data/benchmark/`, and runtime dumps or exports should remain in gitignored
  output paths.
- Debug access to suppressed evidence, superseded facts, and CIAR policy details
  should be privileged because it may reveal internal memory policy decisions.

## 10. Observability Requirements

- TRA must propagate W3C `traceparent` headers on every YAAM REST call and MCP
  tool invocation should carry equivalent trace context when possible.
- YAAM spans should be visible in Phoenix under the same trace as the TRA
  `scm.eval.task` span.
- Required audit fields for memory calls: operation name, interface, source
  tier, `session_id`, `task_id` when present, `agent_id`, result count or
  created id, status, latency, and error type.
- Required metrics: per-operation p50/p95 latency, error counts by status code,
  empty retrieval rate, partial-result rate, and write acknowledgement rate.
- Error traces should make it clear whether a failure occurred in TRA, YAAM
  routing, an LLM-backed YAAM policy function, or a backing store.

## 11. Reliability And Error Handling

- Connection errors, HTTP 501, and HTTP 502 should be retryable or degradable for
  non-critical retrieval/write paths. TRA currently treats them as best-effort
  failures and continues without YAAM data.
- HTTP 4xx contract mismatches, especially 422 validation failures, should not
  be silently swallowed. They indicate that TRA and YAAM disagree on the
  interface contract.
- L3 semantic retrieval may have a long read budget because embeddings and
  retrieval can take tens of seconds; the current client default timeout is 120s
  with a fast connect timeout.
- L2 store/retrieve should be faster than L3 semantic operations and should
  return partial/empty results instead of malformed payloads when no facts exist.
- LLM-backed extraction, CIAR, or evidence-table generation failures should
  return explicit per-capability errors and partial deterministic results where
  possible.
- Expected error shape:

```json
{
  "error": {
    "code": "YAAM_BACKEND_UNAVAILABLE",
    "message": "L3 vector backend unavailable",
    "retryable": true,
    "operation": "l3.query",
    "trace_id": "0af7651916cd43dd8448eb211c80319c"
  }
}
```

## 12. Performance Expectations

| Workflow | Expected QPS | p50 latency | p95 latency | Timeout budget | Notes |
|---|---:|---:|---:|---:|---|
| L2 store tool fact | 1-5 per active benchmark run | <250 ms | <1 s | 5 s preferred | Should not materially slow tool loops. |
| L2 retrieve finalizer facts | 1 per completed task | <250 ms | <1 s | 5 s preferred | Empty result should be fast. |
| L3 semantic query before planning | 1 per task | <5 s | <60 s | 120 s max | Current client allows long reads for embedding/retrieval. |
| L4 finalize artifact | 1 per completed task | <1 s | <5 s | 10 s preferred | Stores final answer and metadata. |
| Debug evidence/CIAR inspection | Ad hoc | <2 s | <15 s | 30 s preferred | Partial results acceptable. |

## 13. Acceptance Tests

| Test | Interface | Setup | Expected result |
|---|---|---|---|
| L2 store sends required identifiers and trace | REST v2 `/v2/memory/l2/facts` | Executor stores a successful tool result with active `traceparent`. | YAAM receives `session_id`, `task_id`, `agent_id`, `content`, and `traceparent`; returns a fact acknowledgement. |
| L2 retrieve accepts list response | REST v2 `/v2/memory/l2/facts` | YAAM returns `[{"fact":"x"}]`. | TRA treats response as a list of facts. |
| L2 retrieve accepts wrapped results | REST v2 `/v2/memory/l2/facts` | YAAM returns `{ "results": [{"fact":"x"}] }`. | TRA unwraps `results` into a fact list. |
| 501/502 degrade gracefully | REST v2 any memory route | YAAM returns 501 or 502 for L2/L3 operation. | TRA receives `None` or `[]`, logs a warning, and continues the agent path. |
| 422 contract mismatch fails visibly | REST v2 any memory route | YAAM returns 422 validation error. | TRA raises an integration error rather than silently dropping the mismatch. |
| Planner preserves trace context | REST v2 `/v2/memory/l3/query` | Planner starts with active OpenTelemetry context. | YAAM receives W3C `traceparent`; Planner continues with retrieved context. |
| Executor preserves trace context | REST v2 `/v2/memory/l2/facts` | Executor auto-stores a tool result. | YAAM receives W3C `traceparent`; tool output returned to model is unchanged. |
| Finalizer preserves trace context | REST v2 L2 retrieve and L4 finalize | Finalizer synthesizes an answer. | YAAM receives W3C `traceparent` for both calls. |
| End-to-end AgenticGraph memory path | REST v2 L3, L2, L4 | Run one task in `AgenticGraph` mode with YAAM configured. | Planner retrieves L3, Executor writes L2, Finalizer reads L2, Finalizer writes L4 under one logical `task_id`/`session_id`. |
| MCP read-only audit bundle | MCP tools/resources | Request session context and CIAR explanation for a completed task. | MCP returns evidence/provenance/CIAR metadata without mutating memory. |

## 14. Open Questions

- Should YAAM require explicit `tenant_id` once TRA runs multiple benchmark
  suites or users, or is `session_id` plus `task_id` sufficient for the near
  term?
- What exact CIAR component names and numeric ranges will be stable across YAAM
  versions?
- Should L2 facts store only text content, or should YAAM accept structured tool
  payloads with normalized tool alias, inputs, outputs, and hashes?
- Should `yaam.evidence.table` generate an Evidence Table autonomously, or only
  assemble deterministic rows for TRA's Finalizer to synthesize?
- What authentication and allowlisting model should MCP use for mutating tools?
- Should L4 finalization be idempotent by `session_id`/`task_id`/title, or
  should each run create a distinct artifact version?
