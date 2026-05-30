# YAAM Consumer Readiness Results Register

**Date created:** 2026-05-30  
**Status:** Living register  
**Scope:** Per-project YAAM consumer readiness reports for the 2026-05-30 test wave  
**Sequence:** `docs/integrations/consumer-readiness-2026-05-30/consumer-testing-sequence.md`

## 1. Purpose

This register records received consumer readiness reports, preserves sanitized evidence, and turns
coverage gaps into ranked follow-up work. The 2026-05-30 wave runs one `YAAM_PROJECT_ID` at a time
so that each consumer writes to its own YAAM namespace.

Verdict values:

- `pass`: consumer can integrate without material findings.
- `pass-with-findings`: consumer can integrate, but there are ranked gaps to address.
- `blocked`: consumer cannot complete readiness because a provider-side or environment blocker exists.
- `fail`: tested behavior is incompatible with required consumer workflow.

Triage status values: `new`, `triaged`, `accepted`, `deferred`, `in-progress`, `fixed`, `verified`,
`wont-fix`.

## 2. Run Register

| Run ID | Date | Consumer | Project namespace | Consumer host | YAAM endpoint | MCP endpoint | Report path | Overall verdict | Triage status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CRUN-20260530-001 | 2026-05-30 | `agentic-scm-tra26` | `agentic-scm-tra26` | MacBook/local network | `http://192.168.107.187:8002` | `http://192.168.107.187:8003/mcp` | `reports/20260530T153445Z-agentic-scm-tra26-full-synthetic-report.md` | `pass` | `triaged` | Full synthetic readiness passed; evidence JSON copied as `reports/20260530T153445Z-agentic-scm-tra26-full-synthetic-results.json`. |

### CRUN-20260530-001 Identifiers

- Session: `agentic-scm-tra26-readiness-20260530T153445Z`
- Isolation session: `agentic-scm-tra26-readiness-20260530T153445Z-isolation`
- Task: `agentic-scm-tra26-readiness-20260530T153445Z-task`
- Run: `agentic-scm-tra26-readiness-20260530T153445Z-run`
- Traceparent: `00-abcdefabcdefabcdefabcdefabcdefab-fedcbafedcbafedc-01`
- Finished at: `2026-05-30T15:35:58.732795+00:00`

## 3. CRUN-20260530-001 Coverage Evaluation

### Verdict

`agentic-scm-tra26` passed the full synthetic readiness run. This is not merely a formal smoke test:
it exercised persisted writes, scoped reads, namespace isolation, L3 retrieval after assimilation,
L4 finalization, MCP read surfaces, evidence table generation, and default denial for MCP write
tools.

### Business Value Demonstrated

The run demonstrates that TRA can use YAAM to:

- store deterministic task/tool facts in L2 and retrieve them under the same logical session;
- keep isolation from unrelated sessions inside the `agentic-scm-tra26` namespace;
- assimilate an L3 episode and retrieve it through the documented REST and MCP read paths;
- persist a final artifact through L4 finalization;
- inspect memory context and evidence through MCP without direct storage access;
- rely on guarded MCP mutation defaults unless an explicit write window is opened.

### Covered Well

| Area | Evidence |
| --- | --- |
| REST health | `REST health` returned HTTP 200. |
| L2 store/retrieve | L2 store returned a fact id; same-session retrieve returned the synthetic marker. |
| L2 isolation | Isolation session returned no marker. |
| L3 assimilation/retrieval | Before assimilation query returned no result; after assimilation query returned `ep-b2e83405`. |
| L4 finalize | L4 finalize returned `kd-6c832092`. |
| Public memory query leakage guard | Public query returned a sanitized L3 result and leakage guard passed. |
| MCP discovery/read | Tools, resources, prompts, health, context, memory query, and evidence table calls succeeded. |
| MCP guarded mutation | `yaam.l2.store_fact` returned structured `permission.writes_disabled` as expected. |
| Negative validation | Missing L2 content was rejected with HTTP 400. |

### Partially Covered

| Area | Gap |
| --- | --- |
| L4 business value | Finalize succeeded, but direct L4 search/readback was not proven; post-finalize public query returned L3 as the first result. |
| Observability | `traceparent` was present, but the report does not include Phoenix span export or UI evidence. |
| Requirements traceability | Checks are strong, but the submitted report does not include an explicit `YAAM-REQ-*` coverage table. |
| MCP writes | Default write denial was validated; mutating MCP tools were not exercised in an allowlisted write window. |

### Not Covered

- A real `agentic-scm-tra26` business workflow using YAAM in the normal AgenticGraph execution path.
- Multi-run memory reuse across separate TRA sessions.
- Provider or DBMS degradation, retry, and failover behavior.
- Phoenix trace correlation evidence across TRA and YAAM spans.

## 4. Requirement Coverage Snapshot

| Requirement | Coverage from CRUN-20260530-001 | Status |
| --- | --- | --- |
| `YAAM-REQ-0001` distinct REST/MCP surfaces | REST and MCP were both exercised independently. | covered |
| `YAAM-REQ-0002` MCP memory query | `yaam.memory.query` returned an L3 result. | covered |
| `YAAM-REQ-0003` MCP context assembly | `yaam.memory.get_context` returned scoped context. | covered |
| `YAAM-REQ-0005` scoped L2 fact store/retrieve | L2 write/read and isolation passed. | covered |
| `YAAM-REQ-0006` L3 episode assimilation | Assimilation returned `ep-b2e83405`. | covered |
| `YAAM-REQ-0007` L3 semantic query | L3 retrieval returned the assimilated episode. | covered |
| `YAAM-REQ-0008` L4 final artifact storage | Finalize returned `kd-6c832092`; direct readback not tested. | partial |
| `YAAM-REQ-0009` provenance on reads/writes | Responses contained source/provenance fields. | covered |
| `YAAM-REQ-0011` read-only MCP defaults | Read tools succeeded without writes. | covered |
| `YAAM-REQ-0012` allowlisted MCP mutation | Default write denial was proven; allowlisted write window not tested. | partial |
| `YAAM-REQ-0014` trace context/Phoenix audit | `traceparent` propagated in requests; Phoenix evidence not included. | partial |
| `YAAM-REQ-0015` health/config inspection | REST health and MCP health succeeded. | covered |
| `YAAM-REQ-0016` Evidence Table generation | `yaam.evidence.table` succeeded. | covered |
| `YAAM-REQ-0034` performance budgets | Most calls were fast; L3 assimilate took about 61.7s and needs tracking. | partial |
| `YAAM-REQ-0038` trace/artifact correlation metadata | Trace/session/task metadata was present; cross-system trace evidence not included. | partial |

## 5. Findings Backlog

| Finding ID | Source run | Consumer | Priority | Category | Title | Reproduction | Evidence | Status | Owner | Linked issue/task | Fix verification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CF-AGTRA26-001 | CRUN-20260530-001 | `agentic-scm-tra26` | `P2` | `performance` | L3 assimilation latency needs monitoring | Run full synthetic readiness and inspect `REST L3 assimilate synthetic episode`. | Evidence JSON reports about `61668.15 ms`. | `triaged` | TBD | TBD | Next readiness run records L3 latency within documented TRA budget or accepted timeout guidance is added. |
| CF-AGTRA26-002 | CRUN-20260530-001 | `agentic-scm-tra26` | `P2` | `contract` | Add direct L4 search/readback to readiness script | Finalize an L4 artifact, then query/read L4 explicitly. | Finalize returned `kd-6c832092`, but public query first result was L3. | `triaged` | TBD | TBD | Readiness evidence includes direct L4 retrieval of the finalized artifact. |
| CF-AGTRA26-003 | CRUN-20260530-001 | `agentic-scm-tra26` | `P3` | `documentation` | Require explicit `YAAM-REQ-*` coverage table in consumer reports | Compare submitted report with `readiness-report-template.md`. | Report has checks and operations, but no requirement coverage table. | `triaged` | TBD | TBD | Next report includes requirement coverage rows or a generated appendix. |
| CF-AGTRA26-004 | CRUN-20260530-001 | `agentic-scm-tra26` | `P3` | `observability` | Include Phoenix trace evidence in future reports | Run readiness with trace export or Phoenix evidence capture. | Report includes `traceparent`, but no Phoenix span evidence. | `triaged` | TBD | TBD | Report links sanitized Phoenix span export or trace screenshot/summary. |

Priority values:

- `P0`: blocks any meaningful consumer integration.
- `P1`: breaks a required workflow or risks data/provenance corruption.
- `P2`: important gap with an acceptable workaround.
- `P3`: documentation, ergonomics, observability, or polish issue that does not block usage.

Category values: `contract`, `deployment`, `documentation`, `MCP`, `observability`, `performance`,
`security`, `data-correctness`, `UX`.

## 6. Fix Verification Policy

Every accepted finding must define verification before it is marked `fixed`. Verification should be
as close as possible to the original consumer path:

- repeated consumer report evidence;
- maintainer-run smoke check against `http://192.168.107.187:8002`;
- MCP Streamable HTTP contract evidence against `http://192.168.107.187:8003/mcp`;
- sanitized Phoenix trace export for observability findings;
- documentation diff plus consumer acknowledgement for report-quality findings.

## 7. Next Consumer Queue

| Order | Consumer | Planned `YAAM_PROJECT_ID` | Status | Notes |
| --- | --- | --- | --- | --- |
| 1 | `agentic-scm-tra26` | `agentic-scm-tra26` | completed synthetic readiness | PASS with non-blocking follow-ups. |
| 2 | `scm-skill-factory` | `scm-skill-factory` | pending | Run after YAAM is switched to this namespace and smoke-tested. |
| 3 | `scm-cognitive-sandwich` | `scm-cognitive-sandwich` | pending | Run after YAAM is switched to this namespace and smoke-tested. |
