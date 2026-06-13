# ADR-008: Adoption of GoodAI-LTM Benchmark v2 and MAS Memory Inspector

**Title:** Strategic Adoption of Comparative Benchmarking Platform and "Glass Box" Observability
**Status:** Accepted
**Date:** February 7, 2026

## 1. Context

The project's initial goal was to prove the efficacy of the MAS Memory Layer. However, the current evaluation methods are manual, opaque, and lack the rigorous "scientific" validation required for the AIMS'25 paper.

Two specific gaps have been identified:
1.  **Evaluation Rigor:** The existing benchmark tools are "naive" runners. We lack a neutral "Arena" that can fairly compare our system against baselines (e.g., standard RAG, vanilla GPT-4) with identical constraints and distraction datasets.
2.  **Internal Validation:** While we claim our system performs "Cognitive Significance Analysis" and "Tiered Storage," we currently have no way to *prove* this is happening during a run. The internal state is a "Black Box," making it difficult to debug or demonstrate to reviewers.

## 2. Decision

We will adopt and implement two new architectural components as defined in `docs/concept-01-benchmark-v2.md` and `docs/concept-02-memory-inspector.md`.

### Component 1: GoodAI-LTM Benchmark v2 (The Referee)
We will refactor the existing CLI tool into a **Comparative Evaluation Platform** that supports:
*   **A/B Scenario Testing:** Running two agent configurations sequentially on the same dataset.
*   **Variable Injection:** Overriding agent parameters (e.g., `memory_window`, `rag_enabled`) via CLI.
*   **Universal Metadata:** Capturing arbitrary debug data from agents without the benchmark needing to understand the schema.

### Component 2: MAS Memory Inspector (The Candidate)
We will instrument the `GoodAIAgent` and the underlying `UnifiedMemorySystem` to emit **Cognitive Telemetry**:
*   **Real-time Event Stream:** Broadcasting "Significance Decisions" (CIAR scores), "Tier Hits/Misses," and "Scratchpad Updates."
*   **Visualizer Support:** Adding the frontend hooks to render this telemetry as a "Glass Box" view (Significance Heatmaps, Tier Lights).

## 3. Rationale

1.  **Scientific Integrity:** By separating the "Judge" (Benchmark v2) from the "Contestant" (Inspector), we eliminate bias. The benchmark measures *outcomes* (Quality, Cost), while the Inspector proves *mechanism*.
2.  **Reviewer Satisfaction:** This directly addresses potential reviewer critique regarding "Black Box" systems. We can now show *why* the system performed better (e.g., "See, it ignored the distraction text here because CIAR score was 0.1").
3.  **Ablation Efficiency:** The "Scenario Builder" allows us to run ablation studies (System w/o L3 vs. System w/ L3) purely through configuration, without maintaining separate code branches.

## 4. Consequences

*   **Positive:**
    *   Enables the generation of the "Comparative Radar Charts" required for the paper's Results section.
    *   Provides a powerful debugging tool for developers (seeing the "brain scan" of the agent).
*   **Negative:**
    *   **Development Overhead:** Requires refactoring the `run_benchmark.py` runner and adding instrumentation decorators throughout the core memory system.
    *   **Performance Impact:** Telemetry emission might add slight overhead, though this can be disabled for production runs.

## 5. References

*   [Concept Document 1: GoodAI-LTM Benchmark v2](../concept-01-benchmark-v2.md)
*   [Concept Document 2: MAS Memory Inspector](../concept-02-memory-inspector.md)

## Status Update (2026-02-10)

The "Memory Inspector" Web UI component is revoked. We are adopting a Headless Microservices architecture.
Telemetry will be handled via standard log exporters (TypeSense/Phoenix), not a custom dashboard.
