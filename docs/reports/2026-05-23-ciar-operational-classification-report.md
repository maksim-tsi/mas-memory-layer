# CIAR Operational Classification Report

Date: 2026-05-23
Status: Complete
Related plan: `docs/plan/2026-05-23-ciar-operational-classification-plan.md`

## Summary

Implemented Batch 1 for CIAR operational classification. CIAR challenge runs now
write an `operational_classification` block into `run_manifest.json`, include
the same classification in `summary.md`, and expose run-quality counts through
the policy-run analyzer.

The change is observability-only. It does not change CIAR scoring, promotion
policy defaults, contradiction policy defaults, storage adapters, provider
routing, or `.env` handling.

## Behavior Added

Run manifests now classify experiment quality as one of:

- `policy_evidence`
- `policy_evidence_with_warnings`
- `operational_noise`
- `incomplete`

The classifier records:

- whether the run completed;
- whether required artifacts exist;
- provider-health status;
- Phoenix UI reachability status;
- cleanup status;
- scenario error count;
- provider fallback or LLM response warning evidence.

The analyzer now:

- preserves per-run `operational_classification`;
- infers conservative classifications for historical artifacts without the new
  manifest field;
- emits aggregate `run_quality_counts`;
- renders a `Run Quality` section in markdown reports.

## Verification

Environment verification:

```text
Darwin MacBook-Pro.local 25.5.0 Darwin Kernel Version 25.5.0: Mon Apr 27 20:41:26 PDT 2026; root:xnu-12377.121.6~2/RELEASE_ARM64_T8132 arm64
MacBook-Pro.local
/Users/max/Documents/code/mas-memory-layer
/Users/max/Documents/code/mas-memory-layer/.venv/bin/python
```

Ruff:

```text
./.venv/bin/ruff check .
All checks passed!
```

Targeted tests:

```text
./.venv/bin/pytest tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_policy_analysis.py -v
18 passed in 2.11s
```

## Follow-Up

- Use the new classification in future CIAR live-run reports before treating a
  run as policy evidence.
- Keep refining detection markers if future providers surface new fallback or
  invalid-response signatures in `events.jsonl`.
- Full repository tests were not run because this batch changed only scripts,
  script tests, and documentation.
