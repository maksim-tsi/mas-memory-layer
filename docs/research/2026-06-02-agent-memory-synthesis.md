# Agent Memory Systems Synthesis

**Date:** 2026-06-02  
**Scope:** Tencent Hunyuan Hy-Memory, TencentDB-Agent-Memory, Graphiti/Zep, Mem0, Agentic Memory/AgeMem, LangMem, and A-MEM/A-mem-sys  
**Method:** Documentation, paper, and repository analysis only. No benchmark runs, provider calls, dependency changes, or `skz-data-lv` checks were performed.

## 1. Executive Synthesis

The current agent-memory landscape is fragmenting into several distinct architectural families. Hy-Memory and TencentDB-Agent-Memory emphasize layered memory and persona/context persistence. Graphiti/Zep emphasizes temporal knowledge graphs. Mem0 emphasizes a broadly integrable memory service with extraction, update, and retrieval. LangMem emphasizes toolkit-level integration with LangGraph. A-MEM emphasizes linked, Zettelkasten-like memory notes. AgeMem shifts the research frontier toward learned, unified LTM/STM memory policy.

These systems are not interchangeable. They differ at the level of architecture, decision making, storage technology, inspectability, production readiness, and governance. A requirement-only comparison would miss the main issue: the field is moving from "store some relevant facts" toward systems that decide how memory should evolve over time.

The strongest common pattern is structured memory evolution. Flat vector memory is no longer the dominant aspirational design. New systems either layer memory, graph it, link it as notes, manage it through tools, or learn memory operations as policy actions. The strongest common gap is governance. Public sources usually provide limited evidence for tenant/run scoping, provenance-preserving deletion, benchmark leakage controls, partial-result semantics, trace correlation, and customer-facing audit contracts.

## 2. Evidence Classes

This synthesis follows the research design document created for this task. Evidence labels are used conservatively:

- **Paper claim:** stated in a research paper but not locally reproduced.
- **Official documentation:** stated in product or project documentation.
- **Repository evidence:** visible in public repository README, examples, or source-level descriptions.
- **Implementation source evidence:** visible source-code behavior reviewed without execution.
- **Benchmark claim:** reported by a third party or project without local execution.
- **Insufficient evidence:** relevant detail not identifiable in the reviewed open sources.

The no-assumption rule is especially important for third-party systems. Absence of evidence is not treated as evidence of absence, but it is also not upgraded into a capability claim.

## 3. System Archetypes

| System | Primary archetype | Memory object | Decision model | Public maturity signal |
| --- | --- | --- | --- | --- |
| Tencent Hunyuan Hy-Memory | Layered memory system | Multi-layer memories / persona and interaction state | Documented pipeline / platform design | Official documentation, public launch material |
| TencentDB-Agent-Memory | Local-first layered memory | Short-term cache, user profile, graph, event logs | LLM-assisted extraction and local storage pipeline | Repository and documentation |
| Graphiti/Zep | Temporal knowledge graph | Episodes, entities, relations, temporal facts | Fixed graph extraction/update/retrieval pipeline | Open-source repo plus product lineage |
| Mem0 | Universal memory service/framework | Extracted user/application memories | Extraction-update-retrieve pipeline, with graph variant evidence | Open-source repo and public docs |
| AgeMem | Learned unified memory policy | LTM entries plus STM context actions | Progressive RL over memory tools | Research paper |
| LangMem | LangGraph toolkit | Store-backed semantic/episodic/procedural memories | Agent tools plus background managers | Official toolkit documentation |
| A-MEM / A-mem-sys | Agentic note network | Structured linked memory notes | LLM-driven note generation and linking | Paper/repo/demo system |

## 4. Architectural Comparison

### 4.1 Layered Memory

Hy-Memory and TencentDB-Agent-Memory are the clearest external examples of layered memory. They reflect a practical intuition also present in YAAM: different memory horizons need different mechanisms. Short-term context, user profile, graph-like associations, and longer-term knowledge should not be collapsed into one vector store.

The gap is that public sources provide limited information about precise lifecycle invariants. The systems appear layered, but open sources do not consistently expose exact semantics for retention, deletion, invalidation, or audit.

### 4.2 Temporal Graph Memory

Graphiti/Zep is the strongest representative of temporal graph memory. It treats memory as an evolving knowledge graph rather than merely a bag of facts. This is especially important for cross-session reasoning, user state evolution, and "what changed when" questions.

The graph approach is powerful, but graph extraction and maintenance create their own governance challenges: relation confidence, stale edges, contradictory facts, partial extraction, and temporal validity semantics must be made inspectable.

### 4.3 Service And Framework Memory

Mem0 and LangMem represent different sides of integrability:

- Mem0 is closer to a general memory layer/service for applications.
- LangMem is a toolkit for developers already building with LangGraph.

Both reduce adoption friction. Both also leave important deployment choices to integrators. This makes them strong ecosystem competitors but weaker sources of universal governance guarantees unless the downstream application adds those guarantees.

### 4.4 Learned Memory Policy

AgeMem is the most research-forward system in the set. It argues that memory should be learned as part of the agent policy, including add, update, delete, retrieve, summarize, and filter actions.

This is a serious conceptual challenge to fixed-threshold systems. However, AgeMem is not documented as a production service. Its contribution is best understood as a learned policy direction that future infrastructure systems may need to incorporate or evaluate against.

### 4.5 Linked Note Memory

A-MEM occupies a distinct niche. Its Zettelkasten-style linked note model is easier to inspect than pure vector search and less operationally heavy than a full temporal graph. It is attractive for personal knowledge, long-lived project memory, and knowledge browsing.

Its public gap is governance. The reviewed sources do not establish customer-grade scoping, provenance contracts, deletion semantics, or observability.

## 5. Lifecycle Comparison

| Dimension | Hy-Memory | TencentDB-Agent-Memory | Graphiti/Zep | Mem0 | AgeMem | LangMem | A-MEM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Capture | Layered conversation/persona capture | Local layered capture | Episode ingestion | Extract from conversations/events | Agent invokes add/update actions | Hot-path tools or background manager | Structured note generation |
| Filtering | Documented at high level; exact internals partly unknown | Local pipeline; exact thresholds partly unknown | Extraction/update pipeline; exact filtering depends on implementation | Extraction and update pipeline | Learned policy and STM filter tool | Agent/tool or manager configuration | LLM-driven note selection and metadata |
| Condensation | Multi-layer summaries/persona likely documented; exact details limited | Context offload/profile compression visible in repo framing | Episodes and graph facts condense interactions | Extracted memory statements; graph variant | Summary tool for STM | Summarization utilities | Note formation and metadata refinement |
| Retrieval | Multi-layer retrieval | Local context/profile/graph retrieval | Temporal graph plus search | Semantic and optional graph retrieval | Retrieve tool into STM | Store semantic search/tool retrieval | Vector and linked-note retrieval |
| Update | Memory evolution claimed | Profile/graph updates visible at high level | Temporal graph updates central | Extract-update pipeline central | Update tool | Tool/store dependent | Continuous refinement |
| Delete/forget | Insufficient evidence for exact public semantics | Insufficient evidence | Graph invalidation/update better evidenced than user deletion semantics | Delete APIs may exist; exact audit semantics need deployment evidence | Delete tool | Store/tool dependent | Insufficient evidence |
| Lifetime policy | Insufficient detail | Insufficient detail | Strong temporal orientation, but retention governance still deployment-dependent | Update/retention depends on configuration | Learned action policy, not product retention | Application-defined | Evolution-oriented, retention semantics unknown |

## 6. Filtering Strategies

External systems use at least five filtering strategies:

1. **Pipeline extraction filtering:** Mem0 and Graphiti/Zep process inputs into candidate memories or graph facts.
2. **Layer admission filtering:** Hy-Memory and TencentDB-Agent-Memory distribute information across memory layers.
3. **Agent tool filtering:** LangMem and AgeMem let the model decide when to store or search.
4. **Learned policy filtering:** AgeMem optimizes memory actions using RL.
5. **Note curation filtering:** A-MEM uses LLM-driven note generation and linking.

The public evidence rarely exposes exact negative filtering behavior: what is discarded, what becomes review-only, and how low-confidence or speculative content is treated. This is a major gap for enterprise and research users because memory quality depends as much on non-storage as on storage.

## 7. Condensation Strategies

Condensation is now central to agent memory:

- AgeMem treats summarization as an STM action.
- LangMem provides summarization utilities for long-running conversations.
- A-MEM condenses content into structured notes.
- Mem0 condenses interactions into memory statements.
- Graphiti/Zep condenses episodes into graph structure.
- Layered systems condense raw context into profile, graph, or long-term layers.

The open problem is loss accounting. Public sources do not consistently show whether condensed memory preserves source spans, compression decisions, uncertainty, or reviewer-visible omissions. This matters for scientific claims and regulated use cases.

## 8. Retrieval Strategies

Retrieval strategies differ substantially:

- **Vector/semantic retrieval:** Mem0, LangMem Store-backed search, A-MEM with ChromaDB evidence, and many layered systems.
- **Temporal graph retrieval:** Graphiti/Zep.
- **Layered context assembly:** Hy-Memory and TencentDB-Agent-Memory.
- **Learned retrieval action:** AgeMem.
- **Linked-note traversal:** A-MEM.

The likely future direction is hybrid retrieval: vector search alone is too weak for temporal and relational questions; graph retrieval alone is brittle when extraction misses implicit context; learned retrieval alone needs governance and explanation. Systems that combine semantic search, graph structure, explicit provenance, and bounded context assembly are better positioned for production research use.

## 9. Memory Evolution And Lifetime Management

Memory lifetime is the least consistently documented dimension.

Graphiti/Zep and A-MEM are strongest on memory evolution as a concept. Mem0 is strong on update-oriented memory pipelines. AgeMem is strongest on learned update/delete action selection. LangMem is flexible but application-defined. Tencent's systems are promising on layered and local memory, but public evidence does not expose enough exact semantics for retention and audit.

The critical distinction is between **capability** and **governance**:

- Capability asks whether a system can update or delete memory.
- Governance asks whether the system can explain, audit, scope, and enforce those updates.

Most public sources provide stronger evidence for capability than governance.

## 10. Production Readiness

| System | Production-readiness reading |
| --- | --- |
| Hy-Memory | Public product/research launch suggests serious engineering investment, but public internals are limited. |
| TencentDB-Agent-Memory | Strong local-first implementation signal; maturity depends on repo completeness and deployment support. |
| Graphiti/Zep | Strongest graph-production lineage in the set due to Zep ecosystem and open-source graph engine. |
| Mem0 | Strong adoption and integration signal; production details depend on chosen deployment. |
| AgeMem | Research framework, not a documented production service. |
| LangMem | Production-useful toolkit for LangGraph users, but not a standalone governed memory service. |
| A-MEM | Research/demo implementation signal; production governance unclear. |

## 11. Auditability And Inspectability

Inspectable memory is becoming more important. Graphiti/Zep's graph, A-MEM's linked notes, TencentDB-Agent-Memory's local-first posture, and layered memory systems all improve inspectability relative to opaque vector stores.

However, inspectability is not the same as auditability. Auditability requires stable source ids, provenance fields, policy decisions, trace correlation, redaction, and scoped access. Public evidence for these properties is limited across most competitors.

## 12. Benchmark Maturity And Reproducibility

The reviewed systems differ in benchmark posture:

- AgeMem reports research benchmark results across long-horizon tasks.
- A-MEM reports paper/repository benchmark claims.
- Mem0 and Graphiti/Zep have public benchmark narratives and comparisons in their ecosystems.
- LangMem is more documentation/toolkit oriented.
- Tencent systems have public claims, but exact reproducible benchmark artifacts were not fully evaluated in this review.

No benchmark runs were performed. All benchmark statements in the individual reports remain external benchmark claims unless the repository already contains reviewed artifacts. This matters because agent-memory benchmarks are vulnerable to leakage, prompt contamination, provider variance, and extraction instability.

## 13. Cross-System Gaps

The main gaps across the landscape are:

- limited public evidence for provenance-preserving deletion and supersession;
- limited customer-facing audit contracts;
- limited traceability from memory output back to extraction/policy decisions;
- weak or unknown handling of speculative, contradicted, or assistant-inferred facts;
- unclear read-degradation and write-failure semantics;
- limited benchmark contamination controls;
- deployment-specific scoping rather than universal session/task/tenant/run semantics;
- limited documentation of memory condensation loss.

These gaps do not imply that the systems cannot implement such features. They mean that the reviewed public sources do not establish them sufficiently for requirement-level confidence.

## 14. Research Implications

The field is moving toward memory systems that are:

- multi-layered rather than monolithic;
- temporal and relational rather than only semantic;
- policy-aware rather than append-only;
- agentic rather than purely background;
- inspectable rather than opaque;
- integrated with application frameworks rather than isolated databases.

The next research frontier is not just better retrieval. It is governed memory evolution: when to remember, when to summarize, when to update, when to forget, how to prove why, and how to prevent leaked or invalid evidence from entering downstream reasoning.

## References

- Tencent Hunyuan Hy-Memory. https://memory.hunyuan.tencent.com
- TencentDB-Agent-Memory. https://github.com/Tencent/TencentDB-Agent-Memory
- Graphiti / Zep. https://github.com/getzep/graphiti
- Mem0. https://github.com/mem0ai/mem0
- Yi Yu et al. "Agentic Memory: Learning Unified Long-Term and Short-Term Memory Management for Large Language Model Agents." https://arxiv.org/html/2601.01885v1
- LangMem documentation. https://langchain-ai.github.io/langmem/
- WujiangXu/A-mem. https://github.com/WujiangXu/A-mem
- WujiangXu/A-mem-sys. https://github.com/WujiangXu/A-mem-sys

