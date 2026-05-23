# CIAR Repeated Correction Repair Plan

Date: 2026-05-23
Status: Implementation planned
Scope: CIAR challenge scenario reliability

## Purpose

Make the `repeated_correction` CIAR challenge scenario reliably observable in
dry runs and more legible for live LLM runs. The repaired scenario should show
latest-correction behavior directly: old and intermediate route facts are
suppressed, and the latest route remains stored.

This batch repairs the scenario fixture and dry-run harness only. It must not
change CIAR scoring, `hybrid_gate`, `ContradictionPolicy`, storage behavior, or
runtime defaults.

## Planned Changes

- Rewrite `repeated_correction` turns to make the shipment anchor and route
  supersession explicit.
- Add a dedicated `CannedTopicSegmenter` branch for `repeated_correction` with
  high certainty and impact.
- Add a dedicated `CannedFactExtractor` branch that returns exactly three route
  facts for Oakland, Los Angeles, and Long Beach.
- Add focused tests proving dry `hybrid_gate + suppress_superseded` produces
  one stored latest fact and two suppressed prior facts.
- Update the CIAR coordination plan with `CIAR-SCEN-1`.

## Acceptance Criteria

Focused dry command:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-repeated-correction-repair-20260523-01 \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode suppress_superseded \
  --scenario-id repeated_correction
```

Expected `promotion_results.json` for `repeated_correction`:

- `segments_promoted = 1`
- `facts_extracted = 3`
- `facts_promoted = 1`
- `facts_suppressed = 2`

Expected `alternative_scores.json`:

- two rows with `suppressed=true`;
- one stored row for the latest Long Beach route.

## Verification Commands

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest tests/scripts/test_ciar_challenge_experiment.py tests/memory/test_contradiction_policy.py tests/memory/engines/test_promotion_engine.py -v
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
```
