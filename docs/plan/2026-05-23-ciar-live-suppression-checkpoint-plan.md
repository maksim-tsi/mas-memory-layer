# CIAR Live Suppression Checkpoint Plan

Date: 2026-05-23
Status: Execution planned
Scope: Live CIAR experiment checkpoint and report

## Purpose

Run a small, controlled live LLM checkpoint before the next CIAR batches to
validate that recent dry-only work survives real LLM segmentation and fact
extraction. The checkpoint focuses on `hybrid_gate + suppress_superseded` with
`contradiction_update` and `repeated_correction`.

This is an experiment and reporting batch only. It must not change CIAR code,
prompts, policy defaults, storage adapters, dependencies, or `.env`.

## Preflight

```bash
uname -a && hostname && pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/python scripts/experiments/run_ciar_challenge_with_env.py --presence-only
```

The presence check may report key names and booleans only. It must not print
secret values.

## Live Matrix

Run three live repeats with the current `.env` service URLs and provider health
as a hard gate:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge_with_env.py \
  --print-presence \
  --run-id ciar-exp-live-suppression-checkpoint-20260523-01 \
  --model tencent/hy3-preview \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode suppress_superseded \
  --require-provider-health \
  --scenario-delay-s 5 \
  --scenario-id contradiction_update \
  --scenario-id repeated_correction
```

Repeat with run IDs ending `-02` and `-03`.

Then aggregate:

```bash
./.venv/bin/python scripts/experiments/analyze_ciar_policy_runs.py \
  logs/ciar_challenge/ciar-exp-live-suppression-checkpoint-20260523-01 \
  logs/ciar_challenge/ciar-exp-live-suppression-checkpoint-20260523-02 \
  logs/ciar_challenge/ciar-exp-live-suppression-checkpoint-20260523-03 \
  --json-output logs/ciar_challenge/ciar-live-suppression-checkpoint-20260523.json \
  --markdown-output logs/ciar_challenge/ciar-live-suppression-checkpoint-20260523.md
```

## Acceptance Criteria

- All three runs complete with required artifacts and no scenario errors.
- Provider health is checked and passes for each run; otherwise classify the
  checkpoint as operationally blocked.
- `operational_classification.policy_evidence` is true for at least two of
  three runs.
- Live extraction produces usable facts for both focused scenarios in at least
  two of three runs.
- `suppression_evaluation` shows at least one auditable `fact_suppressed` result
  for `contradiction_update` or `repeated_correction` across the three runs.
- If suppression fails despite clean operations and usable extracted facts,
  pause policy/default planning and open a live extraction or supersession
  robustness follow-up.

## Reporting

Create `docs/reports/2026-05-23-ciar-live-suppression-checkpoint-report.md`
with:

- run IDs, model, and artifact paths;
- provider health status and operational classification per run;
- suppression counts and extracted fact notes;
- cleanup status;
- recommendation on whether to continue the next CIAR batches.

Live execution requires approval because it makes real provider calls and
touches live Redis, PostgreSQL, and Phoenix services.
