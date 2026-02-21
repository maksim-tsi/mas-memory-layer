---
name: "Clandestine Message Synthesis"
description: "Extract and synthesize meeting details (time/place/items) from scattered messages. Keywords: clandestine, meeting, bring, where, when, received messages."
version: "1.0.0"
compatibility: "YAAM runtime agents (OpenAI-compatible chat, LangGraph ToolRuntime / AutoGen function calling)"
metadata:
  yaam.layer: "policy"
  yaam.mechanism_contract: "docs/specs/spec-mechanism-maturity-and-freeze.md"
allowed-tools: []
---

## Policy

- Track details across messages: participants, time, location, and what to bring.
- When asked, answer as specifically as possible using only the information provided.
- If information is missing, state what's missing succinctly and provide best-effort partials.

## Output Rules

- Do not output routing/planning text (no "selected_skill", "why", "next_action").
- Do not invent extra details beyond what the conversation supports.
