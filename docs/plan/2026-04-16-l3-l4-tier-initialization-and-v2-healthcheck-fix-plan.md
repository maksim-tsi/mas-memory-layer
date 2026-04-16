# Plan: L3/L4 Tier Initialization Regression and V2 Healthcheck Guardrail

**Status:** Proposed  
**Date:** April 16, 2026  
**Owners:** YAAM maintainers, API runtime owners, memory subsystem owners  
**Source report:** [L3/L4 issue report](../notes/2026-04-16-l3-l4-issue-report.md)  
**Related:** [ADR-003](../ADR/003-four-layers-memory.md), [ADR-009](../ADR/009-decoupling-benchmark-api-wall.md), [Environment guide](../environment-guide.md)

## 1. Executive summary

The reported `501 Not Implemented` responses on V2 L3 and L4 endpoints are consistent with a policy-layer wiring defect: the API container initializes a `UnifiedMemorySystem` instance with missing L3 and L4 tier dependency injection, leaving `l3_tier` and `l4_tier` as `None`.

This plan defines a two-track remediation:

1. A production hotfix for `src/evaluation/agent_wrapper.py` to instantiate and inject `EpisodicMemoryTier` (L3) and `SemanticMemoryTier` (L4).
2. A regression-prevention guardrail in `scripts/healthcheck_v2.sh` that fails on HTTP 501 while accepting HTTP 422/502 as evidence that the request path is wired and reachable.

## 2. Problem statement and root-cause hypothesis

### Observed behavior

1. `POST /v2/memory/l3/query` and related L4 flows return `501 Not Implemented` from the YAAM v2 container.
2. The issue is visible in deployed container behavior rather than isolated unit-level mocks.

### Root-cause hypothesis

1. `src/evaluation/agent_wrapper.py` does not complete dependency injection for L3/L4 tiers during runtime initialization.
2. The memory system remains partially wired (`l1_tier`/`l2_tier` present, `l3_tier`/`l4_tier` absent), so endpoint handlers hit explicit not-implemented branches.
3. Existing tests did not fail because they mocked or bypassed this path.

### Architectural classification

1. This is a policy/orchestration-layer defect.
2. No mechanism-layer modification in `src/storage/` is required to resolve the bug.

## 3. Scope and non-goals

### In scope

1. Add adapter and tier instantiation for Qdrant/Neo4j/Typesense-backed L3/L4 tiers in wrapper initialization.
2. Inject those tiers into `UnifiedMemorySystem` construction.
3. Ensure lifecycle startup covers required async `initialize`/`connect` behavior.
4. Add `scripts/healthcheck_v2.sh` with explicit 501-fail logic.
5. Optionally expose `make healthcheck` command for post-startup verification.

### Out of scope

1. Storage adapter redesign in `src/storage/`.
2. Dependency changes (`pyproject.toml`, lockfile) unless explicitly approved.
3. Expanding endpoint semantics beyond initialization correctness.

## 4. Implementation plan

### Phase A: Runtime DI hotfix in wrapper

**Target file:** `src/evaluation/agent_wrapper.py`

1. Import and instantiate:
   - `QdrantAdapter`
   - `Neo4jAdapter`
   - `TypesenseAdapter`
   - `EpisodicMemoryTier`
   - `SemanticMemoryTier`
2. Create tier objects with existing adapter contracts:
   - `episodic_tier = EpisodicMemoryTier(vector_db=qdrant_adapter, graph_db=neo4j_adapter)`
   - `semantic_tier = SemanticMemoryTier(search_db=typesense_adapter)`
3. Inject `episodic_tier` and `semantic_tier` as `l3_tier` and `l4_tier` in `UnifiedMemorySystem(...)`.
4. Preserve existing `NullKnowledgeStoreManager`, L1/L2 wiring, and promotion-engine behavior.

**Acceptance criteria**

1. Wrapper initialization returns a memory system where both `l3_tier` and `l4_tier` are non-null.
2. No regressions in L1/L2 initialization path.

### Phase B: Startup lifecycle correctness

**Target files:** `server.py` and any wrapper startup path where `initialize()` is awaited

1. Verify wrapper initialization executes before serving requests.
2. If adapters/tiers require async startup (`connect`, `initialize`, or equivalent), ensure those calls are awaited in the startup lifespan.
3. Ensure failures surface as startup errors, not deferred runtime `501` behavior.

**Acceptance criteria**

1. Container startup completes with all configured tiers initialized.
2. Misconfiguration produces explicit startup/log errors instead of silent partial initialization.

### Phase C: Automated V2 healthcheck guardrail

**Target file:** `scripts/healthcheck_v2.sh`

1. Add script with optional `BASE_URL` argument defaulting to `http://localhost:8080`.
2. Probe:
   - `POST /v2/memory/l2/facts` with action `retrieve`
   - `POST /v2/memory/l3/query` with dummy payload
3. Enforce response classification:
   - **Fail (exit 1):** any HTTP 501
   - **Pass for wiring proof:** HTTP 422 or HTTP 502
   - **Also pass:** HTTP 200/2xx when available
4. Print endpoint-wise status and final pass/fail summary.

**Acceptance criteria**

1. Script exits 1 on reproduced regression (`501`).
2. Script exits 0 when L3/L4 path is wired (including 422/502 fallback cases).

### Phase D: Optional Makefile integration

**Target file:** `Makefile`

1. Add `healthcheck` target that runs `scripts/healthcheck_v2.sh`.
2. Keep target side-effect free beyond endpoint probing.

**Acceptance criteria**

1. `make healthcheck` provides a single-command post-deploy verification path.

## 5. Verification strategy

### Static and unit/integration checks

1. `./.venv/bin/ruff check .`
2. `./.venv/bin/pytest tests/ -v`

### Container verification

1. Rebuild runtime:
   - `docker compose up -d --build mas-agent`
2. Run healthcheck:
   - `scripts/healthcheck_v2.sh`
   - or `make healthcheck` (if Phase D is applied)
3. Manual endpoint sanity check:
   - `curl` to `/v2/memory/l3/query` must not return 501.

### Evidence required in delivery note

1. Diff excerpt for `src/evaluation/agent_wrapper.py` showing L3/L4 DI.
2. Full `scripts/healthcheck_v2.sh` content.
3. Script execution output from rebuilt container environment.

## 6. Risks and mitigations

1. **Risk:** Adapter init order race or missing await.
   **Mitigation:** Centralize startup sequencing in lifespan and fail fast on init errors.
2. **Risk:** Environment variables missing for external stores.
   **Mitigation:** Explicit startup diagnostics and endpoint-level healthcheck reporting.
3. **Risk:** Script false negatives for expected non-200 responses.
   **Mitigation:** Explicitly classify 422/502 as acceptable wiring evidence.

## 7. Rollback and contingency

1. If hotfix causes startup instability, revert wrapper DI change set and redeploy previous stable image.
2. Keep healthcheck script in place even during rollback to detect persistent partial initialization.
3. Escalate only if mechanism-layer defects are proven; otherwise maintain policy-layer boundary.

## 8. Execution checklist

1. Implement Phase A and Phase B.
2. Run lint and tests.
3. Rebuild container and run healthcheck.
4. Implement Phase C and optional Phase D.
5. Re-run healthcheck and capture outputs.
6. Publish fix evidence in a dated report artifact if required by release process.

## 9. Completion criteria

This plan is considered complete when all items below are true:

1. V2 L3 endpoint no longer returns HTTP 501 under normal initialized runtime.
2. `UnifiedMemorySystem` is initialized with non-null L3 and L4 tiers.
3. Automated script detects the regression class and passes on wired states.
4. Build/deploy workflow has a documented, repeatable post-startup verification step.