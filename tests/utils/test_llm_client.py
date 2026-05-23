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

    async def generate(
        self, *_: object, **__: object
    ) -> LLMResponse:  # pragma: no cover - deterministic helper
        return LLMResponse(text=self._text, provider=self.name, model=self._model)


class _FailingProvider(BaseProvider):
    async def generate(self, *_: object, **__: object) -> LLMResponse:
        raise RuntimeError("simulated failure")


class _FailingHealthProvider(BaseProvider):
    async def generate(self, *_: object, **__: object) -> LLMResponse:
        return LLMResponse(text="ok", provider=self.name)

    async def health_check(self) -> ProviderHealth:
        raise ConnectionError("unhealthy")


class _AsyncClosableProvider(_SuccessProvider):
    def __init__(self, name: str) -> None:
        super().__init__(name=name, text="ok")
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


class _SyncClosableSdkClient:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _ProviderWithSdkClient(_SuccessProvider):
    def __init__(self, name: str, sdk_client: _SyncClosableSdkClient) -> None:
        super().__init__(name=name, text="ok")
        self.client = sdk_client


class _ProviderWithFailingClose(_SuccessProvider):
    async def aclose(self) -> None:
        raise RuntimeError("close failed")


@pytest.mark.asyncio
async def test_generate_uses_fallback_order_when_first_fails() -> None:
    """LLMClient should move to the next provider when the first raises."""

    client = LLMClient()
    client.register_provider(
        _FailingProvider(name="first"), ProviderConfig(name="first", priority=0)
    )
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
    client.register_provider(
        _SuccessProvider(name="healthy", text="done"), ProviderConfig(name="healthy")
    )
    client.register_provider(
        _FailingHealthProvider(name="unhealthy"), ProviderConfig(name="unhealthy")
    )

    report = await client.health_check()

    assert report["healthy"].healthy is True
    assert report["unhealthy"].healthy is False
    assert report["unhealthy"].last_error == "unhealthy"


@pytest.mark.asyncio
async def test_close_closes_async_provider_lifecycle() -> None:
    client = LLMClient()
    provider = _AsyncClosableProvider(name="closable")
    client.register_provider(provider, ProviderConfig(name="closable"))

    cleanup = await client.close()

    assert provider.closed is True
    assert cleanup == {"status": "ok", "errors": []}


@pytest.mark.asyncio
async def test_close_closes_sync_sdk_client_lifecycle() -> None:
    client = LLMClient()
    sdk_client = _SyncClosableSdkClient()
    client.register_provider(
        _ProviderWithSdkClient(name="provider", sdk_client=sdk_client),
        ProviderConfig(name="provider"),
    )

    cleanup = await client.aclose()

    assert sdk_client.closed is True
    assert cleanup == {"status": "ok", "errors": []}


@pytest.mark.asyncio
async def test_close_reports_cleanup_warning_without_raising() -> None:
    client = LLMClient()
    client.register_provider(
        _ProviderWithFailingClose(name="failing", text="ok"),
        ProviderConfig(name="failing"),
    )

    cleanup = await client.close()

    assert cleanup["status"] == "warning"
    assert cleanup["errors"][0]["provider"] == "failing"
    assert cleanup["errors"][0]["error_type"] == "RuntimeError"


def test_provider_config_defaults() -> None:
    """Default provider configs should expose sane defaults."""

    config = ProviderConfig(name="test")

    assert config.enabled is True
    assert config.priority == 0
    assert config.timeout == 15.0
