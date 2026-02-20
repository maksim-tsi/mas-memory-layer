---
name: "Retrieval-Reasoning Gap Mitigation"
description: "Mitigate cases where retrieved facts are present but the model ignores them or contradicts them. Keywords: retrieval-reasoning gap, ignores context, hallucination, grounding, evidence table."
version: "1.0.0"
compatibility: "YAAM runtime agents (LangGraph ToolRuntime)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools:
  - "get_context_block"
  - "memory_query"
  - "l2_search_facts"
  - "l3_search_episodes"
  - "l3_query_graph"
  - "l4_search_knowledge"
  - "synthesize_knowledge"
---

## When to Use

- The model’s draft answer contradicts retrieved facts, or fails to use them.
- The user request requires multi-step reasoning grounded in specific evidence.

## Inputs and Outputs

- **Input:** user question + retrieved context (context block and/or tier queries).
- **Output:** an answer that explicitly cites evidence items, plus a short “evidence used” section when appropriate.

## Procedure (Recipe)

1. **Grounding pass (minimal):**
   - Call `get_context_block(format="text")` with conservative limits.
   - If the question is specific, call exactly one targeted retrieval tool:
     - `l2_search_facts` for exact identifiers,
     - `l3_query_graph` for relationships/timelines,
     - `l3_search_episodes` for precedents,
     - `l4_search_knowledge` / `synthesize_knowledge` for patterns.
2. **Evidence table:**
   - Extract 3–7 atomic claims from retrieved results.
   - For each claim, include: `claim`, `source_tier`, `supporting_snippet`, and `confidence`.
3. **Reasoning constraint:**
   - Answer the user question **only** using the evidence table.
   - If evidence is insufficient, ask 1 clarification question (or state what is missing).
4. **Contradiction handling:**
   - If evidence conflicts (or L4 synthesis reports conflicts), present both sides and ask which policy to apply.

### Example Tool Calls

```json
{"min_ciar": 0.6, "max_turns": 20, "max_facts": 10, "format": "text"}
```

```json
{"query": "container MAEU1234567 ETA Friday 17:00", "min_ciar": 0.7, "limit": 20}
```

## Guardrails (Non-Negotiable)

- Do not “fill in” missing evidence with plausible-sounding details.
- Do not broaden retrieval aggressively (avoid large, low-signal context blocks).

## Failure Modes and Fallback

- If tier tools fail: fall back to `memory_query` with a small limit (5–10).
- If retrieval is consistently empty: treat the task as “no memory available” and proceed using user-provided information only.

