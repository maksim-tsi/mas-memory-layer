---
name: "Context Block Retrieval (L1+L2+L3+L4)"
description: "Retrieve a focused context block for a session: recent turns, significant facts (CIAR), episode summaries, and knowledge snippets. Keywords: context, recap, what do we know, prior conversation, memory block."
version: "1.0.0"
compatibility: "YAAM runtime agents (LangGraph ToolRuntime)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools:
  - "get_context_block"
  - "memory_query"
---

## When to Use

- The user asks for a recap of “what we know” in the current session.
- The agent needs high-signal context before answering (especially long-running enterprise tasks).
- The agent suspects a **retrieval-reasoning gap** and wants to ground the next reasoning step in an explicit context block.

## Preconditions

- Tool runtime provides `session_id` and `memory_system` (via MAS ToolRuntime context).

## Inputs and Outputs

- **Input:** `min_ciar`, `max_turns`, `max_facts`, and an optional follow-up natural language query.
- **Output:** a structured or textual context block suitable for prompt injection and citation.

## Tools

- `get_context_block(min_ciar, max_turns, max_facts, format)`: fetches recent turns + top facts.
- `memory_query(query, limit, l2_weight, l3_weight, l4_weight)`: hybrid search when the user question is specific.

## Procedure (Recipe)

1. Call `get_context_block` with conservative defaults (`min_ciar=0.6`, `max_turns=20`, `max_facts=10`).
2. If the user question is specific (entity/ID/topic), call `memory_query` with a targeted query and a small `limit` (5–10).
3. Answer using only the returned context. If context is insufficient, ask a clarification question rather than guessing.

### Example Tool Calls

```json
{"min_ciar": 0.6, "max_turns": 20, "max_facts": 10, "format": "text"}
```

```json
{"query": "Shanghai shipment ETA Friday 17:00", "limit": 8, "l2_weight": 0.4, "l3_weight": 0.4, "l4_weight": 0.2}
```

## Guardrails (Non-Negotiable)

- Do not request direct DB access or raw queries; use tools only.
- Do not “improve retrieval” by modifying mechanism (`src/storage/`); escalate with evidence instead.

## Failure Modes and Fallback

- If `get_context_block` fails: fall back to `memory_query` with a broad query (“current session summary”).
- If both return empty: treat as “no memory available” and proceed with the user’s provided input only.

