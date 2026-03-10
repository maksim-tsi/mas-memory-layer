# Phoenix Option A Report: Controlled Write-Enabled API-Wall Validation

**Date:** March 10, 2026  
**Status:** Implemented, live validation completed  
**Audience:** Maintainers, observability owners, benchmark operators  
**Phoenix Project:** `mlm-mas-dev-phoenix-option-a-20260310-201826`

**Operational Note:** This report captures the Option A implementation pass after the first live
retriever validation. The procedural baseline remains
`docs/runbooks/phoenix-experiment-reproducibility.md`.

## 1. Objective

Option A was defined as a controlled improvement to the API-Wall evidence path rather than a global
runtime semantic change. The objective was to preserve the existing benchmark-safe default
(`skip_l1_write = true`) while allowing explicit API-Wall experiments to enable write-through
behavior and barrier promotion through request metadata. This would test whether richer live memory
state could be made visible through the public API boundary without collapsing into the internal
`POST /run_turn` wrapper path.

## 2. Code and Validation Changes

The implementation modified the API Wall to accept request metadata directly in the chat-completions
payload and to merge that metadata before applying the existing `skip_l1_write` default. As a
result, requests can now explicitly set `metadata.skip_l1_write = false` while requests that omit
the field continue to use the prior default.

Focused validation confirmed both behaviors:

1. `tests/test_server_api_wall.py` now verifies that the default request path still sets
   `skip_l1_write = true`.
2. The same test module now verifies that `metadata.skip_l1_write = false` is preserved on the
   `RunTurnRequest` passed into the agent.

Repository verification completed successfully:

1. `./.venv/bin/ruff check .` passed.
2. `./.venv/bin/pytest tests/test_server_api_wall.py -v` passed with `2 passed`.
3. `./.venv/bin/pytest tests/ -v` passed with `614 passed, 108 skipped`.

## 3. Live Validation Configuration

The live Option A run used the following configuration:

1. API Wall route: `POST /v1/chat/completions`
2. Session family:
   - two-turn smoke session: `phoenix-option-a-20260310-201826`
   - scripted threshold-crossing session: `phoenix-option-a-scripted-20260310-201826`
3. `MAS_PROMOTION_MODE = barrier`
4. Request metadata override:
   - `skip_l1_write = false`
   - `experiment_label = phoenix-option-a` or `phoenix-option-a-scripted`

This configuration preserved ADR-009 semantics because the experiment still used the public API Wall
and only altered request metadata under explicit experimental control.

## 4. Two-Turn Controlled Smoke Result

The first write-enabled smoke rerun demonstrated that the override path works mechanically:

1. Response metadata preserved `skip_l1_write = false`.
2. `promotion_mode = barrier` was recorded.
3. `promotion_status = completed` was recorded for both turns.
4. The same retrieval request still reported `facts_promoted = 0` and empty working-memory context.

This outcome was not a tracing defect. Repository inspection confirmed that the promotion engine and
topic segmentation flow require a minimum batch size before fact promotion becomes likely, so a
two-turn experiment was analytically insufficient.

## 5. Scripted Threshold-Crossing Result

To cross the promotion threshold through the API Wall itself, a controlled scripted sequence of five
write-enabled priming requests was executed in one fresh session, followed by a retrieval request.

The per-step response metadata showed:

1. Step 1: `promotion_status = completed`, `facts_promoted = 0`
2. Step 2: `promotion_status = completed`, `facts_promoted = 0`
3. Step 3: `promotion_status = completed`, `facts_promoted = 0`
4. Step 4: `promotion_status = timeout`, `working_facts_count = 4`
5. Step 5: `promotion_status = completed`, `working_facts_count = 8`
6. Retrieval turn: `promotion_status = timeout`, `working_facts_count = 10`

The retrieval response content clearly reflected the scripted memory state. The assistant summarized
three concrete lessons about customs delays:

1. pre-submit invoices 48 hours before arrival,
2. pre-submit packing lists 48 hours before arrival,
3. and escalate to the customs broker before cargo lands when delays begin.

This demonstrates that the write-enabled API-Wall route can now drive materially stronger live
memory state than the prior default-suppressed path.

## 6. Phoenix Trace Result

The retrieval turn in the scripted session returned:

1. `yaam_trace_id = 470c21fcab6828ccf7cfd58b4ee2ae38`
2. `yaam_span_id = 504322bcb6255e51`
3. `client_session_id = phoenix-option-a-scripted-20260310-201826`
4. `yaam_session_id = full__baseline:phoenix-option-a-scripted-20260310-201826`

Phoenix returned the expected four-span chain for that trace:

1. `yaam.api_wall.chat_completions`
2. `yaam.agent.run_turn`
3. `yaam.workflow.retrieve`
4. `yaam.retriever.l2`

The live trace therefore confirms that the write-enabled experiment still preserves the intended
parent-child observability structure.

## 7. Key Finding: Stronger Memory State, Incomplete Retriever Payload

The most important result of Option A is mixed rather than purely positive.

Positive outcome:

1. The controlled override works.
2. The public API-Wall route can now be used for write-enabled Phoenix experiments.
3. Response metadata and final assistant behavior showed materially stronger memory usage.

Remaining boundary:

1. The Phoenix `yaam.retriever.l2` span for the scripted retrieval trace still reported:
   - `yaam.retrieval.result_count = 0`
   - `retrieval.documents = []`
2. At the same time, the response metadata reported `working_facts_count = 10`.
3. Repository inspection explains this discrepancy: `MemoryAgent._retrieve_node()` assembles prompt
   context through `get_context_block()` and separately executes `query_memory()` for query-shaped
   retrieval. The current retriever spans reflect the latter path, while the live working-memory
   context that improved the answer was assembled through the former path.

Therefore, Option A successfully removed the write-policy barrier, but it also isolated the next
observability gap more precisely: the API-Wall route can now exercise live memory state, yet the
current Phoenix retriever payload does not fully represent the prompt-context retrieval path used by
the agent.

## 8. Interpretation for the Research Project

This result is important in the broader research context because it sharpens the evidence model.

Before Option A, the dominant ambiguity was whether poor retriever evidence in Phoenix was caused by
request-policy suppression (`skip_l1_write = true`). After Option A, that ambiguity is resolved.

The project can now make two defensible statements:

1. The API Wall supports controlled write-enabled Phoenix experiments without breaking the default
   benchmark posture.
2. The remaining gap is not merely that memory is absent; it is that the currently instrumented
   retriever span path does not yet cover all of the retrieval work that materially contributes to
   prompt context.

This is a stronger research position because it separates runtime policy from observability coverage.

## 9. Recommended Follow-On

The next stage should proceed in two layers.

1. Preserve Option A as complete with respect to write-policy control and evidence collection.
2. Treat the still-empty `yaam.retriever.l2` payload as a new observability-gap finding rather than
   as an Option A failure.
3. Proceed to Option B with awareness that tool execution will not, by itself, fix the
   `get_context_block()` visibility gap.
4. If desired later, open a separate follow-on task to instrument `get_context_block()` or otherwise
   expose prompt-context retrieval evidence in Phoenix.

## 10. Reference Artifacts

- Plan: [2026-03-10-yaam-glassbox-observability-gap-closure-plan.md](../plan/2026-03-10-yaam-glassbox-observability-gap-closure-plan.md)
- Runbook: [phoenix-experiment-reproducibility.md](../runbooks/phoenix-experiment-reproducibility.md)
- Prior retriever report: [2026-03-10-phoenix-retriever-live-validation-report.md](2026-03-10-phoenix-retriever-live-validation-report.md)
- API Wall implementation: [src/server.py](../../src/server.py)
- Retrieval flow: [src/agents/memory_agent.py](../../src/agents/memory_agent.py)
- Unified memory retrieval spans: [src/memory/unified_memory_system.py](../../src/memory/unified_memory_system.py)