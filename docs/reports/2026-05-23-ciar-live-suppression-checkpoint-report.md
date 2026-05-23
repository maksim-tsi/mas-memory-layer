# CIAR Live Suppression Checkpoint Report

Date: 2026-05-23
Status: Completed; checkpoint acceptance not met
Related plan: `docs/plan/2026-05-23-ciar-live-suppression-checkpoint-plan.md`

## Summary

The focused live suppression checkpoint was rerun after environment repair. The
checkpoint produced two completed live policy-evidence runs and one incomplete
run, but it did not validate live supersession behavior.

The key policy result is negative: live extraction did not produce separate
old/current facts for the focused scenarios, and the aggregate suppression
evaluation recorded zero suppressed facts. Do not use this checkpoint to justify
CIAR policy/default changes. The next CIAR work should focus on live
segmentation/extraction robustness for the suppression fixtures before policy
planning resumes.

No CIAR scoring, prompts, policy defaults, storage adapters, dependency
manifests, or runtime defaults were changed.

## Environment Repair

Before the rerun, the local environment was repaired with explicit user
approval:

- `.env` service URL construction was sanitized without printing secret values.
- `.env.example` was updated to avoid inline-comment path construction issues
  and to provide concrete service URL examples.
- `.venv` was synchronized from the existing Poetry lockfile with
  `/Users/max/.local/bin/poetry install --with test,dev`.

The Poetry sync installed packages already declared/resolved by the project,
including the missing OpenRouter dependency path. Dependency manifests were not
changed.

## Preflight Result

Environment checks passed:

```bash
uname -a && hostname && pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/python scripts/experiments/run_ciar_challenge_with_env.py --presence-only
```

The wrapper presence check printed key names/presence only. No secret values
were printed.

Focused script verification after `.venv` synchronization passed:

```bash
./.venv/bin/pytest tests/scripts/test_ciar_challenge_with_env.py tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_policy_analysis.py -v
```

Result: `28 passed`.

## Live Runs

All runs used:

- model: `tencent/hy3-preview`
- promotion policy: `hybrid_gate`
- contradiction policy: `suppress_superseded`
- scenarios: `contradiction_update`, `repeated_correction`
- provider health: required

| Run ID | Result | Operational classification | Notes |
|---|---:|---|---|
| `ciar-exp-live-suppression-checkpoint-20260523-01` | completed | `policy_evidence` | Provider health passed. `contradiction_update` promoted one summary-style fact. `repeated_correction` did not promote its segment. |
| `ciar-exp-live-suppression-checkpoint-20260523-02` | completed | `policy_evidence` | Required Redis timeout retry; completed with `--redis-timeout 60`. Same policy pattern as run `-01`. |
| `ciar-exp-live-suppression-checkpoint-20260523-03` | incomplete | `incomplete` | Provider health passed, but setup failed on Redis timeout even with `--redis-timeout 120`; required policy artifacts were missing. |

Aggregate artifacts:

- `logs/ciar_challenge/ciar-live-suppression-checkpoint-20260523.json`
- `logs/ciar_challenge/ciar-live-suppression-checkpoint-20260523.md`

Aggregate run-quality counts:

```json
{
  "policy_evidence": 2,
  "incomplete": 1
}
```

## Suppression Result

The aggregate suppression evaluation for
`hybrid_gate+suppress_superseded` showed:

| Scenario | Runs | Facts promoted | Facts suppressed | Interpretation |
|---|---:|---:|---:|---|
| `contradiction_update` | 2 | 2 | 0 | Live extraction produced one combined summary fact per completed run, not separable old/current facts. |
| `repeated_correction` | 2 | 0 | 0 | Live segmentation scored the scenario below the promotion threshold in both completed runs. |

Observed `repeated_correction` live segment scores:

- run `-01`: CIAR score `0.5`, threshold `0.6`, decision `IGNORE`
- run `-02`: CIAR score `0.5`, threshold `0.6`, decision `IGNORE`

No `fact_suppressed` events were recorded in the completed live runs.

## Acceptance Status

| Criterion | Status | Notes |
|---|---|---|
| All 3 runs complete with required artifacts and no scenario errors | Not met | Run `-03` is incomplete because Redis setup timed out. |
| Provider health checked and passes for each run | Met for attempted runs | Provider health passed before scenario execution/setup failure. |
| At least 2 of 3 runs are policy evidence | Met | Runs `-01` and `-02` are classified as `policy_evidence`. |
| Usable facts for both focused scenarios in at least 2 of 3 runs | Not met | `repeated_correction` produced no facts; `contradiction_update` produced combined summary facts only. |
| At least one auditable suppressed fact | Not met | Suppression count is zero across the aggregate. |

## Operational Notes

- Redis connectivity was unstable during the checkpoint. Run `-02` completed
  only after increasing Redis timeout to 60 seconds; run `-03` failed even with
  120 seconds.
- Non-blocking OpenInference instrumentation warnings appeared during live
  startup.
- LLM extraction parse warnings appeared in live console output and resulted in
  fallback-style summary facts, but the current artifacts still classified the
  completed runs as `policy_evidence`. A follow-up should consider persisting
  extraction fallback/parse-warning evidence into events or the manifest so the
  operational classifier can mark those runs more conservatively.

## Recommendation

Pause CIAR policy/default planning based on this checkpoint. The dry harness is
working, but the live path does not yet exercise the intended suppression
behavior.

Recommended next work:

1. Add a live robustness batch for focused suppression fixtures, starting with
   `repeated_correction` segment promotion and separable fact extraction for
   `contradiction_update`.
2. Improve artifact-level recording of LLM extraction parse/fallback warnings so
   live operational classification does not depend on console logs.
3. Investigate Redis connectivity/timeouts before the next multi-run live
   checkpoint.
