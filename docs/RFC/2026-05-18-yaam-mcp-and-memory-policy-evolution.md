# RFC: YAAM MCP Interface and Memory Policy Evolution

**Status:** Proposed
**Date:** 2026-05-18
**Authors:** YAAM maintainers
**Scope:** YAAM public interfaces, CIAR evolution, MCP adapter, raw/unified/agentic capability tiers
**Related:** [CIAR audit](../reports/2026-05-18-ciar-design-and-implementation-audit.md), [RFC-014](RFC014%20-%20YAAM%20Semantic%20Gateway%20API%20(v2).md), [ADR-009](../ADR/009-decoupling-benchmark-api-wall.md), [EMAS reviewer feedback RFC](2026-03-28-emas-reviewer-feedback-rfc.md)

## 1. Summary

YAAM should add a Model Context Protocol (MCP) server as a separate product entrypoint, not convert the existing API Wall into MCP. The API Wall remains the OpenAI-compatible HTTP boundary for benchmarks and production-like chat interactions. The MCP server should expose YAAM memory capabilities to agent hosts through tools, resources, and prompts.

The recommended design is a three-tier capability model:

1. **Raw YAAM:** direct access to L1, L2, L3, and L4 tier operations.
2. **Unified YAAM:** cross-tier query and context assembly without autonomous agent behavior.
3. **Agentic YAAM:** CIAR, fact extraction, lifecycle engines, Evidence Table, and LLM-assisted policy tools.

This model directly answers the desired "dumb" vs "smart" split without forking the codebase.

## 2. Decision Proposal

Adopt the following direction:

1. Keep the current API Wall (`/v1/chat/completions` plus control endpoints) for ADR-009 benchmark isolation.
2. Keep the REST Semantic Gateway v2 (`/v2/memory/...`) for TRA and conventional service integration.
3. Add an MCP server as a new adapter over a shared YAAM service layer.
4. Do not put MCP logic inside `src/storage/`.
5. Do not make MCP depend on LangChain tools. Current LangChain tools and the future MCP tools should call the same service functions.
6. Treat CIAR v1 as a deterministic retention signal, not the whole memory policy.
7. Add a second-stage evidence policy for query-aware ranking, provenance, and contradiction handling.

## 3. Why The API Wall Does Not Simply Become The MCP Server

The API Wall and MCP solve different interface problems.

| Interface | Primary purpose | Protocol shape | Main consumer |
| --- | --- | --- | --- |
| API Wall | OpenAI-compatible black-box chat evaluation | HTTP REST, `/v1/chat/completions` | GoodAI benchmark, OpenAI-compatible clients |
| Semantic Gateway v2 | Service API for memory tier operations | HTTP REST, `/v2/memory/...` | TRA/orchestrators/services |
| MCP Server | Agent-host discoverability of tools/resources/prompts | JSON-RPC lifecycle with capabilities | Claude/Codex/agent hosts/MCP clients |

MCP's latest official spec describes a JSON-RPC base protocol with lifecycle/capability negotiation and optional server features: tools, resources, and prompts. Tools can return structured content and resource links; resources expose server-managed context/data by URI; prompts expose reusable prompt templates. These map well to YAAM, but they are not equivalent to an OpenAI chat completion endpoint.

Therefore the API Wall should remain intact. The MCP server should be a new adapter beside it.

## 4. Reviewer Feedback Influence

The reviewer feedback is mostly paper-facing, but it reveals design risks that the interface should avoid:

- Do not conflate database technology with cognitive memory type. PostgreSQL, Redis, Qdrant, Neo4j, and Typesense are mechanisms; L1-L4 are policy/semantics.
- Do not call Neo4j relational memory. It is graph storage used by L3.
- Do not use "cognitive stabilizer" unless there is a measurable mechanism and evaluation.
- Make "Retrieval-Reasoning Gap" mitigation concrete: evidence selection, evidence table, and reasoning support.
- Name skills and tools consistently. If the mechanism is Evidence Table, use that name across docs, tools, and prompts.

The MCP design should expose capability boundaries clearly enough that a client can choose raw DBMS-backed operations, unified retrieval, or intelligent policy tools without ambiguity.

## 5. Target Architecture

```text
                              +------------------------+
                              |      MCP clients       |
                              | Codex, Claude, agents  |
                              +-----------+------------+
                                          |
                                          | JSON-RPC MCP
                                          |
+-------------------+      +-------------v-------------+
| OpenAI-compatible |      |        YAAM MCP Server     |
| API Wall          |      | tools/resources/prompts    |
+---------+---------+      +-------------+-------------+
          |                              |
          | HTTP REST                    | shared service calls
          |                              |
+---------v---------+      +-------------v-------------+
| Semantic Gateway  |----->|     YAAM Service Layer     |
| v2 REST           |      | raw/unified/agentic APIs   |
+-------------------+      +-------------+-------------+
                                          |
                   +----------------------+----------------------+
                   |                      |                      |
                L1 Redis              L2 Postgres          L3/L4 stores
             Active Context         Working Memory       Qdrant/Neo4j/Typesense
```

The service layer is the key refactor. It should hold stable operations that can be called from:

- current LangChain tools,
- REST v2 routes,
- future MCP tools,
- tests and benchmark harnesses.

This avoids tool-specific behavior drift.

## 6. Capability Tiers

### 6.1 Raw YAAM

Raw YAAM exposes individual tiers and DBMS-backed operations directly. It should not run fact extraction, CIAR, lifecycle engines, or autonomous LLM policy unless the requested raw operation inherently needs embedding generation.

Examples:

- store/retrieve L1 turns,
- store/retrieve/search L2 facts,
- search L3 episodes by vector query,
- query L3 graph through safe templates,
- search L4 knowledge documents,
- inspect schemas and health.

Raw mode is useful for debugging, deterministic tests, external orchestrators, and users who want YAAM as a memory substrate rather than an agent.

### 6.2 Unified YAAM

Unified YAAM provides cross-tier operations without autonomous agent behavior.

Examples:

- query memory across L2/L3/L4,
- assemble context blocks,
- return evidence with stable ranking metadata,
- expose all levels together through one endpoint/tool.

Unified mode should be deterministic when given deterministic tier results. It may call embedding services for query-conditioned vector search, but it should not run fact extraction or make independent reasoning decisions.

### 6.3 Agentic YAAM

Agentic YAAM enables intelligent memory policy.

Examples:

- fact extraction,
- topic segmentation,
- CIAR scoring/explanation/filtering,
- promotion/consolidation/distillation lifecycle triggers,
- Evidence Table generation,
- contradiction and supersession analysis,
- retrieval-reasoning-gap mitigation prompts.

Agentic mode may use LLM calls and should expose provenance for any LLM-derived fields.

## 7. MCP Surface

### 7.1 MCP Tools

Tool names should use stable ASCII names and avoid spaces. Proposed names:

Raw tools:

- `yaam.l1.store_turn`
- `yaam.l1.get_turns`
- `yaam.l2.store_fact`
- `yaam.l2.search_facts`
- `yaam.l3.search_episodes`
- `yaam.l3.query_graph`
- `yaam.l4.search_knowledge`

Unified tools:

- `yaam.memory.query`
- `yaam.memory.get_context`
- `yaam.memory.explain_result`

Agentic tools:

- `yaam.ciar.calculate`
- `yaam.ciar.explain`
- `yaam.ciar.filter`
- `yaam.lifecycle.promote`
- `yaam.lifecycle.consolidate`
- `yaam.lifecycle.distill`
- `yaam.evidence.table`
- `yaam.evidence.rank`
- `yaam.memory.extract_facts`

Each tool should provide JSON Schema input and output schemas. For MCP compatibility, tools should return `structuredContent` and also include a compact text summary for clients that expect text.

### 7.2 MCP Resources

Resource URI templates:

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

Resources should be read-only. Sensitive resources should require session scoping and must not expose secrets.

### 7.3 MCP Prompts

Prompts should encode user-selectable workflows, not hidden behavior:

- `yaam.prompt.evidence_table`
- `yaam.prompt.memory_inspection`
- `yaam.prompt.ciar_explanation`
- `yaam.prompt.retrieval_strategy`
- `yaam.prompt.contradiction_review`

These prompts should reference resources where useful, for example a session context resource or a fact schema resource.

## 8. CIAR Evolution

This RFC does not propose removing CIAR. It proposes narrowing and strengthening it.

### Keep CIAR for:

- L1 -> L2 promotion baseline,
- deterministic significance scoring,
- explainable retention behavior,
- benchmark-friendly regression checks.

### Do not use CIAR alone for:

- cross-tier retrieval ranking,
- truth resolution,
- contradiction handling,
- evidence table ordering,
- claims of cognitive stabilization.

### Add EvidenceRanker

Introduce a policy object above retrieval:

```text
EvidenceRanker(
  query_relevance,
  ciar_retention,
  evidence_quality,
  temporal_validity,
  source_authority,
  contradiction_penalty,
  tier_prior
)
```

This should be implemented outside `src/storage/` and should consume tier results rather than changing storage adapters.

## 9. Implementation Plan

### Phase 0: Documentation alignment

1. Mark the 2026-03-10 CIAR/L3/L4 report as partly superseded where it describes old CIAR formula drift.
2. Update CIAR docstrings that still imply a capped `1.0-1.3` recency boost.
3. Align paper-facing terminology with implemented semantics.

### Phase 1: Service layer extraction

Create a small service layer over existing runtime objects:

- `MemoryTierService` for raw L1/L2/L3/L4 operations,
- `UnifiedRetrievalService` for cross-tier query/context,
- `CIARPolicyService` for score/explain/filter,
- `LifecycleService` for promotion/consolidation/distillation.

Existing REST and LangChain tools should call these services. No storage adapter changes are required.

### Phase 2: CIAR behavior hardening

1. Add tests for `Fact` component/score recomputation.
2. Add tests for v2 L2 store score behavior.
3. Add a named promotion policy mode for segment-vs-fact gating.
4. Record both segment-level and fact-level CIAR scores.
5. Add feature provenance to CIAR output.

### Phase 3: Evidence policy

1. Implement `EvidenceRanker`.
2. Implement `yaam.evidence.table` behavior first as service code.
3. Return structured evidence rows with tier, source id, score factors, provenance, and conflict notes.
4. Wire unified context assembly to optionally use `EvidenceRanker`.

### Phase 4: MCP server

1. Choose MCP transport and SDK after explicit dependency approval.
2. Implement MCP server as a separate entrypoint.
3. Expose minimal raw tools first: L1, L2, L3 search, L4 search.
4. Add unified query/context tools.
5. Add CIAR and Evidence Table tools.
6. Add resource templates and prompt templates.
7. Add auth/session scoping and audit logging.

### Phase 5: Evaluation

1. Re-run Smoke5-style benchmark comparisons through API Wall.
2. Add MCP contract tests for tool discovery, schema validation, and structured output.
3. Add tests for raw/unified/agentic capability boundaries.
4. Add Phoenix traces showing retrieval, evidence ranking, and CIAR feature provenance.

## 10. Testing Strategy

Required test groups:

- CIAR formula conformance tests,
- CIAR model validator tests,
- PromotionEngine policy mode tests,
- v2 REST route tests for L2 score consistency,
- unified retrieval ranking tests,
- MCP tool schema tests,
- MCP resource URI template tests,
- MCP prompt discovery tests,
- session isolation tests,
- tool permission/security tests.

After any `src/` change, run:

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest tests/ -v
```

Docs-only changes do not require the full suite.

## 11. Security And Isolation

MCP exposes powerful operations to agent hosts. The first implementation must enforce:

- session scoping for all memory reads/writes,
- explicit distinction between read tools and write/lifecycle tools,
- rate limits for LLM-backed tools,
- no secret exposure through resources,
- audit logging for tool calls,
- input validation through JSON Schema and Pydantic,
- no direct arbitrary Cypher/SQL from MCP clients; graph access should use templates or a controlled query planner.

## 12. Acceptance Criteria

The RFC is implemented when:

1. Existing API Wall behavior remains compatible with ADR-009.
2. REST v2 routes and LangChain tools share service code with MCP tools.
3. MCP clients can discover tools/resources/prompts.
4. Raw, unified, and agentic capability tiers are documented and enforceable.
5. A user can call each tier separately and all tiers together.
6. "Dumb YAAM" can run without agentic policy tools enabled.
7. "Smart YAAM" exposes CIAR, lifecycle, fact extraction, and Evidence Table tools with provenance.
8. CIAR outputs distinguish deterministic score computation from LLM-derived feature provenance.
9. Retrieval results expose enough evidence metadata to mitigate the retrieval-reasoning gap.

## 13. Open Questions

1. Which MCP transport should be supported first: stdio, streamable HTTP, or both?
2. Should write/lifecycle tools require an explicit allowlist separate from read tools?
3. Should MCP expose TRA-oriented REST v2 semantics exactly, or a cleaner MCP-native naming scheme?
4. Should EvidenceRanker be deterministic-only in v1, or allow optional LLM reranking?
5. How should benchmark variants represent raw, unified, and agentic modes?

## 14. Non-Goals

- No changes to `src/storage/` in the first implementation.
- No dependency changes without explicit approval.
- No replacement of the API Wall.
- No claim that MCP is the only public interface to YAAM.
- No paper rewrite in this RFC beyond terminology and documentation recommendations.

## 15. References

- MCP 2025-11-25 basic protocol: https://modelcontextprotocol.io/specification/2025-11-25/basic
- MCP tools: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- MCP resources: https://modelcontextprotocol.io/specification/2025-11-25/server/resources
- MCP prompts: https://modelcontextprotocol.io/specification/2025-11-25/server/prompts
- `docs/ADR/009-decoupling-benchmark-api-wall.md`
- `docs/RFC/RFC014 - YAAM Semantic Gateway API (v2).md`
- `docs/reports/2026-05-18-ciar-design-and-implementation-audit.md`
