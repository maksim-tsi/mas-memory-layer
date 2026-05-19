# CIAR Challenge Experiment Results

Date: 2026-05-19
Status: Dry validation complete; focused live run blocked at preflight
Related plan: `docs/plan/2026-05-19-ciar-challenge-experiment-execution-plan.md`

## Summary

The current CIAR challenge harness produced coherent dry-run artifacts with the
latest session-id separator and deterministic scenario behavior. The focused
live run did not execute provider, Redis, PostgreSQL, or Phoenix experiment
paths because required environment variables were not present in the shell.

This report therefore provides dry-run evidence and an operational live-run
blocker. It does not claim research-grade live evidence for CIAR behavior.

## Commands Run

Environment and interpreter verification:

```bash
uname -a && hostname && pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
```

Targeted harness test:

```bash
./.venv/bin/pytest tests/scripts/test_ciar_challenge_experiment.py -v
```

Dry validation:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-current-20260519-01 \
  --phoenix-access-mode ssh_tunnel
```

Focused live attempt:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --run-id ciar-exp-live-focused-20260519-01 \
  --phoenix-endpoint http://192.168.107.187:6006/v1/traces \
  --phoenix-project-name ciar-challenge-focused-20260519-01 \
  --scenario-id segment_mismatch \
  --scenario-id contradiction_update \
  --scenario-id small_talk
```

## Verification Results

Host verification passed on the local MacBook checkout.

The repository virtual environment exists and the interpreter resolved to:

```text
./.venv/bin/python
```

The focused harness test passed:

```text
4 passed in 0.02s
```

## Dry-Run Artifacts

Artifact directory:

```text
logs/ciar_challenge/ciar-exp-dry-current-20260519-01
```

Generated files included:

- `summary.md`
- `promotion_results.json`
- `l2_facts.json`
- `alternative_scores.json`
- `events.jsonl`
- `ciar_calls.jsonl`
- `formula_probes.json`
- `run_manifest.json`
- `scenarios.json`

The dry manifest recorded missing live environment variables, which is expected
for a dry run in this shell:

```text
OPENROUTER_API_KEY=false
POSTGRES_URL=false
REDIS_URL=false
```

It also recorded that the SSH tunnel Phoenix UI check was blocked by sandbox
network restrictions. Because this was a dry run, the harness completed anyway.

## Dry-Run Scenario Outcomes

| Scenario | Expected | Segments Promoted | Facts Promoted | Floor Flags |
|---|---:|---:|---:|---:|
| clear_constraint | promote | 1 | 1 | 0 |
| speculative_claim | needs_review | 0 | 0 | 0 |
| small_talk | ignore | 0 | 0 | 0 |
| urgent_event | promote | 1 | 1 | 0 |
| contradiction_update | should_conflict | 1 | 2 | 0 |
| segment_mismatch | should_not_floor | 1 | 2 | 0 |
| assistant_inferred | needs_review | 0 | 0 | 0 |

Observed dry-run evidence:

- The new session-id separator is active, for example
  `ciar-exp-dry-current-20260519-01__segment_mismatch`.
- `ciar_calls.jsonl` contains 6 CIAR scorer calls.
- `events.jsonl` contains 13 telemetry events.
- `contradiction_update` promoted both the old Oakland route fact and the new
  Los Angeles correction, confirming the audit finding that CIAR does not
  resolve contradictions or supersession.
- `segment_mismatch` promoted both the urgent container exception and the
  low-value chatter fact. The chatter fact's stored CIAR remained high because
  promotion currently inherits segment-level certainty and impact before
  rescoring.

## Focused Live Attempt

Requested live scenarios:

- `segment_mismatch`
- `contradiction_update`
- `small_talk`

Requested Phoenix project:

```text
ciar-challenge-focused-20260519-01
```

The live attempt stopped during preflight with:

```text
RuntimeError: Missing required environment variables: OPENROUTER_API_KEY, REDIS_URL, POSTGRES_URL
```

The live run created an empty directory:

```text
logs/ciar_challenge/ciar-exp-live-focused-20260519-01
```

No live `run_manifest.json`, `summary.md`, `ciar_calls.jsonl`, or
`alternative_scores.json` were produced. No live CIAR behavior should be inferred
from this failed attempt.

## Interpretation

The dry run validates that the isolated harness is structurally useful and that
the current deterministic scenarios can expose two known CIAR limitations:

1. CIAR is a retention score, not a truth-resolution mechanism.
2. Current promotion behavior can let segment-level scoring dominate fact-level
   quality signals.

The live run remains blocked by environment setup in the execution shell. Under
the repository secret boundary, the agent did not read or source `.env`. The
operator must provide the required environment variables through an approved
runtime path before the focused live experiment can produce evidence.

## Required Follow-Up

Before presenting live CIAR evidence, rerun the focused live command from a
shell where these variables are already configured:

- `OPENROUTER_API_KEY`
- `REDIS_URL`
- `POSTGRES_URL`

The intended OpenRouter model for the rerun is:

```text
tencent/hy3-preview
```

The current CIAR topic segmentation and fact extraction paths allow an 8192
output-token budget, which is sufficient for the 5000-token smoke-test budget
used to validate this model.

The rerun should be checked for:

- scenario-derived facts instead of filler or fallback content;
- a non-empty `ciar_calls.jsonl`;
- Phoenix spans for `yaam.llm.topic_segment`, `yaam.llm.fact_extract`, and
  `yaam.ciar.score`;
- cleanup status in `run_manifest.json`;
- clear `alternative_scores.json` rows for the focused scenarios.

Only after a clean focused live run should implementation proceed on promotion
policy modes or an `EvidenceRanker`.
