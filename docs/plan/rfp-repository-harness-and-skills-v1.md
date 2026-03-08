# RFP: Repository Harness + Skills v1 (YAAM)

**Status:** Draft  
**Date:** February 18, 2026  
**Owner:** YAAM maintainers  
**Audience:** Maintainers, coding assistants, contributors  

## 0. Terminology (to avoid ambiguity)

YAAM interacts with **two distinct classes of “agents/assistants”**:

1. **Development-time coding assistants** (used to build YAAM): GitHub Copilot, Codex CLI, Claude Code,
   Gemini CLI, etc. These assistants read `AGENTS.MD` / `.github/*` and modify this repository.
2. **Runtime MAS agents** (YAAM’s users): multi-agent systems built with frameworks like LangGraph,
   AutoGen, CrewAI, and also external desktop/CLI assistants (e.g., Claude Desktop) that can consume
   YAAM skills and call YAAM’s capabilities in production-like scenarios.

Some product names overlap across contexts (e.g., “Codex” can be a coding assistant and also an agent
platform). Unless stated otherwise:
- “Harness” refers to **development-time** workflows and guardrails.
- “Skills” refer to **runtime** policy artifacts for agents using YAAM.

## 1. Problem Statement

YAAM is developed with multiple development-time coding assistants (Codex, GitHub Copilot, Claude
Code, Gemini CLI). This increases throughput but also increases the risk of architectural drift,
“layer jumping” (assistants modifying stable mechanism code to improve a higher-level policy
outcome), and instruction inconsistency.

In parallel, YAAM is adopting a **Skill-Based Architecture** to enable progressive disclosure of
capabilities and to keep the mechanism layer stable while iterating on policy.

This RFP proposes a minimal “Skills v1” and “Repository Harness v1” foundation that enables safe,
high-velocity iteration without overfitting to benchmarks.

## 2. Goals

1. **Harness consistency:** Ensure a single coherent set of coding-assistant instructions and
   mechanically prevent instruction drift.
2. **Boundary safety:** Reduce “layer jumping” by clearly separating **Mechanism** from **Policy** and
   defaulting the mechanism layer to frozen-by-default.
3. **Skills v1 (policy-first):** Introduce a small set (10–20) of project-specific skills expressed
   primarily as `SKILL.md` instructions that teach runtime agents how to correctly use YAAM’s mechanism.
4. **Progressive disclosure:** Make skills discoverable by name and load their full instructions only
   when needed (initially via manual selection; orchestration/routers are future work).
5. **Benchmark as feedback:** Use the GoodAI benchmark as a **feedback loop** for system behavior,
   stability, and regression detection—not as a target for overfitting.

## 3. Scope (v1)

### 3.1 Repository Harness v1

- Consolidate and align the instruction hierarchy:
  - `AGENTS.MD` as the canonical map + invariants.
  - `.github/copilot-instructions.md` as the Copilot entrypoint, consistent with `AGENTS.MD`.
  - `.github/instructions/*.md` as path-scoped detailed guidance.
- Add mechanical checks for instruction drift (e.g., banned snippets in instruction code blocks).
- Establish the “Mechanism/Policy” terminology and default change boundaries in repo docs.

### 3.2 Skills v1 (Project-specific)

- Create a `skills/` directory at repo root that contains 10–20 skills.
- Each skill is primarily:
  - `skills/<skill_name>/SKILL.md` (policy instructions, usage patterns, guardrails)
  - Optional `skills/<skill_name>/references/` (schemas, examples, invariants)
  - Optional `skills/<skill_name>/tools/` *only if needed later* (v1 assumes tools live in `src/`)
- Skills reference YAAM’s mechanism layer, primarily `src/storage/` adapters and stable public
  interfaces (see `docs/specs/spec-mechanism-maturity-and-freeze.md`).
- Skills are optimized for YAAM’s internal runtime agents first (LangGraph / AutoGen / CrewAI), with
  an explicit decision to generalize for external runtime assistants (e.g., Claude Desktop) in a
  later version.

### 3.3 Benchmark Feedback Loop (GoodAI)

- Benchmark runs are treated as:
  - regression signals,
  - “behavioral integration tests” across mechanism+policy,
  - observability sources (logs/metrics per run),
  - and a way to stress long-horizon memory behaviors.
- Benchmark integration follows the “API Wall” model to keep evaluation decoupled from internal
  implementation details (see ADR-009).

## 4. Non-Goals (v1)

1. **No train-on-test / no benchmark overfitting.** Skills must be written to support the system
   paper’s objectives and general MAS memory behaviors, not to memorize benchmark prompts.
2. **No full skill orchestration router in v1.** Skill selection and injection may be manual or
   minimally automated; dynamic tool exposure routers are explicitly deferred.
3. **No major repository restructure.** v1 does not require splitting YAAM into multiple Poetry
   projects or moving code into `core/` / `agents/` monorepo subtrees.
4. **No dependency churn.** Adding/updating dependencies is out of scope unless explicitly approved.
5. **No freezing without evidence.** The mechanism layer is frozen-by-default, but “hard freeze”
   (strict gates) requires maturity evaluation and evidence.

## 5. Decisions to Record (v1)

### 5.1 Skills location

**Decision (proposed):** Place skills at repo root: `skills/`.

**Rationale:**
- Discoverable for both internal agents and external assistants.
- Keeps skills as first-class repository artifacts, consistent with progressive disclosure.

### 5.2 Tools location

**Decision (v1):** Tools remain in `src/` (mechanism layer). Skills are policy-only (`SKILL.md`).

**Rationale:**
- Reduces duplication and avoids embedding executable logic in skills prematurely.
- Supports “frozen mechanism + iterated policy” workflow.

### 5.3 Benchmark usage

**Decision (v1):** Benchmark is feedback-only, not an optimization target.

**Rationale:**
- Avoids methodological issues in the system paper.
- Preserves benchmark validity as a regression and stress-testing signal.

## 6. Success Criteria

Repository Harness v1:
- Instruction hierarchy is consistent and does not contain conflicting copy-pastable snippets.
- Instruction drift checks run in tests and fail on reintroduction of banned patterns.

Skills v1:
- `skills/` directory exists with an initial set of skills and a consistent template.
- Each skill clearly documents:
  - intent and when to use it,
  - required mechanism interfaces,
  - safety/guardrails to avoid layer jumping,
  - and example “recipes” that are domain/system oriented (not benchmark-script oriented).

Benchmark feedback:
- Runs are repeatable and treated as regression signals.
- Results can be used to guide improvements in policy (skills/prompts/orchestration) without
  modifying mechanism code by default.

## 7. Deliverables

1. An ADR to formalize the Mechanism/Policy split and the frozen-by-default mechanism posture.
2. A plan for skill authoring and mechanism maturity evaluation.
3. A `skills/_template/` with a stable `SKILL.md` structure.

## 8. Open Questions

1. Which exact directories are considered “mechanism” for freeze-by-default beyond `src/storage/`?
2. What is the minimal “skill registry” mechanism for v1 (manual selection vs simple loader)?
3. What subset of skills should be authored first to match the system paper’s core narrative?
