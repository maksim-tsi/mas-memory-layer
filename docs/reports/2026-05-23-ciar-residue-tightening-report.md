# CIAR Residue Tightening Report

Date: 2026-05-23

## Summary

Batch 4 is implemented. `hybrid_gate` now treats assistant-action facts as
conversational residue even when they include domain terms, while preserving
store eligibility for durable operational facts extracted from the same segment.

## Changed Behavior

- Added residue subtype provenance in `EvidenceRanker`:
  - `residue_phrase`;
  - `low_value_mention`;
  - `low_value_chatter`;
  - `assistant_action_residue`.
- Kept `conversational_residue` as the aggregate flag consumed by policy
  analysis and experiment artifacts.
- Added deterministic dry-run facts for `assistant_acknowledgement_noise` and
  `urgent_with_chatter`.
- Added analyzer output:
  - top-level `residue_evaluation` JSON;
  - `## Residue Evaluation` markdown section.
- Updated the CIAR coordination plan with `CIAR-RES-1`.

## Dry Evidence

Focused dry run:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-residue-tightening-20260523-01 \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode off \
  --scenario-id small_talk \
  --scenario-id segment_mismatch \
  --scenario-id assistant_acknowledgement_noise \
  --scenario-id urgent_with_chatter
```

Results:

- `small_talk`: `facts_promoted=0`.
- `assistant_acknowledgement_noise`: `facts_promoted=0`.
- `segment_mismatch`: `facts_promoted=1`, `facts_review_only=1`.
- `urgent_with_chatter`: `facts_promoted=1`, `facts_review_only=1`.
- Analyzer residue evaluation showed `residue_promoted=0` and
  `residue_review_only=1` for both mixed operational/chatter scenarios.

Artifacts:

- `logs/ciar_challenge/ciar-exp-dry-residue-tightening-20260523-01`
- `logs/ciar_challenge/ciar-residue-tightening-20260523.json`
- `logs/ciar_challenge/ciar-residue-tightening-20260523.md`

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
- Targeted tests: `45 passed`.
- CIAR regression pack: `149 passed`.
- Full suite: `663 passed, 139 skipped`.

## Remaining Follow-ups

- Live validation is intentionally deferred until after Batches 5 and 6 unless
  we choose to add an interim live residue checkpoint.
- If live extraction emits only an assistant-action fact without a durable
  operational fact, keep the assistant-action fact review-only and treat the
  missing durable fact as extractor/prompt robustness evidence.
