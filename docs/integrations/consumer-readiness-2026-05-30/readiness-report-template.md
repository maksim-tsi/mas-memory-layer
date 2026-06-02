# YAAM Consumer Readiness Report Template

Save the completed report under:

```text
docs/integrations/consumer-readiness-2026-05-30/reports/YYYY-MM-DD-<project-id>-readiness-report.md
```

Do not include secrets, `.env` contents, provider API keys, tokens, passwords, or private
credentials.

```markdown
# <Project ID> YAAM Readiness Report

**Date:** YYYY-MM-DD
**Consumer project:** <agentic-scm-tra26 | scm-skill-factory | scm-cognitive-sandwich>
**Consumer host/runtime:** <host, branch, commit if available>
**YAAM REST endpoint:** http://192.168.107.187:8002
**YAAM MCP endpoint:** http://192.168.107.187:8003/mcp
**YAAM project namespace:** <YAAM_PROJECT_ID>
**Overall verdict:** pass | pass-with-findings | blocked | fail

## Summary

<One paragraph explaining whether this consumer can use YAAM now and what the most important
limitations are.>

## Environment

| Field | Value |
| --- | --- |
| Consumer project |  |
| Consumer branch/commit |  |
| Test host |  |
| YAAM REST endpoint |  |
| YAAM MCP endpoint |  |
| YAAM project namespace |  |
| Test timestamp and timezone |  |
| Trace ids used |  |

## Documentation Used

| Document | Path or link | Notes |
| --- | --- | --- |
| Project-specific instruction |  |  |
| REST v2 guide | `docs/user-guide/rest-v2.md` |  |
| MCP v1 guide | `docs/user-guide/mcp-v1.md` |  |
| Requirements registry | `docs/requirements/yaam-requirements-registry.md` |  |

## Executed Checks

| Check | Interface | Result | Evidence | Notes |
| --- | --- | --- | --- | --- |
| Health | REST | pass/fail/blocked |  |  |
| Discovery/readiness | MCP | pass/fail/blocked |  |  |
| L2 store/retrieve | REST or MCP | pass/fail/blocked |  |  |
| L2 isolation | REST or MCP | pass/fail/blocked |  |  |
| L3 assimilate/query | REST or MCP | pass/fail/blocked |  |  |
| L4 finalize/search | REST or MCP | pass/fail/blocked |  |  |
| Evidence/CIAR | REST or MCP | pass/fail/blocked |  |  |
| Negative scenario | REST or MCP | pass/fail/blocked |  |  |
| Project-specific scenario | REST or MCP | pass/fail/blocked |  |  |

## Requirement Coverage

| Requirement ID | Requirement summary | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| YAAM-REQ-0001 |  | implemented/partially implemented/missing/unclear |  |  |

Allowed statuses:

- `implemented`
- `partially implemented`
- `missing`
- `unclear`

Every non-`implemented` row should have a finding.

## Findings

| Finding ID | Priority | Category | Title | Evidence | Suggested action |
| --- | --- | --- | --- | --- | --- |
| <PROJECT>-YAAM-001 | P0/P1/P2/P3 | contract/deployment/documentation/MCP/observability/performance/security/data-correctness/UX |  |  |  |

Priority guidance:

- `P0`: blocks any meaningful integration.
- `P1`: breaks a required workflow or risks data/provenance correctness.
- `P2`: important gap with an acceptable workaround.
- `P3`: documentation, ergonomics, or polish.

## Blockers

<List blockers. If none, write "None".>

## Recommended Next Actions

<Prioritized actions for YAAM maintainers and/or the consumer project.>

## Raw Evidence

<Paste sanitized request/response snippets, command outputs, trace ids, and artifact paths.
Keep snippets short and remove secrets.>
```

