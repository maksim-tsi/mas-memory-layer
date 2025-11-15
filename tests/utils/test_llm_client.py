import asyncio
from dataclasses import dataclass

import pytest

from src.utils.llm_client import LLMClient, BaseProvider, LLMResponse


class MockProvider(BaseProvider):
    def __init__(self, name: str, response_text: str = "ok", raise_exc: Exception | None = None):
        super().__init__(name=name)
        self._response_text = response_text
        self._raise = raise_exc

    async def generate(self, prompt: str, model: None = None, **kwargs) -> LLMResponse:
        if self._raise:
            raise self._raise
        # mimic some async delay
        await asyncio.sleep(0)
        return LLMResponse(text=self._response_text, provider=self.name, model=model or "mock-model")


@pytest.mark.asyncio
async def test_llm_client_fallback_order():
    # gemini will fail, groq will succeed
    gemini = MockProvider("gemini", raise_exc=RuntimeError("boom"))
    groq = MockProvider("groq", response_text="groq-ok")

    client = LLMClient(providers={"gemini": gemini, "groq": groq})
    resp = await client.generate("What is 2+2?")

    assert resp.text == "groq-ok"
    assert resp.provider == "groq"


@pytest.mark.asyncio
async def test_llm_client_priority_override():
    gemini = MockProvider("gemini", response_text="gemini-ok")
    groq = MockProvider("groq", response_text="groq-ok")

    client = LLMClient(providers={"gemini": gemini, "groq": groq})
    # Force groq as priority
    resp = await client.generate("Q", provider_priority="groq")

    assert resp.text == "groq-ok"
    assert resp.provider == "groq"


@pytest.mark.asyncio
async def test_llm_client_all_fail_raises():
    gemini = MockProvider("gemini", raise_exc=RuntimeError("fail1"))
    groq = MockProvider("groq", raise_exc=RuntimeError("fail2"))

    client = LLMClient(providers={"gemini": gemini, "groq": groq})
    with pytest.raises(RuntimeError):
        await client.generate("Q")
