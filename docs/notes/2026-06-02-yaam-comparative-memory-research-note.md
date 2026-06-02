# YAAM Comparative Memory Research Note

**Date:** 2026-06-02  
**Scope:** Comparative positioning of YAAM against Hy-Memory, TencentDB-Agent-Memory, Graphiti/Zep, Mem0, AgeMem, LangMem, and A-MEM/A-mem-sys  
**Method:** Local YAAM documentation, requirements, reports, and prior research notes; public third-party documentation, repositories, and papers; no benchmark runs, provider calls, dependency changes, or `skz-data-lv` checks.

## 1. Abstract

This note positions YAAM within the emerging agent-memory landscape. Recent external systems show that agent memory is moving beyond flat vector retrieval toward layered memory, temporal graphs, local-first memory, universal memory services, learned memory policies, LangGraph-native toolkits, and linked note networks. Against this landscape, YAAM's strongest differentiator is not merely that it stores memories in multiple backends. Its stronger claim is that it treats memory as governed research infrastructure: scoped interfaces, explicit public contracts, provenance, Evidence Table support, CIAR policy explanation, contradiction review, benchmark leakage controls, and observability are part of the design rather than incidental implementation details.

The comparison also identifies weaknesses. YAAM has less public ecosystem adoption than Mem0 or LangMem, less mature temporal-graph specialization than Graphiti/Zep, no learned unified LTM/STM policy comparable to AgeMem, and less public product visibility than Tencent's newly announced systems. In addition, YAAM's own reports record residual L3/L4 and operational complexity issues that should be treated as threats to validity until the next infrastructure-backed evaluation window.

## 2. YAAM Local Evidence Base

This note relies on the following local YAAM evidence:

- `docs/ADR/003-four-layers-memory.md`: accepted four-tier memory architecture.
- `docs/ADR/007-agent-integration-layer.md`: LangGraph integration, ToolRuntime, subgraphs, async-first architecture, and tool granularity.
- `docs/ADR/009-decoupling-benchmark-api-wall.md`: API Wall isolation for benchmarks and production-like evaluation.
- `docs/reference/public-contracts.md`: ScopeEnvelope, MemoryResult, ContextResponse, LeakageGuardResult, WriteAck, structured errors, read degradation, and write fail-fast semantics.
- `docs/requirements/yaam-requirements-registry.md`: accepted customer-facing requirements `YAAM-REQ-0001` through `YAAM-REQ-0039`.
- `docs/notes/2026-05-30-ciar-redesign-research-artifact.md`: CIAR as an auditable memory-policy layer with `hybrid_gate`, review-only evidence, suppression lane, and Phoenix spans.
- `docs/notes/2026-05-30-yaam-mcp-evolution-and-domain-pack-extensibility.md`: MCP evolution and domain-pack extensibility.
- `docs/reports/2026-05-28-yaam-runtime-dependency-hardening-validation-report.md`: runtime dependency posture, API-based embeddings, Qdrant validation, and residual L3/L4/Typesense notes.
- `docs/reports/2026-05-30-yaam-consumer-readiness-gate-report.md`: consumer readiness evidence and remote endpoint state as of 2026-05-30.
- `docs/reports/2026-02-22-goodai-smoke5-yaam-vs-pure-llm-comparison.md`: prior benchmark-style comparison evidence.

No new benchmark evidence is introduced in this note.

## 3. YAAM Architecture In Brief

YAAM's accepted design is a four-tier cognitive memory architecture:

| Tier | Role | Primary technology in documentation |
| --- | --- | --- |
| L1 Active Context | Ephemeral recent turns and immediate working buffer | Redis |
| L2 Working Memory | Significant facts and policy-filtered memory candidates | PostgreSQL |
| L3 Episodic Memory | Consolidated episodes and hybrid experience retrieval | Qdrant plus Neo4j |
| L4 Semantic Memory | Distilled final knowledge and artifacts | Typesense |

The memory pipeline is governed by lifecycle engines: promotion, consolidation, and distillation. CIAR began as a retention score and has evolved into an auditable policy layer. The current research note on CIAR records `hybrid_gate` as the selected default promotion policy, with contradiction suppression remaining opt-in. This is important because YAAM distinguishes:

- durable store lane;
- review-only evidence lane;
- suppression lane for superseded facts under opt-in policy.

YAAM also maintains a strict interface distinction:

- API Wall for benchmark isolation and production-like evaluation (`YAAM-REQ-0001`, `YAAM-REQ-0036`);
- REST v2 for backend and batch integrations (`YAAM-REQ-0004`);
- MCP for agent-host memory access (`YAAM-REQ-0002`, `YAAM-REQ-0003`).

The public contracts reference further defines scope, provenance, leakage guard fields, partial-read warnings, and write acknowledgements. This gives YAAM a service-contract posture that many competitor public sources do not expose.

## 4. Requirements-Fit Positioning

YAAM's customer requirements emphasize public interface safety and research auditability:

- distinct API Wall, REST v2, and MCP surfaces (`YAAM-REQ-0001`);
- scoped memory query and context assembly (`YAAM-REQ-0002`, `YAAM-REQ-0003`);
- scoped L2/L3/L4 writes and reads (`YAAM-REQ-0005` through `YAAM-REQ-0008`);
- provenance on reads and writes (`YAAM-REQ-0009`);
- session/task/tenant/run scoping (`YAAM-REQ-0010`);
- read-only default MCP resources and allowlisted mutating tools (`YAAM-REQ-0011`, `YAAM-REQ-0012`);
- redaction and secret boundaries (`YAAM-REQ-0013`);
- Phoenix-auditable operations (`YAAM-REQ-0014`);
- Evidence Table and CIAR explanation (`YAAM-REQ-0016`, `YAAM-REQ-0017`);
- partial-result warnings for degraded reads and fail-fast writes (`YAAM-REQ-0018`, `YAAM-REQ-0033`);
- contradiction/supersession review as opt-in (`YAAM-REQ-0029`);
- benchmark leakage guards (`YAAM-REQ-0036`).

Most competitor systems address memory quality, recall, or persistence more directly than they address this full public-governance surface. This is the main reason YAAM should be positioned as memory infrastructure rather than only a memory algorithm.

## 5. Comparative Analysis By System

### 5.1 YAAM Versus Tencent Hunyuan Hy-Memory

Hy-Memory is strategically important because it validates the multi-layer memory direction. Its public framing suggests a sophisticated memory stack designed for long-term personalization and agent behavior continuity. It is a serious competitor because it comes from a major platform actor and may have strong integration with Hunyuan models and Tencent ecosystem services.

YAAM's advantage is transparency of contracts. Local YAAM documentation exposes explicit interface boundaries, requirement IDs, tier responsibilities, provenance expectations, and policy-reporting needs. Public Hy-Memory material reviewed for this research did not expose enough implementation detail to evaluate equivalent guarantees for deletion, provenance, scoping, partial degradation, contradiction review, or benchmark leakage protection.

Hy-Memory is stronger as a public product signal. YAAM is stronger as a documented research infrastructure artifact.

### 5.2 YAAM Versus TencentDB-Agent-Memory

TencentDB-Agent-Memory is closest to YAAM in layered-memory spirit and local-first inspectability. Its framing around short-term memory, profiles, graph-like memory, and local artifacts makes it practically relevant for developers who want memory outside a managed cloud service.

YAAM differs by making public contracts central. ScopeEnvelope, MemoryResult, ContextResponse, leakage guards, and WriteAck semantics are not just internal data structures; they are compatibility targets across REST and MCP. This directly supports `YAAM-REQ-0009`, `YAAM-REQ-0010`, `YAAM-REQ-0018`, and `YAAM-REQ-0033`.

TencentDB-Agent-Memory may be stronger for local demo ergonomics and context-offload workflows. YAAM is stronger for multi-consumer interface governance.

### 5.3 YAAM Versus Graphiti/Zep

Graphiti/Zep is the strongest external reference for temporal graph memory. It is likely stronger than YAAM in graph-specific maturity, temporal graph modeling, and ecosystem recognition around graph memory. This matters because many real memory failures are temporal: old preferences become wrong, user projects evolve, and facts need time-aware validity.

YAAM has graph ambitions through L3 Neo4j and bi-temporal property-graph design, but it should not overclaim parity with Graphiti's specialization without fresh implementation evidence. YAAM's stronger position is broader governance: API Wall separation, CIAR policy, Evidence Table support, leakage guard fields, and customer-facing scoping. Graphiti/Zep may be a stronger graph memory engine; YAAM is a broader governed memory layer.

The paper-ready claim should be careful: YAAM incorporates temporal and graph-oriented concepts, but its novelty is the combination of tiered memory, policy gates, public contracts, and research auditability.

### 5.4 YAAM Versus Mem0

Mem0 is a major ecosystem competitor because it is easy to understand and broadly integrable. Its value proposition is close to what many developers want: add memory to agents and applications with less infrastructure burden. Public materials emphasize extraction, update, retrieval, and variants including graph-oriented memory.

YAAM is less plug-and-play. It is more complex and has more moving parts. The comparative advantage is that YAAM's complexity buys governance: scoped access, provenance, Evidence Table, CIAR explanation, opt-in contradiction review, benchmark leakage controls, and read/write failure semantics.

For paper positioning, Mem0 should be treated as a strong baseline for practical memory adoption. YAAM should not claim better memory quality without benchmark evidence. It can claim a more explicit governance and audit design based on local documentation.

### 5.5 YAAM Versus AgeMem

AgeMem is the most direct challenge to YAAM's policy novelty. It argues that memory operations should be learned as part of the agent's policy rather than implemented as fixed heuristics or external managers. Its tool set includes add, update, delete, retrieve, summarize, and filter, and its training strategy aims to unify LTM and STM management.

YAAM currently uses explicit policy engineering rather than learned memory policy. CIAR, `hybrid_gate`, review-only lanes, suppression lanes, and Evidence Table explanation are interpretable by design. AgeMem is stronger in adaptivity as a research idea. YAAM is stronger in operational accountability.

The most defensible paper framing is not "YAAM is more intelligent than AgeMem." It is: "YAAM provides auditable, service-oriented memory governance; learned memory policy systems such as AgeMem represent a future direction for optimizing policy decisions within such governed infrastructure."

### 5.6 YAAM Versus LangMem

LangMem is a strong developer-experience competitor for LangGraph users. It provides hot-path memory tools, background extraction, store-backed retrieval, semantic/episodic/procedural memory concepts, namespaces, and summarization utilities. For teams already using LangGraph, this is highly attractive.

YAAM's ADR-007 also uses LangGraph patterns, including ToolRuntime, subgraphs, async-first nodes, and unified/granular tools. However, YAAM deliberately keeps LangChain tools out of customer-facing contracts (`YAAM-REQ-0026`). This is a strategic difference:

- LangMem optimizes framework-native memory behavior.
- YAAM optimizes stable service contracts that can be consumed by multiple agent hosts and backend systems.

LangMem may be easier to adopt inside a single LangGraph application. YAAM is more appropriate when multiple customers, tools, benchmark harnesses, and audit workflows need a shared memory layer.

### 5.7 YAAM Versus A-MEM / A-mem-sys

A-MEM's Zettelkasten-inspired linked note model is a serious memory-organization idea. It makes memory more inspectable and evolvable than flat vector storage. A-mem-sys repository evidence indicates ChromaDB indexing, structured note generation, tags, keywords, context, and continuous refinement.

YAAM is stronger on explicit tiering and public governance. A-MEM is stronger as a lightweight and inspectable model for memory linking. YAAM's L3/L4 roadmap can learn from A-MEM by improving memory-inspector views, linked episode notes, and explainable relation formation.

The gap is that A-MEM public sources did not establish YAAM-equivalent scoping, provenance, deletion, Evidence Table, or trace contracts. YAAM can safely cite A-MEM as related work in agentic memory organization while distinguishing its own contribution as governed multi-interface memory infrastructure.

## 6. Comparative Matrix

| Dimension | YAAM | Strongest external comparator | Interpretation |
| --- | --- | --- | --- |
| Layer model | L1-L4 explicit tiers | Hy-Memory, TencentDB-Agent-Memory | YAAM is comparable and more locally documented. |
| Temporal graph | L3 Neo4j design and bi-temporal ADR | Graphiti/Zep | Graphiti/Zep likely stronger in graph maturity. |
| Filtering | CIAR plus `hybrid_gate`, review-only, suppression opt-in | AgeMem, Mem0 | YAAM is more explainable; AgeMem is more adaptive. |
| Condensation | L2 summaries, L3 episodes, L4 distillation | LangMem, A-MEM, AgeMem | YAAM has a tiered condensation model; implementation evidence should be refreshed. |
| Retrieval | L2/L3/L4 query and context assembly | Graphiti/Zep, Mem0, LangMem | YAAM's advantage is scoped context assembly and provenance. |
| Lifetime | TTL L1, CIAR retention, contradiction review, distillation | AgeMem, Graphiti/Zep, A-MEM | YAAM governance is stronger; learned and temporal evolution competitors are strong. |
| Interfaces | API Wall, REST v2, MCP | Mem0, LangMem | YAAM has broader contract separation; competitors may be easier to adopt. |
| Auditability | Evidence Table, CIAR explanation, Phoenix, public contracts | Graphiti inspectability, A-MEM note inspectability | YAAM has stronger audit contract evidence. |
| Benchmark posture | API Wall and leakage guards; prior reports | AgeMem, A-MEM, Mem0, Graphiti claims | YAAM needs fresh public benchmark results after infrastructure is available. |
| Ecosystem adoption | Internal/research project | Mem0, LangMem, Zep | YAAM is weaker on adoption and external recognition. |

## 7. Where YAAM Is Stronger

YAAM's strongest differentiators are:

- **Governed interfaces:** `YAAM-REQ-0001` preserves API Wall, REST v2, and MCP as separate interfaces.
- **Scoped access:** `YAAM-REQ-0010` requires session/task/tenant/run scoping, reflected in `ScopeEnvelope`.
- **Provenance:** `YAAM-REQ-0009` requires provenance on reads and writes.
- **Audit artifacts:** `YAAM-REQ-0016` and `YAAM-REQ-0017` require Evidence Table generation and CIAR explanation.
- **Policy transparency:** CIAR `hybrid_gate` separates durable storage from review-only and suppression outcomes.
- **Benchmark safety:** `YAAM-REQ-0036` and ADR-009 establish leakage and API Wall controls.
- **Failure semantics:** public contracts document partial reads with warnings and fail-fast writes.
- **Observability:** `YAAM-REQ-0014` and Phoenix reports create a traceability posture.
- **Domain extensibility:** domain packs and artifact lineage requirements give YAAM a path into SCM, Skill Factory, maritime, and benchmark-curation use cases.

These strengths are especially relevant for research papers because they make system behavior inspectable and falsifiable.

## 8. Where Competitors Are Stronger

YAAM should acknowledge the following competitor strengths:

- **Hy-Memory:** stronger public platform signal and likely deeper model-platform integration.
- **TencentDB-Agent-Memory:** stronger local-first repository visibility for developer experimentation.
- **Graphiti/Zep:** stronger temporal graph specialization and ecosystem maturity.
- **Mem0:** stronger adoption signal, simpler integration story, and clearer product-market visibility.
- **AgeMem:** stronger research novelty around learned unified LTM/STM policy.
- **LangMem:** stronger LangGraph-native developer ergonomics.
- **A-MEM:** stronger lightweight linked-note memory organization and inspectable memory evolution.

These are not fatal weaknesses for YAAM, but they should shape claims. YAAM should not compete on every axis. Its best axis is governed, auditable, multi-interface memory infrastructure for agent systems.

## 9. Threats To Validity

This comparative note has several limitations:

- No benchmarks were run for this task.
- `skz-data-lv` was explicitly offline and not checked.
- Third-party analysis depends on public documentation, papers, and repositories available at review time.
- Some competitor systems may implement governance features that are not publicly documented.
- YAAM local evidence includes prior reports and documentation, not fresh end-to-end validation.
- YAAM's L3/L4 implementation has known residual issues in prior reports, including Typesense-related health/read issues that require separate mechanism-layer authorization to triage.
- Public benchmark claims from competitors are not independently reproduced here.

## 10. Paper-Ready Positioning

A conservative paper positioning is:

> YAAM is a governed multi-tier memory layer for AI agents. Unlike systems that focus primarily on extraction, graph representation, or framework-native memory tools, YAAM emphasizes auditable memory policy, scoped public interfaces, provenance, benchmark isolation, and explainable memory admission. Its four-tier design combines ephemeral context, significance-filtered facts, episodic retrieval, and distilled semantic artifacts, while CIAR-based policy separates durable memory from review-only and superseded evidence.

This positioning does not deny competitor strengths. Instead, it locates YAAM in the governance and research-infrastructure part of the design space.

## 11. Future Evaluation Plan

Once infrastructure is available, the next comparative evaluation should:

1. Re-run YAAM's own smoke and regression checks under current production-like configuration.
2. Re-establish L3/L4 health and document any residual storage issues.
3. Create a benchmark protocol that separates answer quality, memory precision, memory recall, contradiction handling, provenance completeness, and leakage guard behavior.
4. Compare YAAM against at least one graph-memory baseline, one universal memory baseline, one LangGraph-native toolkit baseline, and one linked-note baseline where feasible.
5. Include ablations for CIAR modes: no memory, segment gate, fact gate, hybrid gate, and hybrid gate with opt-in suppression.
6. Report both task outcomes and memory-governance outcomes.
7. Keep provider/model variance explicit and use Phoenix traces or equivalent artifacts for run classification.

The central research question should not be only "Which system remembers more?" It should be "Which system remembers the right evidence, under the right scope, with the right provenance, and with auditable behavior under contradiction and degradation?"

## References

- `docs/ADR/003-four-layers-memory.md`
- `docs/ADR/007-agent-integration-layer.md`
- `docs/ADR/009-decoupling-benchmark-api-wall.md`
- `docs/reference/public-contracts.md`
- `docs/requirements/yaam-requirements-registry.md`
- `docs/notes/2026-05-30-ciar-redesign-research-artifact.md`
- `docs/notes/2026-05-30-yaam-mcp-evolution-and-domain-pack-extensibility.md`
- `docs/reports/2026-05-28-yaam-runtime-dependency-hardening-validation-report.md`
- `docs/reports/2026-05-30-yaam-consumer-readiness-gate-report.md`
- `docs/research/2026-06-02-agent-memory-synthesis.md`
- `docs/research/systems/2026-06-02-hymemory.md`
- `docs/research/systems/2026-06-02-tencentdb-agent-memory.md`
- `docs/research/systems/2026-06-02-graphiti-zep.md`
- `docs/research/systems/2026-06-02-mem0.md`
- `docs/research/systems/2026-06-02-agentic-memory-agemem.md`
- `docs/research/systems/2026-06-02-langmem.md`
- `docs/research/systems/2026-06-02-a-mem.md`
