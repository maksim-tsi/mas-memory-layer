# CIAR Design and Implementation Audit

**Date:** 2026-05-18
**Status:** Completed audit, no implementation changes in this report
**Audience:** YAAM maintainers, runtime owners, paper authors
**Related:** [ADR-004](../ADR/004-ciar-scoring-formula.md), [ADR-007](../ADR/007-agent-integration-layer.md), [EMAS reviewer feedback RFC](../RFC/2026-03-28-emas-reviewer-feedback-rfc.md)

## 1. Executive Summary

CIAR is useful as a simple, interpretable baseline policy for L1 -> L2 promotion, but it should not be treated as an optimal memory algorithm. The current implementation mostly matches the accepted ADR-004 formula after earlier reconciliation work, and this is an improvement over the March 10 report. The remaining issues are not in the arithmetic formula itself. They are in calibration, feature provenance, the promotion pipeline, and retrieval-time use of CIAR.

The key conclusion is:

- Keep CIAR v1 as a deterministic, explainable promotion gate.
- Stop presenting it as a complete cognitive memory policy.
- Add a stronger second-stage memory policy that separates evidence quality, task utility, contradiction handling, and query relevance.
- Make CIAR observable and callable through a future MCP interface, but do not make MCP depend on CIAR. MCP should expose both raw tier operations and higher-level policy operations.

## 2. Questions Answered

### Is CIAR optimal?

No. CIAR is a defensible baseline because it is cheap, deterministic, tunable, and explainable. It is not optimal because it compresses several independent concerns into one scalar:

1. belief quality: whether the fact is true,
2. utility: whether the fact matters,
3. retention: whether it should persist,
4. retrieval priority: whether it is useful for this query,
5. evidence quality: whether provenance is strong enough to trust.

These are related, but they are not the same objective. A single scalar is acceptable for L1 -> L2 promotion, but it is too coarse as the long-term policy for a polyglot memory system.

### Does CIAR meet YAAM's current goals?

Partially. It meets the narrow current goal of L1 -> L2 significance filtering. It does not fully meet the broader goals implied by the paper and reviewer feedback:

- "progressive disclosure" requires a query-aware evidence policy, not only retention scoring;
- "retrieval-reasoning gap" mitigation requires structured evidence presentation and conflict handling;
- "polyglot memory" requires per-tier operation and cross-tier fusion with stable score semantics;
- "cognitive stabilizer" requires measured outcome improvements, not only a promotion formula.

### Is the code implemented as documented?

Mostly yes for ADR-004's core formula, with several important caveats:

- `src/memory/ciar_formula.py`, `src/memory/ciar_scorer.py`, and `config/ciar_config.yaml` now implement the ADR-004 exponential age decay plus linear recency reinforcement model.
- `Fact.validate_ciar_score()` recomputes `ciar_score` from stored components, which enforces consistency but can override caller intent when a route tries to set a high score with lower components.
- `PromotionEngine` scores segments before extracting facts, then floors each extracted fact's CIAR score to the promotion threshold. This weakens fact-level filtering.
- `CIARScorer` docstrings still describe recency as `1.0-1.3`, while config allows unbounded reinforcement before final score clamping.
- Older docs and reports contain stale claims from before the CIAR reconciliation and should be marked historical or superseded.

## 3. Evidence Sources

Primary implementation evidence:

- `src/memory/ciar_formula.py`
- `src/memory/ciar_scorer.py`
- `config/ciar_config.yaml`
- `src/memory/models.py`
- `src/memory/engines/promotion_engine.py`
- `src/memory/unified_memory_system.py`
- `src/agents/tools/ciar_tools.py`
- `src/agents/tools/tier_tools.py`
- `src/agents/tools/unified_tools.py`
- `src/api/v2_router.py`

Primary design evidence:

- `docs/ADR/004-ciar-scoring-formula.md`
- `docs/ADR/007-agent-integration-layer.md`
- `docs/ADR/009-decoupling-benchmark-api-wall.md`
- `docs/RFC/RFC014 - YAAM Semantic Gateway API (v2).md`
- `docs/api/TRA_Integration_Guide_v2.md`
- `docs/reports/2026-03-10-ciar-and-l3-l4-retrieval-gap-analysis.md`
- `docs/RFC/2026-03-28-emas-reviewer-feedback-rfc.md`

MCP reference evidence:

- Official MCP 2025-11-25 overview: https://modelcontextprotocol.io/specification/2025-11-25/basic
- Official MCP tools spec: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- Official MCP resources spec: https://modelcontextprotocol.io/specification/2025-11-25/server/resources
- Official MCP prompts spec: https://modelcontextprotocol.io/specification/2025-11-25/server/prompts

## 4. Current CIAR Implementation

The current normative formula is:

```text
CIAR = clamp((certainty * impact) * exp(-lambda * age_days) * (1 + alpha * access_count), 0, 1)
```

Current defaults:

- promotion threshold: `0.6`
- age decay lambda: `0.0231`
- recency alpha: `0.1`
- recency max boost: `null`

The formula is centralized in `src/memory/ciar_formula.py`. `CIARScorer` loads `config/ciar_config.yaml`, derives missing certainty and impact values, computes age decay and recency boost, and clamps the final score to `[0, 1]`.

This is now aligned with ADR-004's accepted model. The earlier report from 2026-03-10 correctly identified a mismatch at that time, but parts of that report are now stale because runtime has since been reconciled.

## 5. Findings

### F1. CIAR arithmetic is consistent, but documentation comments still drift

`CIARScorer` still says recency boost is `1.0-1.3` in docstrings and examples. The actual config keeps `max_boost: null`, so reinforcement can grow linearly before the final score is clamped. This is not a runtime bug, but it is an explanation bug.

Recommended fix:

- Update docstrings and docs to say "1.0 or higher, optionally capped by config, final score clamped to [0, 1]".
- Add a short ADR-004 note that storage clamps the final score even though reinforcement is mathematically unbounded.

### F2. `Fact` validation can silently override explicit `ciar_score`

`Fact.validate_ciar_score()` recomputes `ciar_score` when `certainty`, `impact`, `age_decay`, and `recency_boost` are present. This is desirable for consistency, but it creates surprising behavior in routes that pass `ciar_score=1.0` with lower components.

Example risk:

- `src/api/v2_router.py` creates L2 facts with `ciar_score=1.0`, `certainty=0.8`, `impact=0.5`.
- The model validator can reduce the stored score toward `0.4`.

Recommended fix:

- Treat component fields as authoritative and avoid setting inconsistent `ciar_score`.
- Add tests that assert v2 L2 store behavior uses the intended score.
- If forced insertion is needed, model it explicitly as `source_type="manual"` or `override_reason`, not by contradicting components.

### F3. Promotion floors fact scores to the threshold

`PromotionEngine.process_session()` promotes a segment when the segment score passes the threshold. It then extracts facts and sets:

```python
fact.ciar_score = max(self.scorer.calculate(fact), self.promotion_threshold)
```

This means every fact extracted from an accepted segment is at least promotable, even if the fact-level score is below the threshold. That makes sense as a segment-level retention policy, but it is not fact-level CIAR filtering.

Recommended fix:

- Replace unconditional flooring with explicit policy modes:
  - `segment_gate`: segment score admits all extracted facts, fact score remains honest.
  - `fact_gate`: each extracted fact must independently pass the threshold.
  - `hybrid_gate`: segment admits extraction, but fact below threshold is stored only as low-confidence evidence or discarded.
- Record both `segment_ciar_score` and `fact_ciar_score` in metadata.
- Preserve current behavior only if explicitly configured for benchmark continuity.

### F4. CIAR depends on LLM-derived upstream features in the common path

CIAR scoring is deterministic. However, the usual path gets `certainty` and `impact` from LLM-mediated topic segmentation and fact extraction. That means CIAR is not an LLM call, but it is often an LLM-feature gate.

Recommended fix:

- Trace CIAR as deterministic scoring.
- Trace feature provenance separately: rule-derived, user-supplied, LLM-extracted, segment-inherited.
- Include feature provenance in CIAR explanations and future MCP outputs.

### F5. CIAR does not model contradictions or supersession

CIAR can keep a highly accessed old fact alive even if a newer fact contradicts it. The current formula has no native notion of:

- contradiction,
- validity interval,
- source authority,
- explicit user correction,
- domain-specific expiry.

YAAM has fields that can support some of this, but CIAR itself does not enforce the policy.

Recommended fix:

- Add a contradiction/supersession layer above CIAR.
- Use CIAR for retention priority, not truth resolution.
- Make the Evidence Table / retrieval-reasoning-gap mitigation skill show conflicting facts and provenance.

### F6. Cross-tier retrieval scoring is not yet a stable memory policy

`UnifiedMemorySystem.query_memory()` merges L2, L3, and L4 results with tier weights and per-tier min-max normalization. This is pragmatic, but it is fragile:

- If all scores in a tier are equal, normalization returns `0.5`.
- L2 CIAR, L3 similarity/importance, and L4 confidence/search scores are not semantically equivalent.
- Final rank is sensitive to small candidate sets and tier weights.

Recommended fix:

- Keep the current weighted merge as baseline.
- Introduce a second-stage `EvidenceRanker` that separates retrieval score, retention score, evidence quality, freshness, and tier prior.
- Require structured output with per-factor scores so Phoenix and MCP clients can inspect why evidence was selected.

### F7. Agent-facing CIAR tools are useful but not product-ready as MCP tools

`src/agents/tools/ciar_tools.py` exposes `ciar_calculate`, `ciar_filter`, and `ciar_explain`. These are good development tools, but MCP should return structured content and stable schemas rather than only prose strings. The current tools also instantiate `CIARScorer()` per call and include UI symbols in returned text.

Recommended fix:

- Keep LangChain tools for current agent integration.
- Add a shared service layer for CIAR operations.
- Expose MCP tools with explicit input and output schemas:
  - `yaam.ciar.calculate`
  - `yaam.ciar.explain`
  - `yaam.ciar.filter`
- Return `structuredContent` plus a short text summary, following the MCP tool result model.

### F8. Reviewer feedback supports a sharper engineering boundary

The EMAS feedback is mostly about paper clarity, but it gives useful engineering constraints:

- "Working memory" vs "long-term memory" terminology must map to implemented behavior, not database names.
- Neo4j should not be described as relational memory; it is graph storage used inside the L3 episodic layer.
- "Cognitive stabilizer" must be either measured or removed.
- "Retrieval-Reasoning Gap" needs a distinct mechanism beyond long-context criticism.
- Skills and Evidence Table naming must be consistent and traceable to code or docs.

For code/RFC work, this means YAAM should expose memory operations in three layers:

1. raw tier access,
2. unified retrieval,
3. agentic policy and evidence reasoning.

That directly supports the planned "dumb" and "smart" YAAM modes.

## 6. Better Than CIAR

The immediate replacement should not be a black-box learned ranker. The next step should be a policy stack that keeps CIAR as one signal.

### Option A: CIAR v1 retained as promotion gate

Use CIAR only for L1 -> L2 retention. Keep current formula and improve telemetry, docs, and tests.

This is the lowest-risk baseline.

### Option B: Multi-factor Memory Utility Score

Define a structured score:

```text
memory_utility =
  w_retention * ciar_retention
+ w_relevance * query_relevance
+ w_evidence * evidence_quality
+ w_freshness * temporal_validity
+ w_authority * source_authority
- w_conflict * contradiction_penalty
```

This is better than CIAR for retrieval and context injection because it is query-aware and provenance-aware.

### Option C: Two-stage policy

Use:

1. CIAR for cheap promotion and retention,
2. EvidenceRanker for retrieval-time ranking,
3. Evidence Table for reasoning-time presentation.

This is the recommended path.

### Option D: Learned or adaptive policy

Use benchmark traces and user outcomes to tune thresholds or weights. This should come after structured telemetry and controlled evaluations exist. Otherwise it risks optimizing benchmark artifacts rather than improving memory behavior.

## 7. Recommended Engineering Plan

### Phase 1: CIAR conformance and observability

1. Update stale CIAR docstrings.
2. Add tests for `Fact` score recomputation in v2 storage paths.
3. Add tests for the promotion-floor behavior and decide whether to preserve it as a named policy mode.
4. Add feature provenance to CIAR explanations.

### Phase 2: Evidence policy

1. Introduce `EvidenceRanker` above tier retrieval, outside `src/storage/`.
2. Return per-factor ranking explanations.
3. Add conflict/supersession metadata handling.
4. Implement the Evidence Table as a named policy artifact, not an ambiguous skill alias.

### Phase 3: MCP-compatible service layer

1. Extract stable service functions behind current LangChain tools and REST routes.
2. Add MCP tools/resources/prompts as a separate adapter over the same service layer.
3. Keep the API Wall for OpenAI-compatible benchmark and production parity.
4. Expose dumb and smart YAAM through capability tiers rather than separate code paths.

## 8. Acceptance Criteria

CIAR v1 can be considered solid when:

- ADR-004, config, scorer, model validator, tools, and docs describe the same behavior.
- Promotion can report segment score and fact score separately.
- v2 routes do not create inconsistent fact components and scores.
- Tests cover clamping, high access counts, explicit component overrides, stale facts, and promotion policy modes.
- Phoenix spans and future MCP outputs expose CIAR inputs, score, threshold, decision, and provenance.

The broader memory policy can be considered stronger than CIAR when:

- retrieval ranking is query-aware,
- evidence quality is visible,
- contradictions are surfaced rather than hidden,
- context injection can explain why each memory item was included,
- raw, unified, and agentic modes are all available through documented interfaces.
