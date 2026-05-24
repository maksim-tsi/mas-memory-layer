# Specification: MCP v1 Implementation Contract

**Status:** Draft
**Date:** 2026-05-24
**Related RFC:** [YAAM MCP v1 Planning Freeze](../RFC/2026-05-24-yaam-mcp-v1-planning-freeze.md)
**Requirement coverage:** `YAAM-REQ-0001`, `YAAM-REQ-0002`, `YAAM-REQ-0003`, `YAAM-REQ-0004`, `YAAM-REQ-0005`, `YAAM-REQ-0006`, `YAAM-REQ-0007`, `YAAM-REQ-0008`, `YAAM-REQ-0009`, `YAAM-REQ-0010`, `YAAM-REQ-0011`, `YAAM-REQ-0012`, `YAAM-REQ-0013`, `YAAM-REQ-0014`, `YAAM-REQ-0015`, `YAAM-REQ-0016`, `YAAM-REQ-0017`, `YAAM-REQ-0018`, `YAAM-REQ-0026`, `YAAM-REQ-0027`, `YAAM-REQ-0031`, `YAAM-REQ-0033`, `YAAM-REQ-0034`, `YAAM-REQ-0035`

## 1. Objective

MCP v1 provides a generic, stdio-first Model Context Protocol adapter for YAAM.
The adapter exposes tools, resources, and prompts to agent hosts while
preserving the existing API Wall and REST Semantic Gateway v2 boundaries.

MCP v1 is a service adapter. It must not call `src/storage/` directly, must not
expose LangChain tools as customer contracts, and must not replace
`/v2/memory/...` routes.

## 2. Transport And Dependency

MCP v1 uses the official Python MCP SDK with FastMCP and stdio transport first.
The dependency target is `mcp>=1.12.4,<1.27.1` for the current release. The
upper bound preserves compatibility with the repository's existing
`pydantic==2.8.2` pin; `mcp>=1.27.1` requires `pydantic>=2.11` and is deferred
until a separate Pydantic upgrade is approved and verified.

The runnable entrypoint must be:

```bash
./.venv/bin/python -m src.mcp.server --agent-type full --agent-variant baseline
```

The module must also support default configuration from the same environment
variables used by the API Wall and wrapper runtime. Streamable HTTP is not part
of MCP v1 implementation and remains a follow-on transport.

## 3. Scope Envelope

All MCP operations must normalize caller context into a `ScopeEnvelope` before
calling service code.

Required fields:

- `session_id`
- `agent_id`

Conditionally required fields:

- `task_id` for task-scoped L2 writes, Evidence Table generation, and L4
  finalization.
- `tenant_id` when multi-tenant mode is configured.
- `run_id` when the caller identifies a batch, experiment, or simulation run.

Optional fields:

- `user_id`
- `domain_ids`
- `metadata`
- `traceparent`

The envelope must be validated with Pydantic v2. Pydantic `ValidationError`
instances must be converted into the standard YAAM error shape rather than
retried blindly.

## 4. Service Boundary

MCP v1 requires a shared service layer under `src/memory/services/`.

| Service | Required behavior |
|---|---|
| `MemoryTierService` | Raw L2/L3/L4 read and allowlisted write operations plus tier health/config inspection. |
| `UnifiedRetrievalService` | Cross-tier memory query and bounded context assembly over existing `UnifiedMemorySystem` behavior. |
| `CIARPolicyService` | Deterministic CIAR component explanation and policy metadata serialization. |
| `EvidenceService` | Deterministic Evidence Table row assembly with partial-result reporting. |
| `LifecycleService` | Explicitly disabled default lifecycle entrypoint; future holder for promotion/consolidation/distillation. |
| `PermissionPolicy` | Server-side read/write/lifecycle allowlist decisions independent of MCP client claims. |

REST v2 routes and LangChain tools should be migrated to the service layer only
after service tests protect current behavior.

## 5. MCP Surface

### 5.1 Tools

MCP v1 must expose these tools:

| Tool | Mode | Availability |
|---|---|---|
| `yaam.memory.query` | Read | Enabled |
| `yaam.memory.get_context` | Read | Enabled |
| `yaam.l2.store_fact` | Write | Allowlisted |
| `yaam.l2.search_facts` | Read | Enabled |
| `yaam.l3.search_episodes` | Read | Enabled |
| `yaam.l3.assimilate_episode` | Write/lifecycle | Allowlisted |
| `yaam.l4.search_knowledge` | Read | Enabled |
| `yaam.l4.finalize_artifact` | Write/lifecycle | Allowlisted |
| `yaam.ciar.explain` | Read | Enabled |
| `yaam.evidence.table` | Read/agentic | Enabled as deterministic read assembly |
| `yaam.health.check` | Read | Enabled |

Each tool must return structured content and a compact text summary. Write tools
must return `WriteAck` only after persistence is confirmed.

### 5.2 Resources

MCP v1 resources are read-only:

- `yaam://sessions/{session_id}/context`
- `yaam://sessions/{session_id}/facts`
- `yaam://facts/{fact_id}`
- `yaam://episodes/{episode_id}`
- `yaam://knowledge/{knowledge_id}`
- `yaam://health`
- `yaam://config/ciar`
- `yaam://schemas/fact`
- `yaam://schemas/episode`
- `yaam://schemas/knowledge-document`

Resource handlers must not mutate memory and must redact secrets, raw
environment values, raw LLM reasoning traces, raw Phoenix credentials,
unredacted logs, and direct database connection details.

### 5.3 Prompts

MCP v1 must expose:

- `yaam.prompt.evidence_table`
- `yaam.prompt.memory_inspection`
- `yaam.prompt.ciar_explanation`
- `yaam.prompt.retrieval_strategy`

Prompts must encode reusable inspection workflows only. They must not trigger
hidden autonomous lifecycle behavior.

## 6. Response Contracts

Shared response models must include:

- `Provenance`: tier, source id, scope ids, producing agent, timestamps, and
  optional trace/audit identifiers.
- `YAAMWarning`: code, message, affected tier/capability, retryability, and
  optional details.
- `YAAMErrorPayload`: code, message, retryable, partial, operation,
  affected tier, trace id, audit id, and details.
- `PartialResponseMixin`: `partial` plus `warnings`.
- `MemoryResult`: content, tier, score, source id, metadata, provenance.
- `ContextResponse`: context items, source ids, token or size metadata,
  provenance, partial state, and warnings.
- `EvidenceTableResponse`: deterministic rows with claim, source tier/source
  id, evidence text, policy metadata, provenance, partial state, and warnings.
- `HealthResponse`: overall status and tier statuses without secrets.
- `WriteAck`: status, created or updated id, operation, provenance, audit id.

Read operations may return partial results with warnings. Write and lifecycle
operations must fail explicitly and must not claim persistence on failure.

## 7. Permission Contract

Default MCP v1 policy is read-only.

Configuration:

- `YAAM_MCP_ENABLE_WRITES=false` by default.
- `YAAM_MCP_ALLOWLISTED_TOOLS` contains comma-separated tool names enabled for
  writes or lifecycle operations.
- `YAAM_MCP_AUDIT_VISIBILITY=false` by default.

Denied mutating operations must return a structured non-retryable permission
error. Client capability claims must not override server-side policy.

## 8. Tracing Contract

MCP v1 must integrate with the existing OpenInference/Phoenix direction.

Each tool, resource, and prompt request must emit an auditable span or event
with:

- operation name;
- interface `MCP`;
- read/write/lifecycle classification;
- scope ids;
- caller identity when available;
- status;
- latency;
- result count;
- partial flag;
- warning count;
- error code;
- returned source ids when available.

Inbound `traceparent` from the scope envelope or MCP context metadata must be
propagated into downstream YAAM service calls when available.

## 9. Acceptance Criteria

MCP v1 is implemented when:

1. The MCP stdio server starts and shuts down cleanly.
2. SDK client tests can discover all v1 tools, resources, and prompts.
3. Read tools return structured data, provenance, and compact text summaries.
4. Resources are read-only and redacted.
5. Prompts render deterministic inspection templates.
6. Unallowlisted write tools are denied.
7. Allowlisted write tools persist data and return `WriteAck`.
8. Read degradation returns `partial=true` and warnings.
9. Write failures fail explicitly.
10. REST v2 behavior remains compatible after service extraction.
11. `./.venv/bin/ruff check .` passes.
12. `./.venv/bin/pytest tests/ -v` passes or documents environment-gated skips.

## 10. Non-Goals

MCP v1 does not include Streamable HTTP, customer-specific Skill Factory
resources, Maritime Port Sandbox resources, artifact lineage resources,
autonomous contradiction review, autonomous consolidation, autonomous
distillation, direct storage adapter exposure, arbitrary SQL/Cypher, or hidden
LLM reranking in Evidence Table generation.
