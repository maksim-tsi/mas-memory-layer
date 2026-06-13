---
name: "Skill Builder (YAAM)"
description: "Use when creating or updating YAAM skills (policy artifacts) for runtime agents, especially for multi-agent memory management, knowledge lifecycle automation (promotion/distillation), and evidence-grounded reasoning. Triggers: write a new skill, update a skill, design SKILL.md, progressive disclosure, skill inventory."
version: "1.0.0"
compatibility: "Development-time assistants (Codex, Claude Code) authoring YAAM `skills/` for LangGraph/ToolRuntime-based agents"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools: []
---

## Purpose

Create **high-signal, low-bloat** skills that:

- support progressive disclosure (inventory → selected skill body → optional references),
- map cleanly onto YAAM’s tool surface (LangGraph ToolRuntime tools),
- preserve the Mechanism/Policy boundary (ADR-010), and
- improve auditability (provenance, explicit gating, safe fallbacks).

## Scope (v1)

This skill is for authoring **policy-first** packages under `skills/`:

- `skills/<skill_slug>/SKILL.md` (required)
- `skills/<skill_slug>/references/` (optional; heavy reference only)

Do not create extra files by default (e.g., per-skill README, changelog).

## Design Constraints (Non-Negotiable)

1. **Mechanism freeze-by-default:** do not modify `src/storage/` to “make a skill work” unless explicitly authorized and backed by evidence.
2. **Tool-first integration:** skills must refer to **tool names** (e.g., `get_context_block`, `l2_search_facts`) rather than adapter methods.
3. **No train-on-test:** do not encode benchmark prompts or benchmark-specific scripts.
4. **Token discipline:** assume the agent is smart; include only non-obvious domain/procedural guidance.

## Skill Authoring Workflow

### Step 1 — Define the “Pressure Scenario” (Acceptance Tests)

Write 3–5 short prompts that should trigger the skill, plus 2 that must not.

Example triggers for a memory skill:
- “What do we know about shipment XYZ and what changed since yesterday?”
- “Find similar incidents to this customs delay.”
- “Show the causal chain for this delay.”

Non-triggers:
- “What is a vector database?”
- “Explain Redis in general.”

### Step 2 — Choose a Single Intent + Boundary

Define:

- **Primary intent:** one sentence.
- **Not in scope:** 2–4 bullets (prevents “kitchen sink” growth).
- **Primary tier(s):** L2 vs L3 vs L4 vs unified context block.

Routing cues:
- **Exact identifiers / operational lookup:** L2 (`l2_search_facts`)
- **Precedent / similarity:** L3 vector (`l3_search_episodes`)
- **Relationships / timeline / causality:** L3 graph templates (`l3_query_graph`)
- **General rules / patterns:** L4 synthesis/search (`synthesize_knowledge` / `l4_search_knowledge`)
- **Grounding for response:** `get_context_block`

### Step 3 — Frontmatter (Discovery Metadata)

Write frontmatter fields, but optimize primarily for discovery via:

- `name` (short, specific)
- `description` (high-signal triggers + domain keywords)

Rule: `description` should describe **when to use** the skill, not how it works.

### Step 4 — Body (Procedure + Guardrails)

Minimum sections to include:

- **When to Use** (bullets, symptom-driven)
- **Inputs and Outputs**
- **Tools** (only the expected tool subset)
- **Procedure (Recipe)** (step-by-step, with decision points)
- **Guardrails (Non-Negotiable)** (what the agent must not do)
- **Failure Modes and Fallback** (safe alternatives)

Keep tool-call examples minimal and copy-pastable (JSON-like payloads).

### Step 5 — References (Only When Necessary)

If the skill needs heavy reference (schemas, long examples):

- put it in `references/`,
- link to it from `SKILL.md`,
- and describe exactly when to open it (avoid loading everything by default).

### Step 6 — Repository Hygiene

After adding/updating skills:

- add the new skill slug to `skills/README.md` inventory,
- run `./.venv/bin/ruff check .`,
- run `./.venv/bin/pytest tests/ -q` (offline-by-default mode).

## Quality Rubric (Quick Check)

A good YAAM skill:

- has a single intent and explicit “not in scope” bullets,
- names the primary tier/tool family it expects,
- contains at least one safe fallback path,
- avoids raw query languages unless the tool enforces safety (e.g., template-only graph queries),
- includes explicit guidance to mitigate retrieval-reasoning failure (evidence-first reasoning),
- never instructs mechanism edits as the first-line fix.

