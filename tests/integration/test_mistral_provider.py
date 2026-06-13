"""
Integration tests for Mistral provider.
"""

import os

import pytest

from src.llm.providers.mistral import MistralProvider

HAS_MISTRAL_KEY = bool(os.getenv("MISTRAL_API_KEY"))


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.integration
async def test_mistral_provider_real_call():
    """Test Mistral provider with a real API call."""
    if not HAS_MISTRAL_KEY:
        pytest.skip("MISTRAL_API_KEY not found in environment")

    # Initialize provider directly
    provider = MistralProvider(api_key=os.environ["MISTRAL_API_KEY"])
    health = await provider.health_check()
    assert health.healthy, f"Mistral provider unhealthy: {health.details}"

    # Generate text using default model (mistral-small-2506)
    response = await provider.generate(prompt="Reply with exactly 'OK'", temperature=0.0)

    assert response.text is not None
    assert "OK" in response.text
    assert "mistral" in response.model.lower()  # Accept any mistral model
