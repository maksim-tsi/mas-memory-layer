# Checklist: GoodAI LTM Benchmark Smoke5 (Gemini/Mistral Parity Runs)

**Date:** YYYY-MM-DD  
**Agent Variant:** `v1-min-skillwiring` (Variant A)  
**Goal:** execute Smoke5 runs on Gemini and Mistral under the same conditions as the Groq run, producing comparable artifacts (scores, timing, attribution, and HTML report).

This checklist mirrors `docs/reports/checklist-goodai-smoke5-groq-provider.md` and is intended for parity replication. It does not disclose secrets.

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

Key handling requirement:

- If `GOOGLE_API_KEY` / `MISTRAL_API_KEY` is absent from the environment, it MUST be loaded from `.env` using the command above (do not echo it).

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

Record tunnel port and start time.

## 3. Start API Wall (Gemini) in a New Shell

In a new terminal:

```bash
set -a; source .env; set +a

REDIS_URL=redis://localhost:${TUNNEL_PORT} \
MAS_PORT=${MAS_PORT} \
MAS_AGENT_TYPE=full \
MAS_AGENT_VARIANT=v1-min-skillwiring \
MAS_MODEL=gemini-3-flash-preview \
MAS_PROMOTION_MODE=disabled \
./.venv/bin/uvicorn src.server:app --host 0.0.0.0 --port ${MAS_PORT}
```

Record:

- `git rev-parse HEAD`
- `MAS_MODEL` (expected: `gemini-3-flash-preview`)
- `MAS_PROMOTION_MODE` (expected: `disabled` for Smoke5 parity runs)
- provider availability from `/health` (`llm_providers`)

## 4. Provider Check (Blocker Gate)

### 4.1 Health endpoint

```bash
curl -4 -sS http://127.0.0.1:${MAS_PORT}/health
```

Verify:

- `status` is `ok`
- `agent_type` is `full`
- `agent_variant` is `v1-min-skillwiring`
- `redis: true`

### 4.2 Single-turn API Wall call (attribution + timing)

```bash
curl -4 -sS http://127.0.0.1:${MAS_PORT}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'X-Session-Id: gemini-vischeck-001' \
  -d '{"model":"default","messages":[{"role":"user","content":"Reply with exactly: pong"}]}'
```

Verify response `metadata` contains (at minimum):

- `llm_provider` and `llm_model`
- `llm_ms` and `storage_ms`
- `skill_slug`
- `yaam_session_id` and `client_session_id`
- `context.recent_turns_count`, `context.working_facts_count`, `context.episodic_chunks_count`, `context.semantic_knowledge_count`
- `promotion_mode` and `promotion_status` (expect `disabled` + `skipped` for Smoke5 default)

## 5. Run GoodAI Smoke5 (Gemini)

Use a unique run name that matches the experiment matrix convention:

```bash
cd benchmarks/goodai-ltm-benchmark
set -a; source ../../.env; set +a

RUN_NAME="goodai__smoke5__provider=gemini__model=gemini-3-flash-preview__promotion=disabled__agent=full__v1-min-skillwiring__$(date +%Y%m%d_%H%M%S)"

AGENT_URL=http://127.0.0.1:${MAS_PORT}/v1/chat/completions \
MAS_WRAPPER_TIMEOUT=600 \
./.venv/bin/python -m runner.run_benchmark \
  -a mas-remote \
  -c configurations/mas_variant_a_smoke_5.yml \
  --progress tqdm \
  -y \
  --run-name "$RUN_NAME"
```

Completion gate:

- exit code `0`
- HTML report generated under `benchmarks/goodai-ltm-benchmark/data/reports/`

## 6. Teardown (Gemini)

- Stop benchmark runner (if needed): Ctrl+C
- Stop API Wall: Ctrl+C
- Stop SSH tunnel: Ctrl+C

## 7. Repeat for Mistral (Parity Run)

Start a new tunnel + API Wall instance (same steps as above) but set:

- `MAS_MODEL=mistral-large`
- `MAS_PROMOTION_MODE=disabled`
- `X-Session-Id: mistral-vischeck-001`
- Run name:
  - `goodai__smoke5__provider=mistral__model=mistral-large__promotion=disabled__agent=full__v1-min-skillwiring__<ts>`

Example API Wall start:

```bash
set -a; source .env; set +a

REDIS_URL=redis://localhost:${TUNNEL_PORT} \
MAS_PORT=${MAS_PORT} \
MAS_AGENT_TYPE=full \
MAS_AGENT_VARIANT=v1-min-skillwiring \
MAS_MODEL=mistral-large \
./.venv/bin/uvicorn src.server:app --host 0.0.0.0 --port ${MAS_PORT}
```

## 8. Artifact Collection (Required for Each Run)

From:

`benchmarks/goodai-ltm-benchmark/data/tests/<run_name>/results/RemoteMASAgentSession - remote/`

Collect:

- `run_console.log`
- `master_log.jsonl`
- `turn_metrics.jsonl`
- `runstats.json`
- per dataset: `<Dataset>/0_0.json`

Also collect YAAM-side artifacts:

- `logs/rate_limiter_full_v1-min-skillwiring_<timestamp>.jsonl` (select the file whose timestamp matches the run window)

## 9. Reporting (Required for Each Run)

Create a per-run report under `docs/reports/` and record:

- the exact `RUN_NAME`,
- the `/health` JSON,
- aggregate per-dataset scores,
- and the artifact paths (including the HTML report path).
