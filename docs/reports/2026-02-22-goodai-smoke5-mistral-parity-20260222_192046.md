# Report: GoodAI LTM Benchmark (Agent Variant, Mistral Routing)

**Date:** 2026-02-22  
**YAAM Commit:** `12dd97b59676fa3689052ec5a7e35bb0f469a483`  
**Benchmark Commit/Version:** `12dd97b59676fa3689052ec5a7e35bb0f469a483`  
**Agent Type:** `full`  
**Agent Variant:** `v1-min-skillwiring`  
**Agent ID:** `mas-full__v1-min-skillwiring`  
**Run Name:** `goodai__smoke5__provider=mistral__model=mistral-large__promotion=disabled__agent=full__v1-min-skillwiring__20260222_192046`  

## 1. Executive Summary

Smoke5 completed successfully with Mistral routing. The run produced complete artifacts (master log, turn metrics, run stats, and HTML report). Two deviations appeared: Restaurant scored 0.2/1 (rubric mismatch around drink ordering), and Trigger Response scored 0.667/1 due to a missed trigger response on a later turn. Other datasets scored 1.0/1.0. Results appear repeatable given stable runtime and clean exit.

## 2. Run Configuration (Reproducibility)

### 2.1 Topology

- Host: MacBook (local)
- Redis: `skz-dev-lv` via SSH tunnel to `localhost:6379`
- Postgres: via `POSTGRES_URL` from root `.env` (redacted)
- API Wall: `uvicorn` on `http://127.0.0.1:8081`
- GoodAI runner venv: `benchmarks/goodai-ltm-benchmark/.venv`

### 2.2 Endpoints

- `AGENT_URL`: `http://127.0.0.1:8081/v1/chat/completions`
- `YAAM /health`: `http://127.0.0.1:8081/health`

### 2.3 Environment Variables (YAAM)

| Variable | Value |
|---|---|
| `MAS_AGENT_TYPE` | `full` |
| `MAS_AGENT_VARIANT` | `v1-min-skillwiring` |
| `MAS_MODEL` | `mistral-large` |
| `MAS_PROMOTION_MODE` | `disabled` |
| `MAS_PROMOTION_TIMEOUT_S` | *(default 30s; unused because promotion disabled)* |
| `MAS_FACT_EXTRACTOR_MODEL` | *(defaulted to `MAS_MODEL`)* |
| `MAS_TOPIC_SEGMENTER_MODEL` | *(defaulted to `MAS_MODEL`)* |
| `MAS_MIN_CIAR` | *(default)* |
| `MAS_L1_WINDOW` | *(default)* |
| `MAS_L1_TTL_HOURS` | *(default)* |
| `REDIS_URL` | `redis://localhost:6379` |
| `POSTGRES_URL` | *(redacted host ok)* |

### 2.4 Provider Configuration (Mistral)

- Provider(s) enabled: `mistral`
- Mistral model: `mistral-large`
- Promotion: `disabled` (Smoke5 default; `skip_l1_write` remained true)

### 2.5 LLM-Engine Routing (Critical for Attribution)

Promotion engines were not exercised because `skip_l1_write=true` for API Wall requests. FactExtractor and TopicSegmenter therefore did not run during this benchmark. Their default models are documented above for parity tracking.

## 3. Results

### 3.1 Aggregate Scores

| Dataset | Metric | Score | Notes |
|---|---:|---:|---|
| Instruction Recall | accuracy | 1.0 | Pass |
| Prospective Memory | accuracy | 1.0 | Pass |
| Restaurant | accuracy | 0.2 | Rubric penalized drink ordering |
| Spy Meeting | accuracy | 1.0 | Pass |
| Trigger Response | accuracy | 0.667 | Missed trigger on third attempt |

### 3.2 Performance

| Metric | Value |
|---|---:|
| Turns processed | 100 |
| Duration (s) | 151.26 |
| Total tokens | 29,527 |
| Agent tokens | 4,594 |
| Median `llm_ms` | 3,619.45 |
| P95 `llm_ms` | 9,880.83 |
| P99 `llm_ms` | 31,138.98 |
| Median `storage_ms` | 73.59 |
| P95 `storage_ms` | 86.49 |
| P99 `storage_ms` | 97.90 |

### 3.3 Error Taxonomy (Observed)

| Category | Count | Example symptom | Likely cause |
|---|---:|---|---|
| Reasoning failure (retrieval-reasoning gap) | 1 | Trigger Response missed on later turn | Instruction-following instability |
| Evaluation rubric mismatch | 1 | Restaurant task penalized drink order | Dataset rubric expectation mismatch |
| Infrastructure/network | 0 | n/a | n/a |

## 4. Visibility/Transparency Matrix (Artifact-Based)

| Component | What to verify | Where to observe | Pass/Fail | Notes |
|---|---|---|---|---|
| Session isolation | prefixed session IDs | `master_log.jsonl` metadata `yaam_session_id` | Pass | Prefix visible |
| LLM traceability | provider+model per turn | `master_log.jsonl` metadata `llm_provider`, `llm_model` | Pass | Mistral attribution |
| Timing transparency | storage vs LLM timings | `master_log.jsonl`, `turn_metrics.jsonl` | Pass | `llm_ms`, `storage_ms` present |
| Memory writes | L1/L2 write behavior | response metadata `skip_l1_write` | Pass (expected) | Writes suppressed in Smoke5 |
| Report generation | HTML present | `data/reports/` | Pass | HTML generated |

## 5. Artifacts and Logs

- Raw benchmark outputs: `benchmarks/goodai-ltm-benchmark/data/tests/goodai__smoke5__provider=mistral__model=mistral-large__promotion=disabled__agent=full__v1-min-skillwiring__20260222_192046/results/RemoteMASAgentSession - remote/`
- GoodAI console log: `benchmarks/goodai-ltm-benchmark/data/tests/goodai__smoke5__provider=mistral__model=mistral-large__promotion=disabled__agent=full__v1-min-skillwiring__20260222_192046/results/RemoteMASAgentSession - remote/run_console.log`
- GoodAI master log: `benchmarks/goodai-ltm-benchmark/data/tests/goodai__smoke5__provider=mistral__model=mistral-large__promotion=disabled__agent=full__v1-min-skillwiring__20260222_192046/results/RemoteMASAgentSession - remote/master_log.jsonl`
- GoodAI per-turn metrics: `benchmarks/goodai-ltm-benchmark/data/tests/goodai__smoke5__provider=mistral__model=mistral-large__promotion=disabled__agent=full__v1-min-skillwiring__20260222_192046/results/RemoteMASAgentSession - remote/turn_metrics.jsonl`
- GoodAI run stats: `benchmarks/goodai-ltm-benchmark/data/tests/goodai__smoke5__provider=mistral__model=mistral-large__promotion=disabled__agent=full__v1-min-skillwiring__20260222_192046/results/RemoteMASAgentSession - remote/runstats.json`
- Per-dataset JSON: `.../Instruction Recall/0_0.json`, `.../Prospective Memory/0_0.json`, `.../Restaurant/0_0.json`, `.../Spy Meeting/0_0.json`, `.../Trigger Response/0_0.json`
- YAAM rate limiter JSONL: `logs/rate_limiter_full_v1-min-skillwiring_20260222_171940.jsonl`
- HTML report: `benchmarks/goodai-ltm-benchmark/data/reports/2026-02-22 19_26_58 - Detailed Report - goodai__smoke5__provider=mistral__model=mistral-large__promotion=disabled__agent=full__v1-min-skillwiring__20260222_192046 - RemoteMASAgentSession - remote.html`

## 6. Proposed Next Steps

1. **Comparative summary:** Produce a cross-provider summary report for Groq/Gemini/Mistral parity runs.
2. **Promotion validation:** Execute memory-engine validation runs with `skip_l1_write=false` and `MAS_PROMOTION_MODE=async` then `barrier`, verifying promotion metadata in artifacts.
3. **Failure analysis:** Inspect `master_log.jsonl` entries for Trigger Response and Restaurant to confirm root cause and determine whether policy-layer adjustments are needed.
