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
| CRUN-20260530-002 | 2026-05-30 | `scm-skill-factory` | `scm-skill-factory` | MacBook/local network | `http://192.168.107.187:8002` | `http://192.168.107.187:8003/mcp` | `reports/2026-05-30-scm-skill-factory-readiness-report.md` | `pass-with-findings` | `triaged` | Full synthetic readiness passed; report-only evidence copied. Findings are expected Skill Factory domain-view gaps, not runtime blockers. |

### CRUN-20260530-001 Identifiers

- Session: `agentic-scm-tra26-readiness-20260530T153445Z`
- Isolation session: `agentic-scm-tra26-readiness-20260530T153445Z-isolation`
- Task: `agentic-scm-tra26-readiness-20260530T153445Z-task`
- Run: `agentic-scm-tra26-readiness-20260530T153445Z-run`
- Traceparent: `00-abcdefabcdefabcdefabcdefabcdefab-fedcbafedcbafedc-01`
- Finished at: `2026-05-30T15:35:58.732795+00:00`

### CRUN-20260530-002 Identifiers

- Run timestamp: `2026-05-30T17:54:35Z`
- Consumer branch: `dev-eval`
- Consumer commit: `fd93046` (`chore: prepare YAAM readiness baseline`)
- Consumer runtime: MacBook / macOS, project venv Python 3.13
- Phoenix project name reported by consumer: `scm-skill-factory`
- Full write-enabled command: `./.venv/bin/python scripts/verify_yaam.py --include-writes`
- Completion: `YAAM readiness verification completed in 10.89s`

## 3. Consumer Coverage Evaluation

### CRUN-20260530-001: `agentic-scm-tra26`

#### Verdict

`agentic-scm-tra26` passed the full synthetic readiness run. This is not merely a formal smoke test:
it exercised persisted writes, scoped reads, namespace isolation, L3 retrieval after assimilation,
L4 finalization, MCP read surfaces, evidence table generation, and default denial for MCP write
tools.

#### Business Value Demonstrated

The run demonstrates that TRA can use YAAM to:

- store deterministic task/tool facts in L2 and retrieve them under the same logical session;
- keep isolation from unrelated sessions inside the `agentic-scm-tra26` namespace;
- assimilate an L3 episode and retrieve it through the documented REST and MCP read paths;
- persist a final artifact through L4 finalization;
- inspect memory context and evidence through MCP without direct storage access;
- rely on guarded MCP mutation defaults unless an explicit write window is opened.

#### Covered Well

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

#### Partially Covered

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

### CRUN-20260530-002: `scm-skill-factory`

#### Verdict

`scm-skill-factory` passed the full synthetic readiness run. The result is strong enough to proceed
with the first project-specific YAAM integration test, but the right register verdict is
`pass-with-findings` because the consumer identified expected domain-specific gaps for Skill Factory
views and prompts.

This is not merely a formal connectivity check. The run exercised REST health/context, MCP
discovery/read paths, Phoenix API reachability, OpenRouter/Qwen runtime configuration, L2/L3/L4
synthetic writes, curation writes, evidence, CIAR, and default write-safety behavior.

#### Business Value Demonstrated

The run demonstrates that Skill Factory can use YAAM to:

- assemble pre-generation memory context with leakage-guard metadata;
- store and retrieve scoped L2 facts for skill-generation or repair sessions;
- assimilate and query L3 repair episodes;
- finalize durable L4 artifacts;
- write and list maintainer curation decisions;
- inspect CIAR and evidence through MCP without direct storage coupling;
- run against the isolated `scm-skill-factory` namespace.

#### Covered Well

| Area | Evidence |
| --- | --- |
| Runtime configuration | Consumer reported `OPENROUTER_MODEL=tencent/hy3-preview`, Qwen embeddings, and 4096 dimensions. |
| REST health/context | `/health` passed and context returned `leakage_guard_passed=True`. |
| MCP discovery/read | 16 tools, 5 resources, 5 templates, and 4 prompts were discovered; health, evidence, and CIAR reads passed. |
| L2 store/retrieve/isolation | Synthetic L2 write, same-scope retrieval, and isolation checks passed. |
| L3 assimilation/query | Synthetic repair episode assimilation and query checks passed. |
| L4 finalize | Synthetic artifact finalization returned a knowledge id. |
| Curation | Synthetic maintainer curation decision write and list checks passed. |
| Phoenix reachability | Phoenix API was reachable and listed 65 projects. |

#### Partially Covered

| Area | Gap |
| --- | --- |
| Skill Factory domain views | Generic YAAM primitives passed, but dedicated views by skill, CTT, QA status, repair history, and active-tool status are still expected follow-ups. |
| MCP domain resources | `yaam://skills/{skill_name}` and `yaam://ctts/{ctt_id}` are missing or partial. |
| Domain prompt support | `yaam.prompt.repair_pattern_summary` is missing or partial. |
| Phoenix trace correlation | Phoenix API reachability was proven, but no specific span export or trace correlation evidence was included. |

#### Not Covered

- A normal end-to-end Skill Factory production workflow using YAAM inside skill creation, QA, repair,
  and replay loops.
- Multi-run learning across separate Skill Factory sessions and artifacts.
- Direct validation that the expected Skill Factory domain views exist as first-class MCP resources.
- Provider/DBMS degradation and retry behavior.

## 4. Requirement Coverage Snapshot

| Requirement | Coverage from consumer runs | Status |
| --- | --- | --- |
| `YAAM-REQ-0001` distinct REST/MCP surfaces | Both TRA and Skill Factory exercised REST and MCP independently. | covered |
| `YAAM-REQ-0002` MCP memory query | TRA exercised `yaam.memory.query`; Skill Factory exercised MCP read tools and evidence/CIAR. | covered |
| `YAAM-REQ-0003` MCP context assembly | TRA used `yaam.memory.get_context`; Skill Factory REST context returned leakage guard metadata. | covered |
| `YAAM-REQ-0005` scoped L2 fact store/retrieve | Both runs passed L2 write/read/isolation. | covered |
| `YAAM-REQ-0006` L3 episode assimilation | Both runs passed L3 assimilation. | covered |
| `YAAM-REQ-0007` L3 semantic query | Both runs passed L3 query after synthetic assimilation. | covered |
| `YAAM-REQ-0008` L4 final artifact storage | Both runs passed L4 finalize; direct L4 search/readback still needs stronger evidence. | partial |
| `YAAM-REQ-0009` provenance on reads/writes | Responses and reports include scope/provenance evidence for synthetic paths. | covered |
| `YAAM-REQ-0011` read-only MCP defaults | Read paths succeeded; TRA explicitly validated default write denial. | covered |
| `YAAM-REQ-0012` allowlisted MCP mutation | Default write safety is validated; mutating MCP allowlist window remains untested by consumers. | partial |
| `YAAM-REQ-0014` trace context/Phoenix audit | TRA included `traceparent`; Skill Factory proved Phoenix API reachability. Span export/correlation evidence is still missing. | partial |
| `YAAM-REQ-0015` health/config inspection | REST health and MCP health/config paths succeeded. | covered |
| `YAAM-REQ-0016` Evidence Table generation | Both reports include evidence/CIAR read success. | covered |
| `YAAM-REQ-0022` Skill Factory generation/QA/curation views | Skill Factory report identified this as a gap; optional MCP domain pack now addresses it for the next run. | fixed-pending-consumer-verification |
| `YAAM-REQ-0023` Skill Factory skill/CTT/run resources | Skill Factory report identified missing resources; optional MCP domain pack now adds them. | fixed-pending-consumer-verification |
| `YAAM-REQ-0032` domain-specific prompts | Skill Factory report identified missing repair prompt; optional MCP domain pack now adds `yaam.prompt.repair_pattern_summary`. | fixed-pending-consumer-verification |
| `YAAM-REQ-0034` performance budgets | TRA exposed L3 latency to monitor; Skill Factory completed full verifier in 10.89s. | partial |
| `YAAM-REQ-0038` trace/artifact correlation metadata | Session/task/project metadata is present; cross-system trace evidence remains partial. | partial |

## 5. Findings Backlog

| Finding ID | Source run | Consumer | Priority | Category | Title | Reproduction | Evidence | Status | Owner | Linked issue/task | Fix verification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CF-AGTRA26-001 | CRUN-20260530-001 | `agentic-scm-tra26` | `P2` | `performance` | L3 assimilation latency needs monitoring | Run full synthetic readiness and inspect `REST L3 assimilate synthetic episode`. | Evidence JSON reports about `61668.15 ms`. | `triaged` | TBD | TBD | Next readiness run records L3 latency within documented TRA budget or accepted timeout guidance is added. |
| CF-AGTRA26-002 | CRUN-20260530-001 | `agentic-scm-tra26` | `P2` | `contract` | Add direct L4 search/readback to readiness script | Finalize an L4 artifact, then query/read L4 explicitly. | Finalize returned `kd-6c832092`, but public query first result was L3. | `triaged` | TBD | TBD | Readiness evidence includes direct L4 retrieval of the finalized artifact. |
| CF-AGTRA26-003 | CRUN-20260530-001 | `agentic-scm-tra26` | `P3` | `documentation` | Require explicit `YAAM-REQ-*` coverage table in consumer reports | Compare submitted report with `readiness-report-template.md`. | Report has checks and operations, but no requirement coverage table. | `triaged` | TBD | TBD | Next report includes requirement coverage rows or a generated appendix. |
| CF-AGTRA26-004 | CRUN-20260530-001 | `agentic-scm-tra26` | `P3` | `observability` | Include Phoenix trace evidence in future reports | Run readiness with trace export or Phoenix evidence capture. | Report includes `traceparent`, but no Phoenix span evidence. | `triaged` | TBD | TBD | Report links sanitized Phoenix span export or trace screenshot/summary. |
| CF-SKILL-001 | CRUN-20260530-002 | `scm-skill-factory` | `P2` | `contract` | Add Skill Factory first-class run views | Run Skill Factory readiness and inspect expected gaps. | Report lists missing dedicated run views keyed by skill, CTT, QA status, and active tool status. | `fixed` | YAAM | Skill Factory MCP domain pack | Local MCP/domain-view tests pass; next Skill Factory readiness run verifies resources with canonical metadata. |
| CF-SKILL-002 | CRUN-20260530-002 | `scm-skill-factory` | `P2` | `MCP` | Add `yaam://skills/{skill_name}` and `yaam://ctts/{ctt_id}` resources | Run Skill Factory MCP resource checks. | Report classifies both resources as missing or partially implemented. | `fixed` | YAAM | Skill Factory MCP domain pack | MCP discovery includes resources when pack is enabled; next consumer run verifies payload usefulness. |
| CF-SKILL-003 | CRUN-20260530-002 | `scm-skill-factory` | `P2` | `MCP` | Add repair pattern summary prompt | Run Skill Factory prompt discovery/checks. | Report classifies `yaam.prompt.repair_pattern_summary` as missing or partially implemented. | `fixed` | YAAM | Skill Factory MCP domain pack | Prompt discovery includes `yaam.prompt.repair_pattern_summary` and local render test passes. |
| CF-SKILL-004 | CRUN-20260530-002 | `scm-skill-factory` | `P3` | `observability` | Include concrete Phoenix span evidence in Skill Factory reports | Run readiness with Phoenix export or trace summary. | Report proves Phoenix API reachability but not span correlation for the run. | `triaged` | TBD | TBD | Report links sanitized span export or trace summary for the readiness run. |

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
| 2 | `scm-skill-factory` | `scm-skill-factory` | completed synthetic readiness | PASS with expected Skill Factory domain-view follow-ups. |
| 3 | `scm-cognitive-sandwich` | `scm-cognitive-sandwich` | pending | Run after YAAM is switched to this namespace and smoke-tested. |
