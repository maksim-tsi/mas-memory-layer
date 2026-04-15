# YAAM API v2 (Memory Gateway) - 8-Hour Feasibility Report

**Date:** April 15, 2026  
**Subject:** Feasibility of exposing explicit CRUD operations for L1-L4 within an 8-hour window  

## 1. Feasibility Verdict
**Verdict: YES, Highly Feasible.**
It is entirely feasible to expose the v2 Memory Gateway within a strict 8-hour working window. The core underlying structure of the YAAM codebase cleanly decouples the storage operations from its own cognitive extraction/consolidation layers. 

## 2. Current State & Black Box Analysis

### Codebase Sizing & Entanglement
- The codebase is relatively small and very cleanly structured. The `src/` directory contains roughly ~22,000 lines of code across all files, making it highly navigable.
- The `goodai-ltm-benchmark` is entirely isolated in the `benchmarks/` directory and `.venv-benchmark/` environment. A search within `src/` reveals zero entanglement with the core memory logic or tier engines.

### API Framework & Routing
- YAAM utilizes **FastAPI** (`src/server.py`). The application initialization cleanly drops routes onto the `app` instance using the `@app.post` decorators.
- Injecting new routes for a "v2" API (e.g., `POST /v2/memory/l3/entities` or `GET /v2/memory/l2/facts`) alongside the existing OpenAI-compatible endpoints will be straightforward. New routes only require accessing the initialized state via `request.app.state.wrapper`.

### Facade Decoupling & "Black Box" Analysis
The critical requirement is that the new v2 API can force YAAM to act as a **"dumb" data store**.

- **CRUD Operations**: Are explicit CRUD operations already implemented? **Yes**. The `unified_memory_system.py` serves as a facade to individual tiers (`WorkingMemoryTier`, `EpisodicMemoryTier`, `SemanticMemoryTier`). Each of these tier classes natively implements explicit `store()`, `retrieve()`, `delete()`, and `query()` operations (inheriting from `BaseTier`).
- **Cognitive Logic Bypass**: Does saving a record automatically trigger internal LLM calls? **No, not at the Tier level.** 
  - YAAM does possess cognitive processing logic, but this logic is orchestrated explicitly via `run_promotion_cycle()`, `run_consolidation_cycle()`, and `run_distillation_cycle()` inside the `unified_memory_system.py`. 
  - The tier-level `store()` methods (e.g., `l3_tier.store()`) *do not* self-trigger cognitive logic. They purely execute native database operations against Redis, Postgres, Neo4j, Qdrant, and Typesense. 
  - Even L3 ingestion (`EpisodicMemoryTier.store(...)`) expects the vector embedding to be provided in the `EpisodeStoreInput` payload, proving it does not enforce LLM embedding generation on write.
- **Conclusion**: By having the new FastAPI routes directly call the individual tier methods (`app.state.wrapper.l2_tier.store()`), we completely bypass the internal LLM cycles. **YAAM can successfully function as a 100% bypassed, dumb substrate.**

## 3. 8-Hour Execution Plan

Given the clean separation of concerns, the implementation of the "YAAM API v2" can be executed promptly using the following step-by-step plan:

**Hour 1-2: Pydantic Schema Definition**
- Create a new module e.g., `src/api/v2_schemas.py`.
- Define standardized REST payload schemas (`FactCreateRequest`, `EpisodeCreateRequest`, `KnowledgeCreateRequest`). Because the `tiers` module uses data classes like `Fact` and `EpisodeStoreInput`, the v2 schema simply needs to map properties downstream.

**Hour 3-5: Router Implementation & Integration (server.py)**
- Define FastAPI routers for `v2/memory/l2`, `v2/memory/l3`, and `v2/memory/l4`.
- For L2 (Postgres), map explicit `GET / POST / DELETE` endpoints to `app.state.wrapper.memory_system.l2_tier`.
- For L3 (Qdrant/Neo4j), map endpoints to `l3_tier.store` (taking care to require the orchestrator TRA to pass embeddings).
- For L4 (Typesense), map to `l4_tier.store()`.
- Register the routers inside the `create_app()` factory in `src/server.py`.

**Hour 6-7: Testing & Black Box Verification**
- Expose via `npm run dev` or pytest equivalent (`pytest tests/`).
- Using a mock external orchestrator script, hit the new v2 endpoints to write data.
- Assert that writing data using v2 APIs does not invoke the `LLMClient` or `handle_external_episode()` background task. Verify writes exist natively in postgres/Qdrant.

**Hour 8: Documentation & Handoff**
- Update OpenAPI/Swagger configurations for the v2 tags.
- Finalize the pull request and verify that the 8-hour constraint was met.
