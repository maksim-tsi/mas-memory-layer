---
name: "L3 Graph Traversal (Neo4j Templates)"
description: "Safely answer relationship and timeline questions via template-based L3 graph traversal (Neo4j). Keywords: relationship, parties, causal chain, timeline, journey, document flow."
version: "1.0.0"
compatibility: "YAAM runtime agents (LangGraph ToolRuntime)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools:
  - "l3_query_graph"
---

## When to Use

- You need **relationships** (shipper/consignee/carrier), **timelines**, or **causal chains**.
- The question is naturally expressed as a graph traversal rather than a text search.

## Preconditions

- L3 graph tier is configured and contains entities/edges for the domain.

## Inputs and Outputs

- **Input:** `template_name` + `parameters` (typed dict).
- **Output:** JSON with results and the merged parameters used.

## Tools

- `l3_query_graph(template_name, parameters)`

## Procedure (Recipe)

1. Choose the template that matches the question.
2. Provide only the required parameters; keep `max_hops` conservative (e.g., 10–15).
3. Interpret results as *evidence*; do not hallucinate missing nodes/edges.

### Example Tool Call

```json
{"template_name": "get_container_journey", "parameters": {"container_id": "MAEU1234567", "max_hops": 12}}
```

## Guardrails (Non-Negotiable)

- Do not run raw Cypher. Only templates are permitted (safety and injection prevention).
- Do not broaden `max_hops` without a reason (risk of large responses and weak grounding).

## Failure Modes and Fallback

- If a template returns empty: fall back to `l3_search_episodes` (semantic) or `l2_search_facts` (exact).

