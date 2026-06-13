# TencentDB-Agent-Memory: Individual Research Report

**Date:** 2026-06-02  
**System:** TencentDB-Agent-Memory  
**Evidence posture:** Public repository and product documentation evidence; implementation details partially available through open source.

## 1. Source Inventory

| Source | Evidence class | Notes |
| --- | --- | --- |
| https://github.com/Tencent/TencentDB-Agent-Memory | Repository evidence | Primary source for L0-L3 pipeline, configuration, local-first posture, retrieval strategy, and white-box debug claims. |
| Tencent Cloud Agent Memory product page | Official documentation | Source for managed/product framing around L0-L3 layered engine and precise recall. |
| OpenClaw/ClawHub plugin page | Official/plugin documentation | Source for plugin positioning and local memory service framing. |

This report treats TencentDB-Agent-Memory as a separate system from Hunyuan
Hy-Memory. The systems share Tencent ecosystem context, but their public
documents describe different layer counts, implementation technologies, and
deployment postures.

## 2. Architecture Summary

TencentDB-Agent-Memory presents a four-tier progressive memory pipeline:

- L0 Conversation: raw dialogue;
- L1 Atom: atomic facts;
- L2 Scenario: scene blocks;
- L3 Persona: user profile.

The repository describes the system as "symbolic short-term memory + layered
long-term memory." The long-term path distills fragmented conversations into
structured scenes and persona rather than storing a flat vector pile. The
short-term context-offload path condenses heavy tool logs and task traces into
compact Mermaid-style symbols.

This makes TencentDB-Agent-Memory notable for combining:

- local-first memory persistence;
- explicit inspectable intermediate artifacts;
- symbolic short-term context compression;
- layered persona-oriented long-term memory.

## 3. Implemented Technology

The repository documents:

- local backend based on SQLite and sqlite-vec;
- hybrid retrieval using BM25, vector search, and reciprocal rank fusion;
- OpenClaw plugin integration;
- Hermes Gateway adapter;
- agent tools such as `tdai_memory_search` and `tdai_conversation_search`;
- readable files under a local OpenClaw memory directory;
- L2 scenario blocks as Markdown;
- L3 persona stored as `persona.md`;
- Mermaid canvases for short-term task context compression;
- `result_ref` and `node_id` links from derived artifacts to raw payloads.

Configuration options include:

- `pipeline.everyNConversations`;
- `pipeline.enableWarmup`;
- `pipeline.l1IdleTimeoutSeconds`;
- `pipeline.l2MinIntervalSeconds`;
- `recall.strategy` with keyword, embedding, or hybrid modes;
- `recall.maxResults`;
- recall timeouts;
- dedup/conflict detection;
- local retention days for L0/L1 files;
- offload ratios for mild and aggressive compression;
- BM25 language.

This is one of the more implementation-visible external systems in the set.

## 4. Memory Lifecycle

### Capture

Once enabled, the system automatically captures conversation records. It is
documented as handling conversation capture, memory extraction, scene
aggregation, persona generation, and recall before the next turn.

### Filtering

Filtering is documented indirectly through extraction limits, deduplication,
conflict detection, and progressive promotion across L0-L3. The configuration
includes `extraction.maxMemoriesPerSession`, `extraction.enableDedup`, and
pipeline cadence controls.

Not enough information was identified in open sources to determine the exact
salience scoring formula or the full conflict-resolution algorithm.

### Condensation

Condensation is central:

- raw conversations become atomic facts;
- atom collections become scenario Markdown blocks;
- scenarios inform the persona profile;
- long-running tool traces can become Mermaid symbolic canvases.

This approach prioritizes inspectable compression rather than opaque embedding
storage alone.

### Retrieval

Retrieval is documented as hybrid:

- keyword search;
- embedding search;
- hybrid mode with reciprocal rank fusion.

The system also supports recall limits and timeout behavior. It is therefore
more explicit than many systems about practical retrieval controls.

### Update, Deletion, And Lifetime Management

The repository documents local retention days for L0/L1 files and pipeline
cadence controls. It also documents persona generation cadence and L2 minimum
intervals. This indicates an explicit lifetime-management posture for raw and
lower-level data.

Not enough information was identified in open sources to determine exact L2/L3
retention, persona overwrite semantics, legal hold or audit deletion behavior,
or how conflicting profile updates are adjudicated.

## 5. Decision-Making Model

TencentDB-Agent-Memory appears to be a fixed pipeline with configurable
cadence, thresholds, extraction limits, deduplication, and retrieval strategy.
It is not documented as an RL-trained memory policy. It is also not primarily an
agent-decided hot-path memory tool system. It is more appropriately described
as a local-first plugin pipeline for context governance and persona memory.

## 6. Benchmark Evidence

The repository claims:

- token usage reduction up to 61.38%;
- pass-rate improvement of 51.52% relative in its OpenClaw setting;
- PersonaMem accuracy improvement from 48% to 76%.

These are repository benchmark claims and were not reproduced here. The
availability of code makes the system more reproducible than a pure product
page, but this analysis did not run its tests or benchmarks.

## 7. Strengths

- Strong local-first posture with no required external API dependency in the
  advertised core.
- Clear L0-L3 progressive memory hierarchy.
- Hybrid BM25/vector/RRF retrieval is documented.
- White-box inspectability is a major strength: Markdown, Mermaid, persona
  files, and raw links are human-readable.
- Practical pipeline controls are documented.
- Useful distinction between short-term context offload and long-term persona
  memory.

## 8. Gaps And Unknowns

- Exact salience scoring and conflict-resolution internals are not fully
  documented in the sources inspected.
- No MCP public contract was identified in the primary repository evidence.
- Enterprise-grade permission policy, multi-tenant isolation, and structured
  error contracts are not sufficiently documented.
- It is unclear how well the local-first architecture scales to many governed
  projects or tenants.
- Benchmark claims were not reproduced here.

## 9. Relevance To YAAM Requirements

TencentDB-Agent-Memory appears relevant to:

- `YAAM-REQ-0005` through `YAAM-REQ-0008`, because it supports layered
  progression from raw dialogue to facts, scenarios, and profile;
- `YAAM-REQ-0009`, because its white-box artifact chain supports traceability
  from persona to scenario to atom to conversation;
- `YAAM-REQ-0015`, where local inspectability helps operational debugging;
- `YAAM-REQ-0034`, because pipeline cadence and retrieval limits are documented
  as controls.

Fit is unclear or weak for:

- `YAAM-REQ-0001` through `YAAM-REQ-0004`, because YAAM's explicit API
  Wall/REST/MCP separation is not mirrored;
- `YAAM-REQ-0011` through `YAAM-REQ-0013`, because MCP resources, write
  allowlisting, and redaction policy were not identified;
- `YAAM-REQ-0016` through `YAAM-REQ-0018`, because Evidence Table, CIAR
  explanation, and partial-result contracts are not documented;
- `YAAM-REQ-0036` through `YAAM-REQ-0039`, because benchmark leakage guards,
  curation records, and trace-correlation contracts are not identified.

## 10. Research Interpretation

TencentDB-Agent-Memory is strongest as a local-first, inspectable, layered
memory pipeline. Relative to YAAM, it offers more visible local artifacts and a
clearer short-term context-offload mechanism. YAAM has stronger documented
public-interface governance, requirement traceability, explicit permission
gates, and research-audit contracts.

## References

- Tencent. "TencentDB-Agent-Memory." GitHub repository. https://github.com/Tencent/TencentDB-Agent-Memory
- Tencent Cloud. "Agent Memory." https://cloud.tencent.com/product/agm
- OpenClawDir. "TencentDB Agent Memory - OpenClaw Plugin." https://openclawdir.com/plugins/tencentdb-agent-memory-zthub8
- ClawHub. "TencentDB Agent Memory." https://clawhub.ai/plugins/%40tencentdb-agent-memory/memory-tencentdb
