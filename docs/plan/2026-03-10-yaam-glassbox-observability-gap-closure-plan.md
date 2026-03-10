# Plan: YAAM Glass-Box Observability Gap Closure (Phoenix/OpenInference + CIAR + L3/L4 Retrieval)

**Status:** Proposed  
**Date:** March 10, 2026  
**Owners:** YAAM maintainers, observability owners, memory subsystem owners  
**Related:** [ADR-013](../ADR/013-phoenix-tracing-strategy.md), [RFC: Phoenix tracing (glass-box)](../RFC/phoenix-tracing-rfc.md), [Spec: Phoenix span contract](../specs/observability/phoenix-span-contract.md), [ADR-004](../ADR/004-ciar-scoring-formula.md)

## 1. Purpose

This plan extends the Phoenix/OpenInference “glass-box tracing” roadmap by adding the missing
mechanism work required to keep traces semantically truthful and paper/ADR-aligned.

The plan closes five concrete gaps:

1. CIAR implementation conforms to normative ADR-004.
2. L3 (Qdrant) and L4 (Typesense) retrieval becomes query-conditioned in `UnifiedMemorySystem.query_memory()`.
3. The L3 similarity tool (`l3_search_episodes`) is implemented and reachable for v1-* skill-wired variants.
4. The paper draft’s Promotion Engine section reflects the correct meaning of CIAR and the upstream source of `certainty/impact`.
5. After (2–3), the Phoenix span contract language is updated (retriever vs. enumeration) and glass-box validation is re-run in Phoenix.

Evaluation harness artifacts remain explicitly secondary and MUST NOT drive architecture decisions.

## 2. Constraints and invariants

1. The mechanism layer under `src/storage/` is frozen-by-default. This plan MUST NOT require changes to `src/storage/`.
2. Dependency changes (`pyproject.toml`, `poetry.lock`) require explicit approval and are excluded from baseline scope.
3. Span inventory and required attributes MUST follow the normative contract in `docs/specs/observability/phoenix-span-contract.md`.
4. Repository artifacts MUST NOT introduce absolute host-specific paths.
5. Secrets (`.env`, keys) MUST NOT be committed or echoed into logs.

## 3. Deliverables

1. CIAR scoring implementation matches ADR-004 formula and defaults.
2. Query-aware cross-tier retrieval in `UnifiedMemorySystem.query_memory()` for L3 and L4.
3. `l3_search_episodes` tool implemented (no longer a stub) and usable by v1-* skill-wired agents.
4. Paper draft section updated to remove CIAR terminology drift and to describe upstream sources of CIAR inputs.
5. Updated Phoenix span contract language, plus a repeatable Phoenix validation procedure and evidence report.

## 4. Workstreams and milestones

### Milestone A: CIAR (ADR-004 normative) conformance

**Goal:** CIAR behavior matches ADR-004 in code and configuration.

**Implementation requirements**

1. Update `config/ciar_config.yaml` and `src/memory/ciar_scorer.py` together so the
   effective ADR-004 defaults are enforced without introducing an uncoordinated configuration
   schema break:
   - decay rate `λ = 0.0231`,
   - reinforcement rate `α = 0.1`,
   - promotion threshold `= 0.6`,
   - and no standalone key rename in `config/ciar_config.yaml` unless the scorer parser is
     migrated in the same changeset.
2. Update `src/memory/ciar_scorer.py` to implement:
   - `score = clamp((C * I) * exp(-λ * age_days) * (1 + α * access_count), 0..1)`
3. Remove or refactor duplicate CIAR math so the repository has one normative scoring implementation:
   - `src/memory/models.py` (`Fact.mark_accessed`, `Fact.calculate_age_decay`)
   - `src/memory/tiers/working_memory_tier.py` (access tracking and score updates)
   - `src/agents/tools/ciar_tools.py` (formula explanation text must match ADR-004)
4. Ensure created-at semantics are stable:
   - prefer `created_at` when present; otherwise use `extracted_at`; otherwise treat as “now”,
   - clamp future timestamps to `age_days = 0` to prevent runtime failures.

**Acceptance criteria**

1. CIAR-related unit tests pass (CIAR tools and L2 tier CIAR update paths).
2. No component emits a CIAR score inconsistent with ADR-004 for the same inputs.

### Milestone B: Query-aware L3/L4 retrieval in `UnifiedMemorySystem.query_memory()`

**Goal:** L3 and L4 results are selected by the query string, enabling truthful “RETRIEVER” spans.

**Implementation requirements**

1. L3 default scope is session-scoped similarity search (filter by `session_id`).
2. L3 retrieval uses Qdrant vector similarity:
   - embed query via `LLMClient.get_embedding(...)`,
   - call `EpisodicMemoryTier.search_similar(query_embedding, ..., filters={session_id})`,
   - rank using returned similarity scores (normalize before applying tier weights).
3. L4 retrieval uses Typesense full-text search:
   - call `SemanticMemoryTier.search(query_text=query, ...)`,
   - rank using returned match score (normalize before applying tier weights).

**Acceptance criteria**

1. L3/L4 results vary with query input (not enumeration-only).
2. Backward compatibility is preserved when L3/L4 are not configured.

### Milestone C: Implement `l3_search_episodes` (remove stub) and toolset reachability

**Goal:** Remove the tool stub and make it usable via skills in v1-* variants.

**Implementation requirements**

1. Implement `l3_search_episodes` in `src/agents/tools/tier_tools.py`:
   - embed query via `LLMClient.get_embedding(...)`,
   - call `EpisodicMemoryTier.search_similar(...)`,
   - return JSON including episode identifiers and similarity scores.
2. Ensure tier tool adapters use the actual memory-system attribute names used by runtime memory systems (e.g., `l2_tier/l3_tier/l4_tier`).
3. In `src/agents/memory_agent.py`, keep baseline variants on `UNIFIED_TOOLS`, but for `agent_variant` starting with `v1-` expose `ALL_TOOLS` so skill gating can select tier tools.

**Acceptance criteria**

1. `l3_search_episodes` returns retrieved episodes rather than a “not implemented” error.
2. v1-* variants can reach `l3_search_episodes` through skill gating without changing baseline behavior.

### Milestone D: Paper alignment (Promotion Engine CIAR semantics)

**Goal:** Remove CIAR terminology drift and accurately describe upstream sources of `certainty/impact`.

**Implementation requirements**

1. Update `docs/notes/paper-emas-draft-ru.md`:
   - CIAR must be expanded as Certainty–Impact–Age–Recency,
   - semantic interpretation is described as upstream (topic segmentation / fact extraction), with CIAR as deterministic gating.

**Acceptance criteria**

1. Paper draft does not describe CIAR as “Context-Item-Action-Result”.
2. Paper draft does not imply CIAR scoring itself is an LLM invocation.

### Milestone E: Phoenix span contract + glass-box validation rerun

**Goal:** Ensure span contract language matches behavior and Phoenix traces are semantically correct.

**Implementation requirements**

1. Update `docs/specs/observability/phoenix-span-contract.md`:
   - require recording the retrieval query as `input.value` on retriever spans,
   - remove residual language that classifies CIAR scoring as an LLM-dependent module,
   - and keep CIAR semantics consistently documented as deterministic/tool-like unless a later
     ADR explicitly introduces an LLM-mediated scorer.
2. Re-run Phoenix validation after Milestones B–C:
   - validate `yaam.retriever.l3` and `yaam.retriever.l4` represent query-conditioned evidence selection,
   - validate CIAR spans reflect ADR-004 components and thresholds.

**Acceptance criteria**

1. Phoenix displays query-conditioned L3/L4 retriever evidence.
2. Evidence report produced under `docs/reports/` with trace IDs and screenshots/exported trace JSON.

## 5. Verification procedure

**Local validation commands (order)**

1. `./.venv/bin/ruff check .`
2. `./.venv/bin/pytest tests/ -v`

**Phoenix validation (manual)**

- Execute a request that triggers:
  - query-aware L3 and L4 retrieval, and
  - CIAR scoring in the promotion path (when applicable).
- Export trace JSON or capture screenshots for an evidence report.

## 6. Task breakdown

This section decomposes the milestone plan into execution tasks with owners, dependencies, and
verification targets. It is intended to make sequencing explicit and reviewable in a single
artifact.

### 6.1 Task table

| Task ID | Task | Scope | Primary owner | Depends on | Verification target |
|---|---|---|---|---|---|
| A1 | Finalize CIAR implementation contract | Confirm ADR-004 remains normative; confirm no isolated CIAR config-schema rename | Architecture owner | None | Milestone A wording is internally consistent and implementation-safe |
| A2 | Normalize CIAR defaults | Apply ADR-004 effective defaults in config and scorer parser together | Memory subsystem owner | A1 | `CIARScorer` uses λ=0.0231, α=0.1, threshold=0.6 |
| A3 | Replace logarithmic recency with ADR-004 linear reinforcement | Align scoring behavior with `(1 + α * access_count)` | Memory subsystem owner | A2 | Same CIAR input yields ADR-004-consistent output |
| A4 | Remove duplicate CIAR math | Consolidate or refactor CIAR computations in models, tiers, and tools | Memory subsystem owner | A3 | No code path emits a divergent CIAR score for identical inputs |
| A5 | Add CIAR conformance tests | Add unit and integration coverage for CIAR defaults and promotion-threshold behavior | Test owner | A2, A3, A4 | `./.venv/bin/pytest tests/ -v` passes with explicit CIAR assertions |
| B1 | Confirm embedding reuse path | Reuse `LLMClient.get_embedding(...)` rather than introducing a parallel embedding API | LLM owner | None | Retrieval code calls existing embedding entry point |
| B2 | Implement query-aware L3 retrieval | Replace enumeration-only L3 retrieval with session-scoped vector similarity search | Memory subsystem owner | B1 | Different queries can return different L3 results for the same session |
| B3 | Implement query-aware L4 retrieval | Replace wildcard-style L4 retrieval with text-query search | Memory subsystem owner | None | Different queries can return different L4 results where indexed data exists |
| B4 | Preserve graceful degradation | Keep `query_memory()` safe when L3 or L4 are absent or unconfigured | Memory subsystem owner | B2, B3 | Backward compatibility maintained for partially configured systems |
| C1 | Implement `l3_search_episodes` | Replace stub with embedding-backed similarity search | Agent owner | B1 | Tool returns retrieved episodes with similarity metadata |
| C2 | Align tool/runtime tier references | Ensure tier tools use the runtime memory-system attribute names actually exposed in production | Agent owner | C1 | Tier tools execute without attribute-resolution errors |
| C3 | Expose tier-capable tool pool for v1-* variants | Keep baseline variants on `UNIFIED_TOOLS`; widen v1-* variants so skill gating can reach tier tools | Agent owner | C1, C2 | v1-* skills can select tier tools; baseline behavior remains unchanged |
| D1 | Correct CIAR paper terminology | Replace incorrect CIAR expansion in the paper draft | Docs owner | A1 | No remaining “Context-Item-Action-Result” CIAR wording |
| D2 | Clarify CIAR upstream semantics in paper | Document certainty/impact as upstream signals and CIAR as deterministic gating | Docs owner | A1 | Paper no longer implies that CIAR scoring itself is an LLM invocation |
| E1 | Update retriever-span contract language | Require retriever query capture via `input.value` and align retriever semantics with implemented behavior | Observability owner | B2, B3 | Span contract matches runtime retrieval semantics |
| E2 | Remove residual CIAR-as-LLM contract language | Make the span contract consistently describe CIAR as deterministic/tool-like | Observability owner | A1 | No internal contradiction remains in the span contract |
| E3 | Re-run Phoenix validation | Collect traces after B and C are complete | Observability owner | A5, B4, C3, E1, E2 | Phoenix shows query-conditioned retriever spans and deterministic CIAR spans |
| E4 | Publish evidence report | Record trace identifiers, artifacts, and validation outcomes under `docs/reports/` | Observability owner | E3 | Reviewable evidence report exists |

### 6.2 Execution sequence

The recommended execution order is as follows:

1. Complete A1 before coding so Milestone A cannot be misread as a standalone configuration-schema change.
2. Complete A2-A5 before Phoenix validation, because CIAR spans and thresholds must be semantically truthful before they are used as evidence.
3. Complete B1-B4 before claiming query-conditioned L3/L4 retriever spans.
4. Complete C1-C3 after the retrieval path is stable enough to support the tier tool implementation.
5. Complete D1-D2 in parallel with A and B, because documentation drift does not block runtime implementation but should be corrected in the same workstream.
6. Complete E1-E4 only after A, B, and C have reached a verifiable state.

### 6.3 Work packages for implementation tracking

#### Work package WP-1: CIAR normalization

**Tasks:** A1-A5  
**Primary files:**
- `config/ciar_config.yaml`
- `src/memory/ciar_scorer.py`
- `src/memory/models.py`
- `src/memory/tiers/working_memory_tier.py`
- `src/agents/tools/ciar_tools.py`

**Exit criteria:**
1. ADR-004 effective defaults are enforced.
2. CIAR formula behavior is consistent across all call sites.
3. Tests prove conformance.

#### Work package WP-2: Query-aware retrieval

**Tasks:** B1-B4  
**Primary files:**
- `src/llm/client.py`
- `src/memory/unified_memory_system.py`
- `src/memory/tiers/episodic_memory_tier.py`
- `src/memory/tiers/semantic_memory_tier.py`

**Exit criteria:**
1. L3 retrieval is session-scoped and query-conditioned.
2. L4 retrieval is query-conditioned.
3. Systems without L3/L4 remain operational.

#### Work package WP-3: Tier-tool reachability

**Tasks:** C1-C3  
**Primary files:**
- `src/agents/tools/tier_tools.py`
- `src/agents/memory_agent.py`
- `src/agents/tools/__init__.py`

**Exit criteria:**
1. `l3_search_episodes` is no longer a stub.
2. Tier tools resolve the runtime memory-system interfaces correctly.
3. v1-* skill-wired variants can reach tier tools without changing baseline variants.

#### Work package WP-4: Documentation and validation alignment

**Tasks:** D1-D2, E1-E4  
**Primary files:**
- `docs/notes/paper-emas-draft-ru.md`
- `docs/specs/observability/phoenix-span-contract.md`
- `docs/reports/*.md`

**Exit criteria:**
1. The paper and span contract are semantically aligned with ADR-004 and the implemented runtime.
2. Phoenix evidence is re-collected after the runtime changes land.
3. Reviewers can trace each claim in this plan to either code or an evidence report.

## 7. Post-validation execution branch: Option A before Option B

The first live Phoenix retriever validation completed after WP-4 established an important project
boundary. The API-Wall request path now emits a coherent live span chain
(`yaam.api_wall.chat_completions -> yaam.agent.run_turn -> yaam.workflow.retrieve -> yaam.retriever.*`),
but routine `POST /v1/chat/completions` requests still default to `skip_l1_write=true`. As a
result, the current API-Wall validation path proves span reachability and correlation, but it does
not yet prove that the same production-facing route can expose rich retrieved-memory evidence from a
freshly written session.

This creates two follow-on options that must be sequenced deliberately.

### Option A: Controlled write-enabled API-Wall evidence collection

**Research objective:** Strengthen the evidentiary value of Phoenix traces for the core YAAM claim
that memory-layer activity is inspectable through the API-Wall execution boundary.

**Decision:** Implement Option A before Option B.

**Implementation requirements**

1. Preserve the current API-Wall default behavior for benchmark-style traffic unless an explicit,
   controlled override is provided. The repository already contains plans that rely on
   `skip_l1_write=true` as the default benchmark posture; this MUST NOT be broken by an
   unreviewed default inversion.
2. Allow `POST /v1/chat/completions` to accept a controlled per-request metadata override for
   `skip_l1_write` so Phoenix experiments can enable write-through behavior without bypassing the
   API Wall.
3. Keep ADR-009 semantics intact: the preferred evidence path remains the public API Wall, not only
   the internal `POST /run_turn` wrapper endpoint.
4. Re-run the Phoenix validation workflow through the API Wall and confirm that live retriever spans
   still nest correctly while now carrying non-empty `retrieval.documents` when retrievable content
   exists.

**Why Option A comes first**

1. It improves the quality of the research evidence without changing core agent reasoning behavior.
2. It separates an observability/evidence gap from a future agent-capability change.
3. It preserves methodological clarity for the paper and ADR trail: first prove truthful live
   memory retrieval visibility, then expand the agent's execution model.

### Option B: End-to-end tier-tool execution in normal requests

**Research objective:** Upgrade YAAM from retriever-visible execution to tool-mediated cognitive
execution that is also visible in Phoenix.

**Implementation requirements**

1. Add a real tool-calling path in `src/agents/memory_agent.py` so the existing instrumented tier
   tools in `src/agents/tools/tier_tools.py` execute during ordinary API-Wall requests.
2. Ensure the resulting trace tree preserves correct parent-child relationships from the request
   root through agent and workflow spans into `yaam.tool.*` and nested retriever spans.
3. Evaluate the change as both an observability enhancement and an agent-runtime semantic change,
   because it affects behavior, prompting, and regression risk beyond tracing alone.

**Execution document:** [MemoryAgent tool-calling loop plan](2026-03-10-memoryagent-tool-calling-loop-plan.md)

**First-pass scope decisions**

1. The initial rollout is limited to `v1-*` variants; baseline variants remain unchanged.
2. The initial provider scope is Gemini only; provider parity is deferred.
3. The `get_context_block()` visibility gap identified by Option A remains explicitly out of scope
   for this implementation pass.

**Why Option B is second**

1. It is no longer a narrow tracing patch; it changes the execution semantics of the MemoryAgent.
2. It carries materially higher regression risk than Option A.
3. It is easier to review and justify after the API-Wall evidence path already produces rich live
   retrieval traces.

### Post-validation acceptance sequence

1. Complete Option A and publish a dated evidence artifact showing live API-Wall traces with both
   correct structure and meaningful retrieval payloads.
2. Only then open Option B as a separate implementation pass for end-to-end `yaam.tool.*`
   visibility in normal requests.
3. Treat Option B evidence as a second-stage claim: not merely that YAAM retrieves memory, but that
   YAAM can explicitly select and execute memory tools within the observable request flow.
