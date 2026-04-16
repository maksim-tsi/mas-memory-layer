---
name: "Skill Name"
description: "One sentence describing when to use this skill, with concrete keywords for matching."
version: "1.0.0"
compatibility: "YAAM runtime agents (LangGraph ToolRuntime / AutoGen function calling)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools:
  - "tool_name_1"
  - "tool_name_2"
---

## When to Use

- Describe the triggering user intent and typical situations.
- Include explicit **domain cues** (e.g., “shipment”, “ETA”, “container_id”, “customs delay”).

## Preconditions

- The runtime provides `session_id` and a configured `memory_system` (via ToolRuntime context).
- The required tools in `allowed-tools` are available.

## Inputs and Outputs

- **Inputs:** what the agent needs (identifiers, constraints, query text).
- **Outputs:** what the agent produces (answer text, JSON summary, action plan).

## Tools

List and describe the tools this skill expects (use tool names, not adapter methods).

## Procedure (Recipe)

1. Step-by-step sequence.
2. Include safe defaults and decision points.
3. Prefer deterministic selection rules over “try random things”.

### Example Tool Calls

Provide minimal examples (JSON-like) suitable for tool calling.

## Guardrails (Non-Negotiable)

- Do not modify `src/storage/` (mechanism) unless explicitly authorized.
- Do not access DBs directly; use tools.
- Do not run raw, user-provided query languages (e.g., Cypher/SQL) unless explicitly permitted.

## Failure Modes and Fallback

- If the primary tool fails or returns empty results, specify the fallback path.
- If confidence is low, specify how to ask for clarification.

## Observability (Optional)

- What status updates should be streamed (short, low-noise).
- What metadata should be attached to stored facts (no secrets).

