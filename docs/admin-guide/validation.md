# YAAM Validation Guide

This guide describes local and live validation for YAAM 0.10.

## Required Local Validation

Run these commands from the repository root:

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest tests/api/ tests/mcp/ -v
```

For broader regression coverage, run:

```bash
./.venv/bin/pytest tests/ -v
```

Expected skips are normal when live storage, provider, or explicit MCP live
flags are absent.

## MCP Stdio Validation

Focused deterministic MCP validation:

```bash
./.venv/bin/pytest tests/mcp/ -v
```

Live read validation requires an explicit flag:

```bash
YAAM_MCP_RUN_LIVE_CONTRACT=1 ./.venv/bin/pytest tests/mcp/ -v
```

Live write/lifecycle validation must be intentional and synthetic:

```bash
YAAM_MCP_RUN_LIVE_CONTRACT=1 \
YAAM_MCP_RUN_LIVE_WRITE_CONTRACT=1 \
YAAM_MCP_ENABLE_WRITES=true \
YAAM_MCP_ENABLE_LIFECYCLE=true \
YAAM_MCP_ALLOWLISTED_TOOLS=yaam.l2.store_fact,yaam.l3.assimilate_episode,yaam.l4.finalize_artifact \
./.venv/bin/pytest tests/mcp/test_stdio_contract.py::test_mcp_stdio_live_write_contract_is_env_gated -v
```

Live validation should use synthetic scope identifiers such as
`mcp-live-contract-*` or `rest-live-contract-*`.

## REST Smoke Checks

REST smoke checks should cover:

- `POST /v2/memory/context` with `caller_role=benchmark_runtime_agent`.
- `POST /v2/memory/curation/decisions` with
  `caller_role=benchmark_maintainer`.
- `POST /v2/memory/trace-correlations` with
  `caller_role=post_run_ingestion_service`.
- A negative permission test that returns a structured `YAAMErrorPayload`.

Use synthetic records only. Do not include secrets or customer answer material
in request bodies.

## Customer Validation Location

The most reliable customer validation target is the `skz-data-lv` machine after
pulling the latest branch, because it can use the configured local backends and
provider environment without moving secrets across the network.

LAN validation can be performed when the REST service is intentionally exposed
on the LAN and storage/provider endpoints are reachable from that service
process. LAN clients should send only synthetic payloads and should not carry
provider keys or database credentials.

## What Should Customers Test

Customers should validate:

- MCP discovery, health, resources, prompts, and representative read tools.
- REST guarded reads through `/v2/memory/context` and `/v2/memory/query`.
- Maintainer-only curation write/list flows.
- Post-run trace correlation write/list flows.
- Structured permission errors for unauthorized roles or unallowlisted writes.
- Provenance, scope, and trace fields in successful responses.

Customers do not need to test raw database access, arbitrary query execution,
or deferred customer-specific resource views.

## Interpreting Failures

- Permission failures usually indicate a missing role, missing MCP gate, or
  missing allowlist entry.
- Provider failures usually indicate missing provider configuration or an
  unavailable external model provider.
- Storage failures usually indicate backend connectivity or schema/index
  mismatch.
- MCP transport failures usually indicate the host did not launch the stdio
  server with the expected command or environment.

## Related Documentation

- [Requirements registry](../requirements/README.md)
- [YAAM 0.10 release notes](../releases/0.10.md)
