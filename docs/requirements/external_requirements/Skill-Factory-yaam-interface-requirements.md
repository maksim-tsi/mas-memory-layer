# Skill Factory YAAM Interface Requirements

**System:** Skill Factory  
**Owner:** SCM Skill Factory maintainers / TBD  
**Date:** 2026-05-24  
**Status:** Draft  
**Primary contact:** TBD  

## 1. System Overview

SCM Skill Factory is a Python 3.13+ autonomous skill-generation and skill-curation system for the SCM-Cert-Bench ecosystem. It reads supply chain concept/theory/tool records from the Medallion PostgreSQL `ctt_master` table, asks an LLM to generate strict Pydantic V2 Python skills, validates those skills in an isolated subprocess sandbox, writes accepted code to `skills/generated/`, and stores validated schema metadata in `skill_registry`.

The current generation path is a pure Python `while` / `try-except` orchestrator rather than a LangChain or LangGraph agent. The repository also contains a planned SCM agent state model for downstream multi-step tool execution, active-tool curation logic, mass QA reports, and architecture decisions for APICS field normalization and Phoenix/OpenTelemetry trace enrichment.

Skill Factory is a customer of YAAM because it needs durable cross-run memory for generation episodes, sandbox failure patterns, validated schemas, QA outcomes, active-tool promotion decisions, routing metadata, and audit evidence. The generated skills are intended to be MCP-compatible and consumed by downstream YAAM-based multi-agent systems.

## 2. Integration Goals

- Retrieve relevant cross-session memory before generating or repairing a skill.
  - **Justification:** The orchestrator currently uses only the current CTT plus immediate repair context. YAAM can reduce repeated failures by retrieving prior sandbox failures, accepted schema patterns, APICS naming precedents, and successful repair tactics for similar CTTs.
- Store verified generation episodes after each attempt.
  - **Justification:** Skill generation creates useful operational memory: source CTT, LLM output metadata, sandbox status, error source, retry count, code hash, dependencies, and extracted schemas. This memory should survive across batches and agent sessions.
- Store and retrieve QA and curation outcomes.
  - **Justification:** `scripts/mass_evaluate.py`, `docs/reports/mass_evaluation.json`, and `skills/active/` represent second-stage quality and routing decisions. YAAM should preserve why a skill was accepted, revised, promoted, or excluded.
- Assemble evidence for debugging and audit.
  - **Justification:** Phoenix spans hold generation and reasoning traces, while `SkillRegistry` stores deterministic metadata. YAAM should connect these sources into explainable Evidence Tables without requiring humans to manually cross-reference files, DB rows, and trace UIs.
- Expose memory resources to MCP-capable agent hosts.
  - **Justification:** Skill Factory produces MCP-compatible tools for downstream MAS use. MCP memory tools/resources are the most natural interface for generation agents, curation agents, and future SCM orchestration agents.

## 3. Expected Interface

| Interface | Required? | Purpose | Notes |
|---|---:|---|---|
| API Wall `/v1/chat/completions` | No | Not used directly by Skill Factory for YAAM memory. | The current LLM provider path is OpenRouter through the OpenAI client; memory should not be hidden behind a chat-completion proxy for this system. |
| REST v2 `/v2/memory/...` | Yes | Batch ingestion, administrative reads, report import/export, and non-agent integration from scripts. | Useful for `scripts/run_orchestrator.py`, mass QA ingestion, and backfills from reports or DB snapshots. |
| MCP tools/resources/prompts | Yes | Primary agent-facing memory interface for generation, repair, curation, and audit agents. | Must expose discoverable read-only tools and allowlisted write tools. |
| LangChain tools | No | Not required. | Generated skills and current orchestration intentionally avoid LangChain. |
| Direct library calls | No | Internal YAAM implementation only. | Skill Factory should integrate through stable service interfaces, not private YAAM internals. |

## 4. Required Capabilities

| Capability | Tier | Read/Write/Lifecycle | Required for MVP? | Example input | Expected output |
|---|---|---|---:|---|---|
| Query similar generation history | Unified | Read | Yes | `{"tenant_id":"scm-cert-bench","ctt_id":"017c...","domain_tag":"Inventory","intent":"Calculate EOQ","top_k":5}` | Ranked memories with source ids, tiers, similarity rationale, status, and evidence snippets. |
| Assemble pre-generation context | Unified | Read | Yes | `{"session_id":"sf-run-20260524-001","task_id":"generate-ctt-017c","ctt_id":"017c...","include":["schemas","failures","apics_terms","repair_patterns"]}` | Compact context bundle suitable for prompt construction, with provenance and token/size metadata. |
| Store generation attempt episode | Raw | Write | Yes | `{"run_id":"sf-run-20260524-001","ctt_id":"017c...","attempt":1,"status":"sandbox_failed","error_source":"runtime"}` | Stored episode id, timestamps, scope ids, and audit metadata. |
| Store validated skill fact | Raw | Write | Yes | `{"skill_name":"ctt_017c...","status":"VALIDATED","code_hash":"sha256:...","input_schema_json":{},"output_schema_json":{}}` | Fact ids for skill metadata, schemas, dependencies, and registry status. |
| Retrieve skill registry memory | Raw | Read | Yes | `{"skill_name":"ctt_017c...","include_code":false}` | Skill facts including path, code hash, dependencies, schemas, status, retry count, and provenance. |
| Explain CIAR scoring for retrieved memory | Agentic | Read | Yes | `{"memory_ids":["fact_123","episode_456"],"query":"Why use this repair pattern?"}` | CIAR component scores, final score, explanation, and evidence references. |
| Generate Evidence Table for audit | Agentic | Read | Yes | `{"skill_name":"ctt_017c...","include_superseded":true,"include_traces":true}` | Table rows linking claims to CTT source, skill registry row, QA record, sandbox result, and Phoenix trace ids. |
| Review contradictions or superseded facts | Agentic | Lifecycle | No | `{"skill_name":"ctt_017c...","new_status":"VALIDATED","prior_statuses":["FAILED"]}` | Review result identifying whether facts should be superseded, suppressed, or retained for audit. |
| Consolidate repeated failure patterns | Agentic | Lifecycle | No | `{"domain_tag":"Forecasting_Demand","error_source":"schema_extraction","window":"30d"}` | Distilled repair guidance and candidate policy memories with supporting episodes. |
| Store QA and active-tool curation decisions | Raw | Write | Yes | `{"skill_name":"ctt_017c...","qa_status":"ACCEPTED","active_tool":true,"promotion_reason":"Top-35 Strategy B"}` | Stored QA facts and curation decision ids with source report/file provenance. |

## 5. Use Case Scenarios

### Scenario 1: Pre-Generation Context Hydration

**Trigger:** The orchestrator fetches a pending `CttMaster` record before calling `generate_skill_code()`.  
**Caller:** Skill generation agent or `src/orchestrator.py`.  
**YAAM interface:** MCP tool `yaam.memory.get_context` or REST v2 equivalent.  
**Input example:**

```json
{
  "tenant_id": "scm-cert-bench",
  "session_id": "sf-run-20260524-001",
  "agent_id": "skill-generator",
  "task_id": "generate-ctt-017c",
  "ctt_id": "017c9b3e476d451fb32546f276e3134a",
  "skill_name": "ctt_017c9b3e476d451fb32546f276e3134a",
  "query": "Generate a strict Pydantic V2 SCM skill for an Inventory CTT",
  "include": ["similar_schemas", "sandbox_failures", "repair_patterns", "apics_terms"],
  "top_k": 5
}
```

**Expected YAAM behavior:** Retrieve cross-session memories for similar CTTs and return a compact, provenance-rich context bundle without mutating memory.  
**Expected response shape:** `context_items[]` with `memory_id`, `tier`, `summary`, `evidence`, `ciar_score`, `source_id`, `created_at`, and `producing_agent`.  
**Failure handling:** If YAAM is unavailable or times out, Skill Factory continues with the current CTT-only prompt and records `memory_context_status="unavailable"` in telemetry. Partial results are acceptable.  
**Trace/audit expectations:** The YAAM call must join the active W3C `traceparent`; returned memory ids must be recorded on the parent generation span.

**Requirement justification:** This scenario covers unified read context. It helps prevent repeated schema, APICS, and sandbox errors by making prior validated and failed attempts available before a new LLM call.

### Scenario 2: Sandbox Failure Memory

**Trigger:** `execute_in_sandbox()` returns `is_valid=false`.  
**Caller:** Skill generation agent or `src/orchestrator.py`.  
**YAAM interface:** MCP tool `yaam.memory.store_episode` or REST v2 write endpoint.  
**Input example:**

```json
{
  "tenant_id": "scm-cert-bench",
  "session_id": "sf-run-20260524-001",
  "agent_id": "skill-generator",
  "task_id": "generate-ctt-017c",
  "run_id": "sf-run-20260524-001",
  "ctt_id": "017c9b3e476d451fb32546f276e3134a",
  "skill_name": "ctt_017c9b3e476d451fb32546f276e3134a",
  "attempt": 1,
  "status": "FAILED",
  "error_source": "runtime",
  "error_message": "InputSchema must inherit from pydantic.BaseModel",
  "sandbox_timeout_s": 5,
  "retry_count": 0,
  "phoenix_trace_id": "trace-abc123"
}
```

**Expected YAAM behavior:** Store a raw L3 episode plus extracted L2 facts for error source, failing schema contract, retry state, and repairable pattern.  
**Expected response shape:** `episode_id`, `fact_ids[]`, `write_status`, `scope`, and `audit_record_id`.  
**Failure handling:** Write failures should not block the local retry loop, but the caller should emit a span event and retry YAAM writes at most once for transient errors.  
**Trace/audit expectations:** Store the Phoenix trace id, current span id, attempt number, and redacted error message. Raw generated source must not be stored unless the caller has audit write permission.

**Requirement justification:** This scenario covers write-enabled failure memory. The same runtime and schema failures recur across generated skills, so durable failure episodes are valuable repair context for future batches.

### Scenario 3: Validated Skill Registration

**Trigger:** Sandbox validation succeeds and `save_validated_skill()` writes a `SkillRegistry` row.  
**Caller:** Skill generation agent or `src/orchestrator.py`.  
**YAAM interface:** MCP tool `yaam.l2.store_fact` plus `yaam.memory.store_episode`, or REST v2 batch write.  
**Input example:**

```json
{
  "tenant_id": "scm-cert-bench",
  "session_id": "sf-run-20260524-001",
  "agent_id": "skill-generator",
  "task_id": "generate-ctt-017c",
  "ctt_id": "017c9b3e476d451fb32546f276e3134a",
  "skill_name": "ctt_017c9b3e476d451fb32546f276e3134a",
  "file_path": "skills/generated/ctt_017c9b3e476d451fb32546f276e3134a.py",
  "status": "VALIDATED",
  "code_hash": "sha256:example",
  "dependencies": ["pydantic"],
  "input_schema_json": {"title": "Input"},
  "output_schema_json": {"title": "Output"},
  "retry_count": 1
}
```

**Expected YAAM behavior:** Store validated skill metadata as durable facts and connect them to the generation episode, source CTT, and trace.  
**Expected response shape:** Stored fact ids for skill identity, schema metadata, dependency metadata, and validation state.  
**Failure handling:** If YAAM write fails after local DB persistence succeeds, return a retryable error and allow later reconciliation from `SkillRegistry`.  
**Trace/audit expectations:** Capture code hash and schema hashes, not raw source by default. Link to Phoenix trace id and `SkillRegistry.skill_name`.

**Requirement justification:** This scenario covers raw read/write skill metadata. Downstream DAG construction and MCP tool routing need schemas, dependencies, and validation status without importing generated code.

### Scenario 4: Mass QA And Active-Tool Curation

**Trigger:** A curation agent evaluates generated skills or bootstraps `skills/active/`.  
**Caller:** Mass QA script, curation agent, or active-tool bootstrap workflow.  
**YAAM interface:** REST v2 batch query/write for scripts and MCP tools for curation agents.  
**Input example:**

```json
{
  "tenant_id": "scm-cert-bench",
  "session_id": "sf-curation-20260524-001",
  "agent_id": "skill-curator",
  "task_id": "promote-top-35",
  "query": "Find accepted Inventory and Production_Planning skills with strong routing context",
  "filters": {
    "qa_status": "ACCEPTED",
    "min_interfaces_score": 9,
    "min_logic_score": 9,
    "min_context_score": 9
  }
}
```

**Expected YAAM behavior:** Return QA facts and evidence supporting promotion decisions, then store any selected active-tool decisions as new curation facts.  
**Expected response shape:** Ranked candidate skills with QA scores, routing context, source report provenance, and curation write ids.  
**Failure handling:** Read failures block automated promotion; write failures should leave local files untouched or mark the curation run as incomplete.  
**Trace/audit expectations:** Record source report path, evaluator model if available, curation criteria, selected skill names, and active-tool registry output path.

**Requirement justification:** This scenario covers QA and curation memory. Skill Factory needs YAAM to preserve not just generated code facts, but also why a subset was promoted for downstream MAS use.

### Scenario 5: Debug And Audit Investigation

**Trigger:** A researcher investigates a failed, suspicious, or superseded generated skill.  
**Caller:** Researcher-facing audit agent or maintenance script.  
**YAAM interface:** MCP tools `yaam.evidence.table`, `yaam.ciar.explain`, and read-only resources.  
**Input example:**

```json
{
  "tenant_id": "scm-cert-bench",
  "session_id": "sf-audit-20260524-001",
  "agent_id": "skill-auditor",
  "task_id": "audit-ctt-017c",
  "skill_name": "ctt_017c9b3e476d451fb32546f276e3134a",
  "include_superseded": true,
  "include_review_only": true,
  "include_trace_links": true
}
```

**Expected YAAM behavior:** Produce an Evidence Table linking source CTT, generation attempts, sandbox outcomes, SkillRegistry facts, QA outcomes, curation decisions, CIAR explanations, and trace ids.  
**Expected response shape:** `evidence_table.rows[]` with claim, source tier, source id, timestamp, producing agent, CIAR score, status, and audit visibility.  
**Failure handling:** If agentic evidence assembly fails, return raw facts and a clear `agentic_unavailable` warning.  
**Trace/audit expectations:** Every audit read should be recorded with caller identity, requested visibility level, and whether raw source or reasoning traces were exposed.

**Requirement justification:** This scenario covers agentic evidence and CIAR explanation. Debugging generated mathematical tools requires transparent provenance and controlled access to sensitive reasoning/source artifacts.

## 6. MCP Expectations

Complete this section because Skill Factory expects to use MCP as the primary agent-facing YAAM interface.

### 6.1 Tool Requirements

| Proposed tool | Required? | Read/Write/Lifecycle | Required input fields | Required output fields |
|---|---:|---|---|---|
| `yaam.memory.query` | Yes | Read | `tenant_id`, `query`, optional `session_id`, `agent_id`, `task_id`, `ctt_id`, `skill_name`, `filters`, `top_k` | `results[]`, `memory_id`, `tier`, `summary`, `score`, `source_id`, `provenance` |
| `yaam.memory.get_context` | Yes | Read | `tenant_id`, `session_id`, `task_id`, query or target ids, `include[]`, `top_k`, `max_tokens` | `context_items[]`, `context_summary`, `evidence[]`, `ciar_scores`, `omitted_items` |
| `yaam.memory.store_episode` | Yes | Write | `tenant_id`, `session_id`, `agent_id`, `task_id`, `run_id`, `event_type`, `payload`, `trace_id` | `episode_id`, `fact_ids[]`, `write_status`, `audit_record_id` |
| `yaam.l2.store_fact` | Yes | Write | `tenant_id`, `scope`, `fact_type`, `subject_id`, `payload`, `provenance` | `fact_id`, `version`, `write_status`, `superseded_fact_ids[]` |
| `yaam.ciar.explain` | Yes | Read | `tenant_id`, `memory_ids[]`, `query`, optional `include_components` | `explanations[]`, `certainty`, `impact`, `age_decay`, `recency_boost`, `final_score` |
| `yaam.evidence.table` | Yes | Read/Agentic | `tenant_id`, `skill_name` or `ctt_id`, `include_superseded`, `include_review_only`, `include_traces` | `rows[]`, `claims[]`, `source_refs[]`, `visibility`, `warnings[]` |
| `yaam.contradictions.review` | No | Lifecycle | `tenant_id`, `subject_id`, `new_fact_id`, `candidate_conflicts[]` | `decision`, `superseded_fact_ids[]`, `review_notes`, `audit_record_id` |
| `yaam.memory.consolidate` | No | Lifecycle | `tenant_id`, `scope`, `pattern_query`, `window`, `min_support` | `distillation_id`, `candidate_facts[]`, `supporting_episode_ids[]` |

### 6.2 Resource Requirements

| Proposed resource | Required? | Access scope | Notes |
|---|---:|---|---|
| `yaam://sessions/{session_id}/context` | Yes | Session | Read compact run context for orchestrator and curation sessions. |
| `yaam://sessions/{session_id}/facts` | Yes | Session | Inspect facts written during one generation or curation run. |
| `yaam://facts/{fact_id}` | Yes | Fact | Resolve evidence references returned by query and Evidence Table tools. |
| `yaam://skills/{skill_name}` | Yes | Skill | Skill Factory-specific view of schema, QA, curation, and provenance facts. |
| `yaam://ctts/{ctt_id}` | Yes | CTT | Source CTT memory and related generation history. |
| `yaam://health` | Yes | Service | Scripts should fail fast or degrade cleanly based on health. |
| `yaam://config/ciar` | Yes | Service | Read CIAR scoring policy used for retrieval and audit explanation. |
| `yaam://runs/{run_id}/episodes` | Yes | Run | Replay generation attempts and sandbox outcomes for a batch. |

### 6.3 Prompt Requirements

| Proposed prompt | Required? | Purpose | Expected variables |
|---|---:|---|---|
| `yaam.prompt.evidence_table` | Yes | Generate a structured audit table for a skill or CTT. | `skill_name`, `ctt_id`, `include_superseded`, `include_traces` |
| `yaam.prompt.memory_inspection` | Yes | Summarize relevant memory for generation or curation. | `query`, `scope`, `top_k`, `visibility` |
| `yaam.prompt.ciar_explanation` | Yes | Explain why memories were selected or suppressed. | `memory_ids`, `query`, `include_components` |
| `yaam.prompt.contradiction_review` | No | Review conflicting validation, QA, or curation facts. | `subject_id`, `candidate_facts`, `new_fact` |
| `yaam.prompt.repair_pattern_summary` | Yes | Distill recurring sandbox failures into generation guidance. | `error_source`, `domain_tag`, `ctt_id`, `supporting_episodes` |

## 7. Data And Scope Requirements

- Required identifiers for every call: `tenant_id`, `agent_id`, and either `session_id` or `run_id`.
- Required task identifiers for workflow calls: `task_id`, plus `ctt_id` for CTT generation workflows or `skill_name` for skill-specific workflows.
- Required Skill Factory entity identifiers: `ctt_id`, `skill_name`, `file_path`, `code_hash`, `status`, `retry_count`, and optional `qa_status`.
- Cross-agent sharing is allowed within the same `tenant_id` for validated schemas, APICS glossary patterns, accepted repair patterns, QA summaries, and active-tool curation decisions.
- Agent-private or restricted data includes raw generated Python source, raw prompts, raw LLM reasoning traces, secrets, environment variables, database URLs, and unredacted sandbox stderr.
- Task-scoped data should include individual attempt records, repair context, local retry decisions, and transient partial context bundles.
- Tenant-scoped data should include distilled repair policies, APICS schema norms, accepted curation criteria, and high-confidence skill registry facts.
- Retention expectations:
  - L1 turns/context bundles: short retention, sufficient for run replay and debug.
  - L2 facts: long retention for skill metadata, schema facts, QA status, and curation decisions.
  - L3 episodes: medium-to-long retention for generation attempts, sandbox failures, and audit trails.
  - L4 knowledge documents: long retention for distilled repair patterns, APICS policies, and curation criteria.

## 8. Provenance, Evidence, And CIAR Requirements

Responses should include source tier, source id, timestamp, producing agent, task id, run id, and tenant id for every returned fact or episode. Skill-specific responses should also include `ctt_id`, `skill_name`, `file_path`, `code_hash`, `status`, `retry_count`, and schema hash or schema id when available.

CIAR metadata is required for retrieval and audit responses. At minimum, responses should include certainty, impact, age decay, recency boost, final score, and a short explanation. Skill Factory needs these fields to understand why a prior repair pattern or QA decision was considered relevant to a new generation task.

Review-only evidence should be returned when explicitly requested by audit-capable callers. Suppressed or superseded evidence should be available for audit workflows so investigators can understand transitions such as `FAILED` to `VALIDATED`, `NEEDS_REVISION` to `ACCEPTED`, or active-tool inclusion/exclusion.

Example Evidence Table:

| Claim | Source tier | Source id | Evidence | CIAR score | Visibility |
|---|---|---|---|---:|---|
| Skill was validated after one retry | L3 episode | `episode_456` | Sandbox success for attempt 2 with `retry_count=1` | 0.94 | Standard |
| Skill schemas are DAG-ready | L2 fact | `fact_schema_123` | Input/output JSON schemas stored from sandbox extraction | 0.91 | Standard |
| Raw reasoning trace exists | L1 turn/trace | `trace_abc123` | Phoenix span has `llm.reasoning_trace` | 0.79 | Audit-only |
| Prior failure was superseded | L3 episode | `episode_455` | Attempt 1 failed at runtime before repair | 0.83 | Audit-only |

## 9. Security And Permission Requirements

- Default MCP resources and query tools must be read-only.
- Write tools may store generation attempts, validation facts, QA facts, curation decisions, and trace correlation metadata.
- Lifecycle tools for contradiction review and consolidation must require explicit allowlisting.
- Raw generated Python source must not be returned by default. Return `code_hash`, schema metadata, and file path unless the caller has audit/source-read permission.
- Raw prompts, raw LLM reasoning traces, secrets, environment variables, database URLs, and unredacted exception logs must never be exposed through standard MCP resources.
- Sandbox stderr should be redacted and truncated before storage unless stored under audit-only visibility.
- Mutating calls must require `tenant_id`, `agent_id`, `task_id`, and provenance fields.
- YAAM should preserve immutable audit records for writes and lifecycle changes, including caller identity, tool name, request id, trace id, and payload redaction status.

## 10. Observability Requirements

- Skill Factory should propagate W3C `traceparent` headers or equivalent trace context into every YAAM REST/MCP call.
- YAAM spans should be visible in the same Phoenix trace tree as generation, LLM, sandbox, persistence, QA, and curation spans whenever possible.
- Required YAAM span attributes: `tenant_id`, `session_id`, `agent_id`, `task_id`, `run_id`, `ctt_id`, `skill_name`, `yaam.tool_name`, `yaam.operation`, `yaam.tier`, `yaam.read_write_mode`, `yaam.result_count`, `yaam.partial_result`, and `yaam.error_code`.
- Tool-call audit fields must include request id, caller, interface, operation, scope ids, visibility level, payload hash, redaction status, latency, and outcome.
- Metrics should include p50/p95 latency by operation, timeout count, partial-result count, write failure count, retrieval result count, and agentic operation failure count.
- If YAAM returns partial results, the response and trace should identify omitted tiers, failed downstream components, and whether retry is recommended.

## 11. Reliability And Error Handling

- Read operations for context hydration should be retryable on transient network failures, 429s, and 5xx responses.
- Write operations should be idempotent where possible using caller-provided `request_id`, `run_id`, `task_id`, `ctt_id`, `skill_name`, and `attempt`.
- Generation should continue without YAAM read context if YAAM is unavailable, but should record degraded mode in local telemetry.
- Failed writes after local DB persistence should be retryable by reconciliation from `SkillRegistry`, report files, or run episodes.
- Retrieval should return partial results when some tiers are unavailable, with `partial=true`, warnings, and omitted tier names.
- Agentic operations should fail closed for mutation. If contradiction review or consolidation fails, YAAM must not change fact status.
- Expected error shape:

```json
{
  "error": {
    "code": "YAAM_TIMEOUT",
    "message": "Context retrieval exceeded timeout budget",
    "retryable": true,
    "partial": false,
    "request_id": "req_123",
    "trace_id": "trace_abc123",
    "details": {
      "operation": "yaam.memory.get_context",
      "timeout_ms": 1500
    }
  }
}
```

## 12. Performance Expectations

Provide expected scale and latency targets.

| Workflow | Expected QPS | p50 latency | p95 latency | Timeout budget | Notes |
|---|---:|---:|---:|---:|---|
| Pre-generation context hydration | 1-5 | <= 300 ms | <= 1500 ms | 2 s | Must be fast enough to run before every LLM generation attempt. |
| Store generation attempt episode | 1-10 | <= 200 ms | <= 1000 ms | 2 s | Should not block retry loop for long. |
| Store validated skill facts | 1-5 | <= 300 ms | <= 1500 ms | 3 s | Can be reconciled later from `SkillRegistry` if needed. |
| QA/curation batch read | 0.1-1 | <= 1000 ms | <= 5000 ms | 10 s | Batch/report workflows can tolerate slower responses. |
| Evidence Table audit | 0.1-1 | <= 2000 ms | <= 10000 ms | 15 s | Agentic assembly may be slower but must return warnings on partial results. |
| CIAR explanation | 0.5-2 | <= 500 ms | <= 2500 ms | 5 s | Used during debugging and prompt construction. |

## 13. Acceptance Tests

List the tests or demonstrations that would prove the integration works.

| Test | Interface | Setup | Expected result |
|---|---|---|---|
| Retrieve pre-generation context | MCP `yaam.memory.get_context` | Seed YAAM with one accepted Inventory skill, one prior sandbox failure, and one APICS repair pattern. | Response returns all three with provenance, CIAR scores, and a context summary under the timeout budget. |
| Store sandbox failure episode | MCP or REST write | Submit a failed attempt payload with `ctt_id`, `skill_name`, `attempt`, `error_source`, and trace id. | YAAM returns an episode id, extracted fact ids, audit id, and the episode is queryable by `ctt_id` and `skill_name`. |
| Store validated skill facts | MCP or REST write | Submit validated skill metadata with code hash, dependencies, schemas, retry count, and SkillRegistry path. | YAAM stores L2 facts and links them to the generation episode and source CTT. |
| Generate audit Evidence Table | MCP `yaam.evidence.table` | Seed YAAM with failed attempt, successful attempt, QA result, and active-tool decision for one skill. | Evidence Table includes current and superseded facts, CIAR metadata, trace links, and audit-only visibility labels. |
| Batch QA curation query | REST v2 | Seed QA facts for accepted and needs-revision skills across multiple domains. | Query returns ranked accepted candidates with QA scores, routing context, and report provenance. |
| Permission boundary check | MCP resources | Use a standard caller to request raw generated source or raw reasoning traces. | YAAM denies or redacts restricted fields while still returning non-sensitive metadata. |
| Partial-result behavior | MCP `yaam.memory.query` | Simulate unavailable agentic CIAR service while raw facts are available. | YAAM returns raw results with `partial=true`, warning details, and no mutation. |

## 14. Open Questions

- Should YAAM store raw generated Python source under audit-only visibility, or should Skill Factory store only code hashes and local file paths?
- What exact YAAM tool names will replace the proposed names in this document?
- Which component owns reconciliation when local SkillRegistry writes succeed but YAAM writes fail?
- Should QA report ingestion be pushed from Skill Factory scripts or pulled by YAAM from repository/report artifacts?
- What retention period is acceptable for raw LLM reasoning traces, given their audit value and sensitivity?
- Should CIAR scoring include domain-specific weights for supply chain skill generation, such as APICS conformity or sandbox pass rate?
- Should active-tool curation decisions be modeled as facts, episodes, or lifecycle status transitions on skill facts?
