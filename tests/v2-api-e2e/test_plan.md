# V2 API E2E Semantic Gateway Test Plan

## Modules Under Test
- `src.api.v2_router`: Ensure accurate routing, request/response validation, and HTTP code fidelity.
- `src.api.v2_schemas`: Validation of all newly crafted Pydantic models carrying `session_id` and strict `metadata` trace structures.
- `src.llm.client`: Execution of the Internal Pipeline (text generation for Cypher translation and vectors for Qdrant).
- `src.memory.unified_memory_system`: Bridging between API intercepts and backend tier logic.

## Model Configuration
Since we are evaluating the semantic capabilities against live external tools, the test suite assumes:
- **LLM for Cypher/Entity Extraction:** Configured by `MAS_MODEL` mapping to the system LLMClient (fallback is `gemini-3-flash-preview`). Depending on `AGENT_TYPE` and `.env` presence, it will naturally cascade to Groq or Mistral if available.
- **Embedding Model:** Will invoke `llm_client.get_embedding()`, utilizing Google's `text-embedding-004` (or other default assigned via OpenRouter proxy hooks if `GOOGLE_API_KEY` is not present).

## The Flow
The End-to-End Suite executes a synchronous step-through logic across the layers:
1. **Scenario Readiness:** The Pytest setup reads realistic SCM .md texts.
2. **L3 Assimilate (`POST /v2/semantic/l3/assimilate`):** 
   - Post an SCM scenario (e.g., Strike alert).
   - Verify `get_embedding` generation and DB write. We intercept 502s dynamically and skip assertions gracefully if local API keys limit external generation.
3. **L3 Query (`POST /v2/semantic/l3/query`):**
   - Transmit a question related to the ingested texts (e.g., "How does the strike affect lead times?").
   - Wait for Cypher representation via `llm_client.generate()`.
   - Assert `200 OK` and inspect `provenance.session_id`.
4. **L4 Finalize (`POST /v2/semantic/l4/finalize`):**
   - Post a final `.md` report resolving a supply chain problem (Risk Pooling).
   - Validate creation and payload structures in Typesense backend mappings.
