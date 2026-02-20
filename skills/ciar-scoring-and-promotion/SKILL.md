---
name: "CIAR Scoring and Promotion Gating"
description: "Decide what should be promoted to L2 working memory using CIAR (certainty×impact×age decay×recency boost). Keywords: importance, promote, retain, threshold, audit, why this fact matters."
version: "1.0.0"
compatibility: "YAAM runtime agents (LangGraph ToolRuntime)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools:
  - "ciar_calculate"
  - "ciar_filter"
  - "ciar_explain"
  - "memory_store"
---

## When to Use

- You need to justify whether a fact is significant enough for retention/promotion.
- You are curating “working memory” facts to support enterprise auditability.

## Preconditions

- CIAR tools are available; promotion engines may run asynchronously.

## Inputs and Outputs

- **Input:** candidate fact(s) with explicit certainty/impact and approximate age/access.
- **Output:** CIAR score breakdown and an explicit retain/promote decision.

## Tools

- `ciar_calculate(...)`: score a single fact with components and a promotable verdict.
- `ciar_filter(facts, min_threshold)`: batch-filter a list of facts.
- `ciar_explain(...)`: generate a human-readable explanation of the score.
- `memory_store(content, tier="L2")`: queue a promotable item for L2 via the system’s promotion cycle.

## Procedure (Recipe)

1. For each candidate, assign `certainty` and `impact` explicitly (avoid implicit confidence).
2. Use `ciar_calculate` to score and decide promotability.
3. If promotable and user-aligned, store via `memory_store(..., tier="L2")`.
4. If a decision needs to be audited, attach the CIAR explanation to the record’s metadata (when supported).

### Example Tool Calls

```json
{"content": "Customer XYZ may cancel if delivery misses Friday 17:00.", "certainty": 0.9, "impact": 0.9, "fact_type": "constraint", "days_old": 0, "access_count": 0}
```

```json
{"content": "Customer XYZ may cancel if delivery misses Friday 17:00.", "tier": "L2", "metadata": {"fact_type": "constraint"}}
```

## Guardrails (Non-Negotiable)

- Do not over-promote: keep L2 as high-signal working memory (min threshold typically 0.6+).
- Do not store secrets or raw credentials in fact content.

## Failure Modes and Fallback

- If promotion is not configured: store in L1 with explicit tags and request operator follow-up.

