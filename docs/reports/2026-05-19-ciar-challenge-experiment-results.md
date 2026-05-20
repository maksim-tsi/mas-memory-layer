# CIAR Challenge Experiment Results

Date: 2026-05-19
Last updated: 2026-05-20
Status: Live baseline and policy comparison complete with `tencent/hy3-preview`
Related plan: `docs/plan/2026-05-19-ciar-challenge-experiment-execution-plan.md`

## Summary

The CIAR challenge harness now has both dry-run evidence and a focused live run
against the current single-node topology on `skz-data-lv`. On 2026-05-20, the
harness was extended with a safe `.env` wrapper, explicit promotion policy
modes, fact-level CIAR provenance, and dry/live policy comparison runs.

The live run used:

- OpenRouter model: `tencent/hy3-preview`
- Output-token budget: `8192`
- OpenRouter timeout: `120s`
- Redis/PostgreSQL/Phoenix host: `192.168.107.187`
- PostgreSQL database: `yaam-test`
- PostgreSQL role: `yaam`

The evidence confirms that CIAR is useful as a deterministic retention score
but incomplete as a memory policy. The current default behavior can suppress
small talk and retain urgent facts, but it does not resolve truth/supersession
and can let segment-level scoring promote low-value facts inside an otherwise
important segment. The new `fact_gate` and `hybrid_gate` policy modes reduce
that over-promotion while preserving `segment_gate` as the backward-compatible
baseline.

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

Final verification after policy implementation:

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest tests/ -v
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

Current live baseline with safe `.env` wrapper:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge_with_env.py \
  --run-id ciar-exp-live-env-20260520-03 \
  --phoenix-project-name ciar-challenge-live-env-20260520-03 \
  --force-data-node-services \
  --skip-provider-health \
  --provider-health-skip-reason "provider health checked separately; avoid Redis setup interaction" \
  --scenario-id segment_mismatch \
  --scenario-id contradiction_update \
  --scenario-id small_talk
```

Policy comparison pattern:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge_with_env.py \
  --run-id ciar-exp-live-<mode>-20260520-01 \
  --phoenix-project-name ciar-challenge-live-<mode>-20260520-01 \
  --force-data-node-services \
  --skip-provider-health \
  --provider-health-skip-reason "provider health checked separately; policy comparison run" \
  --promotion-policy-mode <segment_gate|fact_gate|hybrid_gate> \
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

After the May 20 policy implementation:

```text
ruff: All checks passed
pytest: 606 passed, 140 skipped in 259.66s
```

The CIAR policy/provenance implementation was committed as:

```text
eb23673 feat: add CIAR promotion policy modes
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

## Current Live Baseline

The current live baseline fixture is:

```text
logs/ciar_challenge/ciar-exp-live-env-20260520-03
```

Phoenix project:

```text
ciar-challenge-live-env-20260520-03
```

This run used the safe env wrapper
`scripts/experiments/run_ciar_challenge_with_env.py`. The wrapper loaded needed
values into `os.environ`, printed only key names/presence, and forced Redis,
PostgreSQL, and Phoenix endpoints to the active data node without printing
secret values.

Run manifest highlights:

- `runtime.mode=live_l1_l2`
- `runtime.provider_order=["openrouter"]`
- `provider_health.status=skipped`
- skip reason: `provider health checked separately; avoid Redis setup interaction`
- Phoenix UI check succeeded against `http://192.168.107.187:6006`
- L1 cleanup succeeded for all three sessions
- L2 cleanup succeeded where L2 facts existed

Current live baseline outcomes:

| Scenario | Segments Promoted | Facts Promoted | Key Finding |
|---|---:|---:|---|
| small_talk | 0 | 0 | Correctly ignored |
| contradiction_update | 1 | 3 | CIAR retained stale/corrected facts and does not resolve supersession |
| segment_mismatch | 1 | 4 | Segment-level score promoted low-value interaction facts |

The current baseline also fixed the earlier artifact matching issue:
`alternative_scores.json` contains non-null `raw_fact_ciar` and
`current_runtime_ciar` for promoted live facts. This made it possible to compare
raw fact scoring with stored runtime scoring.

## Policy Implementation Results

Implemented policy modes:

- `segment_gate`: default, backward-compatible behavior; segment CIAR decides
  whether extraction/storage proceeds and preserves the previous segment-driven
  certainty/impact inheritance behavior.
- `fact_gate`: uses true pre-inheritance fact CIAR for the L2 store/filter
  decision.
- `hybrid_gate`: uses segment CIAR to admit extraction, but keeps
  below-threshold or obvious low-value facts out of L2 as review-only artifacts.

Implemented provenance fields:

- `segment_ciar`
- `raw_fact_ciar`
- `pre_inheritance_ciar`
- `post_inheritance_ciar`
- `stored_ciar`
- `ciar_score_source`
- `segment_inherited`
- `fact_gate_decision`
- `review_only`
- `evidence_quality_flags`

One artifact gap was found and fixed during live comparison: PostgreSQL rows did
not always round-trip fact metadata, so `alternative_scores.json` now recovers
promotion provenance from `fact_promoted` and `fact_review_only` events when
stored-row metadata is empty.

## Policy Comparison Artifacts

Dry comparison artifacts:

| Run | Mode | Key Outcome |
|---|---|---|
| `ciar-exp-dry-segment-gate-20260520-01` | `segment_gate` | Preserved previous behavior; `segment_mismatch` promoted both urgent and low-value facts |
| `ciar-exp-dry-fact-gate-20260520-01` | `fact_gate` | Filtered the low-value `segment_mismatch` fact |
| `ciar-exp-dry-hybrid-gate-20260520-01` | `hybrid_gate` | Stored the urgent fact and recorded the low-value fact as review-only |

Live comparison artifacts:

| Run | Mode | contradiction_update | segment_mismatch | small_talk |
|---|---|---:|---:|---:|
| `ciar-exp-live-segment-gate-20260520-01` | `segment_gate` | 3 promoted | 4 promoted | 0 promoted |
| `ciar-exp-live-fact-gate-20260520-01` | `fact_gate` | 2 promoted / 3 filtered | 1 promoted / 2 filtered | 0 promoted |
| `ciar-exp-live-hybrid-gate-20260520-01` | `hybrid_gate` | 2 promoted / 1 review-only | 2 promoted / 2 review-only | 0 promoted |
| `ciar-exp-live-hybrid-gate-20260520-02` | `hybrid_gate` | 0 promoted due to live LLM empty-segment behavior | 3 promoted / 2 review-only | 0 promoted |

The first `hybrid_gate` live run is better evidence for contradiction behavior.
The second `hybrid_gate` live run is better evidence for corrected artifact
provenance because it was rerun after event-based provenance recovery was added.

## Interpretation

The dry and live runs validate that the isolated harness is structurally useful
and that the current deterministic scenarios expose three CIAR boundaries:

1. CIAR is a retention score, not a truth-resolution mechanism.
2. Segment-level scoring can dominate fact-level quality signals when promotion
   is not made explicit.
3. Artifact-level provenance must not depend solely on storage metadata
   round-tripping; events are the safer policy evidence source.

The live run is no longer blocked by basic environment setup. The remaining
operational issue is that provider-health preflight can precede and destabilize
the Redis setup path in this harness. For focused CIAR evidence runs, use
`--skip-provider-health` and rely on the actual promotion path plus generated
artifacts for provider behavior.

## Required Follow-Up

The initial policy implementation is complete. Follow-up should now focus on
conformance, repeatability, and policy refinement:

1. Preserve `segment_gate` as the backward-compatible default until broader
   evaluation chooses a new default.
2. Use `fact_gate` and `hybrid_gate` comparison artifacts as the next regression
   fixtures for policy work.
3. Improve contradiction/supersession handling above CIAR; do not encode truth
   resolution into the CIAR formula.
4. Fix or continue explicitly bypassing provider-health preflight for focused
   live harness runs.
5. Complete CIAR conformance cleanup across scorer, validators, tools, docs, and
   v2 routes.
6. Add a schema/migration cleanup task: `002_l2_tsvector_index.sql` currently
   contains a volatile `NOW()` partial-index predicate that cannot be applied
   cleanly on a fresh PostgreSQL database.
