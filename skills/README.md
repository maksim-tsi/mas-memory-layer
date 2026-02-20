# Skills (v1)

This directory contains **policy-first** skill packages for YAAM runtime agents.
Skills are designed for **progressive disclosure**: an agent should load only the
small inventory plus the selected skill’s `SKILL.md`, rather than ingesting all
operational knowledge at once.

## Principles (ADR-010)

- **Mechanism vs Policy:** mechanism lives primarily in `src/storage/`; skills are policy-only.
- **Frozen-by-default mechanism:** do not modify `src/storage/` to “make a skill work” without
  explicit authorization and evidence.
- **No train-on-test:** avoid embedding benchmark-specific prompts or scripts.

## Skill Format

Each skill is a folder:

- `skills/<skill_slug>/SKILL.md` (required)
- `skills/<skill_slug>/references/` (optional; schemas, examples, invariants)

`SKILL.md` uses YAML frontmatter with at least:

- `name`
- `description` (must include domain keywords for matching)
- `version`
- `compatibility` (e.g., LangGraph ToolRuntime, AutoGen function calling)

This format is intentionally compatible with common “agent skills” loaders. citeturn5view1turn5view0

## Authoring Guidelines (Codex / Claude Code Friendly)

- **Single intent:** one skill should solve one class of tasks (avoid “kitchen sink” skills).
- **High-signal description:** include concrete keywords and avoid generic phrases; many routers use
  descriptions for matching. citeturn3view0
- **Tool-first recipes:** describe *which tools to call* and *in what order*; include input/output
  expectations and safe defaults.
- **Guardrails:** document what the agent must **not** do (e.g., no raw Cypher, no direct DB access,
  no mechanism edits).
- **Failure modes:** specify safe fallbacks (e.g., switch from L3 graph traversal to L2 fact lookup).

## Runtime Mapping (LangGraph / AutoGen)

In the current codebase, tools are exposed via LangChain/LangGraph `ToolRuntime` and the MAS wrapper
`MASToolRuntime` (`src/agents/runtime.py`). Skills should reference the *tool names* (e.g.,
`get_context_block`, `l2_search_facts`) rather than internal adapter methods.

AutoGen-based runtimes can treat each skill as:

- a **system instruction** block (from `SKILL.md`), plus
- a **tool subset** to expose for the current turn (from `allowed-tools` and the “Tools” section).

