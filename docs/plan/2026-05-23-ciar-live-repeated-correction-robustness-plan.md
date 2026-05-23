# CIAR Live Repeated Correction Robustness Plan

Date: 2026-05-23
Status: Planned

## Purpose

Make the `repeated_correction` CIAR challenge live-observable without changing
CIAR scoring, thresholds, promotion policy, contradiction policy, storage
adapters, provider routing defaults, dependencies, or `.env` behavior.

Current dry-run evidence is deterministic, but live run
`ciar-exp-live-suppression-checkpoint-20260523-06-required-health-isolation`
scored the `repeated_correction` segment at `0.5`, below the `0.6` threshold.
The immediate goal is to make the ALFA-4421 correction chain read as a
high-impact operational route-change log to live segmentation.

## Scope

- Rewrite only the `repeated_correction` scenario fixture text.
- Add diagnostic fields to existing `significance_scored` telemetry.
- Preserve dry-run expectations and analyzer compatibility.
- Do not modify CIAR scoring, thresholds, policy modes, storage adapters,
  provider routing, dependencies, or `.env` behavior.

## Acceptance Criteria

- Focused dry `hybrid_gate+suppress_superseded` run still yields:
  `segments_promoted=1`, `facts_extracted=3`, `facts_promoted=1`,
  `facts_suppressed=2`.
- CIAR regression pack remains green.
- At least one of two live focused runs is clean policy evidence and reaches
  scenario execution.
- At least one clean live run promotes the `repeated_correction` segment and
  extracts at least two facts.
- Preferred live success: at least one clean live run suppresses at least one
  prior route fact and promotes/stores a current Long Beach fact.

## Verification Commands

```bash
uname -a
hostname
pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_policy_analysis.py -v
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-repeated-correction-live-robustness-20260523-01 \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode suppress_superseded \
  --scenario-id repeated_correction
./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env --json
./.venv/bin/python scripts/experiments/run_ciar_challenge_with_env.py \
  --print-presence \
  --run-id ciar-exp-live-repeated-correction-robustness-20260523-01 \
  --model tencent/hy3-preview \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode suppress_superseded \
  --require-provider-health \
  --redis-timeout 60 \
  --scenario-delay-s 5 \
  --scenario-id repeated_correction
./.venv/bin/python scripts/experiments/run_ciar_challenge_with_env.py \
  --print-presence \
  --run-id ciar-exp-live-repeated-correction-robustness-20260523-02 \
  --model tencent/hy3-preview \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode suppress_superseded \
  --require-provider-health \
  --redis-timeout 60 \
  --scenario-delay-s 5 \
  --scenario-id repeated_correction
```
