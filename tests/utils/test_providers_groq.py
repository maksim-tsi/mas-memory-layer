import sys
import types
import pytest
from types import SimpleNamespace

from src.utils.providers import GroqProvider
from src.utils.llm_client import LLMResponse


class FakeUsage:
    def __init__(self, p=5, c=3, t=8):
        self.prompt_tokens = p
        self.completion_tokens = c
        self.total_tokens = t


class FakeChoice:
    def __init__(self, text: str):
        self.message = SimpleNamespace(content=text)


class FakeResponse:
    def __init__(self, text: str):
        self.choices = [FakeChoice(text)]
        self.usage = FakeUsage()
        self.text = text


class FakeCompletions:
    def __init__(self, response: FakeResponse, raise_exc: Exception | None = None):
        self._response = response
        self._raise = raise_exc

    def create(self, *args, **kwargs):
        if self._raise:
            raise self._raise
        return self._response


class FakeChat:
    def __init__(self, response: FakeResponse, raise_exc: Exception | None = None):
        self.completions = FakeCompletions(response, raise_exc)


class FakeGroq:
    def __init__(self, response: FakeResponse, raise_exc: Exception | None = None):
        self.chat = FakeChat(response, raise_exc)


def register_fake_groq(fake_client, monkeypatch):
    fake_groq_mod = types.SimpleNamespace(Groq=lambda api_key: fake_client)
    monkeypatch.setitem(sys.modules, "groq", fake_groq_mod)


@pytest.mark.asyncio
async def test_groq_generate_success(monkeypatch):
    fake_response = FakeResponse("2 + 2 equals 4")
    fake_client = FakeGroq(fake_response)
    register_fake_groq(fake_client, monkeypatch)

    provider = GroqProvider(api_key="key")
    resp = await provider.generate("Q")
    assert isinstance(resp, LLMResponse)
    assert resp.text.strip().startswith("2 + 2")
    assert resp.provider == "groq"
    assert resp.usage["prompt_tokens"] == 5


@pytest.mark.asyncio
async def test_groq_generate_sdk_error(monkeypatch):
    fake_response = FakeResponse("ignored")
    fake_client = FakeGroq(fake_response, raise_exc=RuntimeError("fail"))
    register_fake_groq(fake_client, monkeypatch)

    provider = GroqProvider(api_key="k")
    with pytest.raises(RuntimeError):
        await provider.generate("Q")
