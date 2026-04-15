# YAAM Forensic Audit: Arize Phoenix + OpenTelemetry Integration (2026-04-15)

This report treats “Phoenix is integrated” as a hypothesis and verifies the *actual* code paths and dependencies present in the repository as of **2026-04-15**.

## Executive Summary

### 1) Integration Status

**Status: Partially integrated.**

- **Dependencies are present and installed** (Phoenix + OTel + OpenInference instrumentation for Google GenAI). See `pyproject.toml` and `requirements.txt` plus the local `.venv` package inventory.
- **A real Phoenix/OTel initialization path exists**, but it is **disabled by default** unless `PHOENIX_COLLECTOR_ENDPOINT` is set.
- **Tracing root span + W3C propagation is implemented for the v1 API Wall endpoint** via an inbound `traceparent` header.
- **The v2 API payload `metadata.trace_id` is *not* used to set OpenTelemetry context**; it is only used for log decoration, so v2 requests do not currently “link up” to an existing trace via that field.

## Step 1 — Dependency Check (Declared + Installed)

### Declared dependencies (repo files)

Phoenix/OTel dependencies are declared in:

- `pyproject.toml`:
  - `arize-phoenix` (observability SDK) (`pyproject.toml:38`)
  - `openinference-instrumentation-google-genai` (`pyproject.toml:39`)
  - `opentelemetry-exporter-otlp` (`pyproject.toml:40`)
- `requirements.txt` (same intent + comments) (`requirements.txt:59`–`requirements.txt:66`)

### Installed dependencies (local `.venv` verification)

The local repo `.venv` contains the Phoenix/OTel stack (verified via `./.venv/bin/python -m pip show ...` on 2026-04-15):

- `arize-phoenix==12.33.1`
- `arize-phoenix-otel==0.14.0`
- `openinference-instrumentation==0.1.44`
- `openinference-instrumentation-google-genai==0.1.10`
- `opentelemetry-api==1.39.1`
- `opentelemetry-sdk==1.39.1`
- `opentelemetry-exporter-otlp==1.39.1`

Notably, **FastAPI auto-instrumentation packages are not present** in the local `.venv` (e.g., `opentelemetry-instrumentation-fastapi` was not found via `pip show` during this audit), so any FastAPI-level automatic server spans/context extraction must come from YAAM code (or additional deps not currently installed).

## Step 2 — Initialization Audit (Where Phoenix/OTel is actually initialized)

### Phoenix initialization code path (real, conditional)

Phoenix/OTel initialization is implemented in `src/llm/client.py`:

- It is **gated by** `PHOENIX_COLLECTOR_ENDPOINT` and returns early if unset (`src/llm/client.py:35`–`src/llm/client.py:41`).
- When enabled, it registers Phoenix OTel exporter/tracer provider via `phoenix.otel.register(...)` (`src/llm/client.py:56`–`src/llm/client.py:67`).
- It enables `auto_instrument=True` (auto-detect instrumentation hooks) (`src/llm/client.py:66`).
- It also **explicitly instruments Google GenAI** (if `google.genai` is installed) using `GoogleGenAIInstrumentor` (`src/llm/client.py:76`–`src/llm/client.py:88`).

This is a **collector/exporter configuration**, not a Phoenix UI bootstrap. There is **no `px.launch_app()` or equivalent** present in YAAM code (a repository-wide search did not find `px.launch_app`).

### When initialization runs (startup sequence)

Initialization is invoked in two concrete ways:

1) **Module import side-effect**:
   - `ensure_phoenix_instrumentation()` is called at import time (`src/llm/client.py:118`–`src/llm/client.py:120`).

2) **FastAPI lifespan hook (API Wall)**:
   - The API Wall calls `_ensure_api_wall_tracing()` during lifespan startup (`src/server.py:199`–`src/server.py:206`), which calls `ensure_phoenix_instrumentation()` (`src/server.py:121`–`src/server.py:128`).

### Where the Phoenix collector endpoint “points”

The code itself does not hard-code `192.168.107.172:6006`. Instead it requires `PHOENIX_COLLECTOR_ENDPOINT` (`src/llm/client.py:35`).

However, the repo includes an ops script that defaults to the dev node IP/ports and prints the exact env var to set:

- `scripts/check_phoenix_connectivity.sh` defaults `DEV_NODE_IP=192.168.107.172` and `PHOENIX_PORT=6006` (`scripts/check_phoenix_connectivity.sh:6`–`scripts/check_phoenix_connectivity.sh:16`)
- It suggests `PHOENIX_COLLECTOR_ENDPOINT=http://${PHOENIX_HOST}:${PHOENIX_HTTP_PORT}/v1/traces` (`scripts/check_phoenix_connectivity.sh:60`–`scripts/check_phoenix_connectivity.sh:63`)

## Step 3 — Instrumentation & Trace Propagation

### A) Do LLM calls get instrumented automatically?

What YAAM does today:

- YAAM registers Phoenix OTel with `auto_instrument=True` (`src/llm/client.py:63`–`src/llm/client.py:67`).
- YAAM explicitly instruments **Google GenAI** calls with `GoogleGenAIInstrumentor` (`src/llm/client.py:76`–`src/llm/client.py:88`).
- YAAM does **not** contain code references to `OpenAIInstrumentor` (repo search returned no matches).

What this implies:

- **Gemini / `google.genai` calls are the only clearly supported auto-instrumentation path in-code**.
- Groq/Mistral providers do not create explicit spans themselves (e.g., `src/llm/providers/gemini.py` does not reference `opentelemetry`), so tracing for those providers would require either:
  - additional OpenInference instrumentor packages (not currently declared/installed), or
  - YAAM adding explicit LLM spans (not present today; no `yaam.llm.*` spans exist in `src/`).

### B) Where YAAM creates spans today (policy-layer spans)

YAAM provides a lightweight tracing helper in `src/observability/tracing.py`:

- `start_span(...)` creates a current span and attaches `openinference.span.kind` (`src/observability/tracing.py:37`–`src/observability/tracing.py:52`).

YAAM uses these helpers in:

- Agent turn span (root-ish in agent pipeline):
  - `yaam.agent.run_turn` (`src/agents/memory_agent.py:103`–`src/agents/memory_agent.py:143`)
- Retrieval spans:
  - `yaam.retriever.l2` (`src/memory/unified_memory_system.py:517`–`src/memory/unified_memory_system.py:527`)
  - `yaam.retriever.l3` (`src/memory/unified_memory_system.py:581`–`src/memory/unified_memory_system.py:591`)
  - `yaam.retriever.l4` (`src/memory/unified_memory_system.py:644`–`src/memory/unified_memory_system.py:654`)

These spans will be exported only if Phoenix instrumentation is successfully enabled (see Step 2).

### C) How trace context propagates today

#### v1 API Wall (`/v1/chat/completions`): W3C `traceparent` is supported

The API Wall endpoint accepts an inbound `traceparent` header and extracts an OpenTelemetry context:

- `_extract_parent_context(...)` uses `opentelemetry.propagate.extract` over a `traceparent` carrier (`src/server.py:130`–`src/server.py:139`).
- The request handler starts a span with that extracted parent context (`src/server.py:261`–`src/server.py:270`).

YAAM also returns trace identifiers in response metadata:

- `yaam_trace_id` / `yaam_span_id` are computed from the current span context (`src/server.py:183`–`src/server.py:197`) and added into response metadata (`src/server.py:311`–`src/server.py:327`).

Net effect for v1:

- If a caller supplies a valid `traceparent`, downstream YAAM spans (agent/memory spans) will be children of the API Wall span (assuming Phoenix/OTel is enabled).

#### v2 Memory Gateway (`/v2/memory/*`): `metadata.trace_id` is *not* used for OTel propagation

The v2 API schemas strongly imply a `trace_id` contract:

- v2 request schemas document `metadata` as “Must contain trace_id for Phoenix” (`src/api/v2_schemas.py:12`–`src/api/v2_schemas.py:15`, similarly repeated in other schemas).

But the actual implementation:

- v2 router only *logs* the `trace_id` if present and does not set OpenTelemetry context (`src/api/v2_router.py:23`–`src/api/v2_router.py:30`).
- There is no code in `src/api/v2_router.py` that:
  - extracts `trace_id`,
  - builds a `SpanContext`, or
  - attaches it to the current OTel context.

**Answer to the explicit question:** YAAM does **not** currently know how to read a `trace_id` from v2 API payload metadata and inject it into an active OpenTelemetry context.

## Step 4 — What’s Missing to Make Phoenix Ready for E2E Assertions

This section enumerates concrete missing code/config required for “Phoenix-ready” end-to-end assertions (trace continuity + expected spans), without implementing anything yet.

### 1) Decide the propagation contract for v2

Today, v2 schemas talk about `metadata.trace_id` (`src/api/v2_schemas.py:12`–`src/api/v2_schemas.py:15`) but YAAM only supports W3C propagation via `traceparent` headers in v1 (`src/server.py:130`–`src/server.py:139`).

You likely need one of:

- **Preferred:** move v2 to also accept `traceparent` (and possibly `tracestate`) and use `opentelemetry.propagate.extract` similarly to v1.
- **Alternative:** if you must accept only `metadata.trace_id`, implement a deterministic mapping to an OpenTelemetry remote parent context:
  - validate `trace_id` format (32 hex chars),
  - construct a remote `SpanContext` (requires a span id; you’d need a contract for parent `span_id` or synthesize one),
  - attach it to the current request context before starting YAAM spans.

### 2) Create a request-root span for v2 endpoints

v2 currently has no request-root span analogous to `yaam.api_wall.chat_completions` (`src/server.py:261`–`src/server.py:270`).

To support E2E assertions, v2 should start a predictable span per request (e.g., `yaam.gateway.v2.<route>`) and attach attributes like:

- `yaam.route`, `session.id`, `agent_id`, `task_id`
- `openinference.span.kind` for the gateway span (likely `CHAIN` or `AGENT` depending on semantics)

### 3) Ensure FastAPI-level automatic tracing is either implemented or intentionally avoided

The repo currently relies on:

- manual spans in `src/server.py` for v1, and
- manual policy-layer spans in agent/memory code.

If you want framework-level spans (HTTP server spans, automatic context extraction from headers, etc.), you likely need to add/install and wire an ASGI/FastAPI instrumentor. This is not currently present in the `.venv` during this audit.

### 4) Ensure LLM tracing coverage matches the Phoenix span contract

YAAM’s in-repo spans cover agent + retriever operations (`src/agents/memory_agent.py:103`–`src/agents/memory_agent.py:143`, `src/memory/unified_memory_system.py:517`–`src/memory/unified_memory_system.py:654`).

However, the repo does not currently emit explicit `yaam.llm.*` spans from YAAM code, and only Google GenAI is explicitly instrumented (`src/llm/client.py:76`–`src/llm/client.py:88`).

If E2E assertions expect LLM spans for Groq/Mistral, missing work includes:

- adding the correct OpenInference instrumentor package(s) (dependency change), or
- adding explicit spans around provider calls in YAAM (policy-layer code).

### 5) Make “Phoenix enabled/disabled” externally observable for tests

Phoenix enablement is currently controlled by `PHOENIX_COLLECTOR_ENDPOINT` (`src/llm/client.py:35`–`src/llm/client.py:41`) and depends on tracer provider state (`src/llm/client.py:61`–`src/llm/client.py:75`).

For robust E2E test assertions, you likely need a deterministic indicator (e.g., a health endpoint field or startup log line already emitted at `INFO` when enabled: `src/llm/client.py:69`–`src/llm/client.py:71`).

## Appendix — Key Evidence Map (Files)

- Dependency declarations: `pyproject.toml:37`, `requirements.txt:59`
- Phoenix init: `src/llm/client.py:33`
- API Wall tracing: `src/server.py:121`, `src/server.py:261`
- v2 “trace_id” schema hints: `src/api/v2_schemas.py:12`
- v2 implementation (log-only): `src/api/v2_router.py:23`
- Tracing helper: `src/observability/tracing.py:37`
- Agent span usage: `src/agents/memory_agent.py:103`
- Retriever span usage: `src/memory/unified_memory_system.py:517`
- Ops connectivity script: `scripts/check_phoenix_connectivity.sh:6`

