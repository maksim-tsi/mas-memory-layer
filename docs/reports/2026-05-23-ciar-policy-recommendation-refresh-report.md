# CIAR Policy Recommendation Refresh Report

Date: 2026-05-23
Status: complete live-evaluated

## Summary

The final CIAR policy refresh ran a six-run live LLM matrix with required
provider health, current `.env` service URLs, Redis timeout `60s`, model
`tencent/hy3-preview`, and explicit Phoenix project names. All six runs
completed as `policy_evidence` with provider health checked, runtime setup
`ok`, cleanup `ok`, Phoenix UI reachable, and no scenario errors.

Recommendation:

- Keep `hybrid_gate` as the promotion default.
- Keep contradiction default `off`.
- Keep `suppress_superseded` opt-in until live extraction/suppression behavior
  is less sensitive to scenario phrasing and fact granularity.

This batch changed only reporting/supporting tooling and docs. It did not
change CIAR scoring, thresholds, promotion defaults, contradiction policy,
storage adapters, dependencies, `.env`, prompts, or schemas.

## Verification

Preflight and local checks:

- `uname -a`, `hostname`, `pwd`: completed.
- `test -d .venv`: passed.
- `./.venv/bin/python -c 'import sys; print(sys.executable)'`: reported the
  repo-local `.venv/bin/python`.
- `./.venv/bin/ruff check .`: passed.
- `./.venv/bin/python scripts/experiments/run_ciar_challenge_with_env.py --presence-only`:
  passed without printing secret values.
- `./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env --json`:
  Redis, PostgreSQL, Phoenix, Qdrant, Neo4j, and Typesense checks passed.

Script tests:

- `./.venv/bin/pytest tests/scripts/test_export_phoenix_spans.py -v`:
  passed.
- `./.venv/bin/pytest tests/scripts/test_export_phoenix_spans.py tests/scripts/test_ciar_policy_analysis.py -v`:
  `13 passed`.

Live matrix and Phoenix export:

- Six live runs completed with required provider health.
- `./.venv/bin/python scripts/experiments/analyze_ciar_policy_runs.py ...`:
  wrote `logs/ciar_challenge/ciar-policy-refresh-20260523.json` and
  `logs/ciar_challenge/ciar-policy-refresh-20260523.md`.
- `./.venv/bin/python scripts/debug/export_phoenix_spans.py ...`:
  wrote raw span JSON under
  `logs/ciar_challenge/phoenix-policy-refresh-20260523` and summary
  `logs/ciar_challenge/ciar-policy-refresh-phoenix-summary-20260523.json`.

The CIAR regression pack was not rerun for this batch because the implementation
added only a Phoenix export helper plus docs and did not modify CIAR harness,
analyzer, scoring, or policy behavior.

## Live Runs

| Run ID | Config | Phoenix Project | Run Quality |
|---|---|---|---|
| `ciar-exp-live-policy-refresh-hybrid-off-20260523-01` | `hybrid_gate+off` | `ciar-challenge-policy-refresh-hybrid-off-20260523-01` | `policy_evidence` |
| `ciar-exp-live-policy-refresh-hybrid-off-20260523-02` | `hybrid_gate+off` | `ciar-challenge-policy-refresh-hybrid-off-20260523-02` | `policy_evidence` |
| `ciar-exp-live-policy-refresh-fact-off-20260523-01` | `fact_gate+off` | `ciar-challenge-policy-refresh-fact-off-20260523-01` | `policy_evidence` |
| `ciar-exp-live-policy-refresh-segment-off-20260523-01` | `segment_gate+off` | `ciar-challenge-policy-refresh-segment-off-20260523-01` | `policy_evidence` |
| `ciar-exp-live-policy-refresh-hybrid-suppress-20260523-01` | `hybrid_gate+suppress_superseded` | `ciar-challenge-policy-refresh-hybrid-suppress-20260523-01` | `policy_evidence` |
| `ciar-exp-live-policy-refresh-hybrid-suppress-20260523-02` | `hybrid_gate+suppress_superseded` | `ciar-challenge-policy-refresh-hybrid-suppress-20260523-02` | `policy_evidence` |

Run quality counts:

| Run Quality | Count |
|---|---:|
| `policy_evidence` | 6 |

No operational replacement runs were required.

## Promotion And Review-Only Findings

`hybrid_gate+off` remains the best default promotion policy candidate:

- Both `hybrid_gate+off` runs were clean policy evidence.
- Positive controls promoted in live evidence, though with live segmentation
  variance: `urgent_event` promoted in both `hybrid_gate+off` runs, while
  `clear_constraint` promoted in one of two.
- `assistant_acknowledgement_noise` promoted no facts under `hybrid_gate+off`.
- `urgent_with_chatter` promoted operational facts and produced some
  review-only residue evidence. However, one assistant-commitment-like fact was
  still promoted in the live aggregate, so residue handling is improved but not
  perfect under live extraction variance.
- `assistant_inferred` produced review-only rows under `hybrid_gate+off`; this
  was safer than `segment_gate+off`, which promoted assistant recommendation
  and tentative-preference style content.
- `access_reinforced_low_signal` did not reach extraction in live runs. This is
  an observability limitation, not a policy failure, because no weak
  access-reinforced content was promoted.

Comparator evidence:

- `segment_gate+off` remained too permissive for live extracted facts. It
  promoted all extracted `assistant_inferred` and `urgent_with_chatter` facts,
  including one residue-promoted row.
- `fact_gate+off` was stricter and promoted useful facts, but it does not
  provide the `hybrid_gate` review-only policy surface that we now use for
  auditable non-storage evidence.

## Suppression Findings

Focused suppression evidence:

| Config | Scenario | Runs | Promoted | Suppressed | Suppression Rate |
|---|---|---:|---:|---:|---:|
| `hybrid_gate+off` | `contradiction_update` | 2 | 1 | 0 | 0.00% |
| `hybrid_gate+off` | `repeated_correction` | 2 | 2 | 0 | 0.00% |
| `hybrid_gate+suppress_superseded` | `contradiction_update` | 2 | 2 | 1 | 33.33% |
| `hybrid_gate+suppress_superseded` | `repeated_correction` | 2 | 4 | 7 | 63.64% |

`suppress_superseded` clearly changes behavior in the intended direction, but
it is not ready as the default:

- `repeated_correction` is now live-observable and produces strong suppression
  evidence.
- `contradiction_update` produced one suppressed prior fact across two clean
  runs, but the behavior remains extraction-sensitive.
- Some `repeated_correction` current/summary facts were also suppressed or
  review-only depending on extraction granularity, which means the policy is
  useful but still needs more precision before defaulting it.

Recommendation: keep `suppress_superseded` opt-in and continue collecting live
evidence before considering a default switch.

## Phoenix Span Summary

Phoenix export covered all six live projects:

| Project | Spans | CIAR Score Spans | Fact Extract Spans | Errors |
|---|---:|---:|---:|---:|
| `ciar-challenge-policy-refresh-hybrid-off-20260523-01` | 29 | 8 | 4 | 0 |
| `ciar-challenge-policy-refresh-hybrid-off-20260523-02` | 39 | 16 | 6 | 0 |
| `ciar-challenge-policy-refresh-fact-off-20260523-01` | 39 | 17 | 5 | 0 |
| `ciar-challenge-policy-refresh-segment-off-20260523-01` | 39 | 17 | 5 | 0 |
| `ciar-challenge-policy-refresh-hybrid-suppress-20260523-01` | 27 | 12 | 3 | 0 |
| `ciar-challenge-policy-refresh-hybrid-suppress-20260523-02` | 28 | 13 | 3 | 0 |

Total exported spans: `201`.

Span names present across projects included:

- `yaam.ciar.score`
- `yaam.llm.fact_extract`
- `yaam.llm.topic_segment`
- experiment node spans for build, setup, seed, promotion, alternative scoring,
  collection, summary, and cleanup

All exported spans had status `UNSET`; the Phoenix summary reported
`error_count=0` for every project.

## Final Recommendation

Keep `hybrid_gate` as the CIAR promotion default.

Rationale:

- Both default-candidate `hybrid_gate+off` runs were clean live policy evidence.
- `hybrid_gate` retains positive operational facts while making review-only
  evidence visible for residue/speculative/inferred content.
- It is less permissive than `segment_gate`, which still promotes extracted
  assistant-action and tentative-preference content.
- It is more operationally useful than plain `fact_gate` because it preserves a
  review-only artifact lane instead of reducing the decision to store/filter.

Keep contradiction default `off`.

Rationale:

- `suppress_superseded` works well enough to remain a valuable opt-in mode.
- The live refresh did not satisfy the stricter default-change bar: both
  suppression scenarios did not cleanly and consistently suppress old facts
  while preserving only current facts in both runs.
- `contradiction_update` remains extraction-sensitive, and `repeated_correction`
  still needs finer current-vs-superseded distinction when live extraction emits
  broad summary facts.

## Remaining Evidence Gaps

- Live `speculative_claim` did not reach extraction in this matrix, so the dry
  review-only behavior remains stronger evidence than live behavior for that
  specific fixture.
- Live `access_reinforced_low_signal` did not reach extraction and current live
  extraction does not populate `access_count`; Phoenix/artifact evidence cannot
  yet prove `recency_access_guardrail=true` in live runs.
- Residue filtering is improved, but one live `urgent_with_chatter` aggregate
  row still promoted assistant-commitment-like content under `hybrid_gate+off`.
- Suppression should remain opt-in until current-fact preservation is more
  robust across both focused contradiction scenarios.

## Artifacts

- Plan:
  `docs/plan/2026-05-23-ciar-policy-recommendation-refresh-plan.md`
- Analysis JSON:
  `logs/ciar_challenge/ciar-policy-refresh-20260523.json`
- Analysis Markdown:
  `logs/ciar_challenge/ciar-policy-refresh-20260523.md`
- Phoenix summary:
  `logs/ciar_challenge/ciar-policy-refresh-phoenix-summary-20260523.json`
- Raw Phoenix spans:
  `logs/ciar_challenge/phoenix-policy-refresh-20260523/`
- Export helper:
  `scripts/debug/export_phoenix_spans.py`
- Export helper tests:
  `tests/scripts/test_export_phoenix_spans.py`
