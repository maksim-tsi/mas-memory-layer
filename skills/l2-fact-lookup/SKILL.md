---
name: "L2 Fact Lookup (Postgres Working Memory)"
description: "Perform fast keyword fact lookup in L2 working memory (Postgres tsvector). Keywords: exact match, SKU, container_id, error code, party name, port code."
version: "1.0.0"
compatibility: "YAAM runtime agents (LangGraph ToolRuntime)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools:
  - "l2_search_facts"
  - "ciar_calculate"
  - "ciar_explain"
---

## When to Use

- You need **exact or near-exact** matches: container IDs, SKUs, bill-of-lading numbers, port codes, error codes.
- You want the fastest path (avoid semantic search) for operational identifiers.

## Preconditions

- L2 tier is configured and reachable; the runtime provides `session_id`.

## Inputs and Outputs

- **Input:** query string + optional `min_ciar` threshold.
- **Output:** JSON of matching facts with CIAR and metadata.

## Tools

- `l2_search_facts(query, min_ciar, limit)`
- `ciar_calculate(...)` / `ciar_explain(...)` (optional; to justify promotion/retention decisions)

## Procedure (Recipe)

1. Run `l2_search_facts` with a narrow query and `limit` (10–30).
2. If results are noisy, raise `min_ciar` (e.g., 0.7–0.8) or tighten the keyword.
3. If you need to justify why a candidate fact should be retained/promoted, compute CIAR explicitly with `ciar_calculate` and optionally produce a human explanation with `ciar_explain`.

### Example Tool Calls

```json
{"query": "MAEU1234567", "min_ciar": 0.7, "limit": 20}
```

## Guardrails (Non-Negotiable)

- Do not run SQL; only use `l2_search_facts`.
- Do not store secrets in fact content or metadata.

## Failure Modes and Fallback

- If L2 is unavailable: fall back to `memory_query` (hybrid) or `get_context_block` to recover recent turns.

