# Checklist: GoodAI LTM Benchmark Smoke5 (Groq Provider Routing)

**Date:** YYYY-MM-DD  
**YAAM Commit:** `<git sha>`  
**Agent Variant:** `v1-min-skillwiring` (Variant A)  
**Goal:** execute a Smoke5 run with Groq routing and collect sufficient artifacts to diagnose correctness, isolation, and failures without interactive reproduction.

## 0. Preconditions (Do Not Record Secrets)

1. Confirm the repository virtual environments exist:
   - `./.venv/bin/python`
   - `benchmarks/goodai-ltm-benchmark/.venv/bin/python`
2. Confirm SSH config contains `Host skz-dev-local`.
3. Confirm `.env` exists at repo root.
4. Load `.env` into the current shell **without printing** its contents:

```bash
set -a; source .env; set +a
```

**Key handling requirement:** if `GROQ_API_KEY` is absent from the environment, it must be loaded from `.env` by the step above. Do not echo or print it.

## 1. Select Ports (Record Chosen Values)

1. Choose a Redis tunnel local port:
   - Prefer `6379`; if already in use, use `6380`.
2. Choose an API Wall port:
   - Prefer `8081`; if already in use, choose a free alternative (e.g., `8083`).

Record:

- `TUNNEL_PORT=<...>`
- `MAS_PORT=<...>`
- `start_time_local=<...>`
- `start_time_utc=<...>`

## 2. Start Redis Tunnel (Foreground)

```bash
ssh -N -L ${TUNNEL_PORT}:127.0.0.1:6379 skz-dev-local
```

Record:

- tunnel start time (local/UTC)
- tunnel port

## 3. Start API Wall (Groq Routing) in a New Shell

In a new terminal:

```bash
set -a; source .env; set +a

REDIS_URL=redis://localhost:${TUNNEL_PORT} \
MAS_PORT=${MAS_PORT} \
MAS_AGENT_TYPE=full \
MAS_AGENT_VARIANT=v1-min-skillwiring \
MAS_MODEL=openai/gpt-oss-120b \
./.venv/bin/uvicorn src.server:app --host 0.0.0.0 --port ${MAS_PORT}
```

Record:

- `git rev-parse HEAD`
- agent type/variant
- `MAS_MODEL` (expected: `openai/gpt-oss-120b`)
- whether Gemini is enabled for this run (presence of `GOOGLE_API_KEY` in environment: yes/no; do not print values)

## 4. Provider Check (Blocker Gate)

### 4.1 Health endpoint

```bash
curl -4 -sS http://127.0.0.1:${MAS_PORT}/health
```

Verify:

- `status` is `ok`
- `agent_type` and `agent_variant` match the configuration
- `redis: true`
- L1/L2 tier storage health is `healthy`

### 4.2 Single-turn API Wall call (metadata + timing)

Perform a minimal request with an explicit `X-Session-Id`:

```bash
curl -4 -sS http://127.0.0.1:${MAS_PORT}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'X-Session-Id: groq-vischeck-001' \
  -d '{"model":"default","messages":[{"role":"user","content":"Reply with exactly: pong"}]}'
```

Verify:

1. Assistant content contains no planner/routing leakage.
2. Response `metadata` includes:
   - `skill_slug` (and related skill identifiers)
   - `storage_ms_pre`, `llm_ms`, `storage_ms_post`
3. **Traceability requirement:** provider and model must be inferable from artifacts.
   - If response metadata does not include `provider` and `model`, capture the API Wall logs for the request and treat missing fields as a visibility gap to fix before relying on benchmarks for attribution.

## 5. LLM-Engine Compatibility Check (FactExtractor, TopicSegmenter)

This repository currently defaults some LLM engines to Gemini model identifiers:

- `FactExtractor.model_name` default: `gemini-3-flash-preview`
- `TopicSegmenter.DEFAULT_MODEL` default: `gemini-3-flash-preview`

Decision (record explicitly):

- **Option A (preferred for Groq-only runs):** configure these engines to use the Groq model (`openai/gpt-oss-120b`) and verify they do not attempt Gemini calls.
- **Option B (allowed fallback):** permit Gemini for these engines (requires a valid paid-tier Gemini key) while keeping the agent’s main routing on Groq.

Tracking requirement:

- For each run, explicitly state which provider/model is used by:
  - the agent main generation,
  - FactExtractor,
  - TopicSegmenter.

## 6. Run GoodAI Smoke5

```bash
cd benchmarks/goodai-ltm-benchmark
set -a; source ../../.env; set +a

AGENT_URL=http://127.0.0.1:${MAS_PORT}/v1/chat/completions \
MAS_WRAPPER_TIMEOUT=600 \
./.venv/bin/python -m runner.run_benchmark \
  -a mas-remote \
  -c configurations/mas_variant_a_smoke_5.yml \
  --progress tqdm \
  -y
```

Record:

- run name
- start time / end time
- exit code

Completion gate:

- Require exit code `0` and a generated HTML report under `benchmarks/goodai-ltm-benchmark/data/reports/`.

## 7. Artifact Collection (Required)

From:

`benchmarks/goodai-ltm-benchmark/data/tests/<run_name>/results/RemoteMASAgentSession - remote/`

Collect:

- `run_console.log`
- `master_log.jsonl`
- `turn_metrics.jsonl`
- `runstats.json`
- per dataset: `<Dataset>/0_0.json`

Also collect YAAM-side artifacts:

- `logs/rate_limiter_<agent_type>_<agent_variant>_<timestamp>.jsonl`
- API Wall log snippet corresponding to the run window (if not already persisted as a file, capture terminal transcript for the run interval)

## 8. Reporting (Required)

Create a run report under `docs/reports/` using the Groq template (see `template-goodai-agent-variant-report-groq.md`), including:

- a filled visibility matrix (session isolation, skill behavior, traceability, timing, memory writes, report generation),
- dataset outcomes and failure taxonomy,
- and explicit artifact paths.

## 9. Teardown

- Stop benchmark runner (if needed): Ctrl+C
- Stop API Wall: Ctrl+C
- Stop SSH tunnel: Ctrl+C

