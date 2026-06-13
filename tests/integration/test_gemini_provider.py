"""
Integration tests for Gemini provider.
"""

import os

import pytest

from src.llm.providers.gemini import GeminiProvider

HAS_GEMINI_KEY = bool(os.getenv("GOOGLE_API_KEY"))


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.integration
async def test_gemini_provider_real_call():
    """Test Gemini provider with a real API call."""
    if not HAS_GEMINI_KEY:
        pytest.skip("GOOGLE_API_KEY not found in environment")

    # Initialize provider directly
    provider = GeminiProvider(api_key=os.environ["GOOGLE_API_KEY"])
    health = await provider.health_check()
    assert health.healthy, f"Gemini provider unhealthy: {health.details}"

    # Generate text using default model (gemini-3-flash-preview)
    response = await provider.generate(prompt="Reply with exactly 'OK'", temperature=0.0)

    assert response.text is not None
    assert "OK" in response.text
    # Usage is a dict
    assert response.usage["prompt_tokens"] > 0
    assert response.usage["response_tokens"] > 0
    assert response.model == "gemini-3-flash-preview"
