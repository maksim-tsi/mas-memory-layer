# Requirements Document: GoodAI-LTM Benchmark v2

**Source Concept:** `docs/concept-01-benchmark-v2.md`
**Scope:** Transformation of the existing CLI benchmark tool into a comparative evaluation platform.

## 1. Functional Requirements (FR)

### FR-01: Scenario Configuration (The "Match Setup")
The system MUST allow users to define and execute comparative "matches" between two agent configurations.

*   **FR-01.1 (Sequential Execution):** The system shall support running two distinct agent configurations sequentially against the exact same dataset instance.
*   **FR-01.2 (Variable Injection - Namespaced):** The system shall accept CLI arguments that override specific values, strictly distinguishing between Agent and Benchmark params.
    *   *Agent Override:* `--agent-override <key>=<value>` (e.g., `enable_rag=True`)
    *   *Benchmark Override:* `--bench-override <key>=<value>` (e.g., `distraction_level=5`)
*   **FR-01.3 (Generator Parameters):** The system shall expose **Generator Parameters** (via `--bench-override`) in the configuration interface, allowing users to dynamically stress-test specific cognitive capabilities.

### FR-02: Universal Metadata Support
The system MUST be able to capture and store arbitrary debugging information from any agent without requiring schema changes to the benchmark runner.

*   **FR-02.1 (Data Ingestion):** The `LtmBenchmark` runner interface shall be updated to accept a return value of type `Tuple[str, Dict[str, Any]]` (Answer, Metadata), instead of just `str`.
*   **FR-02.2 (Data Persistence):** The system shall serialize the received Metadata JSON into the `results.json` output file alongside the graded answer.
*   **FR-02.3 (Metadata Constraints):** The system shall enforce a hard limit (e.g., 50KB) on the size of the Metadata payload per turn, truncating or rejecting excessive data to prevent reporting instability.

### FR-03: Comparative Analytics & Reporting
The system MUST generate reports that visualize the performance differences between the two entities in a match.

*   **FR-03.1 (Side-by-Side Visualization):** The reporting dashboard shall display metrics for "System A" and "System B" in adjacent columns or overlaid charts.
*   **FR-03.2 (Radar Chart):** The report shall generate a radar chart comparing available quantitative metrics: **Correctness Score** (Accuracy), **Response Duration** (Latency), and **Token Consumption** (Efficiency). *Optional:* If 'LLM-as-a-Judge' is enabled, include qualitative metrics like Coherence.
*   **FR-03.3 (Latency Analysis):** The report shall visualize response time distributions (e.g., via box plots) to highlight speed vs. accuracy trade-offs.
*   **FR-03.4 (Cost Tracking):** The report shall display a comparison of token usage/cost for the identical workload.

---

## 2. Non-Functional Requirements (NFR)

### NFR-01: Extensibility & Neutrality
*   **NFR-01.1:** The platform must remain agnostic to the internal architecture of the agents being tested. It must not rely on any MAS-specific libraries for the runner itself.
*   **NFR-01.2:** The Metadata visualization in the report must be generic (e.g., a collapsible JSON tree view) to support any future agent type (MemGPT, AutoGen) without UI code changes.

### NFR-02: Isolation & Fairness
*   **NFR-02.1:** The execution environment should ideally ensure that the memory/state of "System A" is fully cleared before "System B" begins (e.g., fresh process or container).
*   **NFR-02.2 (Process Hygiene):** To ensure NFR-02.1 (Isolation), the system shall support a **'Subprocess Mode'** where each agent run is spawned as a distinct OS process that is terminated and garbage-collected immediately after completion, preventing memory leaks from polluting subsequent runs.

### NFR-03: Usability
*   **NFR-03.1:** Configuration overrides should be intuitive and documented via `--help` in the CLI.
