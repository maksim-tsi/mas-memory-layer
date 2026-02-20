---
name: "Knowledge Lifecycle Distillation"
description: "Distill reusable patterns/rules from multiple episodes and store them as knowledge candidates with provenance. Keywords: distillation, pattern, rule, best practice, promote to knowledge base, lifecycle."
version: "1.0.0"
compatibility: "YAAM runtime agents (LangGraph ToolRuntime)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools:
  - "l3_search_episodes"
  - "l4_search_knowledge"
  - "synthesize_knowledge"
  - "ciar_calculate"
  - "memory_store"
---

## When to Use

- You have multiple similar episodes and want to extract a **general rule** with scope and exceptions.
- You need a candidate policy/insight suitable for L4 semantic memory, with auditability.

## Inputs and Outputs

- **Input:** a situation description + constraints (domain, entity types, time window).
- **Output:** a “knowledge candidate” object (rule/pattern) with provenance and confidence, queued for lifecycle processing.

## Procedure (Recipe)

1. **Collect candidate evidence:**
   - Use `l3_search_episodes` to retrieve 5–10 similar episodes for the situation.
   - Use `l4_search_knowledge` to check whether an equivalent rule already exists.
2. **Synthesize (optional):**
   - If a synthesizer is available, use `synthesize_knowledge` to consolidate existing L4 docs and detect conflicts.
3. **Draft the distillation artifact (policy-level):**
   - Create a candidate with fields:
     - `title`
     - `rule` (normative statement)
     - `scope` (when it applies)
     - `exceptions`
     - `signals` (what to look for in L2/L3)
     - `recommended_actions`
     - `provenance` (episode identifiers/snippets)
     - `confidence` and `impact`
4. **Gate with CIAR:**
   - Score the candidate summary with `ciar_calculate` (treat it as a high-impact “fact” when appropriate).
5. **Queue for lifecycle processing:**
   - Store the candidate via `memory_store(tier="L2")` with metadata tags (e.g., `{"knowledge_candidate": true, "knowledge_type": "pattern"}`).
   - Note: in v1, direct L4 writes are not exposed as tools; L4 population is expected to occur via configured lifecycle engines and operator workflows.

### Example Tool Calls

```json
{"query": "customs clearance delays mitigated by express broker", "limit": 8, "filters": null}
```

```json
{"content": "Pattern candidate: Use express broker to mitigate customs delays when cancellation risk is high.", "certainty": 0.7, "impact": 0.9, "fact_type": "event", "days_old": 0, "access_count": 0}
```

```json
{"content": "KnowledgeCandidate: {\"title\":\"Express broker escalation\",\"rule\":\"...\"}", "tier": "L2", "metadata": {"knowledge_candidate": true, "knowledge_type": "pattern"}}
```

## Guardrails (Non-Negotiable)

- Do not distill benchmark-specific tricks; distillation must be domain/system oriented.
- Do not claim a rule is universally valid; always specify scope and exceptions.
- Do not modify mechanism (`src/storage/`) to force a lifecycle behavior; escalate with evidence instead.

## Failure Modes and Fallback

- If episode retrieval is sparse: ask the user for 1–2 additional constraints (entity ID, time window, domain).
- If conflicts exist in L4: record both variants as candidates and require operator/user preference.

