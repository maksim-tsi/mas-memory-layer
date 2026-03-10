I’m checking the updated ADR, the relocated RFC, and the implementation plan together so I can assess consistency, scope, and any gaps against the current repository state.

Read [](file:///home/max/code/mas-memory-layer/docs/ADR/013-phoenix-tracing-strategy.md)

Read [](file:///home/max/code/mas-memory-layer/docs/integrations/README.md#1-1), lines 1 to 120

Read [](file:///home/max/code/mas-memory-layer/docs/RFC/phoenix-tracing-rfc.md#1-1), lines 1 to 420

Read [](file:///home/max/code/mas-memory-layer/docs/plan/2026-03-10-phoenix-glassbox-tracing-implementation-plan.md)

I’m checking the new span contract and a few code touchpoints now so I can tell you whether the implementation plan matches the current YAAM semantics or accidentally overstates what the code can support.

Read [](file:///home/max/code/mas-memory-layer/docs/specs/observability/phoenix-span-contract.md)

Read [](file:///home/max/code/mas-memory-layer/src/agents/full_context_agent.py#1-1), lines 1 to 220

Read [](file:///home/max/code/mas-memory-layer/src/memory/ciar_scorer.py#1-1), lines 1 to 220

Read [](file:///home/max/code/mas-memory-layer/src/memory/engines/fact_extractor.py)

Read [](file:///home/max/code/mas-memory-layer/src/memory/unified_memory_system.py#330-330), lines 330 to 560

I’ve found a couple of material mismatches between the new tracing docs and the current YAAM behavior. I’m pulling exact line references now so I can give you a proper review with actionable findings rather than a vague summary.

Searched for regex `CIAR scoring|LLM-dependent modules|yaam.ciar.score|llm.ciar|fact_extract|FactExtractor` (`**/docs/{RFC,ADR,specs,plan}/**`), 189 results

Searched for regex `yaam.retriever.l3|yaam.retriever.l4|query_memory\(\)|L3|L4|selected evidence metadata|retriever spans around` (`**/docs/plan/2026-03-10-phoenix-glassbox-tracing-implementation-plan.md`), 4 results

Searched for regex `l3_tier\.query|l4_tier\.query|search_facts|query_by_session` (`**/src/memory/unified_memory_system.py`), 8 results

Searched for regex `class CIARScorer|def calculate\(|Formula: CIAR|certainty|impact|age_decay|recency` (`**/src/memory/ciar_scorer.py`), 129 results

I’m pulling one more narrow batch for exact `L3/L4` contract line numbers so the review can point to the precise mismatch between the plan and the current retrieval implementation.

Searched for regex `yaam\.retriever\.l3|yaam\.retriever\.l4|retrieval.documents` (`**/docs/specs/observability/phoenix-span-contract.md`), 9 results

Searched for regex `Emit benchmark-owned parent spans|evaluation harness|excluded from the repository distribution|transitional development concern` (`**/docs/{RFC,ADR,plan}/**`), 12 results

I reviewed the updated ADR, RFC, spec, and implementation plan. Two substantive issues stand out.

1. The documents currently misclassify CIAR scoring as an LLM-oriented tracing concern, but the implementation is deterministic arithmetic, not an LLM call. The RFC frames CIAR as part of “LLM-dependent modules” at phoenix-tracing-rfc.md, the span contract does the same at phoenix-span-contract.md and then defines `yaam.ciar.score` as a `TOOL` span at phoenix-span-contract.md, and the implementation plan follows that at 2026-03-10-phoenix-glassbox-tracing-implementation-plan.md. But the current scorer in ciar_scorer.py and ciar_scorer.py is a pure formula over certainty, impact, age decay, and recency boost. As written, the docs will steer implementation toward instrumenting a nonexistent LLM path and will also give Phoenix a misleading semantic type. I would rewrite CIAR as deterministic internal scoring, likely with a plain `CHAIN`-style internal step or a YAAM-specific span, and keep the optional `LLM` variant only as a future extension if a model-backed scorer is ever introduced.

2. The L3/L4 retriever contract currently overpromises query-aware retrieval that the code does not actually perform. The span contract says `yaam.retriever.l3` and `yaam.retriever.l4` are `RETRIEVER` spans attached to `query_memory` at phoenix-span-contract.md and phoenix-span-contract.md, and the implementation plan mirrors that at 2026-03-10-phoenix-glassbox-tracing-implementation-plan.md. However, the current `query_memory` implementation does not use the user query for L3 or L4 in a semantically meaningful way: L3 is fetched via `self.l3_tier.query(filters={"session_id": session_id}, limit=limit)` at unified_memory_system.py, and L4 is fetched via `self.l4_tier.query(limit=limit)` with no query argument at unified_memory_system.py. If you emit Phoenix retriever spans exactly as specified today, Phoenix will display “retrieved evidence” that was not actually selected by the current query, which weakens the whole glass-box claim. I would either narrow the plan to describe current L3/L4 behavior honestly as context enumeration, or make “fix query-conditioned L3/L4 retrieval semantics” an explicit prerequisite before those spans are labeled as retrievers.

Aside from those two points, the ADR, RFC, and plan are directionally aligned. The benchmark de-emphasis is internally consistent across 013-phoenix-tracing-strategy.md, phoenix-tracing-rfc.md, and 2026-03-10-phoenix-glassbox-tracing-implementation-plan.md, and I do not see other blocking inconsistencies from this pass.

If you want, I can next produce a concrete doc patch that fixes those two issues in the RFC, ADR-linked spec, and implementation plan without touching any runtime code.


-----