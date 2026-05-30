# Phoenix BatchSpanProcessor Implementation Report

**Date:** 2026-05-30  
**Status:** Local validation passed; remote validation pending  
**Related plan:** `docs/plan/2026-05-30-phoenix-batch-span-processor-plan.md`  
**Requirements:** `YAAM-REQ-0014`, `YAAM-REQ-0034`, `YAAM-REQ-0038`

## Summary

YAAM is being updated to use Phoenix SDK batch span exporting by default for
REST/MCP shared runtimes. The change is internal to observability delivery and
does not alter REST v2, MCP v1, scope, provenance, or `traceparent` contracts.

## Before

- Phoenix instrumentation used `phoenix.otel.register(...)` without explicit
  batch mode.
- Container startup logs included Phoenix's production recommendation to use a
  `BatchSpanProcessor`.
- Shutdown did not explicitly flush YAAM-owned Phoenix tracing resources.

## After

- `YAAM_OTEL_SPAN_PROCESSOR=batch` is the default when Phoenix tracing is
  enabled.
- `YAAM_OTEL_SPAN_PROCESSOR=simple` remains available for local debugging.
- YAAM force-flushes and shuts down only the tracer provider it created.
- Interface containers expose non-secret `OTEL_BSP_*` defaults.

## Validation Results

| Check | Result | Evidence |
| --- | --- | --- |
| `./.venv/bin/ruff check .` | Passed | `All checks passed!` |
| `./.venv/bin/pytest tests/utils/test_llm_client.py -v` | Passed | `14 passed` |
| `./.venv/bin/pytest tests/api/ tests/mcp/ tests/test_server_api_wall.py -v` | Passed | `36 passed, 3 skipped` |
| `./.venv/bin/pytest tests/ -v` | Passed | `746 passed, 142 skipped` |
| Remote REST health | Pending |  |
| Remote MCP live read contract | Pending |  |
| Remote REST L2/L3/L4 smoke | Pending |  |
| Remote Docker log review | Pending |  |
| Phoenix span export | Pending |  |

## Operational Notes

- Batch export means Phoenix spans may appear after a short delay controlled by
  `OTEL_BSP_SCHEDULE_DELAY`.
- Operators should keep a unique `PHOENIX_PROJECT_NAME` for each validation or
  consumer-readiness run.
- If a process exits abruptly, spans still buffered by the batch processor may
  be lost. Graceful shutdown now performs a best-effort force flush.

## Residual Risks

- Remote validation must confirm that the Phoenix startup warning is gone from
  `mas-agent` and `yaam-mcp` logs.
- Live span export remains dependent on Phoenix availability and the configured
  collector endpoint.
