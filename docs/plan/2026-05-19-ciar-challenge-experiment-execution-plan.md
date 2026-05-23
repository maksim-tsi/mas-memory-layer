# CIAR Challenge Experiment and Implementation Coordination Plan

Date: 2026-05-19
Last updated: 2026-05-21
Status: CIAR-DEF-2, CIAR-SUP-2, and CIAR-EVAL-2 implemented and live-evaluated; follow-up remains for operational noise and broader suppression safety
Related:
`docs/reports/2026-05-18-ciar-design-and-implementation-audit.md`,
`docs/reports/2026-05-19-ciar-challenge-experiment-results.md`,
`scripts/experiments/run_ciar_challenge.py`

## Summary

The CIAR challenge experiment has moved from execution readiness to
post-live-run implementation coordination. The dry run and focused live run
produced enough evidence to proceed on policy and observability work above the
storage layer.

CIAR v1 remains the deterministic L1 -> L2 retention baseline. The current
implementation makes promotion behavior explicit, separates segment-level and
fact-level signals in metadata/artifacts, and adds a first evidence policy for
review-only facts without changing the default runtime path.

## Current Baseline

Current baseline fixture:

```text
logs/ciar_challenge/ciar-exp-live-env-20260520-03
```

Current baseline Phoenix project:

```text
ciar-challenge-live-env-20260520-03
```

Previous baseline fixture:

```text
logs/ciar_challenge/ciar-exp-live-focused-tencent-20260519-06
```

Baseline runtime:

- OpenRouter model: `tencent/hy3-preview`
- output-token budget: `8192`
- OpenRouter timeout: `120s`
- Redis/PostgreSQL/Phoenix host: `192.168.107.187`
- PostgreSQL database: `yaam-test`
- provider order: `["openrouter"]`
- provider-health preflight: checked separately, then skipped in the successful
  focused run with a recorded manifest reason
- `.env` loading: `scripts/experiments/run_ciar_challenge_with_env.py`, with
  secret values kept out of logs

Baseline finding:

- `small_talk` produced no promoted facts.
- `contradiction_update` promoted one segment and three facts, confirming CIAR
  does not resolve truth or supersession by itself.
- `segment_mismatch` promoted one segment and four facts, including low-value
  interaction facts, because segment-level certainty and impact dominated the
  promoted facts' stored CIAR scores.

Resolved instrumentation caveat:

- The 2026-05-19 live run had `raw_fact_ciar=null` in `alternative_scores.json`
  because scorer-call fact IDs did not match stored L2 fact IDs.
- The 2026-05-20 live run fixed this: `alternative_scores.json` has non-null
  `raw_fact_ciar` for promoted live facts.

Current implementation delta:

- `segment_gate` is the default policy and preserves the previous segment-driven
  promotion behavior.
- `fact_gate` uses true pre-inheritance fact CIAR for the store/filter decision.
- `hybrid_gate` uses segment CIAR to admit extraction, then keeps below-threshold
  or obvious conversational-residue facts out of L2 as review-only artifacts.
- Promotion metadata now carries `segment_ciar`, `raw_fact_ciar`,
  `pre_inheritance_ciar`, `post_inheritance_ciar`, `stored_ciar`,
  `ciar_score_source`, `segment_inherited`, gate decision, and evidence flags.
- Dry policy comparison artifacts were generated on 2026-05-20:
  `ciar-exp-dry-segment-gate-20260520-01`,
  `ciar-exp-dry-fact-gate-20260520-01`, and
  `ciar-exp-dry-hybrid-gate-20260520-01`.
- Initial live policy comparison artifacts were generated on 2026-05-20:
  `ciar-exp-live-segment-gate-20260520-01`,
  `ciar-exp-live-fact-gate-20260520-01`,
  `ciar-exp-live-hybrid-gate-20260520-01`, and
  `ciar-exp-live-hybrid-gate-20260520-02`.
- `alternative_scores.json` now recovers provenance from promotion events when
  PostgreSQL rows do not round-trip fact metadata.

## Scope And Boundaries

In scope:

- Maintain the isolated CIAR challenge harness and its dry/live artifact set.
- Preserve `ciar-exp-live-env-20260520-03` as the current
  regression fixture until a cleaner run replaces it.
- Add observability needed to compare segment, raw fact, and stored fact scores.
- Add explicit promotion policy modes and tests.
- Add a first evidence gate or `EvidenceRanker` above CIAR and above storage.
- Update CIAR conformance docs/tests so scorer, validator, tools, and routes
  describe the same behavior.
- Track operational follow-ups that affect experiment repeatability.
- Run the local CIAR regression pack before future CIAR policy/default changes:
  `./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py`.

Out of scope without explicit user approval:

- `src/storage/` or other low-level DB adapter changes.
- Dependency or lockfile changes.
- `.github/` workflow/instruction changes.
- `.env`, secret files, key files, or printing secret values.
- Treating one focused live run as benchmark-grade statistical evidence.

## Progress Tracker

| ID | Status | Workstream | Owner | Dependencies | Tracking Evidence | Done When |
|---|---|---|---|---|---|---|
| CIAR-EXP-0 | Complete | Dry/live evidence collection, model selection, artifact capture, and results report | Experiment owner | None | `docs/reports/2026-05-19-ciar-challenge-experiment-results.md`, `logs/ciar_challenge/ciar-exp-live-env-20260520-03` | Dry and live artifacts exist, results are documented, and the live fixture is named |
| CIAR-EXP-1 | Complete | Fix harness observability so raw CIAR calls join reliably to stored L2 facts | Experiment owner | CIAR-EXP-0 | `tests/scripts/test_ciar_challenge_experiment.py`, `logs/ciar_challenge/ciar-exp-live-env-20260520-03/alternative_scores.json` | Scorer calls record session ids, storage-rewritten fact ids can join by session/content, and live `alternative_scores.json` has non-null `raw_fact_ciar` |
| CIAR-EXP-2 | Complete | Stabilize provider-health preflight or document an explicit bypass policy | Experiment owner | CIAR-EXP-0 | `scripts/experiments/run_ciar_challenge.py`, `scripts/experiments/run_ciar_challenge_with_env.py`, `tests/scripts/test_ciar_challenge_experiment.py` | Provider health is diagnostic by default, skip reasons are recorded in `run_manifest.json`, callers can require provider health explicitly, and the wrapper can force skz-data-lv endpoints while preserving credentials |
| CIAR-POL-1 | Complete | Add explicit promotion policy modes: `segment_gate`, `fact_gate`, `hybrid_gate` | Memory policy owner | CIAR-EXP-1 recommended | `src/memory/engines/promotion_engine.py`, `tests/memory/engines/test_promotion_engine.py`, dry/live policy artifacts | Promotion behavior is selected by a named mode and current behavior is preserved as `segment_gate` |
| CIAR-POL-2 | Complete | Separate segment, raw fact, and stored fact score metadata | Memory policy owner | CIAR-POL-1 | Promotion telemetry, L2 fact metadata where storage preserves it, event provenance fallback, `alternative_scores.json` | Promotion outputs report `segment_ciar`, `raw_fact_ciar`, `pre_inheritance_ciar`, `post_inheritance_ciar`, and `stored_ciar` without overwriting the meaning of each score |
| CIAR-POL-3 | Complete | Add first fact-level evidence gate or `EvidenceRanker` before L2 store | Memory policy owner | CIAR-POL-1, CIAR-POL-2 | `EvidenceRanker`, policy tests, dry/live policy artifacts | `segment_mismatch` low-value facts are filtered by `fact_gate` or marked review-only by `hybrid_gate` while urgent facts remain promotable |
| CIAR-CONF-1 | Complete | CIAR conformance cleanup: stale docstrings, v2 score recomputation tests, clamping/high-access/stale-fact coverage | Memory policy owner | CIAR-EXP-0 | `tests/memory/test_ciar_scorer.py`, `tests/agents/tools/test_ciar_tools.py`, `tests/api/test_v2_router_ciar.py`, `./.venv/bin/pytest tests/ -v` | ADR-004, scorer, validators, tools, and docs describe the same deterministic CIAR behavior |
| CIAR-SUP-1 | Complete | Add contradiction/supersession suppression policy above CIAR without changing storage schema | Memory policy owner | CIAR-POL-2, CIAR-POL-3, CIAR-CONF-1 | `tests/memory/test_contradiction_policy.py`, `tests/memory/engines/test_promotion_engine.py`, `tests/memory/test_unified_memory_system.py`, `logs/ciar_challenge/ciar-exp-dry-supersession-20260520-02` | Explicit corrections can mark/suppress superseded facts while CIAR remains a retention score |
| CIAR-DEF-1 | Complete | Choose candidate default CIAR policy using live `fact_gate`/`hybrid_gate` matrix | Experiment owner | CIAR-SUP-1 | `logs/ciar_challenge/ciar-def-1-analysis-20260520.json`, `logs/ciar_challenge/ciar-def-1-analysis-20260520.md`, 12 live run artifacts | Recommend `hybrid_gate` as the experimental promotion default candidate; keep contradiction default `off` until live suppression behavior is improved |
| CIAR-DEF-2 | Complete | Implement approved experimental promotion default switch to `hybrid_gate` while preserving explicit override | Memory policy owner | CIAR-DEF-1, explicit user approval | `src/memory/engines/promotion_engine.py`, `scripts/experiments/run_ciar_challenge.py`, `scripts/experiments/run_ciar_challenge_with_env.py`, `src/evaluation/agent_wrapper.py`, `logs/ciar_challenge/ciar-exp-dry-default-hybrid-20260521-02`, `logs/ciar_challenge/ciar-exp-live-eval2-default-hybrid-off-20260521-01` | Default promotion behavior uses `hybrid_gate`, callers can still select `segment_gate` or `fact_gate`, and dry/live default-path artifacts show `hybrid_gate+off` |
| CIAR-SUP-2 | Complete | Improve live supersession matching so explicit corrections can trigger suppression after LLM extraction variance | Memory policy owner | CIAR-SUP-1, CIAR-DEF-1 | `src/memory/contradiction_policy.py`, `tests/memory/test_contradiction_policy.py`, `logs/ciar_challenge/ciar-sup2-analysis-20260521.md` | Live `contradiction_update` runs produced auditable `fact_suppressed` events; suppression remains opt-in because broader reversal/stale-preference scenarios did not suppress reliably |
| CIAR-EVAL-2 | Complete | Broaden default-policy evaluation beyond the three deterministic challenge scenarios | Experiment owner | CIAR-DEF-2 recommended, CIAR-SUP-2 optional | `scripts/experiments/run_ciar_challenge.py`, `logs/ciar_challenge/ciar-eval2-analysis-20260521.md`, `logs/ciar_challenge/ciar-eval2-analysis-20260521.json` | Candidate defaults were tested against additional correction, stale preference, low-value chatter, and urgent operational scenarios |
| CIAR-OPS-1 | Complete | Reduce live-run operational noise from provider-health bypass, OpenRouter fallback, and Phoenix preflight sandbox behavior | Experiment owner | CIAR-EXP-2, CIAR-DEF-1 | `docs/reports/2026-05-23-ciar-operational-classification-report.md`, `scripts/experiments/run_ciar_challenge.py`, `scripts/experiments/analyze_ciar_policy_runs.py` | Live experiment failures are classified cleanly and do not require manual interpretation from console output |
| CIAR-REG-1 | Complete locally | Add canonical local CIAR regression pack | Experiment owner | CIAR-CONF-1, CIAR-OPS-1 | `scripts/experiments/run_ciar_regression_pack.py`, `tests/scripts/test_ciar_regression_pack.py`, `docs/plan/2026-05-23-ciar-regression-pack-plan.md` | A single local command runs repo venv verification, ruff, and the focused CIAR pytest pack without live provider or `.env` access |
| CIAR-DB-1 | To do | Plan schema/migration cleanup for `002_l2_tsvector_index.sql` volatile `NOW()` partial-index predicate | Database owner | Explicit user approval before migration edits | Migration file and fresh database verification notes | Fresh dedicated PostgreSQL setup can apply schema cleanly without manual index workaround |
| CIAR-MCP-1 | Backlog | Extract shared CIAR/evidence service layer for future REST, LangChain, and MCP adapters | Interface owner | CIAR-POL-2, CIAR-POL-3 | RFC update or implementation plan | LangChain tools and future MCP tools can call stable service functions rather than duplicating policy logic |

Status meanings:

- `Complete`: implemented or documented and no longer blocking current work.
- `Complete locally`: implemented and locally verified; live evidence is still
  pending when noted in `Done When`.
- `In progress`: next implementation target or known partial implementation.
- `To do`: approved direction but not yet implemented.
- `Backlog`: important follow-on work that should not block CIAR experiment
  hardening.

## CIAR-DEF-1 Default Policy Evaluation Tracker

Goal:

- Select a proposed default CIAR policy candidate based on live evidence rather
  than dry-run-only behavior.
- Compare `fact_gate` and `hybrid_gate` under both contradiction policy `off`
  and `suppress_superseded`.
- Preserve the current code default, `segment_gate + off`, until a separate
  default-change decision is approved.

Planned run matrix:

| Promotion Policy | Contradiction Policy | Repetitions | Planned Run IDs |
|---|---|---:|---|
| `fact_gate` | `off` | 3 | `ciar-exp-live-default-fact-gate-off-20260520-01` through `-03` |
| `fact_gate` | `suppress_superseded` | 3 | `ciar-exp-live-default-fact-gate-suppress-20260520-01` through `-03` |
| `hybrid_gate` | `off` | 3 | `ciar-exp-live-default-hybrid-gate-off-20260520-01` through `-03` |
| `hybrid_gate` | `suppress_superseded` | 3 | `ciar-exp-live-default-hybrid-gate-suppress-20260520-01` through `-03` |

Execution tracker:

| Run ID | Promotion Policy | Contradiction Policy | Repetition | Status | Phoenix Project | Artifact Path | Notes |
|---|---|---|---:|---|---|---|---|
| `ciar-exp-live-default-fact-gate-off-20260520-01` | `fact_gate` | `off` | 1 | Complete | `ciar-challenge-live-default-fact-gate-off-20260520-01` | `logs/ciar_challenge/ciar-exp-live-default-fact-gate-off-20260520-01` | 1 sandbox-blocked false start was rerun with network approval |
| `ciar-exp-live-default-fact-gate-off-20260520-02` | `fact_gate` | `off` | 2 | Complete | `ciar-challenge-live-default-fact-gate-off-20260520-02` | `logs/ciar_challenge/ciar-exp-live-default-fact-gate-off-20260520-02` |  |
| `ciar-exp-live-default-fact-gate-off-20260520-03` | `fact_gate` | `off` | 3 | Complete | `ciar-challenge-live-default-fact-gate-off-20260520-03` | `logs/ciar_challenge/ciar-exp-live-default-fact-gate-off-20260520-03` |  |
| `ciar-exp-live-default-fact-gate-suppress-20260520-01` | `fact_gate` | `suppress_superseded` | 1 | Complete | `ciar-challenge-live-default-fact-gate-suppress-20260520-01` | `logs/ciar_challenge/ciar-exp-live-default-fact-gate-suppress-20260520-01` |  |
| `ciar-exp-live-default-fact-gate-suppress-20260520-02` | `fact_gate` | `suppress_superseded` | 2 | Complete | `ciar-challenge-live-default-fact-gate-suppress-20260520-02` | `logs/ciar_challenge/ciar-exp-live-default-fact-gate-suppress-20260520-02` |  |
| `ciar-exp-live-default-fact-gate-suppress-20260520-03` | `fact_gate` | `suppress_superseded` | 3 | Complete | `ciar-challenge-live-default-fact-gate-suppress-20260520-03` | `logs/ciar_challenge/ciar-exp-live-default-fact-gate-suppress-20260520-03` |  |
| `ciar-exp-live-default-hybrid-gate-off-20260520-01` | `hybrid_gate` | `off` | 1 | Complete | `ciar-challenge-live-default-hybrid-gate-off-20260520-01` | `logs/ciar_challenge/ciar-exp-live-default-hybrid-gate-off-20260520-01` |  |
| `ciar-exp-live-default-hybrid-gate-off-20260520-02` | `hybrid_gate` | `off` | 2 | Complete | `ciar-challenge-live-default-hybrid-gate-off-20260520-02` | `logs/ciar_challenge/ciar-exp-live-default-hybrid-gate-off-20260520-02` |  |
| `ciar-exp-live-default-hybrid-gate-off-20260520-03` | `hybrid_gate` | `off` | 3 | Complete | `ciar-challenge-live-default-hybrid-gate-off-20260520-03` | `logs/ciar_challenge/ciar-exp-live-default-hybrid-gate-off-20260520-03` |  |
| `ciar-exp-live-default-hybrid-gate-suppress-20260520-01` | `hybrid_gate` | `suppress_superseded` | 1 | Complete | `ciar-challenge-live-default-hybrid-gate-suppress-20260520-01` | `logs/ciar_challenge/ciar-exp-live-default-hybrid-gate-suppress-20260520-01` | OpenRouter provider failure recovered through rule fallback |
| `ciar-exp-live-default-hybrid-gate-suppress-20260520-02` | `hybrid_gate` | `suppress_superseded` | 2 | Complete | `ciar-challenge-live-default-hybrid-gate-suppress-20260520-02` | `logs/ciar_challenge/ciar-exp-live-default-hybrid-gate-suppress-20260520-02` |  |
| `ciar-exp-live-default-hybrid-gate-suppress-20260520-03` | `hybrid_gate` | `suppress_superseded` | 3 | Complete | `ciar-challenge-live-default-hybrid-gate-suppress-20260520-03` | `logs/ciar_challenge/ciar-exp-live-default-hybrid-gate-suppress-20260520-03` |  |

Live command pattern:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge_with_env.py \
  --run-id <run-id> \
  --phoenix-project-name <phoenix-project> \
  --force-data-node-services \
  --skip-provider-health \
  --provider-health-skip-reason "provider health checked separately; default policy evaluation" \
  --promotion-policy-mode <fact_gate|hybrid_gate> \
  --contradiction-policy-mode <off|suppress_superseded> \
  --scenario-id segment_mismatch \
  --scenario-id contradiction_update \
  --scenario-id small_talk
```

Results documentation requirements:

- For every run, record artifact availability for `summary.md`,
  `promotion_results.json`, `alternative_scores.json`, `events.jsonl`, and
  `run_manifest.json`.
- For each policy pair, aggregate promoted, filtered, review-only, and
  suppressed fact counts by scenario.
- Record small-talk leakage, urgent-fact retention, stale/superseded-fact
  handling, raw-vs-stored CIAR differences, and provider/backend failures.
- Classify failed or partial runs as operational evidence unless artifacts show
  a policy-level failure.
- Update
  `docs/reports/2026-05-19-ciar-challenge-experiment-results.md` with a
  `Default Policy Evaluation` section after live runs and analysis complete.

Important findings log:

| Date/Time | Run/Config | Finding | Evidence File | Impact On Default-Policy Decision | Follow-up Needed |
|---|---|---|---|---|---|
| 2026-05-20 | Planning | Live evidence must compare `fact_gate` and `hybrid_gate` with contradiction policy `off` and `suppress_superseded`; dry CIAR-SUP-1 evidence alone is not enough to choose a default. | This tracker | Establishes 12-run matrix before any runtime default change | Execute matrix and aggregate results |
| 2026-05-20 | 12-run live matrix | All planned live artifacts were produced; no required artifact gaps were found. | `logs/ciar_challenge/ciar-def-1-analysis-20260520.md` | The matrix is usable for a default-policy recommendation. | Keep artifacts as ignored operational evidence; document summary in the report. |
| 2026-05-20 | `fact_gate` vs `hybrid_gate` | `hybrid_gate` retained urgent `segment_mismatch` facts while marking weak facts review-only; `fact_gate` filtered but did not preserve review-only evidence. | `logs/ciar_challenge/ciar-def-1-analysis-20260520.json` | Supports `hybrid_gate` as the experimental promotion default candidate. | Prepare a separate default-change implementation after approval. |
| 2026-05-20 | `suppress_superseded` live runs | Live `suppress_superseded` runs emitted zero `fact_suppressed` events; stale Oakland-style facts were usually filtered or review-only instead. | `promotion_results.json` across `ciar-exp-live-default-*-suppress-*` | Does not support changing contradiction default to `suppress_superseded` yet. | Add a follow-up to improve live supersession matching before defaulting suppression. |
| 2026-05-20 | `small_talk` scenario | All 12 live runs kept `small_talk` at zero promoted facts. | `logs/ciar_challenge/ciar-def-1-analysis-20260520.md` | Confirms policy comparisons did not regress the small-talk boundary. | Keep `small_talk` in the regression set. |

Decision criteria:

- Prefer `hybrid_gate + suppress_superseded` only if it retains important facts
  more reliably than `fact_gate`, keeps weak facts review-only or filtered,
  suppresses explicit superseded facts, and preserves zero or near-zero
  `small_talk` promotion.
- Reject `fact_gate` as the default if it materially drops urgent or corrected
  facts more often than `hybrid_gate`, even when it produces cleaner storage.
- Reject `suppress_superseded` as the contradiction default if live runs show
  mis-suppression, missing correction facts, or insufficient audit provenance.
- If evidence is directionally positive but noisy, document
  `hybrid_gate + suppress_superseded` as the proposed experimental default
  rather than changing the production/runtime default immediately.

Current recommendation from CIAR-DEF-1:

- Proposed experimental promotion default candidate: `hybrid_gate`.
- Proposed contradiction default: keep `off` for now.
- Do not default `suppress_superseded` yet; live runs did not demonstrate
  suppression, even though dry runs did.
- Next implementation decision should be whether to switch the runtime
  promotion default from `segment_gate` to `hybrid_gate`.

## Proposed Next Steps After CIAR-DEF-1

Update on 2026-05-21: CIAR-DEF-2, CIAR-SUP-2, and CIAR-EVAL-2 are now
complete. The current runtime default is `hybrid_gate+off`. The 2026-05-21
live matrix keeps `small_talk` at zero promoted facts, shows `segment_gate`
still over-promotes correction scenarios, and shows `hybrid_gate` preserving
review-only evidence that `fact_gate` discards. `suppress_superseded` produced
live `fact_suppressed` events for `contradiction_update`, but not broadly
enough across stale preference, explicit reversal, and repeated correction
scenarios to become the default.

The original next steps below were ordered by the evidence from the 2026-05-20
live matrix and are retained for traceability.

1. Plan and implement CIAR-DEF-2 after explicit approval.
   - Justification: `hybrid_gate` preserved the small-talk boundary and
     retained urgent `segment_mismatch` facts while adding review-only evidence
     for weak facts; `fact_gate` discarded that audit trail.
   - Implementation intent: change only the experimental/default configuration
     path for promotion policy to `hybrid_gate`; keep `segment_gate` and
     `fact_gate` as explicit modes.
   - Guardrail: do not change contradiction default in the same step.
   - Verification: run focused promotion policy tests, a dry challenge run, and
     at least one focused live smoke run with the default path rather than an
     explicit `--promotion-policy-mode` override.

2. Plan CIAR-SUP-2 before defaulting contradiction suppression.
   - Justification: dry CIAR-SUP-1 proved suppression can work, but all 12
     live CIAR-DEF-1 runs recorded `facts_suppressed=0`.
   - Implementation intent: make supersession matching robust to live
     LLM-extracted wording, especially cases where old Oakland facts and new
     Los Angeles correction facts are extracted as separate paraphrases.
   - Guardrail: keep this above CIAR and outside `src/storage/`; do not change
     schema or migrations.
   - Verification: add unit tests for paraphrased old/new route facts, rerun
     dry supersession, then run a focused live contradiction slice.

3. Broaden evaluation with CIAR-EVAL-2.
   - Justification: CIAR-DEF-1 used only three deterministic scenarios; that is
     enough for an experimental default candidate, not a broad production
     default.
   - Implementation intent: add focused scenarios for stale preferences,
     explicit reversals, repeated corrections, low-value assistant
     acknowledgements, and urgent operational facts with surrounding chatter.
   - Verification: use `analyze_ciar_policy_runs.py` as the aggregate path and
     update the results report with scenario-level deltas.

4. Reduce operational noise with CIAR-OPS-1.
   - Justification: the live matrix had one sandbox-blocked Phoenix false start
     and one OpenRouter provider failure recovered through rule fallback.
   - Implementation intent: make run manifests capture provider fallback and
     Phoenix preflight status clearly enough that future analysis does not
     depend on console logs.
   - Verification: run one live smoke and confirm the manifest classifies
     provider, Phoenix, cleanup, and fallback status.

5. Keep CIAR-DB-1 separate.
   - Justification: fresh database readiness still matters, but the CIAR policy
     work intentionally avoided storage and migration changes.
   - Guardrail: do not edit migrations without explicit authorization.

## Intended Policy Interface

Promotion policy should become explicit rather than implicit. The first planned
configuration key is:

```text
promotion_policy_mode
```

Accepted values:

- `segment_gate`: segment CIAR decides whether extraction/storage proceeds;
  previous certainty/impact inheritance and threshold floor behavior is
  preserved, with honest fact-level provenance recorded separately.
- `fact_gate`: every extracted fact must independently meet the configured CIAR
  threshold before L2 storage.
- `hybrid_gate`: segment CIAR permits extraction, but below-threshold facts are
  kept out of L2 as review-only artifacts; obvious conversational residue is
  also marked review-only by the first evidence gate.

The implementation must preserve benchmark continuity by making any current
behavior explicit rather than silently changing it.

## Required Artifact Fields

Future dry and live runs should preserve the existing artifact set:

- `summary.md`
- `promotion_results.json`
- `l2_facts.json`
- `alternative_scores.json`
- `events.jsonl`
- `ciar_calls.jsonl`
- `formula_probes.json`
- `run_manifest.json`
- `scenarios.json`

`alternative_scores.json` should contain these fields for each promoted or
reviewed fact:

- `scenario_id`
- `session_id`
- `fact_id`
- `content`
- `expectation`
- `segment_ciar`
- `raw_fact_ciar`
- `pre_inheritance_ciar`
- `post_inheritance_ciar`
- `stored_ciar`
- `ciar_score_source`
- `current_runtime_ciar` if retained for backward compatibility
- `fact_gate_decision`
- `floor_applied`
- `review_only` when applicable
- `promotion_policy_mode`
- `utility_candidate_v0` or the active evidence-ranker score
- `evidence_quality_flags`

`evidence_quality_flags` should include, at minimum:

- `llm_extracted`
- `rule_fallback`
- `segment_inherited`
- `contradiction_candidate`
- `conversational_residue`
- `domain_signal`

## Execution History

### Dry-run validation

Completed fixture:

```text
logs/ciar_challenge/ciar-exp-dry-current-20260519-01
```

Command pattern:

```bash
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-current-<timestamp> \
  --phoenix-access-mode ssh_tunnel
```

Expected and observed dry-run behavior:

- Artifact files are written under the run directory.
- High-value scenarios promote facts.
- Low-value and speculative scenarios do not promote facts.
- `contradiction_update` promotes both old and corrected dry-run facts in the
  baseline, demonstrating that CIAR alone does not resolve truth or
  supersession.
- `segment_mismatch` promotes both urgent and low-value dry-run facts,
  demonstrating the segment/fact policy problem.

### Focused live run

Completed fixture:

```text
logs/ciar_challenge/ciar-exp-live-focused-tencent-20260519-06
```

Successful command pattern:

```bash
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

Future live runs must be explicitly approved because they use real LLM/backend
calls. Focused CIAR live runs currently use `--skip-provider-health` with a
recorded reason and rely on the actual promotion path plus artifacts for
provider behavior.

### Policy comparison runs

Dry comparison artifacts:

- `ciar-exp-dry-segment-gate-20260520-01`: preserves previous behavior;
  `segment_mismatch` promotes both facts.
- `ciar-exp-dry-fact-gate-20260520-01`: filters the low-value
  `segment_mismatch` fact.
- `ciar-exp-dry-hybrid-gate-20260520-01`: stores the urgent
  `segment_mismatch` fact and records the low-value fact as review-only.

Live comparison artifacts:

- `ciar-exp-live-segment-gate-20260520-01`: matches the baseline shape;
  `contradiction_update` promoted 3 facts, `segment_mismatch` promoted 4 facts,
  and `small_talk` promoted 0 facts.
- `ciar-exp-live-fact-gate-20260520-01`: promoted 2 and filtered 3 in
  `contradiction_update`; promoted 1 and filtered 2 in `segment_mismatch`.
- `ciar-exp-live-hybrid-gate-20260520-01`: promoted 2 and marked 1 review-only
  in `contradiction_update`; promoted 2 and marked 2 review-only in
  `segment_mismatch`.
- `ciar-exp-live-hybrid-gate-20260520-02`: rerun after artifact provenance
  recovery; `segment_mismatch` promoted 3 and marked 2 review-only, while
  `contradiction_update` had no promoted facts due to live LLM empty-segment
  behavior.

## Implementation Sequence

1. Fix experiment observability first. Complete.
   - Join `ciar_calls.jsonl` to stored L2 facts reliably.
   - Prefer stable fact identifiers or deterministic join keys carried through
     extraction, scoring, storage, and artifact collection.
   - Re-run the focused dry scenario and confirm non-null `raw_fact_ciar`.

2. Add promotion policy modes. Implemented locally; full verification pending.
   - Introduce the named policy mode at the promotion engine boundary.
   - Preserve current behavior as an explicit mode.
   - Add tests for `segment_gate`, `fact_gate`, and `hybrid_gate`.
   - Ensure tests assert both promoted counts and score metadata.

3. Add score separation and evidence metadata. Implemented locally; artifact
   verification pending.
   - Record segment CIAR, raw fact CIAR, stored CIAR, policy mode, and gate
     decision separately.
   - Do not overload `ciar_score` to mean both routing score and fact score.
   - Include feature provenance for certainty and impact where available.

4. Add the first evidence policy. Implemented locally for `hybrid_gate`; dry and
   live comparisons pending.
   - Implement the minimal fact-level evidence gate or `EvidenceRanker` outside
     `src/storage/`.
   - Treat contradiction/supersession as a policy signal, not a CIAR formula
     change.
   - Keep per-factor explanations visible in artifacts and future interfaces.

5. Keep completed conformance cleanup as a regression gate.
   - CIAR-CONF-1 now covers stale CIAR docstrings and explanatory text.
   - Tests cover model validator score recomputation and v2 route behavior.
   - Tests cover CIAR clamping, high access counts, component overrides, and
     future/stale timestamp behavior.
   - Continue tracking provider-health preflight behavior as operational debt.
   - Plan the PostgreSQL migration cleanup with explicit authorization before
     editing migration/schema files.

## Verification Plan

Document-only updates:

- Review links, paths, and tracker status manually.
- Do not run the full test suite solely for markdown changes.

Harness updates:

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest tests/scripts/test_ciar_challenge_experiment.py -v
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-current-<timestamp> \
  --phoenix-access-mode ssh_tunnel
```

Policy code updates under `src/`:

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest tests/ -v
```

Live reruns:

- Require explicit user approval because they make real LLM calls and touch
  live Redis/PostgreSQL/Phoenix services.
- Must record run ID, Phoenix project, model, provider health decision,
  artifact directory, and cleanup status.
- Failed or dirty live runs must be documented as operational evidence, not
  CIAR policy evidence.

Migration/schema cleanup:

- Requires explicit user authorization before editing migration/schema files.
- Must be verified against a fresh dedicated PostgreSQL database.
- Must not rely on manual production-state repair.

## Definition Of Done

Each workstream is done only when all of the following are true:

- The implementation or decision is linked from this plan.
- The relevant artifact, test, or report exists and is named in the tracker.
- Verification commands were run or intentionally skipped with a written reason.
- Any live run records whether provider health was checked or intentionally
  skipped.
- Any failure is classified as operational, policy, data, or mechanism-layer
  evidence.
- No protected area was changed without explicit user authorization.

CIAR v1 can be considered solid when:

- ADR-004, config, scorer, model validator, tools, and docs describe the same
  behavior.
- Promotion reports segment score and fact score separately.
- v2 routes do not create inconsistent fact components and scores.
- Tests cover clamping, high access counts, explicit component overrides, stale
  facts, and promotion policy modes.
- Phoenix spans and experiment artifacts expose CIAR inputs, score, threshold,
  decision, and provenance.

The broader memory policy can be considered stronger than CIAR when:

- retrieval or promotion ranking is query/evidence-aware where appropriate,
- evidence quality is visible,
- contradictions are surfaced rather than hidden,
- context injection can explain why each memory item was included,
- raw, unified, and agentic modes are available through documented interfaces.
