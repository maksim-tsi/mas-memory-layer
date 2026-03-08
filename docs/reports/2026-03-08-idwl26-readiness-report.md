# YAAM Readiness Report for the IDWL 2026 "Sandwich Architecture" Baseline

## 1. Executive Verdict

| Requirement | Verdict | Short Answer | Runnable Today Without Repo Changes |
| --- | --- | --- | --- |
| Artifact Versioning & State Tracking | Partial | YAAM can store multiple states of the same decision flow across tiers, but it does not provide a first-class artifact/version lineage model for `v1 -> v2` transitions. | No |
| Tier-Specific Segregation (L1/L2 vs. L4) | Partial | The tier model supports keeping transient execution data in L1/L2 and only committing durable outputs to L4, but this must be enforced by orchestration convention rather than a policy-safe artifact API. | Partial |
| Auditability & Provenance | Partial | YAAM includes provenance fields and can preserve source links across L2, L3, and L4, but it does not automatically capture the full causal trail for "solver IIS caused artifact revision." | No |
| Tool Compatibility | No | The existing tool set is not sufficient to execute the sandwich flow end-to-end without custom memory-side extensions or tool/runtime fixes. | No |

**Overall recommendation:** `YAAM is usable with strict orchestration conventions`, but it is **not sufficient as-is** for this baseline if strict artifact revision tracking and auditability are required.

## 2. Scenario Mapping

### Step 1: Upstream LLM generates Artifact v1

- The raw routing payload can be stored as a transient execution record in L1 via `TurnData` in [`src/memory/models.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/models.py) and `ActiveContextTier.store()` in [`src/memory/tiers/active_context_tier.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/tiers/active_context_tier.py).
- This is a workable mapping for "artifact as message/turn," but YAAM has no dedicated `Artifact` or `DecisionObject` model.
- If the payload is promoted to L2, it would become a `Fact`, which is a significance-scored natural-language memory object rather than a structured versioned artifact.

### Step 2: Solver fails and returns an IIS log

- The raw IIS log fits naturally in L1 as another `TurnData` item.
- If the IIS result needs short-term retention beyond the L1 buffer, it can be promoted into L2 as a `Fact` with provenance fields such as `source_uri`, `topic_segment_id`, and `justification`.
- This preserves the fact that "a solver failure occurred," but not a typed computational failure object with structured links to a specific artifact revision.

### Step 3: LLM produces Artifact v2

- Artifact v2 can be stored as another L1 transient record or as another L2 fact-like record.
- YAAM can therefore hold both v1 and v2 in the same session context, but the relationship "v2 supersedes v1" must be encoded manually in content or metadata.
- No current model enforces monotonic revision numbers, supersession semantics, or optimistic/append-only artifact history.

### Step 4: Final verified artifact is committed

- If the final result is generalized knowledge, it maps to `KnowledgeDocument` in L4 via `SemanticMemoryTier.store()` in [`src/memory/tiers/semantic_memory_tier.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/tiers/semantic_memory_tier.py).
- If the final result must remain a specific decision payload rather than distilled knowledge, L4 is only a partial fit: `KnowledgeDocument` is designed for durable insights, rules, and patterns, not structured decision-state snapshots.
- The final verified artifact can be committed to L4 by convention, but YAAM does not distinguish "final verified decision artifact" from other knowledge documents at the type-system level.

## 3. Requirement-by-Requirement Analysis

### 3.1 Artifact Versioning & State Tracking

**Answer:** `Partial`

YAAM can track multiple memory records associated with the same session, but it cannot natively model a decision artifact evolving from infeasible `v1` to feasible `v2` as a first-class version chain.

Evidence:

- `Fact` contains provenance-oriented fields such as `source_uri`, `source_type`, `topic_segment_id`, `topic_label`, `metadata`, and `justification` in [`src/memory/models.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/models.py).
- `Episode` preserves `source_fact_ids` and bi-temporal fields such as `fact_valid_from` and `fact_valid_to`, also in [`src/memory/models.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/models.py).
- `KnowledgeDocument` preserves `source_episode_ids` and `provenance_links`, again in [`src/memory/models.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/models.py).

What YAAM can do:

- Store artifact v1 and v2 as separate L1 entries.
- Promote selected elements of those entries into L2 `Fact` records.
- Consolidate related facts into L3 `Episode` objects.
- Distill durable outcomes into L4 `KnowledgeDocument` objects.

What YAAM cannot do natively:

- Represent a typed "artifact id" with multiple revisions.
- Express `v2 replaces v1` as a structured relation.
- Enforce append-only version history for a JSON decision object.
- Preserve the full structured payload lifecycle without reducing it to turns, facts, episodes, or knowledge documents.

Bottom line:

- YAAM supports **memory of successive states**, not **artifact version control**.
- For the sandwich baseline, state tracking is possible only if the agent explicitly writes artifact identifiers and revision metadata into content or `metadata`.

### 3.2 Tier-Specific Segregation (L1/L2 vs. L4)

**Answer:** `Partial`

The four-tier architecture is explicitly designed for this separation, and the current implementation broadly supports it, but there is no hard policy mechanism that guarantees only the final verified artifact reaches L4.

Evidence:

- ADR-003 defines L1 as raw/ephemeral, L2 as significant facts, L3 as episodes, and L4 as distilled knowledge in [`docs/ADR/003-four-layers-memory.md`](/Users/max/Documents/code/mas-memory-layer/docs/ADR/003-four-layers-memory.md).
- `ActiveContextTier` stores raw turns in Redis with PostgreSQL backup and TTL behavior in [`src/memory/tiers/active_context_tier.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/tiers/active_context_tier.py).
- `WorkingMemoryTier` stores CIAR-filtered `Fact` objects in PostgreSQL in [`src/memory/tiers/working_memory_tier.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/tiers/working_memory_tier.py).
- `SemanticMemoryTier` stores `KnowledgeDocument` records in Typesense in [`src/memory/tiers/semantic_memory_tier.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/tiers/semantic_memory_tier.py).

Fit to the scenario:

- Raw IIS log: strong fit for L1, acceptable fit for L2 if promoted.
- Failed Artifact v1: acceptable fit for L1, weak-to-acceptable fit for L2.
- Final verified Artifact v2: possible fit for L4 only if treated as durable knowledge rather than a structured decision-state object.

Important limitation:

- `memory_store` only exposes `L1`, `L2`, and `auto` writes, and its `L2` path actually writes into L1 and waits for later promotion. It does not directly store a `Fact`, and it offers no L4 write path. See [`src/agents/tools/unified_tools.py`](/Users/max/Documents/code/mas-memory-layer/src/agents/tools/unified_tools.py).
- Distillation to L4 is lifecycle-driven through `DistillationEngine`, not a direct "commit final artifact to L4" tool operation. See [`src/memory/engines/distillation_engine.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/engines/distillation_engine.py).

Bottom line:

- The **tier separation concept is present and implementable**.
- The **specific workflow control required by this scenario is not exposed as a safe first-class agent tool flow**.

### 3.3 Auditability & Provenance

**Answer:** `Partial`

YAAM supports provenance fields and lineage fragments, but it does not automatically capture the full cognitive/computational explanation chain required for strict auditability of solver-driven artifact revision.

Evidence:

- `Fact.source_uri` and `Fact.justification` preserve where a fact came from and why it was extracted in [`src/memory/models.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/models.py).
- `PromotionEngine` emits segment/fact-level telemetry with `justification` and writes `source_uri` values such as `l1:{session_id}:segment:{segment_id}` in [`src/memory/engines/promotion_engine.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/engines/promotion_engine.py).
- `Episode.source_fact_ids` provides L3 back-links to L2 facts in [`src/memory/models.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/models.py).
- `KnowledgeDocument.source_episode_ids` and `provenance_links` provide L4 back-links to L3 in [`src/memory/models.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/models.py).

What is supported:

- L2 fact provenance back to L1 segments/turns.
- L3 episode provenance back to L2 facts.
- L4 knowledge provenance back to L3 episodes.

What is missing for the sandwich scenario:

- No native model for a solver invocation, solver output, or IIS conflict object.
- No first-class link that says: "Artifact v2 was created because SCIP reported capacity infeasibility for Artifact v1."
- No automatic causal edge from failed computational step to revised artifact.
- `DistillationEngine.distill(track_provenance=True)` preserves episode references, but `_create_knowledge_document()` does not actually populate `provenance_links` with a richer causal explanation trail. See [`src/memory/engines/distillation_engine.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/engines/distillation_engine.py).

Bottom line:

- YAAM has **traceability primitives**.
- YAAM does **not have complete audit-chain automation** for this baseline without additional schema or orchestration work.

### 3.4 Tool Compatibility

**Answer:** `No`

The current tool set is not sufficient for the sandwich flow as described.

The main reasons are:

- There is no existing tool that directly stores a structured artifact revision to L2 or L4.
- There is no tool that explicitly records provenance links between solver output and revised artifact.
- There is no tool that commits a final verified artifact to L4 as a typed decision object.
- Several tier-specific tools appear to expect unified-memory properties that the current implementation does not expose.

Evidence:

- `memory_store` only writes to L1 directly; its `"L2"` branch actually queues a store request into L1 for later promotion. See [`src/agents/tools/unified_tools.py`](/Users/max/Documents/code/mas-memory-layer/src/agents/tools/unified_tools.py).
- `l3_search_episodes` explicitly returns a placeholder error because embedding-backed episode search is not implemented. See [`src/agents/tools/tier_tools.py`](/Users/max/Documents/code/mas-memory-layer/src/agents/tools/tier_tools.py).
- `l2_search_facts`, `l3_query_graph`, and `l4_search_knowledge` access `memory_system.working_memory`, `memory_system.episodic_memory`, and `memory_system.semantic_memory`, but the current unified memory implementations expose `l2_tier`, `l3_tier`, and `l4_tier` instead. See [`src/agents/tools/tier_tools.py`](/Users/max/Documents/code/mas-memory-layer/src/agents/tools/tier_tools.py), [`src/memory/unified_memory_system.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/unified_memory_system.py), and [`src/memory/system.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/system.py).
- `l4_search_knowledge` formats `created_at`, but `KnowledgeDocument` uses `distilled_at`, not `created_at`. See [`src/agents/tools/tier_tools.py`](/Users/max/Documents/code/mas-memory-layer/src/agents/tools/tier_tools.py) and [`src/memory/models.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/models.py).
- `l2_search_facts` formats `created_at`, but `Fact` uses `extracted_at`, not `created_at`. See [`src/agents/tools/tier_tools.py`](/Users/max/Documents/code/mas-memory-layer/src/agents/tools/tier_tools.py) and [`src/memory/models.py`](/Users/max/Documents/code/mas-memory-layer/src/memory/models.py).

Bottom line:

- The current tools are useful for retrieval and general context assembly.
- They are **not sufficient to run this artifact-centric solver loop cleanly and auditable without new memory tools or targeted fixes**.

## 4. Tool Sufficiency Assessment

### `memory_store`

**Status:** Insufficient for this flow

- Can write transient content to L1.
- Cannot directly write a structured `Fact` to L2.
- Cannot write to L4.
- The `"L2"` option is only a deferred promotion pattern through L1, not an explicit L2 decision-object write.

Usefulness for sandwich flow:

- Good for raw artifact payloads and raw IIS logs as transient records.
- Not good enough for strict artifact revision management.

### `memory_query`

**Status:** Helpful but insufficient

- Performs cross-tier retrieval through `query_memory()`.
- Useful for recalling prior discussion, promoted facts, and stored knowledge.
- Not designed to retrieve a typed artifact revision chain.

Usefulness for sandwich flow:

- Good for context retrieval.
- Not a substitute for artifact lineage search.

### `get_context_block`

**Status:** Helpful but insufficient

- Good for rehydrating recent L1 turns and high-CIAR L2 facts.
- Useful if the agent needs the IIS log and recent artifact context back in the prompt.
- Does not expose artifact lineage or provenance semantics.

Usefulness for sandwich flow:

- Good support tool.
- Not enough for execution or auditability by itself.

### `l2_search_facts`

**Status:** Partially useful, currently fragile

- Intended for fast L2 retrieval by keyword.
- Useful if artifact ids, port names, or solver error terms are stored as facts.
- Currently depends on `memory_system.working_memory`, which the current unified memory implementation does not expose directly.
- Also formats `created_at` rather than `extracted_at`.

Usefulness for sandwich flow:

- Conceptually relevant.
- Needs runtime wiring fixes before it is dependable.

### `l3_query_graph`

**Status:** Low value for the baseline scenario

- Useful for graph-style episode traversal.
- The sandwich baseline is centered on artifact revision and solver-failure provenance, not on entity-graph traversal.
- Also depends on `memory_system.episodic_memory`, which is not exposed as such by the current unified memory implementations.

Usefulness for sandwich flow:

- Not the primary tool.
- Could become relevant only if the scenario is modeled as episode/entity graph relationships.

### `l3_search_episodes`

**Status:** Not usable

- Explicitly returns that episode embedding search is not implemented.

Usefulness for sandwich flow:

- None for current execution.

### `l4_search_knowledge`

**Status:** Retrieval-only and currently fragile

- Useful for querying durable knowledge in Typesense.
- Cannot write the final verified artifact.
- Depends on `memory_system.semantic_memory`, which is not exposed by the current unified memory implementations.
- Formats `created_at`, but the current knowledge model uses `distilled_at`.

Usefulness for sandwich flow:

- Useful only after knowledge is already present in L4.
- Not enough to commit and audit the final artifact.

## 5. Final Recommendation

**Conclusion:** `YAAM is usable with strict orchestration conventions`

That said, for the exact IDWL 2026 sandwich baseline, the repository is **not sufficient without targeted extensions** if you need:

- explicit artifact revision tracking,
- strict segregation between transient failed artifacts and final verified artifact,
- auditable causal links from solver IIS output to revised artifact,
- agent execution through the current YAAM tool surface alone.

### Minimum Required Extensions

1. **Artifact lineage/version model**
   - Add a first-class artifact or decision-object schema with stable `artifact_id`, explicit revision number, status fields such as `infeasible` and `feasible`, and supersession links.

2. **Provenance linkage policy**
   - Add first-class links for computational events such as solver run, failure reason, IIS reference, and revision rationale.
   - Preserve "artifact v2 created because solver returned IIS on capacity constraint" as structured data rather than only freeform text.

3. **Direct-write tier-safe tools**
   - Add tools for explicit L2 artifact write and explicit L4 final artifact commit.
   - Add a provenance-aware tool that can attach causal links between artifact revisions and solver outputs.

4. **Tool/runtime integration fixes**
   - Align tool code with the actual unified memory object surface or add compatibility properties.
   - Fix field mismatches such as `created_at` vs. `extracted_at` and `created_at` vs. `distilled_at`.
   - Implement or remove placeholder tools such as `l3_search_episodes`.

## Final Position

For this baseline, YAAM already provides:

- a strong multi-tier memory architecture,
- workable transient-vs-durable storage separation,
- partial provenance support,
- useful retrieval/context tools.

For this baseline, YAAM does **not** yet provide:

- first-class artifact revision history,
- automatic audit-chain capture for solver-driven revision,
- a complete existing tool set to execute the sandwich loop without custom additions.

If the goal is a rigorously auditable artifact-centric baseline for IDWL 2026, YAAM should be treated as a **good substrate**, not a complete drop-in solution.
