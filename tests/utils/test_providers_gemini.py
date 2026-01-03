import sys
import types
import pytest


from src.utils.providers import GeminiProvider
from src.utils.llm_client import LLMResponse


class FakeUsage:
    def __init__(self, prompt_count=10, candidate_count=15, total=25):
        self.prompt_token_count = prompt_count
        self.candidates_token_count = candidate_count
        self.total_token_count = total


class FakeResponse:
    def __init__(self, text: str):
        self.text = text
        self.usage_metadata = FakeUsage()


class FakeModels:
    def __init__(self, response: FakeResponse, raise_exc: Exception | None = None):
        self._response = response
        self._raise = raise_exc

    def generate_content(self, *args, **kwargs):
        if self._raise:
            raise self._raise
        return self._response


class FakeClient:
    def __init__(self, response: FakeResponse, raise_exc: Exception | None = None):
        self.models = FakeModels(response, raise_exc=raise_exc)


def register_fake_genai(fake_client, monkeypatch):
    """Helper to inject a fake google.genai module with Client returning fake_client."""
    # Create minimal classes to satisfy provider expectations
    class FakePart:
        def __init__(self, text: str):
            self.text = text

        @classmethod
        def from_text(cls, text: str):
            return cls(text)

    class FakeContent:
        def __init__(self, role: str, parts: list):
            self.role = role
            self.parts = parts

    class FakeGenerateContentConfig:
        def __init__(self, temperature=0.0, max_output_tokens=256, system_instruction=None, response_mime_type=None, response_schema=None):
            self.temperature = temperature
            self.max_output_tokens = max_output_tokens
            self.system_instruction = system_instruction
            self.response_mime_type = response_mime_type
            self.response_schema = response_schema

    fake_types = types.SimpleNamespace(
        GenerateContentConfig=FakeGenerateContentConfig,
        Content=FakeContent,
        Part=FakePart,
    )

    fake_genai_mod = types.SimpleNamespace(
        Client=lambda api_key: fake_client,
        types=fake_types,
    )
    fake_google_mod = types.ModuleType("google")
    fake_google_mod.genai = fake_genai_mod
    monkeypatch.setitem(sys.modules, "google", fake_google_mod)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai_mod)


@pytest.mark.asyncio
async def test_gemini_generate_success(monkeypatch):
    fake_response = FakeResponse("2+2 equals 4")
    fake_client = FakeClient(fake_response)
    register_fake_genai(fake_client, monkeypatch)

    provider = GeminiProvider(api_key="testkey")

    resp = await provider.generate("What is 2+2?")
    assert isinstance(resp, LLMResponse)
    assert resp.text == "2+2 equals 4"
    assert resp.provider == "gemini"
    assert resp.model == "gemini-3-flash-preview"
    assert resp.usage["prompt_tokens"] == 10


@pytest.mark.asyncio
async def test_gemini_generate_model_override(monkeypatch):
    fake_response = FakeResponse("override ok")
    fake_client = FakeClient(fake_response)
    register_fake_genai(fake_client, monkeypatch)

    provider = GeminiProvider(api_key="testkey")
    resp = await provider.generate("Q", model="gemini-2.5-flash-lite")
    assert resp.model == "gemini-2.5-flash-lite"
    assert resp.text == "override ok"


@pytest.mark.asyncio
async def test_gemini_generate_sdk_error(monkeypatch):
    fake_response = FakeResponse("ignored")
    fake_client = FakeClient(fake_response, raise_exc=RuntimeError("sdk fail"))
    register_fake_genai(fake_client, monkeypatch)

    provider = GeminiProvider(api_key="testkey")
    with pytest.raises(RuntimeError):
        await provider.generate("Q")
