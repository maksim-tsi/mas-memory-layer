# CIAR Live Review-Only Checkpoint Report

Date: 2026-05-23
Status: Complete with clean operational evidence and partial preferred policy evidence
Related plan: `docs/plan/2026-05-23-ciar-live-review-only-checkpoint-plan.md`

## Summary

The focused live `hybrid_gate+off` checkpoint completed successfully with
required provider health and clean operational classification. The run provides
usable live evidence for Batch 4-6 review-only behavior, with the expected
limitation that live recency/access guardrail evidence cannot fully appear
until live extraction or harness metadata can provide `access_count`.

Run:

- `ciar-exp-live-review-only-checkpoint-20260523-01`
- model: `tencent/hy3-preview`
- promotion policy: `hybrid_gate`
- contradiction policy: `off`
- operational classification: `policy_evidence`

Artifacts:

- `logs/ciar_challenge/ciar-exp-live-review-only-checkpoint-20260523-01`
- `logs/ciar_challenge/ciar-live-review-only-checkpoint-20260523.json`
- `logs/ciar_challenge/ciar-live-review-only-checkpoint-20260523.md`

## Preflight And Runtime

Preflight passed:

- `.venv` existed and interpreter resolved to repo `.venv`.
- `./.venv/bin/ruff check .`: passed.
- `.env` presence check found required key names without printing values.
- YAAM data-node diagnostics passed:
  - Redis `PING`: ok;
  - Postgres TCP: ok;
  - Phoenix HTTP: ok;
  - Qdrant HTTP: ok;
  - Neo4j TCP: ok;
  - Typesense HTTP: ok.

Runtime setup:

- provider health: checked and passed for OpenRouter, Gemini, and Mistral;
- provider-health cleanup: ok;
- post-health Redis probe: ok;
- `runtime_setup.status`: ok;
- Phoenix endpoint: `http://192.168.107.187:6006/v1/traces`;
- cleanup status: ok.

## Scenario Results

| Scenario | Segment Score | Segment Decision | Facts Extracted | Promoted | Review-Only | Interpretation |
|---|---:|---|---:|---:|---:|---|
| `clear_constraint` | 1.00 | promote | 1 | 1 | 0 | Positive control passed. |
| `urgent_event` | 0.95 | promote | 5 | 3 | 2 | Positive control passed; assistant-action residue was review-only. |
| `urgent_with_chatter` | 0.90 | promote | 4 | 1 | 3 | Residue behavior passed. |
| `assistant_acknowledgement_noise` | 0.15 | ignore | 0 | 0 | 0 | Residue was not promoted; no extraction needed. |
| `assistant_inferred` | 0.80 | promote | 3 | 1 | 2 | Partial speculative/inference evidence passed. |
| `speculative_claim` | 0.57 | ignore | 0 | 0 | 0 | Inconclusive for review-only extraction; no speculative promotion. |
| `access_reinforced_low_signal` | 0.50 | ignore | 0 | 0 | 0 | Acceptable live limitation; low-signal content did not promote. |

## Evaluation Findings

Residue:

- `urgent_with_chatter` promoted the durable operational fact:
  `Container MEDU7711009 missed its designated customs hold release window...`
- The assistant confirmation facts were marked review-only with
  `assistant_action_residue=true` and `conversational_residue=true`.
- `assistant_acknowledgement_noise` did not promote any residue.

Speculative/inferred:

- `assistant_inferred` produced review-only evidence, including one row with
  `speculative_claim=true`.
- The single promoted `assistant_inferred` fact was a durable clarification:
  air freight was not mandatory, only a potential option.
- `speculative_claim` scored just below threshold (`0.57 < 0.6`) and did not
  reach extraction, so this run is inconclusive for preferred live speculative
  review-only extraction.

Recency/access:

- `access_reinforced_low_signal` scored below threshold and did not extract or
  promote any facts.
- No `recency_access_guardrail=true` row appeared. This is expected for the
  current live path because the live `FactExtractor` does not populate
  `access_count`, so `recency_boost` remains `1.0` for extracted live facts.

Operational notes:

- The run was classified as `policy_evidence`.
- Console output included one LLM JSON parse fallback warning and one segmenter
  fallback warning, but scenario errors were zero, required artifacts were
  complete, provider fallback was not detected, and the manifest classified the
  run as clean policy evidence.

## Acceptance Assessment

Accepted with caveats:

- Operational gate: passed.
- Positive controls: passed.
- Residue behavior: passed.
- Speculative/inferred behavior: acceptable partial evidence. No speculative or
  inferred content was promoted, but `speculative_claim` did not reach
  extraction.
- Recency/access behavior: acceptable limitation. Low-signal content did not
  promote, but full guardrail evidence requires future live `access_count`
  observability.

## Recommendation

Continue CIAR work. The live checkpoint does not reveal a policy blocker for
Batches 4-6.

Recommended follow-ups:

- If we need stronger live speculative evidence, run a small prompt robustness
  follow-up for `speculative_claim` so it crosses the segment gate and reaches
  extraction without weakening policy thresholds.
- If we need full live recency/access evidence, plan a separate observability
  batch to pass explicit access metadata into live facts or add a harness-only
  access-count injection path for experiments.
