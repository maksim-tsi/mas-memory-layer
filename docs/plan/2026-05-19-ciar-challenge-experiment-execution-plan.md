# CIAR Challenge Experiment Execution Plan

Date: 2026-05-19
Status: Execution ready
Related: `docs/reports/2026-05-18-ciar-design-and-implementation-audit.md`, `scripts/experiments/run_ciar_challenge.py`

## Summary

This plan validates the current CIAR challenge harness before using live results
as evidence for CIAR policy decisions. The goal is not to change CIAR runtime
behavior during the experiment. The goal is to collect clean evidence about
where CIAR v1 works as a deterministic L1 -> L2 gate and where it fails as a
broader memory policy.

The experiment must produce local artifacts under `logs/ciar_challenge/` and
Phoenix traces for live runs. After execution, the results must be documented in
a dedicated report under `docs/reports/`.

## Scope

In scope:

- Run the current isolated CIAR challenge harness.
- Verify dry-run behavior with deterministic canned scenarios.
- Run a focused live scenario set against the configured LLM provider, DBMS
  services, and Phoenix endpoint.
- Inspect generated artifacts for promotion decisions, CIAR calls, fallback
  behavior, and cleanup status.
- Document experiment results and interpretation in `docs/reports/`.

Out of scope:

- Changing `src/storage/` or other mechanism-layer adapters.
- Changing dependencies or lockfiles.
- Reading or printing `.env` or secret values.
- Treating one live run as benchmark-grade statistical evidence.

## Experiment Questions

1. Does the current harness produce coherent dry-run evidence after the latest
   changes?
2. Can a focused live run produce non-fallback facts and Phoenix spans for topic
   segmentation, fact extraction, and CIAR scoring?
3. Does the focused live run show the expected CIAR weaknesses:
   contradiction blindness and segment-level gating that may admit weak facts?
4. Are artifacts strong enough to support the next implementation step:
   explicit promotion policy modes and an evidence-ranking layer above CIAR?

## Required Execution Sequence

### 1. Dry-run validation

Run the harness in dry mode with the current code:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-current-<timestamp> \
  --phoenix-access-mode ssh_tunnel
```

Expected results:

- `summary.md`, `promotion_results.json`, `l2_facts.json`,
  `alternative_scores.json`, `events.jsonl`, `ciar_calls.jsonl`, and
  `run_manifest.json` are written under the run directory.
- High-value scenarios promote facts.
- low-value and speculative scenarios do not promote facts.
- `contradiction_update` promotes both old and corrected facts, demonstrating
  that CIAR does not resolve truth or supersession by itself.
- `segment_mismatch` exposes whether fact-level scores remain honest or are
  inflated by segment-level inheritance/flooring.

### 2. Focused live run

Run only the scenarios that test the known policy edge cases:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --run-id ciar-exp-live-focused-<timestamp> \
  --model tencent/hy3-preview \
  --phoenix-endpoint http://192.168.107.187:6006/v1/traces \
  --phoenix-project-name ciar-challenge-focused-<timestamp> \
  --scenario-id segment_mismatch \
  --scenario-id contradiction_update \
  --scenario-id small_talk
```

Expected results:

- Phoenix UI is reachable and the run manifest records a successful UI check.
- Provider health is recorded unless explicitly skipped.
- The run manifest records `model=tencent/hy3-preview`.
- Live promoted facts are derived from scenario content, not filler turns.
- `ciar_calls.jsonl` exists and contains observed CIAR scoring calls.
- `alternative_scores.json` contains rows with raw fact CIAR, stored CIAR, and
  evidence quality flags.
- The Phoenix project contains experiment spans named:
  - `yaam.experiment.ciar_challenge`
  - `yaam.experiment.node.*`
  - `yaam.llm.topic_segment`
  - `yaam.llm.fact_extract`
  - `yaam.ciar.score`
- Cleanup either succeeds or records a clearly actionable cleanup defect.

## Artifact Review Checklist

For each run, inspect:

- `summary.md`: scenario-level promoted segment and fact counts.
- `promotion_results.json`: errors, extracted facts, promoted facts, filtered
  facts.
- `l2_facts.json`: fact content, source type, CIAR score, certainty, impact,
  topic segment metadata.
- `alternative_scores.json`: `raw_fact_ciar`, `current_runtime_ciar`,
  `fact_gate_decision`, `floor_applied`, and evidence flags.
- `ciar_calls.jsonl`: one record per fact-level CIAR scorer call.
- `events.jsonl`: significance scoring and fact promotion events.
- `run_manifest.json`: model, Phoenix project, endpoint, provider health,
  cleanup status.

## Result Report Requirement

After the focused live run, create a report in `docs/reports/` named:

```text
docs/reports/2026-05-19-ciar-challenge-experiment-results.md
```

The report must include:

- Commands run.
- Artifact directories.
- Phoenix project name.
- Scenario outcomes.
- Whether live facts came from scenario content or fallback/filler content.
- Whether fact-level CIAR calls were observed.
- Whether cleanup succeeded.
- Interpretation against the audit findings.
- Recommendation for the next implementation step.

The report must clearly distinguish dry-run evidence, live smoke evidence, and
research-grade evidence. If the live run is dirty or fallback-driven, the report
must say so and must not present it as proof of CIAR behavior.

## Decision Gates

Proceed to implementation only if the focused live run is clean enough to
support the conclusion.

If the focused live run is clean:

- Implement low-risk CIAR conformance and observability fixes.
- Add explicit promotion policy mode tests.
- Start an `EvidenceRanker` plan above tier retrieval.

If the focused live run is dirty:

- Fix the experiment harness or runtime configuration first.
- Re-run the focused live scenarios.
- Document the failed run as an operational finding, not a CIAR policy finding.
