# LLM Providers

This package contains the implementation of various LLM providers for the MAS Memory Layer.

## Structure

- `client.py`: The main `LLMClient` that orchestrates provider selection and fallback.
- `providers/`: Directory containing individual provider implementations.
  - `base.py`: The abstract base class `BaseProvider` defining the interface.
  - `gemini.py`: Google Gemini provider.
  - `groq.py`: Groq provider (Llama/Mixtral models).
  - `mistral.py`: Mistral AI provider.

## Providers and Default Models

Each provider has a specific default model configured based on current best practices and requirements.

### Google Gemini (`gemini.py`)
- **Default Model**: `gemini-3-flash-preview`
- **Use Case**: General purpose, high throughput, low latency.
- **Provider Class**: `GeminiProvider`
- **Env Var**: `GOOGLE_API_KEY`

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

- `tests/integration/test_gemini_provider.py`: Tests `GeminiProvider` with real API calls.
- `tests/integration/test_groq_provider.py`: Tests `GroqProvider` with real API calls.
- `tests/integration/test_mistral_provider.py`: Tests `MistralProvider` with real API calls.

To run tests for a specific provider:

```bash
poetry run pytest tests/integration/test_gemini_provider.py
```
