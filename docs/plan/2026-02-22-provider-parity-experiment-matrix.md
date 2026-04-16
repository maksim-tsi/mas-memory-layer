# Experiment Matrix: Provider Parity (Groq/Gemini/Mistral) Under API Wall

**Status:** Draft  
**Date:** February 22, 2026  
**Audience:** Maintainers, benchmark operators  
**Related:** `docs/plan/2026-02-22-fast-llm-memory-barrier-provider-parity-plan.md`, `docs/specs/spec-goodai-agent-variant-evaluation-protocol.md`

## 1. Purpose

This document operationalizes provider parity requirements into a concrete experiment matrix and a run-name convention. The objective is to ensure that Groq, Gemini, and Mistral are evaluated under maximally comparable conditions and that any policy-layer changes introduced for one provider are replicated for all providers.

## 2. Invariants (Normative)

For all runs in this matrix, unless explicitly declared as an experimental factor:

- identical benchmark configuration file(s),
- identical agent type and agent variant,
- identical `MAS_WRAPPER_TIMEOUT`,
- identical rate limiter configuration,
- and identical promotion execution semantics (`MAS_PROMOTION_MODE`) when promotion is enabled.

All deviations MUST be recorded in the per-run report.

## 3. Run-Name Convention (Normative)

The GoodAI runner MUST be invoked with a unique `--run-name` containing:

1. experiment id (human-readable),
2. provider id (`groq|gemini|mistral`),
3. model id,
4. promotion mode (`disabled|async|barrier`),
5. agent identity (`<agent_type>__<agent_variant>`),
6. timestamp.

Canonical format:

```
goodai__smoke5__provider=<provider>__model=<model>__promotion=<mode>__agent=full__v1-min-skillwiring__<YYYYMMDD_HHMMSS>
```

## 4. Experiment Matrix

### 4.1 API Wall benchmark runs (Smoke5)

These runs use `POST /v1/chat/completions` and therefore reflect ADR-009 semantics. Note: the API Wall currently defaults to `skip_l1_write=true`, which suppresses promotion. Consequently, `promotion_mode` is recorded for completeness but is not expected to change behavior unless write policy is explicitly modified in a future controlled experiment.

| Provider | `MAS_MODEL` | `MAS_PROMOTION_MODE` | `--run-name` (pattern) | Endpoint |
|---|---|---|---|---|
| Groq | `openai/gpt-oss-120b` | `disabled` | `goodai__smoke5__provider=groq__model=openai-gpt-oss-120b__promotion=disabled__agent=full__v1-min-skillwiring__<ts>` | `/v1/chat/completions` |
| Gemini | `gemini-3-flash-preview` | `disabled` | `goodai__smoke5__provider=gemini__model=gemini-3-flash-preview__promotion=disabled__agent=full__v1-min-skillwiring__<ts>` | `/v1/chat/completions` |
| Mistral | `mistral-large` | `disabled` | `goodai__smoke5__provider=mistral__model=mistral-large__promotion=disabled__agent=full__v1-min-skillwiring__<ts>` | `/v1/chat/completions` |

### 4.2 Memory-engine validation runs (promotion enabled)

These runs are not GoodAI benchmark runs. They are required to validate FactExtractor/TopicSegmenter behavior and timing under provider parity constraints. They SHOULD use the internal wrapper endpoint `POST /run_turn`, because it allows explicit per-request metadata control (e.g., `skip_l1_write=false`) while preserving the same agent implementation.

| Provider | Agent `MAS_MODEL` | Engine models | `MAS_PROMOTION_MODE` | Session plan | Endpoint |
|---|---|---|---|---|---|
| Groq | `openai/gpt-oss-120b` | `MAS_FACT_EXTRACTOR_MODEL` and `MAS_TOPIC_SEGMENTER_MODEL` default to `MAS_MODEL` | `async` then `barrier` | fixed scripted conversation (≥ minimum turns), then a retrieval query turn | `/run_turn` |
| Gemini | `gemini-3-flash-preview` | same | `async` then `barrier` | same script | `/run_turn` |
| Mistral | `mistral-large` | same | `async` then `barrier` | same script | `/run_turn` |

If any engine must use a different provider/model (e.g., structured output compatibility), this MUST be treated as a distinct experimental factor and replicated across providers.

## 5. Documentation Requirements (Per Run)

Every run MUST record:

- YAAM git commit hash,
- benchmark git commit hash (or pinned version),
- provider/model used for each turn (artifact-level),
- timing decomposition (artifact-level),
- session identity (`client_session_id` and prefixed YAAM session id),
- and the exact `--run-name`.

Each run MUST produce a report in `docs/reports/` using:

- `docs/reports/template-goodai-agent-variant-report-groq.md` (for Groq), or
- `docs/reports/template-goodai-agent-variant-report.md` (for non-Groq), with parity fields added explicitly.

