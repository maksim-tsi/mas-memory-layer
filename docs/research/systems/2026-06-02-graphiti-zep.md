# Zep/Graphiti: Individual Research Report

**Date:** 2026-06-02  
**System:** Graphiti open source and Zep managed platform  
**Evidence posture:** Official documentation, repository evidence, product benchmark claims, and arXiv paper evidence.

## 1. Source Inventory

| Source | Evidence class | Notes |
| --- | --- | --- |
| https://github.com/getzep/graphiti | Repository evidence | Primary source for Graphiti OSS architecture, stores, MCP/REST surfaces, and quick-start posture. |
| https://help.getzep.com/graphiti/getting-started/overview | Official documentation | Primary source for temporal context graph concepts and Graphiti/Zep distinction. |
| https://github.com/getzep/graphiti/blob/main/mcp_server/README.md | Repository evidence | Source for Graphiti MCP server capabilities. |
| https://www.getzep.com/platform/graphiti/ | Official product documentation / benchmark claim | Source for Graphiti positioning and Zep performance claims. |
| https://www.getzep.com/research/ | Benchmark claim / methodology | Source for LoCoMo and LongMemEval claims and methodology notes. |
| https://arxiv.org/abs/2501.13956 | Paper claim | Source for Zep temporal knowledge graph architecture and DMR/LongMemEval claims. |

The report distinguishes open-source Graphiti from commercial Zep. Graphiti is
the temporal context graph engine. Zep is the governed, managed context
infrastructure and Context Lake built on top of that engine and proprietary
serving infrastructure.

## 2. Architecture Summary

Graphiti builds dynamic temporal context graphs. The primary memory units are:

- entities/nodes with summaries that evolve over time;
- facts/relationships/edges as triplets with temporal validity windows;
- episodes as raw ingested provenance;
- custom entity and edge types defined with Pydantic models.

The central architectural contribution is temporal graph memory. Facts have
validity windows, and when information changes, old facts are invalidated rather
than deleted. This enables "what is true now" and point-in-time reasoning.

Zep extends this with managed, governed, low-latency context graph serving at
scale.

## 3. Implemented Technology

Graphiti documents support for:

- Neo4j;
- FalkorDB;
- Kuzu;
- Amazon Neptune with OpenSearch Serverless for full-text search;
- OpenAI-compatible LLM and embedding services by default;
- Anthropic, Groq, Gemini, Azure OpenAI, and other provider support through
  configuration;
- structured output capable models for best ingestion reliability;
- hybrid retrieval with semantic, keyword, and graph traversal signals;
- FastAPI REST service under the repository `server` directory;
- an MCP server under the `mcp_server` directory.

The MCP server documents:

- episode management;
- entity and relationship management;
- semantic and hybrid search;
- group management through `group_id`;
- graph maintenance operations;
- HTTP transport and stdio-compatible use through client configuration;
- multiple graph database options;
- multiple LLM and embedding providers;
- telemetry collection that can be disabled.

## 4. Memory Lifecycle

### Capture

Graphiti ingests episodes from unstructured text, structured JSON, and
conversation/business data. Episodes are the source stream and provenance root.

### Filtering

Filtering is not documented as a salience gate comparable to CIAR or an
attention gate. Graphiti focuses on incremental graph construction, entity and
relationship extraction, and temporal invalidation. Not enough information was
identified in open sources to determine whether Graphiti has an explicit
pre-ingestion memory-worthiness filter beyond extraction behavior and client
selection of episodes.

### Condensation

Condensation happens through:

- entity summaries that evolve over time;
- extracted triplets/facts;
- temporal relationship updates;
- possible learned and prescribed ontology construction.

Graphiti is less about hierarchical condensation into profile/persona layers
and more about graph-level extraction, invalidation, and summarization of
entities.

### Retrieval

Graphiti documents hybrid retrieval:

- semantic embedding search;
- keyword/BM25-like full-text search;
- graph traversal and graph algorithms;
- graph-distance reranking in examples;
- temporal querying.

Zep product pages further claim ranked context assembly with low latency and
token-efficient context blocks.

### Update, Deletion, And Lifetime Management

Graphiti's strongest lifetime-management feature is temporal fact invalidation.
Every edge can carry timestamps for when a fact became valid, when it stopped
being valid, when Graphiti learned about it, and when Graphiti learned it was
no longer true. Old facts are preserved as history but removed from current
state.

Graphiti MCP includes tools to delete episodes and entity edges and clear the
graph. Not enough information was identified in open sources to determine
enterprise retention policy, legal hold, or deletion audit behavior in Graphiti
OSS. Zep product pages claim retention policies and audit/API logs for the
commercial platform.

## 5. Decision-Making Model

Graphiti is a temporal graph construction and retrieval engine. Its memory
decision-making is primarily implemented through extraction, temporal logic,
ontology, and retrieval algorithms rather than an RL-trained memory policy. It
does not appear to expose memory operations as agent-learned actions in the
AgeMem sense.

## 6. Benchmark Evidence

Zep and Graphiti public pages claim:

- LoCoMo accuracy of 94.7%, retrieval latency around 155 ms p95, and median
  context size around 5,760 tokens;
- LongMemEval accuracy of 90.2%, retrieval latency around 162 ms p95, and
  median context size around 4,408 tokens;
- auto-search results with smaller context at lower accuracy;
- arXiv paper claims on DMR and LongMemEval relative to baselines.

These are benchmark claims and methodology disclosures. They were not
reproduced in this research.

## 7. Strengths

- Mature temporal graph architecture.
- Strong provenance model through episodes.
- Explicit fact validity windows and invalidation.
- Strong hybrid retrieval story.
- Open-source implementation with multiple graph backends.
- MCP and REST surfaces are documented.
- Zep commercial layer addresses governance, scale, audit logs, and enterprise
  controls more directly than Graphiti OSS.
- Strong published benchmark positioning.

## 8. Gaps And Unknowns

- Graphiti OSS does not by itself provide Zep's governed enterprise Context
  Lake.
- Pre-ingestion salience filtering is not clearly documented.
- Evidence Table-style explanation, CIAR-like policy components, and
  benchmark-leakage guards are not identified.
- Graphiti's MCP server exposes maintenance operations such as `clear_graph`;
  suitability depends on external host authorization and deployment policy.
- Partial-result and structured failure contracts comparable to YAAM's public
  contracts were not identified in the inspected sources.

## 9. Relevance To YAAM Requirements

Graphiti/Zep appears strong for:

- `YAAM-REQ-0006` and `YAAM-REQ-0007`, because episodes and temporal graph
  facts support long-term episode and semantic retrieval;
- `YAAM-REQ-0009`, because episodes are a provenance root;
- `YAAM-REQ-0010`, where `group_id` and Zep user/context graph separation
  provide scoping mechanisms, although exact YAAM-style scope envelope parity is
  not present;
- `YAAM-REQ-0029`, because temporal invalidation addresses contradiction and
  supersession;
- `YAAM-REQ-0034`, given published latency and context-size metrics.

Fit is partial or unclear for:

- `YAAM-REQ-0001` through `YAAM-REQ-0004`, because Graphiti has REST and MCP
  surfaces but not YAAM's explicit API Wall/REST/MCP separation;
- `YAAM-REQ-0011` through `YAAM-REQ-0013`, because read-only resource policy,
  mutating-tool allowlists, and redaction are not specified in the same way;
- `YAAM-REQ-0016` through `YAAM-REQ-0018`, because Evidence Table, CIAR
  explanation, and partial-result semantics are not documented as Graphiti
  surfaces;
- `YAAM-REQ-0036` through `YAAM-REQ-0039`, because benchmark leakage, curation,
  and trace-correlation contracts are YAAM-specific.

## 10. Research Interpretation

Graphiti/Zep is likely the strongest competitor for temporal graph reasoning
and production context-graph retrieval. Compared with YAAM, it appears more
mature as a temporal graph engine and has stronger public benchmark claims.
YAAM remains more explicit about multi-interface research contracts,
requirement traceability, Evidence Table/CIAR audit, benchmark leakage guards,
and service-layer read/write governance.

## References

- GetZep. "Graphiti." GitHub repository. https://github.com/getzep/graphiti
- Zep Documentation. "Graphiti Overview." https://help.getzep.com/graphiti/getting-started/overview
- GetZep. "Graphiti MCP Server README." https://github.com/getzep/graphiti/blob/main/mcp_server/README.md
- Zep. "Graphiti." https://www.getzep.com/platform/graphiti/
- Zep. "Research." https://www.getzep.com/research/
- Daniel Rasmussen et al. "Zep: A Temporal Knowledge Graph for Agent Memory." arXiv. https://arxiv.org/abs/2501.13956
