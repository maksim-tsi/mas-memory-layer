---
name: "Triggered Response Conditions"
description: "Apply or cancel conditional response rules: 'When I say X, say Y' or 'Whenever I do Z, respond with ...'. Keywords: whenever, when I say, if I say, then say, always respond, cancel instructions."
version: "1.0.0"
compatibility: "YAAM runtime agents (OpenAI-compatible chat, LangGraph ToolRuntime / AutoGen function calling)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools: []
---

## Policy

- Identify conditional response rules and apply them only when the condition matches.
- If the user cancels/forgets a rule, stop applying it immediately.
- If the user provides a new conditional rule that conflicts with an older one, follow the most recent rule.

## Output Rules

- Keep the response to the minimum required by the active condition.
- Do not output routing/planning text (no "selected_skill", "why", "next_action").
