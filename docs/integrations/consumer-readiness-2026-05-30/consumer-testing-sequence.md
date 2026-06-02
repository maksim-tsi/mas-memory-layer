# Consumer Testing Sequence

**Purpose:** run one YAAM consumer project at a time against the shared lab endpoint.  
**Runtime host:** `skz-data-lv` via `ssh skz-data-local`.  
**Consumer execution host:** MacBook on the same local network.

## Decision

Yes, consumer testing should be sequential in the current configuration. One YAAM service instance
serves one `YAAM_PROJECT_ID`. Running multiple consumers at the same time through the same REST/MCP
ports would mix project evidence unless each consumer receives its own YAAM instance, ports, and
Phoenix project.

The documented and recently validated runtime is `skz-data-lv`, not `skz-dev-lv`. If YAAM must run
on `skz-dev-lv`, create a separate deployment gate first: verify DBMS connectivity to `skz-data-lv`,
publish dedicated REST/MCP ports, run the same smoke checks, and update these instructions with the
new endpoint.

## Project Windows

| Order | Consumer project | `YAAM_PROJECT_ID` | Phoenix project |
| --- | --- | --- | --- |
| 1 | `agentic-scm-tra26` | `agentic-scm-tra26` | `mlm-mas-dev-consumer-agentic-scm-tra26-20260530` |
| 2 | `scm-skill-factory` | `scm-skill-factory` | `mlm-mas-dev-consumer-scm-skill-factory-20260530` |
| 3 | `scm-cognitive-sandwich` | `scm-cognitive-sandwich` | `mlm-mas-dev-consumer-scm-cognitive-sandwich-20260530` |

## Operator Preflight For Each Window

1. Confirm YAAM repo state on the runtime host:

```bash
ssh skz-data-local 'cd <remote-yaam-checkout> && git status --short'
ssh skz-data-local 'cd <remote-yaam-checkout> && git log -1 --oneline'
```

2. Start the interface containers for the selected project namespace:

```bash
ssh skz-data-local '
  cd <remote-yaam-checkout> &&
  YAAM_PROJECT_ID=<project-id> \
  YAAM_MCP_DOMAIN_PACKS=auto \
  PHOENIX_PROJECT_NAME=<phoenix-project> \
  docker compose \
    -f docker-compose.interface.yml \
    -f docker-compose.skz-data.yml \
    up -d --build mas-agent yaam-mcp
'
```

3. Keep MCP mutating and lifecycle tools disabled by default. Enable them only in a short synthetic
   write window coordinated with the consumer.

   `YAAM_MCP_DOMAIN_PACKS=auto` enables the Skill Factory read-only MCP domain
   pack only for `YAAM_PROJECT_ID=scm-skill-factory`; other consumers keep the
   generic MCP discovery surface.

4. Verify the shared endpoints from the MacBook:

```bash
curl -fsS http://192.168.107.187:8002/health
YAAM_MCP_RUN_LIVE_HTTP_CONTRACT=1 \
YAAM_MCP_HTTP_URL=http://192.168.107.187:8003/mcp \
./.venv/bin/pytest tests/mcp/test_streamable_http_contract.py::test_mcp_streamable_http_live_read_contract_is_env_gated -v
```

5. Review interface logs before handoff:

```bash
ssh skz-data-local '
  cd <remote-yaam-checkout> &&
  docker compose \
    -f docker-compose.interface.yml \
    -f docker-compose.skz-data.yml \
    logs --tail 160 mas-agent yaam-mcp
'
```

Do not print `.env` contents or secrets while preparing a window.

## Consumer Handoff

For each project, give the consumer:

- REST base URL: `http://192.168.107.187:8002`
- MCP Streamable HTTP URL: `http://192.168.107.187:8003/mcp`
- Its project-specific instruction file in this directory.
- The report path and naming convention from `README.md`.

Consumers should use realistic synthetic data, unique `session_id` and `task_id` values, and W3C
`traceparent` when available.

L3 assimilation can legitimately take tens of seconds because it uses provider
API embeddings plus OpenRouter `tencent/hy3-preview` generation with an
8192-token output budget and a 120-second provider timeout. Record latency in
the report, but do not fail readiness only because L3 is slower than a
single-digit-second smoke check.

## After Each Window

1. Collect the consumer report under `reports/`.
2. Export or inspect Phoenix evidence for the project-specific Phoenix project.
3. Review `mas-agent` and `yaam-mcp` logs for Tracebacks, unexpected 5xx responses, provider
   failures, Qdrant dimension errors, Typesense schema/search errors, and OpenInference warnings.
4. Add findings to `docs/integrations/consumer-readiness-2026-05-28/consumer-readiness-results-register.md`
   or a successor register if created.
5. Restart the endpoint with the next `YAAM_PROJECT_ID` only after the current report is captured.

## Parallel Testing Option

Parallel consumer testing is possible only with separate YAAM instances, for example:

| Consumer | REST port | MCP port | Namespace |
| --- | --- | --- | --- |
| `agentic-scm-tra26` | `8002` | `8003` | `agentic-scm-tra26` |
| `scm-skill-factory` | separate port | separate port | `scm-skill-factory` |
| `scm-cognitive-sandwich` | separate port | separate port | `scm-cognitive-sandwich` |

That is a follow-up deployment task, not the recommended first readiness wave.
