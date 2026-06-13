# Concept Document 1: GoodAI-LTM Benchmark v2 (The Evaluation Platform)

**Goal:** To evolve the existing CLI tool into a **Comparative Evaluation Platform** capable of assessing *any* long-term memory system (RAG, Agents, Native Context) against baseline metrics.

### 1. Core Philosophy: "The Arena"

The Benchmark UI should not care *how* the agent works. It cares about **Input (Context)**, **Output (Answer)**, **Resources (Time/Cost)**, and **Quality (Score)**.

### 2. Functional Requirements (New Capabilities)

#### **Feature A: The "Scenario Builder" (Configuration)**

Instead of editing YAML files manually, the UI provides a "Match Setup" screen.

* **Agent A vs. Agent B:** Allow defining two configurations to run sequentially on the same dataset.
    * *Example:* "Run 1: GPT-4o (Naive)" vs. "Run 2: MAS Memory Layer (Full Stack)".
* **Variable Injection:** The UI passes configuration flags to the runner via CLI arguments, overriding the static YAML.
    * *Capabilities:* `enable_rag=True/False`, `memory_window_size=N`.
* **Dataset Selection:** Dropdown to select "Distraction Heavy" vs. "Recall Heavy" datasets (crucial for your implementation guide's "Pitfall 1" check).

#### **Feature B: Universal Metadata Handling**

The benchmark must be able to receive and store *arbitrary* JSON metadata from the agent alongside the text answer, without understanding what it is.

* **Mechanism:** The `LtmBenchmark` runner currently expects a string. It must be updated to accept a tuple: `(Answer_String, Metadata_JSON)`.
* **Storage:** This metadata is saved to `results.json` but not graded.
* **Visualization:** In the report, this metadata is rendered as a collapsible "Agent Details" JSON tree. This allows *any* system (MemGPT, MAS) to attach debug info without changing the benchmark code.

#### **Feature C: Comparative Analytics Dashboard**

A new Reporting View that compares two runs side-by-side.

* **Radar Chart:** Overlaying "Accuracy", "Coherence", and "Context Recall" for System A vs. System B.
* **Latency Box-Plot:** Comparing response time distribution. (e.g., "MAS Memory is 200ms slower on average but has 40% higher accuracy").
* **Cost Analysis:** Token usage comparison.

### 3. Technical Implementation Strategy

* **Refactor `run_benchmark.py`:** Use `argparse` to accept overrides for agent parameters (currently missing).
* **Containerization (Optional but Recommended):** To treat systems fairly, eventually run agents in Docker containers so "System A" doesn't pollute the RAM for "System B".
