# Batch 6 Plan: CIAR Recency/Access Guardrail

## Purpose

Add a `hybrid_gate` guardrail so access/recency reinforcement cannot turn weak base evidence into stored L2 facts by itself.

The policy distinction should be visible in experiment artifacts: the CIAR formula may still boost frequently accessed facts, but `hybrid_gate` should mark low-base evidence as review-only when recency/access is the reason it crosses the storage threshold.

## Scope

In scope:

- Extend `EvidenceRanker` policy evidence flags with base-score and recency/access guardrail diagnostics.
- Add deterministic dry evidence for a low-base, high-access fact.
- Extend the CIAR policy analyzer with a backward-compatible recency/access evaluation section.
- Add focused tests for policy behavior, dry harness artifacts, and analyzer aggregation.
- Record local verification and Phoenix export smoke evidence.

Out of scope:

- CIAR scoring formula changes.
- Recency boost math or threshold changes.
- Promotion-mode default changes.
- Contradiction policy changes.
- Storage adapters, DB schemas, provider routing, dependencies, or `.env` behavior changes.

## Expected Behavior

- Under `hybrid_gate`, a fact with `base_score < gate_threshold`, `final_score >= gate_threshold`, and `recency_boost > 1.0` becomes `REVIEW_ONLY`.
- The review-only row includes `base_evidence_below_threshold=true`, `access_boosted_over_threshold=true`, and `recency_access_guardrail=true`.
- Strong base evidence remains store-eligible even when frequently accessed.
- `fact_gate` and `segment_gate` keep their existing storage semantics, with diagnostic flags only.

## Verification Commands

```bash
uname -a
hostname
pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/memory/engines/test_promotion_engine.py tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_policy_analysis.py tests/memory/test_ciar_scorer.py -v
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-recency-access-guardrail-20260523-01 \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode off \
  --scenario-id access_reinforced_low_signal \
  --scenario-id clear_constraint \
  --scenario-id urgent_event
./.venv/bin/python scripts/experiments/analyze_ciar_policy_runs.py \
  logs/ciar_challenge/ciar-exp-dry-recency-access-guardrail-20260523-01 \
  --json-output logs/ciar_challenge/ciar-recency-access-guardrail-20260523.json \
  --markdown-output logs/ciar_challenge/ciar-recency-access-guardrail-20260523.md
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
./.venv/bin/pytest tests/ -v
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-recency-access-guardrail-phoenix-20260523-01 \
  --phoenix-endpoint http://192.168.107.187:6006/v1/traces \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode off \
  --scenario-id access_reinforced_low_signal \
  --scenario-id clear_constraint
```

## Acceptance Criteria

- Focused dry run classifies `access_reinforced_low_signal` as extracted and review-only, not promoted.
- Positive controls still promote normally.
- `alternative_scores.json` carries recency/access guardrail flags.
- Analyzer JSON and markdown include recency/access evaluation.
- CIAR regression pack and full suite remain green.
- Phoenix export smoke is attempted and documented as observability evidence.
