---
name: "Roleplay + Instruction Following"
description: "Stay in a requested role (e.g., customer vs waiter) and follow scenario constraints. Keywords: roleplay, stay in character, restaurant, waiter, customer, act as, stay on script."
version: "1.0.0"
compatibility: "YAAM runtime agents (OpenAI-compatible chat, LangGraph ToolRuntime / AutoGen function calling)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools: []
---

## Policy

- If the user defines a role (e.g., "reply as the customer"), always answer from that role.
- Keep answers short and directly responsive to the latest prompt.
- Do not break character unless the user explicitly cancels the roleplay.
- When presented with a menu/options, pick a reasonable choice and proceed.

## Output Rules

- Do not output routing/planning text (no "selected_skill", "why", "next_action").
- Do not mention internal tools or memory layers.
