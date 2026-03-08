# YAAM Visibility/Transparency Check (MacBook → skz Redis tunnel)

**Date:** 2026-02-22  
**Repository Commit:** `4230ff08c870398f0038faeba0ae1687bd95ba70`  
**Scope:** Variant A API Wall run with GoodAI LTM Benchmark Smoke5, emphasizing observability from artifacts.

## 1. Objective

This report evaluates whether a single execution turn/run provides sufficient transparency to debug correctness, isolation boundaries, and failures using artifacts alone (i.e., without relying on interactive reproduction).

The target definition of “good visibility” is the ability to recover:

1. **Session isolation:** session identifiers are prefixed by `agent_type` and `agent_variant`.
2. **Skill behavior:** no user-visible planner/routing content; behavior aligns with skill intent.
3. **LLM traceability:** the provider and model are inferable (at minimum from logs; ideally from response metadata).
4. **Timing/latency:** per-turn timing signals distinguish storage and LLM time.
5. **Memory usage:** it is unambiguous whether the agent writes to L1/L2 along the API Wall path; malformed or empty content does not crash the server.
6. **Artifacts:** the benchmark emits per-dataset JSON, `master_log.jsonl`, `turn_metrics.jsonl`, and an HTML report, and exits cleanly.

## 2. Topology and Run Configuration

### 2.1 Topology

- **Host:** MacBook (local checkout)
- **Redis:** remote host (skz), tunneled to local `localhost:6380`
- **Postgres:** via `POSTGRES_URL` sourced from root `.env` (contents not printed)
- **API Wall:** local `uvicorn` (note: port conflict required using `8083`)
- **GoodAI runner:** `benchmarks/goodai-ltm-benchmark/.venv`

### 2.2 Redis tunnel

Foreground tunnel (local port `6380`):

```bash
ssh -N -L 6380:127.0.0.1:6379 skz-dev-local
```

Tunnel start time (local): `2026-02-22 12:27:25 +0200`.

### 2.3 API Wall (Variant A)

API Wall was started with:

- `MAS_AGENT_TYPE=full`
- `MAS_AGENT_VARIANT=v1-min-skillwiring`
- `REDIS_URL=redis://localhost:6380`
- `MAS_PORT=8083`

Health check:

- `GET http://127.0.0.1:8083/health`
- Result: `status: ok`, `agent_type: full`, `agent_variant: v1-min-skillwiring`, `redis: true`, and tier-level storage connectivity.

Default model:

- `MAS_MODEL` default is `gemini-3-flash-preview` in `src/server.py` (unless overridden by environment).

## 3. Benchmark Execution (GoodAI Smoke5)

### 3.1 Command

Executed from `benchmarks/goodai-ltm-benchmark/` with environment sourced from root `.env`, targeting the API Wall endpoint:

- `AGENT_URL=http://127.0.0.1:8083/v1/chat/completions`
- `MAS_WRAPPER_TIMEOUT=600`

### 3.2 Run metadata

From `run_meta.json`:

- **Run name:** `MAS Variant A Smoke 5`
- **Agent name:** `RemoteMASAgentSession - remote`
- **Start time (UTC):** `2026-02-22T10:33:07.038812+00:00`
- **End time (UTC):** `2026-02-22T11:15:40.260554+00:00`

The run was aborted near completion (Ctrl+C), producing exit code `1`. Consequently, the HTML report was not generated for this run.

## 4. Artifact Inventory (Run: MAS Variant A Smoke 5)

Results directory:

- `benchmarks/goodai-ltm-benchmark/data/tests/MAS Variant A Smoke 5/results/RemoteMASAgentSession - remote/`

Key artifacts:

- `run_console.log`
- `master_log.jsonl`
- `turn_metrics.jsonl`
- `runstats.json`
- Per-dataset results: `*/0_0.json` (present for: Restaurant, Instruction Recall, Spy Meeting, Prospective Memory)

HTML reports directory checked:

- `benchmarks/goodai-ltm-benchmark/data/reports/`
- No report matching `MAS Variant A Smoke 5` was created (consistent with non-clean termination).

## 5. Observations Against “Good Visibility”

### 5.1 Session isolation (session prefixing)

- The API Wall requires `X-Session-Id` and applies an internal prefix `"{agent_type}__{agent_variant}:"` (server-side behavior is directly observable in code and by response semantics).
- However, the benchmark artifacts record `session_id` in `turn_metrics.jsonl` as `MAS Variant A Smoke 5 - RemoteMASAgentSession - remote` (not visibly prefixed by `agent_type/variant`).

**Conclusion:** session isolation is **partially** visible. The API Wall path has deterministic prefixing, but benchmark artifacts do not currently surface the prefixed session identifier.

### 5.2 Skill behavior (planner leakage)

In a manual API Wall call, the assistant response content did not include planner/routing text. The response `metadata` contained:

- `skill_slug`, `skill_name`, `skill_namespace`, and wiring configuration fields (e.g., `skill_wiring_mode`).

**Conclusion:** planner leakage control appears to be **satisfactory**, and skill identity is observable.

### 5.3 LLM traceability (provider/model)

- API Wall server logs contained repeated provider failure lines and a Gemini quota exhaustion exception (`429 RESOURCE_EXHAUSTED`), indicating that Gemini was attempted and rate-limited.
- Benchmark artifacts did not include explicit per-turn fields for `provider` or `model`.
- A manual response `metadata` did not include the final provider/model, even though the underlying provider wrapper produces them at the LLM client layer.

**Conclusion:** LLM traceability is **insufficient** at the artifact level. Provider/model must be included in response metadata and/or benchmark logs to support post-mortem debugging without server logs.

### 5.4 Timing/latency transparency (storage vs LLM)

- The API Wall response `metadata` included `storage_ms_pre`, `llm_ms`, `storage_ms_post`, and total `storage_ms`.
- The benchmark `turn_metrics.jsonl` for this run recorded `llm_ms: null` and `storage_ms: null`, while `total_ms` was present.

**Conclusion:** timing visibility is **partial**. The API Wall path provides separation of storage and LLM timing, but the benchmark metrics file does not currently preserve those components.

### 5.5 Memory usage visibility (L1/L2 writes)

- The API Wall sets `skip_l1_write=true` by default (request metadata), which is reflected in response `metadata`.
- The health endpoint surfaces L1/L2 tier health and (for L2) aggregate statistics (e.g., fact counts and average CIAR score).

**Conclusion:** memory visibility is **partial**. The default write-suppression is explicit, but per-turn signals indicating whether L1/L2 were written (and what was promoted) are not currently guaranteed in benchmark artifacts.

### 5.6 Artifact completeness and clean termination

- Per-dataset JSON files existed for four datasets.
- The run did not terminate cleanly (manual abort); thus, the report generation requirement was not satisfied for this execution.

**Conclusion:** artifact completeness is **partial** for aborted runs; clean termination is required for report generation.

## 6. Dataset Outcomes (Partial)

From per-dataset `0_0.json`:

- Restaurant: `0.0/1.0` (agent returned “I’m unable to respond right now.”)
- Spy Meeting: `0.0/1.0` (agent returned “I’m unable to respond right now.”)
- Instruction Recall: `1.0/1.0`
- Prospective Memory: `1.0/1.0`

Given server-side evidence of Gemini `429` quota failures, a plausible explanation is that model calls degraded to fallback responses during rate limiting, causing multiple datasets to fail for reasons unrelated to task specification compliance.

## 7. Visibility Matrix (Pass/Fail)

| Component | What to verify | Where to observe | Pass/Fail | Notes |
|---|---|---|---|---|
| SSH tunnel | stable tunnel | tunnel terminal; `lsof` on local port | Pass | Local port `6380` used due to port contention on `6379`. |
| API Wall health | status/variant/provider list | `/health` JSON | Pass | Tier health and `llm_providers` visible. |
| Session isolation | prefixed session IDs | benchmark artifacts; server logs | Partial | API Wall prefixes `X-Session-Id`, but benchmark `turn_metrics.jsonl` does not surface the prefixed identifier. |
| Skill behavior | no planner leakage | `run_console.log`; response content | Partial | No planner text observed; skill identity observable in API response metadata, but not in benchmark artifacts by default. |
| LLM traceability | provider/model identifiable | server logs; response metadata | Partial | Provider failures visible in server logs; provider/model not reliably present in benchmark artifacts. |
| Timing transparency | storage vs LLM timings | API response metadata; benchmark metrics | Partial | API response metadata contains component timings; `turn_metrics.jsonl` does not preserve them. |
| Report generation | HTML generated + exit 0 | runner output; `data/reports/` | Fail | Run aborted; no HTML report generated for this run. |

## 8. Recommendations (Next Iteration Requirements)

1. **Provider selection for stability:** execute a follow-up run using Groq routing (`MAS_MODEL=openai/gpt-oss-120b`) to avoid Gemini free-tier quota constraints.
2. **Artifact-level traceability:** ensure provider and model identifiers are emitted into response metadata and written to benchmark logs (`master_log.jsonl` and/or `turn_metrics.jsonl`).
3. **Metrics propagation:** preserve storage vs LLM component timing in benchmark metrics (or write a parallel JSONL within the API Wall process and collect it per run).
4. **Report generation gating:** require clean termination and the presence of the HTML report under `benchmarks/goodai-ltm-benchmark/data/reports/` as a run completion criterion.

