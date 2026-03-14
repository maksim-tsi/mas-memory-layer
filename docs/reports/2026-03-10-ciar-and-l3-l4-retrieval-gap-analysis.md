# CIAR and L3/L4 Retrieval Gap Analysis Report

**Date:** March 10, 2026  
**Status:** Analysis completed (no implementation changes in this report)  
**Audience:** Maintainers, paper authors, YAAM runtime owners, observability owners  

## 1. Executive Summary

This report documents a codebase-level validation of two concerns raised during review of the Phoenix “glass-box” tracing documentation:

1. **CIAR scoring is deterministic, but its inputs are often LLM-derived.** The CIAR computation itself is an arithmetic function and should not be represented as an LLM invocation. However, the primary signals that CIAR consumes (notably `certainty` and `impact`) are typically produced by upstream LLM-dependent modules (topic segmentation and fact extraction) in the current implementation.
2. **Cross-tier retrieval is currently not query-conditioned for L3 and L4 in the unified query path.** The `UnifiedMemorySystem.query_memory()` method accepts a query string, but L3 and L4 retrievals are currently implemented as enumerations ordered by tier-native scores rather than semantic/full-text retrieval driven by the query. As a result, labeling those spans as “retriever” operations (in Phoenix/OpenInference terms) would overstate current behavior.

In addition to confirming those two high-level concerns, the analysis identified a third, independent inconsistency: **ADR-004 defines a single “official” CIAR formula and parameterization that does not match the current runtime implementation** (`CIARScorer` + `config/ciar_config.yaml`).

## 2. Scope and Evidence Sources

The analysis was performed against the local repository checkout (GitHub-synchronized), without access to any remote host state.

Primary evidence sources:

- Paper draft: `docs/notes/paper-emas-draft-ru.md`
- CIAR ADR: `docs/ADR/004-ciar-scoring-formula.md`
- CIAR runtime implementation: `src/memory/ciar_scorer.py`, `config/ciar_config.yaml`
- LLM-dependent modules emitting CIAR inputs: `src/memory/engines/topic_segmenter.py`, `src/memory/engines/fact_extractor.py`
- Unified cross-tier retrieval: `src/memory/unified_memory_system.py`
- Tier capabilities:
  - L3 vector similarity: `src/memory/tiers/episodic_memory_tier.py` (`search_similar`)
  - L4 full-text search: `src/memory/tiers/semantic_memory_tier.py` (`search`)
- Agent-access tools:
  - L3 similarity tool stub: `src/agents/tools/tier_tools.py` (`l3_search_episodes`)
  - L4 full-text tool: `src/agents/tools/tier_tools.py` (`l4_search_knowledge`)
- Skills (policy-level instructions): `skills/l3-similar-episodes/SKILL.md`, `skills/l4-knowledge-synthesis/SKILL.md`

## 3. Findings

### 3.1 Paper draft mis-defines CIAR

The paper draft currently expands CIAR as “Context-Item-Action-Result” and describes an “LLM classifier” producing a single significance score inside the promotion mechanism.

Evidence:

- `docs/notes/paper-emas-draft-ru.md:87-90`

This is inconsistent with the repository’s CIAR definition, which is consistently used elsewhere as **Certainty–Impact–Age–Recency** and implemented as an interpretable scoring function for promotion gating.

### 3.2 CIAR scoring is deterministic (not an LLM call), but commonly consumes LLM-derived inputs

CIAR computation is implemented as deterministic arithmetic over four components:

- `certainty` (explicit field preferred, otherwise heuristics/default),
- `impact` (explicit field preferred, otherwise weights and simple heuristics),
- `age_decay` (exponential decay),
- `recency_boost` (logarithmic boost in current implementation).

Evidence:

- `src/memory/ciar_scorer.py:90-128` (deterministic formula application)
- `src/memory/ciar_scorer.py:130-163` (certainty priority: explicit → heuristics → default)
- `src/memory/ciar_scorer.py:165-204` (impact priority: explicit → weights/heuristics)
- `config/ciar_config.yaml` (parameters and explicit recency boost formula)

However, the typical “happy path” for `certainty` and `impact` is LLM-derived:

- `TopicSegmenter` uses an LLM call with structured output and produces segments with `certainty` and `impact`.
- `FactExtractor` uses an LLM call with structured output and emits `Fact(certainty=..., impact=...)`.

Evidence:

- `src/memory/engines/topic_segmenter.py` (LLM-based segmentation; emits `certainty`/`impact`)
- `src/memory/engines/fact_extractor.py:72-116` (LLM extraction; assigns `certainty`/`impact`)

Conclusion:

- **CIAR is not itself an LLM-dependent module in the narrow technical sense (no LLM invocation occurs during scoring).**
- **CIAR is nevertheless an LLM-assisted gate in the common pipeline, because it typically consumes LLM-derived features.**

### 3.3 ADR-004’s “official formula” is not the current runtime formula

ADR-004 states that the project adopts a single official CIAR model:

```
CIAR = (Certainty × Impact) × exp(-λ × days_since_creation) × (1 + α × access_count)
```

with parameter defaults including λ≈0.0231 (half-life ≈ 30 days) and linear reinforcement.

Evidence:

- `docs/ADR/004-ciar-scoring-formula.md:42-71`

The current runtime implementation differs materially:

- `config/ciar_config.yaml` uses λ=0.1 (documented as “~10% per day”), includes `min_score`, and defines a **logarithmic** recency boost:
  - `1 + (boost_factor * log(1 + access_count))` with a cap.

Evidence:

- `config/ciar_config.yaml`
- `src/memory/ciar_scorer.py` (`_calculate_age_decay`, `_calculate_recency`)

Implication:

- ADR-004 cannot currently be treated as the single source of truth for CIAR scoring behavior, and paper-level claims about CIAR must be made carefully until ADR and implementation are reconciled.

### 3.4 UnifiedMemorySystem.query_memory() does not use the query for L3 and L4 retrieval

`UnifiedMemorySystem.query_memory(session_id, query, ...)` is documented as “Hybrid semantic search across L2, L3, and L4 tiers”, but its behavior is presently:

- **L2**: may use `search_facts(query=...)` when available.
- **L3**: uses `l3_tier.query(filters={"session_id": session_id})` (graph enumeration by session) and does not use the query string.
- **L4**: uses `l4_tier.query(limit=...)` which resolves to wildcard text search and does not use the query string.

Evidence:

- `src/memory/unified_memory_system.py:330-473` (entire method)
- L3: `src/memory/unified_memory_system.py:401-406`
- L4: `src/memory/unified_memory_system.py:437-444`
- L4 `query()` semantics: `src/memory/tiers/semantic_memory_tier.py:271-289` (`query_text="*"`)

Conclusion:

- If Phoenix spans are labeled as “retriever” operations for L3/L4 under the unified query path, Phoenix would visually imply query-driven evidence selection that does not currently occur.

### 3.5 L3 and L4 retrieval capabilities exist, but are not fully wired for agent use

Capabilities:

- L3 supports vector similarity via `EpisodicMemoryTier.search_similar(query_embedding, ...)`.
- L4 supports full-text search via `SemanticMemoryTier.search(query_text, ...)`.

Evidence:

- `src/memory/tiers/episodic_memory_tier.py` (`search_similar`)
- `src/memory/tiers/semantic_memory_tier.py` (`search`)

Agent-facing tools:

- `l4_search_knowledge` calls `SemanticMemoryTier.search()` and appears implementable end-to-end.
- `l3_search_episodes` is currently a stub that returns an explicit “not yet implemented” error, despite the repository containing embedding generation capability in `LLMClient.get_embedding()`.

Evidence:

- L3 tool stub: `src/agents/tools/tier_tools.py:242-289`
- Embeddings exist: `src/llm/client.py:305-322`

Skills:

- Policy instructions for both L3 similarity retrieval and L4 knowledge synthesis exist under `skills/`, but L3 cannot satisfy its skill contract until the tool is implemented.

Evidence:

- `skills/l3-similar-episodes/SKILL.md`
- `skills/l4-knowledge-synthesis/SKILL.md`

## 4. Implications for Phoenix “Glass-Box” Tracing

The “glass-box” objective is undermined if tracing presents retrieval evidence that is not actually conditioned on the query. Therefore:

- Until L3/L4 retrieval is query-conditioned in either the unified path or the tool path, Phoenix “retriever” spans for L3/L4 should be treated as aspirational or labeled as enumeration.
- CIAR should be traced as an internal scoring step (deterministic), while separately tracing the upstream LLM modules that provide `certainty`/`impact`.

## 5. Recommendations (No Changes to src/storage/)

### 5.1 Reconcile paper and repository CIAR terminology

- Correct CIAR expansion in the paper draft to **Certainty–Impact–Age–Recency**.
- Describe semantic feature production (certainty/impact) as upstream LLM-assisted extraction/segmentation, followed by deterministic CIAR gating.

### 5.2 Reconcile ADR-004 with runtime CIAR implementation

Select one of the following and enforce it consistently:

1. **Adopt ADR-004 as normative** and update `CIARScorer` + `ciar_config.yaml` to match ADR-004 (linear reinforcement, λ default).
2. **Update ADR-004** to match the current implementation (logarithmic reinforcement + caps + different λ) and explicitly justify the deviation.

Given that ADR-004 frames itself as the “sole official model”, option (1) is typically preferable if ADR-004 is already accepted as a mechanism contract.

### 5.3 Implement query-conditioned L3/L4 retrieval in the unified path

- L3: embed `query` and call `EpisodicMemoryTier.search_similar(...)` rather than `query(filters=...)`.
- L4: call `SemanticMemoryTier.search(query_text=query, ...)` rather than `query("*")`.

### 5.4 Implement the L3 similarity tool to satisfy the existing skill contract

- Implement `l3_search_episodes` in `src/agents/tools/tier_tools.py` using:
  - `LLMClient.get_embedding()` to embed the query text, and
  - `EpisodicMemoryTier.search_similar(...)` to retrieve episodes.

### 5.5 Align agent policy with the intended “IR query formulation” behavior

The architecture narrative expects agents to formulate an explicit retrieval query when additional evidence is needed. Operationalizing this requires one (or both) of:

- A policy-level skill and routing strategy that selects L3/L4 retrieval tools under relevant intents, or
- A unified retrieval planner that rewrites user input into a retrieval query (possibly LLM-assisted), then calls query-conditioned tier retrieval.

## 6. Proposed Next Steps

1. Decide whether ADR-004 is normative for CIAR; produce a short change set to reconcile either code→ADR or ADR→code.
2. Wire L3/L4 query-aware retrieval in `UnifiedMemorySystem.query_memory()`.
3. Implement `l3_search_episodes` tool to remove the current stub.
4. Update the paper draft section on Promotion Engine to reflect the actual CIAR meaning and the upstream source of certainty/impact.
5. After (2–3), update Phoenix span contract language (retriever vs enumeration) to match behavior and re-run “glass-box” trace validation.

