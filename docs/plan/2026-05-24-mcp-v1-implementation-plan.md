# MCP v1 Implementation Plan

**Status:** Draft
**Date:** 2026-05-24
**Spec:** [MCP v1 Implementation Contract](../specs/spec-mcp-v1-implementation.md)
**Related RFC:** [YAAM MCP v1 Planning Freeze](../RFC/2026-05-24-yaam-mcp-v1-planning-freeze.md)

## Summary

This plan implements MCP v1 in senior-developer batches of four hours or less.
The implementation is stdio-first, uses the official Python MCP SDK/FastMCP
after explicit dependency approval, and keeps MCP as an adapter over shared YAAM
services.

## Batch Plan

### Batch 1: Spec Docs And Dependency Approval (<=2h)

- Add the MCP v1 implementation specification and this batch plan.
- Link both from the specs and plans indexes.
- Request explicit approval before modifying `pyproject.toml` or `poetry.lock`
  for the MCP SDK dependency.
- Add `mcp>=1.12.4,<1.27.1`, the newest resolver-compatible SDK range for the
  current `pydantic==2.8.2` pin. Defer `mcp>=1.27.1` until a separate Pydantic
  upgrade is approved and verified.

Acceptance evidence:

- Documentation exists and cites the covered `YAAM-REQ-*` IDs.
- No code or dependency files are changed before approval.

### Batch 2: SDK Dependency And Empty Server Skeleton (<=3h)

- Add the approved MCP SDK dependency.
- Add `src/mcp/server.py` and `src/mcp/__main__.py`.
- Implement FastMCP construction, stdio startup, runtime initialization through
  existing `WrapperConfig` and `initialize_state`, and clean shutdown.
- Add a discovery smoke test using SDK test utilities or an in-process client.

Acceptance evidence:

- The empty server starts and stops.
- A client can initialize and list an empty or minimal MCP capability set.

### Batch 3: Shared Contracts And Serializers (<=4h)

- Add `src/memory/services/contracts.py`.
- Implement `ScopeEnvelope`, provenance, warning, error, partial, result,
  context, evidence, health, and write acknowledgement models.
- Add serializers for `Fact`, `Episode`, `KnowledgeDocument`, and unified
  retrieval result dictionaries.
- Add redaction helpers for metadata and resource responses.

Acceptance evidence:

- Unit tests cover validation, JSON schema generation, serialization, and
  redaction.

### Batch 4: Permission And Runtime Context (<=3h)

- Add `PermissionPolicy` with default read-only behavior.
- Read configuration from `YAAM_MCP_ENABLE_WRITES`,
  `YAAM_MCP_ALLOWLISTED_TOOLS`, and `YAAM_MCP_AUDIT_VISIBILITY`.
- Add MCP runtime context helpers around `AgentWrapperState`.

Acceptance evidence:

- Tests cover denied writes, allowlisted writes, missing scope fields, and audit
  metadata.

### Batch 5: MemoryTierService (<=4h)

- Implement scoped L2 store/search/read, L3 search/read/assimilate, L4
  search/read/finalize, and health/config wrappers.
- Preserve current v2 L2 CIAR component behavior.
- Return structured acknowledgements and warnings.

Acceptance evidence:

- Mocked tier tests cover success, not found, validation failure, backend
  failure, and health/config responses.

### Batch 6: UnifiedRetrievalService (<=3h)

- Wrap `UnifiedMemorySystem.query_memory()` and `get_context_block()`.
- Convert existing outputs into `MemoryResult` and `ContextResponse`.
- Preserve current tier weighting behavior while adding warnings and partial
  state.

Acceptance evidence:

- Tests cover cross-tier query, context assembly, tier failure partial reads,
  and provenance fields.

### Batch 7: CIARPolicyService And EvidenceService (<=4h)

- Implement deterministic CIAR explanation with component scores and policy
  metadata.
- Implement Evidence Table v1 as deterministic row assembly from scoped memory
  results.
- Do not add LLM reranking.

Acceptance evidence:

- Tests cover CIAR output shape, evidence row shape, partial evidence behavior,
  and hidden audit-only data defaults.

### Batch 8: REST v2 Service Refactor (<=4h)

- Refactor `src/api/v2_router.py` to call the shared services.
- Preserve route paths and response compatibility.
- Add traceparent extraction for v2 route spans where missing.

Acceptance evidence:

- Existing v2 tests pass.
- New compatibility tests cover L2, L3, L4, error semantics, and traceparent
  propagation.

### Batch 9: MCP Tools (<=4h)

- Register all MCP v1 tools with FastMCP.
- Wire tools to services and permission policy.
- Return structured content plus compact text summaries.

Acceptance evidence:

- MCP tests cover discovery, tool schemas, read calls, denied writes, and
  allowlisted write paths.

### Batch 10: MCP Resources And Prompts (<=4h)

- Register all MCP v1 resource templates.
- Register all common MCP v1 prompts.
- Ensure resources are read-only and redacted.

Acceptance evidence:

- Tests cover resource discovery, resource reads, prompt discovery, prompt
  rendering, and no mutation.

### Batch 11: MCP Observability And Error Contract (<=3h)

- Add MCP span helpers using existing `src/observability` helpers.
- Normalize service exceptions into MCP-visible structured errors.
- Record operation, scope, status, latency, partial state, warnings, and source
  ids.

Acceptance evidence:

- Fake-tracer tests cover span attributes, trace metadata propagation,
  structured errors, and partial read warnings.

### Batch 12: End-To-End MCP Contract Tests (<=4h)

- Add stdio SDK client contract tests for discovery and representative calls.
- Cover health, memory query, context, L2 search, CIAR explain, Evidence Table,
  resource read, and prompt get.
- Keep live integration tests environment-gated.

Acceptance evidence:

- Stdio contract tests pass without live external services where mocks are used.
- Live tests skip clearly when required environment is absent.

### Batch 13: Runbook And Final Verification (<=3h)

- Add a runbook for launching and inspecting the MCP stdio server.
- Document environment variables, allowlist configuration, and troubleshooting.
- Run repository verification.

Acceptance evidence:

- `./.venv/bin/ruff check .` passes.
- `./.venv/bin/pytest tests/ -v` passes or environment-gated skips are
  documented.

## Implementation Constraints

- Do not modify `src/storage/` without explicit user authorization.
- Do not add or update dependencies without explicit approval.
- Do not expose customer-specific resources in generic MCP v1.
- Do not use raw `.env` values or secrets in resources, prompts, traces, or
  docs.
- Use `pytest-mock` rather than direct `unittest.mock` imports in new tests.

## Verification Sequence

Before running lint or tests:

```bash
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
```

Required after source changes:

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest tests/ -v
```
