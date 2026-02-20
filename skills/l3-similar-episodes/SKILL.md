---
name: "L3 Similar Episodes (Qdrant Episodic Memory)"
description: "Find semantically similar past episodes (L3) using vector similarity search. Keywords: similar incident, like last time, precedent, prior case, pattern match."
version: "1.0.0"
compatibility: "YAAM runtime agents (LangGraph ToolRuntime)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools:
  - "l3_search_episodes"
---

## When to Use

- The user asks: “Have we seen something like this before?” or “What happened in similar cases?”
- You need precedent retrieval across time (not just current-session facts).

## Preconditions

- L3 episodic tier is configured; embeddings are available for episode chunks.

## Inputs and Outputs

- **Input:** natural language `query`, optional `filters`, and `limit`.
- **Output:** JSON with ranked similar episodes/chunks and metadata (topics, scores).

## Tools

- `l3_search_episodes(query, limit, filters)`

## Procedure (Recipe)

1. Express the query as the *situation*, not a keyword list (include constraints and outcome).
2. Use `limit=5..10` to avoid context overload.
3. If you have a session boundary requirement, pass a filter (e.g., `{"session_id": "..."}`) when appropriate.
4. After retrieval, summarize the top 3 episodes and extract actionable similarities/differences.

### Example Tool Call

```json
{"query": "customs clearance delay expedited broker fasttrack logistics", "limit": 8, "filters": null}
```

## Guardrails (Non-Negotiable)

- Do not claim a precedent is applicable unless you can explain the similarity using retrieved fields.

## Failure Modes and Fallback

- If results are empty: fall back to `l2_search_facts` for exact identifiers, or `l3_query_graph` when relationships matter.

