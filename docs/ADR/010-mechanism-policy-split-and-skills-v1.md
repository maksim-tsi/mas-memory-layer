# ADR-010: Mechanism/Policy Split and Skills v1 for Agent-First Development

**Status:** Proposed  
**Date:** February 18, 2026  
**Related:** ADR-003, ADR-007, ADR-009; `docs/specs/spec-mechanism-maturity-and-freeze.md`; `docs/plan/rfp-repository-harness-and-skills-v1.md`  

## 1. Context

YAAM concerns **two distinct classes of “agents/assistants”** that must not be conflated:

1. **Development-time coding assistants** (used to build YAAM): GitHub Copilot, Codex CLI, Claude Code,
   Gemini CLI, etc. These assistants read repository harness instructions and modify this codebase.
2. **Runtime MAS agents** (YAAM’s users): multi-agent systems built with frameworks like LangGraph,
   AutoGen, CrewAI, and also external desktop/CLI assistants (e.g., Claude Desktop) that can consume
   YAAM skills and call YAAM’s capabilities.

YAAM is developed in an agent-first workflow where development-time coding assistants can increase
engineering throughput substantially. This workflow introduces a distinct failure mode: assistants
may “layer jump” by modifying stable, low-level mechanism code in order to improve a higher-level
policy outcome (e.g., a prompt, agent orchestration outcome, or benchmark score). In practice, this
can regress reliability and increase maintenance cost.

In addition, YAAM’s memory stack spans multiple storage backends (Redis, PostgreSQL, Qdrant, Neo4j,
Typesense). Exposing all operational details to a runtime agent simultaneously creates “tool bloat”
and context pollution, which ADR-007 already identifies as a major source of degraded reasoning and
token inefficiency.

We therefore need:

1. A stable **mechanism** layer that provides durable capabilities with strict boundaries,
2. A fast-iterating **policy** layer that controls how these capabilities are used, and
3. A **progressive disclosure** strategy that reveals instructions and interfaces only when needed.

Separately, YAAM uses the GoodAI LTM benchmark for evaluation. To preserve scientific validity, we
must avoid “train-on-test” behavior, where policy artifacts are optimized by encoding benchmark
prompts rather than improving general system behaviors.

## 2. Decision

### 2.1 Adopt an explicit Mechanism/Policy split

We formally separate YAAM into:

- **Mechanism:** low-level data-access and durability capabilities. In the current repository, the
  primary mechanism surface is `src/storage/` (storage adapters and their contract).
- **Policy:** instructions, skills, prompts, and agent orchestration that decide how to use the
  mechanism to accomplish a task.

The mechanism layer is **frozen-by-default**: it must not be modified unless explicitly authorized,
and changes must be justified by evidence and regression tests.

The public mechanism contract is defined by **Connector/Adapter Contract v1** in
`docs/specs/spec-mechanism-maturity-and-freeze.md`, aligned to `src/storage/base.py`.

### 2.2 Introduce Skills v1 as policy-first artifacts

We adopt a **Skill-Based Architecture** in which policy is primarily expressed as versioned,
repository-local skill packages.

**Skills v1 definition:**

- Skills live at repo root under `skills/`.
- Each skill is primarily a `SKILL.md` instruction file describing:
  - intent (“what capability this enables”),
  - required mechanism interfaces,
  - safe usage patterns (“recipes”),
  - and guardrails that prevent layer jumping.
- In v1, executable tools remain in `src/` (mechanism and agent tooling). Skills reference these
  tools and contracts rather than embedding business logic as code inside skills.

Skills v1 are **project-specific** and optimized for YAAM internal agents first, with an explicit
future path to generalize skills for external assistants (e.g., Codex, Claude Desktop) without
changing the mechanism contract.

### 2.3 Progressive disclosure (initially without a router)

Skills are intended to support progressive disclosure:

- Runtime agents should initially see a small inventory (10–20 skills).
- Only the selected skill’s full instruction payload should be injected into context.

In v1, skill selection may be manual or minimally automated. A dedicated skill orchestration router
(dynamic tool exposure, sub-graphs per skill, automatic activation) is deferred to a later phase.

This decision is consistent with ADR-007’s goal of preventing tool bloat and reducing context
pollution, while maintaining compatibility with the existing ToolRuntime pattern.

### 2.4 Benchmark usage is feedback-only

The GoodAI benchmark is used as a feedback loop for system behavior, regression detection, and
observability. It must not be treated as an optimization target for encoding benchmark-specific
scripts inside skills.

Benchmark integration continues to follow ADR-009 (“API Wall”) so that the benchmark remains a
black-box evaluator of the runtime agent system.

## 3. Consequences

### Positive

- **Boundary clarity:** Mechanism changes become intentional and controlled, reducing accidental
  regressions from assistants.
- **Higher iteration velocity:** Policy (skills/prompts/orchestration) becomes the primary surface
  for experimentation.
- **Improved agent legibility:** Skills provide a structured, discoverable knowledge store for
  runtime agents (and their operators) without overwhelming them with global instruction blobs.
- **Scientific validity:** Explicit “feedback-only” benchmark usage reduces the risk of
  train-on-test artifacts that invalidate evaluation claims.

### Negative

- **Up-front overhead:** Defining contracts, maturity criteria, and enforcement checks requires
  initial engineering effort before feature iteration accelerates.
- **Two-phase change process:** Some improvements will require policy edits first, and only
  mechanism edits when evidence proves they are necessary.

### Neutral / Implementation Considerations

- Mechanism freeze must be supported by objective evidence (tests, health checks, observability),
  as defined in `docs/specs/spec-mechanism-maturity-and-freeze.md`.
- Progressive disclosure requires a stable skill inventory format and, later, a router/registry. v1
  intentionally limits this to avoid premature orchestration complexity.

## 4. Implementation Plan (High Level)

1. **Repository harness alignment**
   - Ensure instruction hierarchy is consistent and mechanically checked.
2. **Skill store v1**
   - Create `skills/` and `skills/_template/` with a stable `SKILL.md` format.
   - Author an initial set of 10–20 skills aligned to system-paper objectives.
3. **Mechanism maturity evaluation**
   - Evaluate each adapter under `src/storage/` against the maturity checklist.
   - Add missing evidence (unit/integration tests, health checks, observability assertions).
4. **Mechanism boundary enforcement**
   - Add structural tests ensuring `src/storage/` has no policy-layer imports.
5. **Benchmark feedback loop**
   - Maintain ADR-009 integration and use results as regression signals only.

## 5. Alternatives Considered

### A) Split the repository into multiple Poetry projects (e.g., `core/` and `agents/`)

**Pros:** stronger dependency isolation; clearer packaging boundaries.  
**Cons:** significant refactor; higher coordination cost; risks breaking existing workflows.  
**Why deferred:** not required for Skills v1; ADR-009 already isolates benchmark execution.

### B) Embed executable tools inside each skill package in v1

**Pros:** skills become self-contained deployable units.  
**Cons:** duplicates mechanism code; increases drift risk; complicates freeze-by-default strategy.  
**Why rejected:** v1 uses policy-only skills and keeps executable logic in `src/`.

### C) Implement a full skill orchestration router immediately

**Pros:** fully automated progressive disclosure; dynamic tool exposure.  
**Cons:** high complexity; premature optimization; increases the surface area for failure.  
**Why deferred:** v1 focuses on stable skill packaging and boundary discipline first.
