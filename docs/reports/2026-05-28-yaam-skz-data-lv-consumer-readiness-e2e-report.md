# YAAM skz-data-lv Consumer Readiness E2E Report

> Superseded follow-up: the L3 vector dimension blocker, deprecated OpenRouter default, and MCP
> `ClosedResourceError` log-noise findings in this report were addressed later on 2026-05-28.
> Current evidence is captured in
> `docs/reports/2026-05-28-yaam-runtime-dependency-hardening-validation-report.md`.

**Date:** 2026-05-28
**Runner:** Codex from MacBook workspace
**Remote host:** `skz-data-lv` via `ssh skz-data-local`
**Remote checkout:** `/home/maxim/code/yet-another-agents-memory`
**Branch/commit tested:** `dev-tests` / `39f9796 Add Streamable HTTP transport for MCP consumer readiness`
**REST endpoint:** `http://192.168.107.187:8002`
**MCP endpoint:** `http://192.168.107.187:8003/mcp`
**Phoenix project:** `mlm-mas-dev-consumer-readiness-20260528`

## Verdict

**Consumer readiness is partially ready, with blocking L3 readiness findings.**

REST v2 and MCP Streamable HTTP are reachable from the MacBook, MCP discovery works, MCP read
contract passes, L2 writes work, and L4 finalize writes return acknowledgements. However, both REST
and MCP L3 assimilation fail in the shared `skz-data-lv` runtime because Qdrant collection
`episodes_v2` expects 4096-dimensional vectors while the active embedding path produces 768-dimensional
vectors. This should be fixed before asking consumer projects to validate L3 write/lifecycle workflows.

After the write-enabled E2E window, `yaam-mcp` was restarted without the temporary override. Final MCP
health confirmed `writes_enabled=false` and `lifecycle_enabled=false`; a write tool returned structured
`permission.writes_disabled`.

## Execution Summary

| Check | Result | Evidence |
| --- | --- | --- |
| Local branch sync | Pass | Local `dev-tests` pushed to origin; remote fast-forwarded to `39f9796`. |
| Backend containers | Pass | `postgres`, `redis`, `qdrant`, `neo4j`, `typesense`, and `phoenix` were already running on `skz-data-lv`. |
| Interface containers | Pass | `mas-agent` published `8002:8080`; `yaam-mcp` published `8003:8081`. |
| REST `/health` | Pass | HTTP 200, `status=ok`, L1/L2 healthy, agent healthy. |
| REST L2 store/retrieve | Pass | Store HTTP 200, retrieve HTTP 200 with the synthetic fact. |
| REST L3 assimilate | Fail | HTTP 502, Qdrant vector dimension mismatch: expected 4096, got 768. |
| REST L3 query | Pass/degraded | HTTP 200 with empty results after failed assimilation. |
| REST L4 finalize | Pass | HTTP 201 with `knowledge_id`. |
| MCP HTTP read contract | Pass | `tests/mcp/test_streamable_http_contract.py::test_mcp_streamable_http_live_read_contract_is_env_gated` passed. |
| MCP discovery/read smoke | Pass | Tools, resources, resource templates, prompts, health, and `yaam://config/ciar` available. |
| MCP L2 write | Pass | `yaam.l2.store_fact` returned success ack with provenance. |
| MCP L3 lifecycle write | Fail | `yaam.l3.assimilate_episode` returned structured MCP error backed by storage failure. |
| MCP L4 write | Pass | `yaam.l4.finalize_artifact` returned success ack with provenance. |
| Phoenix ingest | Pass | Phoenix logs showed repeated `POST /v1/traces` HTTP 200. |
| Phoenix project export | Pass/degraded | 36 spans exported, including REST and MCP spans; 4 error spans recorded. |
| Post-test safe mode | Pass | MCP health showed writes/lifecycle disabled; L2 write denied with `permission.writes_disabled`. |

## Commands Run

Key commands executed:

```bash
git push origin dev-tests
ssh skz-data-local 'cd /home/maxim/code/yet-another-agents-memory && git fetch origin && git pull --ff-only origin dev-tests'
ssh skz-data-local 'cd /home/maxim/code/yet-another-agents-memory && docker compose -f docker-compose.interface.yml -f docker-compose.skz-data.yml -f /tmp/yaam-consumer-readiness-override.yml up -d --build mas-agent yaam-mcp'
curl -fsS http://192.168.107.187:8002/health
YAAM_MCP_RUN_LIVE_HTTP_CONTRACT=1 YAAM_MCP_HTTP_URL=http://192.168.107.187:8003/mcp ./.venv/bin/pytest tests/mcp/test_streamable_http_contract.py::test_mcp_streamable_http_live_read_contract_is_env_gated -v
./.venv/bin/python scripts/debug/export_phoenix_spans.py --base-url http://192.168.107.187:6006 --project mlm-mas-dev-consumer-readiness-20260528 --output-dir /tmp/yaam-phoenix-consumer-readiness-20260528 --summary-output /tmp/yaam-phoenix-consumer-readiness-20260528-summary.json --limit 200
ssh skz-data-local 'cd /home/maxim/code/yet-another-agents-memory && docker compose -f docker-compose.interface.yml -f docker-compose.skz-data.yml up -d yaam-mcp'
```

The temporary override enabled only the intended synthetic MCP write window:

```yaml
PHOENIX_PROJECT_NAME: mlm-mas-dev-consumer-readiness-20260528
YAAM_MCP_ENABLE_WRITES: "true"
YAAM_MCP_ENABLE_LIFECYCLE: "true"
YAAM_MCP_ALLOWLISTED_TOOLS: yaam.l2.store_fact,yaam.l3.assimilate_episode,yaam.l4.finalize_artifact
```

## Synthetic IDs

REST run:

- `session_id`: `consumer-readiness-20260528082943`
- `task_id`: `consumer-readiness-task-consumer-readiness-20260528082943`
- `traceparent`: `00-11111111111111111111111111111111-2222222222222222-01`

MCP run:

- `session_id`: `mcp-http-consumer-readiness-af5b6a35`
- `task_id`: `mcp-http-consumer-readiness-task-af5b6a35`

## Findings

| ID | Priority | Category | Finding | Evidence | Recommended action |
| --- | --- | --- | --- | --- | --- |
| E2E-001 | P0 | data-correctness | L3 assimilation cannot store vectors in Qdrant because `episodes_v2` expects 4096 dimensions while runtime embeddings are 768 dimensions. | REST `/v2/memory/l3/assimilate` returned HTTP 502; MCP `yaam.l3.assimilate_episode` returned structured storage error. | Align L3 collection vector size with active embedding model, or route runtime to the 4096-dimension embedding provider used when the collection was created. Re-run REST and MCP L3 write checks. |
| E2E-002 | P1 | deployment | Active OpenRouter model is deprecated and returns 404 for L3 LLM path. | Logs showed provider failure for the configured Grok model before Qdrant storage failure. | Update `MAS_MODEL` default/override to a current supported OpenRouter model and re-run L3 assimilation. |
| E2E-003 | P1 | data-correctness | L4 health is degraded because Typesense collection `knowledge_base_v2` search returns 404, even though finalize writes returned a `knowledge_id`. | MCP `yaam.health.check` reported L4 unavailable with Typesense 404. | Ensure `knowledge_base_v2` exists and health checks match the deployed Typesense schema. Re-run MCP health and L4 search/finalize checks. |
| E2E-004 | P2 | reliability | MCP Streamable HTTP logs emit repeated `anyio.ClosedResourceError` in message router after successful client interactions. | `yaam-mcp` logs showed `Error in message router` with `ClosedResourceError` alongside HTTP 200/202 MCP calls. | Determine whether this is benign client disconnect noise from the SDK or a server lifecycle issue; suppress or fix before broad consumer testing if it pollutes logs. |

## Phoenix Evidence

Phoenix export summary:

```json
{
  "project": "mlm-mas-dev-consumer-readiness-20260528",
  "span_count": 36,
  "error_count": 4,
  "span_counts_by_kind": {
    "TOOL": 8,
    "UNKNOWN": 28
  }
}
```

Notable span names included:

- `GET /health`
- `POST /v2/memory/l2/facts`
- `POST /v2/memory/l3/assimilate`
- `POST /v2/memory/l3/query`
- `POST /v2/memory/l4/finalize`
- `yaam.mcp.tool.yaam.health.check`
- `yaam.mcp.tool.yaam.l2.store_fact`
- `yaam.mcp.tool.yaam.l3.assimilate_episode`
- `yaam.mcp.tool.yaam.l4.finalize_artifact`
- `yaam.mcp.resource.yaam://config/ciar`
- `yaam.mcp.prompt.yaam.prompt.memory_inspection`

## Current Runtime Posture

Final state after the E2E run:

- `mas-agent` is running on `skz-data-lv` and publishes `8002:8080`.
- `yaam-mcp` is running on `skz-data-lv` and publishes `8003:8081`.
- REST `/health` returns HTTP 200 with `status=ok`.
- MCP health returns `degraded` because L4 health is unavailable.
- MCP writes and lifecycle are disabled again:
  - `writes_enabled=false`
  - `lifecycle_enabled=false`
  - write attempts return `permission.writes_disabled`

## Recommendation

Do not ask consumer projects to validate L3 write/lifecycle workflows yet. It is reasonable to ask
them to perform REST health, REST L2, MCP discovery/read, and MCP permission-denial checks while we
fix the L3 vector-size mismatch and L4 Typesense health issue.
