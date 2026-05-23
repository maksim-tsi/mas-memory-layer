# Current State Before CIAR Implementation

Date: 2026-05-19
Branch: `dev-tests`
Status: Ready to proceed after commit and push

## Summary

The repository is ready for the next CIAR implementation phase after this
checkpoint. The current work prepared the CIAR challenge experiment harness,
validated OpenRouter model connectivity, corrected the test suite for the
current `skz-data-lv` topology, and documented the experiment plan and current
results.

No secret values were committed. The local `.env` remains ignored and outside
Git tracking.

## Runtime Topology

Current active topology:

- `skz-data-lv` / `DATA_NODE_IP=192.168.107.187` is the active data/runtime node.
- `skz-dev-lv` and `skz-cloud-lv` are temporarily powered off.
- Redis, PostgreSQL, Qdrant, Neo4j, Typesense, and Phoenix are expected on
  `skz-data-lv`.

The v2 E2E suite no longer requires `CLOUD_NODE_IP` at collection time. Live E2E
tests now skip cleanly when data-node credentials are absent instead of breaking
the full unit suite.

## OpenRouter Model Decision

OpenRouter connectivity was validated through
`scripts/check_openrouter_grok_connectivity.py`.

Observed model results:

- `x-ai/grok-4.1-fast`: OpenRouter health succeeds, but generation fails because
  the model is deprecated.
- `x-ai/grok-4.3`: passes the CIAR smoke check.
- `tencent/hy3-preview`: passes the CIAR smoke check when given a larger output
  budget.

Selected CIAR test model:

```text
tencent/hy3-preview
```

The CIAR segmentation and extraction paths default to an 8192 output-token
budget, which is sufficient for this model. For live runs, use:

```bash
MAS_OPENROUTER_TIMEOUT=120
```

## Experiment Artifacts

Documented plan:

```text
docs/plan/2026-05-19-ciar-challenge-experiment-execution-plan.md
```

Documented results so far:

```text
docs/reports/2026-05-19-ciar-challenge-experiment-results.md
```

Dry-run artifact directory:

```text
logs/ciar_challenge/ciar-exp-dry-current-20260519-01
```

The dry run is coherent and demonstrates two expected CIAR limitations:

1. CIAR does not resolve contradiction or supersession.
2. Segment-level scoring can dominate fact-level quality signals.

The focused live experiment remains to be rerun with data-node credentials and
the selected Tencent model.

## Verification

The following checks passed:

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest tests/ -v
```

Full suite result:

```text
594 passed, 140 skipped
```

The skipped tests are integration/live-backend tests that require explicit
runtime credentials or `--run-integration`.

## Recommended Next Command

After this checkpoint is pushed, run the focused live CIAR experiment with:

```bash
MAS_OPENROUTER_TIMEOUT=120 ./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --run-id ciar-exp-live-focused-tencent-20260519-01 \
  --model tencent/hy3-preview \
  --phoenix-endpoint http://192.168.107.187:6006/v1/traces \
  --phoenix-project-name ciar-challenge-focused-tencent-20260519-01 \
  --scenario-id segment_mismatch \
  --scenario-id contradiction_update \
  --scenario-id small_talk
```

Proceed to implementation only after the live artifacts show scenario-derived
facts, non-empty CIAR calls, and Phoenix traces for segmentation, extraction,
and scoring.
