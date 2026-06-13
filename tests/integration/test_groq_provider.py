"""
Integration tests for Groq provider.
"""

import os

import pytest

from src.llm.providers.groq import GroqProvider

HAS_GROQ_KEY = bool(os.getenv("GROQ_API_KEY"))


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.integration
async def test_groq_provider_real_call():
    """Test Groq provider with a real API call."""
    if not HAS_GROQ_KEY:
        pytest.skip("GROQ_API_KEY not found in environment")

    # Initialize provider directly
    provider = GroqProvider(api_key=os.environ["GROQ_API_KEY"])
    health = await provider.health_check()
    assert health.healthy, f"Groq provider unhealthy: {health.details}"

    # Generate text using default model (openai/gpt-oss-120b)
    response = await provider.generate(prompt="Reply with exactly 'OK'", temperature=0.0)

    assert response.text is not None
    assert "OK" in response.text
    assert response.model == "openai/gpt-oss-120b"
