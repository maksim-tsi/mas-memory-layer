# CIAR Live Repeated Correction Robustness Report

Date: 2026-05-23
Status: Complete locally with live evidence
Related plan: `docs/plan/2026-05-23-ciar-live-repeated-correction-robustness-plan.md`

## Summary

Batch completed. The `repeated_correction` challenge fixture now reads as a
critical operational route-change log, and live focused runs promoted the
segment and extracted separable route facts. This batch did not change CIAR
scoring, thresholds, promotion policy, contradiction policy, storage adapters,
provider routing defaults, dependencies, or `.env` behavior.

## Changed Behavior

- Reworded only the `repeated_correction` scenario text around shipment
  `ALFA-4421`.
- Preserved the route sequence: Oakland -> Los Angeles -> Long Beach.
- Added operational-impact wording for dispatch, carrier booking, port
  appointment, customs destination, and delivery planning.
- Extended `significance_scored` telemetry with segment `certainty`, `impact`,
  `topic_excerpt`, and `summary_excerpt` while preserving existing keys.

## Verification

Passed:

```bash
uname -a
hostname
pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_policy_analysis.py -v
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
./.venv/bin/pytest tests/ -v
```

Results:

- Targeted script tests: `26 passed in 58.43s`
- CIAR regression pack: `145 passed in 177.97s`
- Full suite: `659 passed, 139 skipped in 358.63s`

Dry acceptance run:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-repeated-correction-live-robustness-20260523-01 \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode suppress_superseded \
  --scenario-id repeated_correction
```

Dry result:

| Scenario | Segments promoted | Facts extracted | Facts promoted | Facts suppressed |
|---|---:|---:|---:|---:|
| `repeated_correction` | 1 | 3 | 1 | 2 |

## Live Evidence

Preflight:

```bash
./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env --json
```

Result: all selected YAAM data-node services passed sanitized reachability
checks.

Live runs:

| Run | Quality | Segments promoted | Facts extracted | Facts promoted | Facts suppressed |
|---|---|---:|---:|---:|---:|
| `ciar-exp-live-repeated-correction-robustness-20260523-01` | `policy_evidence` | 1 | 6 | 2 | 3 |
| `ciar-exp-live-repeated-correction-robustness-20260523-02` | `policy_evidence` | 1 | 6 | 2 | 3 |

Aggregate:

- runs analyzed: `2`
- run quality counts: `policy_evidence=2`
- suppression evaluation for `hybrid_gate+suppress_superseded` /
  `repeated_correction`: promoted `4`, suppressed `6`, suppression rate `60%`

Artifacts:

- `logs/ciar_challenge/ciar-exp-live-repeated-correction-robustness-20260523-01`
- `logs/ciar_challenge/ciar-exp-live-repeated-correction-robustness-20260523-02`
- `logs/ciar_challenge/ciar-live-repeated-correction-robustness-20260523.json`
- `logs/ciar_challenge/ciar-live-repeated-correction-robustness-20260523.md`

## Notes

Both live runs reached the preferred success target: the segment was promoted,
facts were extracted, prior Oakland/Los Angeles route facts were suppressed,
and current Long Beach operational facts were promoted.

One standalone Long Beach fact in each run was suppressed as part of the
paraphrased supersession group while another Long Beach/current-destination fact
was promoted. This does not block the batch acceptance, but it is useful
evidence for future duplicate/consolidation cleanup.

## Recommendation

Treat `repeated_correction` live observability as repaired. The next CIAR work
can return to policy/default evaluation or broader live suppression validation,
using `contradiction_update` and `repeated_correction` as focused scenarios with
both dry and clean live evidence.
