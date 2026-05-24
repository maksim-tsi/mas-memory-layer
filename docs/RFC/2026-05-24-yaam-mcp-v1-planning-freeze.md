# RFC: YAAM MCP v1 Planning Freeze

**Status:** Proposed planning freeze
**Date:** 2026-05-24
**Scope:** MCP v1 surface, shared service boundaries, permission policy, error contract, tracing, and requirement traceability
**Related:** [YAAM Requirements Registry](../requirements/yaam-requirements-registry.md), [Customer Requirements Analysis](../requirements/2026-05-24-customer-requirements-analysis.md), [YAAM Interface Evolution Toward MCP - Initial Findings](2026-05-24-yaam-interface-evolution-to-mcp-initial-findings.md), [YAAM MCP Interface and Memory Policy Evolution](2026-05-18-yaam-mcp-and-memory-policy-evolution.md), [RFC-014 Semantic Gateway API v2](RFC014%20-%20YAAM%20Semantic%20Gateway%20API%20(v2).md), [ADR-009](../ADR/009-decoupling-benchmark-api-wall.md), [ADR-013](../ADR/013-phoenix-tracing-strategy.md)

## 1. Summary

MCP v1 will be a generic, service-backed, read-heavy agent-host interface for
YAAM memory inspection, retrieval, context assembly, health inspection, bounded
evidence generation, CIAR explanation, and explicitly allowlisted writes.

MCP v1 will not replace the API Wall or REST Semantic Gateway v2. The API Wall
remains the OpenAI-compatible benchmark and chat boundary. REST v2 remains the
service-to-service and batch integration boundary under the current
`/v2/memory/...` route family. MCP v1 is a separate adapter over shared YAAM
service functions.

The first release must avoid customer-specific product expansion. Skill
Factory-specific resources, Maritime Port Sandbox-specific resources, and
artifact lineage resources are deferred unless MCP v1 is later retargeted to a
specific customer system.

## 2. Requirement Coverage

MCP v1 covers the following accepted P0 and P1 requirements:

| Requirement IDs | Coverage |
|---|---|
| `YAAM-REQ-0001`, `YAAM-REQ-0004` | Preserve API Wall, REST v2, and MCP as distinct public interfaces. |
| `YAAM-REQ-0002`, `YAAM-REQ-0003` | Provide MCP memory query and context assembly. |
| `YAAM-REQ-0005`, `YAAM-REQ-0006`, `YAAM-REQ-0007`, `YAAM-REQ-0008` | Expose scoped L2, L3, and L4 operations through shared service semantics. |
| `YAAM-REQ-0009`, `YAAM-REQ-0010` | Return provenance and enforce scope boundaries. |
| `YAAM-REQ-0011`, `YAAM-REQ-0012`, `YAAM-REQ-0013` | Keep resources read-only, allowlist mutating tools, and redact sensitive data. |
| `YAAM-REQ-0014`, `YAAM-REQ-0015` | Propagate trace context and provide health/config inspection. |
| `YAAM-REQ-0016`, `YAAM-REQ-0017`, `YAAM-REQ-0018` | Provide bounded Evidence Table and CIAR explanation with partial-result behavior. |
| `YAAM-REQ-0026`, `YAAM-REQ-0027` | Keep LangChain tools and direct library calls out of customer-facing contracts. |
| `YAAM-REQ-0031`, `YAAM-REQ-0033`, `YAAM-REQ-0034`, `YAAM-REQ-0035` | Provide common prompts, fail-fast writes, performance observability, and requirement traceability. |

The following requirements are deferred from generic MCP v1:

| Requirement IDs | Deferral reason |
|---|---|
| `YAAM-REQ-0019`, `YAAM-REQ-0020`, `YAAM-REQ-0028` | Artifact lineage requires a separate product decision and may become a customer-specific or v1.1 module. |
| `YAAM-REQ-0022`, `YAAM-REQ-0023`, `YAAM-REQ-0032` | Skill Factory views and domain-specific prompts should follow the generic MCP surface. |
| `YAAM-REQ-0024`, `YAAM-REQ-0025` | Maritime run, scenario, port, and fact views should follow the generic MCP surface. |
| `YAAM-REQ-0029`, `YAAM-REQ-0030` | Contradiction review and autonomous lifecycle operations remain opt-in future capabilities. |

## 3. MCP v1 Scope Envelope

All MCP tools and resource handlers must map caller context into a common scope
envelope before invoking YAAM services.

Required fields:

- `session_id`: logical session or conversation scope.
- `agent_id`: producing or requesting agent identity for tool calls.

Conditionally required fields:

- `task_id`: required for task-scoped L2 writes, Evidence Table generation, and
  L4 finalization.
- `tenant_id`: required when multi-tenant deployment is configured.
- `run_id`: required when the caller identifies an experiment, batch, or
  simulation run.

Optional fields:

- `user_id`: stable human or system user identity when available.
- `domain_ids`: customer or domain identifiers such as `ctt_id`, `skill_name`,
  `scenario_id`, `port_code`, `artifact_id`, or `knowledge_id`.
- `metadata`: JSON-serializable caller metadata, excluding secrets and raw
  environment values.
- `traceparent`: W3C trace context when the host can provide it.

Default visibility rules:

- L2 data is private to `session_id` plus `task_id` unless explicitly queried
  with broader permissions.
- L3 and L4 data may support cross-session retrieval only through explicit
  filters and policy-controlled query semantics.
- Suppressed, superseded, review-only, audit-only, or raw-trace data is hidden
  unless the caller has audit permission and the request explicitly asks for it.

## 4. Service-Layer Responsibilities

MCP v1 must be implemented as an adapter over shared service functions. MCP
tools must not call `src/storage/` adapters directly, and MCP tools must not use
LangChain tools as the service layer.

The service boundary is frozen as follows:

| Service | Responsibility |
|---|---|
| `MemoryTierService` | Raw L1, L2, L3, and L4 operations, including scoped writes, reads, and health checks. |
| `UnifiedRetrievalService` | Cross-tier query and bounded context assembly across L2, L3, and L4. |
| `CIARPolicyService` | CIAR score explanation, component serialization, policy version reporting, and review/suppression metadata. |
| `EvidenceService` | Evidence Table construction, deterministic evidence row assembly, evidence ranking metadata, and partial-result reporting. |
| `LifecycleService` | Promotion, consolidation, and distillation orchestration when explicitly enabled; disabled by default for MCP v1. |
| `ArtifactService` | Existing artifact lineage operations; deferred from generic MCP v1 unless explicitly retargeted. |

REST v2 routes, LangChain tools, future MCP tools, tests, and benchmark harnesses
should converge on these services to avoid interface-specific behavior drift.

## 5. MCP v1 Surface

### 5.1 Tools

| Tool | Mode | Default availability | Notes |
|---|---|---|---|
| `yaam.memory.query` | Read | Enabled | Unified query over scoped L2/L3/L4 memory. |
| `yaam.memory.get_context` | Read | Enabled | Bounded context block with source ids, provenance, token/size metadata, and warnings. |
| `yaam.l2.store_fact` | Write | Allowlisted | Runtime-owned or explicitly authorized fact write. |
| `yaam.l2.search_facts` | Read | Enabled | Scoped L2 fact search. |
| `yaam.l3.search_episodes` | Read | Enabled | Scoped semantic episode search. |
| `yaam.l3.assimilate_episode` | Write/lifecycle | Allowlisted | Controlled episode assimilation; no arbitrary graph query from clients. |
| `yaam.l4.search_knowledge` | Read | Enabled | Scoped or policy-controlled L4 search. |
| `yaam.l4.finalize_artifact` | Write/lifecycle | Allowlisted | Explicit final artifact/document persistence. |
| `yaam.ciar.explain` | Read | Enabled | CIAR component and policy explanation for memory ids or evidence items. |
| `yaam.evidence.table` | Read/agentic | Enabled for read-only assembly | May return partial deterministic rows if agentic scoring is unavailable. |
| `yaam.health.check` | Read | Enabled | Tier and service status without secrets. |

Each tool must expose JSON Schema input and output definitions. MCP responses
must include structured content and a compact text summary for clients that
display only textual tool results.

### 5.2 Resources

Resources are read-only in MCP v1.

| Resource | Purpose |
|---|---|
| `yaam://sessions/{session_id}/context` | Read assembled context for a session. |
| `yaam://sessions/{session_id}/facts` | Read scoped L2 facts. |
| `yaam://facts/{fact_id}` | Resolve fact metadata and provenance. |
| `yaam://episodes/{episode_id}` | Resolve episode metadata and provenance. |
| `yaam://knowledge/{knowledge_id}` | Resolve knowledge document metadata and provenance. |
| `yaam://health` | Read service and tier health status. |
| `yaam://config/ciar` | Read CIAR policy configuration without secrets. |
| `yaam://schemas/fact` | Read public fact schema. |
| `yaam://schemas/episode` | Read public episode schema. |
| `yaam://schemas/knowledge-document` | Read public knowledge-document schema. |

Customer-specific resources such as `yaam://skills/{skill_name}`,
`yaam://ctts/{ctt_id}`, `yaam://runs/{run_id}/scenarios/{scenario_id}`,
`yaam://ports/{port_code}/facts`, and `yaam://artifacts/{artifact_id}/lineage`
are follow-on surfaces.

### 5.3 Prompts

| Prompt | Purpose |
|---|---|
| `yaam.prompt.evidence_table` | Produce a consistent audit-oriented evidence table from scoped memory. |
| `yaam.prompt.memory_inspection` | Summarize memory contents for debugging and review without mutation. |
| `yaam.prompt.ciar_explanation` | Explain memory selection, suppression, or retention metadata. |
| `yaam.prompt.retrieval_strategy` | Guide users or agents in selecting tiers, filters, and visibility flags. |

Prompts must encode reusable inspection workflows, not hidden autonomous
behavior. Domain-specific prompts are deferred from generic MCP v1.

## 6. Permission Model

MCP v1 uses server-side authorization independent of client capability claims.

Default policy:

- Read tools and read-only resources are enabled when the caller has matching
  scope visibility.
- Mutating tools are disabled unless explicitly allowlisted for the caller,
  deployment, or service identity.
- Lifecycle and autonomous tools are disabled unless explicitly allowlisted and
  audited.
- Resources must never mutate memory state.
- Arbitrary SQL, arbitrary Cypher, raw vector-store controls, direct database
  handles, environment variables, provider credentials, `.env` contents, raw
  Phoenix credentials, raw LLM reasoning traces, and unredacted logs must not be
  exposed through MCP.

Write policy:

- Writes must include the applicable scope envelope and provenance.
- Writes must fail explicitly when required persistence, validation, embedding,
  or translation fails.
- Writes must be idempotent where caller-provided `request_id`, payload hash,
  or stable scope identifiers are available.
- A write response must not claim persistence unless the target service confirms
  it.

## 7. Error And Partial-Result Contract

Read operations may degrade when a tier or agentic capability is unavailable.
Write and lifecycle operations must fail explicitly.

Standard error shape:

```json
{
  "error": {
    "code": "YAAM_BACKEND_UNAVAILABLE",
    "message": "L3 vector backend unavailable.",
    "retryable": true,
    "partial": true,
    "operation": "yaam.memory.query",
    "affected_tier": "L3",
    "trace_id": "0af7651916cd43dd8448eb211c80319c",
    "audit_id": "audit-123",
    "details": {}
  }
}
```

Read responses that degrade without failing must include:

- `partial=true`;
- `warnings[]`;
- omitted or failed tier names;
- retryability where known;
- returned source ids and provenance for all available data.

Write failures must include:

- stable error code;
- non-ambiguous retryability;
- affected service or tier;
- validation details for malformed inputs;
- trace or audit correlation id when available.

## 8. Tracing And Observability

MCP v1 must be Phoenix-auditable and aligned with the existing OpenInference
tracing direction.

Requirements:

- Accept and propagate inbound W3C `traceparent` when the MCP host provides it.
- Emit one auditable span or event for every MCP tool/resource/prompt request.
- Propagate trace context into downstream YAAM service calls.
- Record operation name, interface `MCP`, read/write/lifecycle classification,
  scope ids, caller identity when available, status, latency, result count,
  partial-result flag, warning count, error code, and returned source ids.
- Use `openinference.span.kind` where applicable and namespace YAAM-specific
  attributes as `yaam.*`.
- Respect content-capture policy: full, redacted, or metadata-only.
- Never record or return secrets, raw environment values, or unredacted sensitive
  traces through resource or prompt surfaces.

Metrics for MCP v1 should include p50/p95 latency, error count by operation,
permission-denied count, partial-result count, timeout count, write
acknowledgement rate, and empty-retrieval rate.

## 9. Acceptance Tests

MCP v1 implementation is acceptable when the following tests or demonstrations
pass:

1. MCP discovery exposes the v1 tools, resources, and prompts with JSON schemas
   and read/write/lifecycle classification.
2. `yaam.memory.query` and `yaam.memory.get_context` return scoped structured
   results with source ids, provenance, warnings, and partial-result metadata.
3. Resources are read-only and cannot mutate memory state.
4. Mutating tools are unavailable to unallowlisted callers and available only to
   explicitly allowlisted identities.
5. Session/task/tenant isolation prevents cross-scope reads except through
   explicit allowed query semantics.
6. Resource and prompt responses redact secrets, raw environment values, raw LLM
   reasoning traces, and unredacted logs.
7. Read degradation returns `partial=true` and warnings; write failures fail
   explicitly without claiming persistence.
8. Inbound `traceparent` links MCP spans to downstream YAAM service spans in
   Phoenix or equivalent trace inspection.
9. REST v2 and LangChain tool behavior remain compatible while sharing the same
   service-layer semantics as MCP.
10. Implementation plans and PR summaries cite the covered `YAAM-REQ-*` IDs.

## 10. Non-Goals

MCP v1 does not include:

- replacing the API Wall;
- replacing REST v2;
- direct customer library access to YAAM internals;
- exposing LangChain tools as customer contracts;
- changing `src/storage/` adapter contracts;
- adding an MCP SDK dependency without explicit approval;
- shipping Skill Factory-specific, Maritime-specific, or artifact lineage
  resources as part of the generic first release;
- enabling autonomous contradiction review, consolidation, or distillation by
  default.

## 11. Open Decisions Before Implementation

The following decisions remain necessary before code implementation:

1. Choose the first MCP transport: stdio, streamable HTTP, or both.
2. Select the MCP SDK or implementation strategy and obtain explicit dependency
   approval if a dependency change is required.
3. Define the concrete server-side allowlist configuration format.
4. Define the exact Pydantic models for the scope envelope, tool inputs,
   structured outputs, warnings, provenance, and errors.
5. Decide whether Evidence Table v1 is deterministic-only or may optionally use
   LLM-assisted ranking when separately enabled.
