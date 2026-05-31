# YAAM Requirements Registry

**Status:** Initial registry  
**Date:** 2026-05-24  
**Registry format:** Markdown canonical view plus CSV mirror  
**Priority model:** Customer consensus, then MVP need, security/observability risk, and system impact  

## Summary

This registry normalizes the first external customer requirement submissions for
YAAM interface evolution and MCP planning. It captures shared requirements,
customer-specific extensions, and discussion items that should be reviewed
before implementation planning.

Source customer systems:

- TRA
- iAIMS
- Skill Factory
- SCM Cognitive Sandwich
- Maritime Port Sandbox
- SCM-Cert-Bench

## Registry

| ID | Title | Source customers | Tier | Interface | Operation | MVP | Priority | Status | Implementation area |
|---|---|---|---|---|---|---|---|---|---|
| YAAM-REQ-0001 | Keep API Wall, REST v2, and MCP as distinct interfaces | TRA, iAIMS, Skill Factory, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Service | Multiple | Interface | Yes | P0 | Accepted | Public interface architecture |
| YAAM-REQ-0002 | Expose read-heavy MCP memory query | TRA, iAIMS, Skill Factory, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Unified | MCP | Read tool | Yes | P0 | Accepted | MCP service layer |
| YAAM-REQ-0003 | Expose MCP context assembly | TRA, iAIMS, Skill Factory, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Unified | MCP | Read tool/resource | Yes | P0 | Accepted | Unified retrieval/context service |
| YAAM-REQ-0004 | Preserve REST v2 for backend and batch integrations | TRA, iAIMS, Skill Factory, Maritime Port Sandbox, SCM-Cert-Bench | Service | REST v2 | Read/write API | Yes | P0 | Accepted | REST v2 gateway |
| YAAM-REQ-0005 | Provide scoped L2 fact store and retrieve | TRA, iAIMS, Skill Factory, SCM-Cert-Bench | Raw | REST v2, MCP | Read/write | Yes | P0 | Accepted | L2 working memory service |
| YAAM-REQ-0006 | Provide L3 episode assimilation/store | TRA, iAIMS, Skill Factory, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Raw | REST v2, MCP | Write/lifecycle | Yes | P0 | Accepted | L3 episodic memory service |
| YAAM-REQ-0007 | Provide L3 semantic episode query | TRA, iAIMS, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Unified | REST v2, MCP | Read | Yes | P0 | Accepted | L3 retrieval service |
| YAAM-REQ-0008 | Provide L4 final artifact/document storage | TRA, iAIMS, Skill Factory, SCM Cognitive Sandwich | Raw | REST v2, MCP | Write/lifecycle | Yes | P0 | Accepted | L4 semantic memory service |
| YAAM-REQ-0009 | Return provenance on all reads and writes | TRA, iAIMS, Skill Factory, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Service | Multiple | Provenance | Yes | P0 | Accepted | Shared response model |
| YAAM-REQ-0010 | Enforce session/task/tenant/run scoping | TRA, iAIMS, Skill Factory, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Service | Multiple | Security | Yes | P0 | Accepted | Authorization/scope policy |
| YAAM-REQ-0011 | Keep default MCP resources read-only | iAIMS, Skill Factory, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Service | MCP | Resource/security | Yes | P0 | Accepted | MCP authorization policy |
| YAAM-REQ-0012 | Allowlist mutating and lifecycle MCP tools | TRA, iAIMS, Skill Factory, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Service | MCP | Security | Yes | P0 | Accepted | MCP authorization policy |
| YAAM-REQ-0013 | Never expose secrets, raw env, or sensitive traces through resources | iAIMS, Skill Factory, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Service | MCP | Security | Yes | P0 | Accepted | Redaction policy |
| YAAM-REQ-0014 | Propagate trace context and expose Phoenix-auditable operations | TRA, iAIMS, Skill Factory, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Service | Multiple | Observability | Yes | P0 | Accepted | Observability/tracing |
| YAAM-REQ-0015 | Provide health and configuration inspection | iAIMS, Skill Factory, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Service | REST v2, MCP | Read/resource | Yes | P0 | Accepted | Health/config service |
| YAAM-REQ-0016 | Provide Evidence Table generation | iAIMS, Skill Factory, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Agentic | MCP, REST v2 | Read/agentic | Mixed | P1 | Accepted | Evidence service |
| YAAM-REQ-0017 | Provide CIAR explanation with components and policy metadata | TRA, iAIMS, Skill Factory, Maritime Port Sandbox, SCM-Cert-Bench | Agentic | MCP | Read | Mixed | P1 | Accepted | CIAR policy service |
| YAAM-REQ-0018 | Return partial results with warnings for degraded agentic services | iAIMS, Skill Factory, Maritime Port Sandbox, SCM-Cert-Bench | Unified | MCP, REST v2 | Reliability | Yes | P1 | Accepted | Error handling |
| YAAM-REQ-0019 | Support artifact draft/revision/feedback/commit lineage | SCM Cognitive Sandwich | Artifact | MCP | Write/lifecycle/read | Yes | P1 | Needs discussion | Artifact service |
| YAAM-REQ-0020 | Provide artifact lineage resources | SCM Cognitive Sandwich | Artifact | MCP | Resource/read | Yes | P1 | Accepted | Cognitive Sandwich MCP domain pack |
| YAAM-REQ-0021 | Store deterministic feedback and solver/sandbox evidence | SCM Cognitive Sandwich, Maritime Port Sandbox, Skill Factory, SCM-Cert-Bench | Artifact/Raw | MCP, REST v2 | Write | Yes | P1 | Accepted | Evidence/artifact ingestion |
| YAAM-REQ-0022 | Store and query Skill Factory generation, QA, and curation memory | Skill Factory | Raw/Unified | REST v2, MCP | Read/write | Yes | P2 | Accepted | Skill Factory MCP domain pack |
| YAAM-REQ-0023 | Provide Skill Factory resources for skills, CTTs, and runs | Skill Factory | Raw/Unified | MCP | Resource/read | Yes | P2 | Accepted | Skill Factory MCP domain pack |
| YAAM-REQ-0024 | Store and query maritime port/run/scenario evidence | Maritime Port Sandbox | Raw/Unified | REST v2, MCP | Read/write | Yes | P2 | Needs discussion | Domain-specific memory views |
| YAAM-REQ-0025 | Provide maritime resources for runs, scenarios, ports, and facts | Maritime Port Sandbox | Raw/Unified | MCP | Resource/read | Yes | P2 | Needs discussion | MCP resources/customer views |
| YAAM-REQ-0026 | Keep LangChain tools out of customer-facing YAAM contracts | TRA, iAIMS, Skill Factory, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Service | LangChain | Interface constraint | Yes | P1 | Accepted | Tool/service boundary |
| YAAM-REQ-0027 | Avoid direct customer library calls into YAAM internals | TRA, iAIMS, Skill Factory, Maritime Port Sandbox, SCM-Cert-Bench | Service | Direct library | Interface constraint | Yes | P1 | Accepted | Public interface boundary |
| YAAM-REQ-0028 | Preserve transitional facade only until MCP parity for SCM Cognitive Sandwich | SCM Cognitive Sandwich | Service | Direct library, MCP | Compatibility | Yes | P2 | Needs discussion | Migration planning |
| YAAM-REQ-0029 | Provide contradiction/supersession and safe-refusal review as opt-in | Skill Factory, iAIMS, TRA, SCM-Cert-Bench | Agentic | MCP | Lifecycle/read | Mixed | P1 | Accepted | Contradiction policy service |
| YAAM-REQ-0030 | Provide autonomous consolidation/distillation as opt-in only | Skill Factory, SCM Cognitive Sandwich | Agentic | MCP | Lifecycle | No | P3 | Deferred | Lifecycle service |
| YAAM-REQ-0031 | Provide MCP prompt templates for evidence, memory inspection, and CIAR explanation | iAIMS, Skill Factory, SCM Cognitive Sandwich, Maritime Port Sandbox, SCM-Cert-Bench | Agentic | MCP | Prompt | Mixed | P1 | Accepted | MCP prompts |
| YAAM-REQ-0032 | Support domain-specific prompt templates | Skill Factory, SCM Cognitive Sandwich, SCM-Cert-Bench | Agentic | MCP | Prompt | Mixed | P2 | Accepted | MCP domain packs |
| YAAM-REQ-0033 | Preserve fail-fast behavior for write/assimilation failures | TRA, iAIMS, Skill Factory, Maritime Port Sandbox, SCM-Cert-Bench | Service | REST v2, MCP | Reliability | Yes | P1 | Accepted | Error handling |
| YAAM-REQ-0034 | Track performance budgets for query, context, evidence, and CIAR operations | iAIMS, Skill Factory, Maritime Port Sandbox, SCM-Cert-Bench | Service | Multiple | Performance | Yes | P1 | Accepted | SLO/observability |
| YAAM-REQ-0035 | Require implementation plans to reference requirement IDs | Internal governance | Service | Documentation | Governance | Yes | P0 | Accepted | Documentation governance |
| YAAM-REQ-0036 | Enforce benchmark answer-leakage and contamination guards | SCM-Cert-Bench | Service | MCP, REST v2 | Security/read policy | Yes | P0 | Accepted | Authorization/scope policy |
| YAAM-REQ-0037 | Store maintainer-only Gold task curation decisions | SCM-Cert-Bench | Raw/Unified | REST v2, MCP | Write/read | Yes | P1 | Accepted | Curation memory service |
| YAAM-REQ-0038 | Store and retrieve trace and artifact correlation metadata | SCM-Cert-Bench | Service | REST v2, MCP | Metadata read/write | Yes | P1 | Accepted | Observability/tracing |
| YAAM-REQ-0039 | Provide SCM-Cert-Bench task, evidence, curation, and episode resources | SCM-Cert-Bench | Raw/Unified | MCP | Resource/read | Yes | P2 | Needs discussion | MCP resources/customer views |

## Requirement Details

### YAAM-REQ-0001: Keep API Wall, REST v2, and MCP as distinct interfaces

Customers consistently reject using the API Wall as the primary YAAM memory
interface. REST v2 remains important for backend integration and batch jobs,
while MCP is the planned agent-host interface.

Acceptance evidence: interface documentation continues to distinguish API Wall,
REST v2, and MCP; MCP implementation does not replace existing REST v2 routes.

### YAAM-REQ-0002: Expose read-heavy MCP memory query

All customer systems require a discoverable read query surface for memory
retrieval. The common minimum is a scoped query with ranking metadata,
provenance, tier/source ids, and partial-result indicators.

Acceptance evidence: MCP clients can discover and call a memory query tool with
structured input and output schema.

### YAAM-REQ-0003: Expose MCP context assembly

All customers need a context-building operation that composes relevant L2/L3/L4
evidence into a bounded context bundle for agents, auditors, or reports.

Acceptance evidence: context responses include source ids, tier metadata,
provenance, warnings, and size/token metadata where available.

### YAAM-REQ-0004: Preserve REST v2 for backend and batch integrations

TRA, iAIMS, Skill Factory, Maritime Port Sandbox, and SCM-Cert-Bench require
REST v2 for runtime, scripts, ingestion, administrative reads, or test harnesses.

Acceptance evidence: REST v2 remains documented and tested independently of MCP.

### YAAM-REQ-0005: Provide scoped L2 fact store and retrieve

Multiple customers require working-memory facts for deterministic tool outputs,
task facts, skill metadata, benchmark evidence, and final synthesis evidence.

Acceptance evidence: writes return fact ids and provenance; reads enforce scope.

### YAAM-REQ-0006: Provide L3 episode assimilation/store

Customers need L3 persistence for repair loops, generation attempts, simulation
runs, deterministic feedback, and prior episode reuse.

Acceptance evidence: L3 write returns episode id and audit metadata, and the
episode is retrievable by relevant scope fields.

### YAAM-REQ-0007: Provide L3 semantic episode query

TRA, iAIMS, SCM Cognitive Sandwich, Maritime Port Sandbox, and SCM-Cert-Bench
require similar episode retrieval before planning, repair, diagnosis, or audit.

Acceptance evidence: query returns scoped ranked episodes with provenance.

### YAAM-REQ-0008: Provide L4 final artifact/document storage

Customers need verified final artifacts, reports, or knowledge documents stored
as durable L4 knowledge.

Acceptance evidence: finalization returns knowledge id and preserves consensus
or source metadata.

### YAAM-REQ-0009: Return provenance on all reads and writes

Provenance is a shared requirement across all customer systems. Returned data
should identify source tier, source id, timestamps, producing agent/system, and
scope ids where applicable.

Acceptance evidence: public responses include provenance fields for memory ids.

### YAAM-REQ-0010: Enforce session/task/tenant/run scoping

All customer systems rely on isolation boundaries. Scope identifiers vary by
customer, but the shared requirement is explicit and enforceable scoping.

Acceptance evidence: cross-session and cross-tenant reads are blocked unless
explicitly allowed by query/filter semantics.

### YAAM-REQ-0011: Keep default MCP resources read-only

Most customers expect resources to be safe inspection surfaces. Mutations should
be tools, not resources.

Acceptance evidence: MCP resources cannot mutate memory state.

### YAAM-REQ-0012: Allowlist mutating and lifecycle MCP tools

Customers request controlled write/lifecycle access. Mutating tools must not be
broadly model-callable by default.

Acceptance evidence: write/lifecycle tool availability is controlled by
server-side configuration or caller capability.

### YAAM-REQ-0013: Never expose secrets, raw env, or sensitive traces through resources

Customers explicitly prohibit exposing secrets, raw environment values, raw LLM
reasoning traces, database URLs, and unredacted logs through MCP resources.

Acceptance evidence: resource responses are redacted and covered by permission
tests.

### YAAM-REQ-0014: Propagate trace context and expose Phoenix-auditable operations

Customers require traceability for memory reads/writes, evidence aggregation,
CIAR explanation, and agentic review.

Acceptance evidence: calls propagate trace context and emit auditable spans.

### YAAM-REQ-0015: Provide health and configuration inspection

Customers need to distinguish healthy, degraded, unconfigured, and unavailable
tiers before deciding whether to fail fast or continue without memory context.

Acceptance evidence: health/config endpoint or MCP resource reports tier status
without exposing secrets.

### YAAM-REQ-0016: Provide Evidence Table generation

Evidence Table is a shared audit need, especially for final answers, repair
loops, skill debugging, and failed simulations.

Acceptance evidence: Evidence Table responses include claim, source tier/id,
provenance, CIAR/policy metadata where available, visibility, and warnings.

### YAAM-REQ-0017: Provide CIAR explanation with components and policy metadata

Customers need CIAR primarily for audit/debugging, not for core deterministic
runtime decisions.

Acceptance evidence: explanation includes certainty, impact, age decay, recency
boost, final score, policy version, review/suppression status where available.

### YAAM-REQ-0018: Return partial results with warnings for degraded agentic services

For read flows, customers prefer raw/unified results with warnings when
Evidence Table or CIAR explanation is unavailable.

Acceptance evidence: read responses can report `partial=true` or equivalent
warning metadata without mutating state.

### YAAM-REQ-0019: Support artifact draft/revision/feedback/commit lineage

SCM Cognitive Sandwich requires native artifact lineage primitives. This is a
major product extension and should be discussed before implementation. The
Cognitive Sandwich MCP domain pack provides metadata-derived read-only lineage
views, but native transactional lifecycle semantics remain deferred to an
artifact service milestone.

Acceptance evidence: lineage captures artifact, revisions, feedback, commits,
payload hashes, and verification states.

### YAAM-REQ-0020: Provide artifact lineage resources

SCM Cognitive Sandwich requires read-only artifact lineage resources for
inspection and repair context generation. The first supported path is the
optional Cognitive Sandwich MCP domain pack, which reconstructs lineage from
canonical metadata written through generic L2/L3/L4 tools.

Acceptance evidence: resource returns ordered lineage nodes with provenance and
redacted payload behavior.

### YAAM-REQ-0021: Store deterministic feedback and solver/sandbox evidence

SCM Cognitive Sandwich, Maritime Port Sandbox, Skill Factory, and
SCM-Cert-Bench all need to store external deterministic feedback or benchmark
judge evidence.

Acceptance evidence: stored feedback is linked to episode, artifact, run, or
skill scope and is queryable later.

### YAAM-REQ-0022: Store and query Skill Factory generation, QA, and curation memory

Skill Factory requires memory views keyed by CTT, skill name, run id, QA status,
active-tool status, and sandbox outcomes.

Acceptance evidence: Skill Factory acceptance tests can retrieve relevant
generation history, validated skill facts, and QA decisions through the
optional Skill Factory MCP domain pack.

### YAAM-REQ-0023: Provide Skill Factory resources for skills, CTTs, and runs

Skill Factory requests MCP resources such as `yaam://skills/{skill_name}`,
`yaam://ctts/{ctt_id}`, and `yaam://runs/{run_id}/episodes`.

Acceptance evidence: resources expose non-sensitive metadata, enforce scope, and
are enabled only by the optional Skill Factory MCP domain pack.

### YAAM-REQ-0024: Store and query maritime port/run/scenario evidence

Maritime Port Sandbox requires storing port status facts, admin mutations, and
completed simulation runs with payload hashes and audit metadata.

Acceptance evidence: queries by run, scenario, port code, disruption type, and
tenant/task scope return relevant evidence.

### YAAM-REQ-0025: Provide maritime resources for runs, scenarios, ports, and facts

Maritime Port Sandbox requests resources such as `yaam://runs/{run_id}/context`,
`yaam://runs/{run_id}/scenarios/{scenario_id}`, and
`yaam://ports/{port_code}/facts`.

Acceptance evidence: resources enforce scope and do not expose hidden admin
routes to consumer-only agents.

### YAAM-REQ-0026: Keep LangChain tools out of customer-facing YAAM contracts

All customer submissions either reject LangChain tools or treat them as not
required. Shared YAAM services should be below any LangChain or MCP adapter.

Acceptance evidence: customer-facing docs do not require LangChain tool usage.

### YAAM-REQ-0027: Avoid direct customer library calls into YAAM internals

Most customers explicitly reject direct storage or internal library coupling.
SCM Cognitive Sandwich has a temporary facade exception.

Acceptance evidence: customer integrations use REST v2, MCP, or documented
facade transition points.

### YAAM-REQ-0028: Preserve transitional facade only until MCP parity for SCM Cognitive Sandwich

SCM Cognitive Sandwich currently depends on a local facade boundary until MCP
parity exists. The Cognitive Sandwich MCP domain pack provides partial parity
for audit/context/reporting paths, while native mutating artifact lifecycle
tools remain a separate milestone.

Acceptance evidence: migration plan defines facade deprecation or coexistence.

### YAAM-REQ-0029: Provide contradiction/supersession and safe-refusal review as opt-in

Multiple customers request review, and SCM-Cert-Bench needs contradiction-aware
safe-refusal support for adversarial benchmark tasks. Review remains explicit
and should not trigger autonomous mutation by default.

Acceptance evidence: contradiction review returns supporting and conflicting
evidence, an infeasibility or safe-refusal rationale when applicable, and remains
explicitly invoked.

### YAAM-REQ-0030: Provide autonomous consolidation/distillation as opt-in only

Customers treat autonomous lifecycle actions as future or privileged behavior.

Acceptance evidence: lifecycle tools are not enabled by default for customers.

### YAAM-REQ-0031: Provide MCP prompt templates for evidence, memory inspection, and CIAR explanation

Customers request common prompts for evidence tables, memory inspection, and
CIAR explanation.

Acceptance evidence: prompt discovery returns documented templates and variables.

### YAAM-REQ-0032: Support domain-specific prompt templates

Skill Factory, SCM Cognitive Sandwich, and SCM-Cert-Bench request specialized
prompts such as repair-pattern summaries, artifact-repair context, contradiction
review, and curation summaries.

Acceptance evidence: domain prompts are optional, scoped to relevant callers,
and exposed through MCP domain packs rather than the generic always-on surface.
The Cognitive Sandwich pack provides artifact repair context and artifact
lineage summary prompts.

### YAAM-REQ-0033: Preserve fail-fast behavior for write/assimilation failures

For mutating flows, customers generally prefer explicit failure over silent
empty writes or degraded persistence.

Acceptance evidence: failed writes return structured retryable/non-retryable
errors without pretending persistence succeeded.

### YAAM-REQ-0034: Track performance budgets for query, context, evidence, and CIAR operations

iAIMS, Skill Factory, Maritime Port Sandbox, and SCM-Cert-Bench provide latency
budgets for read, write, context, Evidence Table, CIAR explanation, and
contradiction review flows.

Acceptance evidence: plans and tests record workflow-level latency budgets.

### YAAM-REQ-0035: Require implementation plans to reference requirement IDs

To prevent architectural drift, future implementation plans should reference
the requirement IDs they satisfy.

Acceptance evidence: new plans and reports cite registry IDs.

### YAAM-REQ-0036: Enforce benchmark answer-leakage and contamination guards

SCM-Cert-Bench requires runtime retrieval to exclude hidden benchmark answers,
ground-truth reasoning, judge notes, curation records, and other fields that
would contaminate evaluated agents.

Acceptance evidence: runtime context retrieval fails closed or returns only
visibility-filtered memory with a leakage guard indicator and audit metadata.

### YAAM-REQ-0037: Store maintainer-only Gold task curation decisions

SCM-Cert-Bench requires durable storage for Gold task approval, rejection,
defect, and source-triad review decisions while keeping those records hidden
from evaluated runtime agents.

Acceptance evidence: curation writes return a stable curation record id,
visibility scope, source-triad links, timestamp, and audit id; runtime agents are
denied access.

### YAAM-REQ-0038: Store and retrieve trace and artifact correlation metadata

SCM-Cert-Bench needs YAAM records to correlate Phoenix traces, OpenRouter calls,
local JSONL artifacts, task ids, run ids, validation failures, and memory ids for
debugging and reproducibility.

Acceptance evidence: metadata writes and reads preserve correlation ids,
external trace ids, safe artifact references, linked memory ids, and degraded
trace status when an external trace cannot be verified.

### YAAM-REQ-0039: Provide SCM-Cert-Bench task, evidence, curation, and episode resources

SCM-Cert-Bench requests customer-specific MCP resources for task evidence,
session facts, episodes, curation records, health, and CIAR configuration. These
views should be discussed after generic MCP resources remain stable.

Acceptance evidence: resource templates enforce visibility scope, deny
runtime-only callers access to maintainer curation records, and return
JSON-parseable provenance-bearing data.
