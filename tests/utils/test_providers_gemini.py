import sys
import types
from types import SimpleNamespace

import pytest

from src.utils.llm_client import LLMResponse
from src.utils.providers import GeminiProvider


class FakeUsage:
    def __init__(self, prompt_count=10, candidate_count=15, total=25):
        self.prompt_token_count = prompt_count
        self.candidates_token_count = candidate_count
        self.total_token_count = total


class FakeResponse:
    def __init__(self, text: str, function_calls: list | None = None, finish_reason: str = "STOP"):
        self.text = text
        self.usage_metadata = FakeUsage()
        self.function_calls = function_calls or []
        self.candidates = [
            SimpleNamespace(
                finish_reason=finish_reason,
                content=SimpleNamespace(parts=[]),
            )
        ]


class FakeModels:
    def __init__(self, response: FakeResponse, raise_exc: Exception | None = None):
        self._response = response
        self._raise = raise_exc
        self.last_call_kwargs = None

    def generate_content(self, *args, **kwargs):
        self.last_call_kwargs = kwargs
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
        def __init__(self, text: str | None = None, name: str | None = None, response=None):
            self.text = text
            self.name = name
            self.response = response

        @classmethod
        def from_text(cls, text: str):
            return cls(text)

        @classmethod
        def from_function_response(cls, name: str, response):
            return cls(name=name, response=response)

    class FakeContent:
        def __init__(self, role: str, parts: list):
            self.role = role
            self.parts = parts

    class FakeGenerateContentConfig:
        def __init__(
            self,
            temperature=0.0,
            max_output_tokens=256,
            automatic_function_calling=None,
            system_instruction=None,
            tools=None,
            tool_config=None,
            response_mime_type=None,
            response_schema=None,
        ):
            self.temperature = temperature
            self.max_output_tokens = max_output_tokens
            self.automatic_function_calling = automatic_function_calling
            self.system_instruction = system_instruction
            self.tools = tools
            self.tool_config = tool_config
            self.response_mime_type = response_mime_type
            self.response_schema = response_schema

    class FakeFunctionCallingConfig:
        def __init__(self, mode=None, allowed_function_names=None):
            self.mode = mode
            self.allowed_function_names = allowed_function_names

    class FakeToolConfig:
        def __init__(self, function_calling_config=None):
            self.function_calling_config = function_calling_config

    class FakeTool:
        def __init__(self, function_declarations=None):
            self.function_declarations = function_declarations

    fake_types = types.SimpleNamespace(
        GenerateContentConfig=FakeGenerateContentConfig,
        Content=FakeContent,
        Part=FakePart,
        FunctionCallingConfig=FakeFunctionCallingConfig,
        ToolConfig=FakeToolConfig,
        Tool=FakeTool,
    )

    fake_genai_mod = types.SimpleNamespace(
        Client=lambda api_key: fake_client,
        types=fake_types,
    )
    fake_google_mod = types.ModuleType("google")
    fake_google_mod.genai = fake_genai_mod
    monkeypatch.setitem(sys.modules, "google", fake_google_mod)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai_mod)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)


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
    resp = await provider.generate("Q", model="gemini-3-flash-preview")
    assert resp.model == "gemini-3-flash-preview"
    assert resp.text == "override ok"


@pytest.mark.asyncio
async def test_gemini_generate_sdk_error(monkeypatch):
    fake_response = FakeResponse("ignored")
    fake_client = FakeClient(fake_response, raise_exc=RuntimeError("sdk fail"))
    register_fake_genai(fake_client, monkeypatch)

    provider = GeminiProvider(api_key="testkey")
    with pytest.raises(RuntimeError):
        await provider.generate("Q")


@pytest.mark.asyncio
async def test_gemini_generate_extracts_tool_calls(monkeypatch):
    function_call = SimpleNamespace(
        name="l2_search_facts",
        args={"query": "tea"},
        tool_use_id="call-1",
    )
    fake_response = FakeResponse("", function_calls=[function_call], finish_reason="FUNCTION_CALL")
    fake_client = FakeClient(fake_response)
    register_fake_genai(fake_client, monkeypatch)

    provider = GeminiProvider(api_key="testkey")
    resp = await provider.generate(
        "Find facts about tea.",
        tools=[
            {
                "name": "l2_search_facts",
                "description": "Search facts.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            }
        ],
        tool_calling_mode="AUTO",
    )

    assert resp.tool_calls
    assert resp.tool_calls[0].name == "l2_search_facts"
    assert resp.tool_calls[0].arguments == {"query": "tea"}
    assert resp.tool_calls[0].call_id == "call-1"
    assert resp.metadata["finish_reason"] == "FUNCTION_CALL"
    assert resp.raw_content is fake_response.candidates[0].content


@pytest.mark.asyncio
async def test_gemini_generate_uses_gemini3_tool_temperature_default(monkeypatch):
    fake_response = FakeResponse("ok")
    fake_client = FakeClient(fake_response)
    register_fake_genai(fake_client, monkeypatch)

    provider = GeminiProvider(api_key="testkey")
    await provider.generate(
        "Find facts about tea.",
        tools=[
            {
                "name": "l2_search_facts",
                "description": "Search facts.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            }
        ],
    )

    config = fake_client.models.last_call_kwargs["config"]
    assert config.temperature == 1.0


@pytest.mark.asyncio
async def test_gemini_generate_builds_followup_contents_for_tool_results(monkeypatch):
    fake_response = FakeResponse("done")
    fake_client = FakeClient(fake_response)
    register_fake_genai(fake_client, monkeypatch)

    provider = GeminiProvider(api_key="testkey")
    previous_response = SimpleNamespace(parts=[SimpleNamespace(text="model tool call")])
    await provider.generate(
        "Find facts about tea.",
        previous_response=previous_response,
        tool_results=[{"name": "l2_search_facts", "response": {"results_count": 1}}],
    )

    contents = fake_client.models.last_call_kwargs["contents"]
    assert len(contents) == 3
    assert contents[1] is previous_response
    assert contents[2].parts[0].name == "l2_search_facts"
    assert contents[2].parts[0].response == {"results_count": 1}
