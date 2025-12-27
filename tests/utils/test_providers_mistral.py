import sys
import types
import pytest
from types import SimpleNamespace

from src.utils.providers import MistralProvider
from src.utils.llm_client import LLMResponse


class FakeUsage:
    def __init__(self, p=7, c=5, t=12):
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



class FakeChat:
    def __init__(self, response: FakeResponse, raise_exc: Exception | None = None):
        self._response = response
        self._raise = raise_exc

    def complete(self, *args, **kwargs):
        if self._raise:
            raise self._raise
        return self._response

class FakeMistral:
    def __init__(self, response: FakeResponse, raise_exc: Exception | None = None):
        self.chat = FakeChat(response, raise_exc)


def register_fake_mistral(fake_client, monkeypatch):
    fake_mod = types.SimpleNamespace(Mistral=lambda api_key: fake_client)
    monkeypatch.setitem(sys.modules, "mistralai", fake_mod)


@pytest.mark.asyncio
async def test_mistral_generate_success(monkeypatch):
    fake_response = FakeResponse("2+2 is 4")
    fake_client = FakeMistral(fake_response)
    register_fake_mistral(fake_client, monkeypatch)

    provider = MistralProvider(api_key="k")
    resp = await provider.generate("Q")
    assert isinstance(resp, LLMResponse)
    assert resp.text.strip().startswith("2+2")
    assert resp.provider == "mistral"
    assert resp.usage["prompt_tokens"] == 7


@pytest.mark.asyncio
async def test_mistral_generate_sdk_error(monkeypatch):
    fake_response = FakeResponse("ignore")
    fake_client = FakeMistral(fake_response, raise_exc=RuntimeError("fail"))
    register_fake_mistral(fake_client, monkeypatch)

    provider = MistralProvider(api_key="k")
    with pytest.raises(RuntimeError):
        await provider.generate("Q")
