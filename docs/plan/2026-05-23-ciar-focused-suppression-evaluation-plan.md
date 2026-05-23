# CIAR Focused Suppression Evaluation Plan

Date: 2026-05-23
Status: Implementation planned
Scope: CIAR challenge analyzer, deterministic dry-run evidence, and docs

## Purpose

Evaluate CIAR supersession behavior with a deterministic dry-run matrix focused
on the canonical contradiction scenarios: `contradiction_update` and
`repeated_correction`.

The batch should prove that `suppress_superseded` changes only contradiction
handling: old facts are suppressed, current facts remain stored, and `off` plus
`metadata_only` do not suppress. This batch must not change CIAR scoring,
`hybrid_gate`, `ContradictionPolicy`, storage adapters, runtime defaults,
dependencies, or `.env` handling.

## Dry Matrix

Run the same focused scenarios under three contradiction policy modes:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-suppression-eval-off-20260523-01 \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode off \
  --scenario-id contradiction_update \
  --scenario-id repeated_correction

./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-suppression-eval-metadata-20260523-01 \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode metadata_only \
  --scenario-id contradiction_update \
  --scenario-id repeated_correction

./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-suppression-eval-suppress-20260523-01 \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode suppress_superseded \
  --scenario-id contradiction_update \
  --scenario-id repeated_correction
```

## Planned Changes

- Extend `scripts/experiments/analyze_ciar_policy_runs.py` with a backward
  compatible top-level `suppression_evaluation` JSON object.
- Render a `## Suppression Evaluation` markdown section before recommendation
  inputs.
- Report, per config and focused scenario: runs, promoted facts, suppressed
  facts, suppression rate, promoted contents, and suppressed contents.
- Add analyzer tests for the new JSON and markdown behavior, including partial
  or older run artifacts.
- Update the CIAR coordination plan with `CIAR-SUP-3`.

## Acceptance Criteria

For the dry matrix:

- `hybrid_gate+off`: `contradiction_update` promotes 2 and suppresses 0;
  `repeated_correction` promotes 3 and suppresses 0.
- `hybrid_gate+metadata_only`: same promoted and suppressed counts as `off`,
  while contradiction metadata can still be present.
- `hybrid_gate+suppress_superseded`: `contradiction_update` promotes 1 and
  suppresses 1; `repeated_correction` promotes 1 and suppresses 2.

For analyzer output:

- Existing JSON and markdown fields remain unchanged.
- `suppression_evaluation` appears in JSON.
- Markdown includes `## Suppression Evaluation`.
- Runs without the focused scenarios do not crash and simply omit missing
  suppression rows.

## Verification Commands

```bash
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/scripts/test_ciar_policy_analysis.py tests/scripts/test_ciar_challenge_experiment.py -v
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
```

Live LLM reruns are optional follow-up and require explicit approval because
they use provider/network resources and can be affected by operational noise.
