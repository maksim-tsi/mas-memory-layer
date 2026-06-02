# Customer Requirements Analysis For YAAM Interface Evolution

**Status:** Initial analysis  
**Date:** 2026-05-24  
**Registry:** [yaam-requirements-registry.md](yaam-requirements-registry.md)  
**Sources:** [external_requirements/](external_requirements/)

## 1. Executive Summary

The first customer requirement batch confirms the May 2026 interface direction:
YAAM should keep the API Wall, REST v2, and MCP as separate public interfaces.
Customers generally do not want YAAM memory hidden behind chat completions, do
not want direct storage/library coupling, and do not want LangChain tools as the
customer-facing contract.

The shared target is a service-backed interface model:

- REST v2 remains necessary for backend, batch, and current production-style
  integrations.
- MCP becomes the preferred agent-host and inspection interface.
- Raw memory operations, unified retrieval/context, and agentic evidence/CIAR
  behavior must remain separable.
- Write and lifecycle operations must be explicit, scoped, audited, and
  allowlisted.
- Benchmark integrations also need contamination guards that prevent evaluated
  agents from seeing hidden answers, judge reasoning, or maintainer curation
  notes.

## 2. Customer Submissions Reviewed

| Customer system | Primary interface expectation | Notable emphasis |
|---|---|---|
| TRA | REST v2 now, MCP later | Benchmark-safe memory, deterministic tool output storage, final evidence persistence. |
| iAIMS | REST v2 now, MCP read-heavy later | Repair-loop memory, pre-decision context, audit/evidence inspection. |
| Skill Factory | REST v2 for batch, MCP primary for agents | Skill generation history, QA/curation memory, CIAR and Evidence Table audits. |
| SCM Cognitive Sandwich | MCP-first | Artifact draft/revision/feedback/commit lineage and solver feedback. |
| Maritime Port Sandbox | REST v2 and MCP | Port/run/scenario evidence, admin mutation audit, simulation diagnostics. |
| SCM-Cert-Bench | REST v2 and MCP | Benchmark contamination controls, Gold curation isolation, Phoenix/artifact correlation, contradiction and safe-refusal review. |

## 3. Shared P0 Requirements

The following requirements appear across most or all customer submissions and
should be treated as first-class architecture constraints:

| Theme | Registry IDs | Impact |
|---|---|---|
| Separate API Wall, REST v2, and MCP roles | `YAAM-REQ-0001`, `YAAM-REQ-0004` | Prevents interface drift and preserves benchmark/service compatibility. |
| MCP read query and context assembly | `YAAM-REQ-0002`, `YAAM-REQ-0003` | Defines the first MCP value proposition. |
| Scoped L2/L3/L4 operations | `YAAM-REQ-0005` to `YAAM-REQ-0008` | Confirms REST v2 and MCP must share service-layer operations. |
| Provenance and scope enforcement | `YAAM-REQ-0009`, `YAAM-REQ-0010` | Required for auditability and multi-customer isolation. |
| MCP safety boundaries | `YAAM-REQ-0011` to `YAAM-REQ-0013` | Write/lifecycle operations need explicit allowlisting and redaction. |
| Observability and health | `YAAM-REQ-0014`, `YAAM-REQ-0015` | Phoenix visibility and health/config inspection are acceptance criteria. |
| Benchmark contamination controls | `YAAM-REQ-0036` | Runtime benchmark context must fail closed or exclude hidden answers, judge notes, and curation-only records. |
| Requirements governance | `YAAM-REQ-0035` | Future plans should cite requirements to prevent architectural drift. |

## 4. High-Impact P1 Themes

### 4.1 Evidence Table

Evidence Table generation is requested by iAIMS, Skill Factory, SCM Cognitive
Sandwich, and Maritime Port Sandbox. It is runtime-critical for some workflows
and audit/debug-only for others. The first design should therefore support
read-only evidence assembly before any autonomous memory mutation.

Relevant IDs: `YAAM-REQ-0016`, `YAAM-REQ-0031`.

### 4.2 CIAR Explanation

Customers need CIAR primarily for transparency, not as an opaque runtime
decision. Outputs should distinguish deterministic components from policy
metadata and review/suppression status.

Relevant ID: `YAAM-REQ-0017`.

### 4.3 Deterministic Feedback Storage

SCM Cognitive Sandwich, Maritime Port Sandbox, and Skill Factory all need to
persist external deterministic feedback such as solver logs, sandbox failures,
QA results, and simulation metrics.

Relevant IDs: `YAAM-REQ-0021`, `YAAM-REQ-0019`.

### 4.4 Reliability Split

Customers distinguish read and write failure behavior:

- read flows may return partial results with warnings;
- mutating flows should fail explicitly if persistence or required translation
  fails.

Relevant IDs: `YAAM-REQ-0018`, `YAAM-REQ-0033`.

### 4.5 Contradiction And Safe-Refusal Review

SCM-Cert-Bench makes contradiction review an MVP-aligned benchmark capability
because adversarial tasks need supporting and conflicting evidence plus a safe
refusal or infeasibility rationale. This promotes the prior deferred
contradiction review item into an accepted P1 requirement.

Relevant ID: `YAAM-REQ-0029`.

## 5. Customer-Specific Extensions

### 5.1 SCM Cognitive Sandwich Artifact Lineage

SCM Cognitive Sandwich requires artifact primitives: draft, feedback, revision,
commit, and lineage resources. This is the largest customer-specific product
extension and should be discussed before implementation.

Relevant IDs: `YAAM-REQ-0019`, `YAAM-REQ-0020`, `YAAM-REQ-0028`.

### 5.2 Skill Factory Domain Views

Skill Factory requires views by `skill_name`, `ctt_id`, `run_id`, QA status,
active-tool status, and generation/sandbox outcomes.

Relevant IDs: `YAAM-REQ-0022`, `YAAM-REQ-0023`, `YAAM-REQ-0032`.

### 5.3 Maritime Port Sandbox Domain Views

Maritime Port Sandbox requires views by `tenant_id`, `task_id`, `run_id`,
`scenario_id`, `port_code`, disruption type, admin mutation, and simulation
result.

Relevant IDs: `YAAM-REQ-0024`, `YAAM-REQ-0025`.

### 5.4 SCM-Cert-Bench Benchmark Views

SCM-Cert-Bench requires customer-specific views for benchmark tasks, Gold
curation records, evidence tables, post-run episodes, and trace/artifact
correlation. These are separate from generic MCP v1 resources because the
visibility model must distinguish evaluated runtime agents from maintainers and
post-run ingestion services.

Relevant IDs: `YAAM-REQ-0037`, `YAAM-REQ-0038`, `YAAM-REQ-0039`.

## 6. Conflicts And Design Tensions

| Tension | Observation | Recommendation |
|---|---|---|
| REST v2 vs MCP first | Most customers need both, but SCM Cognitive Sandwich is MCP-first. | Design services first, then adapters. Do not let one interface define the domain model alone. |
| Generic MCP surface vs customer resources | Customers request generic memory tools plus domain resources. | Keep core MCP generic; add customer/domain resource views only after service-layer scope design. |
| Agentic tools vs safety | Customers want Evidence/CIAR tools but restricted mutation. | Enable read-only agentic inspection first; gate lifecycle tools. |
| Artifact lineage vs current tier model | Artifact lineage is not only L1/L2/L3/L4 storage. | Treat artifact lineage as a service-level concept backed by tiers, not as storage adapter logic. |
| Partial reads vs fail-fast writes | Customers expect different degradation modes. | Encode this as interface policy: reads may degrade, writes must be explicit. |
| Benchmark context vs answer leakage | SCM-Cert-Bench wants runtime memory context, but hidden Gold answers and curation notes would invalidate evaluations. | Add a benchmark contamination guard requirement and fail closed when visibility filtering cannot be verified. |

## 7. Priority Discussion Agenda

Discuss these decisions before implementation planning:

1. Should the first MCP milestone include only generic memory tools
   (`YAAM-REQ-0002`, `YAAM-REQ-0003`) plus health, or also the first Evidence
   Table tool (`YAAM-REQ-0016`)?
2. Should artifact lineage (`YAAM-REQ-0019`) become a core YAAM concept or a
   customer-specific service module?
3. Should customer-specific resource templates for Skill Factory and Maritime
   Port Sandbox be included in MCP v1 or deferred until generic resources are
   stable?
4. What is the minimum common scope envelope for public interfaces:
   `session_id`, `task_id`, `tenant_id`, `agent_id`, `run_id`, and optional
   domain ids?
5. Which mutating MCP tools should be enabled first, and what allowlist model
   should control them?
6. Should CIAR explanation be part of MCP v1, given its high audit value and
   relatively bounded implementation surface?
7. Should SCM-Cert-Bench use generic task/session scopes first, or define a
   first-class benchmark task scope before customer-specific MCP resources?

## 8. Recommended Next Planning Step

The next planning discussion should classify `P0` and `P1` requirements into
three implementation waves:

1. **Governance and service layer:** registry enforcement, shared service
   boundaries, scope envelope, response provenance.
2. **MCP read surface:** query, context, health, config, facts/resources, and
   prompt discovery.
3. **Evidence and controlled writes:** Evidence Table, CIAR explanation,
   allowlisted L2/L3/L4 writes, and deterministic feedback ingestion.

Artifact lineage and customer-specific resources should be discussed as
separate impact items because they may require new domain models rather than a
simple adapter layer.

SCM-Cert-Bench adds one cross-cutting P0 to that planning discussion:
benchmark-safe context retrieval must prove hidden-answer and curation leakage
guards before returning runtime context.
