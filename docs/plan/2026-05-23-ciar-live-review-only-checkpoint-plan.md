# CIAR Live Review-Only Checkpoint Plan

Date: 2026-05-23

## Summary

Run one focused live LLM checkpoint to verify that the Batch 4-6 review-only
layer survives real segmentation and extraction under `hybrid_gate+off`.

This is an experiment and reporting batch only. It does not change CIAR
scoring, thresholds, promotion defaults, contradiction policy, storage
adapters, dependencies, `.env`, prompts, schemas, or runtime behavior.

## Live Run

Run one required-provider-health live checkpoint with:

- promotion policy: `hybrid_gate`;
- contradiction policy: `off`;
- model: `tencent/hy3-preview`;
- scenarios:
  - `assistant_acknowledgement_noise`;
  - `urgent_with_chatter`;
  - `speculative_claim`;
  - `assistant_inferred`;
  - `access_reinforced_low_signal`;
  - `clear_constraint`;
  - `urgent_event`.

Because current live `FactExtractor` does not populate `access_count`,
`access_reinforced_low_signal` is live coverage evidence. A
`recency_access_guardrail=true` row is preferred, but not required for this
checkpoint.

## Verification Commands

```bash
uname -a
hostname
pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/python scripts/experiments/run_ciar_challenge_with_env.py --presence-only
./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env --json
./.venv/bin/python scripts/experiments/run_ciar_challenge_with_env.py \
  --print-presence \
  --run-id ciar-exp-live-review-only-checkpoint-20260523-01 \
  --model tencent/hy3-preview \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode off \
  --require-provider-health \
  --redis-timeout 60 \
  --scenario-delay-s 5 \
  --scenario-id assistant_acknowledgement_noise \
  --scenario-id urgent_with_chatter \
  --scenario-id speculative_claim \
  --scenario-id assistant_inferred \
  --scenario-id access_reinforced_low_signal \
  --scenario-id clear_constraint \
  --scenario-id urgent_event
./.venv/bin/python scripts/experiments/analyze_ciar_policy_runs.py \
  logs/ciar_challenge/ciar-exp-live-review-only-checkpoint-20260523-01 \
  --json-output logs/ciar_challenge/ciar-live-review-only-checkpoint-20260523.json \
  --markdown-output logs/ciar_challenge/ciar-live-review-only-checkpoint-20260523.md
```

## Acceptance Criteria

- Operational gate passes: required artifacts are present, provider health is
  checked, runtime setup is `ok`, and operational classification reports policy
  evidence.
- Positive controls promote at least one durable fact each.
- Residue scenarios do not promote assistant/user acknowledgement residue.
- Speculative/inferred scenarios do not promote speculative or inferred
  content; preferred result is review-only evidence with matching flags.
- Recency/access low-signal content does not promote. Missing guardrail flags
  are acceptable if live extraction does not provide `access_count`.

## Reporting

Create `docs/reports/2026-05-23-ciar-live-review-only-checkpoint-report.md`
after execution with run ID, model, provider health, runtime setup status,
operational classification, per-scenario outcomes, analyzer output, and the
recommendation for next CIAR work.
