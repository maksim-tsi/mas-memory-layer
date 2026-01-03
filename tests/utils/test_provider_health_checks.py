import sys
import types
import pytest
from types import SimpleNamespace

from src.utils.providers import GeminiProvider, GroqProvider, MistralProvider
from src.utils.llm_client import ProviderHealth


class FakeResponse:
    pass


class FakeGeminiClient:
    def __init__(self, raise_exc=None):
        self.models = SimpleNamespace(generate_content=lambda *args, **kwargs: (_ for _ in ()).throw(raise_exc) if raise_exc else FakeResponse())


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


class FakeGroqClient:
    def __init__(self, raise_exc=None):
        class Chat:
            def __init__(self, raise_exc):
                self.completions = SimpleNamespace(create=lambda *a, **k: (_ for _ in ()).throw(raise_exc) if raise_exc else FakeResponse())

        self.chat = Chat(raise_exc)


def register_fake_groq(fake_client, monkeypatch):
    fake_groq_mod = types.SimpleNamespace(Groq=lambda api_key: fake_client)
    monkeypatch.setitem(sys.modules, "groq", fake_groq_mod)


class FakeMistralClient:
    def __init__(self, raise_exc=None):
        class Chat:
            def __init__(self, raise_exc):
                self._raise = raise_exc

            def complete(self, *args, **kwargs):
                if self._raise:
                    raise self._raise
                return FakeResponse()

        self.chat = Chat(raise_exc)


def register_fake_mistral(fake_client, monkeypatch):
    fake_mod = types.SimpleNamespace(Mistral=lambda api_key: fake_client)
    monkeypatch.setitem(sys.modules, "mistralai", fake_mod)


@pytest.mark.asyncio
async def test_gemini_health_ok(monkeypatch):
    fake_client = FakeGeminiClient()
    register_fake_genai(fake_client, monkeypatch)
    provider = GeminiProvider(api_key="k")
    report = await provider.health_check()
    assert isinstance(report, ProviderHealth)
    assert report.healthy is True


@pytest.mark.asyncio
async def test_gemini_health_failure(monkeypatch):
    fake_client = FakeGeminiClient(raise_exc=RuntimeError("boom"))
    register_fake_genai(fake_client, monkeypatch)
    provider = GeminiProvider(api_key="k")
    report = await provider.health_check()
    assert isinstance(report, ProviderHealth)
    assert report.healthy is False


@pytest.mark.asyncio
async def test_groq_health_ok(monkeypatch):
    fake_client = FakeGroqClient()
    register_fake_groq(fake_client, monkeypatch)
    provider = GroqProvider(api_key="k")
    report = await provider.health_check()
    assert report.healthy is True


@pytest.mark.asyncio
async def test_groq_health_failure(monkeypatch):
    fake_client = FakeGroqClient(raise_exc=RuntimeError("boom"))
    register_fake_groq(fake_client, monkeypatch)
    provider = GroqProvider(api_key="k")
    report = await provider.health_check()
    assert report.healthy is False


@pytest.mark.asyncio
async def test_mistral_health_ok(monkeypatch):
    fake_client = FakeMistralClient()
    register_fake_mistral(fake_client, monkeypatch)
    provider = MistralProvider(api_key="k")
    report = await provider.health_check()
    assert report.healthy is True


@pytest.mark.asyncio
async def test_mistral_health_failure(monkeypatch):
    fake_client = FakeMistralClient(raise_exc=RuntimeError("boom"))
    register_fake_mistral(fake_client, monkeypatch)
    provider = MistralProvider(api_key="k")
    report = await provider.health_check()
    assert report.healthy is False
