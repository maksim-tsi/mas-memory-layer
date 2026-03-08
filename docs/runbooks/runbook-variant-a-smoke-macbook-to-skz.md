# Runbook: Variant A Smoke (MacBook -> skz-dev-lv Redis)

This runbook starts a local MAS API Wall (Variant A) on a MacBook while tunneling Redis from
`skz-dev-lv` (via SSH), then runs a 5-task GoodAI smoke benchmark against it.

## Preconditions

- You can SSH to `skz-dev-lv` using the `skz-dev-local` host from `~/.ssh/config`.
- Redis is reachable from `skz-dev-lv` at `localhost:6379`.
- `POSTGRES_URL` in `.env` is reachable from the MacBook (direct LAN/VPN), or you have a tunnel for it.
- Both venvs exist:
  - MAS repo: `./.venv/bin/python`
  - Benchmark repo: `benchmarks/goodai-ltm-benchmark/.venv/bin/python`

## 0) Load env (no printing)

In each shell/process that needs env, load it explicitly:

```bash
set -a; source .env; set +a
```

Do not print `.env` contents.

## 1) Tunnel Redis from skz-dev-lv

Pick a local port. Use `6379` if free; otherwise use `6380`.

```bash
# Foreground (recommended for visibility)
ssh -N -L 6379:127.0.0.1:6379 skz-dev-local

# If 6379 is busy, use:
ssh -N -L 6380:127.0.0.1:6379 skz-dev-local
```

## 2) Start API Wall (Variant A) with Redis override

Run the API Wall on a dedicated port (example: `8081`), but point Redis at the local tunnel.

```bash
set -a; source .env; set +a

REDIS_URL=redis://localhost:6379 \
MAS_PORT=8081 \
MAS_AGENT_TYPE=full \
MAS_AGENT_VARIANT=v1-min-skillwiring \
./.venv/bin/uvicorn src.server:app --host 0.0.0.0 --port 8081
```

If you used local port `6380` for the tunnel, update `REDIS_URL=redis://localhost:6380`.

## 3) Sanity checks

```bash
curl -s http://localhost:8081/health
```

Expect:
- `status` is `ok` (or `degraded` if Redis ping fails)
- `agent_type: full`
- `agent_variant: v1-min-skillwiring`

## 4) Run GoodAI smoke (5 datasets x 1 example)

Use `mas-remote` so the benchmark talks to API Wall via `AGENT_URL`.

```bash
cd benchmarks/goodai-ltm-benchmark
set -a; source ../../.env; set +a

AGENT_URL=http://localhost:8081/v1/chat/completions \
MAS_WRAPPER_TIMEOUT=600 \
./.venv/bin/python -m runner.run_benchmark \
  -a mas-remote \
  -c configurations/mas_variant_a_smoke_5.yml \
  --progress tqdm \
  -y
```

## Outputs

- Generated definitions: `benchmarks/goodai-ltm-benchmark/data/tests/<run_name>/definitions/`
- Results: `benchmarks/goodai-ltm-benchmark/data/tests/<run_name>/results/mas-remote/`
- HTML report: `benchmarks/goodai-ltm-benchmark/data/reports/`

## Teardown

- Stop benchmark: Ctrl+C
- Stop API Wall: Ctrl+C
- Stop SSH tunnel: Ctrl+C

