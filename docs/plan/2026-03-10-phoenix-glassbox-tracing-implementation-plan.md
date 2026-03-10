# Plan: Phoenix Glass-Box Tracing Implementation for YAAM (OpenInference)

**Status:** Proposed  
**Date:** March 10, 2026  
**Owners:** YAAM maintainers, observability owners  
**Related:** [ADR-013](../ADR/013-phoenix-tracing-strategy.md), [RFC: Phoenix tracing (glass-box)](../RFC/phoenix-tracing-rfc.md), [Spec: Phoenix span contract](../specs/observability/phoenix-span-contract.md)

## 1. Purpose

This plan defines an execution roadmap for implementing Phoenix/OpenInference tracing that makes
YAAM agent cognition observable at a "glass-box" level. The primary target is to expose, within a
single Phoenix trace (or a session-correlated set of traces):

1. agent workflow phases (perceive/retrieve/reason/update/respond),
2. memory reads and writes across L1-L4,
3. and LLM-dependent modules (fact extraction and response generation) plus CIAR scoring decisions.

This plan prioritizes YAAM observability. Evaluation harness artifacts are explicitly secondary and
should not drive architecture or implementation decisions.

## 2. Constraints and invariants

1. The mechanism layer under `src/storage/` is frozen-by-default. This plan MUST NOT require changes
   to `src/storage/`.
2. Dependency changes (`pyproject.toml`, `poetry.lock`) require explicit approval and are excluded
   from baseline scope.
3. The span inventory and required attributes are normative and MUST follow
   [Spec: Phoenix span contract](../specs/observability/phoenix-span-contract.md).
4. Secrets (`.env`, keys) MUST NOT be committed or echoed into logs.

## 3. Deliverables

1. Code changes that emit the contract spans and required OpenInference attributes.
2. A documented content-capture mode policy (`full`, `redacted`, `metadata_only`) applied consistently.
3. A deterministic verification procedure and evidence checklist to validate traces in Phoenix.
4. A follow-up ADR update is not required; ADR-013 should remain stable and reference the spec.

## 4. Workstreams and milestones

### Milestone A: Context and root-span hardening (API wall)

**Goal:** Ensure every request trace has an OpenInference-compatible root span with stable session
correlation and consistent YAAM identifiers.

**Primary files**

1. `src/server.py`

**Implementation steps**

1. Set `openinference.span.kind=CHAIN` on the API wall request span.
2. Set `session.id=<yaam_session_id>` on the API wall request span (and ensure it propagates).
3. Normalize YAAM identifiers on the span as `yaam.*` (e.g., `yaam.turn_id`, `yaam.agent_type`).
4. Ensure error reporting is consistent (`error.type`, `error.message`).

**Acceptance criteria**

1. A request produces a Phoenix trace with `yaam.api_wall.chat_completions` span.
2. The span includes `session.id`, `openinference.span.kind`, and stable `yaam.*` fields.

### Milestone B: Agent-phase spans (MemoryAgent, RAGAgent, FullContextAgent)

**Goal:** Represent the agent cognition path as a semantic span graph aligned with the contract.

**Primary files**

1. `src/agents/memory_agent.py`
2. `src/agents/rag_agent.py`
3. `src/agents/full_context_agent.py`

**Implementation steps**

1. Wrap each `run_turn(...)` in an `AGENT` span (`yaam.agent.run_turn`) with `input.value` and
   `output.value` (subject to content-capture mode).
2. For `MemoryAgent`, emit per-node `CHAIN` spans around `perceive`, `retrieve`, `reason`, `update`,
   `respond`, with `graph.node.*` fields set to reflect the LangGraph node identity.
3. For `RAGAgent` and `FullContextAgent`, emit at minimum:
   - `yaam.workflow.retrieve` (parent of retrieval work)
   - `yaam.workflow.reason` (parent of response generation)
   - `yaam.workflow.update` (if memory writes/lifecycle occur synchronously)

**Acceptance criteria**

1. `MemoryAgent` traces contain `AGENT` and five workflow `CHAIN` spans.
2. `RAGAgent` and `FullContextAgent` traces contain `AGENT` plus retrieval/reason spans.

### Milestone C: L1-L4 retriever spans and evidence payloads

**Goal:** Make retrieval explainable by emitting tier-specific `RETRIEVER` spans with
`retrieval.documents` populated.

**Primary files**

1. `src/memory/unified_memory_system.py`

**Implementation steps**

1. Instrument `get_context_block(...)` to emit:
   - `yaam.retriever.l1` (recent turns)
   - `yaam.retriever.l2` (high-CIAR facts)
2. Instrument `query_memory(...)` to emit:
   - `yaam.retriever.l2`, `yaam.retriever.l3`, `yaam.retriever.l4`
3. Populate `retrieval.documents` using the schema in the contract spec, including tier metadata.
4. Implement a content-capture mode switch:
   - `full`: include `document.content`
   - `redacted`: replace content with a short redaction marker and preserve metadata
   - `metadata_only`: omit content and preserve only ids/scores/metadata

**Acceptance criteria**

1. Retrieval spans exist for each tier accessed by the request.
2. Each retrieval span includes `retrieval.documents` with at least `document.id`.

### Milestone D: Lifecycle and LLM-module spans (promotion/consolidation/distillation)

**Goal:** Make lifecycle operations and LLM-dependent modules inspectable with semantically labeled
spans.

**Primary files**

1. `src/memory/unified_memory_system.py` (cycle entry points)
2. `src/memory/engines/promotion_engine.py`
3. `src/memory/engines/fact_extractor.py`
4. `src/memory/ciar_scorer.py`

**Implementation steps**

1. Emit lifecycle `CHAIN` spans for synchronous lifecycle operations:
   - `yaam.lifecycle.promotion`
   - `yaam.lifecycle.consolidation`
   - `yaam.lifecycle.distillation`
2. Emit `TOOL` span `yaam.ciar.score` for CIAR scoring decisions, including:
   - `yaam.ciar.threshold`
   - structured `output.value` summarizing scores and filtering outcomes (subject to mode).
3. Emit `LLM` span `yaam.llm.fact_extract` around FactExtractor’s LLM path with:
   - `llm.*` attribution fields (provider/model/invocation parameters/token counts) where available
   - structured `output.value` describing extracted facts (subject to mode).

**Acceptance criteria**

1. At least one lifecycle operation is visible as a semantic span when executed synchronously.
2. CIAR scoring and fact extraction are represented as distinct semantic spans when they occur.

### Milestone E: Asynchronous promotion trace correlation (if enabled)

**Goal:** Ensure asynchronous lifecycle traces remain discoverable and attributable to the session
and triggering turn.

**Primary files**

1. `src/agents/memory_agent.py` (promotion scheduling)
2. `src/memory/unified_memory_system.py` and/or lifecycle engines (trace context creation)

**Implementation steps**

1. For asynchronous promotion tasks, start a new trace that sets `session.id` and includes:
   - `yaam.trigger_turn_id`
   - `yaam.promotion_mode`
2. Ensure the trace can be found in Phoenix by filtering on `session.id` (primary) and tags
   (secondary).

**Acceptance criteria**

1. Asynchronous promotion traces are discoverable via `session.id`.
2. The triggering turn id is recorded.

## 5. Verification procedure (evidence)

This plan is considered complete only when evidence can be produced for each milestone.

**Minimum evidence artifacts**

1. A captured Phoenix trace ID and screenshots (or exported trace JSON) showing:
   - API wall root span with `session.id` and `openinference.span.kind`
   - agent `AGENT` span with phase spans
   - at least one `RETRIEVER` span with populated `retrieval.documents`
2. A reproducible request script (curl) that triggers the trace.

**Local validation commands (order)**

1. `./.venv/bin/ruff check .`
2. `./.venv/bin/pytest tests/ -v` (after code changes in `src/`)

If the team decides to add unit tests for tracing, tests SHOULD use an in-memory OpenTelemetry span
exporter and MUST not require network access. Test changes are out-of-scope for this plan unless
explicitly authorized.

## 6. Risks and mitigations

1. **Trace noise and overhead:** Apply sampling policies and avoid large payloads by default; rely on
   content-capture modes and document truncation.
2. **Privacy and sensitive data:** Default to `redacted` or `metadata_only` outside controlled
   development environments; treat `full` as explicitly opt-in.
3. **Provider instrumentation gaps:** Prefer auto-instrumentation where available; do not introduce
   new dependencies without explicit approval.
4. **Async workflow fragmentation:** Correlate via `session.id` and explicit trigger metadata
   (`yaam.trigger_turn_id`).
