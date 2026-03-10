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

1. Update `config/ciar_config.yaml` to ADR-004 keys and defaults:
   - `lambda_decay: 0.0231`
   - `alpha_reinforcement: 0.1`
   - `promotion_threshold: 0.6`
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
   - require recording the retrieval query as `input.value` on retriever spans.
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
