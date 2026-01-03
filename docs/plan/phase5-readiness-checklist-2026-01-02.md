# Phase 5 Readiness Checklists (Graded)

**Date:** 2026-01-02  
**Purpose:** Provide a structured, graded readiness framework for Phase 5, aligned to the four-tier cognitive memory architecture and lifecycle engines. Grades: Green (meets bar), Amber (minor gaps), Red (blocking gaps). Each item lists required evidence and project-specific improvement guidance.

## 2026-01-03 Final Status - Phase 4 Complete ✅

**🟢 FULL TEST SUITE PASSING: 574/586 (0 failed)**

All Phase 4 integration hardening complete. Test suite fully green, all lifecycle paths verified.

### Test Results Summary (2026-01-03)
```bash
================== 574 passed, 12 skipped, 0 failed in 131.29s ==================

Integration Tests (4/4):
✅ test_l1_to_l2_promotion_with_ciar_filtering
✅ test_l2_to_l3_consolidation_with_episode_clustering (FIXED)
✅ test_l3_to_l4_distillation_with_knowledge_synthesis
✅ test_full_lifecycle_end_to_end

Storage Adapters (199/199):
✅ Redis: 32/32 | PostgreSQL: 24/24 | Qdrant: 46/46 | Neo4j: 53/53 | Typesense: 44/44

Memory Tiers (61/61):
✅ L1: 17/17 | L2: 12/12 | L3: 16/16 | L4: 16/16

Lifecycle Engines (59/59):
✅ Promotion: 10/10 | Consolidation: 9/9 | Distillation: 12/12
✅ FactExtractor: 4/4 | TopicSegmenter: 10/10 | KnowledgeSynthesizer: 14/14

Agent Tools (60/60):
✅ CIAR Tools: 16/16 | Tier Tools: 18/18 | Unified Tools: 26/26
```

### Critical Fix: Qdrant Scroll vs Search
- **Problem:** Test stored episodes successfully but failed to retrieve them with `search()` + filter
- **Root Cause:** Qdrant `search()` is vector-similarity-first; dummy query vector `[0.1]*768` had ~0 similarity to real embeddings, causing filter-based queries to return nothing
- **Solution:** Added `scroll()` method to `QdrantAdapter` for pure filter-based retrieval; updated test to use `scroll()` instead of `search()`
- **Full Report:** [docs/reports/qdrant-scroll-vs-search-debugging-2026-01-03.md](../reports/qdrant-scroll-vs-search-debugging-2026-01-03.md)

### Key Implementation Changes
| File | Change |
|------|--------|
| `src/storage/qdrant_adapter.py` | Added `scroll()` method for filter-only retrieval (76 lines) |
| `tests/integration/test_memory_lifecycle.py` | Changed Qdrant verification from `search()` to `scroll()` |
| `tests/storage/test_qdrant_adapter.py` | Updated backward compatibility test for session_id filter behavior |

### Design Guideline Established
- Use `search()` for semantic similarity queries ("find items similar to X")
- Use `scroll()` for metadata-based queries ("find all items matching session_id=Y")

---

## 2026-01-03 Status Update (Session 1)
- See daily report [docs/reports/lifecycle-status-2026-01-03.md](../reports/lifecycle-status-2026-01-03.md) and log entry in [DEVLOG.md](../../DEVLOG.md).
- ~~Current gap: end-to-end lifecycle test still fails due to zero L4 knowledge documents; distillation now forces processing with rule-based fallback but episode retrieval remains sparse in integration flow.~~
- ~~Next action: verify episodic retrieval and Typesense writes during distillation, then rerun full lifecycle test and update grading outcomes.~~
- **UPDATE:** All core lifecycle tests now pass. See Session 2 update above.

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

---

## 2026-01-03 Implementation Session: Data Starvation Cascade Fix

### Root Cause Analysis

The `test_full_lifecycle_end_to_end` test fails due to a **data starvation cascade**:
1. Too few facts flow from L1→L2 (semantic weakness in test data)
2. Results in thin L3 episodes 
3. Produces zero L4 knowledge documents

Contributing factors identified:
- **Vector dimension mismatch**: QdrantAdapter defaults to 384, EpisodicMemoryTier expects 768, Gemini outputs 3072 by default
- **Low query limits**: `query_by_session()` defaults to 10 results (truncates during consolidation)
- **Weak test content**: Generic "Container arrived" messages don't trigger meaningful LLM fact extraction

### Completed Fixes (2026-01-03)

| Fix | File | Change |
|-----|------|--------|
| ✅ Vector dimension to 768 | `src/utils/providers.py` | Added `output_dimensionality=768` to `GeminiProvider.get_embedding()` |
| ✅ Fallback embedding aligned | `src/memory/engines/consolidation_engine.py` | Changed fallback from 1536 to 768 dims |
| ✅ L2 query limits increased | `src/memory/tiers/working_memory_tier.py` | `query_by_session()` and `query_by_type()` default limit: 10→100 |
| ✅ Rich test data | `tests/integration/test_memory_lifecycle.py` | New `SUPPLY_CHAIN_CONVERSATION_TEMPLATES` with realistic scenarios |
| ✅ Distillation logging | `src/memory/engines/distillation_engine.py` | Added INFO log in `_retrieve_episodes()` (pre/post filter counts) |
| ✅ L4 store confirmation | `src/memory/tiers/semantic_memory_tier.py` | Added INFO log confirming Typesense write with `knowledge_id` |

### Pending: Arize Phoenix Integration

#### Overview
Phoenix provides LLM call tracing for debugging embeddings, latencies, and token usage. Already deployed on `skz-dev-lv:6006`.

#### Environment Configuration

Add to `.env`:
```bash
# --- Arize Phoenix (LLM Observability) ---
PHOENIX_PORT=6006
PHOENIX_GRPC_PORT=4317
PHOENIX_COLLECTOR_ENDPOINT=http://${DEV_NODE_IP}:${PHOENIX_PORT}/v1/traces
PHOENIX_PROJECT_NAME=mlm-mas-dev
PHOENIX_URL=http://${DEV_NODE_IP}:${PHOENIX_PORT}
```

#### Project Naming Convention
| Environment | Project Name |
|-------------|--------------|
| Development | `mlm-mas-dev` |
| Testing | `mlm-mas-test` |
| Production | `mlm-mas-prod` |

#### Dependencies to Add (requirements.txt)
```txt
# --- Observability & Tracing (Arize Phoenix) ---
arize-phoenix>=4.0.0                              # Phoenix observability SDK
openinference-instrumentation-google-genai>=0.1.0 # Auto-instrumentation for Google GenAI
opentelemetry-exporter-otlp>=1.20.0               # OTLP exporter (HTTP/gRPC)
```

#### Connectivity Check Script

Create `scripts/check_phoenix_connectivity.sh`:
```bash
#!/usr/bin/env bash
# Verify Arize Phoenix connectivity
set -euo pipefail

PHOENIX_HOST="${DEV_NODE_IP:-192.168.107.172}"
PHOENIX_HTTP_PORT="${PHOENIX_PORT:-6006}"
PHOENIX_GRPC_PORT="${PHOENIX_GRPC_PORT:-4317}"

echo "=== Arize Phoenix Connectivity Check ==="
echo "Host: ${PHOENIX_HOST}"

# Check HTTP endpoint (UI + OTLP HTTP collector)
echo -n "HTTP (port ${PHOENIX_HTTP_PORT}): "
if curl -sf "http://${PHOENIX_HOST}:${PHOENIX_HTTP_PORT}" -o /dev/null 2>/dev/null; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Check gRPC endpoint
echo -n "gRPC (port ${PHOENIX_GRPC_PORT}): "
if nc -z "${PHOENIX_HOST}" "${PHOENIX_GRPC_PORT}" 2>/dev/null; then
    echo "✅ OK"
else
    echo "⚠️  Not reachable (may not be exposed)"
fi

echo ""
echo "=== Collector Endpoints ==="
echo "OTLP HTTP: http://${PHOENIX_HOST}:${PHOENIX_HTTP_PORT}/v1/traces"
echo "OTLP gRPC: ${PHOENIX_HOST}:${PHOENIX_GRPC_PORT}"
```

#### Instrumentation Code for llm_client.py

Replace Phoenix init in `src/utils/llm_client.py`:
```python
# Phoenix configuration constants
PHOENIX_DEFAULT_PROJECT = "mlm-mas-dev"
PHOENIX_SERVICE_NAME = "mas-memory-layer"

def _init_phoenix_instrumentation() -> None:
    """Initialize Phoenix/OpenTelemetry instrumentation if configured.
    
    Environment Variables:
        PHOENIX_COLLECTOR_ENDPOINT: OTLP collector URL (e.g., http://192.168.107.172:6006/v1/traces)
        PHOENIX_PROJECT_NAME: Project name for trace grouping (default: mlm-mas-dev)
    """
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
    if not endpoint:
        logger.debug(
            "PHOENIX_COLLECTOR_ENDPOINT not set; Phoenix instrumentation disabled. "
            "Set to http://<host>:6006/v1/traces to enable."
        )
        return
    
    project_name = os.environ.get("PHOENIX_PROJECT_NAME", PHOENIX_DEFAULT_PROJECT)
    
    try:
        from phoenix.otel import register
        
        tracer_provider = register(
            project_name=project_name,
            endpoint=endpoint,
            auto_instrument=True,
        )
        
        logger.info(
            "Phoenix instrumentation enabled: project=%s, endpoint=%s",
            project_name,
            endpoint
        )
        
        # Explicitly instrument Google GenAI
        try:
            from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
            if not GoogleGenAIInstrumentor().is_instrumented_by_opentelemetry:
                GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
                logger.info("Google GenAI instrumentation enabled (explicit)")
        except ImportError:
            logger.debug("openinference-instrumentation-google-genai not installed")
        except Exception as e:
            logger.warning("Failed to instrument Google GenAI: %s", e)
        
    except ImportError:
        logger.debug("arize-phoenix not installed; run 'pip install arize-phoenix'")
    except Exception as e:
        logger.warning("Failed to initialize Phoenix instrumentation: %s", e)

# Initialize at module load (idempotent)
_init_phoenix_instrumentation()
```

### Next Steps (Priority Order)

1. **Verify Phoenix Deployment**: Run connectivity check script against `skz-dev-lv:6006`
2. **Install Dependencies**: Add Phoenix packages to requirements.txt
3. **Update .env.example**: Add Phoenix configuration variables
4. **Finalize llm_client.py**: Update instrumentation code with project naming
5. **Run Full Lifecycle Test**: Verify data starvation fixes resolve the E2E test
6. **Observe in Phoenix UI**: Confirm embedding dimensions and LLM calls are traced

### Test Commands

```bash
# Run full lifecycle test
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/integration/test_memory_lifecycle.py::TestMemoryLifecycleFlow::test_full_lifecycle_end_to_end -v > /tmp/copilot.out 2>&1; cat /tmp/copilot.out

# Run all integration tests  
/home/max/code/mas-memory-layer/.venv/bin/pytest tests/integration/ -v > /tmp/copilot.out 2>&1; cat /tmp/copilot.out

# Grade phase 5 readiness
./scripts/grade_phase5_readiness.sh --mode full > /tmp/copilot.out 2>&1; cat /tmp/copilot.out
```