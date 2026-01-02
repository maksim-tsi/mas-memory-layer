# Phase 5 Readiness Checklists (Graded)

**Date:** 2026-01-02  
**Purpose:** Provide a structured, graded readiness framework for Phase 5, aligned to the four-tier cognitive memory architecture and lifecycle engines. Grades: Green (meets bar), Amber (minor gaps), Red (blocking gaps). Each item lists required evidence and project-specific improvement guidance.

## 2026-01-03 Status Update
- See daily report [docs/reports/lifecycle-status-2026-01-03.md](../reports/lifecycle-status-2026-01-03.md) and log entry in [DEVLOG.md](../../DEVLOG.md).
- Current gap: end-to-end lifecycle test still fails due to zero L4 knowledge documents; distillation now forces processing with rule-based fallback but episode retrieval remains sparse in integration flow.
- Next action: verify episodic retrieval and Typesense writes during distillation, then rerun full lifecycle test and update grading outcomes.

## 1. Architecture & ADR Alignment
- **Tier responsibilities and flow (L1–L4)** — Evidence: [docs/ADR/003-four-layers-memory.md](../ADR/003-four-layers-memory.md), [AGENTS.MD](../../AGENTS.MD), [docs/reports/adr-003-architecture-review.md](../reports/adr-003-architecture-review.md). Improvement: ensure diagrams and text reflect current engine code paths and dual-index commitments.
- **CIAR policy compliance** — Evidence: [docs/ADR/004-ciar-scoring-formula.md](../ADR/004-ciar-scoring-formula.md), [config/ciar_config.yaml](../../config/ciar_config.yaml), [src/memory/ciar_scorer.py](../../src/memory/ciar_scorer.py). Improvement: verify decay/recency parameters match ADR defaults per domain; record rationale in config comments.
- **Lifecycle engines coverage (promotion → consolidation → distillation)** — Evidence: [src/memory/engines/promotion_engine.py](../../src/memory/engines/promotion_engine.py), [src/memory/engines/consolidation_engine.py](../../src/memory/engines/consolidation_engine.py), [src/memory/engines/distillation_engine.py](../../src/memory/engines/distillation_engine.py), [docs/reports/adr-003-architecture-review.md](../reports/adr-003-architecture-review.md). Improvement: document retry/circuit-breaker thresholds and ensure tests exercise degradation paths.
- **Dual-index guarantees (L3 Qdrant + Neo4j; L4 Typesense)** — Evidence: [src/memory/tiers/episodic_memory_tier.py](../../src/memory/tiers/episodic_memory_tier.py), [src/memory/tiers/semantic_memory_tier.py](../../src/memory/tiers/semantic_memory_tier.py). Improvement: specify divergence detection and repair runbooks; add idempotent write checks.
- **Operating vs persistent layer boundaries** — Evidence: [src/memory/tiers/active_context_tier.py](../../src/memory/tiers/active_context_tier.py), [src/memory/tiers/working_memory_tier.py](../../src/memory/tiers/working_memory_tier.py). Improvement: confirm hot-path TTL/windowing constraints (10–20 turns, 24h TTL) are enforced and logged.

## 2. Implementation Depth
- **Tier behavior completeness** — Evidence: [src/memory/tiers/base_tier.py](../../src/memory/tiers/base_tier.py) plus concrete tiers above. Improvement: add edge-case handling (empty windows, backpressure) and metrics per method entry/exit.
- **Data contracts (Fact, Episode, KnowledgeDocument)** — Evidence: [src/memory/models.py](../../src/memory/models.py). Improvement: validate provenance fields persist across L2→L4; align required/optional fields with engine assumptions.
- **LLM orchestration and fallbacks** — Evidence: [src/utils/llm_client.py](../../src/utils/llm_client.py), [docs/LLM_PROVIDER_TESTS.md](../LLM_PROVIDER_TESTS.md), [docs/LLM_PROVIDER_TEST_RESULTS.md](../LLM_PROVIDER_TEST_RESULTS.md). Improvement: document routing by task (segmentation vs summarization vs scoring) and ensure GOOGLE_API_KEY usage is uniform.
- **Storage adapters and metrics** — Evidence: [src/storage/](../../src/storage), [docs/metrics_usage.md](../metrics_usage.md). Improvement: confirm metrics on errors/timeouts; document reconnection/backoff policies and pools per backend.

## 3. Testing Realism & Coverage
- **Unit vs integration breadth** — Evidence: [tests/memory/](../../tests/memory), [tests/storage/](../../tests/storage), [tests/utils/](../../tests/utils), [tests/integration/](../../tests/integration). Improvement: map each lifecycle path to at least one integration test; add failure-injection (backend unavailable, partial index writes).
- **Mocks vs real backends** — Evidence: skip markers in integration and LLM tests, [tests/integration/test_llmclient_real.py](../../tests/integration/test_llmclient_real.py), [tests/utils/test_gemini_structured_output.py](../../tests/utils/test_gemini_structured_output.py). Improvement: prioritize real-backend runs for critical paths under feature flags; retain mocks only for isolation.
- **Coverage posture** — Evidence: [htmlcov/status.json](../../htmlcov/status.json), [docs/LLM_PROVIDER_TEST_RESULTS.md](../LLM_PROVIDER_TEST_RESULTS.md). Improvement: raise coverage on lifecycle error branches, divergence repair, and retry/circuit-breaker logic.
- **Acceptance and performance tests** — Evidence: [benchmarks/README.md](../../benchmarks/README.md), [benchmarks/configs/](../../benchmarks/configs). Improvement: ensure latency gate (<2s p95 lifecycle) is enforced in automated checks with real backends.

## 4. Performance & Benchmarking
- **Latency/throughput SLAs** — Evidence: [docs/reports/adr-003-architecture-review.md](../reports/adr-003-architecture-review.md), [docs/metrics_usage.md](../metrics_usage.md). Improvement: run lifecycle benchmarks on Redis/Postgres/Qdrant/Neo4j/Typesense; capture p95/p99 plus queue depth.
- **Resource and configuration tuning** — Evidence: pooling/batching in [src/storage/](../../src/storage) and configs in [config/](../../config). Improvement: document recommended pool sizes, batch sizes, and load-shedding/backpressure behavior; add tests to validate defaults.
- **GoodAI LTM benchmark readiness** — Evidence: [docs/uc-01.md](../uc-01.md), [docs/research/](../research). Improvement: prepare reproducible scripts and baselines (standard RAG vs full-context) with fixed seeds and logging.

## 5. Documentation & Status Integrity
- **Status currency** — Evidence: [DEVLOG.md](../../DEVLOG.md), [docs/plan/](.), [docs/reports/adr-003-architecture-review.md](../reports/adr-003-architecture-review.md). Improvement: reconcile any “engines missing” statements with current code; record Phase 4 closure and pending gates.
- **Operational runbooks** — Evidence: [docs/environment-guide.md](../environment-guide.md), [docs/metrics_usage.md](../metrics_usage.md). Improvement: add runbooks for lifecycle failures, divergence repair, and LLM provider fallback behavior.
- **Config-to-ADR alignment** — Evidence: [config/ciar_config.yaml](../../config/ciar_config.yaml), [docs/ADR/004-ciar-scoring-formula.md](../ADR/004-ciar-scoring-formula.md). Improvement: include domain-specific CIAR overrides and rationale.
- **Risk register and lessons** — Evidence: [docs/lessons-learned.md](../lessons-learned.md). Improvement: log Phase 4 incidents (if any) with mitigations and links to code changes.

## 6. Governance & Safety
- **Error handling and circuit breakers** — Evidence: engine implementations and adapter error paths in [src/memory/engines/](../../src/memory/engines) and [src/storage/](../../src/storage). Improvement: confirm thresholds and retry budgets are implemented, documented, and covered by tests.
- **Provenance and auditability** — Evidence: lineage fields in [src/memory/models.py](../../src/memory/models.py) and writes in engine code. Improvement: add tests ensuring provenance survives L2→L4 promotions and reconciliations.
- **Data retention and TTLs** — Evidence: L1/L2 tier logic and configs. Improvement: validate TTL enforcement and retention policies match ADR and compliance notes; ensure metrics expose TTL expirations.

## Usage Guidance
- Assign Green/Amber/Red per item with a short note and link to evidence above. 
- For Amber/Red, add a one-line, project-specific improvement (e.g., “Run promotion→consolidation E2E against Redis/Postgres/Qdrant/Neo4j/Typesense and record p95 in metrics export”).
- Keep grading results in this document until we formalize a dedicated tracker; update after each validation cycle.

## Grading Automation Approach (Planned)
- **Script location:** Place readiness graders under `scripts/` (e.g., `scripts/grade_phase5_readiness.sh` plus optional `scripts/grade_phase5_readiness.py`). Document outputs into [docs/reports/phase5-readiness.md](../reports/phase5-readiness.md).
- **Interpreter choice:** On the managed host, scripts must call `/home/max/code/mas-memory-layer/.venv/bin/python` and `/home/max/code/mas-memory-layer/.venv/bin/pytest` directly (no activation). For portability, allow fallback to `./.venv/bin/python`/`./.venv/bin/pytest` when the absolute path is unavailable.
- **Environment loading:** Users run scripts in a shell that already exports variables from `.env`; the repo must not read or commit `.env`. In bash wrappers, note the pattern `set -a; source .env; set +a` is to be executed by users, not baked into committed code. Scripts should verify required variables (e.g., `GOOGLE_API_KEY`, backend connection settings) before running real-provider or real-backend checks.
- **Real vs mock runs:** Keep fast path (lint + unit/mocked tests) and real path (integration with Redis/Postgres/Qdrant/Neo4j/Typesense and real LLM providers). Gate real paths on env presence and skip markers; report clearly whether real backends were exercised.
- **Outputs:** Emit structured summaries (e.g., JSON or concise text) with status of lint, unit, integration, coverage (from `htmlcov/status.json`), and optional benchmarks (p95/p99). These outputs feed grading in [docs/reports/phase5-readiness.md](../reports/phase5-readiness.md).
- **Example invocations:**
	- Fast path: `./scripts/grade_phase5_readiness.sh --mode fast`
	- Full path with summary file: `./scripts/grade_phase5_readiness.sh --mode full --summary-out /tmp/phase5-readiness.json`
	- To skip real LLM/provider checks even if `GOOGLE_API_KEY` is set: add `--skip-llm`