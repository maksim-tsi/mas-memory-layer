# RFC: YAAM Interface Evolution Toward MCP - Initial Findings

**Status:** Draft for planning  
**Date:** 2026-05-24  
**Scope:** Public YAAM interfaces, MCP adapter planning, service-layer boundaries, customer requirements intake  
**Related:** [YAAM MCP Interface and Memory Policy Evolution](2026-05-18-yaam-mcp-and-memory-policy-evolution.md), [RFC-014 Semantic Gateway API v2](RFC014%20-%20YAAM%20Semantic%20Gateway%20API%20(v2).md), [TRA Integration Guide v2](../api/TRA_Integration_Guide_v2.md), [ADR-009](../ADR/009-decoupling-benchmark-api-wall.md), [CIAR Policy Recommendation Refresh Report](../reports/2026-05-23-ciar-policy-recommendation-refresh-report.md)

## 1. Summary

YAAM is ready to proceed with MCP interface planning, but the next step should be
service-boundary design rather than immediate MCP server implementation. The
existing documentation and codebase already define three public integration
directions:

1. the OpenAI-compatible API Wall for benchmark isolation and black-box chat
   evaluation;
2. the REST Semantic Gateway v2 for TRA and service-to-service integration;
3. a proposed MCP server for agent-host discoverability of YAAM tools,
   resources, and prompts.

The current architectural finding is that MCP should be implemented as a
separate adapter over shared YAAM service functions. It should not replace the
API Wall, should not duplicate the REST v2 implementation, and should not call
storage adapters directly.

## 2. Current Interface Baseline

### 2.1 API Wall

The API Wall remains the benchmark-facing boundary described by
[ADR-009](../ADR/009-decoupling-benchmark-api-wall.md). Its main responsibility
is protocol compatibility and evaluation isolation. It should not become the MCP
server because MCP has a different lifecycle, capability negotiation model, and
discovery surface.

### 2.2 Semantic Gateway v2

The v2 REST interface is active as a service integration boundary under the
`/v2/memory` prefix. It exposes memory operations in a way that hides storage
mechanisms from external orchestrators. The current implemented routes include:

- `POST /v2/memory/l1/turns`
- `GET /v2/memory/l1/turns/{session_id}`
- `DELETE /v2/memory/l1/turns/{session_id}`
- `POST /v2/memory/l2/facts`
- `POST /v2/memory/l3/assimilate`
- `POST /v2/memory/l3/query`
- `POST /v2/memory/l4/finalize`

The TRA integration guide also establishes an important operational convention:
distributed tracing should be propagated through W3C `traceparent` headers
rather than through ad hoc request-body trace fields.

### 2.3 Existing Tool Surface

YAAM already contains LangChain-compatible tools for several future MCP
capabilities:

- direct tier access in `src/agents/tools/tier_tools.py`;
- unified query and context assembly in `src/agents/tools/unified_tools.py`;
- CIAR calculation, filtering, and explanation in
  `src/agents/tools/ciar_tools.py`.

These tools are useful reference implementations, but they should not be treated
as the MCP service layer. MCP and LangChain tools should call shared services
instead of calling each other.

## 3. Initial Findings

### 3.1 MCP should be a new adapter, not a replacement interface

The documented interface model remains sound: API Wall, REST v2, and MCP solve
different problems. The MCP adapter should expose YAAM capability discovery to
agent hosts, while REST v2 should remain the conventional service API and API
Wall should remain the benchmark-compatible chat interface.

### 3.2 Service-layer extraction is the main prerequisite

The primary implementation gap is not tool naming or transport selection. The
primary gap is the absence of a small, stable service layer that can be reused
by REST routes, LangChain tools, MCP tools, tests, and benchmarks.

The proposed services are:

- `MemoryTierService` for raw L1, L2, L3, and L4 operations;
- `UnifiedRetrievalService` for cross-tier query and context assembly;
- `CIARPolicyService` for score calculation, explanation, filtering, and
  provenance;
- `LifecycleService` for promotion, consolidation, and distillation;
- `EvidenceService` for Evidence Table construction and evidence ranking.

This service layer should stay above `src/storage/`. Storage adapters remain
mechanisms; the service layer expresses YAAM policy and interface semantics.

### 3.3 CIAR redesign improves MCP readiness

The recent CIAR redesign materially improves readiness for MCP planning. CIAR is
now closer to a policy-controlled evidence gate than a bare scalar threshold.
The current default recommendation is:

- keep `hybrid_gate` as the promotion default;
- keep contradiction policy `off` by default;
- keep `suppress_superseded` opt-in until live extraction behavior is more
  stable.

For MCP, this means CIAR tools can expose structured provenance:

- raw fact CIAR;
- segment CIAR;
- stored CIAR, if any;
- evidence quality flags;
- review-only status;
- contradiction policy metadata.

This distinction is important because MCP clients should be able to inspect why
YAAM stored, filtered, reviewed, or suppressed a candidate memory item.

### 3.4 MCP capability tiers remain the correct abstraction

The three-tier capability model from the May 18 RFC remains appropriate:

1. **Raw YAAM:** direct tier operations without autonomous memory policy.
2. **Unified YAAM:** cross-tier retrieval and context assembly without
   autonomous agent behavior.
3. **Agentic YAAM:** fact extraction, CIAR policy, lifecycle engines, Evidence
   Table, and contradiction analysis.

This model lets customers choose "dumb memory substrate", "unified retriever",
or "policy-aware memory assistant" behavior without requiring separate
codebases.

### 3.5 Customer requirements are required before final MCP surface selection

The current MCP tool/resource/prompt list is plausible but still internally
driven. Before committing to the first MCP release surface, the project should
collect structured requirements from each customer system, including TRA, IAMS,
Skill Factory, and any additional orchestrator or agent host expected to consume
YAAM.

The requirements intake should identify:

- which integration interface each customer expects to use;
- whether they need raw, unified, or agentic capability tiers;
- which operations must be read-only, write-enabled, or lifecycle-triggering;
- expected session, tenant, agent, and task scoping;
- tracing and auditability requirements;
- latency, reliability, and retry expectations;
- security constraints and allowed write surfaces;
- required schemas and examples.

## 4. Proposed MCP Surface For Planning

### 4.1 Raw Tools

- `yaam.l1.store_turn`
- `yaam.l1.get_turns`
- `yaam.l2.store_fact`
- `yaam.l2.search_facts`
- `yaam.l3.search_episodes`
- `yaam.l3.query_graph`
- `yaam.l4.search_knowledge`
- `yaam.health.check`

### 4.2 Unified Tools

- `yaam.memory.query`
- `yaam.memory.get_context`
- `yaam.memory.explain_result`

### 4.3 Agentic Tools

- `yaam.ciar.calculate`
- `yaam.ciar.explain`
- `yaam.ciar.filter`
- `yaam.memory.extract_facts`
- `yaam.lifecycle.promote`
- `yaam.lifecycle.consolidate`
- `yaam.lifecycle.distill`
- `yaam.evidence.table`
- `yaam.evidence.rank`
- `yaam.contradiction.review`

### 4.4 Resource URI Templates

- `yaam://sessions/{session_id}/context`
- `yaam://sessions/{session_id}/turns`
- `yaam://sessions/{session_id}/facts`
- `yaam://facts/{fact_id}`
- `yaam://episodes/{episode_id}`
- `yaam://knowledge/{knowledge_id}`
- `yaam://schemas/fact`
- `yaam://schemas/episode`
- `yaam://schemas/knowledge-document`
- `yaam://health`
- `yaam://config/ciar`

Resources should be read-only in the first implementation. Any write behavior
should be exposed as tools with explicit schemas and audit logging.

### 4.5 Prompt Templates

- `yaam.prompt.evidence_table`
- `yaam.prompt.memory_inspection`
- `yaam.prompt.ciar_explanation`
- `yaam.prompt.retrieval_strategy`
- `yaam.prompt.contradiction_review`

Prompt templates should encode reusable inspection and reasoning workflows, not
hidden autonomous behavior.

## 5. Security And Isolation Findings

The first MCP implementation must treat write and lifecycle tools as privileged.
The minimum security requirements are:

- session scoping on every read and write;
- explicit distinction between read-only tools and mutating tools;
- optional allowlists for lifecycle tools;
- audit logging for all tool calls;
- no secret exposure through resources;
- JSON Schema and Pydantic validation for tool inputs;
- no arbitrary SQL or Cypher accepted from MCP clients;
- trace propagation for MCP calls into Phoenix spans;
- rate limits or explicit approvals for LLM-backed agentic tools.

These requirements are especially important because MCP clients may be agent
hosts with broad tool-calling autonomy.

## 6. Planning Recommendations

1. Collect customer requirements using the customer-system Markdown template in
   [YAAM Customer Interface Requirements Request](../requirements/2026-05-24-yaam-customer-interface-requirements-request.md).
2. Freeze the first MCP release scope to read-mostly raw and unified tools
   unless a customer provides a concrete write/lifecycle requirement.
3. Design the shared service layer before adding an MCP SDK dependency.
4. Define tool input/output schemas as reusable Pydantic models before binding
   them to MCP transport.
5. Treat `traceparent` propagation and Phoenix span visibility as acceptance
   criteria, not optional observability.
6. Add MCP contract tests for discovery, schema validation, structured output,
   resources, prompts, session isolation, and permission boundaries.

## 7. Open Questions

1. Which MCP transport should be implemented first: stdio, streamable HTTP, or
   both?
2. Should all write and lifecycle tools require an explicit server-side allowlist
   independent of client capabilities?
3. Should MCP expose REST v2 semantics exactly, or use a cleaner MCP-native
   naming and schema model?
4. Should `yaam.evidence.rank` be deterministic in the first release, or allow
   optional LLM reranking?
5. What customer systems require agentic tools in the first release rather than
   raw or unified retrieval only?
6. What authentication model should be used for local MCP clients versus remote
   MCP clients?

## 8. Acceptance Criteria For The Planning Phase

The MCP planning phase is complete when:

1. each target customer system has submitted a Markdown requirements document;
2. the first-release tool, resource, and prompt surface is explicitly scoped;
3. raw, unified, and agentic capability boundaries are testable;
4. service-layer responsibilities are documented before implementation;
5. security and write-permission policies are specified;
6. tracing requirements are specified for MCP calls and downstream YAAM spans;
7. dependency and transport choices are ready for explicit approval.

