# Runbook: MCP v1 Server

**Status:** Active  
**Date:** 2026-05-24  
**Audience:** Maintainers, MCP host integrators, validation operators  
**Related:** [MCP v1 implementation contract](../specs/spec-mcp-v1-implementation.md), [MCP v1 implementation plan](../plan/2026-05-24-mcp-v1-implementation-plan.md), [MCP v1 planning freeze](../RFC/2026-05-24-yaam-mcp-v1-planning-freeze.md)

## 1. Purpose

This runbook defines the repeatable procedure for launching and validating the
YAAM MCP v1 adapter over stdio and Streamable HTTP. MCP v1 is a generic,
service-backed interface over YAAM memory services. It does not replace the API
Wall or REST Semantic Gateway v2 routes.

The default operational posture is read-only. Mutating and lifecycle tools are
available only when server-side environment flags explicitly enable writes,
enable lifecycle actions, and allowlist the target tool names.

## 2. Preconditions

Run commands from the repository root with the repository virtual environment.
Do not activate the environment; call the executables directly.

```bash
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
```

The interpreter path must point to this repository's `.venv/bin/python`.

## 3. Start The Stdio Server

Use the production MCP entrypoint:

```bash
./.venv/bin/python -m src.mcp.server --agent-type full --agent-variant mcp
```

For parity with the original implementation specification, the `baseline`
variant is also accepted:

```bash
./.venv/bin/python -m src.mcp.server --agent-type full --agent-variant baseline
```

An MCP host should launch the command as a stdio subprocess. The server writes
MCP protocol messages over stdio and should not be inspected with an ordinary
terminal prompt as an interactive CLI.

## 4. Start The Streamable HTTP Server

Use Streamable HTTP when consumer systems need to connect to a shared YAAM MCP
runtime:

```bash
./.venv/bin/python -m src.mcp.server \
  --transport streamable-http \
  --agent-type full \
  --agent-variant mcp \
  --mcp-host 0.0.0.0 \
  --mcp-port 8081 \
  --mcp-path /mcp
```

The lab Compose runtime publishes this service at:

```text
http://192.168.107.187:8003/mcp
```

Streamable HTTP exposes the same tools, resources, prompts, permissions, and
service-layer contracts as stdio.

## 5. Expected MCP Surface

Tools:

- `yaam.memory.query`
- `yaam.memory.get_context`
- `yaam.l2.store_fact`
- `yaam.l2.search_facts`
- `yaam.l3.search_episodes`
- `yaam.l3.assimilate_episode`
- `yaam.l4.search_knowledge`
- `yaam.l4.finalize_artifact`
- `yaam.ciar.explain`
- `yaam.evidence.table`
- `yaam.contradiction.review`
- `yaam.health.check`
- `yaam.curation.record_decision`
- `yaam.curation.list_decisions`
- `yaam.trace.record_correlation`
- `yaam.trace.lookup`

Resources:

- `yaam://health`
- `yaam://config/ciar`
- `yaam://schemas/fact`
- `yaam://schemas/episode`
- `yaam://schemas/knowledge-document`
- `yaam://sessions/{session_id}/context`
- `yaam://sessions/{session_id}/facts`
- `yaam://facts/{fact_id}`
- `yaam://episodes/{episode_id}`
- `yaam://knowledge/{knowledge_id}`

Prompts:

- `yaam.prompt.evidence_table`
- `yaam.prompt.memory_inspection`
- `yaam.prompt.ciar_explanation`
- `yaam.prompt.retrieval_strategy`

## 6. Permission Configuration

Read tools, resources, and prompts are enabled by default. Writes and lifecycle
operations require server-side configuration:

```bash
export YAAM_MCP_ENABLE_WRITES=true
export YAAM_MCP_ENABLE_LIFECYCLE=true
export YAAM_MCP_ALLOWLISTED_TOOLS=yaam.l2.store_fact,yaam.l3.assimilate_episode,yaam.l4.finalize_artifact
```

Permission flags are evaluated by the server. MCP client capability claims do
not grant additional access.

SCM-Cert-Bench curation and trace-correlation writes use the same write
allowlist, and they also require `caller_role=benchmark_maintainer` or
`caller_role=post_run_ingestion_service` in the tool scope. Runtime benchmark
callers should use `caller_role=benchmark_runtime_agent` and
`visibility_scope=benchmark_runtime` when requesting context so the leakage
guard reports checked and filtered items.

Default-denied writes return a structured MCP-visible YAAM error payload with:

- `code`
- `message`
- `operation`
- `retryable`
- `affected_tier`
- `details`

For default write denial, the expected code is
`permission.writes_disabled` and `affected_tier` is `SYSTEM`.

## 7. Local Contract Validation

Run deterministic MCP stdio tests without live external services:

```bash
./.venv/bin/pytest tests/mcp/ -v
```

This validates discovery, read tools, resources, prompts, benchmark
leakage-guard metadata, contradiction review, maintainer-only curation reads,
trace-correlation reads, structured errors, and test-fixture write
acknowledgements over the real MCP stdio transport.

Run the repository verification sequence:

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest tests/ -v
```

## 8. Streamable HTTP Contract Validation

The deterministic Streamable HTTP contract test starts a fixture-backed MCP
server and validates discovery, representative read operations, resource reads,
prompt rendering, and default write denial:

```bash
./.venv/bin/pytest tests/mcp/test_streamable_http_contract.py -v
```

Live Streamable HTTP validation is read-only and environment-gated:

```bash
YAAM_MCP_RUN_LIVE_HTTP_CONTRACT=1 \
YAAM_MCP_HTTP_URL=http://192.168.107.187:8003/mcp \
./.venv/bin/pytest tests/mcp/test_streamable_http_contract.py::test_mcp_streamable_http_live_read_contract_is_env_gated -v
```

## 9. Live Read Validation

Live production-server read checks are opt-in:

```bash
YAAM_MCP_RUN_LIVE_CONTRACT=1 \
./.venv/bin/pytest tests/mcp/test_stdio_contract.py::test_mcp_stdio_live_read_contract_is_env_gated -v
```

The live read test starts the production stdio server, performs discovery,
calls `yaam.health.check`, reads `yaam://config/ciar`, and renders
`yaam.prompt.memory_inspection`. The test remains read-only.

## 10. Live Write And Lifecycle Validation

Live write validation is intentionally separate because it persists synthetic
test records through the configured YAAM backends and L3 lifecycle validation
may call the configured LLM provider.

Use a dedicated validation environment and enable all required flags:

```bash
YAAM_MCP_RUN_LIVE_CONTRACT=1 \
YAAM_MCP_RUN_LIVE_WRITE_CONTRACT=1 \
YAAM_MCP_ENABLE_WRITES=true \
YAAM_MCP_ENABLE_LIFECYCLE=true \
YAAM_MCP_ALLOWLISTED_TOOLS=yaam.l2.store_fact,yaam.l3.assimilate_episode,yaam.l4.finalize_artifact \
./.venv/bin/pytest tests/mcp/test_stdio_contract.py::test_mcp_stdio_live_write_contract_is_env_gated -v
```

The live write test calls:

- `yaam.l2.store_fact`
- `yaam.l3.assimilate_episode`
- `yaam.l4.finalize_artifact`

Each call must return a structured `WriteAck` with `status=success`,
`operation`, `created_id`, and provenance fields for source tier, session,
agent, and task.

## 11. Troubleshooting

- If discovery fails, confirm the MCP SDK dependency is installed in the active
  repository virtual environment.
- If the stdio process exits during startup, run the server command directly
  and inspect only non-secret configuration errors.
- If Streamable HTTP discovery fails, confirm the MCP URL includes `/mcp`, the
  `yaam-mcp` service is running, and port `8003` is reachable from the
  consumer host.
- If write tools return `permission.writes_disabled`, set
  `YAAM_MCP_ENABLE_WRITES=true`.
- If lifecycle tools return `permission.lifecycle_disabled`, set
  `YAAM_MCP_ENABLE_LIFECYCLE=true`.
- If write tools return `permission.tool_not_allowlisted`, include the exact
  tool name in `YAAM_MCP_ALLOWLISTED_TOOLS`.
- If L3 lifecycle validation fails in live mode, verify the configured LLM
  provider and embedding path are available without printing provider secrets.
