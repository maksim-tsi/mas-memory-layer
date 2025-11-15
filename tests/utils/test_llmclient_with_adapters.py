import sys
import types
import pytest
from types import SimpleNamespace

from src.utils.llm_client import LLMClient, ProviderConfig
from src.utils.providers import GeminiProvider, GroqProvider, MistralProvider


def register_fake_genai(fake_client, monkeypatch):
    class FakeGenerateContentConfig:
        def __init__(self, temperature=0.0, max_output_tokens=256, system_instruction=None):
            self.temperature = temperature
            self.max_output_tokens = max_output_tokens
            self.system_instruction = system_instruction

    fake_genai_mod = types.SimpleNamespace(
        Client=lambda api_key: fake_client,
        types=types.SimpleNamespace(GenerateContentConfig=FakeGenerateContentConfig),
    )
    fake_google_mod = types.ModuleType("google")
    fake_google_mod.genai = fake_genai_mod
    monkeypatch.setitem(sys.modules, "google", fake_google_mod)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai_mod)


def register_fake_groq(fake_client, monkeypatch):
    fake_groq_mod = types.SimpleNamespace(Groq=lambda api_key: fake_client)
    monkeypatch.setitem(sys.modules, "groq", fake_groq_mod)


class SimpleResponse:
    def __init__(self, text: str):
        self.text = text
        self.usage_metadata = SimpleNamespace(prompt_token_count=1, candidates_token_count=1, total_token_count=2)
        self.usage = SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        # groq and mistral style choices
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=text))]


class FakeGeminiClient:
    def __init__(self, response: SimpleResponse, raise_exc=None):
        self.models = SimpleNamespace(generate_content=lambda *args, **kwargs: (_ for _ in ()).throw(raise_exc) if raise_exc else response)


class FakeGroqClient:
    def __init__(self, response: SimpleResponse, raise_exc=None):
        class Chat:
            def __init__(self, resp, raise_exc):
                self.completions = SimpleNamespace(create=lambda *a, **k: (_ for _ in ()).throw(raise_exc) if raise_exc else resp)

        self.chat = Chat(response, raise_exc)


class FakeMistralClient:
    def __init__(self, response: SimpleResponse, raise_exc=None):
        class Chat:
            def __init__(self, resp, raise_exc):
                self._resp = resp
                self._raise = raise_exc

            def complete(self, *args, **kwargs):
                if self._raise:
                    raise self._raise
                return self._resp

        self.chat = Chat(response, raise_exc)


def register_fake_mistral(fake_client, monkeypatch):
    fake_mod = types.SimpleNamespace(Mistral=lambda api_key: fake_client)
    monkeypatch.setitem(sys.modules, "mistralai", fake_mod)


@pytest.mark.asyncio
async def test_llmclient_with_mistral(monkeypatch):
    # gemini fails, mistral succeeds
    gemini_resp = SimpleResponse("gemini response")
    mistral_resp = SimpleResponse("mistral response")
    register_fake_genai(FakeGeminiClient(gemini_resp, raise_exc=RuntimeError("boom")), monkeypatch)
    register_fake_mistral(FakeMistralClient(mistral_resp), monkeypatch)

    gemini = GeminiProvider(api_key="k")
    mistral = MistralProvider(api_key="k")

    client = LLMClient()
    client.register_provider(gemini, ProviderConfig(name="gemini", priority=0))
    client.register_provider(mistral, ProviderConfig(name="mistral", priority=1))

    resp = await client.generate("What is it")
    assert resp.text == "mistral response"
    assert resp.provider == "mistral"


@pytest.mark.asyncio
async def test_llmclient_fallback_with_adapters(monkeypatch):
    # Gemini fails, Groq succeeds
    gemini_resp = SimpleResponse("gemini response")
    groq_resp = SimpleResponse("groq response")
    register_fake_genai(FakeGeminiClient(gemini_resp, raise_exc=RuntimeError("boom")), monkeypatch)
    register_fake_groq(FakeGroqClient(groq_resp), monkeypatch)

    gemini = GeminiProvider(api_key="k")
    groq = GroqProvider(api_key="k")

    client = LLMClient()
    client.register_provider(gemini, ProviderConfig(name="gemini", priority=0))
    client.register_provider(groq, ProviderConfig(name="groq", priority=1))

    resp = await client.generate("What is 2+2?")
    assert resp.text == "groq response"
    assert resp.provider == "groq"


@pytest.mark.asyncio
async def test_llmclient_priority_override(monkeypatch):
    gemini_resp = SimpleResponse("gemini-ok")
    groq_resp = SimpleResponse("groq-ok")
    register_fake_genai(FakeGeminiClient(gemini_resp), monkeypatch)
    register_fake_groq(FakeGroqClient(groq_resp), monkeypatch)

    gemini = GeminiProvider(api_key="k")
    groq = GroqProvider(api_key="k")

    client = LLMClient()
    client.register_provider(gemini, ProviderConfig(name="gemini", priority=1))
    client.register_provider(groq, ProviderConfig(name="groq", priority=0))

    # Should pick groq by priority
    resp = await client.generate("Q")
    assert resp.provider == "groq"
