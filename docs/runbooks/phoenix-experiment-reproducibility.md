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
2. Deeper retriever and tool spans, which are now implemented in the policy layer and should be
   validated through the runtime paths that actually execute them.

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
2. The external benchmark environment exists if benchmark-mode validation is required:
   - `../goodai-ltm-benchmark-yaam/.venv/bin/python`
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
MAS_PROMOTION_MODE=barrier \
./.venv/bin/uvicorn src.server:app --host 0.0.0.0 --port 8080
```

Operational guidance:

1. `MAS_PROMOTION_MODE=barrier` is recommended for controlled retriever-evidence experiments so the
   promotion cycle completes within the request rather than racing the next turn.
2. This setting is not required for basic request-root tracing checks.

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

The current request path can now emit the following additional spans when retrieval is exercised:

1. `yaam.agent.run_turn`
2. `yaam.workflow.retrieve`
3. `yaam.retriever.l2`
4. `yaam.retriever.l3`
5. `yaam.retriever.l4`

Use a request that is expected to exercise query-aware retrieval rather than only the API root span.
The exact prompt depends on the runtime state being tested. For example:

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

Expected interpretation:

1. The API Wall request should still return `yaam_trace_id` and `yaam_span_id`.
2. Phoenix should show the API root span plus the agent and retrieval spans above.
3. The retriever spans should carry truthful `input.value` values for the live query.
4. Populated `retrieval.documents` values should only be expected when the runtime path actually has
   retrievable tier content available for that session.

Observed runtime note on March 10, 2026:

1. The current API-Wall endpoint initializes request metadata internally and applies
   `skip_l1_write = true` by default in `src/server.py`.
2. Routine API-Wall validation requests therefore do not persist new L1 content unless the request
   explicitly overrides that metadata.
3. Consequently, a live request can validly produce the expected agent and retriever spans while
   still returning empty `retrieval.documents` payloads unless the target session was populated by
   some other path beforehand.
4. Treat this as a runtime validation boundary, not as evidence that Phoenix retriever
   instrumentation failed.

### 7.2.1 Controlled write-enabled API-Wall experiment

The API Wall now accepts request metadata in the chat-completions payload. This allows a
controlled experiment to enable writes without changing the default benchmark posture.

Example request:

```bash
curl -s -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: phoenix-option-a-$(date +%Y%m%d-%H%M%S)" \
  -d '{
    "model": "gemini-3-flash-preview",
    "messages": [{
      "role": "user",
      "content": "Operational note: pre-submit invoices 48 hours before arrival."
    }],
    "metadata": {
      "skip_l1_write": false,
      "experiment_label": "phoenix-option-a"
    }
  }'
```

Interpretation rules for this controlled mode:

1. The default remains benchmark-safe because requests that omit `metadata.skip_l1_write` still run
   with `skip_l1_write = true`.
2. The controlled override only changes the current request.
3. Promotion evidence still depends on promotion-engine preconditions. In the live March 10 run,
   promotion required enough stored turns to cross the promotion engine's batch threshold.
4. In practice, a single write-enabled turn is not sufficient for rich L2 evidence. A short
   scripted sequence of multiple write-enabled requests may be required before a retrieval turn.
5. When barrier promotion is enabled, the response metadata should be inspected for
   `promotion_status`, `promotion_result`, and context counts before concluding whether Phoenix
   retriever payloads are expected to be populated.

### 7.3 Tier-Tool Span Inventory and Current Validation Boundary

The tier-tool instrumentation now emits the following tool-wrapper spans when the corresponding
tool coroutines are invoked:

1. `yaam.tool.l2_search_facts`
2. `yaam.tool.l3_query_graph`
3. `yaam.tool.l3_search_episodes`
4. `yaam.tool.l4_search_knowledge`

Retrieval-oriented tier tools also emit nested retriever spans:

1. `yaam.retriever.l2` under `yaam.tool.l2_search_facts`
2. `yaam.retriever.l3` under `yaam.tool.l3_search_episodes`
3. `yaam.retriever.l4` under `yaam.tool.l4_search_knowledge`

The graph-query tool currently emits a `TOOL` span only. This is intentional because its output is
structured graph-query data rather than ranked retrieval evidence.

Runtime gating (as of March 10, 2026):

1. The API-Wall-rooted request path always emits request and agent spans when tracing is enabled:
   `yaam.api_wall.chat_completions` and `yaam.agent.run_turn`.
2. Retriever spans (`yaam.retriever.l2/l3/l4`) are emitted from the policy-layer retrieval flow and
   are query-conditioned when `UnifiedMemorySystem.query_memory()` is executed. This is typically
   driven by the user query routed through `MemoryAgent._retrieve_node()`.
3. Tier-tool spans (`yaam.tool.*`) are emitted only when the agent executes a tool loop and invokes
   the corresponding tool coroutine. In the current implementation this requires:
   - a `v1-*` skill-wired agent variant (so the tool pool can be constrained by skills), and
   - a Gemini model path (the current bounded tool loop is Gemini-first).
4. The API Wall defaults `skip_l1_write` to `true`. Therefore, routine same-session “prime then
   retrieve” experiments may validate span structure while still returning empty
   `retrieval.documents` unless the session already contains retrievable content or the request
   explicitly overrides `metadata.skip_l1_write = false`.
5. Even after a controlled write-enabled experiment populates working-memory context, the current
   retriever spans still reflect the `query_memory()` path rather than the `get_context_block()`
   path used to assemble prompt context. This distinction matters when interpreting why response
   quality and `working_facts_count` may improve while `yaam.retriever.l2` still reports an empty
   `retrieval.documents` payload.

### 7.3.1 March 10, 2026 controlled Option A result

The March 10 controlled API-Wall rerun established the following:

1. The API Wall now accepts a per-request `metadata.skip_l1_write = false` override.
2. With `MAS_PROMOTION_MODE=barrier`, the promotion cycle reports completion or timeout directly in
   response metadata.
3. A five-request scripted priming sequence produced `working_facts_count = 10` by the retrieval
   turn, which demonstrates that the API-Wall route can now drive live write-enabled memory state in
   a reproducible Phoenix experiment.
4. The Phoenix trace for that retrieval request still showed an empty `yaam.retriever.l2`
   `retrieval.documents` payload because the current traced retriever path covers `query_memory()`
   while the observed working-memory context was assembled through `get_context_block()`.
5. Therefore, the write-policy experiment is successful, and the remaining gap is now more precise:
   prompt-context retrieval visibility is incomplete even when live write-enabled memory state is
   present.

See the dated evidence artifact:

- [2026-03-10-phoenix-option-a-write-enabled-api-wall-report.md](../reports/2026-03-10-phoenix-option-a-write-enabled-api-wall-report.md)

### 7.3.2 March 10, 2026 successful Option B result

The March 10 live Option B rerun established that normal `v1-*` API-Wall traffic can now emit real
tier-tool spans in Phoenix.

The current successful example trace is recorded in:

- [2026-03-10-phoenix-option-b-live-tool-loop-report.md](../reports/2026-03-10-phoenix-option-b-live-tool-loop-report.md)

That report documents Phoenix project `mlm-mas-dev-phoenix-option-b-live-20260310-211012` and the
successful trace `1b92c7e7816e4226393d6146d6191259`, which confirmed the following live span chain:

1. `yaam.api_wall.chat_completions`
2. `yaam.agent.run_turn`
3. `yaam.workflow.retrieve`
4. `yaam.retriever.l2`
5. `yaam.tool.l2_search_facts`
6. nested `yaam.retriever.l2`

This is the current reference trace for successful normal-request tier-tool observability through
the public API Wall.


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

When validating the current implementation, interpret the returned names as follows:

1. `yaam.agent.run_turn` confirms agent-level execution is now represented explicitly.
2. `yaam.workflow.retrieve` confirms the retrieval phase is grouped under the agent span.
3. `yaam.retriever.l2`, `yaam.retriever.l3`, and `yaam.retriever.l4` confirm tier-specific
   evidence selection.
4. `yaam.tool.*` spans should only be expected when the corresponding tool coroutine is actually
   invoked.

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
4. the expected YAAM span names such as `yaam.agent.run_turn`, `yaam.workflow.retrieve`,
   `yaam.retriever.l3`, `yaam.retriever.l4`, and the relevant `yaam.tool.*` names

## 11. Failure Interpretation

Use the following interpretation rules:

1. If Docker shows no Phoenix container and `localhost:6006` fails, the experiment is blocked on
   observability infrastructure.
2. If `GET /` succeeds but `/docs` or `/openapi.json` fails, the UI may still be live but the
   reproducible API workflow should be treated as degraded until the schema is confirmed.
3. If the API Wall response includes `yaam_trace_id` but no matching spans are fetched from Phoenix,
   check project naming and time-window selection first.
4. If request-root spans exist but agent/retriever spans do not, treat that as a runtime
   instrumentation gap rather than a Phoenix availability failure.
5. If request-root, agent, and retriever spans exist but `yaam.tool.*` spans do not, first confirm
   that the tested runtime path actually invoked a tier tool before treating the absence as a bug.
6. If the raw OpenAPI path works but a `phoenix.client` example fails, prefer the raw HTTP path and
   record the client incompatibility as version drift rather than a server outage.

## 12. Relationship to Dated Artifacts

This runbook is the reusable operational procedure for future Phoenix experiments. The following
documents remain valuable, but they should be treated as historical context rather than the primary
source of step-by-step execution instructions:

1. [Phoenix API Wall live validation plan](../plan/2026-03-09-phoenix-api-wall-observability-validation-plan.md)
2. [Phoenix API Wall progress report](../reports/2026-03-09-phoenix-api-wall-observability-progress-report.md)

Future reruns should update a new dated report with evidence, while keeping the reusable procedure
in this runbook.
