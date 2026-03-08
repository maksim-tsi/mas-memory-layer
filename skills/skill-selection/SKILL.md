---
name: "Skill Selection (Executive Function)"
description: "Select the most appropriate YAAM skill(s) for the current user intent and constraints. Keywords: which skill, choose tool, decide strategy, routing, executive function."
version: "1.0.0"
compatibility: "YAAM runtime agents (LangGraph ToolRuntime / AutoGen function calling)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools:
  - "get_context_block"
  - "memory_query"
---

## When to Use

- You need to decide **which skill** to apply before acting.
- The user request is ambiguous (recap vs relationship vs precedent vs policy).
- You want to minimize tool bloat by exposing only a small subset of tools for the next step.

## Inputs and Outputs

- **Input:** the user’s latest request + (optional) a short context block.
- **Output:** a recommended skill name (or 1–2 skills in sequence) plus a short rationale and the next tool call.

## Procedure (Recipe)

1. If session context may matter, call `get_context_block` (`format="text"`, conservative limits).
2. Classify the user request into one of the routing buckets:
   - **Recap / grounding:** use `Context Block Retrieval (L1+L2+L3+L4)`.
   - **Exact identifiers / fast lookup:** use `L2 Fact Lookup (Postgres Working Memory)`.
   - **Precedents / “similar case”:** use `L3 Similar Episodes (Qdrant Episodic Memory)`.
   - **Relationships / timeline / causality:** use `L3 Graph Traversal (Neo4j Templates)`.
   - **General patterns / best practices:** use `L4 Knowledge Synthesis (Typesense + Synthesizer)`.
   - **What to retain/promote:** use `CIAR Scoring and Promotion Gating`.
   - **Model ignores retrieved evidence:** use `Retrieval-Reasoning Gap Mitigation`.
   - **Create/refine reusable rules:** use `Knowledge Lifecycle Distillation`.
3. If the user request is narrowly scoped, optionally run a small `memory_query` to confirm the relevant tier(s).
4. Return:
   - `selected_skill`: one of the skill names above,
   - `why`: 1–3 bullet reasons,
   - `next_action`: the exact next tool call parameters.

## Guardrails (Non-Negotiable)

- Do not call many tools “just in case”. Select a skill and proceed with a minimal tool set.
- Do not modify mechanism (`src/storage/`) to address a policy/routing problem.

