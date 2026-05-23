# CIAR Residue Tightening Plan

Date: 2026-05-23

## Purpose

Batch 4 tightens CIAR conversational-residue handling so `hybrid_gate` keeps
assistant acknowledgements, assistant commitments, and low-value chatter out of
stored L2 policy evidence while preserving real operational facts extracted from
the same segments.

## Scope

This batch may change the promotion evidence ranker, CIAR experiment harness,
CIAR policy analyzer, focused tests, and CIAR coordination documentation. It
must not change CIAR scoring formula, thresholds, promotion-mode defaults,
contradiction policy, storage adapters, DB schemas, provider routing,
dependencies, or `.env` behavior.

## Implementation Plan

- Extend `EvidenceRanker` to classify assistant-action facts such as
  "assistant confirmed", "assistant will record", and "I will check" as
  conversational residue under `hybrid_gate`.
- Preserve store eligibility for durable operational facts about shipment
  routes, ETA, port, customs, delivery, temperature, and warehouse state.
- Add residue subtype provenance, while keeping `conversational_residue` as the
  aggregate flag.
- Add deterministic canned facts for `assistant_acknowledgement_noise` and
  `urgent_with_chatter`.
- Extend CIAR policy analysis with backward-compatible `residue_evaluation`
  JSON and markdown sections.
- Update the CIAR coordination plan with `CIAR-RES-1` after local verification.

## Acceptance Criteria

- `small_talk` and `assistant_acknowledgement_noise` promote zero facts in the
  focused dry matrix.
- `segment_mismatch` and `urgent_with_chatter` promote operational facts while
  assistant/chatter residue is review-only.
- `hybrid_gate` stores durable operational state rather than conversational acts
  about recording, acknowledging, or checking that state.
- `fact_gate` and `segment_gate` behavior remains unchanged except for
  diagnostic provenance flags.
- Targeted tests, CIAR regression pack, and the full test suite pass.

## Verification Commands

```bash
uname -a
hostname
pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/memory/engines/test_promotion_engine.py tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_policy_analysis.py -v
./.venv/bin/python scripts/experiments/run_ciar_challenge.py \
  --dry-run \
  --run-id ciar-exp-dry-residue-tightening-20260523-01 \
  --promotion-policy-mode hybrid_gate \
  --contradiction-policy-mode off \
  --scenario-id small_talk \
  --scenario-id segment_mismatch \
  --scenario-id assistant_acknowledgement_noise \
  --scenario-id urgent_with_chatter
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
./.venv/bin/pytest tests/ -v
```

## Assumptions

- This batch is dry-first; live validation can follow Batches 4-6.
- If live extraction emits only an assistant-action fact without the durable
  operational fact, the assistant-action fact should still be review-only.
- Because this batch touches `src/`, the full test suite is required.
