# ADR-013: Phoenix Tracing Strategy for YAAM and Benchmark Observability

**Status:** Proposed  
**Date:** March 10, 2026  
**Related:** [ADR-003](003-four-layers-memory.md), [ADR-007](007-agent-integration-layer.md), [ADR-009](009-decoupling-benchmark-api-wall.md), [ADR-010](010-mechanism-policy-split-and-skills-v1.md), [RFC: Arize Phoenix Tracing for YAAM Glass-Box Observability](../RFC/phoenix-tracing-rfc.md), [Spec: Phoenix span contract](../specs/observability/phoenix-span-contract.md)

## 1. Context

YAAM already contains a functional Arize Phoenix integration at the request boundary. Phoenix initialization is implemented in [src/llm/client.py](../../src/llm/client.py), and request-level tracing is implemented in [src/server.py](../../src/server.py). Live March 2026 validation demonstrated that API Wall requests for Gemini, Groq, and Mistral appear in Phoenix and that benchmark artifacts preserve `yaam_trace_id` and `yaam_span_id` for trace correlation.

This existing capability is necessary but not sufficient for YAAM's observability objectives. The current trace model primarily exposes request envelopes, provider metadata, and aggregate timing. It does not yet expose the internal memory operations that motivate YAAM architecture, including retrieval from L1-L4, CIAR-informed memory selection, and lifecycle transitions across tiers.

At the same time, [ADR-010](010-mechanism-policy-split-and-skills-v1.md) constrains the repository to avoid unnecessary changes in the mechanism layer under [src/storage](../../src/storage). Therefore, any tracing strategy must improve cognitive observability without introducing architectural drift into storage adapters.

## 2. Decision

We will standardize YAAM tracing on **Arize Phoenix with OpenInference semantic conventions** and treat it as the primary tracing substrate for both YAAM request execution and benchmark correlation.

The normative span inventory, required attributes, and code attachment points are defined in
[Spec: Phoenix span contract](../specs/observability/phoenix-span-contract.md).

### 2.1 Root span ownership

The API Wall will remain the canonical owner of request root spans.

This preserves the decoupled architecture established in [ADR-009](009-decoupling-benchmark-api-wall.md), in which benchmark execution and YAAM request serving remain separated by an HTTP boundary.

### 2.2 Semantic span strategy

Future tracing expansion will use OpenInference-aligned semantic spans above the storage mechanism layer.

The target span model is:

1. request root span at the API Wall,
2. chain or agent spans for YAAM workflow phases,
3. retriever spans for memory access across L1-L4,
4. LLM spans for model invocations,
5. and lifecycle spans for promotion, consolidation, and distillation where applicable.

### 2.3 Benchmark correlation strategy

Evaluation harness integrations (including the GoodAI benchmark while it remains in-repository) will
continue preserving current `yaam_*` correlation metadata while the project incrementally adds
stronger session and metadata alignment with OpenInference conventions.

Harness-owned tracing enhancements should occur at the harness or API boundary, not by collapsing
the current HTTP separation. The repository's primary long-term objective is YAAM runtime
observability; evaluation harness visibility is considered a transitional development concern.

### 2.4 Implementation boundary

Initial tracing enhancements will occur in:

1. [src/server.py](../../src/server.py),
2. [src/agents](../../src/agents),
3. [src/memory/unified_memory_system.py](../../src/memory/unified_memory_system.py),
4. [src/memory/tiers](../../src/memory/tiers),
5. and [src/memory/engines](../../src/memory/engines).

Initial phases will not require changes to [src/storage](../../src/storage) unless later evidence demonstrates that higher-level instrumentation is insufficient and explicit authorization is provided.

## 3. Consequences

### Positive

1. YAAM tracing becomes aligned with an established observability standard rather than remaining a repository-specific set of metrics and metadata fields.
2. Phoenix can evolve from a request-level debugging tool into a genuine cognitive observability surface for YAAM.
3. Evaluation failures become easier to diagnose because harness artifacts and Phoenix traces can be correlated systematically.
4. The project gains stronger evidence for architectural claims related to retrieval, memory layering, and lifecycle processing.

### Negative

1. Richer tracing will increase schema complexity and requires disciplined metadata design.
2. Retrieving and recording prompt or document content raises privacy and redaction concerns that must be governed explicitly.
3. Poorly scoped instrumentation could add runtime overhead or produce low-value trace noise.

### Neutral

1. Existing JSONL metrics and internal telemetry remain valuable and should not be assumed to be replaced entirely by Phoenix.
2. The repository will need to maintain backward compatibility for current `yaam_*` metadata during the transition to more OpenInference-aligned attributes.

## 4. Implementation Plan

1. Harden and normalize the existing request-level tracing and provider metadata contract.
2. Add YAAM workflow and retriever spans above the storage mechanism boundary.
3. Add lifecycle spans for promotion, consolidation, and distillation.
4. Add benchmark-owned spans and richer benchmark metadata only after the YAAM trace graph is semantically meaningful.
5. Define and apply a privacy policy for prompt and retrieved-content capture before broader deployment.

## 5. Alternatives Considered

### Alternative A: Retain API-Wall-only tracing

**Pros**: Minimal effort, already validated, low conceptual risk.  
**Cons**: Does not satisfy the requirement for memory-aware and lifecycle-aware observability.  
**Why rejected**: It preserves a shallow trace model and leaves the core YAAM architecture largely invisible in Phoenix.

### Alternative B: Instrument only the benchmark harness

**Pros**: Strong benchmark metadata and direct run-level visibility.  
**Cons**: Still fails to expose internal YAAM cognition and risks moving observability emphasis away from the true execution boundary.  
**Why rejected**: YAAM observability must be rooted in YAAM execution, not only in benchmark orchestration.

### Alternative C: Add tracing primarily in `src/storage/`

**Pros**: Fine-grained adapter-level visibility.  
**Cons**: Conflicts with frozen-by-default mechanism policy and risks architectural drift.  
**Why rejected**: Higher-level memory and agent instrumentation should be attempted first because it aligns better with OpenInference semantics and repository governance.
