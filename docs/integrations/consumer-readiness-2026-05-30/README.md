# YAAM Consumer Readiness Wave

**Date:** 2026-05-30  
**Status:** Prepared instructions for sequential consumer testing  
**Primary runtime:** `skz-data-lv`  
**Consumer host:** MacBook on the same local network  
**REST endpoint:** `http://192.168.107.187:8002`  
**MCP endpoint:** `http://192.168.107.187:8003/mcp`

This directory contains the handoff package for the first project-scoped YAAM consumer readiness
wave.

## Why One Project At A Time

Current YAAM deployment uses one runtime-level project namespace per service instance. The active
`YAAM_PROJECT_ID` derives the logical DBMS namespace for the running `mas-agent` and `yaam-mcp`
containers. That means a single shared endpoint should be handed to one consumer project at a time
unless operators intentionally run separate YAAM instances on separate ports.

Sequential testing avoids mixed L2/L3/L4 records, keeps Phoenix evidence easy to review, and lets
YAAM maintainers restart the same endpoint with a clean project namespace for each consumer.

## Recommended Order

1. `agentic-scm-tra26`
   - Best first target because its requirements are closest to the implemented REST v2 L2/L3/L4
     workflows.
   - Validates the core service path before MCP-heavy consumers begin.
2. `scm-skill-factory`
   - Exercises both REST v2 and MCP, including evidence, curation, trace correlation, and skill
     generation memory scenarios.
   - Uses the optional Skill Factory MCP domain pack for skill, CTT, run, QA-status, active-tool
     status, and repair-pattern prompt checks.
3. `scm-cognitive-sandwich`
   - Most artifact-centric and MCP-first.
   - Best after the core path is proven, because several artifact lifecycle requirements are
     intentionally classified as partial or missing in the current YAAM surface.

## Project Instructions

- [agentic-scm-tra26](agentic-scm-tra26-test-instructions.md)
- [scm-skill-factory](scm-skill-factory-test-instructions.md)
- [scm-cognitive-sandwich](scm-cognitive-sandwich-test-instructions.md)
- [readiness report template](readiness-report-template.md)

Use [consumer-testing-sequence.md](consumer-testing-sequence.md) as the operator checklist for each
testing window.

## Report Location

Consumer reports collected on the MacBook should be stored under:

```text
docs/integrations/consumer-readiness-2026-05-30/reports/
```

Use:

```text
YYYY-MM-DD-<project-id>-readiness-report.md
```

Reports must include sanitized request/response snippets, trace ids, artifact paths, and findings.
Do not include `.env` contents, API keys, tokens, passwords, or provider secrets.

## Documentation Base

These instructions build on:

- `docs/integrations/consumer-readiness-2026-05-28/consumer-readiness-test-assignment.md`
- `docs/user-guide/rest-v2.md`
- `docs/user-guide/mcp-v1.md`
- `docs/integrations/yaam_v2_connection_policy.md`
- `docs/requirements/yaam-requirements-registry.md`
