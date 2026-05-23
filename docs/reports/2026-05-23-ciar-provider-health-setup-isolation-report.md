# CIAR Provider-Health Setup Isolation Report

Date: 2026-05-23
Status: Complete locally
Related plan: `docs/plan/2026-05-23-ciar-provider-health-setup-isolation-plan.md`

## Summary

Implemented provider-health cleanup and a post-health Redis probe to stabilize
CIAR live required-health runs before Redis/L1 setup. This batch did not change
CIAR scoring, promotion policy, contradiction policy, storage adapters, DB
schemas, provider routing defaults, dependencies, or `.env` behavior.

The required-health verification run
`ciar-exp-live-suppression-checkpoint-20260523-06-required-health-isolation`
completed successfully with `runtime_setup.status=ok` and
`operational_classification.run_quality=policy_evidence`.

## Changed Behavior

- `LLMClient` now exposes async `close()` and `aclose()` lifecycle methods.
- Registered providers and provider SDK clients are closed best-effort via
  `aclose` or `close` when available.
- Cleanup diagnostics are returned as `{status, errors}` and never mask the
  original health-check result.
- CIAR provider-health preflight now:
  - creates the health-check `LLMClient` explicitly;
  - always closes it in `finally`;
  - records `provider_health.cleanup`;
  - runs a Redis adapter connect probe after health cleanup for required-health
    live runs;
  - records the probe under `provider_health.post_health_redis_probe`.

## Verification

Passed:

```bash
uname -a && hostname && pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/utils/test_llm_client.py tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_challenge_with_env.py -v
./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env --json
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
```

Results:

- Targeted tests: `32 passed in 101.90s`
- CIAR regression pack: `145 passed in 180.25s`
- Data-node diagnostic: all default services passed

Full-suite protocol check:

```bash
./.venv/bin/pytest tests/ -v
```

Result: `653 passed, 135 skipped, 5 failed, 4 errors in 361.78s`.

The failures/errors were outside this batch's changed files:

- `tests/memory/test_episodic_memory_tier.py`: five failures where tests expect
  embedding size `1536`, while the runtime tier reports `4096`.
- `tests/v2-api-e2e/test_semantic_gateway_e2e.py`: four setup errors from
  Qdrant connection attempts failing in the E2E fixture.

These are recorded as residual full-suite blockers, not regressions observed in
the CIAR provider-health isolation path.

## Live Verification

Command:

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

Outcome:

- Exit code: `0`
- Provider health: `checked`
- Provider cleanup: `ok`
- Post-health Redis probe: `ok`, elapsed `78.866ms`
- Runtime setup: `ok`
- Operational classification: `policy_evidence`
- Scenario errors: `0`

Promotion results:

| Scenario | Segments promoted | Facts extracted | Facts promoted | Facts suppressed |
|---|---:|---:|---:|---:|
| `contradiction_update` | 1 | 3 | 2 | 1 |
| `repeated_correction` | 0 | 0 | 0 | 0 |

Aggregate with prior checkpoint runs `-01` through `-06`:

```json
{
  "policy_evidence": 3,
  "policy_evidence_with_warnings": 1,
  "incomplete": 2
}
```

Suppression evaluation now includes one live suppressed fact for
`contradiction_update`. `repeated_correction` remains a live prompt/segmentation
robustness gap because its segment still scored below the promotion threshold.

Aggregate artifacts:

- `logs/ciar_challenge/ciar-live-suppression-checkpoint-20260523-with-06.json`
- `logs/ciar_challenge/ciar-live-suppression-checkpoint-20260523-with-06.md`

## Recommendation

Treat the provider-health to Redis/L1 setup interaction as fixed for the
current harness path. The next CIAR batch should focus on live suppression
fixture robustness, especially making `repeated_correction` live-observable and
more consistently extracting separable old/current facts across both focused
scenarios.
