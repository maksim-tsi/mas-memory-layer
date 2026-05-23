# CIAR Operational Classification Plan

Date: 2026-05-23
Status: Implementation planned
Scope: CIAR challenge harness and policy-run analyzer

## Purpose

Add explicit run-quality classification to CIAR challenge experiment artifacts so
operators can distinguish policy evidence from operational noise without reading
console logs.

This batch is observability-only. It must not change CIAR scoring, promotion
policy, contradiction policy, storage adapters, runtime defaults, or secret
handling.

## Planned Changes

- Write `operational_classification` into each run's `run_manifest.json`.
- Include the classification in `summary.md`.
- Teach `scripts/experiments/analyze_ciar_policy_runs.py` to preserve per-run
  classifications and aggregate run-quality counts.
- Infer conservative classifications for older artifacts that do not yet have
  the new manifest field.

## Classification Shape

```json
{
  "run_quality": "policy_evidence",
  "policy_evidence": true,
  "reasons": ["clean run"],
  "signals": {
    "completed": true,
    "dry_run": false,
    "provider_health_status": "checked",
    "provider_fallback_detected": false,
    "phoenix_ui_ok": true,
    "artifact_complete": true,
    "cleanup_status": "ok",
    "scenario_errors": 0,
    "llm_response_warning_count": 0
  }
}
```

Allowed `run_quality` values:

- `policy_evidence`
- `policy_evidence_with_warnings`
- `operational_noise`
- `incomplete`

## Acceptance Criteria

- Completed clean dry runs classify as `policy_evidence`.
- Skipped provider health with a recorded reason classifies as
  `policy_evidence_with_warnings`, not operational noise.
- Rule fallback, invalid or empty LLM response evidence, provider failure
  evidence, or scenario errors classify as `operational_noise`.
- Missing completion or required artifacts classify as `incomplete`.
- Partial cleanup classifies as a warning unless artifacts cannot be
  interpreted.
- Historical artifacts without `operational_classification` do not break the
  analyzer.

## Verification Commands

```bash
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_policy_analysis.py -v
```
