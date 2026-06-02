# Phoenix BatchSpanProcessor Implementation Report

**Date:** 2026-05-30  
**Status:** Complete  
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
| Remote REST health | Passed | `curl -fsS http://192.168.107.187:8002/health` returned HTTP 200 |
| Remote MCP live read contract | Passed | `1 passed` against `http://192.168.107.187:8003/mcp` |
| Remote REST L2/L3/L4 smoke | Passed | Synthetic session `bsp-phoenix-project-1780150430`; L2 store/retrieve, L3 assimilate/query, L4 finalize all returned 2xx |
| Remote Docker log review | Passed | No Phoenix default processor banner/warning, OpenInference warning, Traceback, or unexpected `5xx` in final logs |
| Phoenix span export | Passed | Project `mlm-mas-dev-phoenix-bsp-20260530`; `50` spans, `0` errors |

## Remote Evidence Summary

Final deployment commit: `e1c3433`.

Fresh Phoenix project:

```text
mlm-mas-dev-phoenix-bsp-20260530
```

Synthetic REST scope:

```text
session_id: bsp-phoenix-project-1780150430
task_id: bsp-phoenix-project-1780150430-task
traceparent: 00-fedcba9876543210fedcba9876543210-abcdefabcdefabcd-01
```

REST smoke:

| Operation | HTTP | Result |
| --- | --- | --- |
| L2 store | 200 | fact `e5aeb79f-0d0b-4755-b988-a98bcb6ceaa5` |
| L2 retrieve | 200 | retrieved `1` fact |
| L3 assimilate | 201 | episode `ep-c073c999` |
| L3 query | 200 | successful query, `0` matching results |
| L4 finalize | 201 | knowledge `kd-6d9d09f9` |

Phoenix export summary:

| Metric | Value |
| --- | --- |
| Total spans | `50` |
| Errors | `0` |
| Span kinds | `EMBEDDING=2`, `LLM=2`, `TOOL=3`, `UNKNOWN=43` |
| REST spans | L2 facts, L3 assimilate/query, L4 finalize |
| MCP spans | `yaam.health.check`, `yaam://config/ciar`, `yaam.prompt.memory_inspection` |

## Operational Notes

- Batch export means Phoenix spans may appear after a short delay controlled by
  `OTEL_BSP_SCHEDULE_DELAY`.
- Operators should keep a unique `PHOENIX_PROJECT_NAME` for each validation or
  consumer-readiness run.
- If a process exits abruptly, spans still buffered by the batch processor may
  be lost. Graceful shutdown now performs a best-effort force flush.

## Residual Risks

- Live span export remains dependent on Phoenix availability and the configured
  collector endpoint.
- Abrupt container termination can still lose spans that have not yet been
  flushed by the batch processor.
