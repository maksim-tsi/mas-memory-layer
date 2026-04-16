# Plan: Implement ADR-010 (Repository Harness + Skills v1)

**Status:** Draft  
**Date:** February 18, 2026  
**ADR:** `docs/ADR/010-mechanism-policy-split-and-skills-v1.md`  
**Spec:** `docs/specs/spec-mechanism-maturity-and-freeze.md`  
**RFP:** `docs/plan/rfp-repository-harness-and-skills-v1.md`  

## 0. Terminology (to avoid ambiguity)

YAAM interacts with two distinct classes of “agents/assistants”:

1. **Development-time coding assistants** (used to build YAAM): GitHub Copilot, Codex CLI, Claude Code,
   Gemini CLI, etc. These assistants read repository harness instructions and modify this repository.
2. **Runtime MAS agents** (YAAM’s users): systems built with LangGraph/AutoGen/CrewAI and external
   assistants (e.g., Claude Desktop) that can consume YAAM skills and call YAAM’s capabilities.

Unless stated otherwise in this plan:
- “Harness” refers to development-time guardrails for coding assistants.
- “Skills” refer to runtime policy artifacts.

## 1. Objective

Implement ADR-010 by establishing:

1. A coherent **repository harness** (coding-assistant instruction hierarchy + mechanical drift checks),
2. A **Skills v1** store (policy-first, progressive disclosure oriented), and
3. An evidence-based pathway to **freeze-by-default** the mechanism layer (`src/storage/`) while
   preserving the ability to evolve it under explicit change control.

## 2. Guiding Principles (Non-Negotiable)

1. **Mechanism vs Policy separation:** Mechanism provides stable capabilities; Policy governs usage.
2. **Frozen-by-default mechanism:** `src/storage/` changes require explicit authorization and
   evidence-driven justification.
3. **Progressive disclosure:** Runtime agents should not ingest a global “everything manual” by default.
4. **No train-on-test:** The GoodAI benchmark is a feedback signal, not an optimization target for
   embedding benchmark-specific scripts in skills or prompts.
5. **Mechanical enforcement over social enforcement:** Prefer structural tests/linters over “please
   remember” instructions.

## 3. Current State (as of 2026-02-18)

The following foundations already exist:

- Instruction hierarchy aligned:
  - `AGENTS.MD` is a short map + invariants.
  - `.github/copilot-instructions.md` is a Copilot entrypoint consistent with `AGENTS.MD`.
  - `.github/instructions/*` has been aligned to avoid conflicting copy-pastable snippets.
- Mechanical drift check:
  - `tests/test_instruction_consistency.py` validates banned snippets in instruction code blocks.
- Spec and ADR:
  - Mechanism contract and freeze readiness checklist are defined in
    `docs/specs/spec-mechanism-maturity-and-freeze.md`.
  - ADR-010 is authored; ADR-007 and ADR-009 have been updated for consistency.

This plan focuses on the remaining work to realize Skills v1 and enforce boundaries.

## 4. Workstreams and Milestones

### Workstream A — Harness Hardening (Drift-Resistant Instructions)

**A0. Establish a default “local-only” test mode (development harness)**

- Default execution of `./.venv/bin/pytest tests/ -v` MUST succeed in environments without
  connectivity to external services (including provider APIs and LAN-hosted DBs).
- Integration tests and real-provider tests MUST be explicitly enabled via command-line flags,
  to avoid accidental network access from agent sandboxes and to reduce false-negative CI signals.
- The follow-up debugging plan for networked environments is tracked in
  `docs/plan/plan-network-and-integration-tests.md`.

**A1. Expand instruction-drift checks (optional, incremental)**

- Extend `tests/test_instruction_consistency.py` if new drift patterns emerge (e.g., “activate venv”).
- Add a small allowlist mechanism if needed to avoid false positives in provider SDK references.

**A2. Add “dependency direction” enforcement for mechanism layer**

- Add a structural test that fails if `src/storage/` imports from policy layers (e.g., `src/agents/`,
  future `skills/`, evaluation-only policy modules).
- Ensure the rule is documented in the spec (already present) and in ADR-010 (already present).

**A3. Ensure the harness is discoverable**

- Add a short pointer section in `README.md` (optional) referencing `AGENTS.MD` + ADR-010 + the skill store.
- If updated, keep statements factual and aligned with Poetry constraints.

**Exit Criteria**

- Structural dependency-direction test exists and passes.
- Instruction drift tests remain stable and low-noise.

---

### Workstream B — Skill Store v1 (Policy-First Artifacts)

**B1. Create a stable skill package layout**

Create:

- `skills/README.md` (inventory and authoring rules)
- `skills/_template/SKILL.md` (canonical template)
- Optional: `skills/_template/references/` (example schema placement)

**B2. Define SKILL.md schema (frontmatter + sections)**

Define a minimal, stable structure intended for both internal agents and future external assistants:

Frontmatter (v1):
- `name`
- `version`
- `intent` (short)
- `mechanism_contract` (reference to Contract v1)
- `required_capabilities` (e.g., which adapters / which tool families)
- `safety` (non-negotiable guardrails)
- `examples` (optional)

Body sections (v1):
- **When to use**
- **Inputs/Outputs**
- **Mechanism calls (“connect/query/store” mapping)**
- **Recipes** (system-oriented, not benchmark-script oriented)
- **Failure modes and safe fallback**
- **Do not do** (layer-jumping guardrails)

**B3. Author initial skill inventory (10–20 skills)**

Selection criteria:
- aligned with the YAAM system paper narrative (memory lifecycle, auditability, multi-agent state),
- broad enough to be meaningful outside the benchmark,
- small enough to enable progressive disclosure.

Recommended starting set (draft; subject to adjustment):
- `operating_memory_l1` (Redis L1 usage patterns; session-scoped context hygiene)
- `working_memory_l2_audit_trail` (Postgres facts/audit patterns; CIAR thresholds and provenance)
- `episodic_memory_l3_graph_reasoning` (Neo4j traversal patterns and safety constraints)
- `episodic_memory_l3_similarity_search` (Qdrant search patterns and grounding)
- `semantic_memory_l4_search_and_artifacts` (Typesense search patterns and artifact indexing)
- `knowledge_lifecycle_promotion` (how/when to promote; what evidence should be stored)
- `knowledge_lifecycle_distillation` (how/when to distill; avoid premature generalization)

**Exit Criteria**

- `skills/` exists with a template and at least 3–5 initial skills drafted.
- Each skill references the mechanism contract and includes explicit guardrails.

---

### Workstream C — Mechanism Maturity Evaluation (Freeze Readiness Evidence)

**C1. Adapter maturity matrix**

For each adapter under `src/storage/` (Redis/Postgres/Qdrant/Neo4j/Typesense):

- Record maturity status against the checklist in `docs/specs/spec-mechanism-maturity-and-freeze.md`.
- Identify missing evidence (tests, retry behavior, timeout config, health check depth, metrics).
- Define “must fix before freeze” vs “can defer” items.

Deliverable:
- `docs/reports/` or `docs/plan/` artifact summarizing maturity and gaps (format to be decided).

**C2. Add contract tests**

Add tests that assert:
- public method behavior (happy path),
- exception typing by failure mode (connection/query/data/timeout),
- health_check semantics,
- metrics existence for core operations (where practical).

**C3. Validate observability surfaces**

Define and test minimal observability expectations:
- metrics include operation counts and latency distributions,
- logs include operation + identifiers and do not leak secrets.

**Exit Criteria**

- Each adapter has an evidence trail for Contract v1 readiness.
- Known gaps are tracked and explicitly accepted or remediated.

---

### Workstream D — Freeze-by-Default Enforcement (Change Control)

**D1. Repository-level enforcement**

Implement enforcement mechanisms that bias assistants toward policy-layer changes:

- Structural dependency-direction tests (Workstream A2).
- Optional: a “mechanism change gate” that flags diffs touching `src/storage/` and requires explicit
  approval (implementation approach to be decided; may be CI-only later).

**D2. Change control process**

Document the process for mechanism changes:
- require an ADR for breaking changes (Contract v2+),
- require regression tests for any mechanism changes,
- require explicit authorization for dependency updates (Poetry).

**Exit Criteria**

- There is a clear, documented path to change the mechanism layer without silent drift.

---

### Workstream E — Benchmark Feedback Loop (Regression + System Health)

**E1. Define how benchmark results are used**

Create a short guideline:
- benchmark runs as regression signals,
- interpretability of failures (what layer likely needs changes),
- avoid embedding benchmark prompts into skills.

**E2. Establish a minimal “benchmark-driven debugging loop”**

Define a repeatable workflow:
- run benchmark (API Wall),
- collect results,
- map regressions to policy changes first,
- consider mechanism changes only when evidence indicates a mechanism defect.

**Exit Criteria**

- Benchmark usage is documented as feedback-only and integrated into iteration loops without
  encouraging overfitting.

## 5. Proposed Sequence (Suggested Execution Order)

1. Workstream A2 (dependency-direction structural test) to prevent early drift.
2. Workstream B1–B2 (skill store skeleton + SKILL.md schema).
3. Workstream B3 (draft 3–5 initial skills).
4. Workstream C1 (maturity matrix) to identify mechanism gaps exposed by skills.
5. Workstream C2–C3 (tests/observability evidence) to close critical gaps.
6. Workstream D (freeze-by-default enforcement strengthening).
7. Workstream E (benchmark feedback loop documentation and routine).

## 6. Acceptance Criteria (Definition of Done for v1)

1. `skills/` exists with a stable template and an initial curated set of skills.
2. Mechanism contract is treated as stable and referenced by skills.
3. Structural tests enforce dependency direction for `src/storage/`.
4. Instruction drift tests protect against reintroduction of banned snippets and contradictory
   guidance.
5. Benchmark usage is explicitly documented as feedback-only.

## 7. Risks and Mitigations

- **Risk:** Skills become benchmark-specific.  
  **Mitigation:** enforce “no train-on-test” in ADR-010 and skill authoring guidelines; peer review
  skills against system-paper objectives rather than benchmark scripts.

- **Risk:** Freeze occurs before maturity evidence exists.  
  **Mitigation:** freeze-by-default only; activate strict gates only after Workstream C evidence.

- **Risk:** Instruction base grows into an encyclopedia.  
  **Mitigation:** keep `AGENTS.MD` short; store detail in `docs/` and `.github/instructions/*`;
  enforce with drift tests.

## 8. Open Questions

1. Should additional directories be treated as mechanism (frozen-by-default) beyond `src/storage/`?
2. What is the minimal v1 “skill registry” interface (manual selection vs minimal loader)?
3. Which 3–5 skills should be authored first to best support the system paper’s core claims?
