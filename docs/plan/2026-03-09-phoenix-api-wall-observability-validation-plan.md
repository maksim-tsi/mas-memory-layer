# Phoenix API Wall Observability Validation Plan

**Status:** Draft  
**Date:** March 9, 2026  
**Audience:** Maintainers, benchmark operators, observability owners  
**Related:** `docs/ADR/009-decoupling-benchmark-api-wall.md`, `docs/specs/spec-goodai-agent-variant-evaluation-protocol.md`, `docs/plan/2026-02-22-provider-parity-experiment-matrix.md`, `benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml`

## 1. Objective

This document defines a validation plan for Arize Phoenix monitoring and observability across the YAAM API Wall and the GoodAI benchmark integration. The immediate goal is to determine, on host `skz-dev-lv`, whether Gemini, Groq, and Mistral calls are traceable in Phoenix both when invoked directly through the API Wall and when invoked indirectly through the benchmark runner. The broader architectural goal is to assess whether Phoenix ownership should be relocated from the LLM client layer to the OpenAI-compatible `POST /v1/chat/completions` ingress boundary.

The plan is intentionally constrained to one benchmark example per provider. The benchmark configuration selected for this purpose is `benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml`, which executes a single `prospective_memory` example with `dataset_examples: 1` and `memory_span: 32000`.

## 2. Current Repository State

### 2.1 Two Poetry Environments

The repository is intentionally split into two Python environments:

1. The root YAAM environment in the repository root, targeting Python `>=3.12,<3.14`.
2. The GoodAI benchmark environment in `benchmarks/goodai-ltm-benchmark/`, targeting Python `>=3.11,<3.13`.

This split is materially relevant for Phoenix analysis because only the root environment declares Phoenix and OpenInference dependencies, while the benchmark environment acts primarily as an HTTP client when it is operated in `mas-remote` mode.

### 2.2 Phoenix Initialization Today

Current Phoenix initialization is centered in `src/llm/client.py`. The file:

- checks `PHOENIX_COLLECTOR_ENDPOINT`,
- registers OpenTelemetry through `phoenix.otel.register(...)`,
- enables `auto_instrument=True`,
- and applies explicit `GoogleGenAIInstrumentor` instrumentation when `google.genai` is importable.

This design yields provider-centric instrumentation, but it does not make the API Wall the clear tracing owner. Consequently, request-level benchmarking evidence can be partially decoupled from tracing evidence, especially when requests traverse `src/server.py` and benchmark-originated context is not promoted into an ingress span.

### 2.3 API Wall Behavior Today

The API Wall in `src/server.py` already provides several observability primitives:

- `POST /v1/chat/completions` as the primary benchmark-facing data-plane endpoint,
- `X-Session-Id` for session isolation,
- optional `traceparent` header intake,
- and response metadata including `yaam_session_id`, `client_session_id`, `yaam_configured_model`, `llm_ms`, `storage_ms_pre`, `storage_ms_post`, and aggregate `storage_ms`.

These features provide strong correlation hooks, but they do not yet constitute a complete request-level tracing strategy. The API Wall records metadata; it does not presently appear to create a dedicated request span that becomes the parent of all downstream work.

### 2.4 Benchmark Invocation Modes

The GoodAI benchmark runner supports two materially different classes of execution:

1. Direct provider sessions such as `gemini`, `groq`, and `mistral`.
2. Remote API Wall execution via `mas-remote`.

Only the second mode is suitable for Phoenix validation of YAAM. Direct benchmark provider sessions bypass the root YAAM process and therefore do not validate the tracing path implemented in `src/llm/client.py` and `src/server.py`.

### 2.5 Potential Gemini Compatibility Concern

The root environment pins `google-genai = "1.2.0"` in `pyproject.toml`. The lockfile metadata for `openinference-instrumentation-google-genai` indicates an extras relationship that targets substantially newer `google-genai` versions. This mismatch does not prove runtime incompatibility by itself, but it provides a credible explanation for the observed phenomenon in which Gemini calls succeed while Google GenAI tracing is degraded or unavailable.

## 3. Architectural Assessment

### 3.1 Recommended Ownership Model

If Phoenix is to be deepened, the recommended architecture is to make `src/server.py` the tracing owner for `POST /v1/chat/completions`, while retaining `src/llm/client.py` as the provider instrumentation layer.

Under this model:

1. The API Wall creates an ingress span per request.
2. The ingress span carries benchmark-facing identifiers such as session id, agent type, agent variant, configured model, and latency decomposition.
3. The LLM client contributes provider-level child spans and provider-specific attributes.
4. Trace context propagation becomes explicit and stable at the HTTP boundary defined by ADR-009.

This separation is preferable to the current arrangement because it distinguishes request observability from provider SDK observability. If Gemini tracing fails while ingress tracing remains healthy, the failure can be classified precisely as a Google/OpenInference integration issue rather than as a Phoenix platform failure.

### 3.2 Why API Wall Integration Is Superior

An API-Wall-first integration provides the following advantages:

- It aligns tracing ownership with the boundary defined in `docs/ADR/009-decoupling-benchmark-api-wall.md`.
- It enables a unified observability model for benchmark-originated and non-benchmark-originated requests.
- It allows direct correlation between benchmark artifacts and Phoenix traces, even if provider-specific SDK instrumentation is partial.
- It reduces ambiguity when diagnosing mixed symptoms such as successful LLM responses with incomplete tracing.

### 3.3 Risks of Preserving the Current Ownership Model

If tracing remains conceptually centered in `src/llm/client.py`, several ambiguities remain:

- Phoenix may capture provider spans without a strong request root span.
- Benchmark evidence may need to be reconstructed indirectly from timestamps and session metadata rather than from an explicit trace tree.
- Duplicate or competing tracer-provider initialization remains harder to reason about.
- Symptoms such as the reported Gemini warning may appear to be benchmark problems even when they are not.

## 4. Validation Scope

The validation matrix covers three providers and two execution modes.

### 4.1 Providers

- Gemini using `gemini-3-flash-preview`
- Groq using `openai/gpt-oss-120b`
- Mistral using `mistral-large-latest`

These model choices are selected to remain aligned with the repository’s current provider wiring. In particular, `src/llm/client.py` contains explicit routing for `openai/gpt-oss-120b`, while other candidate Groq models are not mapped as cleanly for wrapper-driven validation.

### 4.2 Modes

1. Direct API Wall request, without the benchmark runner.
2. GoodAI benchmark request via `mas-remote`, using `benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml`.

This yields a six-cell validation matrix:

| Provider | Direct API Wall | GoodAI `mas-remote` |
|---|---|---|
| Gemini | Required | Required |
| Groq | Required | Required |
| Mistral | Required | Required |

## 5. Invariants

Unless explicitly noted otherwise, all runs in this plan MUST preserve the following invariants:

- identical host context: `skz-dev-lv`,
- root API Wall process launched from the root YAAM environment,
- benchmark runner launched from the benchmark Poetry environment,
- `mas-remote` used for all benchmark-side Phoenix validation,
- unique `PHOENIX_PROJECT_NAME` and benchmark `--run-name` values per provider run,
- identical benchmark config file: `benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml`,
- and identical agent identity unless an agent-type experiment is explicitly introduced.

## 6. Detailed Execution Plan

### Phase 0. Host and Environment Preflight

1. Confirm host context with `uname -a`, `hostname`, and `pwd`.
2. Verify the root interpreter path required by repository instructions: `/home/max/code/mas-memory-layer/.venv/bin/python`.
3. Verify the benchmark interpreter in `benchmarks/goodai-ltm-benchmark/.venv/`.
4. Record installed package versions in the root environment for:
   - `google-genai`,
   - `arize-phoenix`,
   - `openinference-instrumentation-google-genai`,
   - `opentelemetry-exporter-otlp`.
5. Record installed package versions in the benchmark environment for:
   - `google-genai`,
   - and whether Phoenix-related packages are absent, as expected.

This phase establishes the evidentiary basis for later interpretation of any Gemini-specific tracing anomaly.

### Phase 1. Phoenix Collector Readiness

1. Execute `scripts/check_phoenix_connectivity.sh` from the root repository.
2. Confirm the HTTP UI endpoint and OTLP HTTP collector endpoint are reachable.
3. Confirm the intended values for:
   - `PHOENIX_COLLECTOR_ENDPOINT`,
   - `PHOENIX_PROJECT_NAME`,
   - and, if used, `AGENT_TYPE`.

If Phoenix is not reachable, all subsequent failures MUST be classified as infrastructure blockage rather than provider or benchmark failures.

### Phase 2. Direct API Wall Validation

For each provider:

1. Start or restart the API Wall from `src/server.py` in the root environment.
2. Set `MAS_MODEL` to the provider-specific model.
3. Enable Phoenix through `PHOENIX_COLLECTOR_ENDPOINT` and a unique `PHOENIX_PROJECT_NAME`.
4. Send a trivial `POST /v1/chat/completions` request with a unique `X-Session-Id`.
5. Record:
   - HTTP response payload,
   - response metadata,
   - API Wall logs,
   - and Phoenix trace evidence.

This phase validates that Phoenix can observe the full YAAM request path without benchmark involvement.

### Phase 3. Provider Readiness Gates

The following scripts SHOULD be used as readiness gates only:

- `scripts/test_gemini.py`
- `scripts/test_groq.py`
- `scripts/test_mistral.py`

These scripts validate credentials and basic provider availability. They do not validate API Wall tracing and MUST NOT be treated as conclusive Phoenix tests.

### Phase 4. GoodAI Benchmark Validation

For each provider:

1. Keep the benchmark on `mas-remote` so that all benchmark traffic traverses the API Wall.
2. Use `benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml` unchanged for dataset scope.
3. Override `--run-name` with a provider-specific value that includes provider id, model id, and timestamp.
4. Point `AGENT_URL` to the active API Wall endpoint.
5. Run a single benchmark example.
6. Preserve benchmark outputs, especially:
   - `turnmetrics-mas-remote.jsonl`,
   - `runstats-mas-remote.json`,
   - and the run result directory.

This phase validates whether Phoenix still captures and correlates requests when they originate from the separate benchmark environment.

### Phase 5. Correlation and Classification

For each benchmark run, correlate:

- benchmark session identifiers,
- API Wall response metadata,
- request timestamps,
- latency decomposition,
- and Phoenix traces.

The expected correlation keys are:

- `client_session_id`,
- `yaam_session_id`,
- `yaam_configured_model`,
- `llm_ms`,
- `storage_ms`,
- and run timestamps.

The benchmark client currently captures response metadata in `benchmarks/goodai-ltm-benchmark/model_interfaces/remote_agent.py`. This is sufficient for operational correlation even if explicit `traceparent` propagation is not yet fully exploited.

## 7. Evidence Requirements

Each provider-mode cell in the matrix MUST produce the following evidence:

1. The exact command invocation.
2. The YAAM git revision.
3. The benchmark revision or current working revision.
4. The API response metadata.
5. The benchmark artifacts, if applicable.
6. A Phoenix trace or span screenshot or an equivalent exported trace record.
7. The classification outcome: Pass, Warn, or Fail.

## 8. Outcome Definitions

### Pass

A run is classified as Pass when:

- the provider call succeeds,
- the API Wall returns expected metadata,
- Phoenix records a corresponding trace or span,
- and the provider/model/session can be identified with sufficient confidence.

### Warn

A run is classified as Warn when:

- the provider call succeeds,
- but Phoenix observability is degraded.

Examples include:

- ingress trace present but provider span missing,
- generic spans without useful provider detail,
- benchmark artifacts present but trace correlation weak,
- or a reproducible Gemini-specific instrumentation warning with otherwise successful request execution.

### Fail

A run is classified as Fail when:

- the provider call fails,
- Phoenix is unreachable,
- no corresponding trace can be found,
- or the benchmark path does not traverse the traced YAAM process.

## 9. Analytical Interpretation of the Reported Gemini Symptom

The reported observation is internally coherent: Gemini-backed agents can function while Phoenix reports that Google GenAI instrumentation cannot start. This is plausible under the present architecture for at least three reasons.

1. The provider SDK may be operational while OpenInference instrumentation for that SDK is version-incompatible.
2. Phoenix may be initialized successfully at the platform level while the Google-specific instrumentor fails.
3. Request-level observability may be under-specified because the request ingress boundary does not yet clearly own tracing.

Accordingly, reproduction of the warning SHOULD be interpreted as a targeted observability defect until evidence shows broader platform failure.

## 10. Recommended Next Design Step

If implementation work is approved, the preferred next step is to refactor tracing so that:

1. `src/server.py` creates and owns the request-level span for `POST /v1/chat/completions`.
2. `src/llm/client.py` retains provider instrumentation and span enrichment.
3. Benchmark-originated context is propagated into Phoenix from the API Wall boundary.
4. The response metadata may optionally expose `trace_id` for stronger benchmark-to-Phoenix joins.

This architecture would preserve the benchmark’s black-box posture while providing more rigorous and interpretable observability.

## 11. Files of Primary Interest

- `src/server.py`
- `src/llm/client.py`
- `src/evaluation/agent_wrapper.py`
- `pyproject.toml`
- `poetry.lock`
- `scripts/check_phoenix_connectivity.sh`
- `scripts/test_gemini.py`
- `scripts/test_groq.py`
- `scripts/test_mistral.py`
- `tests/integration/test_llmclient_real.py`
- `benchmarks/goodai-ltm-benchmark/pyproject.toml`
- `benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml`
- `benchmarks/goodai-ltm-benchmark/runner/run_benchmark.py`
- `benchmarks/goodai-ltm-benchmark/model_interfaces/remote_agent.py`
- `benchmarks/goodai-ltm-benchmark/runner/turn_metrics.py`
- `benchmarks/goodai-ltm-benchmark/docs/visibility-analysis.md`
- `docker-compose.yml`
- `Dockerfile`

## 12. Scope Exclusions

This document does not itself authorize:

- dependency upgrades,
- tracer refactors,
- instrumentation package changes,
- or benchmark code modifications.

Those actions are follow-up implementation tasks and should be approved separately if the validation exercise confirms a defect.