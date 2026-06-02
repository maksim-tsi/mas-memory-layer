# Maritime Port Sandbox YAAM Interface Requirements

**System:** Maritime Port Sandbox  
**Owner:** TBD / Maritime Port Sandbox maintainers  
**Date:** 2026-05-24  
**Status:** Draft  
**Primary contact:** TBD / Maritime Port Sandbox maintainers  

## 1. System Overview

The Maritime Port Sandbox is a deterministic FastAPI mock API and Discrete
Event Simulation (DES) environment for maritime logistics agents. It returns
DCSA-compliant port status data, accepts controlled admin state mutations, and
executes candidate routing scenarios through deterministic DES and Operations
Research (OR) capacity checks.

The sandbox does not currently integrate with YAAM directly. It would benefit
from YAAM as an external memory layer for agent test context, simulation run
history, admin mutation audit, and infeasible-run debugging. The sandbox itself
must remain a physics and rules engine: it must not use YAAM to choose routes,
calculate Pareto frontiers, retry agent workflows, mutate port state, or generate
human-readable reports for API responses.

Main callers:

- Autonomous SCM agents that read `GET /api/v1/pcs/terminals/{portCode}/status`.
- Simulation controllers and test harnesses that write state through
  `/admin/simulation/scenario` and `/api/v1/admin/set-state`.
- Orchestrators that execute scenario batches through
  `POST /api/v1/simulation/execute`.

## 2. Integration Goals

- Retrieve cross-session memory before an SCM agent queries port status or
  submits candidate routes. Justification: agent behavior is tested across
  repeated deterministic scenarios, and prior run context can help the
  orchestrator avoid repeating already evaluated candidates without changing the
  sandbox response.
- Store verified DCSA port facts, admin mutations, and simulation episodes.
  Justification: current state is in-memory and deterministic, while YAAM can
  preserve an auditable record across sessions and test runs.
- Aggregate evidence from simulation inputs, metrics, `critical_events`, and
  `failure_reason`. Justification: the simulation schema already exposes event
  timelines for explainability, and YAAM can make those timelines searchable for
  debugging.
- Inspect CIAR decisions and evidence tables for review only. Justification:
  RFC-006 requires subjective decisions, retries, Pareto selection, and report
  formatting to remain outside the sandbox.
- Expose memory resources to MCP-capable agent hosts. Justification: the main
  consumers are agents and orchestrators, so discoverable MCP resources and
  tools are the preferred human-agent interface.

## 3. Expected Interface

| Interface | Required? | Purpose | Notes |
|---|---:|---|---|
| API Wall `/v1/chat/completions` | No | Not needed by the sandbox API. | The sandbox is deterministic and should not route API behavior through chat completions. |
| REST v2 `/v2/memory/...` | Yes | Backend read/write integration for orchestrators and test harnesses. | Required for storing run episodes and admin mutation audit records after HTTP calls complete. |
| MCP tools/resources/prompts | Yes | Agent-host access to memory context, evidence, and review prompts. | Preferred for SCM agents and debugging workflows. |
| LangChain tools | No | Not required for MVP. | May be reconsidered only if the orchestrator standardizes on LangChain. |
| Direct library calls | No | Avoid coupling the sandbox process to YAAM internals. | The sandbox should remain deployable as a standalone FastAPI service. |

## 4. Required Capabilities

| Capability | Tier | Read/Write/Lifecycle | Required for MVP? | Example input | Expected output |
|---|---|---|---:|---|---|
| Retrieve route and disruption context by `tenant_id`, `task_id`, `run_id`, `scenario_id`, `port_code`, and disruption type. | Unified | Read | Yes | `{"tenant_id":"demo","task_id":"reroute-42","run_id":"api-run-xyz","port_code":"DEHAM","query":"prior congestion and storm surge outcomes"}` | Ordered context snippets with evidence ids, source tier, timestamps, producing agent, and source endpoint. |
| Store a DCSA port status fact after `GET /api/v1/pcs/terminals/{portCode}/status`. | Raw YAAM | Write | Yes | `{"port_code":"DEHAM","operationalStatus":"NORMAL","metrics":{"availableCapacityTEU":25000},"source_endpoint":"/api/v1/pcs/terminals/DEHAM/status"}` | Stored L2 fact id with provenance, timestamp, scope ids, and deterministic payload hash. |
| Store an admin mutation record after `/admin/simulation/scenario` or `/api/v1/admin/set-state`. | Raw YAAM | Write | Yes | `{"port_code":"DEHAM","scenarioType":"STORM_SURGE","severity":"HIGH","before":{...},"after":{...}}` | Stored L3 episode id with before/after state, caller metadata, trace id, and audit classification. |
| Store a completed simulation run from `/api/v1/simulation/execute`. | Raw YAAM | Write | Yes | `{"run_id":"api-run-xyz","scenarios":[{"scenario_id":"scenario-123","target_ports":["NLRTM","USNYC"]}],"result":{...}}` | Stored L3 episode id containing candidate input, metrics, `critical_events`, and failures. |
| Aggregate evidence for a simulation or port decision. | Unified | Read | Yes | `{"run_id":"api-run-xyz","scenario_id":"scenario-123","include_events":true}` | Evidence bundle with source facts, simulation events, metrics, failure reason, and retrieval explanation. |
| Generate an Evidence Table for failed or disputed runs. | Agentic YAAM | Read/Agentic | No | `{"run_id":"api-run-xyz","scenario_id":"congestion-path-deham","question":"Why was the scenario infeasible?"}` | Review-only table of claims, evidence ids, CIAR components, and suppressed/superseded evidence when requested. |
| Explain CIAR scoring for memory promotion and contradiction review. | Agentic YAAM | Read/Lifecycle | No | `{"memory_id":"mem_l3_123","include_components":true}` | CIAR score explanation with certainty, impact, age decay, recency boost, and final score. |

Requirement-to-scenario justification:

| Requirement | Justification | Scenario coverage |
|---|---|---|
| Retrieve route and disruption context. | Prior deterministic runs and admin mutations are useful to the orchestrator, but should not be embedded into sandbox execution logic. | Scenario 1, Scenario 4 |
| Store DCSA port status facts. | `PortStatusResponse` is the sandbox's public DCSA contract, and storing verified facts gives agents stable evidence across sessions. | Scenario 1, Scenario 3 |
| Store admin mutation records. | Admin endpoints mutate in-memory state, so before/after evidence is required to reconstruct test setup and explain downstream run results. | Scenario 3, Scenario 4 |
| Store completed simulation runs. | `/api/v1/simulation/execute` already returns deterministic inputs, metrics, events, and failures that should become searchable run history. | Scenario 2, Scenario 4 |
| Aggregate evidence for simulations or port decisions. | Debugging agent behavior requires joining facts, mutations, metrics, and `critical_events` without letting YAAM make sandbox decisions. | Scenario 1, Scenario 4 |
| Generate Evidence Tables for failed or disputed runs. | Infeasible simulations need reviewable claims and evidence, but this must remain outside the deterministic API response path. | Scenario 4 |
| Explain CIAR scoring for memory policy review. | CIAR helps audit why memories were promoted or weighted, while lifecycle behavior remains explicitly allowlisted and non-MVP. | Scenario 4 |

Agentic capabilities are explicitly non-MVP because the sandbox must not
delegate runtime behavior or deterministic API responses to autonomous memory
policy.

## 5. Use Case Scenarios

### Scenario 1: Retrieve Prior Context Before Agent Route Evaluation

**Trigger:** An SCM agent is about to query port status or submit candidate
routes for a task already seen in previous sessions.  
**Caller:** MCP-capable SCM agent or external orchestrator.  
**YAAM interface:** MCP tool `yaam.memory.get_context` or REST v2 read endpoint.  
**Input example:**

```json
{
  "tenant_id": "demo-tenant",
  "task_id": "reroute-42",
  "run_id": "api-run-xyz",
  "agent_id": "scm-agent-1",
  "trace_id": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00",
  "query": "Prior DEHAM disruption outcomes for target ports DEHAM and NLRTM",
  "filters": {
    "port_code": "DEHAM",
    "disruption_type": "STORM_SURGE"
  }
}
```

**Expected YAAM behavior:** Return relevant memory without mutating sandbox
state or triggering simulation. Include DCSA facts, prior admin mutation
episodes, and previous simulation outcomes that share the same tenant/task
scope.  
**Expected response shape:**

```json
{
  "context_id": "ctx_20260524_001",
  "items": [
    {
      "memory_id": "mem_l3_deham_storm_001",
      "tier": "L3",
      "source_endpoint": "/admin/simulation/scenario",
      "timestamp": "2026-05-24T10:15:00Z",
      "producing_agent": "simulation-controller",
      "summary": "DEHAM storm surge closed the port and set availableCapacityTEU to 0.",
      "evidence_ids": ["ev_admin_001", "ev_status_002"]
    }
  ],
  "retrieval_explanation": "Matched tenant_id, task_id, port_code, and disruption_type."
}
```

**Failure handling:** If YAAM retrieval fails or times out, the caller proceeds
without memory context and the sandbox API remains deterministic. Retryable
errors should be marked `retryable: true`.  
**Trace/audit expectations:** Preserve `trace_id`, `tenant_id`, `task_id`,
`run_id`, `agent_id`, query text, filters, returned memory ids, and latency.

**Requirement justification:** This scenario supports the Unified context
retrieval requirement. The sandbox exposes deterministic port and simulation
data, but cross-session context belongs in YAAM so the sandbox does not become a
decision or report system.

### Scenario 2: Store Completed Simulation Episode

**Trigger:** The orchestrator receives a completed response from
`POST /api/v1/simulation/execute`.  
**Caller:** External orchestrator or simulation test harness.  
**YAAM interface:** REST v2 write endpoint or MCP tool
`yaam.memory.store_episode`.  
**Input example:**

```json
{
  "tenant_id": "demo-tenant",
  "task_id": "reroute-42",
  "run_id": "api-run-xyz",
  "agent_id": "orchestrator-1",
  "trace_id": "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-00",
  "source_endpoint": "/api/v1/simulation/execute",
  "request": {
    "run_id": "api-run-xyz",
    "scenarios": [
      {
        "scenario_id": "scenario-123",
        "target_ports": ["NLRTM", "USNYC"]
      }
    ]
  },
  "response": {
    "run_id": "api-run-xyz",
    "simulated_scenarios": [
      {
        "scenario_id": "scenario-123",
        "execution_status": "SUCCESS",
        "metrics": {
          "total_lead_time_hours": 24.0,
          "average_queue_time_hours": 0.0,
          "total_cost_usd": 30000.0
        },
        "critical_events": [
          {"timestamp": 0.0, "event_type": "SIMULATION_START", "details": "Began simulation for scenario-123"},
          {"timestamp": 60.0, "event_type": "SIMULATION_END", "details": "Completed simulation for scenario-123"}
        ],
        "failure_reason": null
      }
    ]
  }
}
```

**Expected YAAM behavior:** Store a Raw L3 episode and index scenario ids, target
ports, event types, execution status, metrics, and source endpoint.  
**Expected response shape:**

```json
{
  "memory_id": "mem_l3_api_run_xyz",
  "tier": "L3",
  "stored": true,
  "evidence_ids": ["ev_request_001", "ev_result_001", "ev_event_001"],
  "scope": {
    "tenant_id": "demo-tenant",
    "task_id": "reroute-42",
    "run_id": "api-run-xyz"
  }
}
```

**Failure handling:** Storage failure must not alter the sandbox response. The
caller may retry idempotently using `run_id` and `scenario_id` as natural
dedupe keys.  
**Trace/audit expectations:** Record payload hash, source endpoint,
orchestrator id, trace id, event count, and per-scenario status.

**Requirement justification:** This scenario supports Raw episode storage and
Unified evidence aggregation. The simulation engine already returns metrics and
critical events; YAAM provides durable history without changing DES behavior.

### Scenario 3: Audit Admin State Mutation

**Trigger:** A simulation controller posts to `/admin/simulation/scenario` or
`/api/v1/admin/set-state`.  
**Caller:** Simulation controller, test harness, or human admin workflow.  
**YAAM interface:** REST v2 write endpoint or MCP tool
`yaam.l3.store_episode`.  
**Input example:**

```json
{
  "tenant_id": "demo-tenant",
  "task_id": "reroute-42",
  "run_id": "admin-seed-001",
  "agent_id": "simulation-controller",
  "user_id": "operator-7",
  "trace_id": "00-cccccccccccccccccccccccccccccccc-dddddddddddddddd-00",
  "source_endpoint": "/admin/simulation/scenario",
  "mutation": {
    "targetPort": "DEHAM",
    "scenarioType": "STORM_SURGE",
    "severity": "HIGH"
  },
  "before": {
    "portCode": "DEHAM",
    "operationalStatus": "NORMAL",
    "metrics": {"availableCapacityTEU": 25000}
  },
  "after": {
    "portCode": "DEHAM",
    "operationalStatus": "CLOSED",
    "metrics": {"availableCapacityTEU": 0}
  }
}
```

**Expected YAAM behavior:** Store before/after state as an auditable episode,
link the resulting DCSA fact to the mutation, and make it retrievable by
`port_code`, disruption type, task, run, and actor.  
**Expected response shape:**

```json
{
  "memory_id": "mem_l3_admin_deham_001",
  "stored": true,
  "audit_class": "state_mutation",
  "evidence_ids": ["ev_before_001", "ev_mutation_001", "ev_after_001"]
}
```

**Failure handling:** If YAAM is unavailable, the admin endpoint must still
return according to sandbox rules. The controller should emit a retryable audit
write error outside the sandbox.  
**Trace/audit expectations:** Record actor, user id when present, endpoint,
before/after hashes, port code, mutation type, and trace id.

**Requirement justification:** This scenario supports Raw fact and episode
storage. Admin endpoints mutate in-memory state, so an external audit trail is
needed to reconstruct test setup across sessions.

### Scenario 4: Diagnose Infeasible Simulation

**Trigger:** `/api/v1/simulation/execute` returns
`INFEASIBLE_DURING_SIMULATION` with `failure_reason`.  
**Caller:** Orchestrator debugging workflow or MCP-capable developer agent.  
**YAAM interface:** MCP tools `yaam.memory.query`, `yaam.evidence.table`, and
optional `yaam.ciar.explain`.  
**Input example:**

```json
{
  "tenant_id": "demo-tenant",
  "task_id": "reroute-42",
  "run_id": "api-run-failed-001",
  "scenario_id": "congestion-path-deham",
  "agent_id": "debug-agent-1",
  "trace_id": "00-eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee-ffffffffffffffff-00",
  "question": "Which prior capacity mutations and DES events explain the infeasible DEHAM run?"
}
```

**Expected YAAM behavior:** Retrieve similar failed runs and produce a
review-only evidence table. YAAM must not retry the simulation, propose a
Pareto frontier, or write new sandbox state.  
**Expected response shape:**

```json
{
  "evidence_table_id": "evt_congestion_path_deham_001",
  "rows": [
    {
      "claim": "DEHAM capacity was reduced below vessel payload.",
      "evidence_id": "ev_admin_001",
      "source_tier": "L3",
      "ciar": {
        "certainty": 0.98,
        "impact": 0.91,
        "age_decay": 0.02,
        "recency_boost": 0.10,
        "final_score": 0.94
      }
    },
    {
      "claim": "The DES retry loop exceeded the maximum queue retry count.",
      "evidence_id": "ev_failure_001",
      "source_tier": "L3",
      "ciar": {
        "certainty": 1.0,
        "impact": 0.88,
        "age_decay": 0.0,
        "recency_boost": 0.08,
        "final_score": 0.96
      }
    }
  ]
}
```

**Failure handling:** If agentic evidence generation fails, return retrieved
raw evidence or an explicit partial result. The sandbox must not block on this
workflow.  
**Trace/audit expectations:** Record query, memory ids considered, generated
claims, CIAR component scores, suppressed evidence requested, and partial result
status.

**Requirement justification:** This scenario supports Agentic review
capabilities while preserving RFC-006 boundaries. YAAM helps debug the run, but
the sandbox remains a deterministic executor.

## 6. MCP Expectations

Complete this section because the system expects MCP use by agent hosts and
developer debugging workflows.

### 6.1 Tool Requirements

| Proposed tool | Required? | Read/Write/Lifecycle | Required input fields | Required output fields |
|---|---:|---|---|---|
| `yaam.memory.query` | Yes | Read | `tenant_id`, `task_id`, query, optional `run_id`, `scenario_id`, `port_code`, `trace_id` | `items`, `memory_id`, `tier`, `evidence_ids`, `retrieval_explanation`, `trace_id` |
| `yaam.memory.get_context` | Yes | Read | `tenant_id`, `task_id`, `agent_id`, query, filters, `trace_id` | `context_id`, ordered context items, evidence ids, provenance |
| `yaam.l2.store_fact` | Yes | Write | `tenant_id`, `task_id`, `run_id`, `agent_id`, `trace_id`, fact payload, source endpoint | `memory_id`, `tier`, `stored`, payload hash, provenance |
| `yaam.l3.store_episode` | Yes | Write | `tenant_id`, `task_id`, `run_id`, `agent_id`, `trace_id`, episode payload, source endpoint | `memory_id`, `tier`, `stored`, evidence ids, scope |
| `yaam.ciar.explain` | No | Read | `tenant_id`, `task_id`, `memory_id`, `trace_id` | CIAR component scores, final score, source evidence |
| `yaam.evidence.table` | No | Read/Agentic | `tenant_id`, `task_id`, `run_id`, `scenario_id`, question, `trace_id` | table id, rows, claims, evidence ids, CIAR components, partial status |

Write tools are required because the project needs durable run and mutation
history. Agentic tools are not required for MVP because they support debugging
only and must not affect sandbox execution.

### 6.2 Resource Requirements

| Proposed resource | Required? | Access scope | Notes |
|---|---:|---|---|
| `yaam://sessions/{session_id}/context` | No | Session | Useful but not required because this project scopes primarily by task and run. |
| `yaam://sessions/{session_id}/facts` | No | Session | Optional for interactive debugging. |
| `yaam://runs/{run_id}/context` | Yes | Run | Required to inspect simulation context by `run_id`. |
| `yaam://runs/{run_id}/scenarios/{scenario_id}` | Yes | Scenario | Required to inspect stored simulation episodes and failures. |
| `yaam://ports/{port_code}/facts` | Yes | Port | Required to retrieve DCSA facts and admin mutation history. |
| `yaam://facts/{fact_id}` | Yes | Fact | Required for evidence traceability. |
| `yaam://health` | Yes | Service | Required so callers can degrade gracefully when memory is unavailable. |
| `yaam://config/ciar` | No | Service | Debug-only visibility into CIAR policy. |

### 6.3 Prompt Requirements

| Proposed prompt | Required? | Purpose | Expected variables |
|---|---:|---|---|
| `yaam.prompt.evidence_table` | No | Review failed or disputed simulation runs. | `tenant_id`, `task_id`, `run_id`, `scenario_id`, `question` |
| `yaam.prompt.memory_inspection` | Yes | Inspect prior facts and episodes before agent action. | `tenant_id`, `task_id`, optional `run_id`, `port_code`, `disruption_type` |
| `yaam.prompt.ciar_explanation` | No | Explain why a memory was promoted or weighted. | `memory_id`, `tenant_id`, `task_id` |
| `yaam.prompt.contradiction_review` | No | Review conflicting DCSA facts across test sessions. | `tenant_id`, `task_id`, `port_code`, time window |

## 7. Data And Scope Requirements

- Mandatory identifiers for every write: `tenant_id`, `task_id`, `run_id`,
  `agent_id`, and `trace_id`.
- `scenario_id` is mandatory for scenario-specific simulation memories.
- `port_code` is mandatory for port facts and admin mutation memories.
- `user_id` is required only for human-triggered admin or test activity.
- `session_id` is optional and may be used by interactive MCP hosts.
- Read sharing across agents is allowed inside the same `tenant_id` and
  `task_id`, because orchestrators and SCM agents need shared route context.
- Memory must not be shared across tenants unless YAAM has an explicit
  cross-tenant test-fixture mode.
- Admin mutation audit records should be visible to simulation controllers and
  debugging agents, but not to consumer-only agents unless explicitly allowed.
- Retention expectation: L2 DCSA facts may be compacted when superseded by newer
  facts with the same scope; L3 simulation and admin episodes should be retained
  for the duration of the experiment or benchmark; L4 distilled knowledge is
  optional and should only contain non-sensitive generalized findings.

These scoping requirements are necessary because the sandbox is used for
repeatable agent tests where the same port codes and scenario ids may appear in
different tenants or benchmark tasks.

## 8. Provenance, Evidence, And CIAR Requirements

- Responses must include source tier, source id, timestamp, producing agent,
  source endpoint, scope ids, and payload hash when available.
- Retrieval responses should include evidence ids and a retrieval explanation so
  downstream agents can distinguish DCSA facts from admin mutations and
  simulation outcomes.
- CIAR components should be returned for agentic review workflows:
  `certainty`, `impact`, `age_decay`, `recency_boost`, and `final_score`.
- Review-only evidence should be returned for debugging when requested.
- Suppressed or superseded evidence should be returned only for audit and
  contradiction review tools, never by default in consumer context.
- Evidence Tables are useful for failed or disputed simulations, especially
  when an infeasible run must be explained from prior admin mutations and DES
  event history.

Example Evidence Table:

| Claim | Evidence id | Source tier | Source endpoint | CIAR final score | Notes |
|---|---|---|---|---:|---|
| DEHAM was closed before the simulation run. | `ev_admin_001` | L3 | `/admin/simulation/scenario` | 0.94 | Before/after state shows `availableCapacityTEU` changed to 0. |
| Scenario `congestion-path-deham` exceeded queue retries. | `ev_failure_001` | L3 | `/api/v1/simulation/execute` | 0.96 | `failure_reason` and `critical_events` include retry exhaustion. |

These metadata requirements are justified by the sandbox's existing event
timeline and strict API contracts: a memory result must be traceable back to a
specific endpoint response or admin input.

## 9. Security And Permission Requirements

- Consumer SCM agents must have read-only YAAM access.
- Simulation controllers and test harnesses may write facts and episodes.
- Admin audit writes must be allowlisted because they may include before/after
  state and human operator metadata.
- Lifecycle operations such as promotion, consolidation, contradiction review,
  distillation, and Evidence Table generation must require explicit
  allowlisting.
- YAAM must never mutate sandbox state, call admin endpoints, calculate Pareto
  frontiers, handle retries, or generate sandbox API responses.
- Private `.env` values, concrete private IPs, credentials, and secrets must not
  be stored in YAAM memories or exposed through MCP resources.
- MCP resources must not expose hidden admin routes to consumer-only agents
  unless the caller is explicitly authorized.

These restrictions preserve RFC-006 separation of concerns and prevent memory
tools from becoming an unreviewed control plane for deterministic simulations.

## 10. Observability Requirements

- Callers should propagate W3C `traceparent` headers or equivalent `trace_id`
  fields into YAAM reads and writes.
- Phoenix or equivalent tracing should show spans for memory context retrieval,
  fact/episode storage, evidence aggregation, and agentic CIAR review.
- Tool-call audits must include `tenant_id`, `task_id`, `run_id`, optional
  `scenario_id`, `port_code`, `agent_id`, optional `user_id`, source endpoint,
  memory ids returned or written, latency, status, and error code.
- Required metrics: request count, p50/p95 latency by workflow, timeout count,
  retry count, partial result count, and write dedupe count.
- Traces should correlate YAAM operations with sandbox endpoint calls such as
  `http://${DEV_NODE_IP}:8001/api/v1/simulation/execute` without storing
  private host values.

Observability is required because YAAM must be debuggable as a sidecar memory
layer while failures must not change deterministic sandbox behavior.

## 11. Reliability And Error Handling

- Retrieval failures should fail open: the caller proceeds without YAAM context
  and records a memory warning outside the sandbox response.
- Write failures should be retryable and idempotent using `run_id`,
  `scenario_id`, source endpoint, and payload hash as dedupe keys.
- Evidence Table and CIAR failures should return partial raw evidence when
  possible.
- Embedding or LLM-backed extraction failures must not block DCSA reads,
  simulation execution, or admin mutations.
- YAAM should return a consistent error shape:

```json
{
  "code": "YAAM_TIMEOUT",
  "message": "Memory context retrieval exceeded timeout budget.",
  "retryable": true,
  "trace_id": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00",
  "partial_results": []
}
```

This behavior is required because the sandbox is a deterministic test fixture:
memory is valuable for context and audit, but must not become a runtime
dependency for core API correctness.

## 12. Performance Expectations

| Workflow | Expected QPS | p50 latency | p95 latency | Timeout budget | Notes |
|---|---:|---:|---:|---:|---|
| Context query before agent decision | 1-5 | 150 ms | 500 ms | 1 s | Low-QPS interactive or orchestrator workflow. Retrieval timeout must fail open. |
| Store DCSA fact or admin mutation | 1-10 | 250 ms | 1 s | 2 s | Writes should be idempotent and retryable by payload hash. |
| Store completed simulation episode | 1-5 | 300 ms | 1 s | 2 s | Episode payloads may include multiple scenarios and event timelines. |
| Evidence aggregation for run debugging | <1 | 1 s | 3 s | 5 s | Can return partial evidence. |
| Agentic Evidence Table or CIAR review | <1 | 2 s | 5 s | 15 s | Review-only path; may be asynchronous if needed. |

The expected load is low because the sandbox is used for deterministic
experiments and agent evaluation, not high-volume production traffic.

## 13. Acceptance Tests

| Test | Interface | Setup | Expected result |
|---|---|---|---|
| Retrieve prior route context | MCP `yaam.memory.get_context` or REST read | Store one DEHAM storm-surge admin episode and one simulation episode under the same `tenant_id` and `task_id`. | Query by `port_code=DEHAM` and `disruption_type=STORM_SURGE` returns both memories with evidence ids and provenance. |
| Store completed simulation episode | REST write or MCP `yaam.l3.store_episode` | Execute a sample payload equivalent to `{"run_id":"api-run-xyz","scenarios":[{"scenario_id":"scenario-123","target_ports":["NLRTM","USNYC"]}]}` against `/api/v1/simulation/execute`. | YAAM stores an L3 episode with run id, scenario id, target ports, metrics, `critical_events`, source endpoint, and payload hash. |
| Audit admin mutation | REST write or MCP `yaam.l3.store_episode` | Apply a DEHAM `STORM_SURGE` mutation and capture before/after DCSA state. | YAAM stores before/after evidence, actor metadata, `trace_id`, source endpoint, and audit class `state_mutation`. |
| Diagnose infeasible simulation | MCP `yaam.memory.query` plus optional `yaam.evidence.table` | Store an infeasible DEHAM scenario with `failure_reason` and prior capacity mutation evidence. | Query returns similar failed runs and an evidence table linking failure to admin mutation and DES retry exhaustion. |
| Fail open on YAAM timeout | MCP or REST | Force a YAAM retrieval timeout before an agent reads `http://${DEV_NODE_IP}:8001/api/v1/pcs/terminals/DEHAM/status`. | Caller records `YAAM_TIMEOUT`, proceeds without memory context, and sandbox API behavior is unchanged. |

## 14. Open Questions

- Should YAAM provide a first-class `run_id` resource namespace, or should run
  records be represented only as session/task-scoped episodes?
- Which actor is responsible for writing memories: the sandbox process, the
  external orchestrator, or a sidecar audit collector?
- Should Evidence Table generation be synchronous for small runs or always
  asynchronous?
- What exact allowlist mechanism should gate lifecycle operations such as
  promotion, consolidation, contradiction review, and distillation?
- How should YAAM dedupe repeated deterministic runs when the same `run_id` is
  intentionally reused during regression testing?
