# CIAR Recency/Access Guardrail Report

Date: 2026-05-23

## Summary

Batch 6 is implemented. `hybrid_gate` now treats access/recency reinforcement
as insufficient by itself when base CIAR evidence is weak: the fact remains
observable, but it is marked `review_only` instead of being stored.

## Changed Behavior

- Added `EvidenceRanker` component-aware flags:
  - `base_evidence_below_threshold`;
  - `access_boosted_over_threshold`;
  - `recency_access_guardrail`.
- Under `hybrid_gate`, facts become `REVIEW_ONLY` when base evidence is below
  the gate threshold, final CIAR crosses the gate through recency/access boost,
  and `recency_boost > 1.0`.
- Strong base evidence remains store-eligible even when frequently accessed.
- `fact_gate` and `segment_gate` storage semantics are unchanged; guardrail
  flags are diagnostic there.
- Added dry scenario `access_reinforced_low_signal`.
- Analyzer output now includes:
  - top-level `recency_access_evaluation` JSON;
  - `## Recency/Access Evaluation` markdown.
- Updated the CIAR coordination plan with `CIAR-REC-1`.

## Dry Evidence

Focused dry run:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-recency-access-guardrail-20260523-01 \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode off \
  --scenario-id access_reinforced_low_signal \
  --scenario-id clear_constraint \
  --scenario-id urgent_event
```

Results:

- `access_reinforced_low_signal`: `segments_promoted=1`,
  `facts_extracted=1`, `facts_promoted=0`, `facts_review_only=1`.
- The review-only row has `raw_fact_ciar=0.75`, `stored_ciar=null`,
  `base_evidence_below_threshold=true`, `access_boosted_over_threshold=true`,
  and `recency_access_guardrail=true`.
- `clear_constraint`: `facts_promoted=1`.
- `urgent_event`: `facts_promoted=1`.
- Analyzer `recency_access_evaluation` showed one guardrail review-only row and
  zero guardrail promoted rows.

Artifacts:

- `logs/ciar_challenge/ciar-exp-dry-recency-access-guardrail-20260523-01`
- `logs/ciar_challenge/ciar-recency-access-guardrail-20260523.json`
- `logs/ciar_challenge/ciar-recency-access-guardrail-20260523.md`

The first dry run was classified as `policy_evidence_with_warnings` because the
sandbox blocked Phoenix span export. Policy artifacts were complete and
scenario errors were zero.

## Phoenix Export Smoke

Escalated local-network smoke:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-recency-access-guardrail-phoenix-20260523-01 \
  --phoenix-endpoint http://192.168.107.187:6006/v1/traces \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode off \
  --scenario-id access_reinforced_low_signal \
  --scenario-id clear_constraint
```

Results:

- Command exited `0`.
- Phoenix export completed without sandbox `Operation not permitted` warnings.
- `access_reinforced_low_signal`: `facts_promoted=0`,
  `facts_review_only=1`.
- `clear_constraint`: `facts_promoted=1`.
- Operational classification: `policy_evidence`.

Artifacts:

- `logs/ciar_challenge/ciar-exp-dry-recency-access-guardrail-phoenix-20260523-01`

## Verification

```bash
uname -a
hostname
pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/memory/engines/test_promotion_engine.py tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_policy_analysis.py tests/memory/test_ciar_scorer.py -v
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
./.venv/bin/pytest tests/ -v
```

Results:

- `ruff check .`: passed.
- Targeted tests: `101 passed`.
- CIAR regression pack: `156 passed`.
- Full suite: `670 passed, 139 skipped`.

## Remaining Follow-ups

- No immediate policy blocker remains from Batch 6.
- Live LLM validation for Batches 4-6 can be grouped into the next CIAR live
  checkpoint if we want live evidence before default/policy decisions.
