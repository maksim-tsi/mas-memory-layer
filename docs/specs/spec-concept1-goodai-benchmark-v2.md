This plan is **APPROVED** with one critical technical addition to ensure scientific validity.
# Detailed Implementation Spec: GoodAI-LTM Benchmark v2

**Goal:** Build the "Referee" system capable of running A/B tests.
**Target Files:** `scripts/run_benchmark_v2.py`, `src/benchmark/runner.py`, `src/reporting/comparator.py`

## 1. CLI & Entry Point (`scripts/run_benchmark_v2.py`)

This script replaces the old `run_benchmark.py`. It acts as the orchestrator, not the worker.

### 1.1 Arguments (Argparse)

* `--agent-config` (Required): Path to the primary agent's YAML (e.g., `configs/agent_a.yaml`).
* `--compare-with` (Optional): Path to the challenger agent's YAML. If present, triggers "Match Mode".
* `--dataset-config` (Optional): Path to dataset generation config.
* `--overrides` (Optional, repeatable): Key-value pairs to patch YAMLs (e.g., `agent.context_size=8000`).
* `--output-dir`: Where to save the `comparison_report.html`.

### 1.2 Orchestration Logic

```python
def main():
    args = parse_args()
    
    # 1. Prepare the Arena (Dataset)
    # Generate the dataset ONCE so both agents face the exact same tokens.
    dataset_path = dataset_manager.generate_temp_dataset(args.dataset_config)
    
    # 2. Run Agent A (The Champion)
    results_a = run_subprocess(
        agent_config=args.agent_config,
        dataset_path=dataset_path,
        overrides=args.overrides
    )
    
    if args.compare_with:
        # 3. Run Agent B (The Challenger)
        # Clean the environment (Docker/Process kill) before starting
        results_b = run_subprocess(
            agent_config=args.compare_with,
            dataset_path=dataset_path,  # SAME path
            overrides=args.overrides
        )
        
        # 4. Generate Comparative Report
        generate_comparison_report(results_a, results_b, args.output_dir)
    else:
        # Standard Single Run Report
        generate_single_report(results_a, args.output_dir)

```

---

## 2. The Worker Process (`src/benchmark/runner.py`)

This class runs inside the subprocess. It executes the actual conversation loop.

### 2.1 Metadata Sanitizer (FR-02.3)

We need a safety wrapper around the agent's response to prevent 100MB logs.

```python
class MetadataSanitizer:
    MAX_BYTES = 50 * 1024  # 50KB limit

    @staticmethod
    def sanitize(metadata: dict) -> dict:
        import json
        payload = json.dumps(metadata)
        if len(payload) > MetadataSanitizer.MAX_BYTES:
            return {
                "error": "Metadata exceeded 50KB limit",
                "truncated_keys": list(metadata.keys())
            }
        return metadata

```

### 2.2 Updated Interaction Loop

The runner must now accept the tuple return type `(str, dict)`.

```python
# In LtmBenchmark.user_turn()
response_payload = agent.reply(user_message)

if isinstance(response_payload, tuple):
    answer_text, raw_metadata = response_payload
    safe_metadata = MetadataSanitizer.sanitize(raw_metadata)
else:
    answer_text = response_payload
    safe_metadata = {}

# Save to log
self.interaction_log.append({
    "turn": i,
    "user": user_message,
    "agent": answer_text,
    "metadata": safe_metadata  # Saved alongside text
})

```

---

## 3. The Analytics Engine (`src/reporting/comparator.py`)

This module generates the HTML report.

### 3.1 Data Structure

We need a normalized structure to compare runs.

```python
class RunMetrics(BaseModel):
    agent_name: str
    total_score: float
    avg_latency_ms: float
    token_cost: float
    metadata_events: int

class MatchResult(BaseModel):
    champion: RunMetrics
    challenger: RunMetrics
    dataset_id: str

```

### 3.2 Visualization (HTML Template)

Use a Jinja2 template for the dashboard.

* **Radar Chart:** Use `Chart.js` (CDN) to plot the normalized metrics.
* *Axes:* Accuracy (Score), Speed (1/Latency), Efficiency (1/Tokens).


* **Turn-by-Turn Accordion:**
* *Row:* Turn #1 | User Question
* *Col A:* Agent A Answer (Green/Red bg based on correctness)
* *Col B:* Agent B Answer
* *Expandable Details:* Click to reveal the `metadata` JSON tree (e.g., "Reasoning Trace" or "Memory Hits").



---
