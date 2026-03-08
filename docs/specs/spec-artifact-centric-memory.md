# Specification: Artifact-Centric Memory

**Status:** Draft  
**Date:** March 8, 2026  
**Audience:** Maintainers, agent-tool authors, runtime orchestration developers  
**Related:** [ADR-012](../ADR/012-artifact-centric-memory-extension.md), [ADR-003](../ADR/003-four-layers-memory.md), [ADR-007](../ADR/007-agent-integration-layer.md)

## 1. Overview

This specification defines the YAAM extension required to support artifact-centric cognitive workflows in which an agent iteratively produces, evaluates, revises, and finalizes a structured decision artifact.

The extension is generic. It does not prescribe any domain-specific payload schema and does not assume supply-chain semantics. Instead, it introduces a neutral model for:

- artifact identity,
- artifact revision history,
- external computational feedback,
- explicit finalization and semantic commitment,
- auditable lineage retrieval.

## 2. Architectural Placement

The extension resides in `src/memory/artifacts/` and sits above the existing storage/tier mechanism.

### 2.1 Module structure

- `src/memory/artifacts/models.py`
  Pydantic contracts for artifacts, revisions, feedback, commits, and lineage queries/results.
- `src/memory/artifacts/repository.py`
  Persistence coordination layer that writes:
  - lineage graph state to Neo4j,
  - working-state projections to L1/L2,
  - final projection to L4.
- `src/memory/artifacts/service.py`
  Orchestration layer for lifecycle operations.
- `src/agents/tools/artifact_tools.py`
  Runtime tool surface for agents.

## 3. Data Contracts

### 3.1 Artifact

Represents the stable logical object across revisions.

Required fields:
- `artifact_id`
- `artifact_kind`
- `session_id`
- `status`
- `created_at`
- `updated_at`

Optional fields:
- `workspace_id`
- `current_revision_id`
- `metadata`

### 3.2 ArtifactRevision

Represents one concrete artifact state.

Required fields:
- `revision_id`
- `artifact_id`
- `revision_number`
- `payload`
- `payload_hash`
- `verification_state`
- `tier_state`
- `created_at`

Optional fields:
- `parent_revision_id`
- `trigger_feedback_id`
- `created_by`
- `summary`
- `metadata`

### 3.3 ArtifactFeedback

Represents external feedback linked to one artifact revision.

Required fields:
- `feedback_id`
- `artifact_id`
- `revision_id`
- `feedback_type`
- `source_system`
- `content`
- `created_at`

Optional fields:
- `structured_payload`
- `severity`
- `metadata`

### 3.4 ArtifactCommit

Represents explicit finalization of a validated artifact revision.

Required fields:
- `commit_id`
- `artifact_id`
- `revision_id`
- `committed_at`

Optional fields:
- `knowledge_id`
- `commit_reason`
- `metadata`

### 3.5 ArtifactLineageResult

Returns ordered lineage nodes for audit and prompt assembly.

The lineage must preserve, at minimum:
- revision order,
- applied feedback,
- final commit record,
- semantic-memory projection reference if created.

## 4. State Transitions

### 4.1 Artifact status

Allowed top-level statuses:
- `draft`
- `failed`
- `validated`
- `committed`
- `superseded`

### 4.2 Revision verification state

Allowed revision-level states:
- `unverified`
- `infeasible`
- `feasible`

### 4.3 Tier state

Allowed tier state values:
- `working`
- `committed`

### 4.4 Transition rules

1. `artifact_save_draft`
   - creates an artifact if one does not exist,
   - creates a new revision with `verification_state="unverified"` and `tier_state="working"`.

2. `artifact_attach_feedback`
   - creates a feedback node and links it to a targeted revision,
   - may update verification state based on feedback type:
     - failure-like feedback => `infeasible`,
     - success-like feedback => `feasible`.

3. `artifact_create_revision`
   - creates revision `N+1`,
   - links it to the parent revision,
   - optionally links it to the feedback that triggered the change.

4. `artifact_commit_final`
   - requires `verification_state="feasible"`,
   - creates an explicit commit record,
   - writes a final semantic-memory projection,
   - marks the revision `tier_state="committed"`.

## 5. Storage Semantics

### 5.1 Neo4j lineage graph

Neo4j is the source of truth for:
- artifact existence,
- revision order,
- supersession edges,
- feedback attachment,
- causal trigger edges,
- commit edges,
- optional semantic-memory linkage.

### 5.2 L1 projection

L1 stores raw artifact events for immediate prompt recovery:
- draft creation,
- feedback attachment,
- revision creation.

These projections are transient and prompt-oriented.

### 5.3 L2 projection

L2 stores retrieval-friendly operational summaries:
- revision summary facts,
- feedback summary facts.

These projections exist to support search and context assembly. They are not the lineage source of truth.

### 5.4 L4 projection

L4 stores only final committed artifact projections.

The L4 projection must include:
- artifact identifier,
- committed revision identifier,
- revision number,
- lineage entry point,
- provenance references sufficient to locate the full graph lineage.

## 6. Tool Contracts

### 6.1 `artifact_save_draft`

Inputs:
- `artifact_kind`
- `payload`
- `artifact_id?`
- `summary?`
- `metadata?`

Output:
- `artifact_id`
- `revision_id`
- `revision_number`
- `verification_state`

### 6.2 `artifact_attach_feedback`

Inputs:
- `artifact_id`
- `revision_id`
- `feedback_type`
- `source_system`
- `content`
- `structured_payload?`
- `metadata?`

Output:
- `feedback_id`

### 6.3 `artifact_create_revision`

Inputs:
- `artifact_id`
- `parent_revision_id`
- `payload`
- `trigger_feedback_id?`
- `summary?`
- `metadata?`

Output:
- `artifact_id`
- `revision_id`
- `revision_number`
- `trigger_feedback_id`

### 6.4 `artifact_commit_final`

Inputs:
- `artifact_id`
- `revision_id`
- `commit_reason?`
- `metadata?`

Output:
- `commit_id`
- `knowledge_id`
- `artifact_id`
- `revision_id`

### 6.5 `artifact_get_lineage`

Inputs:
- `artifact_id`
- `revision_id?`

Output:
- ordered lineage result

## 7. Non-Goals

- YAAM does not validate the internal domain schema of the payload.
- YAAM does not execute the external solver.
- YAAM does not prescribe domain-specific success/failure semantics beyond generic feedback typing.
- YAAM does not require changes to `src/storage/` adapter contracts.

## 8. Acceptance Criteria

The extension is considered complete when:

1. an agent can save a draft artifact without writing it to L4,
2. external feedback can be attached to a specific revision,
3. a new revision can be explicitly linked to a predecessor and triggering feedback,
4. only a feasible revision can be committed to L4,
5. lineage retrieval returns the ordered trail of revisions, feedback, commit, and semantic projection.
