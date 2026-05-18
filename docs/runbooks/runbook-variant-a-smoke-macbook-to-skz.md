# Runbook: Variant A Smoke Against skz-data-lv

This runbook runs a small GoodAI LTM smoke benchmark from an external benchmark checkout against the YAAM API Wall on `skz-data-lv`.

## Preconditions

- `skz-data-lv` is powered on.
- YAAM API Wall is healthy at `http://192.168.107.187:8002/health`.
- Benchmark repository is cloned separately from YAAM:
  `git@github.com-skazo4ny:maksim-tsi/goodai-ltm-benchmark-yaam.git`
- Benchmark Poetry environment exists:
  `../goodai-ltm-benchmark-yaam/.venv/bin/python`

`skz-dev-lv` is not required. Redis now lives on `skz-data-lv` with the other DBMS resources.

## 1. Check YAAM Health

```bash
curl -fsS http://192.168.107.187:8002/health
```

Expect `status` to be `ok`, with `agent_type` and `agent_variant` fields present.

## 2. Run GoodAI Smoke

From the benchmark repository:

```bash
cd ../goodai-ltm-benchmark-yaam

AGENT_URL=http://192.168.107.187:8002/v1/chat/completions \
MAS_WRAPPER_TIMEOUT=600 \
./.venv/bin/python -m runner.run_benchmark \
  -a mas-remote \
  -c configurations/mas_variant_a_smoke_5.yml \
  --progress tqdm \
  -y
```

From the YAAM repository, use the wrapper script:

```bash
GOODAI_BENCHMARK_DIR=../goodai-ltm-benchmark-yaam \
./scripts/run_goodai_remote_variant.sh \
  --agent-url http://192.168.107.187:8002/v1/chat/completions \
  --agent-type full \
  --agent-variant v1-min-skillwiring \
  --config configurations/mas_variant_a_smoke_5.yml
```

## Outputs

Benchmark outputs are written inside the external benchmark repository:

- Generated definitions: `data/tests/<run_name>/definitions/`
- Results: `data/tests/<run_name>/results/mas-remote/`
- HTML report: `data/reports/`

## Teardown

No local Redis tunnel or local API Wall process is required for this runbook. Stop only the benchmark process if it is still running.
