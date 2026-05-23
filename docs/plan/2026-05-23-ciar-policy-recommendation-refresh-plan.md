# CIAR Policy Recommendation Refresh Plan

Date: 2026-05-23

## Summary

Refresh the CIAR policy recommendation using a fresh live LLM matrix, exported
Phoenix spans, and accumulated Batch 1-7 evidence.

This batch produces recommendation evidence only. It must not change CIAR
scoring, thresholds, policy defaults, contradiction policy, storage adapters,
dependencies, `.env`, prompts, or schemas.

## Key Changes

- Add a reusable read-only Phoenix span exporter:
  `scripts/debug/export_phoenix_spans.py`.
- Add mocked unit coverage for the exporter:
  `tests/scripts/test_export_phoenix_spans.py`.
- Run a six-run live matrix:
  - `hybrid_gate+off` twice;
  - `fact_gate+off` once;
  - `segment_gate+off` once;
  - `hybrid_gate+suppress_superseded` twice.
- Aggregate CIAR artifacts with `scripts/experiments/analyze_ciar_policy_runs.py`.
- Export Phoenix spans for every live project and summarize span counts.
- Create final recommendation report:
  `docs/reports/2026-05-23-ciar-policy-recommendation-refresh-report.md`.
- Update the CIAR coordination plan with `CIAR-DEF-3`.

## Live Matrix Defaults

- model: `tencent/hy3-preview`;
- provider health: required;
- Redis timeout: `60`;
- scenario delay: `5`;
- service URLs: current `.env` values;
- network: explicit escalation for LLM calls, YAAM data-node checks, Phoenix
  export, and Phoenix span reads.

If a run fails operationally before usable artifacts, run one replacement for
the same config with suffix `-replacement-01`. Do not rerun policy failures just
to improve results.

## Recommendation Rules

- Keep `hybrid_gate` as promotion default if both `hybrid_gate+off` runs are
  policy evidence, positive controls promote, and residue/speculative
  over-promotion is no worse than comparators.
- Keep contradiction default `off` unless both `hybrid_gate+suppress_superseded`
  runs cleanly suppress old facts while preserving current facts for both
  canonical suppression scenarios.
- Recommend `suppress_superseded` as opt-in, not default, if suppression
  succeeds only for `repeated_correction` or remains extraction-sensitive for
  `contradiction_update`.
- Treat missing live `recency_access_guardrail` as an observability limitation,
  not a policy failure, unless low-signal access content is promoted.

## Verification

```bash
uname -a
hostname
pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/python scripts/experiments/run_ciar_challenge_with_env.py --presence-only
./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env --json
./.venv/bin/pytest tests/scripts/test_export_phoenix_spans.py -v
./.venv/bin/pytest tests/scripts/test_export_phoenix_spans.py tests/scripts/test_ciar_policy_analysis.py -v
```

Run `./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py` only if
CIAR analyzer or harness behavior changes beyond the Phoenix exporter and docs.
