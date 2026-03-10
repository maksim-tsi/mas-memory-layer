# Plan: MemoryAgent Tool-Calling Loop for Normal API-Wall Requests

**Status:** Proposed  
**Date:** March 10, 2026  
**Owners:** YAAM maintainers, observability owners, agent-runtime owners  
**Related:** [ADR-009](../ADR/009-decoupling-benchmark-api-wall.md), [ADR-013](../ADR/013-phoenix-tracing-strategy.md), [Phoenix span contract](../specs/observability/phoenix-span-contract.md), [YAAM glass-box observability gap-closure plan](2026-03-10-yaam-glassbox-observability-gap-closure-plan.md), [Phoenix Option A report](../reports/2026-03-10-phoenix-option-a-write-enabled-api-wall-report.md)

## 1. Purpose

This plan defines the first implementation pass for end-to-end tier-tool execution in normal API-Wall
requests. Its objective is to make `yaam.tool.*` spans observable in Phoenix under ordinary request
traffic rather than only through direct tool invocation tests.

The plan explicitly follows Option A. The repository already demonstrated that API-Wall requests can
produce agent and retriever spans and that controlled write-enabled requests can produce materially
stronger memory state. The remaining targeted gap is that normal requests still do not execute the
already instrumented tier tools in `src/agents/tools/tier_tools.py`.

This plan is not a general redesign of the YAAM agent architecture. It is a bounded agent-runtime
change that adds LLM-selected tool execution while preserving the current benchmark-safe and
baseline-safe boundaries.

## 2. Scope and non-goals

### In scope

1. Add a real tool-calling loop to `MemoryAgent` for normal requests.
2. Extend the LLM provider/client contract so provider responses can carry structured tool-call
   data.
3. Enable Gemini-first tool-calling support for the first pass.
4. Restrict the new loop to `v1-*` variants so baseline behavior remains unchanged.
5. Validate live `yaam.tool.*` span visibility through the API Wall and Phoenix.

### Not in scope

1. Provider parity across Gemini, Groq, and Mistral in the first pass.
2. Changing baseline variants to use the new tool loop.
3. Instrumenting `get_context_block()` or solving the prompt-context visibility gap isolated by
   Option A.
4. Modifying the mechanism layer under `src/storage/`.

## 3. Constraints and invariants

1. The API Wall remains the canonical execution boundary under [ADR-009](../ADR/009-decoupling-benchmark-api-wall.md).
2. The mechanism layer under `src/storage/` remains frozen-by-default.
3. The first-pass tool loop applies only to `agent_variant` values beginning with `v1-`.
4. Baseline variants must preserve the current retrieve-then-synthesize behavior.
5. The first provider target is Gemini. Provider parity is a separate follow-on decision.
6. The plan must preserve the existing skill-gating contract and reuse the current `ALL_TOOLS`
   versus `UNIFIED_TOOLS` distinction.
7. The resulting spans must remain consistent with the [Phoenix span contract](../specs/observability/phoenix-span-contract.md).

## 4. Deliverables

1. A normalized tool-call response contract in `src/llm/providers/base.py` and `src/llm/client.py`.
2. Gemini-first provider support for tool-call generation and parsing.
3. A bounded tool-execution loop in `src/agents/memory_agent.py` for `v1-*` variants.
4. Unit and focused integration coverage for the new loop, including tracing assertions.
5. A dated Phoenix evidence report showing `yaam.tool.*` spans from a normal API-Wall request.

## 5. Current-state assessment

The repository already contains the majority of the policy-layer building blocks required for this
work:

1. `src/agents/tools/tier_tools.py` already emits `TOOL` spans and nested `RETRIEVER` spans.
2. `src/agents/runtime.py` already defines `MASContext` and `MASToolRuntime` for runtime context
   injection.
3. `src/agents/memory_agent.py` already loads `ALL_TOOLS` for `v1-*` variants.
4. `tests/agents/tools/test_tier_tools.py` already validates direct tool behavior and tracing.

The missing pieces are structural rather than conceptual:

1. `MemoryAgent` does not currently bind or execute tools during normal requests.
2. `LLMResponse` is text-only and does not carry structured tool calls.
3. Gemini currently disables automatic function calling.
4. No existing test exercises an end-to-end normal-request tool loop.

## 6. Workstreams and milestones

### Milestone A: Provider and client tool-call contract

**Goal:** Normalize provider tool-call output so the agent loop can execute tools without using
provider-specific parsing logic.

**Implementation requirements**

1. Extend `LLMResponse` in `src/llm/providers/base.py` with a structured `tool_calls` field.
2. Extend `LLMClient.generate(...)` in `src/llm/client.py` so the caller can supply tool schemas or
   tool descriptors.
3. Define one repository-wide normalized tool-call shape with at least:
   - tool name,
   - arguments,
   - and provider-native call identifier if available.
4. Ensure non-tool generations continue to work unchanged when no tools are supplied.

**Acceptance criteria**

1. Providers can return text-only responses without regression.
2. The client can return structured tool calls to `MemoryAgent` in a stable, provider-agnostic
   format.

### Milestone B: Gemini-first tool-calling enablement

**Goal:** Support LLM-selected tool calls on the current primary Phoenix path.

**Implementation requirements**

1. Update `src/llm/providers/gemini.py` so tool calling is enabled for the new path rather than
   hard-disabled.
2. Pass tool schemas into the Gemini SDK call.
3. Parse Gemini tool-call output and normalize it into `LLMResponse.tool_calls`.
4. Preserve current behavior for non-tool generations.

**Acceptance criteria**

1. Gemini can return at least one structured tool call in the normalized format.
2. Standard text-only turns still work without behavioral regression.

### Milestone C: Bounded tool-execution loop in MemoryAgent

**Goal:** Execute LLM-selected tools during normal requests for `v1-*` variants.

**Implementation requirements**

1. Add a bounded loop in `src/agents/memory_agent.py` that:
   - calls the LLM with allowed tool schemas,
   - inspects returned tool calls,
   - invokes matching tools with `MASContext`,
   - appends tool results into the message/state history,
   - and terminates after an explicit iteration cap.
2. Keep baseline variants on the current non-tool path.
3. Preserve the existing skill-gating contract so only allowed tools are exposed for the selected
   skill and variant.
4. Fail safely on unknown tools, malformed arguments, provider responses without tool calls, and
   loop exhaustion.

**Acceptance criteria**

1. At least one tier tool can execute end to end in a normal `v1-*` request.
2. Baseline variants remain unchanged.
3. The loop is bounded and failure-safe.

### Milestone D: Tracing, verification, and evidence

**Goal:** Prove live `yaam.tool.*` observability without conflating it with the separate
`get_context_block()` visibility gap.

**Implementation requirements**

1. Extend `tests/agents/test_memory_agent.py` with tool-loop execution cases.
2. Reuse `tests/helpers/fake_tracing.py` and the current tool-span patterns to assert normal-request
   tool spans and nested retriever spans.
3. Re-run Phoenix through the API Wall with a `v1-*` variant and a prompt that should trigger at
   least one tier tool.
4. Publish a dated report under `docs/reports/` with trace identifiers and observed span names.
5. Explicitly state in the report whether the `get_context_block()` visibility gap remains open.

**Acceptance criteria**

1. Phoenix shows `yaam.tool.*` under the normal request path.
2. The dated report distinguishes the solved tool-loop gap from the still-separate prompt-context
   visibility gap.

## 7. Task breakdown

| Task ID | Task | Scope | Depends on | Verification target |
|---|---|---|---|---|
| B1 | Extend `LLMResponse` with tool-call support | `src/llm/providers/base.py` | None | Response contract can represent tool calls |
| B2 | Add `tools` support to `LLMClient.generate(...)` | `src/llm/client.py` | B1 | Client passes tool schemas without breaking text-only generations |
| B3 | Enable Gemini tool calling | `src/llm/providers/gemini.py` | B1, B2 | Gemini returns normalized tool-call data |
| C1 | Add bounded tool loop for `v1-*` variants | `src/agents/memory_agent.py` | B1, B2, B3 | A normal request can execute at least one tool |
| C2 | Inject `MASContext` into tool execution | `src/agents/runtime.py`, `src/agents/memory_agent.py` | C1 | Tool receives correct session and memory context |
| C3 | Preserve skill-gating and allowed-tool filtering | `src/agents/memory_agent.py`, skill wiring helpers | C1 | Only allowed tools are exposed and callable |
| D1 | Add unit tests for tool-loop behavior | `tests/agents/test_memory_agent.py` | C1, C2, C3 | Tool loop works and baseline path is unchanged |
| D2 | Add tracing assertions for normal-request tool spans | `tests/agents/test_memory_agent.py`, `tests/helpers/fake_tracing.py` | D1 | `yaam.tool.*` and nested retriever spans are asserted |
| D3 | Run live Phoenix validation for a `v1-*` request | API Wall + Phoenix | D1, D2 | Request trace contains live tool span(s) |
| D4 | Publish Option B evidence report | `docs/reports/` | D3 | Reviewable artifact exists |

## 8. Verification procedure

**Repository validation**

1. `./.venv/bin/ruff check .`
2. Focused agent and tool tests
3. `./.venv/bin/pytest tests/ -v`

**Live Phoenix validation**

1. Start the API Wall with a `v1-*` variant and Gemini configured.
2. Send a request designed to trigger at least one tier tool.
3. Capture `yaam_trace_id` from the API response metadata.
4. Fetch the corresponding spans through the Phoenix project spans API.
5. Confirm the trace includes request root, `yaam.agent.run_turn`, and at least one `yaam.tool.*`
   span, with nested retriever spans when the selected tool performs retrieval.

## 9. Decisions

1. The first-pass provider scope is Gemini only.
2. The first-pass rollout scope is `v1-*` variants only.
3. The implementation should use a bounded custom loop over the existing `MemoryAgent` flow rather
   than a large immediate migration to a fully LangGraph-native `ToolNode` architecture.
4. The existing tool inventory and skill-gating surfaces are reused rather than redesigned.
5. The Option A `get_context_block()` visibility gap is explicitly excluded from this plan.

## 10. Further considerations

1. If Gemini tool calling proves unstable in the current SDK path, the fallback should remain
   provider-local rather than widening first-pass scope to all providers.
2. If cleaner parent span structure requires a dedicated `yaam.workflow.reason` span, that should
   be added as part of this plan because it is tightly coupled to tool-loop observability.
3. After this plan is implemented, the next planning pass should decide between provider parity for
   tool calling and instrumentation of `get_context_block()`.