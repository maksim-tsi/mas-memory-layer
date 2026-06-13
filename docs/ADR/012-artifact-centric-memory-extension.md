# ADR-012: Artifact-Centric Memory Extension

**Status:** Proposed  
**Date:** March 8, 2026  
**Related:** [ADR-003](003-four-layers-memory.md), [ADR-007](007-agent-integration-layer.md), [ADR-010](010-mechanism-policy-split-and-skills-v1.md)

## 1. Context

YAAM currently provides a four-tier memory architecture optimized for turns, facts, episodes, and distilled knowledge. This structure is sufficient for conversational memory and lifecycle-based knowledge formation, but it does not provide a first-class model for the iterative evolution of a single structured decision artifact under external computational feedback.

The immediate driver is the requirement captured in [RFE001 - YAAM Support for Artifact-Centric Cognitive Architectures](../requirements/RFE001%20-%20YAAM%20Support%20for%20Artifact-Centric%20Cognitive%20Architectures.md). That requirement calls for four generic capabilities:

1. explicit draft storage without accidental promotion to semantic memory,
2. explicit attachment of external feedback to a specific artifact revision,
3. explicit lineage across revisions and triggering feedback,
4. explicit finalization of a validated artifact into semantic memory with auditability.

The requirement originates from a supply-chain LLM -> OR Solver -> LLM "sandwich" workflow, but the architectural gap is not supply-chain-specific. The missing concept is a general YAAM primitive for auditable, versioned, artifact-centric cognition.

At the same time, ADR-010 requires that the mechanism layer under `src/storage/` remain frozen-by-default. Therefore, the enhancement must strengthen YAAM without introducing architectural drift into the adapter contract.

## 2. Decision

We will introduce an **artifact-centric memory subsystem** as a **core YAAM capability above the existing tier/storage mechanism**.

### 2.1 Architectural placement

- The subsystem will live under `src/memory/artifacts/`.
- It will not modify the public connector/adapter contract defined by `src/storage/`.
- It will coordinate existing tiers and adapters through a bounded repository/service layer.

### 2.2 Source of truth for lineage

**Neo4j** will be the source of truth for artifact lineage and causal provenance.

The graph will store:
- `Artifact`
- `ArtifactRevision`
- `ArtifactFeedback`
- `ArtifactCommit`

and the key causal relationships:
- `HAS_REVISION`
- `SUPERSEDES`
- `APPLIES_TO`
- `TRIGGERED_BY`
- `COMMITS`
- `DERIVED_FROM_ARTIFACT`

### 2.3 Tier projections

The artifact subsystem will project state into existing YAAM tiers as follows:

- **L1**: raw draft payloads and raw feedback events for prompt-context recovery,
- **L2**: searchable operational summaries of revisions and feedback,
- **L4**: final committed artifact projection only.

Historical draft state will not be written to L4.

### 2.4 Agent surface

Artifact lifecycle operations will be exposed through a new dedicated tool module rather than by overloading existing general-purpose memory tools.

The minimum tool set is:
- `artifact_save_draft`
- `artifact_attach_feedback`
- `artifact_create_revision`
- `artifact_commit_final`
- `artifact_get_lineage`

## 3. Consequences

### Positive

- YAAM gains a missing generic primitive for artifact-centric cognition.
- Auditability improves materially because external computational feedback becomes first-class rather than implied through freeform memory content.
- The four-tier architecture remains intact and is extended rather than replaced.
- The mechanism/policy boundary from ADR-010 is preserved because storage adapters are reused rather than rewritten.

### Negative

- The memory domain model becomes broader, and the new artifact subsystem introduces additional concepts maintainers must understand.
- Neo4j becomes more important as a semantic backbone, increasing the importance of graph test coverage and query correctness.
- There will be some overlap between existing `Fact`/`KnowledgeDocument` semantics and artifact projections, which must be documented carefully.

### Neutral

- The first implementation may use existing L2 fact projections for working-state retrieval rather than dedicated artifact projection tables, provided the adapter contract remains unchanged.
- Domain-specific payload schemas remain outside YAAM core; artifact payloads are treated as opaque structured dictionaries.

## 4. Implementation Plan

1. Add `src/memory/artifacts/` with Pydantic models, repository, and orchestration service.
2. Expose the subsystem through the unified memory facade as `artifact_service` / `artifacts`.
3. Add `src/agents/tools/artifact_tools.py` with the minimal artifact lifecycle tool set.
4. Add focused unit and integration tests for lineage, feedback attachment, and final commit semantics.
5. Add a technical specification and implementation plan to document schemas, state transitions, and rollout.

## 5. Alternatives Considered

### Alternative A: Encode artifact lifecycle inside existing `Fact`, `Episode`, and `KnowledgeDocument` only

**Pros**: No new subsystem, fewer new files.  
**Cons**: Artifact lineage remains implicit, revision semantics stay weak, and the tool surface remains ambiguous.  
**Why rejected**: This approach preserves the current gap rather than solving it.

### Alternative B: Extend `src/storage/` with artifact-specific adapters or new adapter contract methods

**Pros**: Stronger storage-level typing and potentially simpler persistence semantics.  
**Cons**: Violates frozen-by-default mechanism discipline and creates architectural drift.  
**Why rejected**: The requirement can be satisfied above the storage mechanism.

### Alternative C: Ship the feature as a research-only extension

**Pros**: Lower bar for immediate delivery and narrower maintenance scope.  
**Cons**: Treats a generic capability gap as a one-off benchmark customization.  
**Why rejected**: The requirement exposes a reusable YAAM concept that should be modeled generically.
