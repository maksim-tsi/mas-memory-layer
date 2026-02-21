# Plan: Execute Agent Variant Benchmarking (Skills Wiring v1 → v2)

**Status:** Draft  
**Date:** February 21, 2026  
**Related:** ADR-009, ADR-010, ADR-011; `docs/specs/spec-goodai-agent-variant-evaluation-protocol.md`

## Progress Update (2026-02-21)

Closed pre-benchmark correctness gaps for ADR-011 operational readiness:

- API Wall `/health` now reports `agent_type` and `agent_variant` in addition to subsystem health.
- API Wall startup examples now use `uvicorn src.server:app` with explicit variant-specific ports.
- Variant A policy wiring is now started in `MemoryAgent`: per-turn `skill_slug` selection,
  skill-body system instruction injection, and `allowed-tools` preparation metadata.

## 1. Objective

Establish a research-grade, reproducible process to evaluate YAAM agent variants on the GoodAI LTM
Benchmark, starting with minimal skills wiring and progressing to an advanced, tool-gated approach.

## 2. Experimental Design

### 2.1 Variants

- **Variant A (v1 minimal):** skill body injection + toolset gating preparation; no router.
- **Variant B (v2 advanced):** hard tool gating + real tool calling via `allowed-tools`; no router
  unless explicitly studied as Variant C.

### 2.2 Controlled Variables (Fixed Across Variants)

- Benchmark version/commit and manifest.
- Provider/model (including temperature and max output tokens).
- Backing services and endpoints (Redis/Postgres and other DBMS as required).
- Rate limiter configuration (RPM/TPM and delay).
- Run counts and random seeds (where applicable).

### 2.3 Measured Outcomes

- Benchmark score(s) (GoodAI reported).
- Per-turn latency and token estimates (API Wall metadata).
- Error taxonomy: retrieval failures vs reasoning failures vs tool misuse.
- Cost proxies: prompt/response token estimates; provider request counts.

## 3. Execution Phases

### Phase 0 — Infrastructure and Validation

Exit criteria:

- Network-enabled host can run integration tests and provider smoke tests.
- API Wall `/health` returns `agent_type` and `agent_variant`.
- Session prefixes are isolated across variants.

Operator notes:

- Use one service instance per `(agent_type, agent_variant)` tuple.
- Use distinct ports per variant; the benchmark runner selects the variant by setting `AGENT_URL`.

### Phase 1 — Variant A: Minimal Skills Wiring

Tasks:

1. Implement a minimal skills wiring agent variant (V1) with:
   - per-turn `skill_slug` selection,
   - skill body injected into `system_instruction`,
   - toolset gating prepared from `allowed-tools` and recorded in metadata.
2. Run a benchmark smoke test on a reduced manifest.
3. Run full benchmark N times (recommended: N≥5) and publish a report.

Exit criteria:

- Reports contain all fields in the report template.
- Runs are repeatable within acceptable variance.

### Phase 2 — Variant B: Advanced Tool-Gated Skills

Tasks:

1. Implement a tool-gated skills execution variant (V2) with:
   - hard enforcement of `allowed-tools` at runtime tool execution,
   - real tool calling (DBMS adapters via tools) and LLM calls as required,
   - failure-mode guardrails consistent with the skills inventory.
2. Run the same benchmark manifest N times.
3. Publish a comparative report A vs B.

Exit criteria:

- A vs B comparison includes score deltas, error taxonomy deltas, and latency/token deltas.

## 3.1 Concrete Entrypoints (Operational)

### A) Start two API Wall instances (example)

```bash
# Variant A
MAS_PORT=8081 MAS_AGENT_TYPE=full MAS_AGENT_VARIANT=v1-min-skillwiring \
  ./.venv/bin/uvicorn src.server:app --host 0.0.0.0 --port 8081

# Variant B
MAS_PORT=8082 MAS_AGENT_TYPE=full MAS_AGENT_VARIANT=v2-adv-toolgated \
  ./.venv/bin/uvicorn src.server:app --host 0.0.0.0 --port 8082
```

### B) Run GoodAI against each instance (example)

```bash
cd benchmarks/goodai-ltm-benchmark

AGENT_URL="http://localhost:8081/v1/chat/completions" \
  poetry run python -m runner.run_benchmark \
    -c configurations/mas_remote_test.yml \
    -a mas-remote \
    --run-name "goodai__full__v1-min-skillwiring"

AGENT_URL="http://localhost:8082/v1/chat/completions" \
  poetry run python -m runner.run_benchmark \
    -c configurations/mas_remote_test.yml \
    -a mas-remote \
    --run-name "goodai__full__v2-adv-toolgated"
```

Optional helper script:

```bash
./scripts/run_goodai_remote_variant.sh \
  --agent-url "http://localhost:8081/v1/chat/completions" \
  --agent-type full \
  --agent-variant v1-min-skillwiring \
  --config configurations/mas_remote_test.yml
```

## 4. Artifacts

- Reports: `docs/reports/<YYYY-MM-DD>_goodai_variant_report_<agent_type>__<agent_variant>.md`
- Raw benchmark outputs: stored under a run directory referenced from the report.
- Wrapper logs and rate limiter JSONL files referenced from the report.

## 5. Risk Controls

- Enforce rate limits (<10 provider requests/minute unless explicitly approved).
- Use variant-qualified session prefixes to prevent cross-contamination.
- Treat benchmark as feedback-only; avoid embedding benchmark prompts into skills.
