# Plan: Close Phoenix “Prompt-Context Evidence” Gap by Instrumenting `get_context_block()` Retrieval

**Date:** March 11, 2026  
**Target output (after approval):** `docs/plan/2026-03-11-phoenix-context-block-retriever-evidence-plan.md`

## Findings (basis for this plan)

1. The live Option A run demonstrated materially stronger memory usage (e.g., `working_facts_count > 0`) while Phoenix still showed empty `retrieval.documents` on `yaam.retriever.l2`. This is consistent with the code path: prompt context is assembled via `UnifiedMemorySystem.get_context_block()`, while the currently-instrumented retriever evidence primarily reflects `UnifiedMemorySystem.query_memory()`.
2. The normative span contract already assigns ownership of `yaam.retriever.l1` and `yaam.retriever.l2` (context-assembly) to `UnifiedMemorySystem.get_context_block()`, but the current implementation does not emit those spans there.
3. Option B confirmed that tool spans can be emitted through the API Wall for `v1-*` + Gemini, so the remaining glass-box gap is not “tools are not visible” but specifically “prompt-context assembly is not visible”.

## Implementation changes (decision-complete)

### A) Emit retriever spans from `UnifiedMemorySystem.get_context_block()`
Implement OpenInference/Phoenix-compatible evidence spans at the source of prompt-context assembly:

1. **L1 context evidence**
   - Add span: `yaam.retriever.l1` with `openinference.span.kind=RETRIEVER`.
   - Wrap the actual `l1_tier.retrieve_session(session_id=...)` call inside the span.
   - Set required attributes:
     - `session.id` (required)
     - `retrieval.documents` (required)
     - `yaam.memory.tier="L1"`
     - `yaam.retrieval.surface="context_block"`
     - `yaam.retrieval.limit=<max_turns>`
   - Populate `retrieval.documents` from returned `TurnData` (newest-first), using:
     - `document.id="L1:<turn_id>"`
     - `document.content` = **turn content truncated** to a fixed safe limit (see “Assumptions”)
     - `document.score` = `null` (no inherent relevance score)
     - `document.metadata` = `{role, timestamp_iso, turn_id, window_index}`

2. **L2 context evidence**
   - Add span: `yaam.retriever.l2` with `openinference.span.kind=RETRIEVER`.
   - Wrap the actual `l2_tier.query_by_session(session_id=..., min_ciar_score=..., limit=...)` call inside the span.
   - Set required attributes:
     - `session.id` (required)
     - `retrieval.documents` (required)
     - `yaam.memory.tier="L2"`
     - `yaam.retrieval.surface="context_block"`
     - `yaam.retrieval.limit=<max_facts>`
     - `yaam.ciar.threshold=<min_ciar>`
   - Populate `retrieval.documents` from returned `Fact` objects (these are the facts *actually injected* into the prompt context):
     - `document.id="L2:<fact_id>"`
     - `document.content` = **fact content truncated** to the same safe limit
     - `document.score` = `ciar_score`
     - `document.metadata` = `{tier:"L2", session_id, fact_type, access_count, extracted_at_iso, certainty, impact}` when available

3. **Keep `input.value` semantics truthful**
   - Do **not** set `input.value` on `yaam.retriever.l1` or the threshold-only `yaam.retriever.l2` emitted by `get_context_block()` (allowed by the contract: context assembly is not query-conditioned).
   - Leave `input.value` requirements unchanged for query-conditioned spans emitted by `query_memory()`.

### B) Documentation updates (to prevent semantic drift)
1. Update `docs/specs/observability/phoenix-span-contract.md` to explicitly distinguish the two surfaces that can emit `yaam.retriever.l2`:
   - `yaam.retriever.l2` with `yaam.retrieval.surface="context_block"` (threshold-gated prompt context)
   - `yaam.retriever.l2` with `yaam.retrieval.surface="query_memory"` (query-conditioned evidence selection)
2. Update `docs/runbooks/phoenix-experiment-reproducibility.md` to add a new validation checkpoint:
   - After a scripted Option A session (write-enabled), verify that the trace includes:
     - `yaam.retriever.l2` (surface=context_block) with non-empty `retrieval.documents` matching `working_facts_count`.

### C) Tests (must be added with the code change)
Add a focused unit test that proves `get_context_block()` emits the new spans and documents:

- Test location: extend `tests/memory/test_unified_memory_system.py`
- Approach:
  - Patch `src.observability.tracing._get_tracer` to `FakeTracer()` (existing test pattern).
  - Mock `l1_tier.retrieve_session` to return 2 `TurnData`.
  - Mock `l2_tier.query_by_session` to return 2 `Fact`.
  - Call `UnifiedMemorySystem.get_context_block(session_id=..., min_ciar=..., max_turns=..., max_facts=...)`.
  - Assert:
    - spans started include `yaam.retriever.l1` then `yaam.retriever.l2` (order may be fixed by implementation)
    - each span has `openinference.span.kind="RETRIEVER"` and `session.id`
    - each span has JSON-parseable `retrieval.documents` with expected `document.id` prefix (`L1:` / `L2:`)
    - L2 documents carry `document.score == ciar_score` and include `yaam.ciar.threshold`

## Validation procedure (Phoenix “glass-box” rerun)
1. Run scripted Option A priming + retrieval session with `metadata.skip_l1_write=false` and barrier promotion.
2. For the retrieval request trace, verify in Phoenix (UI or `/v1/projects/.../spans`) that:
   - `yaam.retriever.l2` with `yaam.retrieval.surface="context_block"` has populated `retrieval.documents` and `yaam.retrieval.result_count > 0`.
   - The prior “empty `retrieval.documents` but improved answer quality” mismatch is resolved.
3. Record a new dated evidence report in `docs/reports/` with:
   - Phoenix project name, trace id, session id, and the span evidence excerpt.

## Assumptions / defaults (locked for implementation)
- **Instrumentation placement:** inside `UnifiedMemorySystem.get_context_block()` (source-local, matches contract ownership).
- **L1 capture policy:** include `document.content` but **truncate** to `2000` characters (fixed constant in code for now; no new env/config in this step).
- **Span differentiation:** set `yaam.retrieval.surface="context_block"` on the new spans to prevent confusion with `query_memory()` or tool-nested retrievers.
- **No changes to `src/storage/`** and no dependency changes.
