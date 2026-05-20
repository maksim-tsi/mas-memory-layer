# CIAR Challenge Experiment and Implementation Coordination Plan

Date: 2026-05-19
Last updated: 2026-05-20
Status: Live evidence collected; implementation coordination active
Related:
`docs/reports/2026-05-18-ciar-design-and-implementation-audit.md`,
`docs/reports/2026-05-19-ciar-challenge-experiment-results.md`,
`scripts/experiments/run_ciar_challenge.py`

## Summary

The CIAR challenge experiment has moved from execution readiness to
post-live-run implementation coordination. The dry run and focused live run
produced enough evidence to proceed on policy and observability work above the
storage layer.

CIAR v1 remains the deterministic L1 -> L2 retention baseline. The next work is
to make promotion behavior explicit, separate segment-level and fact-level
signals, improve experiment observability, and prepare an evidence policy above
CIAR. This plan tracks that work so implementation can be split safely without
architectural drift.

## Current Baseline

Baseline fixture:

```text
logs/ciar_challenge/ciar-exp-live-focused-tencent-20260519-06
```

Baseline Phoenix project:

```text
ciar-challenge-focused-tencent-20260519-06
```

Baseline runtime:

- OpenRouter model: `tencent/hy3-preview`
- output-token budget: `8192`
- OpenRouter timeout: `120s`
- Redis/PostgreSQL/Phoenix host: `192.168.107.187`
- PostgreSQL database: `yaam-test`
- provider order: `["openrouter"]`
- provider-health preflight: skipped for the successful focused run

Baseline finding:

- `small_talk` produced no promoted facts.
- `contradiction_update` produced no promoted facts because its live segment
  score was below threshold.
- `segment_mismatch` promoted one segment and five facts, including low-value
  interaction facts, because segment-level certainty and impact dominated the
  promoted facts' stored CIAR scores.

Instrumentation caveat:

- The live run contains five `ciar_calls.jsonl` records, but
  `alternative_scores.json` has `raw_fact_ciar=null` for live rows because the
  scorer-call fact IDs do not match the stored L2 fact IDs. The policy issue is
  visible, but the automated raw-vs-stored fact score comparison is not yet
  reliable.

## Scope And Boundaries

In scope:

- Maintain the isolated CIAR challenge harness and its dry/live artifact set.
- Preserve `ciar-exp-live-focused-tencent-20260519-06` as the current
  regression fixture until a cleaner run replaces it.
- Add observability needed to compare segment, raw fact, and stored fact scores.
- Add explicit promotion policy modes and tests.
- Add a first evidence gate or `EvidenceRanker` above CIAR and above storage.
- Update CIAR conformance docs/tests so scorer, validator, tools, and routes
  describe the same behavior.
- Track operational follow-ups that affect experiment repeatability.

Out of scope without explicit user approval:

- `src/storage/` or other low-level DB adapter changes.
- Dependency or lockfile changes.
- `.github/` workflow/instruction changes.
- `.env`, secret files, key files, or printing secret values.
- Treating one focused live run as benchmark-grade statistical evidence.

## Progress Tracker

| ID | Status | Workstream | Owner | Dependencies | Tracking Evidence | Done When |
|---|---|---|---|---|---|---|
| CIAR-EXP-0 | Complete | Dry/live evidence collection, model selection, artifact capture, and results report | Experiment owner | None | `docs/reports/2026-05-19-ciar-challenge-experiment-results.md` | Dry and live artifacts exist, results are documented, and the live fixture is named |
| CIAR-EXP-1 | In progress | Fix harness observability so raw CIAR calls join reliably to stored L2 facts | Experiment owner | CIAR-EXP-0 | `alternative_scores.json`, `ciar_calls.jsonl`, `l2_facts.json` | Live `alternative_scores.json` has non-null `raw_fact_ciar` for promoted facts and can explain raw-vs-stored score differences |
| CIAR-EXP-2 | To do | Stabilize provider-health preflight or document an explicit bypass policy | Experiment owner | CIAR-EXP-0 | `run_manifest.json`, provider health output | Future live runs either record provider health without destabilizing Redis setup or intentionally record `provider_health_skipped_reason` |
| CIAR-POL-1 | To do | Add explicit promotion policy modes: `segment_gate`, `fact_gate`, `hybrid_gate` | Memory policy owner | CIAR-EXP-1 recommended | Promotion engine tests and config docs | Promotion behavior is selected by a named mode, with current behavior preserved only as an explicit mode |
| CIAR-POL-2 | To do | Separate segment, raw fact, and stored fact score metadata | Memory policy owner | CIAR-POL-1 | Promotion telemetry, L2 fact metadata, experiment artifacts | Promotion outputs report `segment_ciar`, `raw_fact_ciar`, and `stored_ciar` without overwriting the meaning of each score |
| CIAR-POL-3 | To do | Add first fact-level evidence gate or `EvidenceRanker` before L2 store | Memory policy owner | CIAR-POL-1, CIAR-POL-2 | Policy tests, focused dry run, focused live run if approved | Low-value facts in `segment_mismatch` are explainably filtered, downgraded, or marked for review while urgent facts remain promotable |
| CIAR-CONF-1 | To do | CIAR conformance cleanup: stale docstrings, v2 score recomputation tests, clamping/high-access/stale-fact coverage | Memory policy owner | CIAR-EXP-0 | CIAR unit tests, v2 route tests, docs diff | ADR-004, scorer, validators, tools, and docs describe the same CIAR behavior |
| CIAR-DB-1 | To do | Plan schema/migration cleanup for `002_l2_tsvector_index.sql` volatile `NOW()` partial-index predicate | Database owner | Explicit user approval before migration edits | Migration file and fresh database verification notes | Fresh dedicated PostgreSQL setup can apply schema cleanly without manual index workaround |
| CIAR-MCP-1 | Backlog | Extract shared CIAR/evidence service layer for future REST, LangChain, and MCP adapters | Interface owner | CIAR-POL-2, CIAR-POL-3 | RFC update or implementation plan | LangChain tools and future MCP tools can call stable service functions rather than duplicating policy logic |

Status meanings:

- `Complete`: implemented or documented and no longer blocking current work.
- `In progress`: next implementation target or known partial implementation.
- `To do`: approved direction but not yet implemented.
- `Backlog`: important follow-on work that should not block CIAR experiment
  hardening.

## Intended Policy Interface

Promotion policy should become explicit rather than implicit. The first planned
configuration key is:

```text
promotion_policy_mode
```

Accepted values:

- `segment_gate`: segment CIAR decides whether extraction/storage proceeds;
  fact scores remain honest and are recorded separately.
- `fact_gate`: every extracted fact must independently meet the configured CIAR
  threshold before L2 storage.
- `hybrid_gate`: segment CIAR permits extraction, but below-threshold facts are
  either filtered, downgraded, or stored as review evidence according to policy
  configuration.

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
- `stored_ciar`
- `current_runtime_ciar` if retained for backward compatibility
- `fact_gate_decision`
- `floor_applied`
- `promotion_policy_mode`
- `utility_candidate_v0` or the active evidence-ranker score
- `evidence_quality_flags`

`evidence_quality_flags` should include, at minimum:

- `llm_extracted`
- `rule_fallback`
- `segment_inherited`
- `contradiction_candidate`
- `assistant_inferred`
- `low_value_interaction`

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
- `contradiction_update` promotes both old and corrected dry-run facts,
  demonstrating that CIAR does not resolve truth or supersession by itself.
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
calls. Until CIAR-EXP-2 is complete, focused CIAR live runs should use
`--skip-provider-health` and rely on the actual promotion path plus artifacts
for provider behavior.

## Implementation Sequence

1. Fix experiment observability first.
   - Join `ciar_calls.jsonl` to stored L2 facts reliably.
   - Prefer stable fact identifiers or deterministic join keys carried through
     extraction, scoring, storage, and artifact collection.
   - Re-run the focused dry scenario and confirm non-null `raw_fact_ciar`.

2. Add promotion policy modes.
   - Introduce the named policy mode at the promotion engine boundary.
   - Preserve current behavior as an explicit mode.
   - Add tests for `segment_gate`, `fact_gate`, and `hybrid_gate`.
   - Ensure tests assert both promoted counts and score metadata.

3. Add score separation and evidence metadata.
   - Record segment CIAR, raw fact CIAR, stored CIAR, policy mode, and gate
     decision separately.
   - Do not overload `ciar_score` to mean both routing score and fact score.
   - Include feature provenance for certainty and impact where available.

4. Add the first evidence policy.
   - Implement the minimal fact-level evidence gate or `EvidenceRanker` outside
     `src/storage/`.
   - Treat contradiction/supersession as a policy signal, not a CIAR formula
     change.
   - Keep per-factor explanations visible in artifacts and future interfaces.

5. Clean up conformance and operational debt.
   - Update stale CIAR docstrings and explanatory text.
   - Add tests for model validator score recomputation and v2 route behavior.
   - Add tests for CIAR clamping, high access counts, component overrides, and
     stale facts.
   - Resolve provider-health preflight behavior.
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
