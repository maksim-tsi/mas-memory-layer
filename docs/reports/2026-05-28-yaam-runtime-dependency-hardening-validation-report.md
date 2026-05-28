# YAAM Runtime Dependency Hardening Validation Report

Date: 2026-05-28
Branch: `dev-tests`
Commit: `fb7b793`
Host: local MacBook plus `skz-data-lv`

## Summary

Production YAAM runtime was hardened by moving local SentenceTransformer/Torch/CUDA dependencies into the optional `local-embeddings` Poetry group. The production REST/MCP image now keeps Qdrant integration through `qdrant-client` and API-based embeddings, while the legacy/offline `QdrantVectorStore` path remains available with `poetry install --with local-embeddings`.

MCP Streamable HTTP logging was also narrowed so the benign `anyio.ClosedResourceError` emitted on normal client session close is suppressed without hiding unrelated transport/runtime exceptions.

## Local Validation

| Check | Result |
| --- | --- |
| `./.venv/bin/ruff check .` | passed |
| `git diff --check` | passed |
| `./.venv/bin/pytest tests/storage/test_vector_store_client_optional.py tests/mcp/test_server.py::test_create_mcp_server_configures_streamable_http_transport tests/mcp/test_server.py::test_streamable_http_closed_resource_filter_is_narrow tests/mcp/test_server.py::test_streamable_http_server_installs_closed_resource_filter_once -v` | 5 passed |
| `./.venv/bin/pytest tests/mcp/ -v` | 23 passed, 3 skipped |
| `./.venv/bin/pytest tests/api/test_v2_router_ciar.py tests/storage/test_vector_store_client_optional.py -v` | 12 passed |
| `./.venv/bin/pytest tests/ -v` | 729 passed, 142 skipped |

Dependency group check:

- `sentence-transformers`, `torch`, `transformers`, `triton`, and `nvidia-cublas-cu12` are assigned to `local-embeddings`.
- `poetry show --only main` no longer includes the local embedding/Torch/CUDA stack.
- `qdrant-client` remains in main dependencies.

## Remote Runtime Validation

Remote checkout on `skz-data-lv` was fast-forwarded to `fb7b793` and interface services were rebuilt:

- `mas-agent`: `0.0.0.0:8002 -> 8080`
- `yaam-mcp`: `0.0.0.0:8003 -> 8081`

Docker evidence after rebuild:

| Item | Result |
| --- | --- |
| `yet-another-agents-memory-mas-agent:latest` | 660 MB |
| `yet-another-agents-memory-yaam-mcp:latest` | 660 MB |
| Docker images total | 5.566 GB |
| Build cache | 718.6 MB |

Production container import probe:

```json
{
  "fastapi": true,
  "mcp": true,
  "openai": true,
  "qdrant_client": true,
  "sentence_transformers": false,
  "torch": false,
  "transformers": false
}
```

## REST E2E

Endpoint: `http://192.168.107.187:8002`

| Check | Result |
| --- | --- |
| `GET /health` | HTTP 200, status `ok` |
| `POST /v2/memory/l2/facts` store | success, fact created |
| `POST /v2/memory/l2/facts` retrieve | success, synthetic fact retrieved |
| `POST /v2/memory/l3/assimilate` | success, episode `ep-06917b38` |
| `POST /v2/memory/l3/query` | success |
| `POST /v2/memory/l4/finalize` | success, knowledge document `kd-8493ba88` |

The previous L3 vector dimension failure was not reproduced.

## MCP HTTP Validation

Endpoint: `http://192.168.107.187:8003/mcp`

| Check | Result |
| --- | --- |
| live Streamable HTTP read contract | passed |
| `yaam.health.check` | returned healthy/degraded/unavailable-compatible structured payload |
| `yaam://config/ciar` | readable |
| `yaam.prompt.memory_inspection` | readable |
| default write posture | `yaam.l2.store_fact` denied with `permission.writes_disabled` |
| session-close log noise | no `ClosedResourceError` / `Error in message router` noise observed after smoke tests |

## Qdrant Validation

| Collection | Status | Vector Size | Points |
| --- | --- | ---: | ---: |
| `episodes_qwen_v2` | green | 4096 | 315 |
| `episodes_v2` | green | 4096 | 3 |

Runtime configuration points L3 at `episodes_qwen_v2`, preserving Qdrant as the production L3 vector store while removing the local embedding model dependency from the production image.

## Residual Follow-Ups

| Priority | Category | Finding | Suggested Action |
| --- | --- | --- | --- |
| P2 | observability | OpenInference instrumentation logs warnings for Google GenAI import and GROQ enum support during startup. Runtime remains healthy. | Decide whether to disable unsupported instrumentation paths or pin/update instrumentation packages. |
| P2 | storage / observability | MCP health/read logs still show existing Typesense adapter tracebacks: `object dict can't be used in 'await' expression` in health check and `422 Unprocessable Entity` for search sort by `usefulness_score`. | Triage separately with explicit mechanism-layer authorization because this is in `src/storage/`. |
| P3 | Docker | Production image is now much smaller, but still installs build tools and Poetry at runtime. | Next hardening step: multi-stage Dockerfile and wheel/runtime split. |

