# Report: GoodAI LTM Benchmark (Agent Variant)

**Date:** YYYY-MM-DD  
**YAAM Commit:** `<git sha>`  
**Benchmark Commit/Version:** `<git sha or tag>`  
**Agent Type:** `<full|rag|full_context>`  
**Agent Variant:** `<v1-min-skillwiring|v2-adv-toolgated|...>`  
**Agent ID:** `mas-<agent_type>__<agent_variant>`  

## 1. Executive Summary

Provide a short, factual summary:

- score delta(s) versus baseline,
- notable failure modes,
- and whether results are repeatable.

## 2. Run Configuration (Reproducibility)

### 2.1 Endpoints

- `AGENT_URL`: `http://<host>:<port>/v1/chat/completions`
- `YAAM /health`: `http://<host>:<port>/health`

### 2.2 Environment Variables (YAAM)

| Variable | Value |
|---|---|
| `MAS_AGENT_TYPE` | |
| `MAS_AGENT_VARIANT` | |
| `MAS_MODEL` | |
| `MAS_PROMOTION_MODE` | |
| `MAS_PROMOTION_TIMEOUT_S` | |
| `MAS_FACT_EXTRACTOR_MODEL` | |
| `MAS_TOPIC_SEGMENTER_MODEL` | |
| `MAS_MIN_CIAR` | |
| `MAS_L1_WINDOW` | |
| `MAS_L1_TTL_HOURS` | |
| `REDIS_URL` | *(redacted host ok)* |
| `POSTGRES_URL` | *(redacted host ok)* |

### 2.3 Provider Configuration

- Provider(s): `<gemini|groq|mistral|...>`
- Temperature / max output tokens: `<...>`
- Rate limiting policy: `<rpm/tpm/min_delay>`

## 3. Results

### 3.1 Aggregate Scores

| Dataset | Metric | Score | Notes |
|---|---:|---:|---|
| | | | |

### 3.2 Performance

| Metric | Value |
|---|---:|
| Turns processed | |
| Median latency (ms) | |
| P95 latency (ms) | |
| Estimated prompt tokens (total) | |
| Estimated completion tokens (total) | |

### 3.3 Error Taxonomy

| Category | Count | Example symptom | Likely cause |
|---|---:|---|---|
| Retrieval failure | | | |
| Reasoning failure (retrieval-reasoning gap) | | | |
| Tool misuse | | | |
| Infrastructure/network | | | |

### 3.4 Variant A (`v1-min-skillwiring`) Skill Aggregation

Use API Wall response metadata (`skill_slug`, `allowed_tools`, `gated_tool_names`,
`storage_ms_pre`, `llm_ms`, `storage_ms_post`) to aggregate per-skill behavior.

| skill_slug | Turns | Share of turns (%) | Avg score contribution | Notes |
|---|---:|---:|---:|---|
| `skill-selection` | | | | |
| `context-block-retrieval` | | | | |
| `l2-fact-lookup` | | | | |
| `l3-similar-episodes` | | | | |
| `l3-graph-templates` | | | | |
| `l4-knowledge-synthesis` | | | | |
| `ciar-scoring-and-promotion` | | | | |
| `retrieval-reasoning-gap-mitigation` | | | | |
| `knowledge-lifecycle-distillation` | | | | |

### 3.5 Variant A Skill-Level Latency and Cost

| skill_slug | Median `llm_ms` | P95 `llm_ms` | Median `storage_ms` | Prompt tokens (total) | Completion tokens (total) |
|---|---:|---:|---:|---:|---:|
| | | | | | |

### 3.6 Variant A Skill-Level Error Distribution

| skill_slug | Retrieval failures | Reasoning failures | Tool misuse | Infrastructure/network | Dominant failure mode |
|---|---:|---:|---:|---:|---|
| | | | | | |

## 4. Qualitative Analysis

Summarize representative failure cases and why they occurred. For each case:

- quote the minimal evidence (turn IDs, short snippets),
- identify the skill(s) that should have applied,
- and propose a minimal remediation hypothesis.

## 5. Artifacts and Logs

- Raw benchmark outputs: `<path or URL>`
- Wrapper logs: `<path>`
- Rate limiter JSONL: `logs/rate_limiter_<agent_type>_<agent_variant>_<timestamp>.jsonl`
- API Wall responses/trace extract for skill aggregation: `<path to parsed response metadata>`
- GoodAI per-run console log: `<bench_run_path>/run_console.log`
- GoodAI stuck watchdog error (if present): `<bench_run_path>/run_error.json`
- GoodAI per-turn metrics (if enabled): `<bench_run_path>/turn_metrics.jsonl`

## 6. Conclusions and Next Actions

- What changed relative to the previous variant?
- What should be tested next (unit/integration/benchmark)?
- What is explicitly out of scope for the next iteration?
