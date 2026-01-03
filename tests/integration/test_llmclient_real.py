import os
import pytest

from src.utils.llm_client import LLMClient, ProviderConfig
from src.utils.providers import GeminiProvider, GroqProvider, MistralProvider


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(
    not (os.getenv("GOOGLE_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("MISTRAL_API_KEY")),
    reason="No LLM provider API keys configured in environment",
)
async def test_llmclient_real_providers():
    """Integration test using real provider adapters; skipped when keys absent.

    This test uses `GOOGLE_API_KEY`, `GROQ_API_KEY`, and `MISTRAL_API_KEY` from environment
    and registers provider adapters found in the environment. It then runs a health-check
    across all providers and performs a simple generation to ensure the `LLMClient` can
    successfully fallback between providers when configured.
    """

    client = LLMClient()
    # Register providers if keys available
    if os.getenv("GOOGLE_API_KEY"):
        client.register_provider(GeminiProvider(api_key=os.getenv("GOOGLE_API_KEY")), ProviderConfig(name="gemini", priority=0))
    if os.getenv("GROQ_API_KEY"):
        client.register_provider(GroqProvider(api_key=os.getenv("GROQ_API_KEY")), ProviderConfig(name="groq", priority=1))
    if os.getenv("MISTRAL_API_KEY"):
        client.register_provider(MistralProvider(api_key=os.getenv("MISTRAL_API_KEY")), ProviderConfig(name="mistral", priority=2))

    assert client.available_providers(), "No providers registered"

    # Perform health check (none paused) and ensure we get a report for each
    health = await client.health_check()
    assert set(health.keys()) == set(client.available_providers())

    # Do a single generation (provider ordering enforces sdk order)
    resp = await client.generate("What is 2+2? Answer briefly.")
    assert resp is not None
    assert hasattr(resp, "text")
    assert isinstance(resp.text, str)
