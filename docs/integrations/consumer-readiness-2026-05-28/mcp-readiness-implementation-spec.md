# YAAM MCP v1 Consumer Readiness Specification

**Date:** 2026-05-28
**Status:** Active readiness specification
**Scope:** MCP v1 transport and contract readiness for consumer-system testing
**Related spec:** `docs/specs/spec-mcp-v1-implementation.md`
**Related runbook:** `docs/runbooks/mcp-v1-stdio-server.md`

## 1. Summary

YAAM MCP is no longer treated as a pending v0.1 placeholder for consumer readiness. The active
contract is MCP v1: a FastMCP service-backed adapter over the YAAM memory service layer.

YAAM supports two MCP transports over the same tools, resources, prompts, permissions, and response
contracts:

- **stdio**: reference/local transport for MCP hosts that launch YAAM as a subprocess.
- **Streamable HTTP**: shared lab/production transport for remote consumer systems.

Streamable HTTP is a transport extension over the same MCP server surface. It is not a REST wrapper
and it must not introduce separate memory semantics.

## 2. Required Consumer-Visible Endpoints

Stdio command:

```bash
./.venv/bin/python -m src.mcp.server --transport stdio --agent-type full --agent-variant mcp
```

Shared Streamable HTTP endpoint after deployment:

```text
http://192.168.107.187:8003/mcp
```

The shared HTTP service should run as `yaam-mcp`, separate from `mas-agent`, with writes and
lifecycle operations disabled by default.

## 3. Required MCP v1 Surface

Tools:

```text
yaam.memory.query
yaam.memory.get_context
yaam.l2.store_fact
yaam.l2.search_facts
yaam.l3.search_episodes
yaam.l3.assimilate_episode
yaam.l4.search_knowledge
yaam.l4.finalize_artifact
yaam.ciar.explain
yaam.evidence.table
yaam.contradiction.review
yaam.health.check
yaam.curation.record_decision
yaam.curation.list_decisions
yaam.trace.record_correlation
yaam.trace.lookup
```

Resources:

```text
yaam://health
yaam://config/ciar
yaam://schemas/fact
yaam://schemas/episode
yaam://schemas/knowledge-document
yaam://sessions/{session_id}/context
yaam://sessions/{session_id}/facts
yaam://facts/{fact_id}
yaam://episodes/{episode_id}
yaam://knowledge/{knowledge_id}
```

Prompts:

```text
yaam.prompt.evidence_table
yaam.prompt.memory_inspection
yaam.prompt.ciar_explanation
yaam.prompt.retrieval_strategy
```

## 4. Permission and Reliability Contract

- Read tools, resources, and prompts are enabled by default.
- Write and lifecycle tools are disabled by default.
- Mutating tools require `YAAM_MCP_ENABLE_WRITES=true` and explicit
  `YAAM_MCP_ALLOWLISTED_TOOLS`.
- Lifecycle tools additionally require `YAAM_MCP_ENABLE_LIFECYCLE=true`.
- Default write denial must return a structured, non-retryable permission error.
- Read operations may return partial results with warnings.
- Write and lifecycle operations must fail fast and must not report success unless persistence or
  lifecycle execution completed.
- Responses must preserve scope, provenance, warnings, structured errors, and trace metadata where
  available.
- Resources must not expose secrets, raw `.env` values, provider keys, database passwords, or raw
  sensitive traces.

## 5. Deployment Expectations

Compose runtime:

```text
REST/API Wall service: mas-agent -> http://192.168.107.187:8002
MCP Streamable HTTP service: yaam-mcp -> http://192.168.107.187:8003/mcp
```

`yaam-mcp` must receive the same non-secret `skz-data-lv` backend endpoint overrides as
`mas-agent`. Secrets remain in runtime environment files and must not be copied into docs,
reports, logs, or MCP resource payloads.

## 6. Consumer Readiness Checks

Before asking external consumers to run MCP readiness:

```bash
./.venv/bin/python -c 'import mcp'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/mcp/ -v
```

Required deterministic checks:

- stdio discovery and read contract;
- Streamable HTTP discovery and read contract;
- `yaam.health.check`;
- `yaam://config/ciar`;
- `yaam.prompt.memory_inspection`;
- default write-denial for `yaam.l2.store_fact`.

Live read-only HTTP validation:

```bash
YAAM_MCP_RUN_LIVE_HTTP_CONTRACT=1 \
YAAM_MCP_HTTP_URL=http://192.168.107.187:8003/mcp \
./.venv/bin/pytest tests/mcp/test_streamable_http_contract.py::test_mcp_streamable_http_live_read_contract_is_env_gated -v
```

Live write validation remains opt-in, synthetic, and explicitly allowlisted.

## 7. Non-Goals

- no direct storage adapter exposure;
- no arbitrary SQL, Cypher, Redis, Qdrant, or Typesense command execution;
- no customer-specific resource views unless accepted in a separate requirement;
- no hidden autonomous lifecycle behavior through prompts or resources;
- no dependency updates beyond the already approved `mcp>=1.12.4,<1.27.1` range unless a later SDK
  compatibility issue requires explicit approval.
