# Phoenix API Wall Observability Progress Report

**Date:** March 9, 2026  
**Status:** Implemented, pending live Phoenix validation  
**Audience:** Maintainers, benchmark operators, observability owners  
**YAAM Commit:** `c09508dfbd5d6da48481f6f3aa839f2787550d74`

## 1. Executive Summary

This report documents progress on the Phoenix observability task for YAAM, with particular emphasis on the OpenAI-compatible API Wall defined in `src/server.py`. The work completed in this iteration establishes request-level tracing ownership at the `POST /v1/chat/completions` boundary while preserving provider-level instrumentation in `src/llm/client.py`.

The principal analytical conclusion is that Phoenix integration is more coherent when the API Wall serves as the tracing boundary and the LLM client remains responsible for provider-specific child instrumentation. This architecture is especially important for the GoodAI benchmark because the benchmark should be validated through `mas-remote` and the API Wall, not through benchmark-local provider sessions that bypass YAAM entirely.

Implementation is complete for the API-Wall-level tracing enhancement. Static validation, targeted unit validation, and full repository test execution all completed successfully. Live validation against a running Phoenix collector and benchmark-originated requests remains outstanding.

## 2. Problem Statement

The task originated from an inconsistency observed during benchmark-related activity: Gemini-backed agents could run successfully while Phoenix reported that Google GenAI instrumentation could not start. This symptom indicated that the provider runtime and the observability layer were only partially coupled.

Repository analysis identified three relevant conditions:

1. Phoenix and OpenInference dependencies exist only in the root YAAM environment, not in the benchmark environment.
2. The benchmark’s direct provider modes (`gemini`, `groq`, `mistral`) bypass the YAAM process and therefore cannot serve as definitive Phoenix validation paths.
3. Existing tracing initialization was centered in `src/llm/client.py`, which instrumented provider SDK activity but did not establish a clear request-level root span at the API Wall ingress.

These conditions made it difficult to determine whether a missing trace was caused by provider instrumentation failure, benchmark topology, or incomplete request-level tracing.

## 3. Analytical Outcome

The completed analysis concluded that the preferred design is an API-Wall-first tracing architecture.

Under this design:

- `src/server.py` owns request-level tracing for `POST /v1/chat/completions`.
- `src/llm/client.py` remains responsible for Phoenix initialization and provider-level span enrichment.
- HTTP ingress metadata such as session identifiers, configured model, agent type, and timing decomposition are attached to the request span.
- Downstream provider spans, when available, become children of the request-level span.

This model is superior because it aligns tracing ownership with the architectural boundary defined by [ADR-009](../ADR/009-decoupling-benchmark-api-wall.md). It also improves interpretability: if a request span exists but a Gemini-specific child span is degraded or absent, the defect can be localized to Google/OpenInference instrumentation rather than to Phoenix as a platform.

## 4. Implemented Changes

### 4.1 API Wall request-level tracing

Implemented request-level tracing logic in:

- `src/server.py`

The following capabilities were added:

1. API Wall startup now explicitly ensures Phoenix tracing is initialized before serving requests.
2. `POST /v1/chat/completions` now opens a request-level span named `yaam.api_wall.chat_completions` when OpenTelemetry is available.
3. The API Wall now extracts inbound `traceparent` headers into an OpenTelemetry parent context when present.
4. The request span is enriched with YAAM-specific attributes, including:
   - route,
   - agent type,
   - agent variant,
   - configured model,
   - request model,
   - client session id,
   - prefixed YAAM session id,
   - turn id,
   - message count,
   - prompt token estimate,
   - and whether `traceparent` was supplied.
5. On success, the request span is further enriched with:
   - provider id,
   - model id,
   - `llm_ms`,
   - `storage_ms_pre`,
   - `storage_ms_post`,
   - aggregate `storage_ms`,
   - completion token estimate,
   - and total token estimate.
6. On failure, the active request span records error attributes and receives error status when OpenTelemetry status types are available.

### 4.2 Trace identifiers in API responses

The API Wall now returns request-level trace identifiers in the response metadata:

- `yaam_trace_id`
- `yaam_span_id`

These values materially improve correlation between Phoenix and benchmark artifacts because the benchmark already captures response metadata through `benchmarks/goodai-ltm-benchmark/model_interfaces/remote_agent.py`.

### 4.3 Focused regression coverage

Added a dedicated unit test in:

- `tests/test_server_api_wall.py`

This test verifies that:

1. the API Wall returns `yaam_trace_id` and `yaam_span_id` in response metadata,
2. request-level span creation occurs with the expected span name,
3. inbound trace context is accepted,
4. and the span is enriched with session, agent, and provider/model attributes.

## 5. Files Added or Modified

### Modified

- `src/server.py`

### Added

- `tests/test_server_api_wall.py`
- `docs/plan/2026-03-09-phoenix-api-wall-observability-validation-plan.md`

## 6. Validation Performed

### 6.1 Static and targeted validation

Executed:

```bash
/home/max/code/mas-memory-layer/.venv/bin/ruff check src/server.py tests/test_server_api_wall.py
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/test_server_api_wall.py -v
```

Results:

- Ruff: passed
- Focused unit test: passed

### 6.2 Full repository test execution

Executed:

```bash
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/ -v
```

Result:

- `593 passed, 108 skipped`

This result indicates that the API Wall tracing change did not introduce observable regressions into the repository test suite.

## 7. Current Scope Completion

### Completed in this iteration

The following task components are complete:

1. repository analysis of Phoenix, provider instrumentation, and benchmark topology,
2. creation of a formal dated validation plan,
3. implementation of API-Wall-level request tracing,
4. exposure of trace identifiers in response metadata,
5. and repository-level verification of the code change.

### Not yet completed

The following validation tasks remain open:

1. live Phoenix collector validation on `skz-dev-lv`,
2. one direct API Wall request per provider against a running Phoenix collector,
3. one benchmark `mas-remote` single-example run per provider using `benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml`,
4. and empirical confirmation that `yaam_trace_id` values correspond to traces visible in Phoenix.

## 8. Known Technical Interpretation

The Gemini symptom remains analytically plausible even after this implementation. A request-level trace can now exist even if Google-specific provider instrumentation is degraded. If that warning reappears, the likely interpretation is no longer a general Phoenix failure. It is more likely to indicate one of the following:

1. a compatibility issue between the root environment’s `google-genai` version and the OpenInference Google instrumentor,
2. a Google-specific instrumentation import gap,
3. or a provider-level tracing limitation beneath an otherwise healthy request trace.

This is a materially better failure mode because the system can now distinguish ingress observability from provider instrumentation quality.

## 9. Recommended Next Actions

The next recommended steps are:

1. Execute a live API Wall request on `skz-dev-lv` with Phoenix enabled and confirm that the response `yaam_trace_id` matches the trace visible in Phoenix.
2. Run one `mas-remote` benchmark example per provider using `benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml` and confirm benchmark-to-Phoenix correlation.
3. If stronger distributed tracing is required, extend `benchmarks/goodai-ltm-benchmark/model_interfaces/remote_agent.py` to propagate `traceparent` explicitly.
4. If Gemini provider spans remain degraded while request spans are healthy, treat that outcome as a focused provider instrumentation defect rather than as a benchmark or API Wall defect.

## 10. Reference Artifacts

- Plan: [2026-03-09-phoenix-api-wall-observability-validation-plan.md](../plan/2026-03-09-phoenix-api-wall-observability-validation-plan.md)
- API Wall implementation: [src/server.py](../../src/server.py)
- Regression test: [tests/test_server_api_wall.py](../../tests/test_server_api_wall.py)
- Benchmark config for live validation: [benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml](../../benchmarks/goodai-ltm-benchmark/configurations/mas_single_test.yml)