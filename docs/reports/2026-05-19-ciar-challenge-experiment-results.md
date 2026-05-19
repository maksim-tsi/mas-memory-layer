# CIAR Challenge Experiment Results

Date: 2026-05-19
Status: Focused live run complete with `tencent/hy3-preview`
Related plan: `docs/plan/2026-05-19-ciar-challenge-experiment-execution-plan.md`

## Summary

The CIAR challenge harness now has both dry-run evidence and a focused live run
against the current single-node topology on `skz-data-lv`.

The live run used:

- OpenRouter model: `tencent/hy3-preview`
- Output-token budget: `8192`
- OpenRouter timeout: `120s`
- Redis/PostgreSQL/Phoenix host: `192.168.107.187`
- PostgreSQL database: `yaam-test`
- PostgreSQL role: `yaam`

The live evidence confirms that the current pipeline can promote useful urgent
facts, suppress small talk, and suppress one contradiction scenario because its
segment score falls below threshold. It also confirms that promoted facts still
inherit segment-level certainty/impact strongly enough to promote low-value
facts inside an otherwise urgent segment.

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

Focused live run with Tencent and the dedicated YAAM database:

```bash
set -a; . ./.env; set +a
MAS_REDIS_TIMEOUT=15 \
MAS_OPENROUTER_TIMEOUT=120 \
MAS_MAX_OUTPUT_TOKENS=8192 \
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --run-id ciar-exp-live-focused-tencent-20260519-06 \
  --model tencent/hy3-preview \
  --phoenix-endpoint http://192.168.107.187:6006/v1/traces \
  --phoenix-project-name ciar-challenge-focused-tencent-20260519-06 \
  --skip-provider-health \
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
`alternative_scores.json` were produced from this first failed attempt. No live
CIAR behavior should be inferred from it.

## Dedicated YAAM Database Setup

A dedicated PostgreSQL role and database were created on `skz-data-lv`:

```text
role: yaam
database: yaam-test
```

The `yaam` password is stored in local `.env` both inside `POSTGRES_URL` and as
an explicit `POSTGRES_PASSWORD` key. The value is intentionally not recorded in
this report.

The `yaam-test` schema was initialized with:

- `active_context`
- `working_memory`
- CIAR metric columns on `working_memory`
- `content_tsv` full-text column and GIN index
- session/CIAR index without the old volatile `NOW()` partial predicate

A real adapter round-trip succeeded:

```text
L1 stored and retrieved 1 session turn
L2 stored and queried 1 fact
```

## Focused Live Run

Artifact directory:

```text
logs/ciar_challenge/ciar-exp-live-focused-tencent-20260519-06
```

Phoenix project:

```text
ciar-challenge-focused-tencent-20260519-06
```

Run manifest highlights:

```text
graph_backend=langgraph
runtime.mode=live_l1_l2
runtime.provider_order=["openrouter"]
provider_health=null
cleanup completed for all three scenario sessions
```

Provider-health preflight was skipped because the same run path repeatedly
timed out on Redis after provider health, while direct Redis/L1/L2 setup and the
full experiment without provider-health both succeeded. The actual promotion
path still used OpenRouter through `tencent/hy3-preview`.

Live scenario outcomes:

| Scenario | Expected | Segments Created | Segments Promoted | Facts Extracted | Facts Promoted | Errors |
|---|---:|---:|---:|---:|---:|---:|
| small_talk | ignore | 1 | 0 | 0 | 0 | 0 |
| contradiction_update | should_conflict | 1 | 0 | 0 | 0 | 0 |
| segment_mismatch | should_not_floor | 1 | 1 | 5 | 5 | 0 |

Observed live segment scores:

- `small_talk`: CIAR `0.15`, decision `IGNORE`
- `contradiction_update`: CIAR `0.5`, decision `IGNORE`
- `segment_mismatch`: CIAR `0.9`, decision `PROMOTE`

Promoted live facts for `segment_mismatch`:

- Urgent temperature excursion incident involving container `MAEU9182736`.
- `MAEU9182736` as the relevant supply-chain container.
- Assistant action to log the exception.
- User thanks the assistant for prompt response.
- User defers further discussion to a later unspecified time.

The last two facts are useful challenge evidence: they are low-value interaction
facts that received CIAR scores near `0.9` because the promoted urgent segment
dominates fact-level scoring. `alternative_scores.json` assigned each promoted
fact a `utility_candidate_v0` score of `0.785`, lower than current runtime CIAR
but still above threshold.

## Interpretation

The dry run validates that the isolated harness is structurally useful and that
the current deterministic scenarios can expose two known CIAR limitations:

1. CIAR is a retention score, not a truth-resolution mechanism.
2. Current promotion behavior can let segment-level scoring dominate fact-level
   quality signals.

The live run is no longer blocked by basic environment setup. The remaining
operational issue is that provider-health preflight can precede and destabilize
the Redis setup path in this harness. For focused CIAR evidence runs, use
`--skip-provider-health` and rely on the actual promotion path plus generated
artifacts for provider behavior.

## Required Follow-Up

Implementation can now proceed on the policy side, without changing low-level
storage adapters:

1. Add a fact-level evidence gate or `EvidenceRanker` before L2 store.
2. Keep segment CIAR as a routing signal, not the sole promoted-fact score.
3. Preserve the focused live run as the regression fixture:
   `ciar-exp-live-focused-tencent-20260519-06`.
4. Fix or bypass provider-health preflight for future live harness runs.
5. Add a schema/migration cleanup task: `002_l2_tsvector_index.sql` currently
   contains a volatile `NOW()` partial-index predicate that cannot be applied
   cleanly on a fresh PostgreSQL database.
