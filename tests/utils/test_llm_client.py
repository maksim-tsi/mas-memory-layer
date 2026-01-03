import pytest

from src.utils.llm_client import (
    BaseProvider,
    LLMClient,
    LLMResponse,
    ProviderConfig,
    ProviderHealth,
)


class _SuccessProvider(BaseProvider):
    def __init__(self, name: str, text: str, model: str | None = None) -> None:
        super().__init__(name=name)
        self._text = text
        self._model = model

    async def generate(self, *_: object, **__: object) -> LLMResponse:  # pragma: no cover - deterministic helper
        return LLMResponse(text=self._text, provider=self.name, model=self._model)


class _FailingProvider(BaseProvider):
    async def generate(self, *_: object, **__: object) -> LLMResponse:
        raise RuntimeError("simulated failure")


class _FailingHealthProvider(BaseProvider):
    async def generate(self, *_: object, **__: object) -> LLMResponse:
        return LLMResponse(text="ok", provider=self.name)

    async def health_check(self) -> ProviderHealth:
        raise ConnectionError("unhealthy")


@pytest.mark.asyncio
async def test_generate_uses_fallback_order_when_first_fails() -> None:
    """LLMClient should move to the next provider when the first raises."""

    client = LLMClient()
    client.register_provider(_FailingProvider(name="first"), ProviderConfig(name="first", priority=0))
    client.register_provider(
        _SuccessProvider(name="second", text="ok", model="m1"),
        ProviderConfig(name="second", priority=1),
    )

    response = await client.generate("prompt")

    assert response.text == "ok"
    assert response.provider == "second"
    assert response.model == "m1"


@pytest.mark.asyncio
async def test_health_check_reports_unhealthy_provider() -> None:
    """Health check should capture providers that raise during readiness."""

    client = LLMClient()
    client.register_provider(_SuccessProvider(name="healthy", text="done"), ProviderConfig(name="healthy"))
    client.register_provider(_FailingHealthProvider(name="unhealthy"), ProviderConfig(name="unhealthy"))

    report = await client.health_check()

    assert report["healthy"].healthy is True
    assert report["unhealthy"].healthy is False
    assert report["unhealthy"].last_error == "unhealthy"


def test_provider_config_defaults() -> None:
    """Default provider configs should expose sane defaults."""

    config = ProviderConfig(name="test")

    assert config.enabled is True
    assert config.priority == 0
    assert config.timeout == 15.0
