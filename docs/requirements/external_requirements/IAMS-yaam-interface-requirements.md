# iAIMS YAAM Interface Requirements

**System:** IAMS / iAIMS MAS consensus SCM  
**Owner:** iAIMS MAS research project team  
**Date:** 2026-05-24  
**Status:** Draft  
**Primary contact:** TBD  

## 1. System Overview

The iAIMS 2026 project is a LangGraph-based multi-agent consensus system for
logistics and supply chain disruption handling. The runtime coordinates a
Planner agent, a Validator agent, deterministic SCM solver tools, and a
Finalizer path that stores verified consensus artifacts.

The Planner translates disruption context into semantic plans. The Validator
executes deterministic checks through the Cognitive Sandwich protocol and
returns conflict sets when a draft is infeasible. LangGraph state is the active
context carrier, Redis checkpointing preserves graph execution, and YAAM v2 is
the external memory substrate for working facts, episodic repair knowledge, and
final verified artifacts.

The deployment is a distributed home-lab environment. External service
locations must be resolved through environment variables such as
`YAAM_SEMANTIC_GATEWAY_URL`, `DEV_NODE_IP`, and `PHOENIX_COLLECTOR_ENDPOINT`.
The iAIMS runtime must not assume `localhost` for YAAM, Redis, Phoenix, or
database services. LLM calls are routed through OpenRouter using
`OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`, and `OPENROUTER_MODEL`.

## 2. Integration Goals

iAIMS needs YAAM for concrete memory workflows that support multi-agent
consensus and research traceability:

- Retrieve relevant prior disruptions, repairs, and consensus artifacts before
  the Planner drafts a strategy. This reduces repeated repair loops and
  supports apt deference to known feasible patterns.
- Store Planner and Validator facts in L2 working memory so both agents share
  a consistent task-level workspace. This prevents each node from reasoning
  over a different version of the plan.
- Assimilate failed drafts, solver conflict sets, repaired drafts, and final
  reasoning episodes into L3. These episodes are useful for future repair-loop
  learning and benchmark analysis.
- Finalize mathematically verified consensus artifacts into L4 so completed
  tasks can be searched, cited, and reused.
- Inspect evidence, provenance, CIAR decisions, health, and memory context from
  MCP-capable research or agent-host clients without bypassing YAAM policy.

## 3. Expected Interface

| Interface | Required? | Purpose | Notes |
|---|---:|---|---|
| API Wall `/v1/chat/completions` | No | Not used by the iAIMS runtime. | iAIMS already routes LLM calls through LangChain/OpenRouter and uses YAAM as memory, not as a chat-completion facade. |
| REST v2 `/v2/memory/...` | Yes | Current production integration for L2, L3, and L4 memory operations. | Used by `YaamSemanticClient`; must continue to accept natural-language payloads and typed envelopes. |
| MCP tools/resources/prompts | Yes | Planned discoverable interface for context retrieval, evidence inspection, CIAR explanation, health checks, and controlled writes. | First iAIMS use should be read-heavy, with privileged write/lifecycle tools allowlisted. |
| LangChain tools | No | Not required as the YAAM interface for this project. | iAIMS uses LangGraph and deterministic SCM tools; future YAAM tools should call shared YAAM services, not become a project-local dependency. |
| Direct library calls | No | Must not couple iAIMS to YAAM internals. | iAIMS must not generate embeddings locally, issue direct Cypher, or call storage adapters. |

## 4. Required Capabilities

| Capability | Tier | Read/Write/Lifecycle | Required for MVP? | Example input | Expected output | Justification |
|---|---|---|---:|---|---|---|
| Store task facts in L2 | Raw YAAM / L2 | Write | Yes | `{"session_id":"sess-123","task_id":"db_port_buffer_001","agent_id":"planner","action":"store","content":"Draft reroutes DB cargo through Port B with 3 day buffer."}` | `{"status":"success","fact_id":"fact-..."}` | Required so the Planner can publish semantic drafts to a shared workspace visible to downstream nodes. |
| Retrieve task facts from L2 | Raw YAAM / L2 | Read | Yes | `{"session_id":"sess-123","task_id":"db_port_buffer_001","agent_id":"validator","action":"retrieve"}` | `{"status":"success","facts":[...]}` | Required so the Validator can inspect the same facts the Planner used before invoking deterministic tools. |
| Query similar episodes | Raw or Unified YAAM / L3 | Read | Yes | `{"session_id":"sess-123","agent_id":"planner","nl_query":"similar port disruption with rail capacity conflict","top_k":3,"filters":{"domain_tags":["logistics"]}}` | Ranked results with source ids, provenance, and timestamps. | Required for apt deference: the Planner should reuse prior repair patterns when similar disruptions exist. |
| Assimilate repair-loop episodes | Raw or Agentic YAAM / L3 | Write/Lifecycle | Yes | `{"session_id":"sess-123","agent_id":"validator","text_to_assimilate":"Draft exceeded Port B capacity; repaired by shifting 20 percent to rail.","domain_tags":["logistics","repair-loop"]}` | `{"status":"success","episode_id":"ep-..."}` | Required to preserve failed drafts, conflict sets, and successful repairs as future training/evaluation evidence. |
| Finalize verified consensus artifact | Raw YAAM / L4 | Lifecycle | Yes | `{"task_id":"db_port_buffer_001","session_id":"sess-123","title":"Completed Task: db_port_buffer_001","final_artifact":"...","consensus_metadata":{"loops":2}}` | `{"status":"success","knowledge_id":"kd-..."}` | Required to store only mathematically verified outputs as durable consensus knowledge. |
| Assemble pre-decision context | Unified YAAM | Read | Yes | `{"session_id":"sess-123","task_id":"db_port_buffer_001","agent_id":"planner","query":"context for port capacity disruption","tiers":["l2","l3","l4"],"top_k":5}` | Context block plus evidence list and retrieval explanation. | Required to reduce prompt assembly drift and keep YAAM responsible for cross-tier evidence aggregation. |
| Explain CIAR or evidence ranking | Agentic YAAM | Read | No | `{"session_id":"sess-123","fact_id":"fact-123","include_components":true}` | CIAR components, final score, review status, and provenance. | Required for research auditability and debugging, but not needed for the first runtime-critical path. |
| Build Evidence Table | Agentic YAAM | Read | No | `{"session_id":"sess-123","task_id":"db_port_buffer_001","query":"why was this repair selected?"}` | Evidence rows with claim, source tier, source id, relevance, CIAR/policy metadata, and status. | Required for paper-quality postmortems and MCP inspection workflows. |
| Check YAAM health/config | Raw YAAM / Service | Read | Yes | `{"include_tiers":true}` or resource `yaam://health` | Tier status, configured/unconfigured indicators, and version/config summary. | Required for batch-run reliability and for distinguishing unconfigured tiers from outages. |

## 5. Use Case Scenarios

### Scenario 1: Planner Retrieves Similar Disruptions Before Drafting

**Trigger:** A new benchmark task enters the LangGraph graph.  
**Caller:** `planner_node` or a pre-planner context assembly step.  
**YAAM interface:** REST v2 `/v2/memory/l3/query`; future MCP `yaam.memory.get_context` or `yaam.memory.query`.  
**Input example:**

```json
{
  "session_id": "sess-123",
  "agent_id": "planner",
  "nl_query": "similar port congestion disruption requiring capacity-feasible rerouting",
  "top_k": 3,
  "filters": {
    "domain_tags": ["logistics", "ports"]
  }
}
```

**Expected YAAM behavior:** Query L3/L4 using natural language, return ranked
episodes or knowledge artifacts with provenance and enough evidence metadata
for prompt injection. YAAM must perform embeddings or graph expansion
internally; iAIMS must not generate embeddings or Cypher.  
**Expected response shape:** A list of results with `source_tier`,
`source_id`, `score` or ranking metadata, `content`, `timestamp`, and
`provenance.producing_agent` when available.  
**Failure handling:** Empty results are acceptable. `501` means L3/L4 is not
configured and should be recorded as a degraded memory condition. `502/503/504`
or network failures should degrade gracefully so the Planner can continue from
LangGraph state. `422` and `500` should fail loudly.  
**Trace/audit expectations:** Every request must include W3C `traceparent`.
Phoenix should show the Planner span, YAAM retrieval span, and any internal
YAAM retrieval or LLM-assisted spans under the same trace when supported.

### Scenario 2: Planner Writes Semantic Draft Facts To L2

**Trigger:** The Planner emits a draft plan or direct answer content.  
**Caller:** `planner_node`.  
**YAAM interface:** REST v2 `/v2/memory/l2/facts`; future MCP
`yaam.l2.store_fact`.  
**Input example:**

```json
{
  "session_id": "sess-123",
  "task_id": "db_port_buffer_001",
  "agent_id": "planner",
  "action": "store",
  "content": "Planner draft: reroute 40 percent of delayed cargo through Port B and reserve a 3 day buffer."
}
```

**Expected YAAM behavior:** Persist the fact in L2 scoped to the session and
task, attach provenance for the producing agent, and return a durable fact id.  
**Expected response shape:** `{"status":"success","fact_id":"fact-..."}`.  
**Failure handling:** The graph must continue if YAAM is temporarily
unreachable because LangGraph state remains the active context. `422` indicates
contract drift and must fail loudly. `501` indicates L2 is not configured and
must be recorded as a configuration problem.  
**Trace/audit expectations:** Store calls must include `traceparent`, and the
stored fact must retain `session_id`, `task_id`, `agent_id`, timestamp, and
request provenance for later audit.

### Scenario 3: Validator Records Conflict Sets And Repairs

**Trigger:** A deterministic solver rejects a Planner draft or a repair loop
produces a corrected draft.  
**Caller:** Validator node, repair-loop handler, or final graph diagnostic path.  
**YAAM interface:** REST v2 `/v2/memory/l3/assimilate`; future MCP
`yaam.lifecycle.promote` or controlled `yaam.memory.extract_facts` when
allowlisted.  
**Input example:**

```json
{
  "session_id": "sess-123",
  "agent_id": "validator",
  "text_to_assimilate": "Conflict set: Port B capacity exceeded by 20 percent. Repair shifted overflow to rail and reduced buffer from 3 days to 2 days.",
  "domain_tags": ["logistics", "validator", "repair-loop"]
}
```

**Expected YAAM behavior:** Store an episodic memory item that preserves the
failed draft, conflict set, repair action, and producing agent. If agentic
extraction or CIAR is enabled, return policy metadata separately from the stored
episode id.  
**Expected response shape:** `{"status":"success","episode_id":"ep-..."}`
plus optional provenance and policy metadata.  
**Failure handling:** `502` means the YAAM internal pipeline failed after
reaching the tier; the MAS should mark L3 unhealthy and continue if the
current task can still be completed. `422` and `500` should fail loudly during
contract validation runs.  
**Trace/audit expectations:** The conflict-set episode must be linked to the
same `traceparent` as the Planner/Validator loop and include `task_id` in
metadata when the interface supports it.

### Scenario 4: Finalizer Stores Verified Consensus Artifact

**Trigger:** The Planner/Validator loop reaches a final artifact or a controlled
fallback artifact is generated.  
**Caller:** Orchestrator finalization path.  
**YAAM interface:** REST v2 `/v2/memory/l4/finalize`; future MCP controlled
lifecycle tool if a research agent host is allowed to finalize artifacts.  
**Input example:**

```json
{
  "task_id": "db_port_buffer_001",
  "session_id": "sess-123",
  "title": "Completed Task: db_port_buffer_001",
  "final_artifact": "Verified rerouting plan with capacity-feasible allocation...",
  "consensus_metadata": {
    "loops": 2,
    "solver_status": "feasible"
  }
}
```

**Expected YAAM behavior:** Store the final artifact in L4 as durable semantic
knowledge and return a knowledge id. YAAM should distinguish verified consensus
artifacts from draft or review-only evidence.  
**Expected response shape:** `{"status":"success","knowledge_id":"kd-..."}`.  
**Failure handling:** If L4 is unconfigured (`501`) or unavailable
(`502/503/504`), the local run output remains valid but the batch result should
mark `l4_healthy=false`. `422` and `500` indicate schema or backend failures
that should be surfaced.  
**Trace/audit expectations:** The L4 document must include finalizer
provenance, `session_id`, `task_id`, timestamp, consensus metadata, and
`traceparent` linkage.

### Scenario 5: Researcher Inspects Evidence Through MCP

**Trigger:** A researcher, Codex session, or MCP-capable agent host audits a
completed or failed run.  
**Caller:** MCP client.  
**YAAM interface:** MCP resources and read-only tools, including
`yaam://sessions/{session_id}/context`, `yaam://sessions/{session_id}/facts`,
`yaam://health`, `yaam://config/ciar`, `yaam.memory.get_context`,
`yaam.ciar.explain`, and `yaam.evidence.table`.  
**Input example:**

```json
{
  "session_id": "sess-123",
  "task_id": "db_port_buffer_001",
  "query": "Explain the evidence behind the final repair decision.",
  "include_review_only": true,
  "include_suppressed": false
}
```

**Expected YAAM behavior:** Return read-only context and evidence with
provenance, CIAR/policy metadata, and source links. Resources must not expose
secrets, raw environment variables, API keys, direct database queries, or
unscoped tenant data.  
**Expected response shape:** Structured content with a compact text summary,
evidence rows, source ids, source tiers, timestamps, producing agents,
review-only flags, and policy explanations.  
**Failure handling:** MCP read failures should return structured errors with a
stable error code, retryability indicator, and partial evidence if available.  
**Trace/audit expectations:** Tool calls must be audited with client identity
when available, `session_id`, `task_id`, tool name, read/write classification,
timestamp, and downstream YAAM trace linkage.

## 6. MCP Expectations

### 6.1 Tool Requirements

| Proposed tool | Required? | Read/Write/Lifecycle | Required input fields | Required output fields |
|---|---:|---|---|---|
| `yaam.memory.query` | Yes | Read | `session_id`, `agent_id`, `query`, `top_k`, optional `task_id`, optional filters | Results, source tier/id, ranking metadata, provenance, partial-result flag |
| `yaam.memory.get_context` | Yes | Read | `session_id`, `task_id`, `agent_id`, `query`, tiers, `top_k` | Context block, evidence list, retrieval explanation, health metadata |
| `yaam.l2.store_fact` | Yes | Write | `session_id`, `task_id`, `agent_id`, `content`, optional metadata | `fact_id`, status, provenance |
| `yaam.l2.search_facts` | Yes | Read | `session_id`, `task_id`, `agent_id`, optional query/filter | Facts, source ids, timestamps, producing agents |
| `yaam.l3.search_episodes` | Yes | Read | `session_id`, `agent_id`, query, `top_k`, optional filters | Episodes, source ids, relevance/rank, provenance |
| `yaam.l3.assimilate_episode` | Yes | Write/Lifecycle | `session_id`, `agent_id`, `text_to_assimilate`, `domain_tags`, optional `task_id` metadata | `episode_id`, status, optional policy metadata |
| `yaam.l4.search_knowledge` | Yes | Read | `session_id`, `agent_id`, query, `top_k`, optional filters | Knowledge results, ids, provenance, ranking metadata |
| `yaam.l4.finalize_artifact` | Yes | Lifecycle | `session_id`, `task_id`, `title`, `final_artifact`, `consensus_metadata` | `knowledge_id`, status, audit metadata |
| `yaam.ciar.explain` | Yes | Read | `session_id`, `fact_id` or evidence item id, optional `include_components` | CIAR components, final score, review status, policy version |
| `yaam.evidence.table` | Yes | Read/Agentic | `session_id`, `task_id`, query, include flags | Evidence rows, source tier/id, claim, policy metadata, audit status |
| `yaam.health.check` | Yes | Read | Optional tier list | Overall health, tier config status, version/config summary |

### 6.2 Resource Requirements

| Proposed resource | Required? | Access scope | Notes |
|---|---:|---|---|
| `yaam://sessions/{session_id}/context` | Yes | Session | Read-only assembled context for Planner/Validator audit. |
| `yaam://sessions/{session_id}/facts` | Yes | Session/task | Read-only L2 working facts; should support task filtering. |
| `yaam://facts/{fact_id}` | Yes | Fact | Must enforce session/task/tenant visibility checks. |
| `yaam://episodes/{episode_id}` | Yes | Episode | Useful for repair-loop postmortems. |
| `yaam://knowledge/{knowledge_id}` | Yes | Knowledge artifact | Useful for verified consensus reuse and citation. |
| `yaam://health` | Yes | Service | Must distinguish configured, unconfigured, degraded, and unavailable tiers. |
| `yaam://config/ciar` | Yes | Service | Read-only policy inspection; no secrets. |
| `yaam://schemas/fact` | No | Service | Helpful but not required for iAIMS MVP. |
| `yaam://schemas/episode` | No | Service | Helpful but not required for iAIMS MVP. |
| `yaam://schemas/knowledge-document` | No | Service | Helpful but not required for iAIMS MVP. |

### 6.3 Prompt Requirements

| Proposed prompt | Required? | Purpose | Expected variables |
|---|---:|---|---|
| `yaam.prompt.evidence_table` | Yes | Generate a consistent audit view of evidence behind a final artifact or repair. | `session_id`, `task_id`, `query`, `include_review_only`, `include_suppressed` |
| `yaam.prompt.memory_inspection` | Yes | Inspect what YAAM knows for a session/task without mutating memory. | `session_id`, `task_id`, optional tiers |
| `yaam.prompt.ciar_explanation` | Yes | Explain retention or ranking decisions for facts and evidence. | `fact_id` or evidence id, `session_id`, `include_components` |
| `yaam.prompt.contradiction_review` | No | Review conflicting evidence during advanced audits. | `session_id`, `task_id`, candidate claims |
| `yaam.prompt.retrieval_strategy` | No | Help tune retrieval for exploratory research runs. | Query, tiers, filters, expected artifact type |

## 7. Data And Scope Requirements

- Mandatory identifiers for runtime REST calls: `session_id`, `agent_id`, and
  `traceparent`; `task_id` is mandatory for L2 and L4 and should be included in
  L3 metadata where supported.
- Mandatory identifiers for MCP calls: `session_id`, operation/tool name, and
  client identity when available. `task_id` is mandatory for task-scoped
  inspection, evidence table generation, L2 writes, and artifact finalization.
- Optional/future identifiers: `tenant_id` and `user_id` for multi-user or
  multi-project deployments.
- L2 facts are private to a `session_id` plus `task_id` by default. Planner and
  Validator agents in the same session/task may share them.
- L3 episodes and L4 knowledge may be queried across sessions only through
  explicit filters and policy-controlled retrieval. Cross-session search must
  return provenance and source tier metadata.
- L1 is optional in `MAS_V2_MODE`; LangGraph state remains the active context
  carrier. iAIMS does not require L1 for MVP.
- Retention expectations: L2 should persist for the run and postmortem window;
  L3 repair episodes should be retained for benchmark learning; L4 verified
  consensus artifacts should be retained durably for reuse and citation.

## 8. Provenance, Evidence, And CIAR Requirements

Responses should include provenance by default:

- source tier, source id, timestamp, producing agent, `session_id`, and
  `task_id` where applicable;
- retrieval rank or score metadata when YAAM performs retrieval;
- policy version and CIAR components when CIAR is used;
- explicit flags for review-only, partial, suppressed, superseded, or
  contradiction-related evidence when these policies are enabled.

CIAR details are required for audit and research inspection, not for the
minimum runtime path. When returned, CIAR should include certainty, impact,
age/recency behavior, final score, review status, and enough explanation to
distinguish retention policy from query relevance.

Example Evidence Table:

| Claim | Source tier | Source id | Producing agent | Evidence status | Policy metadata | Why it matters |
|---|---|---|---|---|---|---|
| Port B capacity was exceeded in the first draft. | L3 | `ep-123` | validator | accepted | `conflict_set=true` | Explains why the Planner had to repair the route allocation. |
| Final artifact was solver-feasible after 2 loops. | L4 | `kd-456` | finalizer | accepted | `loops=2` | Supports reuse as a verified consensus artifact. |
| Planner proposed a 3 day buffer. | L2 | `fact-789` | planner | superseded | `superseded_by=ep-123` | Preserves audit history without treating the draft as final truth. |

## 9. Security And Permission Requirements

- MCP resources must be read-only in the first iAIMS integration.
- Mutating MCP tools should be explicitly allowlisted. Minimum write surface:
  `yaam.l2.store_fact`, controlled L3 episode assimilation, and controlled L4
  finalization.
- Lifecycle and agentic tools such as promotion, consolidation, distillation,
  contradiction review, and fact extraction should require server-side
  allowlisting independent of client capability claims.
- Direct database access, arbitrary SQL, arbitrary Cypher, local embedding
  generation, and vector-store-specific controls must not be exposed to iAIMS
  clients.
- MCP resources must never expose `.env` values, API keys, OpenRouter secrets,
  database credentials, raw Phoenix credentials, or infrastructure host
  inventory beyond intentional health summaries.
- Read access must enforce session, task, tenant, and user boundaries when
  those identifiers are configured.

## 10. Observability Requirements

- iAIMS must propagate W3C `traceparent` headers on every REST v2 YAAM request.
- MCP calls should generate auditable spans and propagate trace context into
  downstream YAAM service calls when the host supports tracing.
- Phoenix should make the following visible when enabled: Planner span,
  Validator/tool span, YAAM L2 write/read span, YAAM L3 query/assimilate span,
  YAAM L4 finalize span, and internal YAAM policy spans for agentic tools.
- Required audit fields: operation/tool name, interface (`REST v2` or `MCP`),
  read/write/lifecycle classification, `session_id`, `task_id`, `agent_id` or
  client id, timestamp, status, error code, latency, and returned source ids.
- Batch outputs should continue recording `l3_healthy` and `l4_healthy`, and
  should add exact trace ids in future runs when available.

## 11. Reliability And Error Handling

- `422` means malformed request or contract drift and must fail loudly.
- `500` means backend crash and should fail loudly during validation and
  integration tests.
- `501` means the requested tier or capability is not configured. iAIMS should
  mark the affected tier as unavailable or unconfigured, not treat it as a
  generic outage.
- `502` means YAAM reached an initialized tier but failed inside an internal
  LLM-assisted or dependent processing pipeline.
- `503`, `504`, timeouts, and network errors should degrade gracefully where
  LangGraph state can still complete the task.
- Retrieval should return partial results when possible, but the response must
  explicitly mark partial, degraded, or tier-skipped results.
- Current iAIMS REST client timeout budget is 120 seconds for YAAM calls. MCP
  inspection tools should use shorter defaults where possible, with longer
  budgets reserved for explicitly agentic evidence or CIAR operations.
- Error responses should include a stable error code, human-readable message,
  retryability indicator, affected tier/capability, and trace/audit id when
  available.

## 12. Performance Expectations

| Workflow | Expected QPS | p50 latency | p95 latency | Timeout budget | Notes |
|---|---:|---:|---:|---:|---|
| L2 fact store/retrieve | 1-5 during batch runs | <= 250 ms | <= 1 s | 5 s | Should be lightweight shared-workspace traffic. |
| L3 query similar episodes | 1 per task before or during planning | <= 2 s | <= 10 s | 30 s | May involve embedding/vector/graph retrieval inside YAAM. |
| L3 assimilate repair episode | 1-3 per task | <= 5 s | <= 30 s | 120 s | May involve extraction or indexing; must not block graph correctness if degraded. |
| L4 finalize artifact | 1 per completed task | <= 2 s | <= 10 s | 30 s | Stores verified final artifact for reuse. |
| MCP context/evidence inspection | Ad hoc research use | <= 2 s | <= 10 s | 30 s | Read-heavy; should return partial data if agentic scoring is slow. |
| MCP CIAR/evidence table | Ad hoc research use | <= 5 s | <= 30 s | 60 s | LLM-backed policy behavior should be explicit and audited. |

## 13. Acceptance Tests

| Test | Interface | Setup | Expected result |
|---|---|---|---|
| L2 contract and traceparent | REST v2 | Mock YAAM receives `POST /v2/memory/l2/facts` store and retrieve payloads with `traceparent`. | Payload includes `session_id`, `task_id`, `agent_id`, `action`; response unwraps `fact_id` or `facts`; header is preserved. |
| L3 query/assimilate contract | REST v2 | Mock YAAM receives query and assimilate calls. | Query sends `nl_query`, `top_k`, and filters; assimilate sends natural-language text and domain tags; no local embeddings or Cypher are generated. |
| L4 finalize contract | REST v2 | Mock YAAM receives final artifact after graph output. | Payload includes `task_id`, `session_id`, `title`, `final_artifact`, and `consensus_metadata`; response returns `knowledge_id`. |
| Error semantics | REST v2 | Mock YAAM returns `501`, `502`, network error, `422`, and `500`. | `501/502/network` degrade according to policy; `422` and `500` fail loudly. |
| End-to-end trace linkage | REST v2 + Phoenix | Run one MAS task against reachable YAAM and Phoenix. | L2/L3/L4 calls include `traceparent`; Phoenix can correlate MAS and YAAM spans or logs under the same trace context. |
| MCP discovery | MCP | Connect MCP-capable client to YAAM MCP server. | Required tools and resources are discoverable with JSON schemas and read/write/lifecycle classification. |
| MCP read-only resources | MCP | Read `yaam://sessions/{session_id}/context`, facts, health, and CIAR config. | Resources return scoped data without secrets or unscoped tenant/session leakage. |
| MCP evidence table | MCP | Request evidence table for a completed task. | Response includes structured evidence rows with source tier/id, provenance, policy metadata, and review/suppression flags. |
| Isolation boundary | REST v2 + MCP | Create two sessions/tasks and store facts in both. | Session/task-scoped reads cannot access the other task's L2 facts; cross-session L3/L4 retrieval only works through explicit allowed query/filter semantics. |

## 14. Open Questions

- Should YAAM v2 add a first-class `task_id` field to L3 assimilation and query
  responses, or should iAIMS continue sending task identity in metadata and
  tags where supported?
- Should the first MCP transport for iAIMS be stdio for local Codex/agent-host
  inspection, streamable HTTP for distributed services, or both?
- Which CIAR components are stable enough to expose as contract fields in the
  first MCP release?
- Should L4 finalization through MCP be enabled for research agent hosts, or
  restricted to the existing orchestrator finalization path?
- What authentication and authorization model should apply to local research
  clients versus remote MCP clients in the home-lab deployment?
- Should future batch JSONL outputs include exact trace ids and YAAM source ids
  to support deterministic Phoenix joins?
