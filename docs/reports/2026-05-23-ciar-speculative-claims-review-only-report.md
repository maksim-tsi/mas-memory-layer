# CIAR Speculative Claims Review-Only Report

Date: 2026-05-23

## Summary

Batch 5 is implemented. Speculative and assistant-inferred facts are now
observable as `review_only` under `hybrid_gate`, while explicit durable facts
remain store-eligible.

## Changed Behavior

- Added `EvidenceRanker` flags:
  - `speculative_claim`;
  - `assistant_inference`.
- `hybrid_gate` now sends speculative and inferred facts to `REVIEW_ONLY` even
  when their raw CIAR score would otherwise pass.
- Explicit equivalents such as direct user preferences or confirmed operational
  facts remain eligible for storage.
- Dry `speculative_claim` and `assistant_inferred` scenarios now reach fact
  extraction so the review-only decision is visible in artifacts.
- Analyzer output now includes:
  - top-level `speculative_evaluation` JSON;
  - `## Speculative Evaluation` markdown.
- Updated the CIAR coordination plan with `CIAR-REV-1`.

## Dry Evidence

Focused dry run:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-speculative-review-only-20260523-01 \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode off \
  --scenario-id speculative_claim \
  --scenario-id assistant_inferred \
  --scenario-id clear_constraint \
  --scenario-id urgent_event
```

Results:

- `speculative_claim`: `segments_promoted=1`, `facts_extracted=1`,
  `facts_promoted=0`, `facts_review_only=1`.
- `assistant_inferred`: `segments_promoted=1`, `facts_extracted=1`,
  `facts_promoted=0`, `facts_review_only=1`.
- `clear_constraint`: `facts_promoted=1`.
- `urgent_event`: `facts_promoted=1`.
- Analyzer speculative evaluation showed zero speculative/inference promoted
  rows and one review-only row for each focused review scenario.

Artifacts:

- `logs/ciar_challenge/ciar-exp-dry-speculative-review-only-20260523-01`
- `logs/ciar_challenge/ciar-speculative-review-only-20260523.json`
- `logs/ciar_challenge/ciar-speculative-review-only-20260523.md`

The dry run was classified as `policy_evidence_with_warnings` only because the
sandbox blocked Phoenix span export during a dry run; policy artifacts were
complete and scenario errors were zero.

## Verification

```bash
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/memory/engines/test_promotion_engine.py tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_policy_analysis.py -v
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
./.venv/bin/pytest tests/ -v
```

Results:

- `ruff check .`: passed.
- Targeted tests: `48 passed`.
- CIAR regression pack: `152 passed`.
- Full suite: `666 passed, 139 skipped`.

## Remaining Follow-ups

- Live validation is intentionally deferred until after Batch 6 unless we choose
  to add an interim live review-only checkpoint.
- If live extraction emits speculative phrasing for a fact the user later
  confirms, the speculative fact remains review-only until a confirmed durable
  fact is extracted.
