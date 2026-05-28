# LLM Providers

This package contains the implementation of various LLM providers for the MAS Memory Layer.

## Structure

- `client.py`: The main `LLMClient` that orchestrates provider selection and fallback.
- `providers/`: Directory containing individual provider implementations.
  - `base.py`: The abstract base class `BaseProvider` defining the interface.
  - `openrouter.py`: OpenRouter provider (via OpenAI SDK compatibility layer).
  - `gemini.py`: Google Gemini provider.
  - `groq.py`: Groq provider (Llama/Mixtral models).
  - `mistral.py`: Mistral AI provider.

## Current Runtime Capabilities

As of April 17, 2026, the LLM layer supports both text-only generations and provider-normalized
tool-call responses, with OpenRouter configured as the default V2 API execution path when
`OPENROUTER_API_KEY` is present.

The current normalized response contract includes:

- response text,
- provider/model attribution,
- usage metadata,
- structured tool calls,
- and provider-native raw response data when follow-up turns require it.

This contract is currently used by the `MemoryAgent` tool loop for `v1-*` variants.

For V2 memory APIs, the runtime also uses provider-level embeddings via
`LLMClient.get_embedding()`, with OpenRouter configured by
`OPENROUTER_EMBEDDING_MODEL`.

Production REST/MCP runtime does not install the local SentenceTransformer/Torch stack. Local
embeddings are reserved for legacy/offline experiments through the optional Poetry group:
`poetry install --with local-embeddings`.

## Providers and Default Models

Each provider has a specific default model configured based on current best practices and requirements.

### OpenRouter (`openrouter.py`)
- **Default Generation Model**: `tencent/hy3-preview`
- **Default Embedding Model**: `qwen/qwen3-embedding-8b`
- **Use Case**: Default V2 API generation and embedding path.
- **Provider Class**: `OpenRouterProvider`
- **Env Vars**: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_EMBEDDING_MODEL`

### Google Gemini (`gemini.py`)
- **Default Model**: `gemini-3-flash-preview`
- **Use Case**: Secondary provider and fallback path when enabled.
- **Provider Class**: `GeminiProvider`
- **Env Var**: `GOOGLE_API_KEY`
- **Current Status**: Supports manual function-calling/tool-loop execution for `v1-*`
  API-Wall requests.

### Gemini Tool-Calling Notes

The current Gemini implementation uses a bounded manual tool loop rather than SDK-managed automatic
tool execution. This was chosen to keep tool execution inside YAAM policy/runtime control and to
preserve Phoenix observability for tool spans.

Two implementation details are operationally important for Gemini 3 models:

1. Function-call-only responses must not rely on `response.text` being present.
2. Follow-up turns in a manual tool loop must preserve the full SDK response object so Gemini 3
   thought-signature validation succeeds.

### Groq (`groq.py`)
- **Default Model**: `openai/gpt-oss-120b`
- **Use Case**: Very low latency inference for open-source models.
- **Provider Class**: `GroqProvider`
- **Env Var**: `GROQ_API_KEY`

### Mistral AI (`mistral.py`)
- **Default Model**: `mistral-small-2506`
- **Use Case**: European data locality, strong reasoning capabilities.
- **Provider Class**: `MistralProvider`
- **Env Var**: `MISTRAL_API_KEY`

## Testing

Integration tests are separated by provider to ensure isolation and clarity. These tests require valid API keys in the environment.

Focused unit tests for provider normalization and Gemini tool-calling behavior live under
`tests/utils/`.

- `tests/integration/test_gemini_provider.py`: Tests `GeminiProvider` with real API calls.
- `tests/integration/test_groq_provider.py`: Tests `GroqProvider` with real API calls.
- `tests/integration/test_mistral_provider.py`: Tests `MistralProvider` with real API calls.
- `tests/utils/test_providers_gemini.py`: Unit tests for Gemini response parsing, tool-call
  normalization, and thought-signature-safe follow-up behavior.

For V2 runtime validation of collection naming and embedding vector sizing, use:
- `scripts/debug/check_tier_collection.py`

To run tests for a specific provider:

```bash
poetry run pytest tests/integration/test_gemini_provider.py
```
