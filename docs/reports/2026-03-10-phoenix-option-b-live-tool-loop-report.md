# Phoenix Option B Report: Live Tier-Tool Execution Through the API Wall

**Date:** March 10, 2026  
**Status:** Implemented, live validation completed  
**Audience:** Maintainers, observability owners, benchmark operators  
**Phoenix Project:** `mlm-mas-dev-phoenix-option-b-live-20260310-211012`

**Operational Note:** This report captures the first successful live validation of the Option B
tool-calling loop for normal API-Wall requests. The procedural baseline remains
[phoenix-experiment-reproducibility.md](../runbooks/phoenix-experiment-reproducibility.md).

## 1. Objective

Option B was defined as the first end-to-end validation of tier-tool execution in ordinary
API-Wall traffic. The objective was narrower than a full agent-runtime redesign. The goal was to
demonstrate that a normal `v1-*` request can:

1. cause Gemini to emit a structured tool call,
2. execute an already instrumented YAAM tier tool,
3. emit `yaam.tool.*` spans plus nested retriever spans in Phoenix,
4. and still complete the request through the public `POST /v1/chat/completions` boundary.

This experiment therefore addresses the specific Option B claim: Phoenix should reveal real
tool-mediated memory access during normal request handling rather than only during isolated unit
tests or direct tool invocation.

## 2. Implementation Scope and Follow-On Fixes

The Option B implementation added a bounded Gemini-first tool loop for `v1-*` variants in the
policy layer. During live validation, two Gemini-specific runtime defects were observed and fixed
before the final successful rerun.

The final live-capable implementation state was:

1. `src/llm/providers/base.py` exposes structured tool calls through the normalized response
   contract.
2. `src/llm/providers/gemini.py` parses Gemini function calls, safely handles function-call-only
   responses whose `.text` accessor raises, and preserves the full SDK response object for
   follow-up turns.
3. `src/agents/memory_agent.py` executes a bounded tool loop for `v1-*` variants and records tool
   loop metadata in the response.
4. `tests/utils/test_providers_gemini.py` and `tests/agents/test_memory_agent.py` cover the
   provider and normal-request tool-loop behavior.

These live fixes were not speculative cleanups. They were required to make the first successful
Gemini 3 tool-loop trace complete without provider fallback or follow-up request rejection.

## 3. Live Validation Configuration

The successful live Option B run used the following configuration:

1. API Wall route: `POST /v1/chat/completions`
2. Phoenix project: `mlm-mas-dev-phoenix-option-b-live-20260310-211012`
3. API Wall runtime:
   - `MAS_AGENT_TYPE = full`
   - `MAS_AGENT_VARIANT = v1-min-skillwiring`
   - `MAS_MODEL = gemini-3-flash-preview`
   - `MAS_PROMOTION_MODE = barrier`
4. Request session: `phoenix-option-b-live-20260310-211012-rerun2`
5. Request metadata:
   - `skill_slug = l2-fact-lookup`
   - `skip_l1_write = false`
   - `experiment_label = phoenix-option-b-live`

The forced skill selection was important because it constrained the exposed toolset to the L2 fact
lookup skill contract and reduced ambiguity about which tool Gemini should call.

## 4. Initial Live Failure Modes and Their Interpretation

The first live Option B attempts produced analytically useful failures.

### 4.1 Function-call-only response text access

Gemini did emit a function call for `l2_search_facts`, but the provider still attempted to read
`response.text` directly. The Google GenAI SDK raises on that property when the response contains
function-call parts rather than text-only parts.

This defect did not invalidate the Option B design. It showed that the provider contract needed a
safe text extraction path that tolerates tool-call turns.

### 4.2 Gemini 3 thought-signature follow-up validation

After the first provider fix, the next live rerun failed with `400 INVALID_ARGUMENT` because the
follow-up turn did not preserve Gemini 3 thought-signature state correctly during the manual tool
loop.

The key lesson was precise: carrying forward only `response.candidates[0].content` was insufficient
for Gemini 3 function-calling follow-up turns in this SDK path. Preserving the full SDK response
object allowed the second model turn to complete successfully.

These failures were important because they established that the remaining live blockers were not in
the YAAM tool execution path itself. They were provider-local runtime issues that could be fixed
without reopening Option B scope.

## 5. Successful Live Request Result

The successful rerun used the session `phoenix-option-b-live-20260310-211012-rerun2` and returned a
completed `200 OK` response through the API Wall. The assistant response content was:

1. `none found`

The response metadata is the critical evidence surface for the normal request path. It reported:

1. `tool_loop_enabled = true`
2. `tool_loop_rounds = 1`
3. `tool_call_count = 1`
4. `llm_provider = gemini`
5. `llm_model = gemini-3-flash-preview`
6. `promotion_status = completed`
7. `yaam_session_id = full__v1-min-skillwiring:phoenix-option-b-live-20260310-211012-rerun2`

This confirms that the successful request stayed on the intended Gemini path, executed one tool
round, and completed normally through the public API boundary.

## 6. Phoenix Trace Result

The successful live request returned:

1. `yaam_trace_id = 1b92c7e7816e4226393d6146d6191259`
2. `yaam_span_id = 6916160ebb7e1ca6`
3. `client_session_id = phoenix-option-b-live-20260310-211012-rerun2`
4. `yaam_session_id = full__v1-min-skillwiring:phoenix-option-b-live-20260310-211012-rerun2`

Phoenix returned the following confirmed span chain for that trace:

1. `yaam.api_wall.chat_completions`
2. `yaam.agent.run_turn`
3. `yaam.workflow.retrieve`
4. `yaam.retriever.l2`
5. `yaam.tool.l2_search_facts`
6. `yaam.retriever.l2`

The important structural point is that the tool span appears under the normal request path and that
the tool itself contains a nested retriever span. This is the exact observability claim Option B
was intended to prove.

## 7. Span-Level Interpretation

The successful trace supports four concrete conclusions.

1. The public API-Wall request root still parents the entire trace correctly.
2. The `MemoryAgent` now performs an actual Gemini-mediated tool loop during normal `v1-*`
   requests.
3. The already instrumented tier tool emits a live `TOOL` span in Phoenix.
4. The tool's retrieval work is separately visible through a nested `RETRIEVER` span.

For this specific session, the L2 lookup returned no matching facts. That is reflected consistently
in both the API response and the Phoenix span payload:

1. assistant content: `none found`
2. `yaam.results_count = 0` on `yaam.tool.l2_search_facts`
3. `yaam.retrieval.result_count = 0` on the nested `yaam.retriever.l2`
4. `retrieval.documents = []` on the nested retriever span

This is still a successful Option B result because the experiment was designed to validate live
tool-loop observability, not to prove non-empty fact retrieval for the chosen session.

## 8. Boundary That Remains Open

The prompt-context observability gap isolated by Option A remains open.

The successful Option B trace proves that live tool-mediated retrieval is now visible in Phoenix.
However, this does not mean that all memory contributing to prompt construction is now visible. The
existing `get_context_block()` path remains a separate retrieval surface, and its contribution to
prompt context is still not fully represented by the current retriever span inventory.

Accordingly, the correct interpretation is:

1. Option B succeeded with respect to live `yaam.tool.*` visibility in normal requests.
2. Option B does not close the separate `get_context_block()` prompt-context visibility gap.

This distinction should be preserved in any paper or ADR-facing claims.

## 9. Repository Validation State After Live Fixes

Repository validation was re-run after the Gemini live-fix changes landed.

1. `./.venv/bin/ruff check .` passed.
2. `./.venv/bin/pytest tests/ -v` passed with `620 passed, 108 skipped`.

This post-live validation matters because the final successful Phoenix result depends on the
Gemini-specific follow-up fixes described above, not merely on the earlier Option B implementation
pass.

## 10. Conclusion

Option B is now supported by live Phoenix evidence.

The repository can now make the following defensible statement: under normal `v1-*` API-Wall
traffic, Gemini can select a YAAM tier tool, the tool executes within the request, and Phoenix
records both the tool span and its nested retriever span in the same end-to-end trace.

This is stronger than the earlier instrumentation-only claim because it is grounded in a completed
live request rather than in isolated tests or direct tool coroutine execution.

## 11. Reference Artifacts

- Plan: [2026-03-10-memoryagent-tool-calling-loop-plan.md](../plan/2026-03-10-memoryagent-tool-calling-loop-plan.md)
- Main plan: [2026-03-10-yaam-glassbox-observability-gap-closure-plan.md](../plan/2026-03-10-yaam-glassbox-observability-gap-closure-plan.md)
- Runbook: [phoenix-experiment-reproducibility.md](../runbooks/phoenix-experiment-reproducibility.md)
- Option A report: [2026-03-10-phoenix-option-a-write-enabled-api-wall-report.md](2026-03-10-phoenix-option-a-write-enabled-api-wall-report.md)
- Provider implementation: [src/llm/providers/gemini.py](../../src/llm/providers/gemini.py)
- Agent tool loop: [src/agents/memory_agent.py](../../src/agents/memory_agent.py)
- Gemini provider tests: [tests/utils/test_providers_gemini.py](../../tests/utils/test_providers_gemini.py)
- MemoryAgent tests: [tests/agents/test_memory_agent.py](../../tests/agents/test_memory_agent.py)