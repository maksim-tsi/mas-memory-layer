# CIAR Challenge Experiment Results

Date: 2026-05-19
Last updated: 2026-05-20
Status: Live baseline, policy comparison, CIAR conformance, deterministic supersession cleanup, and CIAR-DEF-1 default-policy evaluation complete
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
small talk and retain urgent facts, but CIAR alone does not resolve
truth/supersession and can let segment-level scoring promote low-value facts
inside an otherwise important segment. The new `fact_gate`, `hybrid_gate`, and
`suppress_superseded` policies reduce those failure modes while preserving
`segment_gate` and contradiction policy `off` as backward-compatible defaults.
The CIAR-DEF-1 live matrix now supports `hybrid_gate` as the experimental
promotion default candidate, but it does not yet support defaulting
`suppress_superseded` because live suppression events did not fire.

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

CIAR-DEF-1 default-policy matrix pattern:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge_with_env.py \
  --run-id ciar-exp-live-default-<promotion>-<contradiction>-20260520-<nn> \
  --phoenix-project-name ciar-challenge-live-default-<promotion>-<contradiction>-20260520-<nn> \
  --force-data-node-services \
  --skip-provider-health \
  --provider-health-skip-reason "provider health checked separately; default policy evaluation" \
  --promotion-policy-mode <fact_gate|hybrid_gate> \
  --contradiction-policy-mode <off|suppress_superseded> \
  --scenario-id segment_mismatch \
  --scenario-id contradiction_update \
  --scenario-id small_talk
```

CIAR-DEF-1 artifact aggregation:

```bash
./.venv/bin/python scripts/experiments/analyze_ciar_policy_runs.py \
  logs/ciar_challenge/ciar-exp-live-default-*-20260520-* \
  --json-output logs/ciar_challenge/ciar-def-1-analysis-20260520.json \
  --markdown-output logs/ciar_challenge/ciar-def-1-analysis-20260520.md
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

After the May 20 CIAR-CONF-1 cleanup:

```text
ruff: All checks passed
pytest: 611 passed, 140 skipped in 259.29s
```

Focused conformance tests also passed:

```text
tests/memory/test_ciar_scorer.py: 49 passed
tests/agents/tools/test_ciar_tools.py: 16 passed
tests/api/test_v2_router_ciar.py: 1 passed
tests/memory/test_working_memory_tier.py: 18 passed
```

For CIAR-DEF-1 analyzer and harness coverage:

```text
ruff: All checks passed for analyzer and script tests
tests/scripts/test_ciar_policy_analysis.py tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_challenge_with_env.py: 16 passed
```

## CIAR-CONF-1 Findings

CIAR-CONF-1 closed the main conformance gaps identified after the policy
comparison work:

- `Fact.validate_ciar_score()` was a field validator on `ciar_score`, so it ran
  before all component fields were available. It now validates after model
  construction and treats explicitly supplied full CIAR components as
  authoritative.
- `POST /v2/memory/l2/facts` previously constructed facts with
  `ciar_score=1.0`, `certainty=0.8`, and `impact=0.5`, which contradicted the
  ADR-004 formula. It now creates an internally consistent high-confidence
  semantic assertion and records agent/task provenance in metadata.
- ADR-004, scorer docstrings, and CIAR tool explanations now agree that
  reinforcement can exceed `1.0`, while the stored final CIAR score is clamped
  to `[0.0, 1.0]`.
- Tests now cover final-score clamping, high-access reinforcement,
  future/stale timestamp behavior, explicit component recomputation, access
  updates, v2 route consistency, and CIAR tool explanation wording.

## CIAR-SUP-1 Findings

CIAR-SUP-1 adds a deterministic contradiction/supersession policy above CIAR.
CIAR still scores retention priority; the new policy records explicit correction
metadata and can suppress superseded facts from promotion and prompt context.

The implemented modes are:

- `off`: current backward-compatible behavior.
- `metadata_only`: annotate conflict/supersession metadata while storing both
  facts.
- `suppress_superseded`: store the current correction, emit `fact_suppressed`
  for the old fact, and omit superseded L2 facts from `query_memory()` and
  `get_context_block()`.

Dry-run evidence:

```text
logs/ciar_challenge/ciar-exp-dry-supersession-20260520-02
```

Result with `hybrid_gate + suppress_superseded`:

```text
contradiction_update: facts_extracted=2, facts_promoted=1, facts_suppressed=1
segment_mismatch: facts_extracted=2, facts_promoted=1, facts_review_only=1
small_talk: segments_promoted=0, facts_promoted=0
```

The dry harness also recorded blocked Phoenix export attempts to
`127.0.0.1:16006` in the sandbox. That is operational noise for this local
dry-run; artifact generation completed successfully.

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
| contradiction_update | 1 | 3 | CIAR baseline retained stale/corrected facts and does not resolve supersession |
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

## Default Policy Evaluation

CIAR-DEF-1 executed 12 focused live runs on 2026-05-20:

- 3 runs of `fact_gate + off`
- 3 runs of `fact_gate + suppress_superseded`
- 3 runs of `hybrid_gate + off`
- 3 runs of `hybrid_gate + suppress_superseded`

Aggregate artifact:

```text
logs/ciar_challenge/ciar-def-1-analysis-20260520.md
logs/ciar_challenge/ciar-def-1-analysis-20260520.json
```

All 12 runs produced `summary.md`, `promotion_results.json`,
`alternative_scores.json`, `events.jsonl`, and `run_manifest.json`.

Run matrix:

| Run | Config | contradiction_update p/r/f/s | segment_mismatch p/r/f/s | small_talk promoted |
|---|---|---:|---:|---:|
| `ciar-exp-live-default-fact-gate-off-20260520-01` | `fact_gate+off` | 1/0/2/0 | 1/0/0/0 | 0 |
| `ciar-exp-live-default-fact-gate-off-20260520-02` | `fact_gate+off` | 2/0/3/0 | 3/0/2/0 | 0 |
| `ciar-exp-live-default-fact-gate-off-20260520-03` | `fact_gate+off` | 2/0/3/0 | 3/0/2/0 | 0 |
| `ciar-exp-live-default-fact-gate-suppress-20260520-01` | `fact_gate+suppress_superseded` | 1/0/2/0 | 3/0/2/0 | 0 |
| `ciar-exp-live-default-fact-gate-suppress-20260520-02` | `fact_gate+suppress_superseded` | 2/0/1/0 | 2/0/2/0 | 0 |
| `ciar-exp-live-default-fact-gate-suppress-20260520-03` | `fact_gate+suppress_superseded` | 2/0/1/0 | 3/0/1/0 | 0 |
| `ciar-exp-live-default-hybrid-gate-off-20260520-01` | `hybrid_gate+off` | 2/1/0/0 | 3/2/0/0 | 0 |
| `ciar-exp-live-default-hybrid-gate-off-20260520-02` | `hybrid_gate+off` | 0/0/0/0 | 5/1/0/0 | 0 |
| `ciar-exp-live-default-hybrid-gate-off-20260520-03` | `hybrid_gate+off` | 2/1/0/0 | 3/1/0/0 | 0 |
| `ciar-exp-live-default-hybrid-gate-suppress-20260520-01` | `hybrid_gate+suppress_superseded` | 2/1/0/0 | 1/0/0/0 | 0 |
| `ciar-exp-live-default-hybrid-gate-suppress-20260520-02` | `hybrid_gate+suppress_superseded` | 1/2/0/0 | 3/1/0/0 | 0 |
| `ciar-exp-live-default-hybrid-gate-suppress-20260520-03` | `hybrid_gate+suppress_superseded` | 4/4/0/0 | 3/1/0/0 | 0 |

Legend: `p/r/f/s` means promoted / review-only / filtered / suppressed facts.

Aggregate recommendation inputs:

| Config | Small Talk Promoted | Segment Mismatch Promoted | Segment Mismatch Review-Only | Contradiction Promoted | Contradiction Review-Only | Contradiction Suppressed |
|---|---:|---:|---:|---:|---:|---:|
| `fact_gate+off` | 0 | 7 | 0 | 5 | 0 | 0 |
| `fact_gate+suppress_superseded` | 0 | 8 | 0 | 5 | 0 | 0 |
| `hybrid_gate+off` | 0 | 11 | 4 | 4 | 2 | 0 |
| `hybrid_gate+suppress_superseded` | 0 | 7 | 2 | 7 | 7 | 0 |

Findings:

- `small_talk` remained clean: zero promoted facts in all 12 live runs.
- `hybrid_gate` retained urgent `segment_mismatch` facts and produced
  review-only evidence for weak or conversational facts. This better matches
  the desired audit trail than strict filtering alone.
- `fact_gate` filtered facts but does not preserve review-only evidence, making
  it less useful as the default when we want conservative retention plus
  inspectable non-storage decisions.
- `suppress_superseded` did not emit any live `fact_suppressed` events. In live
  LLM outputs, stale Oakland facts were commonly filtered or marked
  review-only before the suppression policy could prove a supersession pair.
- One `hybrid_gate+suppress_superseded` run recorded an OpenRouter provider
  failure and recovered through rule fallback. The run completed and produced
  artifacts, but it should be treated as operational noise when interpreting
  LLM behavior.

Recommendation:

- Proposed experimental promotion default: `hybrid_gate`.
- Proposed contradiction default: keep `off`.
- Do not default `suppress_superseded` yet. Dry evidence proves the mechanism,
  but live evidence shows the current matching policy is not reliably activated
  on LLM-extracted correction facts.
- Next implementation should either switch only `promotion_policy_mode` to
  `hybrid_gate` after approval, or first add CIAR-SUP-2 to improve live
  supersession matching and then rerun the contradiction slice.

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

The initial policy implementation and CIAR-DEF-1 live default-policy evaluation
are complete. Follow-up should now focus on converting the evidence into a
controlled default change, improving live supersession behavior, and reducing
operational ambiguity in future live runs.

1. CIAR-DEF-2: implement the approved experimental promotion default switch to
   `hybrid_gate`.
   - Evidence: the 12-run matrix kept `small_talk` at zero promoted facts, and
     `hybrid_gate` retained urgent `segment_mismatch` facts while producing
     review-only evidence for weak facts.
   - Constraint: keep `segment_gate` and `fact_gate` as explicit override modes
     and do not change contradiction policy default in this step.
   - Acceptance: default-path dry and focused live smoke runs show
     `hybrid_gate` behavior without passing `--promotion-policy-mode`.

2. CIAR-SUP-2: improve live supersession matching before defaulting
   `suppress_superseded`.
   - Evidence: dry CIAR-SUP-1 produced `facts_suppressed=1`, but all 12 live
     CIAR-DEF-1 runs produced `facts_suppressed=0`.
   - Likely gap: live LLM wording creates paraphrased old/new facts that are
     filtered or review-only before the deterministic policy can prove a
     supersession pair.
   - Acceptance: focused live `contradiction_update` reruns emit auditable
     `fact_suppressed` events, or the report documents why suppression should
     remain opt-in.

3. CIAR-EVAL-2: broaden scenario coverage before treating `hybrid_gate` as a
   production-grade default.
   - Evidence: CIAR-DEF-1 is strong enough for an experimental default
     candidate, but it still covers only `small_talk`, `segment_mismatch`, and
     `contradiction_update`.
   - Add scenarios for stale preferences, explicit reversals, repeated
     corrections, low-value assistant acknowledgements, and urgent facts inside
     longer chatter.
   - Acceptance: `analyze_ciar_policy_runs.py` aggregates the expanded matrix
     and the report records scenario-level regressions or improvements.

4. CIAR-OPS-1: improve live-run operational classification.
   - Evidence: one Phoenix preflight attempt was blocked by sandbox networking,
     and one OpenRouter provider failure recovered through rule fallback.
   - Add or document manifest fields that distinguish provider fallback,
     Phoenix preflight status, cleanup status, and policy evidence quality.
   - Acceptance: future analysis can classify operational noise from artifacts
     without relying on console logs.

5. Keep CIAR conformance tests as non-negotiable regression gates.
   - Evidence: today’s full suite passed with `624 passed, 140 skipped`.
   - Continue running scorer, validator, tool, API, promotion policy, and
     analyzer tests before changing defaults.

6. Keep CIAR-DB-1 separate from policy work.
   - Evidence: the current policy improvements stayed above storage, while the
     PostgreSQL migration issue remains a fresh-database readiness risk.
   - Do not edit migrations or schema files without explicit authorization.
