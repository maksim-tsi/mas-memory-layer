# CIAR Focused Suppression Evaluation Report

Date: 2026-05-23

## Summary

Batch 3 added focused dry-run suppression evaluation for the canonical CIAR
contradiction scenarios: `contradiction_update` and `repeated_correction`.

The batch stayed in the analyzer, tests, and docs. It did not change CIAR
scoring, `hybrid_gate`, `ContradictionPolicy`, storage adapters, runtime
defaults, dependencies, or `.env` handling.

## Changes Implemented

- Added plan: `docs/plan/2026-05-23-ciar-focused-suppression-evaluation-plan.md`.
- Extended `scripts/experiments/analyze_ciar_policy_runs.py` with:
  - top-level `suppression_evaluation` JSON output;
  - `## Suppression Evaluation` markdown rendering;
  - per-config/per-scenario runs, promoted facts, suppressed facts,
    suppression rate, promoted contents, and suppressed contents.
- Extended `tests/scripts/test_ciar_policy_analysis.py` to cover focused
  suppression aggregation, markdown rendering, and partial/older runs without
  focused scenarios.
- Updated the CIAR coordination plan with `CIAR-SUP-3` as complete locally.

## Dry Matrix Results

Artifacts:

- `logs/ciar_challenge/ciar-exp-dry-suppression-eval-off-20260523-01`
- `logs/ciar_challenge/ciar-exp-dry-suppression-eval-metadata-20260523-01`
- `logs/ciar_challenge/ciar-exp-dry-suppression-eval-suppress-20260523-01`
- Analyzer JSON: `logs/ciar_challenge/ciar-sup3-analysis-20260523.json`
- Analyzer markdown: `logs/ciar_challenge/ciar-sup3-analysis-20260523.md`

Observed focused suppression summary:

| Config | Scenario | Facts Promoted | Facts Suppressed | Suppression Rate |
|---|---|---:|---:|---:|
| `hybrid_gate+off` | `contradiction_update` | 2 | 0 | 0.00% |
| `hybrid_gate+off` | `repeated_correction` | 3 | 0 | 0.00% |
| `hybrid_gate+metadata_only` | `contradiction_update` | 2 | 0 | 0.00% |
| `hybrid_gate+metadata_only` | `repeated_correction` | 3 | 0 | 0.00% |
| `hybrid_gate+suppress_superseded` | `contradiction_update` | 1 | 1 | 50.00% |
| `hybrid_gate+suppress_superseded` | `repeated_correction` | 1 | 2 | 66.67% |

For `hybrid_gate+suppress_superseded`, the analyzer reported:

- `contradiction_update`: stored current Los Angeles route; suppressed prior
  Oakland route.
- `repeated_correction`: stored latest Long Beach route; suppressed prior
  Oakland and Los Angeles routes.

All three dry runs were classified as `policy_evidence_with_warnings` because
Phoenix UI/export was unavailable in the sandbox. The policy artifacts were
complete and matched the acceptance target.

## Verification

Environment checks:

```bash
uname -a && hostname && pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
```

The interpreter resolved to this repository's virtual environment:

```text
.venv/bin/python
```

Lint:

```bash
./.venv/bin/ruff check .
```

Result: passed.

Targeted tests:

```bash
./.venv/bin/pytest tests/scripts/test_ciar_policy_analysis.py tests/scripts/test_ciar_challenge_experiment.py -v
```

Result: `22 passed`.

Canonical CIAR regression pack:

```bash
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
```

Result: ruff passed and CIAR pytest pack passed with `141 passed`.

## Remaining Follow-Ups

- Optional live LLM suppression evaluation can be planned separately with
  explicit provider/network approval.
- Phoenix export/UI availability remains an operational sandbox concern, not a
  CIAR suppression policy blocker.
