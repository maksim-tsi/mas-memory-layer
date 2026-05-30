# Plan: Phoenix BatchSpanProcessor Hardening

**Date:** 2026-05-30  
**Status:** In progress  
**Requirements:** `YAAM-REQ-0014`, `YAAM-REQ-0034`, `YAAM-REQ-0038`

## Objective

Move YAAM Phoenix/OpenTelemetry export to the Phoenix SDK batch span processor
path for shared REST/MCP runtimes while preserving the existing public REST,
MCP, scope, provenance, and trace context contracts.

## Execution Tracker

| Step | Status | Evidence |
| --- | --- | --- |
| Code: enable `phoenix.otel.register(..., batch=True)` by default | Complete | `src/llm/client.py` |
| Code: add graceful flush/shutdown for YAAM-owned tracer provider | Complete | `src/llm/client.py`, REST/MCP lifecycles |
| Runtime: add non-secret BSP env defaults for interface containers | Complete | `docker-compose.interface.yml` |
| Tests: add deterministic Phoenix init/shutdown coverage | Complete | `tests/utils/test_llm_client.py` |
| Docs: update observability/admin/user documentation | Complete | Docs listed below |
| Local validation | Complete | `ruff`, focused tests, API/MCP tests, full suite |
| Remote validation on `skz-data-lv` | Pending | REST/MCP smoke, logs, Phoenix spans |
| Report | In progress | `docs/reports/2026-05-30-phoenix-batch-span-processor-implementation-report.md` |

## Implementation Notes

- Default processor mode is `batch` when `PHOENIX_COLLECTOR_ENDPOINT` is set.
- `YAAM_OTEL_SPAN_PROCESSOR=simple` remains available for local debugging.
- Invalid `YAAM_OTEL_SPAN_PROCESSOR` values fall back to `batch` with a compact
  warning.
- YAAM only force-flushes and shuts down tracer providers it creates itself.
  Externally preconfigured providers are used but not owned.
- REST/MCP clients do not need to change payloads. `traceparent` propagation,
  returned trace metadata, and public response schemas remain unchanged.

## Validation Commands

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest tests/utils/test_llm_client.py -v
./.venv/bin/pytest tests/api/ tests/mcp/ tests/test_server_api_wall.py -v
./.venv/bin/pytest tests/ -v
```

Remote validation target:

```text
REST: http://192.168.107.187:8002
MCP:  http://192.168.107.187:8003/mcp
Phoenix: http://192.168.107.187:6006
```

## Done Criteria

- Interface container startup logs no longer include Phoenix's default
  SpanProcessor production warning.
- REST and MCP smoke tests still pass.
- Phoenix spans are exported after the batch delay.
- No OpenInference startup warnings, Tracebacks, or unexpected `5xx` responses
  appear during the readiness smoke.
