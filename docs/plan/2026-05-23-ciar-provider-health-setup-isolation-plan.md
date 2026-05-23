# CIAR Provider-Health Setup Isolation Plan

Date: 2026-05-23
Status: Planned

## Purpose

Stabilize CIAR live required-health runs by isolating and cleaning up LLM
provider-health resources before Redis/L1 setup begins. Recent evidence shows
Redis and YAAM data-node endpoints are healthy in isolation, while required
provider-health runs fail at `l1_initialize_started`; skip-health runs pass
L1/L2 setup.

This batch is an operational lifecycle fix. It must not change CIAR scoring,
promotion policy, contradiction policy, storage adapters, DB schemas, provider
routing defaults, dependencies, or `.env` behavior.

## Scope

- Add explicit best-effort lifecycle cleanup to `LLMClient` and registered
  provider SDK clients.
- Update CIAR provider-health preflight to close its health-check client before
  Redis/L1 setup.
- Add a post-health Redis probe for live required-health runs so Redis setup
  failures are classified before policy artifacts are attempted.
- Document verification results and live checkpoint outcome.

## Acceptance Criteria

- Required-health live runs either reach `runtime_setup.status=ok` and scenario
  execution, or fail earlier with `provider_health.post_health_redis_probe`
  evidence.
- Provider-health cleanup metadata is recorded in `run_manifest.json`.
- LLM provider cleanup is deterministic and cleanup warnings do not mask health
  reports.
- CIAR dry behavior and the regression pack remain green.

## Verification Commands

```bash
uname -a && hostname && pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/utils/test_llm_client.py tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_challenge_with_env.py -v
./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env --json
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
```

Live verification:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge_with_env.py \
  --print-presence \
  --run-id ciar-exp-live-suppression-checkpoint-20260523-06-required-health-isolation \
  --model tencent/hy3-preview \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode suppress_superseded \
  --require-provider-health \
  --redis-timeout 60 \
  --scenario-delay-s 5 \
  --scenario-id contradiction_update \
  --scenario-id repeated_correction
```
