# YAAM Runtime Hardening Validation Report

Date: 2026-05-28
Branch: `dev-tests`
Commit validated: `f83df5c`
Remote host: `skz-data-lv`
REST endpoint: `http://192.168.107.187:8002`
MCP endpoint: `http://192.168.107.187:8003/mcp`

## Verdict

Pass with follow-up items.

The runtime hardening change removes the previous L3 vector dimension blocker.
YAAM now runs with OpenRouter generation default `tencent/hy3-preview`,
OpenRouter embedding model `qwen/qwen3-embedding-8b`, 4096-dimensional
embeddings, and L3 collection `episodes_qwen_v2`.

## Configuration Evidence

Tracked runtime defaults were added in `config/runtime.yaml`:

- `llm.openrouter_model`: `tencent/hy3-preview`
- `llm.openrouter_embedding_model`: `qwen/qwen3-embedding-8b`
- `memory.l3.collection_name`: `episodes_qwen_v2`
- `memory.l3.vector_size`: `4096`
- `memory.l4.collection_name`: `knowledge_base_v2`

Container non-secret runtime environment was verified:

- `OPENROUTER_MODEL=tencent/hy3-preview`
- `OPENROUTER_EMBEDDING_MODEL=qwen/qwen3-embedding-8b`
- `EMBEDDING_DIMENSIONS=4096`
- `MAS_L3_COLLECTION=episodes_qwen_v2`
- `MAS_L4_COLLECTION=knowledge_base_v2`

Qdrant collection `episodes_qwen_v2` was verified as green with vector size
`4096` and `312` existing points before synthetic validation writes.

The live embedding probe from inside `mas-agent` returned dimension `4096`.

## Local Verification

Commands:

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest tests/evaluation/test_agent_wrapper_runtime_config.py -v
./.venv/bin/pytest tests/mcp/ -v
./.venv/bin/pytest tests/api/test_v2_router_ciar.py -v
./.venv/bin/pytest tests/test_server_api_wall.py -v
git diff --check
```

Results:

- Ruff: pass
- Runtime config tests: `2 passed`
- MCP tests: `21 passed, 3 skipped`
- REST v2 API router tests: `10 passed`
- Server API Wall tests: `3 passed`
- Diff whitespace check: pass

## Remote Deployment

Remote checkout was fast-forwarded to `f83df5c` and `mas-agent` plus
`yaam-mcp` were rebuilt and restarted with:

```bash
docker compose -f docker-compose.interface.yml -f docker-compose.skz-data.yml up -d --build mas-agent yaam-mcp
```

Docker build context after `.dockerignore` was approximately `81 KB`.
The rebuilt YAAM images are approximately `10.3 GB` each. They still share
layers, so this is not two fully independent 10.3 GB footprints.

## REST E2E Evidence

Health:

- `GET /health`: HTTP 200, status `ok`

Synthetic REST run:

- `session_id`: `runtime-hardening-fe47ac88be`
- `task_id`: `task-fe47ac88be`
- `traceparent`: `00-abda741080464e4094982b493f3c9400-94d69870d6fc4801-01`

Results:

| Check | Status | Result |
| --- | ---: | --- |
| L2 store | 200 | `fact_id=8254f45d-4563-40e0-8aae-67c7a91cbf70` |
| L2 retrieve | 200 | `status=success` |
| L3 assimilate | 201 | `episode_id=ep-7c4d91e3` |
| L3 query | 200 | `status=success` |
| L4 finalize | 201 | `knowledge_id=kd-0032ee5e` |

The previous L3 `Vector dimension error` was not reproduced.

## MCP HTTP Evidence

Live read contract:

```bash
YAAM_MCP_RUN_LIVE_HTTP_CONTRACT=1 \
YAAM_MCP_HTTP_URL=http://192.168.107.187:8003/mcp \
./.venv/bin/pytest tests/mcp/test_streamable_http_contract.py::test_mcp_streamable_http_live_read_contract_is_env_gated -v
```

Result: `1 passed`

Temporary allowlisted MCP write/lifecycle window:

- `session_id`: `mcp-runtime-hardening-7932f91a31`
- `task_id`: `mcp-task-7932f91a31`

Results:

| Tool | Status | Created ID |
| --- | --- | --- |
| `yaam.l2.store_fact` | success | `ba4e171a-56f9-400b-8ba7-567de9fffd3b` |
| `yaam.l3.assimilate_episode` | success | `ep-8edc9279` |
| `yaam.l4.finalize_artifact` | success | `kd-3377b3e7` |

After the write window, `yaam-mcp` was restarted without the override. A safe
mode write attempt returned:

```json
{"is_error": true, "code": "permission.writes_disabled"}
```

## Observability

Phoenix project `mlm-mas-dev` exported `79` spans:

- REST spans for `/health`, L2, L3 assimilate/query, and L4 finalize were present.
- MCP spans for health, CIAR resource, prompt read, L2/L3/L4 tools were present.
- Phoenix ingest logs showed repeated `POST /v1/traces 200 OK`.
- Two ERROR spans were expected `YAAMPermissionError` events from write-denial checks.

Recent YAAM logs did not show L3 vector dimension errors. `yaam-mcp` logs did
show `anyio.ClosedResourceError` Traceback entries from the MCP SDK Streamable
HTTP message router when client sessions closed after successful calls. This did
not crash the service, but should be tracked as log-noise/operability follow-up.

## Docker Cache Evidence

Before cleanup:

- YAAM images had previously been around `27.6 GB` each.
- Rebuilt YAAM images after Dockerfile cache cleanup are around `10.3 GB` each.
- `docker system df` still reported Build Cache `65.38 GB` reclaimable.

Cleanup:

- `docker builder prune --filter until=24h --force` did not reclaim the large
  BuildKit cache on this host.
- `docker buildx prune --all --filter until=24h --force` also did not reclaim it.
- After validation, `docker buildx prune --all --force` removed the unused
  BuildKit cache.

After cleanup:

- `docker system df`: Build Cache `0B`
- Containers remained running.
- `GET /health` remained HTTP 200.

## Follow-Up Items

| Priority | Area | Item |
| --- | --- | --- |
| P1 | Docker | Split production dependencies so API/MCP runtime does not install local `sentence-transformers`, Torch, Triton, and CUDA wheels when OpenRouter embeddings are the production path. This requires explicit dependency/lockfile approval. |
| P2 | MCP HTTP logs | Investigate whether MCP SDK Streamable HTTP `anyio.ClosedResourceError` on client close can be downgraded, suppressed, or avoided through session handling. |
| P2 | Observability | Move Phoenix tracing from `SimpleSpanProcessor` to `BatchSpanProcessor` for production-like runtime. |
| P3 | Compose | Remove obsolete Compose `version` field to silence startup warnings. |

