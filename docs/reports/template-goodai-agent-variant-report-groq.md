# Report: GoodAI LTM Benchmark (Agent Variant, Groq Routing)

**Date:** YYYY-MM-DD  
**YAAM Commit:** `<git sha>`  
**Benchmark Commit/Version:** `<git sha or tag>`  
**Agent Type:** `<full|rag|full_context>`  
**Agent Variant:** `<v1-min-skillwiring|v2-adv-toolgated|...>`  
**Agent ID:** `mas-<agent_type>__<agent_variant>`  

## 1. Executive Summary

Provide a short, factual summary:

- aggregate score outcomes and deltas versus the last comparable run,
- the primary failure modes (task logic vs infrastructure/provider issues),
- and whether the results appear repeatable.

## 2. Run Configuration (Reproducibility)

### 2.1 Topology

- Host: `<MacBook|...>`
- Redis: `<remote host>` tunneled to `localhost:<tunnel_port>`
- Postgres: via `POSTGRES_URL` from root `.env` (redacted)
- API Wall: `uvicorn` on `http://127.0.0.1:<mas_port>`
- GoodAI runner venv: `benchmarks/goodai-ltm-benchmark/.venv`

### 2.2 Endpoints

- `AGENT_URL`: `http://127.0.0.1:<mas_port>/v1/chat/completions`
- `YAAM /health`: `http://127.0.0.1:<mas_port>/health`

### 2.3 Environment Variables (YAAM)

| Variable | Value |
|---|---|
| `MAS_AGENT_TYPE` | |
| `MAS_AGENT_VARIANT` | |
| `MAS_MODEL` | `openai/gpt-oss-120b` |
| `MAS_MIN_CIAR` | |
| `MAS_L1_WINDOW` | |
| `MAS_L1_TTL_HOURS` | |
| `REDIS_URL` | `redis://localhost:<tunnel_port>` *(redacted host ok)* |
| `POSTGRES_URL` | *(redacted host ok)* |

### 2.4 Provider Configuration (Groq)

- Provider(s) enabled: `<groq (+ optional gemini for engines)>`
- Groq model: `openai/gpt-oss-120b`
- Temperature / max output tokens: `<...>`
- Rate limiting policy (YAAM): `<rpm/tpm/min_delay>`

### 2.5 LLM-Engine Routing (Critical for Attribution)

For this run, state explicitly which provider/model was used for each subsystem:

| Subsystem | Provider | Model | Evidence |
|---|---|---|---|
| Agent main generation | | | `<artifact path / log snippet>` |
| FactExtractor | | | `<artifact path / log snippet>` |
| TopicSegmenter | | | `<artifact path / log snippet>` |

If FactExtractor/TopicSegmenter were permitted to use Gemini, document the rationale (e.g., structured output compatibility) and the paid-tier key status (present/absent), without disclosing key values.

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
| Provider quota/rate limit | | | |
| Provider/model mismatch | | | |
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

### 3.5 Skill-Level Latency and Tokens

| skill_slug | Median `llm_ms` | P95 `llm_ms` | Median `storage_ms` | Prompt tokens (total) | Completion tokens (total) |
|---|---:|---:|---:|---:|---:|
| | | | | | |

### 3.6 Skill-Level Error Distribution

| skill_slug | Retrieval failures | Reasoning failures | Tool misuse | Infrastructure/network | Dominant failure mode |
|---|---:|---:|---:|---:|---|
| | | | | | |

## 4. Visibility/Transparency Matrix

Fill this table using **only artifacts** produced by the run.

| Component | What to verify | Where to observe | Pass/Fail | Notes |
|---|---|---|---|---|
| SSH tunnel | stable tunnel | terminal transcript; tunnel port evidence |  |  |
| API Wall health | status/variant/provider list | `/health` JSON artifact |  |  |
| Session isolation | prefixed session IDs include agent type+variant | benchmark logs + YAAM logs |  |  |
| Skill behavior | no planner leakage | `master_log.jsonl`, `run_console.log` |  |  |
| LLM traceability | provider+model identifiable per turn | response metadata/logs |  |  |
| Timing transparency | storage vs LLM timings per turn | response metadata; metrics JSONL |  |  |
| Memory writes | L1/L2 write behavior observable | YAAM memory state / logs |  |  |
| Report generation | HTML generated + exit code 0 | runner output + `data/reports/` |  |  |

## 5. Qualitative Analysis

Summarize representative failure cases and why they occurred. For each case:

- quote minimal evidence (turn IDs; short snippets),
- identify the skill(s) that should have applied,
- and propose a minimal remediation hypothesis.

## 6. Artifacts and Logs

- Raw benchmark outputs: `<benchmarks/goodai-ltm-benchmark/data/tests/<run_name>/results/RemoteMASAgentSession - remote/>`
- GoodAI console log: `<.../run_console.log>`
- GoodAI master log: `<.../master_log.jsonl>`
- GoodAI per-turn metrics: `<.../turn_metrics.jsonl>`
- GoodAI run stats: `<.../runstats.json>`
- Per-dataset JSON: `<.../<Dataset>/0_0.json>`
- YAAM rate limiter JSONL: `logs/rate_limiter_<agent_type>_<agent_variant>_<timestamp>.jsonl`
- YAAM API Wall logs (run window): `<path or terminal transcript reference>`
- HTML report: `benchmarks/goodai-ltm-benchmark/data/reports/<report_file>.html`

## 7. Conclusions and Next Actions

- What changed relative to the previous run (provider, model, or key configuration)?
- Which visibility gaps remain (e.g., missing provider/model fields in artifacts)?
- What minimal policy-layer changes are recommended next?

