# YAAM Consumer Readiness Gate Report

Date: 2026-05-30  
Branch: `dev-tests`  
Local validation commit: `2109939` plus additive L2 metadata migration follow-up  
Remote host: `skz-data-lv`  
REST endpoint: `http://192.168.107.187:8002`  
MCP endpoint: `http://192.168.107.187:8003/mcp`

## Verdict

Pass after remediation.

The initial gate found the shared consumer endpoints down because `mas-agent`
and `yaam-mcp` were stopped. The interface services were rebuilt and restarted,
Compose restart/healthcheck settings were added, and both services are now
healthy.

The first REST smoke after restart found an L2 schema drift: `working_memory`
was missing the `metadata` column required for project/provenance metadata.
The additive migration was applied on `skz-data-lv`, and the repeat REST smoke
passed.

## Configuration Evidence

- `YAAM_PROJECT_ID=test`
- `OPENROUTER_MODEL=tencent/hy3-preview`
- `OPENROUTER_EMBEDDING_MODEL=qwen/qwen3-embedding-8b`
- `EMBEDDING_DIMENSIONS=4096`
- `MAS_L3_COLLECTION` unset, so L3 derives `yaam-test-episodes`
- `MAS_L4_COLLECTION` unset, so L4 derives `yaam-test`
- MCP writes/lifecycle remain disabled by default

## Local Validation

| Check | Result |
| --- | --- |
| `./.venv/bin/ruff check .` | passed |
| `YAAM_PROJECT_ID=test ./.venv/bin/pytest tests/api/ tests/mcp/ tests/memory/test_namespace.py -v` | 46 passed, 8 skipped |
| `./.venv/bin/pytest tests/ -v` | 740 passed, 142 skipped |
| `git diff --check` | passed |

## Remote Gate Evidence

| Check | Result |
| --- | --- |
| `docker compose ... ps` | `mas-agent` and `yaam-mcp` healthy |
| `GET /health` | HTTP 200, `status=ok` |
| REST L2 store | HTTP 200, fact `e1c8fef3-2bbb-49b5-b6b6-110e20012e5a` |
| REST L2 retrieve | HTTP 200, retrieved 1 fact |
| REST L2 isolation | HTTP 200, retrieved 0 facts from another session |
| REST L3 assimilate | HTTP 201, episode `ep-b633de41` |
| REST L3 query | HTTP 200 |
| REST L4 finalize | HTTP 201, knowledge `kd-ba107058` |
| MCP HTTP live read contract | passed |
| MCP default write posture | denied with `permission.writes_disabled` |

Synthetic REST scope:

- `session_id`: `consumer-readiness-20260530-1780142801`
- `task_id`: `consumer-readiness-20260530-1780142801-task`
- `traceparent`: `00-abcdefabcdefabcdefabcdefabcdefab-fedcbafedcbafedc-01`

## Remediations Applied

- Added `restart: unless-stopped` and healthchecks for interface services.
- Removed obsolete Compose `version` field.
- Updated consumer readiness assignment/register and E2E test plan for
  `YAAM_PROJECT_ID=test` and project-derived `yaam-test-*` collections.
- Removed legacy `MAS_L3_COLLECTION` and `MAS_L4_COLLECTION` overrides from the
  remote runtime environment.
- Added and applied additive migration
  `migrations/004_add_working_memory_metadata.sql`.

## Residual Notes

- Startup logs still include the known Phoenix recommendation to use
  `BatchSpanProcessor` in production-like deployments. This is observability
  hardening, not a consumer-readiness blocker.
- The current shared endpoint is ready for first-wave consumer testing as a
  single project namespace instance using `YAAM_PROJECT_ID=test`.
