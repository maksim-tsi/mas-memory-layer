# Phoenix API Wall Live Observability Validation Plan

**Status:** Ready for Execution  
**Date:** March 9, 2026  
**Audience:** Maintainers, benchmark operators, observability owners  
**Related:** `docs/ADR/009-decoupling-benchmark-api-wall.md`, `docs/specs/spec-goodai-agent-variant-evaluation-protocol.md`, `docs/plan/2026-02-22-provider-parity-experiment-matrix.md`, `benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml`, `docs/reports/2026-03-09-phoenix-api-wall-observability-progress-report.md`

## 1. Objective

This document defines the live execution procedure for validating Arize Phoenix observability on host `skz-dev-lv` across the YAAM API Wall and the GoodAI benchmark integration. The validation matrix covers three providers, namely Gemini, Groq, and Mistral, and two execution modes, namely direct API Wall calls and benchmark-originated `mas-remote` calls.

The procedure is intentionally ordered so that Phoenix infrastructure is validated before any YAAM or benchmark traffic is exercised. This sequencing is required to prevent misclassification of infrastructure failures as provider or application failures. The benchmark portion remains constrained to one example per provider, using `benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml`, which targets a single `prospective_memory` example with `dataset_examples: 1` and `memory_span: 32000`.

## 2. Operational Context

### 2.1 Environment Topology

The repository uses two distinct Python environments:

1. The root YAAM environment at the repository root, targeting Python `>=3.12,<3.14`.
2. The GoodAI benchmark environment under `benchmarks/goodai-ltm-benchmark/`, targeting Python `>=3.11,<3.13`.

This distinction is operationally significant because Phoenix, OpenTelemetry, and OpenInference instrumentation reside in the root environment, whereas the benchmark environment acts as an HTTP client when executed in `mas-remote` mode.

### 2.2 Validated Host Service Topology on `skz-dev-lv`

Live preflight on `skz-dev-lv` established the following service topology:

1. Arize Phoenix is running locally on `skz-dev-lv` and is reachable via HTTP on port `6006`.
2. Redis is running locally on `skz-dev-lv` and is reachable on port `6379`.
3. PostgreSQL, Qdrant, Neo4j, and Typesense are not intended to be started locally for this validation. Instead, they are hosted on `skz-data-lv` at `192.168.107.187` and were confirmed reachable on ports `5432`, `6333`, `7687`, and `8108`, respectively.

This finding is operationally decisive. On `skz-dev-lv`, the validation procedure SHALL use the existing local Phoenix and Redis services together with the remote data services on `skz-data-lv`. The `docker compose --profile local-db up` path SHALL NOT be used for routine execution on this host because it can conflict with already-running local services, as evidenced by a Redis port collision on `6379` during execution.

### 2.3 Current Tracing Architecture

The implemented tracing model is API-Wall-first:

1. `src/server.py` owns request-level tracing for `POST /v1/chat/completions`.
2. `src/llm/client.py` remains responsible for Phoenix initialization and provider-level instrumentation.
3. API responses expose correlation metadata including `yaam_trace_id`, `yaam_span_id`, `client_session_id`, `yaam_session_id`, `yaam_configured_model`, `llm_ms`, and `storage_ms`.

This architecture materially improves diagnosability because request ingress tracing can now be evaluated independently of provider-specific child instrumentation.

### 2.4 Benchmark Execution Boundary

The GoodAI benchmark supports both direct provider sessions and remote YAAM execution. Only `mas-remote` is valid for the present validation because direct benchmark agents such as `gemini`, `groq`, and `mistral` bypass the YAAM API Wall and therefore cannot serve as Phoenix evidence for YAAM.

### 2.5 Known Gemini Risk

The root environment presently pins `google-genai = "1.2.0"`, while lockfile metadata for `openinference-instrumentation-google-genai` suggests compatibility pressure toward substantially newer `google-genai` versions. This remains a plausible explanation for the historical symptom in which Gemini calls succeed while Google-specific Phoenix instrumentation is degraded.

## 3. Validation Scope

### 3.1 Provider Matrix

The live matrix SHALL use the following provider-model pairs:

- Gemini with `gemini-3-flash-preview`
- Groq with `openai/gpt-oss-120b`
- Mistral with `mistral-large-latest`

These choices align with the routing behavior currently implemented in `src/llm/client.py`.

### 3.2 Execution Modes

Each provider SHALL be evaluated in two modes:

1. Direct API Wall request without benchmark involvement.
2. GoodAI benchmark request through `mas-remote` using `benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml`.

The resulting six-cell validation matrix is shown below.

| Provider | Direct API Wall | GoodAI `mas-remote` |
|---|---|---|
| Gemini | Required | Required |
| Groq | Required | Required |
| Mistral | Required | Required |

## 4. Invariants and Constraints

All runs in this procedure SHALL preserve the following invariants:

- host context remains `skz-dev-lv`,
- Phoenix readiness is validated before any traced provider traffic,
- existing local and remote service availability is verified before any attempt to start replacement containers,
- the root API Wall runs from the root YAAM environment,
- the benchmark runs from the benchmark Poetry environment,
- benchmark-side validation uses `mas-remote` exclusively,
- the benchmark configuration remains `benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml`,
- each provider run uses unique Phoenix project naming, session identifiers, and benchmark `--run-name` values,
- and traced provider runs execute serially because `MAS_MODEL` is process-scoped at API Wall startup.

In addition, `.env` contents SHALL NOT be printed or copied into logs. When runtime values are needed, the procedure MAY load them into the shell environment using `set -a && source .env && set +a`, but only presence checks and derived non-secret connectivity results should be recorded.

Provider readiness scripts may execute in parallel after Phoenix readiness has been confirmed because they do not constitute Phoenix evidence.

## 5. Detailed Execution Procedure

### Phase 0. Host and Phoenix Infrastructure Preflight

The validation SHALL begin with infrastructure readiness on the same machine.

1. Confirm host context with `uname -a`, `hostname`, and `pwd`.
2. Verify the YAAM interpreter path required by repository instructions: `/home/max/code/mas-memory-layer/.venv/bin/python`.
3. Verify the benchmark interpreter path in the benchmark Poetry project without activating shells.
4. Load `.env` into the current shell only for execution purposes using `set -a && source .env && set +a`, without printing any secret values.
5. Confirm that the Phoenix server is running locally by inspecting Docker state first.
6. Identify the Phoenix container using `docker ps` or an equivalent filtered command.
7. If the container is unhealthy or absent, inspect `docker logs` for the Phoenix service before proceeding.
8. Execute `scripts/check_phoenix_connectivity.sh` from the repository root.
9. Confirm that the resolved HTTP UI and OTLP HTTP collector endpoint correspond to the intended local Phoenix instance.
10. Verify that Redis is reachable locally on port `6379`.
11. Verify that PostgreSQL, Qdrant, Neo4j, and Typesense are reachable on `skz-data-lv` before starting the API Wall.
12. Only after the existing topology has been confirmed may any container startup decision be made.

If this phase fails, the entire live validation SHALL be classified as blocked on observability infrastructure.

### Phase 1. Environment and Dependency Gate

After Phoenix infrastructure is confirmed, validate the runtime assumptions.

1. Confirm the presence, but not the values, of `PHOENIX_COLLECTOR_ENDPOINT`, `PHOENIX_PROJECT_NAME`, `REDIS_URL`, `POSTGRES_URL`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, and `MISTRAL_API_KEY`.
2. Record the root-environment versions of:
   - `google-genai`,
   - `arize-phoenix`,
   - `openinference-instrumentation-google-genai`,
   - and `opentelemetry-exporter-otlp`.
3. Record the benchmark-environment version of `google-genai` and confirm that Phoenix-related packages are absent, as expected.
4. Confirm that the loaded `REDIS_URL` and `POSTGRES_URL` align with the validated topology, namely Redis on `skz-dev-lv` and PostgreSQL on `skz-data-lv`.

If a provider key is missing, the corresponding provider branch SHALL be marked blocked before any tracing conclusion is drawn.

### Phase 2. Lock Artifact Naming and Project Separation

Before any live request is issued, establish unique identifiers for each provider branch.

1. Assign a unique Phoenix project name per provider, for example `mlm-mas-dev-phoenix-gemini`, `mlm-mas-dev-phoenix-groq`, and `mlm-mas-dev-phoenix-mistral`.
2. Assign a unique direct-call `X-Session-Id` pattern per provider.
3. Assign a unique benchmark `--run-name` per provider that includes provider id, model id, and timestamp.
4. Preserve the mapping between provider, project name, session identifiers, and run names in the execution notes.

This separation prevents trace and artifact collision across the six validation cells.

### Phase 3. Direct API Wall Validation

The direct validation phase SHALL be executed serially, one provider at a time.

1. Start or restart the API Wall using the root environment and the production serving path defined by `src/server.py` and `Dockerfile`.
2. Export provider-specific values for `MAS_MODEL`, `PHOENIX_COLLECTOR_ENDPOINT`, `PHOENIX_PROJECT_NAME`, `MAS_AGENT_TYPE`, `REDIS_URL`, and `POSTGRES_URL`.
3. Reuse the validated host service topology rather than attempting to replace Redis or PostgreSQL with local Compose services unless an explicit recovery procedure has been approved.
4. Verify `/health` before issuing any traced request.
5. Send one trivial `POST /v1/chat/completions` request with a unique `X-Session-Id`.
6. Capture the HTTP response body and response metadata.
7. Capture API Wall logs for startup and request handling.
8. Inspect Phoenix and confirm the presence of a corresponding request trace rooted at `yaam.api_wall.chat_completions`.

The minimum direct-call evidence SHALL include the following metadata when present:

- `client_session_id`
- `yaam_session_id`
- `yaam_configured_model`
- `llm_ms`
- `storage_ms`
- `yaam_trace_id`
- `yaam_span_id`

### Phase 4. Provider Readiness Gates

Provider readiness checks SHALL be executed only as prerequisites for later benchmark runs.

The relevant scripts are:

- `scripts/test_gemini.py`
- `scripts/test_groq.py`
- `scripts/test_mistral.py`

These scripts validate credentials and basic provider availability. They SHALL NOT be treated as Phoenix evidence because they bypass the API Wall.

### Phase 5. GoodAI Benchmark Validation Through `mas-remote`

Benchmark validation SHALL be executed serially by provider.

1. Keep the benchmark on `mas-remote` so all traffic traverses the active API Wall.
2. Use `benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml` unchanged.
3. Point `AGENT_URL` to the live API Wall endpoint, typically `http://localhost:8080/v1/chat/completions` or the host-local equivalent on `skz-dev-lv`.
4. Run `python -m runner.run_benchmark` from the benchmark Poetry environment with:
   - `-c configurations/mas_single_test.yml`,
   - `-a mas-remote`,
   - `-y`,
   - a provider-specific `--run-name`,
   - and a headless-safe progress mode such as `--progress tqdm`.
5. Preserve the run directory created under `benchmarks/goodai-ltm-benchmark/data/tests/<run_name>/results/mas-remote/`.

Because provider selection is controlled by `MAS_MODEL` on the API Wall, the API Wall SHALL be restarted or reconfigured between Gemini, Groq, and Mistral benchmark runs.

### Phase 6. Correlation and Classification

For each benchmark run, correlate benchmark artifacts, API Wall metadata, and Phoenix traces using:

- `client_session_id`,
- `yaam_session_id`,
- `yaam_configured_model`,
- request and benchmark timestamps,
- `llm_ms`,
- and `storage_ms`.

The benchmark client currently relies on response metadata captured in `benchmarks/goodai-ltm-benchmark/model_interfaces/remote_agent.py`. Explicit `traceparent` propagation is not required for a passing result in the present procedure.

## 6. Evidence Requirements

Each provider-mode cell in the matrix SHALL produce the following evidence:

1. Exact command invocation.
2. YAAM git revision.
3. Benchmark git revision or working revision.
4. API Wall response metadata.
5. Benchmark artifacts, when applicable.
6. Phoenix trace evidence, either as a screenshot or exported trace record.
7. Final classification outcome, namely `Pass`, `Warn`, or `Fail`.

Benchmark artifact collection SHOULD include, when present:

- `run_meta.json`,
- `run_console.log`,
- `turn_metrics.jsonl` or `turnmetrics-mas-remote.jsonl`,
- `runstats.json` or `runstats-mas-remote.json`,
- and the per-example result JSON file.

## 7. Outcome Definitions

### Pass

A run SHALL be classified as `Pass` when:

- the provider call succeeds,
- the API Wall returns expected correlation metadata,
- Phoenix records a corresponding request trace,
- and the provider, model, and session can be identified with sufficient confidence.

### Warn

A run SHALL be classified as `Warn` when:

- the provider call succeeds,
- but Phoenix observability is degraded.

Representative warning conditions include:

- request trace present but provider child span missing,
- generic spans without sufficient provider detail,
- benchmark artifacts present but trace correlation weak,
- or a reproducible Gemini-specific instrumentation warning with otherwise successful request execution.

### Fail

A run SHALL be classified as `Fail` when:

- the provider call fails,
- Phoenix is unreachable,
- no corresponding trace can be found,
- or the exercised path does not traverse the traced YAAM API Wall.

## 8. Analytical Interpretation of the Gemini Symptom

The historical Gemini symptom remains logically consistent with the current system behavior. Gemini-backed requests may succeed while Google-specific Phoenix instrumentation is degraded if the provider SDK is operational but the corresponding OpenInference instrumentation path is version-incompatible or otherwise impaired.

Accordingly, if Gemini reproduces the warning while request-level traces remain healthy, the result SHOULD be interpreted as a provider-instrumentation defect in the root environment rather than as a Phoenix platform failure or a benchmark-path failure.

## 9. Files of Primary Interest

- `src/server.py`
- `src/llm/client.py`
- `src/evaluation/agent_wrapper.py`
- `pyproject.toml`
- `poetry.lock`
- `scripts/check_phoenix_connectivity.sh`
- `scripts/test_gemini.py`
- `scripts/test_groq.py`
- `scripts/test_mistral.py`
- `benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml`
- `benchmarks/goodai-ltm-benchmark/runner/run_benchmark.py`
- `benchmarks/goodai-ltm-benchmark/model_interfaces/remote_agent.py`
- `benchmarks/goodai-ltm-benchmark/runner/turn_metrics.py`
- `docker-compose.yml`
- `Dockerfile`
- `docs/reports/2026-03-09-phoenix-api-wall-observability-progress-report.md`

## 10. Scope Exclusions

This document does not authorize:

- dependency upgrades,
- tracer refactors,
- instrumentation package changes,
- benchmark code modifications,
- or operational recovery work beyond confirming Phoenix readiness.

If the live validation exposes a defect, remediation SHALL be handled as a separate implementation task.