# CIAR Speculative Claims Review-Only Plan

Date: 2026-05-23

## Purpose

Batch 5 makes speculative and assistant-inferred CIAR facts observable as
`review_only` under `hybrid_gate`, rather than silently skipping them at segment
gate or storing them as durable facts.

## Scope

This batch may change the promotion evidence ranker, CIAR experiment harness,
CIAR policy analyzer, focused tests, and CIAR coordination documentation. It
must not change CIAR scoring formula, thresholds, promotion-mode defaults,
contradiction policy, storage adapters, DB schemas, provider routing,
dependencies, or `.env` behavior.

## Implementation Plan

- Extend `EvidenceRanker` with uncertainty and inference flags:
  - `speculative_claim` for terms such as `might`, `maybe`, `possibly`,
    `could`, `not sure`, `unconfirmed`, and `suspected`.
  - `assistant_inference` for inferred user-preference phrasing such as
    `likely prefers`, `probably prefers`, and `appears to prefer`.
- Under `hybrid_gate`, make speculative or inferred facts `REVIEW_ONLY` even
  when raw CIAR would otherwise pass.
- Preserve storage eligibility for explicit durable facts, such as confirmed
  supplier misses or directly stated user preferences.
- Make `speculative_claim` and `assistant_inferred` dry scenarios reach fact
  extraction while keeping extracted facts review-only.
- Add analyzer output for speculative review-only evidence.
- Update the CIAR coordination plan with `CIAR-REV-1` after verification.

## Acceptance Criteria

- Focused dry `hybrid_gate+off` run promotes zero speculative/inferred facts and
  marks each as review-only.
- Positive controls such as `clear_constraint` and `urgent_event` still promote
  durable operational facts.
- `alternative_scores.json` includes review-only rows with uncertainty flags.
- Existing residue, suppression, repeated-correction, regression-pack, and
  full-suite behavior remains green.

## Verification Commands

```bash
uname -a
hostname
pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/memory/engines/test_promotion_engine.py tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_policy_analysis.py -v
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-speculative-review-only-20260523-01 \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode off \
  --scenario-id speculative_claim \
  --scenario-id assistant_inferred \
  --scenario-id clear_constraint \
  --scenario-id urgent_event
./.venv/bin/python scripts/experiments/analyze_ciar_policy_runs.py \
  logs/ciar_challenge/ciar-exp-dry-speculative-review-only-20260523-01 \
  --json-output logs/ciar_challenge/ciar-speculative-review-only-20260523.json \
  --markdown-output logs/ciar_challenge/ciar-speculative-review-only-20260523.md
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
./.venv/bin/pytest tests/ -v
```

## Assumptions

- `needs_review` means extracted but not stored.
- This batch is dry-first; live validation can be grouped after Batches 5 and 6.
- Speculative phrasing remains review-only until a confirmed durable fact is
  extracted.
