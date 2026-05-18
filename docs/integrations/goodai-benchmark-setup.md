# GoodAI LTM Benchmark Setup Guide

## Overview

The GoodAI LTM benchmark is no longer embedded in this repository. YAAM owns the API Wall and memory orchestration runtime; the benchmark lives in a separate repository and calls YAAM over HTTP.

- YAAM repository: `yet-another-agents-memory`
- Benchmark repository: `git@github.com-skazo4ny:maksim-tsi/goodai-ltm-benchmark-yaam.git`
- Runtime boundary: OpenAI-compatible `POST /v1/chat/completions`
- Current lab endpoint: `http://192.168.107.187:8002/v1/chat/completions`

This split keeps the incompatible Poetry environments isolated and makes the API Wall the contract between consumer applications, benchmarks, and the YAAM runtime.

## Repository Layout

Recommended local checkout layout:

```bash
research-code/
├── yet-another-agents-memory/
└── goodai-ltm-benchmark-yaam/
```

Clone and install the benchmark separately:

```bash
cd ../
git clone git@github.com-skazo4ny:maksim-tsi/goodai-ltm-benchmark-yaam.git
cd goodai-ltm-benchmark-yaam
poetry install
```

If the benchmark checkout lives elsewhere, pass it to YAAM helper scripts with:

```bash
export GOODAI_BENCHMARK_DIR=/path/to/goodai-ltm-benchmark-yaam
```

## Runtime Topology

YAAM currently runs on `skz-data-lv` with DBMS resources colocated on the same host. Consumers should use the LAN IP rather than SSH host aliases:

```bash
curl -fsS http://192.168.107.187:8002/health
```

The service is started from the YAAM repository on `skz-data-lv` with both compose files:

```bash
docker compose -f docker-compose.interface.yml -f docker-compose.skz-data.yml up -d mas-agent
```

Do not move secrets into docs or scripts. The `.env` file remains local to the runtime host and must not be printed.

## API Wall Contract

The benchmark talks to YAAM through the same endpoint used by external consumers:

```text
POST /v1/chat/completions
```

The benchmark adapter should provide:

- `AGENT_URL`, for example `http://192.168.107.187:8002/v1/chat/completions`
- `X-Session-Id` per benchmark session
- optional `X-Mock-Time` for controlled temporal experiments

YAAM returns an OpenAI-compatible chat completion response with additional metadata useful for analysis, including selected skill and timing fields.

## Run A Smoke Benchmark

From the benchmark repository:

```bash
AGENT_URL=http://192.168.107.187:8002/v1/chat/completions \
MAS_WRAPPER_TIMEOUT=600 \
./.venv/bin/python -m runner.run_benchmark \
  -a mas-remote \
  -c configurations/mas_variant_a_smoke_5.yml \
  --progress tqdm \
  -y
```

From the YAAM repository, the helper script resolves the benchmark checkout from `GOODAI_BENCHMARK_DIR` or the recommended sibling directory:

```bash
GOODAI_BENCHMARK_DIR=../goodai-ltm-benchmark-yaam \
./scripts/run_goodai_remote_variant.sh \
  --agent-url http://192.168.107.187:8002/v1/chat/completions \
  --agent-type full \
  --agent-variant v1-min-skillwiring \
  --config configurations/mas_variant_a_smoke_5.yml
```

## Output Locations

Benchmark-generated state and reports are owned by the benchmark repository:

- `data/tests/<run_name>/definitions/`
- `data/tests/<run_name>/results/<agent>/`
- `data/reports/`

YAAM keeps only copied or curated result artifacts under `benchmarks/results/` when needed.

## Troubleshooting

If a YAAM helper script cannot find the benchmark, set `GOODAI_BENCHMARK_DIR` to the external checkout.

If the benchmark venv is missing, run `poetry install` from the benchmark repository.

If `/health` is unavailable, confirm `skz-data-lv` is powered on and the `mas-agent` container is running. `skz-dev-lv` is no longer required for Redis.

## Status

**Last updated:** 2026-05-18
**Status:** Decoupled benchmark repository; YAAM retains API Wall runtime only.
