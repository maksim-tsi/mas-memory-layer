---
name: "Prospective Memory Followthrough"
description: "Execute a requested action after a delay (e.g., in N turns) or at a specific future condition. Keywords: in 2 turns, after responding, on my 5th message, later, remind me, append on response N."
version: "1.0.0"
compatibility: "YAAM runtime agents (OpenAI-compatible chat, LangGraph ToolRuntime / AutoGen function calling)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools: []
---

## Policy

- Track delayed instructions precisely (turn counts and conditions).
- When the trigger condition is met (e.g., "5th response"), perform the action exactly then.
- If the user asks to cancel/forget the delayed instruction, stop applying it immediately.

## Output Rules

- Always produce the user-facing answer for the current turn.
- If a delayed action triggers on this turn (e.g., "append the quote"), append it after the main answer exactly as requested.
- Do not output routing/planning text (no "selected_skill", "why", "next_action").
