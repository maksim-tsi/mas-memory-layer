# SCM-Cert-Bench YAAM Interface Requirements

**System:** SCM-Cert-Bench  
**Owner:** SCM-Cert-Bench maintainers  
**Date:** 2026-05-24  
**Status:** Draft  
**Primary contact:** Maksim Ilin / project maintainers  

## 1. System Overview

SCM-Cert-Bench is a research benchmark and tooling repository for evaluating agentic AI and multi-agent systems (MAS) in supply chain management. The project contains benchmark datasets, a Bronze/Silver/Gold medallion data pipeline, task generation utilities, Gold task curation artifacts, and LLM-as-judge evaluation scripts.

The current generation architecture uses:

- Bronze sources such as extracted Cognitive Task Templates (CTTs), retail numbers, port and maritime data, and economics story templates.
- A committed Silver layer under `data/silver/`.
- A dedicated Gold PostgreSQL database reached via `SCM_BENCH_DB_URL`.
- A Triad generator that combines `CTTMaster`, `DomainRetail` or `DomainPorts`, and `StoryTemplate` records into synthetic supply-chain tasks.
- Gold benchmark files under `data/gold/`, including `golden_tasks_complete.jsonl` and the answer-safe `golden_tasks_questions_only.jsonl`.
- OpenRouter-based generation and LLM-as-judge workflows.
- Arize Phoenix tracing for generation and debugging.

SCM-Cert-Bench must remain methodologically isolated from YAAM / agent-memory databases during benchmark generation and evaluation. YAAM may still be valuable as an external memory capability if it enforces strong scoping, answer-leakage controls, provenance, and write permissions.

## 2. Integration Goals

SCM-Cert-Bench needs YAAM for concrete full-lifecycle workflows:

- retrieve contamination-safe operational context before an evaluated MAS answers a benchmark prompt;
- store completed benchmark run episodes after evaluation, including tool traces, final artifacts, and judge metrics;
- retrieve evidence tables and provenance for generated tasks, Gold curation, and judged results;
- inspect CIAR decisions and memory-policy behavior for debugging without letting benchmark runners mutate memory policy;
- support contradiction review and safe-refusal evaluation for adversarial benchmark tasks;
- store Gold curation decisions in a maintainer-only memory scope;
- correlate YAAM memory records with Phoenix traces and local benchmark artifacts.

The primary integration goal is not to let YAAM solve benchmark tasks. It is to provide controlled memory, auditability, and post-run learning while preserving benchmark validity.

## 3. Expected Interface

| Interface | Required? | Purpose | Notes |
|---|---:|---|---|
| API Wall `/v1/chat/completions` | No | Chat-completion mediation is not required for SCM-Cert-Bench MVP. | May be revisited if YAAM becomes the central gateway for evaluated agents. |
| REST v2 `/v2/memory/...` | Yes | Batch ingestion of run episodes, judged results, and curation events. | Needed for script-driven workflows such as IAIMS run evaluation ingestion. |
| MCP tools/resources/prompts | Yes | Agent-host access to read-only memory context, evidence, contradiction review, and controlled maintainer writes. | Preferred interface for MAS experiments and future MCP-capable agent hosts. |
| LangChain tools | No | No direct LangChain tool contract is required by current repo workflows. | Optional adapter only if a future harness adopts LangChain. |
| Direct library calls | No | Preserve service boundary and deployment portability. | SCM-Cert-Bench should not import YAAM internals directly. |

## 4. Required Capabilities

| Capability | Tier | Read/Write/Lifecycle | Required for MVP? | Example input | Expected output |
|---|---|---|---:|---|---|
| Contamination-safe benchmark context retrieval | Unified YAAM | Read | Yes | `{"task_id":"db_port_buffer_001","agent_id":"iaims-runner","allowed_fields":["scenario_context","public_facts"]}` | Ranked context with source ids, no hidden answers, no judge notes, no curation-only fields. |
| Post-run episode storage | Raw YAAM / Agentic YAAM | Write / Lifecycle | Yes | `{"task_id":"db_port_buffer_001","model_id":"deepseek/deepseek-v3.2","final_artifact":"...","tool_trace":[...],"judged_metrics":{...}}` | Stable episode id, stored artifact ids, audit metadata, optional lifecycle status. |
| Evidence and provenance retrieval | Unified YAAM | Read | Yes | `{"task_id":"db_port_buffer_001","include":["ctt","domain_data","story","judge"]}` | Evidence table with source tier, source id, timestamp, producing service, and confidence metadata. |
| CIAR explanation and memory-policy audit | Agentic YAAM | Read | Yes | `{"memory_ids":["fact_123","episode_456"],"explain":true}` | Certainty, impact, age decay, recency boost, final score, and promotion/suppression rationale. |
| Contradiction and safe-refusal support | Unified YAAM / Agentic YAAM | Read / Controlled Agentic | Yes | `{"task_id":"adversarial_port_strike_001","claims":[...]}` | Supporting and conflicting evidence, contradiction flag, infeasibility rationale, safe-refusal cue. |
| Gold task curation memory | Raw YAAM | Write | Yes | `{"task_id":"candidate_001","decision":"rejected","reason":"incorrect EOQ arithmetic","source_triad":{...}}` | Maintainer-only curation record linked to candidate task and source triad. |
| Trace correlation with Phoenix and benchmark artifacts | Raw YAAM / Unified YAAM | Read / Write metadata | Yes | `{"trace_id":"phoenix-trace-id","artifact_path":"data/dev_bench/tasks/synthetic_tasks.jsonl","task_id":"candidate_001"}` | Cross-reference record linking YAAM memory ids, Phoenix trace id, and local artifact identifiers. |
| Strict write and lifecycle permissions | Raw / Unified / Agentic YAAM | Security control | Yes | `{"caller_role":"benchmark_runtime_agent","tool":"yaam.l2.store_fact"}` | Permission denial unless caller is allowlisted as maintainer or approved ingestion service. |

### Requirement Justifications

- **R1: Contamination-safe benchmark context retrieval.** Evaluated agents may benefit from operational memory, but exposure to `ground_truth_answer`, hidden judge reasoning, or curation notes would invalidate benchmark results.
- **R2: Post-run episode storage.** Benchmark runs produce valuable multi-turn trajectories, final artifacts, failures, and scores that should be preserved for reproducibility and longitudinal analysis.
- **R3: Evidence and provenance retrieval.** Publication review and benchmark maintenance require explaining how a generated or curated task connects to CTTs, domain data, story templates, run artifacts, and judge evidence.
- **R4: CIAR explanation and memory-policy audit.** Maintainers need to debug why YAAM promoted, suppressed, or ranked memory items without granting benchmark runners mutation rights.
- **R5: Contradiction and safe-refusal support.** SCM-Cert-Bench v2 explicitly tests adversarial contradictions and safe refusal; YAAM must support conflict-aware evidence retrieval.
- **R6: Gold task curation memory.** Human review decisions are durable research artifacts, but they are hidden from evaluated agents and must be scoped to maintainers.
- **R7: Trace correlation with Phoenix and benchmark artifacts.** Generation failures and judge anomalies need a path from Phoenix traces to YAAM evidence and local JSONL artifacts.
- **R8: Strict write and lifecycle permissions.** Runtime agents must not mutate benchmark memory or trigger consolidation/promotion during evaluation unless explicitly allowlisted.

## 5. Use Case Scenarios

### Scenario 1: Pre-run context retrieval with hidden-answer leakage guard

**Trigger:** An evaluated MAS starts a task from `golden_tasks_questions_only.jsonl`.  
**Caller:** Benchmark runtime agent or orchestration harness.  
**YAAM interface:** MCP tool `yaam.memory.get_context`.  
**Input example:**

```json
{
  "task_id": "db_port_buffer_001",
  "session_id": "iaims26-may2026-run-001",
  "agent_id": "planning-agent",
  "allowed_fields": ["public_context", "operational_facts", "tool_sops"],
  "forbidden_fields": ["ground_truth_answer", "ground_truth_reasoning", "judge_reasoning", "curation_notes"]
}
```

**Expected YAAM behavior:** Return relevant public memory and operational facts only. Filter out all Gold answers, judge artifacts, and curation-only records.  
**Expected response shape:** Ranked context chunks with `memory_id`, `source_tier`, `source_id`, `timestamp`, `producer`, `summary`, `evidence`, and `leakage_guard_passed=true`.  
**Failure handling:** If YAAM cannot prove the leakage guard passed, return a fail-closed error and no context.  
**Trace/audit expectations:** Audit caller identity, task id, forbidden-field filter, returned memory ids, and trace correlation id.

### Scenario 2: Post-run episode storage from IAIMS debug ledger

**Trigger:** An IAIMS run finishes and `evaluation_results_debug_[model].jsonl` is available.  
**Caller:** SCM-Cert-Bench ingestion script.  
**YAAM interface:** REST v2 write endpoint or MCP write tool `yaam.l3.store_episode`.  
**Input example:**

```json
{
  "task_id": "db_port_buffer_001",
  "model_id": "deepseek/deepseek-v3.2",
  "session_id": "iaims26-may2026",
  "final_artifact": "...",
  "messages": ["..."],
  "tool_trace": ["..."],
  "status": "completed",
  "judged_metrics": {
    "overall_score": 9.4
  }
}
```

**Expected YAAM behavior:** Store the run as an episode after the task is complete. Do not expose it to active benchmark agents in the same evaluation scope.  
**Expected response shape:** `episode_id`, stored artifact ids, created timestamp, policy status, and audit id.  
**Failure handling:** Return a retryable error for transient storage failures; never block local benchmark result files from being written.  
**Trace/audit expectations:** Include source artifact path, ingest script identity, model id, and judge model id if available.

### Scenario 3: Evidence table retrieval for a generated Gold task

**Trigger:** A reviewer or maintainer asks why a task is included in the Gold set.  
**Caller:** Maintainer review tool or documentation agent.  
**YAAM interface:** MCP tool `yaam.evidence.table` and resource `yaam://facts/{fact_id}`.  
**Input example:**

```json
{
  "task_id": "db_port_buffer_001",
  "include_sources": ["ctt", "domain_data", "story_template", "generation_trace", "judge_result"]
}
```

**Expected YAAM behavior:** Return a structured evidence table linking the task to its source triad, generation trace, curation decision, and evaluation results when available.  
**Expected response shape:** Evidence rows with `source_tier`, `source_id`, `artifact_ref`, `producer`, `timestamp`, `claim`, `supports`, and `visibility_scope`.  
**Failure handling:** Return partial evidence with an explicit `partial=true` flag if some sources are unavailable.  
**Trace/audit expectations:** Record reviewer identity and every evidence id returned.

### Scenario 4: CIAR explanation for conflicting port data

**Trigger:** A generated task uses port data that conflicts with newer port evidence.  
**Caller:** Maintainer or generation-debug agent.  
**YAAM interface:** MCP read tool `yaam.ciar.explain`.  
**Input example:**

```json
{
  "claims": [
    "Port of Singapore annual throughput is 41.12 million TEU",
    "Port of Singapore average transshipment dwell time is 9.5 days"
  ],
  "task_id": "db_port_buffer_001",
  "include_suppressed": true
}
```

**Expected YAAM behavior:** Explain which memory items support or conflict with each claim and why each item was ranked, suppressed, or promoted.  
**Expected response shape:** CIAR components including certainty, impact, age decay, recency boost, final score, rationale, and evidence ids.  
**Failure handling:** If CIAR policy metadata is unavailable, return evidence rankings and a clear `ciar_unavailable` warning.  
**Trace/audit expectations:** Include policy version, scoring timestamp, and caller role.

### Scenario 5: Contradiction review for adversarial safe-refusal task

**Trigger:** SCM-Cert-Bench constructs or evaluates a contradiction-injected task.  
**Caller:** Benchmark generation or evaluation support agent.  
**YAAM interface:** MCP prompt `yaam.prompt.contradiction_review` and tool `yaam.memory.query`.  
**Input example:**

```json
{
  "task_id": "adversarial_port_strike_001",
  "claims": [
    "Terminal is closed due to strike",
    "Terminal has normal handling capacity during the same window"
  ],
  "expected_behavior": "safe_refusal_if_infeasible"
}
```

**Expected YAAM behavior:** Return both supporting and conflicting evidence and flag whether the planning context is infeasible.  
**Expected response shape:** `contradiction_detected`, `infeasibility_reason`, `supporting_evidence`, `conflicting_evidence`, and suggested safe-refusal rationale.  
**Failure handling:** If evidence is insufficient, return `insufficient_evidence` rather than inventing a contradiction.  
**Trace/audit expectations:** Capture all claims, returned evidence ids, and the contradiction decision.

### Scenario 6: Curator writes rejection or approval metadata

**Trigger:** A human curator validates a generated candidate task.  
**Caller:** Maintainer-only curation script or review UI.  
**YAAM interface:** REST v2 write endpoint or MCP write tool `yaam.curation.record_decision`.  
**Input example:**

```json
{
  "task_id": "candidate_001",
  "decision": "rejected",
  "reason": "incorrect EOQ arithmetic in ground_truth_reasoning",
  "source_triad": {
    "ctt_id": "ctt-uuid",
    "domain_data_id": "port-uuid",
    "story_template_id": "story-uuid"
  },
  "reviewer": "maintainer"
}
```

**Expected YAAM behavior:** Store the curation decision in a maintainer-only scope and link it to the source triad and generation trace.  
**Expected response shape:** `curation_record_id`, `task_id`, `visibility_scope=maintainer_only`, timestamp, and audit id.  
**Failure handling:** Reject writes from runtime agents or unauthenticated callers.  
**Trace/audit expectations:** Capture reviewer, decision, source triad ids, and original generation trace id.

### Scenario 7: Phoenix trace correlation for generation failure

**Trigger:** The Triad generator fails Pydantic validation or returns malformed JSON.  
**Caller:** Maintainer or debugging assistant.  
**YAAM interface:** REST metadata write plus MCP evidence read.  
**Input example:**

```json
{
  "trace_id": "phoenix-trace-id",
  "generation_attempt": 2,
  "task_candidate_id": "candidate_001",
  "error_type": "ValidationError",
  "artifact_ref": "data/dev_bench/tasks/synthetic_tasks.jsonl"
}
```

**Expected YAAM behavior:** Store or retrieve the correlation between Phoenix trace, candidate task, source triad, raw model response reference, and validation failure.  
**Expected response shape:** Correlation id, trace id, task candidate id, source triad ids, error summary, and linked memory ids.  
**Failure handling:** If Phoenix is unavailable, preserve the YAAM correlation record with `trace_status=unverified`.  
**Trace/audit expectations:** Include `traceparent` if provided and record all linked artifact identifiers.

### Scenario 8: Runtime write or lifecycle permission denial

**Trigger:** An evaluated runtime agent attempts to write a fact or trigger memory consolidation during benchmark execution.  
**Caller:** Benchmark runtime agent.  
**YAAM interface:** MCP tool such as `yaam.l2.store_fact` or lifecycle tool.  
**Input example:**

```json
{
  "caller_role": "benchmark_runtime_agent",
  "task_id": "db_port_buffer_001",
  "operation": "yaam.l2.store_fact",
  "payload": {
    "fact": "The correct answer is 15 days"
  }
}
```

**Expected YAAM behavior:** Deny the operation unless the caller is allowlisted as a maintainer or approved post-run ingestion service.  
**Expected response shape:** Permission error with code, caller role, operation, and remediation hint.  
**Failure handling:** Fail closed. Do not queue unauthorized writes.  
**Trace/audit expectations:** Log caller identity, attempted operation, task id, and denial reason.

## 6. MCP Expectations

SCM-Cert-Bench expects MCP to be the primary agent-facing YAAM interface for MVP. Runtime agents should mostly receive read-only tools and resources; maintainer and ingestion workflows may receive write tools through explicit allowlisting.

### 6.1 Tool Requirements

| Proposed tool | Required? | Read/Write/Lifecycle | Required input fields | Required output fields |
|---|---:|---|---|---|
| `yaam.memory.query` | Yes | Read | `query`, `task_id`, `session_id`, `agent_id`, `visibility_scope`, `forbidden_fields` | `results`, `source_ids`, `source_tiers`, `scores`, `leakage_guard_passed` |
| `yaam.memory.get_context` | Yes | Read | `task_id`, `session_id`, `agent_id`, `allowed_fields`, `forbidden_fields` | `context`, `evidence_ids`, `visibility_scope`, `audit_id` |
| `yaam.l2.store_fact` | No for runtime agents; Yes for maintainers | Write | `fact`, `source`, `task_id`, `caller_role`, `visibility_scope` | `fact_id`, `policy_status`, `audit_id` |
| `yaam.l3.store_episode` | Yes | Write / Lifecycle | `task_id`, `session_id`, `model_id`, `final_artifact`, `tool_trace`, `judged_metrics`, `caller_role` | `episode_id`, `artifact_ids`, `policy_status`, `audit_id` |
| `yaam.ciar.explain` | Yes | Read | `memory_ids` or `claims`, `task_id`, `include_suppressed`, `caller_role` | `ciar_components`, `rationale`, `evidence_ids`, `policy_version` |
| `yaam.evidence.table` | Yes | Read / Agentic | `task_id`, `include_sources`, `visibility_scope` | `rows`, `partial`, `suppressed_evidence`, `audit_id` |
| `yaam.contradiction.review` | Yes | Read / Controlled Agentic | `task_id`, `claims`, `expected_behavior`, `caller_role` | `contradiction_detected`, `supporting_evidence`, `conflicting_evidence`, `safe_refusal_rationale` |
| `yaam.curation.record_decision` | Yes | Write | `task_id`, `decision`, `reason`, `source_triad`, `reviewer`, `caller_role` | `curation_record_id`, `visibility_scope`, `audit_id` |

### 6.2 Resource Requirements

| Proposed resource | Required? | Access scope | Notes |
|---|---:|---|---|
| `yaam://sessions/{session_id}/context` | Yes | Session | Runtime-readable only after leakage guard and visibility filtering. |
| `yaam://sessions/{session_id}/facts` | Yes | Session | Must exclude Gold answers and curation-only records for runtime agents. |
| `yaam://facts/{fact_id}` | Yes | Fact | Used for evidence and provenance review. |
| `yaam://episodes/{episode_id}` | Yes | Episode | Maintainer/ingestion scope for benchmark run artifacts. |
| `yaam://tasks/{task_id}/evidence` | Yes | Task | Required for publication audit and Gold curation review. |
| `yaam://tasks/{task_id}/curation` | Yes | Task / Maintainer-only | Must not be visible to evaluated agents. |
| `yaam://health` | Yes | Service | Harness can fail fast or degrade cleanly. |
| `yaam://config/ciar` | Yes | Service / Maintainer-only | Needed for reproducible policy audits. |

### 6.3 Prompt Requirements

| Proposed prompt | Required? | Purpose | Expected variables |
|---|---:|---|---|
| `yaam.prompt.evidence_table` | Yes | Produce a reviewer-friendly evidence table for a task or run. | `task_id`, `include_sources`, `visibility_scope` |
| `yaam.prompt.memory_inspection` | Yes | Inspect what memory would be visible to an evaluated agent. | `task_id`, `session_id`, `agent_id`, `forbidden_fields` |
| `yaam.prompt.ciar_explanation` | Yes | Explain CIAR decisions for facts, episodes, or claims. | `memory_ids`, `claims`, `include_suppressed` |
| `yaam.prompt.contradiction_review` | Yes | Review conflicting evidence and safe-refusal implications. | `claims`, `task_id`, `expected_behavior` |
| `yaam.prompt.curation_summary` | Yes | Summarize curation decisions without exposing answers to runtime agents. | `task_id`, `curation_record_ids`, `reviewer_scope` |

## 7. Data And Scope Requirements

- Required identifiers for every runtime read call: `task_id`, `session_id`, `agent_id`, `caller_role`.
- Required identifiers for write or lifecycle calls: `task_id`, `session_id` or `run_id`, `caller_role`, `tenant_id` if multi-tenant deployment is enabled.
- `user_id` is optional for batch scripts but required for human curator writes when available.
- Runtime agents may read only public operational memory, public task context, and approved tool SOPs.
- Runtime agents must never read `ground_truth_answer`, `ground_truth_reasoning`, judge reasoning, curation notes, rejected-task diagnostics, or hidden Gold internals.
- Post-run ingestion services may write completed episodes after an evaluation task has ended.
- Maintainers may write curation records and request CIAR explanations.
- Cross-agent sharing is allowed only for approved operational facts and SOPs; task-specific run traces remain scoped to the run/session unless promoted by policy after evaluation.
- Retention expectations:
  - L1 turns: retained long enough for run debugging, then compacted or linked to episodes.
  - L2 facts: retained when verified and not benchmark-answer-bearing.
  - L3 episodes: retained for benchmark reproducibility and longitudinal analysis.
  - L4 knowledge documents: retained for stable, non-copyrighted derived knowledge and public documentation.

## 8. Provenance, Evidence, And CIAR Requirements

Responses should include provenance metadata whenever memory is returned:

- source tier;
- source id;
- timestamp;
- producing agent, script, service, or reviewer;
- original artifact reference when safe to expose;
- visibility scope;
- task id, session id, and run id when applicable.

CIAR responses should include certainty, impact, age decay, recency boost, final score, policy version, promotion/suppression status, and rationale. Review-only evidence may be returned to maintainers, but runtime agents should receive only evidence within their visibility scope. Suppressed or superseded evidence should be available for audit to maintainers and excluded from runtime context unless explicitly requested in a safe, read-only review workflow.

Example Evidence Table:

| Claim | Source tier | Source id | Supports? | Visibility | Notes |
|---|---|---|---:|---|---|
| Task uses DBR capacity calculation | CTT | `ctt_master:<uuid>` | Yes | Maintainer / public summary | Shows source CTT intent and constraints. |
| Port capacity value is used in prompt | Domain data | `domain_ports:<uuid>` | Yes | Public if no hidden answer | Links task to port entity attributes. |
| Candidate was accepted into Gold | Curation | `curation:<id>` | Yes | Maintainer-only | Must not be exposed to evaluated agents. |
| Judge score supports correctness | Episode / judge | `episode:<id>` | Yes | Maintainer-only | May include hidden answer comparison. |

## 9. Security And Permission Requirements

- Runtime benchmark agents receive read-only MCP access by default.
- Runtime benchmark agents must not trigger fact extraction, promotion, consolidation, distillation, contradiction lifecycle changes, or curation writes.
- Write tools require explicit allowlisting by caller role and service identity.
- Lifecycle operations are maintainer-only or approved ingestion-service-only.
- YAAM must fail closed if caller role, task id, session id, or visibility scope is missing.
- Data classes that must never be exposed to runtime MCP resources:
  - Gold answers and reasoning;
  - judge prompts, judge reasoning, and internal scoring notes;
  - curation approvals/rejections and defect notes;
  - copyrighted source text or verbatim textbook/manual excerpts;
  - secrets, API keys, `.env` values, and database URLs;
  - YAAM policy internals beyond approved read-only explanations.

## 10. Observability Requirements

- SCM-Cert-Bench should propagate W3C `traceparent` headers when available.
- YAAM should store or return a correlation id for Phoenix traces, OpenRouter calls, local JSONL artifact refs, run ids, and task ids.
- Phoenix-visible spans or linked metadata should cover:
  - Triad generation prompt assembly;
  - OpenRouter generation call;
  - Pydantic validation failure or success;
  - post-run episode ingestion;
  - LLM-as-judge evaluation ingestion;
  - MCP memory retrieval calls during benchmark execution.
- Required tool-call audit fields:
  - caller role;
  - agent id;
  - task id;
  - session id or run id;
  - tool/resource name;
  - input hash or redacted payload reference;
  - returned memory ids;
  - denied operations and denial reasons.
- Metrics should include request count, latency, timeout count, permission denial count, leakage-guard failure count, partial-result count, and downstream dependency failures.

## 11. Reliability And Error Handling

- Retrieval failures should be fail-closed when leakage guards cannot be applied.
- Retrieval may return partial results only when each returned item has passed visibility filtering.
- Post-run ingestion should be retryable and idempotent by `task_id`, `run_id`, and `model_id`.
- Runtime context retrieval timeout budget should be short enough to avoid distorting benchmark runs; if YAAM times out, the harness should continue with no YAAM context and record the failure.
- LLM-backed extraction, CIAR explanation, or contradiction review should fail fast when the LLM provider is unavailable unless the workflow explicitly allows cached results.
- Error responses should include `error_code`, `message`, `retryable`, `correlation_id`, and `safe_to_continue`.

Expected error shape:

```json
{
  "error_code": "LEAKAGE_GUARD_UNVERIFIED",
  "message": "YAAM could not verify that hidden benchmark fields were excluded.",
  "retryable": false,
  "correlation_id": "audit-123",
  "safe_to_continue": true
}
```

## 12. Performance Expectations

| Workflow | Expected QPS | p50 latency | p95 latency | Timeout budget | Notes |
|---|---:|---:|---:|---:|---|
| Runtime context retrieval | 1-5 | <= 300 ms | <= 1000 ms | 2 s | Should not materially slow benchmark execution. |
| Evidence table retrieval | < 1 | <= 1 s | <= 5 s | 10 s | Maintainer/reviewer workflow; partial results acceptable. |
| Post-run episode ingestion | Batch | <= 500 ms per record | <= 2 s per record | 30 s per batch chunk | Should be idempotent and retryable. |
| CIAR explanation | < 1 | <= 2 s | <= 10 s | 15 s | Maintainer-only debug workflow. |
| Contradiction review | < 1 | <= 3 s | <= 15 s | 20 s | May use agentic/LLM-backed behavior. |
| Permission check | 1-10 | <= 50 ms | <= 200 ms | 500 ms | Should be deterministic and fail closed. |

## 13. Acceptance Tests

| Test | Interface | Setup | Expected result |
|---|---|---|---|
| Hidden-answer leakage guard | MCP `yaam.memory.get_context` | Request context for a known Gold `task_id` as runtime agent. | Response contains no `ground_truth_answer`, no `ground_truth_reasoning`, no judge notes, and `leakage_guard_passed=true`. |
| Unauthorized write denial | MCP `yaam.l2.store_fact` | Runtime agent attempts to store a fact during benchmark execution. | YAAM denies the write with non-retryable permission error and audit id. |
| Post-run episode ingestion | REST v2 or MCP write | Submit a completed IAIMS-style debug ledger record with `task_id`, `model_id`, final artifact, and judged metrics. | YAAM returns stable `episode_id` and idempotently handles duplicate ingestion. |
| Evidence table provenance | MCP `yaam.evidence.table` | Maintainer requests evidence for a Gold task. | Response includes source tier, source id, timestamp, producer, visibility scope, and artifact references. |
| CIAR audit explanation | MCP `yaam.ciar.explain` | Maintainer requests explanation for conflicting port facts. | Response includes CIAR components, final score, rationale, policy version, and supporting/suppressed evidence ids. |
| Contradiction review | MCP `yaam.contradiction.review` | Submit mutually inconsistent port availability claims. | Response returns both supporting and conflicting evidence and a safe-refusal/infeasibility recommendation. |
| Phoenix trace correlation | REST metadata write + MCP read | Store a generation failure with `trace_id` and candidate task id. | Later lookup returns YAAM correlation id, Phoenix trace id, task id, source triad ids, and error summary. |
| Curation scope isolation | MCP resource `yaam://tasks/{task_id}/curation` | Runtime agent and maintainer both request same curation resource. | Runtime agent is denied; maintainer receives curation records. |

## 14. Open Questions

- Should YAAM define a first-class `benchmark_task` scope, or should SCM-Cert-Bench encode task scope through generic `task_id` metadata?
- Should curation decisions live in L3 episodes, L4 knowledge documents, or a dedicated curation record type?
- Should contradiction review be exposed as a deterministic Unified YAAM operation first, with Agentic YAAM summaries optional?
- What exact role names should YAAM standardize for `benchmark_runtime_agent`, `benchmark_maintainer`, and `post_run_ingestion_service`?
- Should YAAM store raw debug ledger messages, redacted message hashes, or both?
- How should YAAM represent local artifact references for files that will not exist outside the SCM-Cert-Bench workspace?
- Should SCM-Cert-Bench runtime memory retrieval be disabled by default for official publication runs and enabled only for MAS memory experiments?
