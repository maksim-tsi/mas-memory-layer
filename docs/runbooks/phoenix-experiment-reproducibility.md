# Runbook: Phoenix Experiment Reproducibility

**Status:** Active  
**Date:** March 10, 2026  
**Audience:** Maintainers, observability owners, benchmark operators  
**Related:** [ADR-013](../ADR/013-phoenix-tracing-strategy.md), [Phoenix span contract](../specs/observability/phoenix-span-contract.md), [Phoenix API Wall live validation plan](../plan/2026-03-09-phoenix-api-wall-observability-validation-plan.md), [Phoenix API Wall progress report](../reports/2026-03-09-phoenix-api-wall-observability-progress-report.md), [scripts/check_phoenix_connectivity.sh](../../scripts/check_phoenix_connectivity.sh)

## 1. Purpose

This runbook defines the repeatable procedure for validating YAAM traces against a live local
Arize Phoenix server, fetching observations programmatically, and preserving enough evidence to
reproduce or compare future runs. It is intended to outlive any single dated validation report.

The procedure covers two levels of validation:

1. API-Wall-rooted tracing, which is already implemented.
2. Deeper retriever and tool spans, which should be exercised after the corresponding runtime
   instrumentation lands.

This document assumes execution from the host machine on which Phoenix is running. When the same
workflow is executed from another container, replace `localhost` with the appropriate container or
network address.

## 2. Validated Local Baseline

The following deployment facts were confirmed on March 10, 2026 and should be re-checked before
any new experiment series:

1. Repository-local `docker compose ps` showed no active services, so Phoenix is not currently
   managed by the repository compose stack.
2. Phoenix is running as a standalone Docker container named `phoenix`.
3. The current image is `arizephoenix/phoenix:latest`.
4. Host port `6006` is published to the Phoenix UI and REST API.
5. The local server responds successfully at:
   - `http://localhost:6006/`
   - `http://localhost:6006/docs`
   - `http://localhost:6006/openapi.json`
6. The server identifies itself with header `x-phoenix-server-version: 12.14.2`.
7. The live OpenAPI schema confirms project-scoped observation endpoints, including:
   - `GET /v1/projects`
   - `GET /v1/projects/{project_identifier}/spans`
   - `GET /v1/projects/{project_identifier}/spans/otlpv1`
   - `GET /v1/projects/{project_identifier}/span_annotations`

These facts are operationally important because they justify using the local OpenAPI surface as the
primary observation interface rather than relying only on manual UI inspection.

## 3. Preconditions

Before starting any Phoenix experiment, confirm the following:

1. The root YAAM environment exists and is used without activation:
   - `./.venv/bin/python`
   - `./.venv/bin/pytest`
   - `./.venv/bin/ruff`
2. The benchmark environment exists if benchmark-mode validation is required:
   - `benchmarks/goodai-ltm-benchmark/.venv/bin/python`
3. `.env` is sourced only into the current shell and is never printed.
4. `PHOENIX_COLLECTOR_ENDPOINT` points to the live local collector.
5. The YAAM API Wall can be started from the root environment.
6. For deep-memory validation, the target request is expected to exercise the retrieval or tool path
   under test.

Load runtime environment values without printing secrets:

```bash
set -a; source .env; set +a
```

## 4. Phoenix Readiness Checks

### 4.1 Docker State

If Phoenix is expected to be managed by the repository compose stack, check that first:

```bash
docker compose ps
```

If Phoenix is managed as a standalone container, use system-wide Docker inspection:

```bash
docker ps --all --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}"
docker inspect phoenix --format 'name={{.Name}} image={{.Config.Image}} status={{.State.Status}} started={{.State.StartedAt}} ports={{json .NetworkSettings.Ports}}'
```

Expected interpretation:

1. A standalone container named `phoenix` is present and `status=running`.
2. Host port `6006` is published.
3. Phoenix may expose internal ports such as `4317/tcp` and `9090/tcp` without publishing them to
   the host.

### 4.2 HTTP and OpenAPI Reachability

The root path is expected to return HTML rather than JSON. This is normal and indicates that the UI
is running.

```bash
curl -I http://localhost:6006/
curl -I http://localhost:6006/docs
curl -I http://localhost:6006/openapi.json
```

Expected interpretation:

1. `GET /` returns `200 OK` with `content-type: text/html`.
2. `GET /docs` returns `200 OK` and confirms the interactive API docs are enabled.
3. `GET /openapi.json` returns `200 OK` and confirms the REST contract is discoverable.

For a lightweight schema signature check:

```bash
curl -s http://localhost:6006/openapi.json | head -c 120
```

Expected prefix:

```text
{"openapi":"3.1.0","info":{"title":"Arize-Phoenix REST API","version":"1.0"},
```

### 4.3 Connectivity Helper

The repository helper may still be used as a quick readiness gate:

```bash
./scripts/check_phoenix_connectivity.sh
```

## 5. Project Naming Convention

Every experiment series should use a unique Phoenix project name to avoid trace collisions across
reruns. The recommended convention is:

```bash
export PHOENIX_PROJECT_NAME="mlm-mas-dev-phoenix-${EXPERIMENT_LABEL}-$(date +%Y%m%d-%H%M%S)"
```

Example:

```bash
export EXPERIMENT_LABEL="retriever-tool-spans"
export PHOENIX_PROJECT_NAME="mlm-mas-dev-phoenix-${EXPERIMENT_LABEL}-$(date +%Y%m%d-%H%M%S)"
```

This convention keeps project names sortable, human-readable, and safe for direct use in the REST
paths confirmed by the local OpenAPI schema.

## 6. Start the API Wall

Run the API Wall from the root YAAM environment without activating a shell.

```bash
set -a; source .env; set +a

PHOENIX_COLLECTOR_ENDPOINT="http://localhost:6006/v1/traces" \
PHOENIX_PROJECT_NAME="$PHOENIX_PROJECT_NAME" \
MAS_AGENT_TYPE=full \
MAS_AGENT_VARIANT=baseline \
MAS_MODEL="gemini-3-flash-preview" \
./.venv/bin/uvicorn src.server:app --host 0.0.0.0 --port 8080
```

Before sending traced traffic, verify API Wall health:

```bash
curl -s http://localhost:8080/health
```

## 7. Direct Experiment Execution

### 7.1 Baseline Request-Level Trace

Use a simple request when the goal is only to validate API-Wall-rooted tracing:

```bash
curl -s -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: phoenix-direct-$(date +%Y%m%d-%H%M%S)" \
  -d '{
    "model": "gemini-3-flash-preview",
    "messages": [{"role": "user", "content": "Return the token OK."}]
  }'
```

Capture and retain the response metadata, especially:

1. `yaam_trace_id`
2. `yaam_span_id`
3. `yaam_session_id`
4. `yaam_configured_model`
5. `llm_ms`
6. `storage_ms`

### 7.2 Retriever and Tool Experiment

After retriever and tool instrumentation lands, use a request that is expected to exercise the
target span path rather than only the API root span. The exact prompt depends on the runtime state
being tested. For example:

```bash
curl -s -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: phoenix-retriever-$(date +%Y%m%d-%H%M%S)" \
  -d '{
    "model": "gemini-3-flash-preview",
    "messages": [{
      "role": "user",
      "content": "Find similar past episodes about customs delays and summarize the reusable lesson."
    }]
  }'
```

For tier-tool validation, choose a `v1-*` agent variant or another runtime configuration that can
actually reach the broader tool pool.

## 8. Observation Retrieval Through the Live OpenAPI

### 8.1 List Available Projects

The local REST API is confirmed to return project data directly:

```bash
curl -s "http://localhost:6006/v1/projects?limit=5"
```

This endpoint returned live data during validation on March 10, 2026, including projects such as
`mlm-mas-dev-phoenix-gemini`, `mlm-mas-dev-phoenix-groq`, and post-patch project variants.

### 8.2 Fetch Project-Scoped Spans

The primary observation path is:

```bash
curl -s "http://localhost:6006/v1/projects/${PHOENIX_PROJECT_NAME}/spans?limit=200&start_time=${START_TIME}&end_time=${END_TIME}"
```

Where `START_TIME` and `END_TIME` are ISO-8601 timestamps, for example:

```bash
export START_TIME="2026-03-10T16:00:00+00:00"
export END_TIME="2026-03-10T16:30:00+00:00"
```

For OTLP-shaped responses, use:

```bash
curl -s "http://localhost:6006/v1/projects/${PHOENIX_PROJECT_NAME}/spans/otlpv1?limit=200&start_time=${START_TIME}&end_time=${END_TIME}"
```

The live local schema confirms the following query parameters for both endpoints:

1. `project_identifier`
2. `cursor`
3. `limit`
4. `start_time`
5. `end_time`

### 8.3 Analyze Retrieved Spans with the OpenAPI Response

The following host-side Python snippet fetches spans and prints the retriever and tool spans of
interest:

```bash
./.venv/bin/python - <<'PY'
import json
import os
import urllib.parse
import urllib.request

project = os.environ["PHOENIX_PROJECT_NAME"]
start_time = os.environ["START_TIME"]
end_time = os.environ["END_TIME"]
params = urllib.parse.urlencode({
    "limit": 200,
    "start_time": start_time,
    "end_time": end_time,
})
url = (
    f"http://localhost:6006/v1/projects/{urllib.parse.quote(project, safe='')}/spans?{params}"
)

with urllib.request.urlopen(url) as response:
    payload = json.load(response)

for span in payload.get("data", []):
    name = span.get("name", "")
    if name.startswith("yaam.retriever.") or name.startswith("yaam.tool."):
        attrs = span.get("attributes", {})
        print(name)
        print("  session.id:", attrs.get("session.id"))
        print("  input.value:", attrs.get("input.value"))
        print("  retrieval.documents present:", "retrieval.documents" in attrs)
PY
```

This is the preferred first-pass analysis path because it is guaranteed by the live local OpenAPI
contract and does not rely on undocumented client behavior.

## 9. Optional `phoenix.client` Workflow

The root YAAM environment currently includes `phoenix.client`, and it can query the local server.
However, its local signature differs from the latest upstream examples. In the validated local
environment:

1. `client.projects.list()` takes no `limit` argument.
2. `client.spans.get_spans()` supports `project_identifier`, `start_time`, `end_time`, `limit`, and
   `timeout`.
3. Newer client examples that assume additional server capabilities, such as some trace-id-specific
   shortcuts, should not be treated as guaranteed on local server version `12.14.2`.

Validated local example:

```bash
./.venv/bin/python - <<'PY'
from phoenix.client import Client

client = Client(base_url="http://localhost:6006")
project = client.projects.list()[0]["name"]
spans = client.spans.get_spans(project_identifier=project, limit=2)

print(project)
for span in spans:
    print(span["name"], span.get("span_kind"))
PY
```

Use the client when it improves local ergonomics, but treat the live OpenAPI schema as the primary
source of truth for reproducible documentation.

## 10. Evidence Checklist

Each experiment record should preserve the following items:

1. The exact API Wall command invocation.
2. The exact Phoenix project name.
3. The client-side `X-Session-Id` used for the request.
4. The API response metadata containing `yaam_trace_id` and `yaam_span_id`.
5. The Docker snapshot showing Phoenix container name, image, status, and port bindings.
6. The Phoenix server version as observed from the HTTP headers.
7. The raw or analyzed spans fetched from the local REST API.
8. The final interpretation of whether the expected span contract was satisfied.

For retriever and tool span validation specifically, verify that the fetched spans contain the
attributes required by the Phoenix span contract, especially:

1. `session.id`
2. `input.value` where the retrieval is query-conditioned
3. `retrieval.documents`
4. the expected YAAM span names such as `yaam.retriever.l3`, `yaam.retriever.l4`, and the relevant
   `yaam.tool.*` names

## 11. Failure Interpretation

Use the following interpretation rules:

1. If Docker shows no Phoenix container and `localhost:6006` fails, the experiment is blocked on
   observability infrastructure.
2. If `GET /` succeeds but `/docs` or `/openapi.json` fails, the UI may still be live but the
   reproducible API workflow should be treated as degraded until the schema is confirmed.
3. If the API Wall response includes `yaam_trace_id` but no matching spans are fetched from Phoenix,
   check project naming and time-window selection first.
4. If request-root spans exist but retriever/tool spans do not, treat that as a runtime
   instrumentation gap rather than a Phoenix availability failure.
5. If the raw OpenAPI path works but a `phoenix.client` example fails, prefer the raw HTTP path and
   record the client incompatibility as version drift rather than a server outage.

## 12. Relationship to Dated Artifacts

This runbook is the reusable operational procedure for future Phoenix experiments. The following
documents remain valuable, but they should be treated as historical context rather than the primary
source of step-by-step execution instructions:

1. [Phoenix API Wall live validation plan](../plan/2026-03-09-phoenix-api-wall-observability-validation-plan.md)
2. [Phoenix API Wall progress report](../reports/2026-03-09-phoenix-api-wall-observability-progress-report.md)

Future reruns should update a new dated report with evidence, while keeping the reusable procedure
in this runbook.