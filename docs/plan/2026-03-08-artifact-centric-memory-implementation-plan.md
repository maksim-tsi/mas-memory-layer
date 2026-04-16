# Artifact-Centric Memory Implementation Plan

**Status:** Draft  
**Date:** March 8, 2026  
**Related:** [ADR-012](../ADR/012-artifact-centric-memory-extension.md), [Artifact-Centric Memory Spec](../specs/spec-artifact-centric-memory.md)

## 1. Summary

This document defines the implementation phases for adding artifact-centric memory support to YAAM as a bounded extension above the existing four-tier architecture.

The implementation goal is to support auditable, revisioned artifacts with explicit external feedback and explicit finalization while preserving the current storage adapter contracts.

## 2. Phase Breakdown

### Phase 1: Core contracts and orchestration

Deliverables:
- `src/memory/artifacts/models.py`
- `src/memory/artifacts/repository.py`
- `src/memory/artifacts/service.py`
- `src/memory/artifacts/__init__.py`

Acceptance criteria:
- artifact, revision, feedback, commit, and lineage models validate,
- the service can create drafts, attach feedback, create revisions, and commit finals,
- lineage can be retrieved as an ordered structure.

### Phase 2: Unified memory exposure

Deliverables:
- memory facade exposes `artifact_service` / `artifacts`

Acceptance criteria:
- runtime agent code can access artifact operations without direct adapter handling,
- existing memory APIs remain unchanged.

### Phase 3: Agent tool surface

Deliverables:
- `src/agents/tools/artifact_tools.py`
- tool exports updated in `src/agents/tools/__init__.py`

Acceptance criteria:
- agents can execute:
  - save draft,
  - attach feedback,
  - create revision,
  - commit final,
  - get lineage
  using YAAM-provided tools only.

### Phase 4: Test coverage

Deliverables:
- `tests/memory/artifacts/test_models.py`
- `tests/memory/artifacts/test_service.py`
- `tests/agents/tools/test_artifact_tools.py`
- `tests/integration/test_artifact_lineage_flow.py`

Acceptance criteria:
- schema validation tests pass,
- service lifecycle tests pass,
- tool invocation tests pass,
- the focused lineage scenario passes end-to-end.

### Phase 5: Documentation

Deliverables:
- ADR for architectural decision,
- technical spec,
- implementation plan,
- optional follow-up updates to broader memory documentation in later work.

Acceptance criteria:
- maintainers can understand the extension without reverse-engineering the code,
- the mechanism/policy boundary is explicitly documented.

## 3. Testing Strategy

### Unit tests

Validate:
- payload hashing,
- revision numbering,
- commit feasibility checks,
- ownership checks between artifact and revision,
- tool error handling when artifact service is unavailable.

### Integration scenario

Scenario:
1. save draft v1,
2. attach solver IIS feedback,
3. create v2 from v1 and feedback,
4. attach solver success feedback,
5. commit v2,
6. retrieve lineage and verify the full trail.

Assertions:
- v1 remains working-state only,
- failure feedback is preserved,
- v2 becomes feasible only after success feedback,
- commit creates a semantic projection,
- lineage contains revision, feedback, commit, and knowledge nodes.

## 4. Rollout and Compatibility

### Compatibility guarantees

- `src/storage/` remains unchanged.
- Existing tier code remains the same public mechanism.
- Existing unified/tier tools remain available and are not overloaded with artifact semantics.

### Operational posture

- Neo4j becomes the authoritative lineage store.
- L1 and L2 projections are retrieval helpers only.
- L4 stores final committed projections only.

## 5. Known Follow-Up Opportunities

The initial implementation may be strengthened later by:
- dedicated L2 projection tables for artifact revisions and feedback,
- richer graph queries for focal revision sub-lineage retrieval,
- artifact-specific context block assembly,
- operator-facing visualization of lineage DAGs,
- scenario-specific skills that sit above the generic artifact toolset.
