# Plan: Fast-LLM Parity and Memory-Workflow Barriers (Groq/Gemini/Mistral)

**Status:** Draft  
**Date:** February 22, 2026  
**Audience:** Maintainers, benchmark operators  
**Scope:** Policy/behavior layer changes and evaluation protocol updates for provider parity under the GoodAI LTM Benchmark API Wall constraint.

## 1. Motivation and Problem Statement

Recent Smoke5 runs indicate that Groq-backed inference can be substantially lower latency than the end-to-end YAAM request path (HTTP handling, memory retrieval, storage IO, and optional background promotion). This creates two risks:

1. **Attribution/traceability risk:** without artifact-level metadata, it is difficult to determine which provider/model produced each response and whether the memory layer contributed to the response generation.
2. **Workflow-completeness risk:** when memory promotion and enrichment steps execute asynchronously, subsequent turns may be processed before those steps complete. Under fast inference, this can increase the likelihood of “missing memory” effects that are not attributable to provider quality but to scheduling.

The overarching requirement is **academic cleanliness**: Groq, Gemini, and Mistral must be evaluated under *maximally equivalent* conditions. If behavior-layer changes (e.g., promotion barriers, revised timeouts) are introduced to stabilize fast Groq runs, then the same changes must be applied and experiments repeated for Gemini and Mistral.

## 2. Current Pipeline (Observed Architecture)

### 2.1 API Wall request flow (per request)

For `POST /v1/chat/completions`, the service:

1. Validates headers and message payload (requires `X-Session-Id`).
2. Applies the session prefix `<agent_type>__<agent_variant>:` for isolation.
3. Stores the user turn to L1 (subject to `skip_l1_write`).
4. Invokes `agent.run_turn(...)` with the request and optional `history`.
5. Stores the assistant turn to L1 (subject to `skip_l1_write`).
6. Returns an OpenAI-compatible response payload.

### 2.2 Agent pipeline (MemoryAgent)

The agent pipeline is sequential per request:

1. **Retrieve:** fetch context block (recent turns + significant facts) and optionally query memory.
2. **Reason:** build prompt and call the LLM.
3. **Update:** optionally write to L1 and spawn a background promotion cycle (currently asynchronous).

### 2.3 Default suppression of writes

The API Wall currently sets `skip_l1_write=true` by default. Consequently, promotion-cycle engines (TopicSegmenter, FactExtractor) are typically not exercised during benchmark runs unless explicitly enabled.

## 3. Key Risks Under Fast Inference

### 3.1 Asynchronous promotion scheduling

When `skip_l1_write=false`, `MemoryAgent._update_node` spawns promotion as a background task. If the benchmark issues a subsequent request immediately, the next retrieval step may not observe the promoted L2 facts. This creates a confounder: the effective “memory quality” depends on timing.

### 3.2 Timeout and output budget mismatches

Provider timeouts, maximum output tokens, and wrapper timeouts influence whether responses are complete and whether downstream steps (e.g., structured extraction) succeed. These parameters must be controlled to avoid provider-specific advantages or disadvantages.

### 3.3 Artifact insufficiency for post-mortem debugging

To satisfy reproducibility and auditability, the benchmark artifacts must allow reconstruction of:

- session identity and isolation,
- provider/model attribution,
- storage versus LLM timing decomposition,
- memory contributions (counts and deltas),
- and the presence/absence of asynchronous promotion.

## 4. Requirements (Normative for Parity Experiments)

### 4.1 Provider parity (experimental control)

For parity experiments, the following MUST be held constant across providers unless explicitly studied as an independent variable:

- benchmark configuration file(s) and dataset versions,
- agent type and variant,
- rate limiter settings,
- wrapper timeouts,
- model output token limit,
- and promotion mode (disabled / async / barrier-synchronous).

Any deviation MUST be documented and repeated across all providers.

### 4.2 Observability from artifacts

For each turn, artifacts MUST allow recovery of:

- `llm_provider` and `llm_model`,
- per-turn timings (`llm_ms`, `storage_ms` at minimum; ideally pre/post decomposition),
- session identifiers (client session id and prefixed YAAM session id),
- and a minimal memory-context summary (e.g., counts of retrieved turns/facts).

## 5. Proposed Policy-Layer Enhancements (Implementation Plan)

### 5.1 Promotion barrier modes

Introduce a policy-layer switch for promotion execution semantics when writes are enabled:

- `MAS_PROMOTION_MODE=disabled|async|barrier`
  - `disabled`: do not run promotion
  - `async`: current behavior (background task)
  - `barrier`: await promotion completion before returning from a turn (optionally with timeout)

This switch MUST apply identically across Groq/Gemini/Mistral runs.

### 5.2 Context-completeness workflow checks

Add per-turn metadata to confirm that the model request had access to:

- the benchmark’s current user instruction,
- the provided `history`,
- and the retrieved memory context from YAAM.

This should not expose user content. Recommended signals:

- `context.recent_turns_count`
- `context.working_facts_count`
- `context.episodic_chunks_count`
- `context.semantic_knowledge_count`
- `context.retrieval_ms`

### 5.3 Provider/model attribution and timing in benchmark artifacts

Ensure that the GoodAI runner records API Wall response metadata into:

- `master_log.jsonl` (per assistant message),
- and `turn_metrics.jsonl` (via `llm_ms` and `storage_ms` fields).

### 5.4 Engine model routing controls

For LLM-backed engines used in promotion and enrichment (FactExtractor, TopicSegmenter), provide explicit configuration:

- `MAS_FACT_EXTRACTOR_MODEL` (default: `MAS_MODEL`)
- `MAS_TOPIC_SEGMENTER_MODEL` (default: `MAS_MODEL`)

If an engine must remain on Gemini for functional reasons (e.g., structured output compatibility), this MUST be:

1. documented as a deviation,
2. tested under identical conditions for all provider comparisons, and
3. treated as a separate experimental factor.

## 6. Evaluation Protocol (Repeatable Experiments)

### 6.1 Benchmark run set (API Wall)

For each provider condition, run:

1. Smoke5 with unique `--run-name` including `<agent_type>__<agent_variant>` and provider identifier.
2. Record `/health` JSON, run start/end times, and exit code.
3. Collect artifacts:
   - `run_console.log`, `master_log.jsonl`, `turn_metrics.jsonl`, `runstats.json`, per-dataset `0_0.json`
   - YAAM rate limiter JSONL for the run window
   - HTML report under `benchmarks/goodai-ltm-benchmark/data/reports/`

### 6.2 Memory-engine validation set (promotion enabled)

Benchmark runs commonly set `skip_l1_write=true`, which suppresses promotion. Therefore, memory-engine validation MUST be performed as a separate controlled test:

- Enable L1 writes and select a promotion mode (`async` or `barrier`).
- Send a fixed conversation script that triggers promotion thresholds.
- Validate:
  - promotion produces L2 facts,
  - FactExtractor/TopicSegmenter provider/model attribution is recorded,
  - and retrieval on subsequent turns includes the promoted facts.

### 6.3 Provider replication policy (mandatory)

If any change is introduced to improve Groq stability (e.g., barrier mode, revised timeouts), the identical change MUST be:

1. applied to the shared code path,
2. re-run under Gemini and Mistral conditions,
3. and documented in a single comparative report with matching run configurations.

## 7. Documentation and Tracking Deliverables

All documentation MUST be written in English and maintain an academic tone.

For each experiment batch, produce:

1. A per-run report in `docs/reports/` using `docs/reports/template-goodai-agent-variant-report-groq.md` (for Groq) or the standard template for non-Groq runs.
2. A comparative summary report that:
   - enumerates controlled variables and deviations,
   - aggregates latency distributions (p50/p95/p99),
   - and reports dataset scores and failure taxonomy.

## 8. Acceptance Criteria

The work is considered complete when:

1. Artifact-only debugging can recover provider/model attribution and timing decomposition for each turn.
2. Promotion mode is explicitly controlled and documented for memory-engine validation experiments.
3. Any behavior-layer change introduced for Groq is replicated under Gemini and Mistral with the same configuration and reported outcomes.

