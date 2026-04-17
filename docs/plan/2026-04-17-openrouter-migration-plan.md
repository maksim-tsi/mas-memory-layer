# OpenRouter Migration Plan
**Date:** 2026-04-17

## Overview
Based on the production load test on 2026-04-16, Gemini proved unstable for Cypher generation (leaving an orphaned knowledge graph) and bypassed OTel tracing. This plan covers deprecating Gemini and standardizing on OpenRouter for both conversational/logic generation and vector embeddings, while ensuring Arize Phoenix tracing works seamlessly using the OpenAI SDK integration.

## 1. Unified OpenRouter Client

### Environment Variables
Modify the `.env` template and application config to support:
- `OPENROUTER_API_KEY`: API authentication.
- `OPENROUTER_MODEL`: Identifier for the primary LLM (e.g., `meta-llama/llama-3.1-8b-instruct:free`).
- `OPENROUTER_EMBEDDING_MODEL`: Identifier for the embedding model (e.g., `qwen3-embedding-8b`).

### Code Changes
- **New Provider (`src/llm/providers/openrouter.py`)**: 
  - Subclass `BaseProvider` to implement `OpenRouterProvider`.
  - Initialize using the official OpenAI Python package: `AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=...)`.
  - Implement `generate()` mapping internally to OpenRouter's Chat Completions structure.
  - Implement `get_embedding()` mapped to OpenRouter's Embeddings interface.
- **Deprecation**: Keep `src/llm/providers/gemini.py` for backward compatibility with v1 logic, but mark the class with `@deprecated` using Python warnings.

## 2. Arize Phoenix Tracing Integration

**Strategy:** 
The transition to OpenRouter using the `openai` SDK is highly advantageous for observability. Phoenix natively traces `openai` package calls via the `OpenAIInstrumentor`.
- **Implementation Strategy**: In `src/llm/client.py`, the `_init_phoenix_instrumentation()` already checks for `openinference-instrumentation-openai`. This will hook cleanly into `openai.AsyncOpenAI` instances, even when the `base_url` points to OpenRouter.
- **Assurance Mechanism**: We explicitly install and configure `OpenAIInstrumentor`. When `client.chat.completions.create` runs, the trace data (including OpenRouter model name, latency, cost metrics, and token usage) is natively forwarded to the OpenTelemetry span processor and ingested by Arize Phoenix. We avoid using the `gemini` or raw `requests`-level tracing, effectively solving the dropped span issue highlighted in the load test findings.

## 3. Qdrant Dimensionality Safety

**Strategy: Collection Versioning**
Switching from Gemini (`text-embedding-004` / `gemini-embedding-001` at 768 dimensions) to OpenRouter `qwen/qwen3-embedding-8b` (configured via `EMBEDDING_DIMENSIONS`) alterations vector dimensional requirements. We must not delete the existing collections.
- **Memory Tier modifications**: Make the `collection_name` default to `episodes_v2` and `knowledge_base_v2` (or append `_v2` dynamically) for Gateway v2 operations within `EpisodicMemoryTier` and `SemanticMemoryTier`. This guarantees backward compatibility and prevents dimensionality collision without aggressive data loss.
