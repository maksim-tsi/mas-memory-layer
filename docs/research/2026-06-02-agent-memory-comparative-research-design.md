# Comparative Research Design: Agent Memory Systems

**Date:** 2026-06-02
**Status:** Research design for documentation-only comparative analysis
**Scope:** External agent-memory systems, YAAM comparison strategy, and evidence rules
**Constraint:** No benchmark runs, provider calls, dependency changes, or `local-yaam-host` checks.

## 1. Purpose

This document defines the research method for comparing contemporary agent-memory
systems against one another and against YAAM. The comparison is intentionally
not limited to customer requirements. It also examines architecture, implemented
technology, write and read workflows, filtering, condensation, retrieval,
lifetime management, observability, and decision-making policy.

The systems in scope are:

- Tencent Hunyuan Hy-Memory;
- TencentDB-Agent-Memory;
- Zep/Graphiti;
- Mem0;
- Alibaba/Wuhan University Agentic Memory, AgeMem;
- LangMem;
- A-MEM / A-mem-sys;
- H-Mem;
- YAAM, used as the final comparison target.

## 2. Evidence Classes

Every substantive claim in the research package should be assignable to one of
the following evidence classes.

| Evidence class | Meaning | Use in reports |
| --- | --- | --- |
| Official documentation | Vendor or project documentation, product pages, official guides, or official README files. | Default source for public interfaces, configuration, and stated architecture. |
| Paper claim | Peer-reviewed, preprint, or public technical paper claim. | Used for methods, benchmark claims, and theoretical framing. |
| Repository evidence | Public repository README, examples, scripts, and manifests. | Used for implementation posture and reproducibility signals. |
| Implementation source evidence | Public source code inspected directly. | Used only when open source code clearly shows a behavior. |
| Benchmark claim | Published benchmark result or methodology from the project authors. | Reported as a claim unless independently reproduced. |
| YAAM local evidence | Local YAAM docs, ADRs, reports, logs, and source inspection in this repository. | Used for YAAM implementation and validation state. |
| Insufficient evidence | The available open sources do not identify the detail. | Used instead of inference for third-party internals. |

## 3. No-Assumption Rule

Third-party systems must not be credited with behavior that is not identified in
open sources. If a source describes a capability at a product level but not an
implementation mechanism, the report should say so explicitly.

Required phrasing pattern:

> Not enough information was identified in open sources to determine ...

This applies especially to:

- retention and deletion semantics;
- security policy and access control;
- audit logging internals;
- exact scoring/ranking formulas;
- cost and latency behavior outside published benchmarks;
- multi-tenant isolation;
- failure and partial-result semantics.

## 4. Common Analysis Dimensions

Each individual report should cover the following dimensions.

| Dimension | Questions |
| --- | --- |
| Architecture and layer model | Is the system layered, graph-native, vector-first, toolkit-based, or learned? What are the named memory types or tiers? |
| Implemented technology | Which stores, embedding models, LLM providers, graph engines, vector databases, search methods, APIs, plugins, or SDKs are documented? |
| Write path | How does raw interaction data become memory? Is writing synchronous, asynchronous, batch-triggered, agent-invoked, or background-managed? |
| Filtering | What determines whether a candidate memory is stored, updated, suppressed, or ignored? |
| Condensation | How are raw messages compressed into facts, notes, scenarios, profiles, summaries, schemas, or context states? |
| Retrieval and ranking | Which retrieval signals are used: vector similarity, BM25, graph traversal, reranking, temporal filtering, RRF, context packing? |
| Lifetime management | How are updates, deletion, invalidation, supersession, TTL, aging, profile evolution, or memory decay handled? |
| STM versus LTM | Does the system manage active context, long-term memory, or both? Are these independently managed or unified? |
| Scope and isolation | What scoping dimensions are documented: user, session, agent, group, tenant, project, run? |
| Provenance and auditability | Can derived memory be traced back to raw sources? Are artifacts readable? Are operations observable? |
| Interfaces | What surfaces exist: library, SDK, REST, MCP, plugin, CLI, hosted platform, local service? |
| Governance and safety | Are write gates, read-only resources, redaction, permission policy, audit logs, or benchmark leakage controls documented? |
| Benchmark evidence | What has been evaluated, against which baselines, and how reproducible is the evidence? |

## 5. Deliverable Structure

The research package consists of three layers.

### Individual System Reports

Each report should be self-contained and include:

- source inventory;
- source confidence;
- architecture summary;
- technology implementation;
- memory lifecycle;
- decision-making model;
- lifetime management;
- strengths;
- gaps and unknowns;
- relevance to YAAM requirements where applicable.

### Cross-System Synthesis

The synthesis report should compare the external systems without centering YAAM
as the main object. It should identify field-level patterns:

- layered memory versus graph memory versus learned memory;
- service, toolkit, plugin, local-first, and research-framework models;
- filtering and condensation strategies;
- retrieval/ranking strategies;
- memory evolution and lifetime-management patterns;
- benchmark and reproducibility posture.

### YAAM Comparative Note

The final note should compare YAAM against the synthesized landscape. It should
cite individual reports where possible and draw on local YAAM evidence:

- requirements registry;
- architecture ADRs;
- MCP/REST/public contract documentation;
- CIAR policy reports and logs;
- consumer-readiness and runtime-hardening reports;
- GoodAI Smoke5 comparison artifacts.

## 6. Requirement Traceability

YAAM customer-fit claims should cite relevant requirement IDs. The most
important requirement families for this research are:

- `YAAM-REQ-0001` through `YAAM-REQ-0004`: interface separation and MCP/REST/API Wall roles;
- `YAAM-REQ-0005` through `YAAM-REQ-0008`: tier-specific L2/L3/L4 operations;
- `YAAM-REQ-0009` through `YAAM-REQ-0015`: provenance, scoping, security, health, and tracing;
- `YAAM-REQ-0016` through `YAAM-REQ-0018`: Evidence Table, CIAR explanation, and degraded reads;
- `YAAM-REQ-0019` through `YAAM-REQ-0025`: artifact and domain-specific memory;
- `YAAM-REQ-0026` through `YAAM-REQ-0028`: public-contract boundaries;
- `YAAM-REQ-0029` through `YAAM-REQ-0030`: contradiction and lifecycle controls;
- `YAAM-REQ-0031` through `YAAM-REQ-0039`: prompts, performance budgets, benchmark leakage, curation, and trace correlation.

## 7. Threats To Validity

The research package must preserve these limitations:

- no external benchmark results are reproduced in this work;
- public benchmark claims are not directly comparable unless datasets,
  readers, judges, prompts, context sizes, and scoring protocols match;
- product pages may omit operational details such as failure behavior,
  authorization, or lifecycle workers;
- open-source repositories may lag hosted products;
- YAAM evidence is richer operationally but currently lacks fresh live
  competitor benchmark runs because `local-yaam-host` is offline.

## 8. Source Inventory

Primary sources identified for this research:

- Hy-Memory: https://memory.hunyuan.tencent.com/ and https://memory.hunyuan.tencent.com/openclaw/
- TencentDB-Agent-Memory: https://github.com/Tencent/TencentDB-Agent-Memory and Tencent Cloud Agent Memory product documentation.
- Graphiti/Zep: https://github.com/getzep/graphiti, https://help.getzep.com/graphiti/getting-started/overview, https://github.com/getzep/graphiti/blob/main/mcp_server/README.md, https://www.getzep.com/platform/graphiti/, https://www.getzep.com/research/, and https://arxiv.org/abs/2501.13956.
- Mem0: https://github.com/mem0ai/mem0, https://docs.mem0.ai/, https://docs.mem0.ai/open-source/features/graph-memory, and https://arxiv.org/abs/2504.19413.
- AgeMem: https://arxiv.org/html/2601.01885v1.
- LangMem: https://langchain-ai.github.io/langmem/.
- A-MEM: https://arxiv.org/abs/2502.12110, https://github.com/WujiangXu/A-mem, and https://github.com/WujiangXu/A-mem-sys/.
- H-Mem: https://arxiv.org/html/2605.15701v1.
- YAAM: local repository documentation, reports, logs, and source under this checkout.
