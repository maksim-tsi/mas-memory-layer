# Phoenix Span Contract (OpenInference) for YAAM Glass-Box Observability

**Status:** Draft  
**Date:** March 10, 2026  
**Owners:** YAAM maintainers, observability owners  
**Related:** [ADR-013](../../ADR/013-phoenix-tracing-strategy.md), [RFC: Phoenix tracing (glass-box)](../../RFC/phoenix-tracing-rfc.md)

## 1. Objective

This specification defines a normative tracing contract for YAAM execution using Arize Phoenix with
OpenInference semantic conventions. The contract is designed to support "glass-box" inspection of:

1. agent workflow stages (perception, retrieval, reasoning, update, response),
2. memory reads and writes across L1-L4,
3. and LLM-dependent modules (CIAR scoring, fact extraction, consolidation, distillation).

The contract is defined above the frozen mechanism layer. It MUST NOT require modifications to
`src/storage/`.

## 2. Scope and non-goals

**In scope**

1. API wall request root spans and correlation fields.
2. YAAM agent spans and phase spans.
3. Memory retrieval and context-assembly spans for L1-L4.
4. Lifecycle spans for promotion, consolidation, and distillation.
5. LLM spans for CIAR scoring, fact extraction, and other explicit LLM modules.

**Not a goal**

1. Benchmark-owned tracing or evaluation harness reporting.
2. Guaranteeing a specific Phoenix UI layout beyond OpenInference-compatible semantics.
3. Instrumenting storage adapters in `src/storage/` (mechanism is frozen-by-default).

## 3. Normative conventions

### 3.1 Required OpenInference keys

Spans emitted under this contract MUST use OpenInference keys for kind and core fields:

| Category | Key | Requirement |
|---|---|---|
| Span kind | `openinference.span.kind` | MUST be set for all spans in this contract |
| Session | `session.id` | MUST be set on the request root span and propagated to child spans |
| User | `user.id` | SHOULD be set when a stable user identifier exists |
| High-level I/O | `input.value`, `output.value` | SHOULD be set on `AGENT` spans (or equivalent boundary spans) |
| Workflow graph | `graph.node.id`, `graph.node.parent_id`, `graph.node.name` | SHOULD be used for workflow phases when the agent executes a DAG |
| Retrieval evidence | `retrieval.documents` plus `document.*` | MUST be used on `RETRIEVER` spans |
| LLM calls | `llm.*` (provider, model, invocation parameters, tokens) | MUST be used on explicit `LLM` spans |
| Tags | `tag.tags` | MAY be used for slicing traces (agent variant, experiment id) |

### 3.2 YAAM namespacing rule

YAAM-specific attributes MUST be namespaced as `yaam.*`. Examples include:

1. `yaam.turn_id`
2. `yaam.agent_type`
3. `yaam.agent_variant`
4. `yaam.memory.weights`
5. `yaam.ciar.threshold`

OpenInference keys SHOULD be preferred over YAAM-specific alternatives when both exist.

## 4. Span inventory and required attributes

This section defines the required spans for a single YAAM request.

### 4.1 Span table

| Span name (stable) | Kind | Owner (code point) | Parent | Required attributes | Notes |
|---|---|---|---|---|---|
| `yaam.api_wall.chat_completions` | `CHAIN` | `src/server.py:create_app()->chat_completions` | Trace root | `openinference.span.kind`, `session.id`, `yaam.turn_id`, `yaam.agent_type`, `yaam.agent_variant`, `yaam.configured_model` | Root span remains API-wall owned by ADR-013 |
| `yaam.agent.run_turn` | `AGENT` | `src/agents/*:run_turn` | `yaam.api_wall.chat_completions` | `openinference.span.kind`, `session.id`, `input.value`, `output.value`, `yaam.turn_id`, `tag.tags` | `input.value` is user message; `output.value` is final assistant response |
| `yaam.workflow.perceive` | `CHAIN` | `src/agents/*` | `yaam.agent.run_turn` | `openinference.span.kind`, `graph.node.*`, `session.id` | Use when a stable phase exists |
| `yaam.workflow.retrieve` | `CHAIN` | `src/agents/*` | `yaam.agent.run_turn` | `openinference.span.kind`, `graph.node.*`, `session.id` | Parent for tier retrievers |
| `yaam.retriever.l1` | `RETRIEVER` | `src/memory/unified_memory_system.py:get_context_block` | `yaam.workflow.retrieve` | `openinference.span.kind`, `session.id`, `retrieval.documents` | L1 documents represent turns or context window elements |
| `yaam.retriever.l2` | `RETRIEVER` | `src/memory/unified_memory_system.py:get_context_block` and `query_memory` | `yaam.workflow.retrieve` | `openinference.span.kind`, `session.id`, `retrieval.documents` | L2 documents represent facts with CIAR-related metadata |
| `yaam.retriever.l3` | `RETRIEVER` | `src/memory/unified_memory_system.py:query_memory` | `yaam.workflow.retrieve` | `openinference.span.kind`, `session.id`, `retrieval.documents` | L3 documents represent episode summaries or episodic chunks |
| `yaam.retriever.l4` | `RETRIEVER` | `src/memory/unified_memory_system.py:query_memory` | `yaam.workflow.retrieve` | `openinference.span.kind`, `session.id`, `retrieval.documents` | L4 documents represent semantic knowledge documents |
| `yaam.workflow.reason` | `CHAIN` | `src/agents/*` | `yaam.agent.run_turn` | `openinference.span.kind`, `graph.node.*`, `session.id` | Parent for response LLM call(s) |
| `yaam.llm.respond` | `LLM` | `src/llm/client.py:LLMClient.generate` | `yaam.workflow.reason` | `openinference.span.kind`, `session.id`, `llm.provider`, `llm.model_name`, `llm.invocation_parameters`, `llm.token_count.*` | Prefer provider auto-instrumentation; this span is an explicit fallback |
| `yaam.workflow.update` | `CHAIN` | `src/agents/*` | `yaam.agent.run_turn` | `openinference.span.kind`, `graph.node.*`, `session.id` | Parent for memory writes and lifecycle |
| `yaam.lifecycle.promotion` | `CHAIN` | `src/memory/unified_memory_system.py:run_promotion_cycle` | `yaam.workflow.update` | `openinference.span.kind`, `session.id`, `yaam.ciar.threshold`, `yaam.lifecycle.result` | Use when promotion is synchronous under request |
| `yaam.lifecycle.consolidation` | `CHAIN` | `src/memory/unified_memory_system.py:run_consolidation_cycle` | `yaam.workflow.update` | `openinference.span.kind`, `session.id`, `yaam.lifecycle.result` | Use when consolidation is executed |
| `yaam.lifecycle.distillation` | `CHAIN` | `src/memory/unified_memory_system.py:run_distillation_cycle` | `yaam.workflow.update` | `openinference.span.kind`, `session.id`, `yaam.lifecycle.result` | Use when distillation is executed |
| `yaam.llm.ciar_score` | `LLM` | CIAR scorer module (planned) | `yaam.lifecycle.promotion` or `yaam.workflow.retrieve` | `openinference.span.kind`, `session.id`, `llm.*`, `output.value`, `yaam.ciar.threshold` | Output SHOULD be structured JSON for per-fact scores |
| `yaam.llm.fact_extract` | `LLM` | Fact extractor module (planned) | `yaam.lifecycle.promotion` | `openinference.span.kind`, `session.id`, `llm.*`, `output.value` | Output SHOULD be structured JSON of extracted facts |

### 4.2 Retrieval document schema (per tier)

Each `RETRIEVER` span MUST populate `retrieval.documents` with an ordered list. Each document entry
MUST include `document.id` and SHOULD include other fields as available.

| Field | Key | Requirement | Guidance |
|---|---|---|---|
| Document identifier | `document.id` | MUST | Recommended format: `<tier>:<native_id>` |
| Document content | `document.content` | SHOULD | Use content-capture policy (see §5) |
| Similarity or relevance score | `document.score` | SHOULD | `None` is permitted when no score exists |
| Metadata | `document.metadata` | SHOULD | JSON-serializable map (tier, timestamps, provenance) |

Tier guidance for `document.metadata`:

1. L1: `role`, `timestamp`, `turn_id`, `window_index`
2. L2: `ciar_score`, `source_turn_ids`, `valid_from`, `valid_to`
3. L3: `episode_id`, `time_window`, `fact_count`, `provenance`
4. L4: `knowledge_id`, `source`, `version`, `provenance`

## 5. Content-capture and privacy modes

This contract assumes development and evaluation contexts where full capture can be acceptable, but
it defines three deployment modes that MUST be supported by future implementation.

| Mode | Prompts (`input.value`, `llm.input_messages`) | Retrieval (`document.content`) | Guidance |
|---|---|---|---|
| `full` | Captured | Captured | Use for development and controlled evaluation |
| `redacted` | Redacted | Redacted | Replace content with summaries or hashes and preserve metadata |
| `metadata_only` | Not captured | Not captured | Preserve only counts, ids, and scores |

The mode MUST be applied consistently across YAAM spans within a trace.

## 6. Code attachment map (non-mechanism)

This section defines the intended attachment points in the YAAM codebase. It is normative for
where spans are created, but it does not prescribe implementation details.

| Component | File | Entry point | Expected spans |
|---|---|---|---|
| API wall | `src/server.py` | `create_app()->chat_completions` | Root span; session correlation; error capture |
| Agents | `src/agents/memory_agent.py` | `run_turn` and workflow nodes | `AGENT` span and workflow `CHAIN` spans |
| Agents | `src/agents/rag_agent.py` | `run_turn` and retrieval call sites | `AGENT`, `workflow.retrieve`, tier `RETRIEVER` spans |
| Memory system | `src/memory/unified_memory_system.py` | `query_memory`, `get_context_block` | Tier `RETRIEVER` spans; retrieval document schema |
| Lifecycle engines | `src/memory/engines/*` | `process` or system entrypoints | Lifecycle spans and explicit LLM spans when LLM modules run |
| LLM client | `src/llm/client.py` | `LLMClient.generate` | Provider/model attribution; explicit `LLM` spans if needed |

## 7. Verification checklist

An implementation conforms to this contract only if all statements below are true:

1. Each request trace contains an API wall root span with `session.id` and `openinference.span.kind`.
2. Each agent execution contains an `AGENT` span with `input.value` and `output.value` (subject to §5 mode).
3. Each retrieval operation produces tier `RETRIEVER` spans with `retrieval.documents` populated.
4. At least one lifecycle operation is visible as a semantic span under `workflow.update` when it occurs synchronously.
5. Explicit LLM modules (CIAR scoring, fact extraction) produce dedicated `LLM` spans or equivalent OpenInference-compatible spans.
