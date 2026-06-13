# Requirements Document: MAS Memory Inspector

**Source Concept:**### 1. Core Philosophy: "Cognitive Telemetry"

The system must broadcast its internal state changes (Perception → Promotion → Storage) in real-time. Crucially, this requires the backend to **generate and capture reasoning** for every decision, transforming the current "Black Box" into a "Glass Box."

## 2. Prerequisites (Backend Refactoring)

Before the UI can be built, the underlying system must be patched to expose the "Invisible Brain."

### PR-01: Schema Updates (The "Reasoning" Field)
*   **PR-01.1:** The `Fact` and `TopicSegment` data models MUST be updated to include a `justification` field (type: `str | None`).
*   **PR-01.2:** This field shall store the LLM-generated explanation or the heuristic rule ID that triggered the promotion/demotion.

### PR-02: Explainability Injection
*   **PR-02.1:** The `FactExtraction` prompts MUST be modified to force the LLM to generate a 1-sentence `justification` for every extracted fact, explaining its significance.
*   **PR-02.2:** The `CIARScorer` should ideally log the components of its arithmetic calculation (`Certainty * Impact * Age`) to provide a mathematical breakdown of the score.

### PR-03: Telemetry Infrastructure
*   **PR-03.1:** A lightweight, non-blocking `AsyncCognitiveMonitor` (or `TelemetryStream`) class MUST be implemented using `asyncio.Queue` to decouple event generation from processing.

---

## 3. Functional Requirements (FR)

### FR-01: Cognitive Telemetry Stream
The system MUST emit a structured event stream that exposes the internal decision-making process.

*   **FR-01.1 (Significance Reporting):** The `PromotionEngine` shall emit a `CognitiveEvent` for every significance calculation.
    *   *Payload:* Input segment, CIAR score, Decision (PROMOTE/IGNORE), and **Justification (Reasoner Output)**.
*   **FR-01.2 (Tier Access Logging):** The system shall emit events detailing every read/write operation to the memory tiers (L1, L2, L3), including latency metrics and hit/miss status.
*   **FR-01.3 (Scratchpad Updates):** The system shall emit events whenever the agent updates its internal "scratchpad" or working memory.

### FR-02: Glass Box Visualization
The system MUST provide a frontend component to visualize the telemetry stream in real-time or post-hoc.

*   **FR-02.1 (Layer Activity Indicator):** The UI shall visually represent the activity of each memory tier (e.g., via color-coded indicators for L1/L2/L3) corresponding to the received telemetry events.
*   **FR-02.2 (Significance Heatmap):** The UI shall render the user's input text with color-coded highlighting based on the CIAR significance scores (e.g., red for high importance, gray for low).

### FR-03: Experimental Control (Ablation Toggles)
The system MUST support configuration flags to enable or disable specific cognitive features for ablation testing.

*   **FR-03.1 (Feature Flags):** The `UnifiedMemorySystem` constructor shall accept boolean flags (e.g., `enable_promotion`, `enable_l3`) to selectively turn off components without code changes.

---

## 2. Non-Functional Requirements (NFR)

### NFR-01: Performance & Overhead
*   **NFR-01.1:** The telemetry emission process must be non-blocking and strictly decoupled from the critical path of the agent's response generation to minimize latency impact.
*   **NFR-01.2:** The system must allow telemetry to be completely disabled in production environments to avoid unnecessary overhead.

### NFR-02: Standardization
*   **NFR-02.1:** All telemetry events must adhere to a strict schema (e.g., Pydantic models) to ensure consistent parsing by the visualization tool and the benchmark runner.

### NFR-03: Integration
*   **NFR-03.1:** The "Glass Box" UI component must be implementable as a standalone widget that can be embedded into the GoodAI Benchmark report or developed as a separate debugging tool.
