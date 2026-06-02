import sys
import types
from types import SimpleNamespace

import pytest

from src.llm.providers.openrouter import OpenRouterEmptyCompletionError, OpenRouterProvider
from src.utils.llm_client import ProviderHealth
from src.utils.providers import GeminiProvider, GroqProvider, MistralProvider


class FakeResponse:
    pass


class FakeGeminiClient:
    def __init__(self, raise_exc=None):
        self.models = SimpleNamespace(
            generate_content=lambda *args, **kwargs: (_ for _ in ()).throw(raise_exc)
            if raise_exc
            else FakeResponse()
        )


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
                self.completions = SimpleNamespace(
                    create=lambda *a, **k: (_ for _ in ()).throw(raise_exc)
                    if raise_exc
                    else FakeResponse()
                )

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


class FakeOpenRouterCompletions:
    def __init__(self, response=None, raise_exc=None):
        self.response = response
        self.raise_exc = raise_exc
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_exc:
            raise self.raise_exc
        return self.response or _openrouter_response(content="ok")


class FakeOpenRouterClient:
    def __init__(self, completions):
        self.chat = SimpleNamespace(completions=completions)
        self.embeddings = SimpleNamespace()
        self.models = SimpleNamespace(list=lambda: [])


def register_fake_openrouter(completions, monkeypatch):
    fake_mod = types.SimpleNamespace(
        AsyncOpenAI=lambda base_url, api_key: FakeOpenRouterClient(completions)
    )
    monkeypatch.setitem(sys.modules, "openai", fake_mod)


def _openrouter_response(content, *, finish_reason="stop"):
    return SimpleNamespace(
        model="tencent/hy3-preview-20260421",
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(content=content, tool_calls=None),
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            completion_tokens_details=SimpleNamespace(reasoning_tokens=5),
        ),
    )


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


@pytest.mark.asyncio
async def test_openrouter_generate_uses_8192_max_completion_tokens_by_default(monkeypatch):
    monkeypatch.delenv("MAS_MAX_OUTPUT_TOKENS", raising=False)
    monkeypatch.delenv("OPENROUTER_REASONING_EFFORT", raising=False)
    monkeypatch.delenv("OPENROUTER_REASONING_EXCLUDE", raising=False)
    monkeypatch.setenv("OPENROUTER_MODEL", "tencent/hy3-preview")
    completions = FakeOpenRouterCompletions()
    register_fake_openrouter(completions, monkeypatch)

    provider = OpenRouterProvider(api_key="k")
    response = await provider.generate("hello")

    assert response.text == "ok"
    assert completions.calls[0]["max_completion_tokens"] == 8192
    assert "max_tokens" not in completions.calls[0]
    assert completions.calls[0]["extra_body"]["reasoning"] == {
        "effort": "low",
        "exclude": True,
    }


@pytest.mark.asyncio
async def test_openrouter_generate_respects_explicit_and_env_token_budgets(monkeypatch):
    completions = FakeOpenRouterCompletions()
    register_fake_openrouter(completions, monkeypatch)
    monkeypatch.setenv("MAS_MAX_OUTPUT_TOKENS", "7000")

    provider = OpenRouterProvider(api_key="k")
    await provider.generate("hello")
    await provider.generate("hello", max_output_tokens=9000)

    assert completions.calls[0]["max_completion_tokens"] == 7000
    assert completions.calls[1]["max_completion_tokens"] == 9000


@pytest.mark.asyncio
async def test_openrouter_generate_applies_reasoning_env(monkeypatch):
    completions = FakeOpenRouterCompletions()
    register_fake_openrouter(completions, monkeypatch)
    monkeypatch.setenv("OPENROUTER_MODEL", "tencent/hy3-preview")
    monkeypatch.setenv("OPENROUTER_REASONING_EFFORT", "none")
    monkeypatch.setenv("OPENROUTER_REASONING_EXCLUDE", "false")

    provider = OpenRouterProvider(api_key="k")
    response = await provider.generate("hello")

    assert response.metadata["reasoning"] == {"effort": "none", "exclude": False}
    assert completions.calls[0]["extra_body"]["reasoning"] == {
        "effort": "none",
        "exclude": False,
    }


@pytest.mark.asyncio
async def test_openrouter_empty_length_completion_is_generation_failure(monkeypatch):
    completions = FakeOpenRouterCompletions(
        response=_openrouter_response(content=None, finish_reason="length")
    )
    register_fake_openrouter(completions, monkeypatch)

    provider = OpenRouterProvider(api_key="k")

    with pytest.raises(OpenRouterEmptyCompletionError):
        await provider.generate("hello")
