# YAAM Customer Interface Requirements Request

**Status:** Draft request template  
**Date:** 2026-05-24  
**Audience:** Customer system owners integrating with YAAM  
**Related:** [YAAM Interface Evolution Toward MCP - Initial Findings](../RFC/2026-05-24-yaam-interface-evolution-to-mcp-initial-findings.md), [YAAM MCP Interface and Memory Policy Evolution](../RFC/2026-05-18-yaam-mcp-and-memory-policy-evolution.md), [TRA Integration Guide v2](../api/TRA_Integration_Guide_v2.md)

## 1. Purpose

YAAM is evolving from a memory subsystem with REST and agent-tool entrypoints
into a multi-interface memory capability platform. The next planned interface is
an MCP server that exposes YAAM memory operations as discoverable tools,
resources, and prompts for agent hosts.

Before finalizing the MCP interface, we need structured requirements from each
customer system. Each customer should provide one Markdown document describing
how that system expects to use YAAM, which interface it requires, and what
operational constraints must be preserved.

Requested customer documents include, but are not limited to:

- `TRA-yaam-interface-requirements.md`
- `IAMS-yaam-interface-requirements.md`
- `Skill-Factory-yaam-interface-requirements.md`

Additional customer systems should submit equivalent Markdown files using the
same structure.

## 2. Request To Customer System Owners

Please provide a Markdown document for your system using the template below. The
goal is to capture concrete integration requirements, not a general product
wishlist. Where possible, include example payloads, expected tool calls, latency
expectations, failure handling rules, and tracing requirements.

The document should answer:

- which YAAM capabilities your system needs;
- whether your system expects REST, MCP, API Wall, LangChain tools, or multiple
  interfaces;
- which operations are read-only, write-enabled, or lifecycle-triggering;
- how sessions, agents, tasks, tenants, and users should be scoped;
- what evidence, provenance, and audit metadata must be returned;
- what error behavior your system expects;
- what acceptance tests would prove the interface works for your system.

## 3. Capability Model To Consider

When writing requirements, please classify each requested capability as one of
the following:

1. **Raw YAAM:** direct tier access such as L1 turns, L2 facts, L3 episodes, L3
   graph templates, and L4 knowledge documents.
2. **Unified YAAM:** cross-tier query, context assembly, retrieval explanation,
   and evidence aggregation without autonomous policy behavior.
3. **Agentic YAAM:** fact extraction, CIAR scoring and explanation, promotion,
   consolidation, distillation, Evidence Table generation, contradiction review,
   and other LLM-assisted memory policy functions.

This distinction helps us avoid exposing overly powerful agentic behavior to
systems that only need deterministic retrieval.

## 4. Required Markdown Template

Copy this section into a system-specific Markdown file and complete it.

```markdown
# <Customer System> YAAM Interface Requirements

**System:** <TRA | IAMS | Skill Factory | other>  
**Owner:** <name/team>  
**Date:** YYYY-MM-DD  
**Status:** Draft | Reviewed | Approved  
**Primary contact:** <name/contact>  

## 1. System Overview

Briefly describe the customer system and its role in the larger multi-agent
architecture. Include the main agent types, orchestration framework, and
deployment environment if known.

## 2. Integration Goals

Describe what the system needs from YAAM. Focus on concrete workflows.

Examples:

- retrieve relevant cross-session memory before an agent decision;
- store verified task facts in working memory;
- assimilate completed episodes into long-term memory;
- inspect CIAR decisions for debugging;
- expose memory resources to an MCP-capable agent host.

## 3. Expected Interface

State which interface or interfaces the system expects to use.

| Interface | Required? | Purpose | Notes |
|---|---:|---|---|
| API Wall `/v1/chat/completions` | Yes/No |  |  |
| REST v2 `/v2/memory/...` | Yes/No |  |  |
| MCP tools/resources/prompts | Yes/No |  |  |
| LangChain tools | Yes/No |  |  |
| Direct library calls | Yes/No |  |  |

## 4. Required Capabilities

List required YAAM capabilities. Classify each as Raw, Unified, or Agentic.

| Capability | Tier | Read/Write/Lifecycle | Required for MVP? | Example input | Expected output |
|---|---|---|---:|---|---|
|  | Raw/Unified/Agentic | Read/Write/Lifecycle | Yes/No |  |  |

## 5. Use Case Scenarios

Provide concrete scenarios. Each scenario should include the trigger, data sent
to YAAM, expected YAAM behavior, and expected customer-system behavior.

### Scenario 1: <name>

**Trigger:**  
**Caller:**  
**YAAM interface:**  
**Input example:**  
**Expected YAAM behavior:**  
**Expected response shape:**  
**Failure handling:**  
**Trace/audit expectations:**  

### Scenario 2: <name>

**Trigger:**  
**Caller:**  
**YAAM interface:**  
**Input example:**  
**Expected YAAM behavior:**  
**Expected response shape:**  
**Failure handling:**  
**Trace/audit expectations:**  

## 6. MCP Expectations

Complete this section if the system expects to use MCP.

### 6.1 Tool Requirements

List expected MCP tools, including whether they should be read-only or mutating.

| Proposed tool | Required? | Read/Write/Lifecycle | Required input fields | Required output fields |
|---|---:|---|---|---|
| `yaam.memory.query` | Yes/No | Read |  |  |
| `yaam.memory.get_context` | Yes/No | Read |  |  |
| `yaam.l2.store_fact` | Yes/No | Write |  |  |
| `yaam.ciar.explain` | Yes/No | Read |  |  |
| `yaam.evidence.table` | Yes/No | Read/Agentic |  |  |

### 6.2 Resource Requirements

List expected MCP resources.

| Proposed resource | Required? | Access scope | Notes |
|---|---:|---|---|
| `yaam://sessions/{session_id}/context` | Yes/No | Session |  |
| `yaam://sessions/{session_id}/facts` | Yes/No | Session |  |
| `yaam://facts/{fact_id}` | Yes/No | Fact |  |
| `yaam://health` | Yes/No | Service |  |
| `yaam://config/ciar` | Yes/No | Service |  |

### 6.3 Prompt Requirements

List reusable MCP prompts the system would use.

| Proposed prompt | Required? | Purpose | Expected variables |
|---|---:|---|---|
| `yaam.prompt.evidence_table` | Yes/No |  |  |
| `yaam.prompt.memory_inspection` | Yes/No |  |  |
| `yaam.prompt.ciar_explanation` | Yes/No |  |  |
| `yaam.prompt.contradiction_review` | Yes/No |  |  |

## 7. Data And Scope Requirements

Describe scoping rules.

- Required identifiers: `session_id`, `agent_id`, `task_id`, `tenant_id`,
  `user_id`, or other.
- Which identifiers are mandatory for every call?
- Which data can be shared across agents?
- Which data must remain private to an agent, task, tenant, or user?
- What retention expectations apply to each memory tier?

## 8. Provenance, Evidence, And CIAR Requirements

Describe what provenance and memory-policy metadata the system needs.

Questions to answer:

- Should responses include source tier, source id, timestamp, and producing
  agent?
- Should responses include CIAR components such as certainty, impact, age decay,
  recency boost, and final score?
- Should review-only evidence be returned?
- Should suppressed or superseded evidence be returned for audit purposes?
- Does the system need an Evidence Table? If yes, provide an example.

## 9. Security And Permission Requirements

Describe required access control and write restrictions.

Questions to answer:

- Which operations must be read-only?
- Which operations may mutate memory?
- Which lifecycle operations may be triggered by this system?
- Should write or lifecycle tools require explicit allowlisting?
- Are there data classes that must never be exposed through MCP resources?

## 10. Observability Requirements

Describe tracing, metrics, and audit requirements.

Questions to answer:

- Should the system propagate W3C `traceparent` headers?
- Which spans or events must be visible in Phoenix?
- What tool-call audit fields are required?
- What latency or error metrics are required?

## 11. Reliability And Error Handling

Describe expected behavior when YAAM or downstream services fail.

Questions to answer:

- Which failures should be retryable?
- What timeout budget is acceptable for each workflow?
- Should YAAM fail fast when LLM-backed extraction or embedding fails?
- Should partial results be returned for retrieval?
- What error shape does the customer system expect?

## 12. Performance Expectations

Provide expected scale and latency targets.

| Workflow | Expected QPS | p50 latency | p95 latency | Timeout budget | Notes |
|---|---:|---:|---:|---:|---|
|  |  |  |  |  |  |

## 13. Acceptance Tests

List the tests or demonstrations that would prove the integration works.

| Test | Interface | Setup | Expected result |
|---|---|---|---|
|  |  |  |  |

## 14. Open Questions

List unresolved questions, assumptions, or decisions needed from the YAAM team.
```

## 5. Suggested Minimal Response For Each Customer

If a full specification is not yet available, provide at least:

1. three concrete use case scenarios;
2. the preferred interface or interfaces;
3. required identifiers and isolation rules;
4. required read and write operations;
5. required provenance and CIAR metadata;
6. expected failure handling;
7. one acceptance test per scenario.

## 6. YAAM Team Review Criteria

The YAAM team will review each customer document against the following criteria:

- whether the requested capability belongs in Raw, Unified, or Agentic YAAM;
- whether the request should be served by REST v2, MCP, API Wall, or multiple
  interfaces;
- whether the request requires new service-layer functions;
- whether the request requires privileged write or lifecycle access;
- whether tracing and audit requirements are sufficient;
- whether the request can be tested without relying on hidden implementation
  details.

## 7. Expected Output

For planning purposes, each customer system should submit one Markdown file. The
preferred naming convention is:

```text
<customer-system>-yaam-interface-requirements.md
```

Examples:

```text
TRA-yaam-interface-requirements.md
IAMS-yaam-interface-requirements.md
Skill-Factory-yaam-interface-requirements.md
```

