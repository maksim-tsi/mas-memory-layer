---
name: "L4 Knowledge Synthesis (Typesense + Synthesizer)"
description: "Synthesize distilled knowledge (L4) into an answer with provenance and conflict detection. Keywords: best practice, common causes, policy, rule, pattern, contradictions."
version: "1.0.0"
compatibility: "YAAM runtime agents (LangGraph ToolRuntime)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools:
  - "synthesize_knowledge"
  - "l4_search_knowledge"
---

## When to Use

- The user asks for **general rules/patterns** rather than a specific past event.
- You need to reconcile multiple knowledge documents and surface contradictions.

## Preconditions

- L4 is configured (Typesense) and the memory system provides a knowledge synthesizer.

## Inputs and Outputs

- **Input:** query + optional metadata filters (domain constraints).
- **Output:** JSON with `synthesized_text`, source candidates, and conflicts (if any).

## Tools

- `synthesize_knowledge(query, metadata_filters, max_results)`
- `l4_search_knowledge(query, filters, limit)` (fallback: direct retrieval without synthesis)

## Procedure (Recipe)

1. Prefer `synthesize_knowledge` with `max_results=3..7`.
2. If the synthesizer is unavailable or errors, fall back to `l4_search_knowledge` and provide a cautious summary.
3. If conflicts are reported, present them explicitly and ask the user which policy to prefer.

### Example Tool Call

```json
{"query": "common causes of port delays and mitigations", "metadata_filters": {"category": "delays"}, "max_results": 5}
```

## Guardrails (Non-Negotiable)

- Do not present synthesized text as ground truth when conflicts exist.
- Do not leak internal identifiers unless they are required for the user’s operational workflow.

## Failure Modes and Fallback

- If both synthesis and search return empty: revert to L3 episode similarity search for “case-based” evidence.

