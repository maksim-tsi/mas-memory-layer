import pytest

import src.llm.client as client_module
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


class _FakeTracerProvider:
    def __init__(self) -> None:
        self.force_flush_calls: list[dict[str, int]] = []
        self.shutdown_called = False

    def force_flush(self, *, timeout_millis: int) -> None:
        self.force_flush_calls.append({"timeout_millis": timeout_millis})

    def shutdown(self) -> None:
        self.shutdown_called = True


class _ExternalTracerProvider:
    pass


def _reset_phoenix_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_module, "_PHOENIX_INITIALIZED", False)
    monkeypatch.setattr(client_module, "_PHOENIX_PROJECT_NAME", None)
    monkeypatch.setattr(client_module, "_PHOENIX_OWNED_TRACER_PROVIDER", None)


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


def test_from_env_uses_120s_openrouter_timeout_by_default(monkeypatch) -> None:
    monkeypatch.setattr(client_module, "ensure_phoenix_instrumentation", lambda: None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MAS_OPENROUTER_TIMEOUT", raising=False)
    for key in ("GOOGLE_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    client = LLMClient.from_env()

    assert client._configs["openrouter"].timeout == 120.0


@pytest.mark.asyncio
async def test_generate_logs_provider_failure_type(caplog) -> None:
    client = LLMClient()
    client.register_provider(
        _FailingProvider(name="first"), ProviderConfig(name="first", priority=0)
    )
    client.register_provider(
        _SuccessProvider(name="second", text="ok"), ProviderConfig(name="second", priority=1)
    )

    with caplog.at_level("WARNING"):
        response = await client.generate("prompt")

    assert response.text == "ok"
    assert "Provider 'first' failed: RuntimeError: simulated failure" in caplog.text


def test_instrumentation_version_guard_accepts_compatible_package(monkeypatch) -> None:
    """Instrumentation guard should allow SDK versions required by OpenInference."""

    monkeypatch.setattr(client_module, "version", lambda _: "2.8.1")

    assert client_module._package_version_at_least("openai", "2.8.0") is True


def test_instrumentation_version_guard_rejects_stale_package(monkeypatch) -> None:
    """Instrumentation guard should skip stale SDKs before importing instrumentors."""

    monkeypatch.setattr(client_module, "version", lambda _: "1.14.0")

    assert client_module._package_version_at_least("openai", "2.8.0") is False


def test_phoenix_registers_batch_span_processor_by_default(monkeypatch) -> None:
    """Phoenix registration should use the SDK BatchSpanProcessor path by default."""

    _reset_phoenix_state(monkeypatch)
    fake_provider = _FakeTracerProvider()
    calls: list[dict[str, object]] = []

    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://phoenix.test:6006/v1/traces")
    monkeypatch.delenv("YAAM_OTEL_SPAN_PROCESSOR", raising=False)
    monkeypatch.setattr(client_module, "_get_current_tracer_provider", lambda: object())
    monkeypatch.setattr(client_module, "_is_proxy_tracer_provider", lambda _: True)
    monkeypatch.setattr(client_module, "_instrument_provider_sdks", lambda _: None)

    def register(**kwargs: object) -> _FakeTracerProvider:
        calls.append(kwargs)
        return fake_provider

    monkeypatch.setattr(client_module, "_register_phoenix_tracer_provider", register)

    client_module._init_phoenix_instrumentation()

    assert calls[0]["batch"] is True
    assert client_module._PHOENIX_OWNED_TRACER_PROVIDER is fake_provider


def test_phoenix_registers_simple_span_processor_when_requested(monkeypatch) -> None:
    """Operators should be able to keep the old simple processor for debugging."""

    _reset_phoenix_state(monkeypatch)
    calls: list[dict[str, object]] = []

    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://phoenix.test:6006/v1/traces")
    monkeypatch.setenv("YAAM_OTEL_SPAN_PROCESSOR", "simple")
    monkeypatch.setattr(client_module, "_get_current_tracer_provider", lambda: object())
    monkeypatch.setattr(client_module, "_is_proxy_tracer_provider", lambda _: True)
    monkeypatch.setattr(client_module, "_instrument_provider_sdks", lambda _: None)
    monkeypatch.setattr(
        client_module,
        "_register_phoenix_tracer_provider",
        lambda **kwargs: calls.append(kwargs) or _FakeTracerProvider(),
    )

    client_module._init_phoenix_instrumentation()

    assert calls[0]["batch"] is False


def test_phoenix_invalid_span_processor_falls_back_to_batch(monkeypatch, caplog) -> None:
    """Invalid processor config should be safe and visible in logs."""

    _reset_phoenix_state(monkeypatch)
    calls: list[dict[str, object]] = []

    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://phoenix.test:6006/v1/traces")
    monkeypatch.setenv("YAAM_OTEL_SPAN_PROCESSOR", "surprise")
    monkeypatch.setattr(client_module, "_get_current_tracer_provider", lambda: object())
    monkeypatch.setattr(client_module, "_is_proxy_tracer_provider", lambda _: True)
    monkeypatch.setattr(client_module, "_instrument_provider_sdks", lambda _: None)
    monkeypatch.setattr(
        client_module,
        "_register_phoenix_tracer_provider",
        lambda **kwargs: calls.append(kwargs) or _FakeTracerProvider(),
    )

    with caplog.at_level("WARNING"):
        client_module._init_phoenix_instrumentation()

    assert calls[0]["batch"] is True
    assert "defaulting Phoenix tracing to BatchSpanProcessor" in caplog.text


def test_phoenix_no_endpoint_disables_instrumentation(monkeypatch) -> None:
    """Missing endpoint should keep Phoenix optional and avoid provider setup."""

    _reset_phoenix_state(monkeypatch)
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    monkeypatch.setattr(
        client_module,
        "_get_current_tracer_provider",
        lambda: pytest.fail("tracer provider should not be inspected"),
    )

    client_module._init_phoenix_instrumentation()

    assert client_module._PHOENIX_INITIALIZED is False
    assert client_module._PHOENIX_OWNED_TRACER_PROVIDER is None


def test_phoenix_external_tracer_provider_is_not_owned_or_shutdown(monkeypatch) -> None:
    """YAAM should not replace or shut down tracer providers created elsewhere."""

    _reset_phoenix_state(monkeypatch)
    external_provider = _ExternalTracerProvider()
    instrumented: list[object] = []

    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://phoenix.test:6006/v1/traces")
    monkeypatch.setattr(client_module, "_get_current_tracer_provider", lambda: external_provider)
    monkeypatch.setattr(client_module, "_is_proxy_tracer_provider", lambda _: False)
    monkeypatch.setattr(client_module, "_instrument_provider_sdks", instrumented.append)
    monkeypatch.setattr(
        client_module,
        "_register_phoenix_tracer_provider",
        lambda **_: pytest.fail("external provider should not be overwritten"),
    )

    client_module._init_phoenix_instrumentation()
    client_module.shutdown_phoenix_instrumentation()

    assert instrumented == [external_provider]
    assert client_module._PHOENIX_OWNED_TRACER_PROVIDER is None


def test_phoenix_shutdown_flushes_and_shuts_down_owned_provider(monkeypatch) -> None:
    """YAAM-owned Phoenix providers should be flushed before shutdown."""

    _reset_phoenix_state(monkeypatch)
    fake_provider = _FakeTracerProvider()
    monkeypatch.setenv("YAAM_OTEL_FORCE_FLUSH_TIMEOUT_MS", "1234")
    monkeypatch.setattr(client_module, "_PHOENIX_INITIALIZED", True)
    monkeypatch.setattr(client_module, "_PHOENIX_PROJECT_NAME", "phoenix-test")
    monkeypatch.setattr(client_module, "_PHOENIX_OWNED_TRACER_PROVIDER", fake_provider)

    client_module.shutdown_phoenix_instrumentation()

    assert fake_provider.force_flush_calls == [{"timeout_millis": 1234}]
    assert fake_provider.shutdown_called is True
    assert client_module._PHOENIX_INITIALIZED is False
    assert client_module._PHOENIX_PROJECT_NAME is None
    assert client_module._PHOENIX_OWNED_TRACER_PROVIDER is None
