# V2 API E2E Semantic Gateway Test Plan

## Modules Under Test
- `src.api.v2_router`: Ensure accurate routing, request/response validation, and HTTP code fidelity.
- `src.api.v2_schemas`: Validation of all newly crafted Pydantic models carrying `session_id` and strict `metadata` trace structures.
- `src.llm.client`: Execution of the Internal Pipeline (text generation for Cypher translation and vectors for Qdrant).
- `src.memory.unified_memory_system`: Bridging between API intercepts and backend tier logic.

## Model Configuration
Since we are evaluating the semantic capabilities against live external tools, the test suite assumes:
- **LLM for Cypher/Entity Extraction:** Routed through OpenRouter using `tencent/hy3-preview` for semantic reasoning and Cypher translation.
- **Embedding Model:** Uses `llm_client.get_embedding()` via OpenRouter with `qwen/qwen3-embedding-8b`, configured for empirically verified 4096-dimensional vectors.
- **Project Namespace:** Uses `YAAM_PROJECT_ID=test` by default, deriving L3 Qdrant collection `yaam-test-episodes` and L4 Typesense collection `yaam-test`.
- **Credential Requirement:** External model calls require `OPENROUTER_API_KEY` in the environment.

## The Flow
The End-to-End Suite executes a synchronous step-through logic across the layers:
1. **Scenario Readiness:** The Pytest setup reads realistic SCM .md texts.
2. **L3 Assimilate (`POST /v2/memory/l3/assimilate`):** 
   - Post an SCM scenario (e.g., Strike alert).
   - Verify `get_embedding` generation and DB write. We intercept 502s dynamically and skip assertions gracefully if local API keys limit external generation.
3. **L3 Query (`POST /v2/memory/l3/query`):**
   - Transmit a question related to the ingested texts (e.g., "How does the strike affect lead times?").
   - Wait for Cypher representation via `llm_client.generate()`.
   - Assert `200 OK` and inspect `provenance.session_id`.
4. **L4 Finalize (`POST /v2/memory/l4/finalize`):**
   - Post a final `.md` report resolving a supply chain problem (Risk Pooling).
   - Validate creation and payload structures in Typesense backend mappings.
