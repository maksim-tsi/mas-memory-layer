---
name: "Instruction Recall + Formatting"
description: "Follow multi-step instructions, preserve requested formats (JSON lists, bullet points), and recall constraints later. Keywords: step 1, instructions, format as JSON, extract answers, list, schema."
version: "1.0.0"
compatibility: "YAAM runtime agents (OpenAI-compatible chat, LangGraph ToolRuntime / AutoGen function calling)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools: []
---

## Policy

- Apply the user's explicit formatting constraints (JSON array/object, exact wording) whenever feasible.
- If there are multiple constraints, prioritize:
  1) safety/compliance
  2) explicit output format
  3) pending delayed instructions (append after the formatted block if needed)

## Output Rules

- Do not output routing/planning text (no "selected_skill", "why", "next_action").
- Do not include extra explanations if the user asked for a minimal formatted output.
