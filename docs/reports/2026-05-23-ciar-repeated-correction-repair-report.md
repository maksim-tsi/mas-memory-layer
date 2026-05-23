# CIAR Repeated Correction Repair Report

Date: 2026-05-23

## Summary

Batch 2 repaired the `repeated_correction` CIAR challenge fixture so focused dry-run evidence is deterministic and directly shows latest-correction behavior under `hybrid_gate` plus `suppress_superseded`.

The batch stayed in the experiment harness, tests, and docs. It did not change CIAR scoring, `hybrid_gate`, `ContradictionPolicy`, storage adapters, runtime defaults, dependencies, or `.env` handling.

## Changes Implemented

- Added plan: `docs/plan/2026-05-23-ciar-repeated-correction-repair-plan.md`.
- Updated `scripts/experiments/run_ciar_challenge.py`:
  - made `repeated_correction` turns explicit around shipment `ALFA-4421`;
  - anchored routes as Oakland, Los Angeles, then Long Beach;
  - added a dedicated canned segmenter branch for dry-run observability;
  - added a dedicated canned extractor branch returning exactly three route facts.
- Extended `tests/scripts/test_ciar_challenge_experiment.py`:
  - confirmed `repeated_correction` remains a default `should_conflict` scenario;
  - covered the dedicated canned extractor output;
  - covered focused dry `hybrid_gate` plus `suppress_superseded` behavior;
  - kept coverage for suppressed rows recorded through alternative scoring.
- Updated `docs/plan/2026-05-19-ciar-challenge-experiment-execution-plan.md` with `CIAR-SCEN-1` as complete locally.

## Focused Dry-Run Result

Command:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-repeated-correction-repair-20260523-01 \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode suppress_superseded \
  --scenario-id repeated_correction
```

Result artifacts: `logs/ciar_challenge/ciar-exp-dry-repeated-correction-repair-20260523-01`.

Observed scenario stats:

| Scenario | Segments Promoted | Facts Extracted | Facts Promoted | Facts Suppressed | Errors |
|---|---:|---:|---:|---:|---:|
| `repeated_correction` | 1 | 3 | 1 | 2 | 0 |

Observed stored fact:

- `Latest correction: shipment ALFA-4421 is now routed to Long Beach instead of Los Angeles or Oakland.`

Observed suppressed facts:

- `Shipment ALFA-4421 was scheduled for Oakland.`
- `Update: shipment ALFA-4421 is now routed to Los Angeles.`

The run manifest classified the run as `policy_evidence_with_warnings` because Phoenix UI/export was unavailable in the sandboxed dry run. The dry-run policy evidence itself was complete and matched the acceptance target.

## Verification

Environment checks:

```bash
uname -a && hostname && pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
```

The interpreter resolved to the repository virtual environment:

```text
/Users/max/Documents/code/mas-memory-layer/.venv/bin/python
```

Lint:

```bash
./.venv/bin/ruff check .
```

Result: passed.

Targeted tests:

```bash
./.venv/bin/pytest tests/scripts/test_ciar_challenge_experiment.py tests/memory/test_contradiction_policy.py tests/memory/engines/test_promotion_engine.py -v
```

Result: `39 passed`.

Canonical CIAR regression pack:

```bash
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
```

Result: ruff passed and CIAR pytest pack passed with `139 passed`.

## Remaining Follow-Ups

- Live LLM reruns can be performed separately to evaluate whether the more explicit scenario wording improves provider extraction reliability.
- Phoenix export/UI availability remains an operational environment concern for sandboxed dry runs, not a blocker for this fixture repair.
