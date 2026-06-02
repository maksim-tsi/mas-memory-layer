# YAAM Consumer Readiness Results Register

**Date created:** 2026-05-28  
**Status:** Living register  
**Scope:** First-wave YAAM readiness reports from downstream consumer systems  
**Assignment:** `docs/integrations/consumer-readiness-2026-05-28/consumer-readiness-test-assignment.md`

> Superseded for active per-project testing by
> `docs/integrations/consumer-readiness-2026-05-30/consumer-readiness-results-register.md`.
> Keep this register for the earlier 2026-05-28 shared `test` namespace planning record.

## 1. Purpose

This register is the triage surface for consumer readiness reports. It converts external findings
into ranked, trackable work items while preserving evidence from each consumer system. The register
should be updated after every received report and after every fix verification pass.

## 2. Run Register

| Run ID | Date | Consumer | Consumer host | YAAM endpoint | Report path | Overall verdict | Triage status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CRUN-001 | TBD | TBD | TBD | `http://192.168.107.187:8002` | TBD | TBD | new | Placeholder for first received report. |

Verdict values:

- `pass`: consumer can integrate without material findings.
- `pass-with-findings`: consumer can integrate, but there are ranked gaps to address.
- `blocked`: consumer cannot complete readiness because a provider-side or environment blocker exists.
- `fail`: tested behavior is incompatible with required consumer workflow.

Triage status values:

- `new`
- `triaged`
- `accepted`
- `deferred`
- `in-progress`
- `fixed`
- `verified`
- `wont-fix`

## 3. Findings Backlog

| Finding ID | Source run | Consumer | Priority | Category | Title | Reproduction | Evidence | Status | Owner | Linked issue/task | Fix verification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CF-001 | TBD | TBD | TBD | TBD | Placeholder | TBD | TBD | new | TBD | TBD | TBD |

Priority values:

- `P0`: blocks any meaningful consumer integration.
- `P1`: breaks a required workflow or risks data/provenance corruption.
- `P2`: important gap with an acceptable workaround.
- `P3`: documentation, ergonomics, observability, or polish issue that does not block usage.

Category values:

- `contract`
- `deployment`
- `documentation`
- `MCP`
- `observability`
- `performance`
- `security`
- `data-correctness`
- `UX`

Status values:

- `new`: received but not reviewed.
- `triaged`: reviewed and classified.
- `accepted`: accepted for implementation or documentation work.
- `deferred`: valid, but not planned for the next work batch.
- `in-progress`: assigned and being addressed.
- `fixed`: implementation or documentation change has landed.
- `verified`: the reporting consumer or maintainer has verified the fix.
- `wont-fix`: deliberately rejected with rationale.

## 4. Ranking Policy

Use the highest applicable priority. Do not downgrade an issue only because it affects one consumer;
rank by integration impact and evidence quality.

| Priority | Criteria | Typical action |
| --- | --- | --- |
| `P0` | No consumer can perform meaningful integration, endpoint unreachable, contract absent, or severe security exposure. | Stop and fix before broad testing continues. |
| `P1` | Required workflow fails, session isolation fails, data is corrupted, provenance is missing where required, or retry semantics are unsafe. | Take into the next implementation batch. |
| `P2` | Capability works with workaround, documentation mismatch causes avoidable friction, or observability is insufficient for diagnosis. | Rank against other accepted work. |
| `P3` | Non-blocking naming, formatting, report quality, minor docs, or convenience issue. | Batch with related cleanup. |

## 5. Duplicate Handling

Merge duplicate findings by behavior, not by wording. Keep the earliest finding ID as canonical and
record all affected consumers in the evidence field.

Example duplicate note:

```text
Duplicate evidence merged from CRUN-002 and CRUN-004. Both consumers observed HTTP 502 from
L3 assimilate when the provider timed out after approximately 45 seconds.
```

If two reports describe similar symptoms with different root causes, keep separate findings and
cross-reference them.

## 6. Fix Verification Policy

Every accepted finding must define verification before it is marked `fixed`. Verification should be
as close as possible to the original consumer path.

Acceptable verification evidence:

- a repeated consumer report showing the issue resolved;
- a maintainer-run smoke check against `http://192.168.107.187:8002`;
- a targeted contract or integration test result;
- a documentation diff plus consumer acknowledgement for docs-only findings;
- an MCP stdio or Streamable HTTP contract test result.

For REST v2 findings, record the endpoint, request shape, status code, and sanitized response. For
observability findings, record the trace id or Phoenix evidence path. For security findings, record
the redaction or access-control evidence without exposing secrets.

## 7. Initial Known Provider-Side Items

These items are known before the first consumer reports and should be reconciled with incoming
evidence.

| Finding ID | Priority | Category | Title | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| CF-KNOWN-001 | P1 | MCP | MCP Streamable HTTP implementation and deployment path are available. | fixed | MCP v1 Streamable HTTP exists and was previously validated; keep live read contract in the readiness gate for every deployment refresh. |
| CF-KNOWN-002 | P2 | documentation | Older RFC examples mention `/v2/semantic/*`, while active implementation uses `/v2/memory/*`. | accepted | Assignment states `/v2/memory/*` as active contract; docs alignment may still be needed later. |
| CF-KNOWN-003 | P0 | deployment | Shared `mas-agent` and `yaam-mcp` interface services must be running and freshly validated after project namespace changes. | accepted | Consumer handoff requires `GET /health`, MCP HTTP live read contract, REST L2/L3/L4 smoke, and safe-mode MCP write denial against the post-namespace runtime. |
| CF-KNOWN-004 | P1 | data-correctness | Consumer readiness runtime uses one project namespace per YAAM instance. | accepted | First-wave shared runtime must use `YAAM_PROJECT_ID=test`, L3 `yaam-test-episodes`, and L4 `yaam-test`; do not write readiness data into legacy `episodes_qwen_v2` or `knowledge_base_v2` by default. |

## 8. Report Intake Checklist

For each received report:

- Assign a `CRUN-*` run ID.
- Copy or link the report under `docs/integrations/consumer-readiness-2026-05-28/reports/`.
- Confirm the report contains no secrets.
- Add each actionable issue to the findings backlog.
- Merge duplicate issues where appropriate.
- Rank priority and category.
- Identify owner and next action for `P0` and `P1` issues.
- Record any unresolved question in the finding notes rather than losing it in chat history.
