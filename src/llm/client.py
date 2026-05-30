"""LLM client scaffolding for multi-provider Phase 2 work.

This module defines an orchestrating LLM client that can register multiple
provider wrappers, execute fallback-aware generations, and surface simple
health indicators for the lifecycle engines that will promote facts across
tiers.
"""

from __future__ import annotations

import asyncio
import importlib.util
import inspect
import logging
import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from typing import Any, ClassVar, cast

from src.llm.providers.base import BaseProvider, LLMResponse, ProviderHealth

logger = logging.getLogger(__name__)


# Phoenix configuration constants
PHOENIX_DEFAULT_PROJECT = "mlm-mas-dev"
PHOENIX_SERVICE_NAME = "mas-memory-layer"

_PHOENIX_INITIALIZED = False
_PHOENIX_PROJECT_NAME: str | None = None
_PHOENIX_OWNED_TRACER_PROVIDER: Any | None = None

_GOOGLE_GENAI_OPENINFERENCE_MIN_VERSION = "1.57.0"
_OPENAI_OPENINFERENCE_MIN_VERSION = "2.8.0"

_PHOENIX_SPAN_PROCESSOR_ENV = "YAAM_OTEL_SPAN_PROCESSOR"
_PHOENIX_FORCE_FLUSH_TIMEOUT_ENV = "YAAM_OTEL_FORCE_FLUSH_TIMEOUT_MS"
_PHOENIX_DEFAULT_FORCE_FLUSH_TIMEOUT_MS = 5000


def _package_version_at_least(package_name: str, minimum_version: str) -> bool:
    """Return whether an installed package is new enough for explicit instrumentation."""
    try:
        from packaging.version import Version

        return Version(version(package_name)) >= Version(minimum_version)
    except PackageNotFoundError:
        return False
    except Exception as e:
        logger.debug("Could not inspect package version for %s: %s", package_name, e)
        return False


def _phoenix_uses_batch_span_processor() -> bool:
    """Return whether Phoenix should use its BatchSpanProcessor path."""
    configured = os.environ.get(_PHOENIX_SPAN_PROCESSOR_ENV, "batch").strip().lower()
    if configured == "simple":
        return False
    if configured == "batch":
        return True
    logger.warning(
        "Invalid %s=%r; defaulting Phoenix tracing to BatchSpanProcessor",
        _PHOENIX_SPAN_PROCESSOR_ENV,
        configured,
    )
    return True


def _phoenix_force_flush_timeout_ms() -> int:
    """Return the configured Phoenix force-flush timeout in milliseconds."""
    configured = os.environ.get(_PHOENIX_FORCE_FLUSH_TIMEOUT_ENV)
    if configured is None:
        return _PHOENIX_DEFAULT_FORCE_FLUSH_TIMEOUT_MS
    try:
        timeout = int(configured)
    except ValueError:
        logger.warning(
            "Invalid %s=%r; defaulting to %dms",
            _PHOENIX_FORCE_FLUSH_TIMEOUT_ENV,
            configured,
            _PHOENIX_DEFAULT_FORCE_FLUSH_TIMEOUT_MS,
        )
        return _PHOENIX_DEFAULT_FORCE_FLUSH_TIMEOUT_MS
    if timeout <= 0:
        logger.warning(
            "Invalid %s=%r; defaulting to %dms",
            _PHOENIX_FORCE_FLUSH_TIMEOUT_ENV,
            configured,
            _PHOENIX_DEFAULT_FORCE_FLUSH_TIMEOUT_MS,
        )
        return _PHOENIX_DEFAULT_FORCE_FLUSH_TIMEOUT_MS
    return timeout


def _get_current_tracer_provider() -> Any:
    """Return the active OpenTelemetry tracer provider."""
    from opentelemetry import trace

    return trace.get_tracer_provider()


def _is_proxy_tracer_provider(tracer_provider: Any) -> bool:
    """Return whether OpenTelemetry still has only the lazy proxy provider."""
    from opentelemetry import trace

    return isinstance(tracer_provider, trace.ProxyTracerProvider)


def _register_phoenix_tracer_provider(
    *,
    project_name: str,
    endpoint: str,
    batch: bool,
) -> Any:
    """Register YAAM's Phoenix tracer provider."""
    from phoenix.otel import register

    return register(
        project_name=project_name,
        endpoint=endpoint,
        batch=batch,
        verbose=False,
        auto_instrument=False,
    )


def _instrument_provider_sdks(tracer_provider: Any) -> None:
    """Enable supported provider SDK instrumentation against the tracer provider."""
    # Explicitly instrument Google GenAI if auto_instrument missed it
    try:
        # Check if google.genai is actually installed first to avoid "Could not import" warning from instrumentor
        if importlib.util.find_spec("google.genai"):
            if _package_version_at_least("google-genai", _GOOGLE_GENAI_OPENINFERENCE_MIN_VERSION):
                from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

                instrumentor = GoogleGenAIInstrumentor()
                if not getattr(instrumentor, "_is_instrumented_by_opentelemetry", False):
                    instrumentor.instrument(tracer_provider=tracer_provider)
                    logger.info("Google GenAI instrumentation enabled (explicit)")
            else:
                logger.info(
                    "Skipping Google GenAI instrumentation: google-genai must be >=%s",
                    _GOOGLE_GENAI_OPENINFERENCE_MIN_VERSION,
                )
        else:
            logger.debug("google.genai module not found; skipping instrumentation")

    except ImportError:
        logger.debug(
            "openinference-instrumentation-google-genai not installed; "
            "Google GenAI calls will not be traced"
        )
    except Exception as e:
        logger.warning("Failed to instrument Google GenAI: %s", e)

    # Explicitly instrument OpenAI SDK (which powers OpenRouter calls)
    try:
        if _package_version_at_least("openai", _OPENAI_OPENINFERENCE_MIN_VERSION):
            from openinference.instrumentation.openai import OpenAIInstrumentor

            instrumentor = OpenAIInstrumentor()
            if not getattr(instrumentor, "_is_instrumented_by_opentelemetry", False):
                instrumentor.instrument(tracer_provider=tracer_provider)
                logger.info("OpenAI instrumentation enabled")
        else:
            logger.info(
                "Skipping OpenAI instrumentation: openai must be >=%s",
                _OPENAI_OPENINFERENCE_MIN_VERSION,
            )
    except ImportError:
        logger.debug(
            "openinference-instrumentation-openai not installed; OpenAI calls will not be traced"
        )
    except Exception as e:
        logger.warning("Failed to instrument OpenAI: %s", e)


# Phoenix/OpenTelemetry auto-instrumentation (optional)
def _init_phoenix_instrumentation() -> None:
    """Initialize Phoenix/OpenTelemetry instrumentation if configured."""
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
    if not endpoint:
        logger.debug(
            "PHOENIX_COLLECTOR_ENDPOINT not set; Phoenix instrumentation disabled. "
            "Set to http://<host>:6006/v1/traces to enable."
        )
        return

    agent_type = os.environ.get("AGENT_TYPE")
    default_project = (
        f"{PHOENIX_DEFAULT_PROJECT}-{agent_type}" if agent_type else PHOENIX_DEFAULT_PROJECT
    )
    project_name = os.environ.get("PHOENIX_PROJECT_NAME", default_project)

    try:
        global _PHOENIX_INITIALIZED
        global _PHOENIX_PROJECT_NAME
        global _PHOENIX_OWNED_TRACER_PROVIDER
        # Mark as initialized immediately to prevent retries on partial failures
        _PHOENIX_INITIALIZED = True
        _PHOENIX_PROJECT_NAME = project_name

        # Register tracer provider with Phoenix collector
        # Check if tracer provider is already registered to avoid "Overriding of current TracerProvider" warning
        current_provider = _get_current_tracer_provider()

        if _is_proxy_tracer_provider(current_provider):
            # Only register if no real provider is set
            use_batch = _phoenix_uses_batch_span_processor()
            tracer_provider = _register_phoenix_tracer_provider(
                project_name=project_name,
                endpoint=endpoint,
                batch=use_batch,
            )
            _PHOENIX_OWNED_TRACER_PROVIDER = tracer_provider

            logger.info(
                "Phoenix instrumentation enabled: project=%s, endpoint=%s, span_processor=%s",
                project_name,
                endpoint,
                "batch" if use_batch else "simple",
            )
        else:
            logger.debug("Phoenix instrumentation skipped: TracerProvider already set")
            tracer_provider = current_provider

        _instrument_provider_sdks(tracer_provider)

    except ImportError:
        logger.debug(
            "arize-phoenix not installed; run 'pip install arize-phoenix' to enable tracing"
        )
    except Exception as e:
        logger.warning("Failed to initialize Phoenix instrumentation: %s", e)


def ensure_phoenix_instrumentation() -> None:
    """Ensure Phoenix instrumentation is initialized for current environment."""
    global _PHOENIX_INITIALIZED
    agent_type = os.environ.get("AGENT_TYPE")
    desired_project = os.environ.get(
        "PHOENIX_PROJECT_NAME",
        f"{PHOENIX_DEFAULT_PROJECT}-{agent_type}" if agent_type else PHOENIX_DEFAULT_PROJECT,
    )
    if _PHOENIX_INITIALIZED and desired_project == _PHOENIX_PROJECT_NAME:
        return
    _init_phoenix_instrumentation()


def shutdown_phoenix_instrumentation() -> None:
    """Flush and shut down YAAM-owned Phoenix tracing resources."""
    global _PHOENIX_INITIALIZED
    global _PHOENIX_OWNED_TRACER_PROVIDER
    global _PHOENIX_PROJECT_NAME

    tracer_provider = _PHOENIX_OWNED_TRACER_PROVIDER
    if tracer_provider is None:
        return

    timeout_ms = _phoenix_force_flush_timeout_ms()
    if hasattr(tracer_provider, "force_flush"):
        try:
            tracer_provider.force_flush(timeout_millis=timeout_ms)
        except TypeError:
            tracer_provider.force_flush(timeout_ms)
        except Exception as e:  # pragma: no cover - defensive cleanup path
            logger.warning("Failed to force-flush Phoenix spans: %s", e)

    if hasattr(tracer_provider, "shutdown"):
        try:
            tracer_provider.shutdown()
        except Exception as e:  # pragma: no cover - defensive cleanup path
            logger.warning("Failed to shut down Phoenix tracer provider: %s", e)

    _PHOENIX_OWNED_TRACER_PROVIDER = None
    _PHOENIX_INITIALIZED = False
    _PHOENIX_PROJECT_NAME = None


# Initialize at module load time (idempotent)
ensure_phoenix_instrumentation()


@dataclass
class ProviderConfig:
    """Configuration metadata used to prioritize and time-bound providers."""

    name: str
    timeout: float = 15.0
    priority: int = 0
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMClient:
    """Multi-provider orchestrator with fallback support and health diagnostics."""

    # Model-to-provider routing map
    MODEL_ROUTING: ClassVar[dict[str, list[str]]] = {
        "x-ai/grok-4.1-fast": ["openrouter"],
        "tencent/hy3-preview": ["openrouter"],
        "qwen/qwen3-embedding-8b": ["openrouter"],
        "gemini-3-flash-preview": ["google", "gemini", "openrouter"],  # Try both possible names
        "gemini-3-pro-preview": ["google-pro", "google", "gemini", "openrouter"],
        "gemini-2.5-flash": ["google", "gemini"],
        "gemini-embedding-001": ["google", "gemini"],
        "text-embedding-004": ["google", "gemini"],
        "openai/gpt-oss-120b": ["groq", "openrouter"],
        "mistral-large": ["mistral", "openrouter"],
    }

    def __init__(self, provider_configs: Iterable[ProviderConfig] | None = None) -> None:
        self.name = "llm-client"
        self._providers: dict[str, BaseProvider] = {}
        self._configs: dict[str, ProviderConfig] = {}
        if provider_configs:
            for config in provider_configs:
                self._configs[config.name] = config

    @classmethod
    def from_env(cls) -> LLMClient:
        """Build an LLMClient with providers configured from environment variables."""
        # Delayed imports to avoid circular dependencies
        from src.llm.providers.gemini import GeminiProvider
        from src.llm.providers.groq import GroqProvider
        from src.llm.providers.mistral import MistralProvider
        from src.llm.providers.openrouter import OpenRouterProvider

        ensure_phoenix_instrumentation()

        openrouter_timeout = float(os.environ.get("MAS_OPENROUTER_TIMEOUT", "45.0"))

        client = cls(
            provider_configs=[
                ProviderConfig(name="openrouter", timeout=openrouter_timeout, priority=0),
                ProviderConfig(name="groq", timeout=30.0, priority=1),
                ProviderConfig(name="mistral", timeout=30.0, priority=2),
                ProviderConfig(name="gemini", timeout=30.0, priority=3),
            ]
        )

        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if openrouter_key:
            client.register_provider(OpenRouterProvider(api_key=openrouter_key))
        else:
            logger.warning("OPENROUTER_API_KEY not set; OpenRouter provider disabled.")

        google_key = os.environ.get("GOOGLE_API_KEY")
        if google_key:
            client.register_provider(GeminiProvider(api_key=google_key))

        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            client.register_provider(GroqProvider(api_key=groq_key))

        mistral_key = os.environ.get("MISTRAL_API_KEY")
        if mistral_key:
            client.register_provider(MistralProvider(api_key=mistral_key))

        if not client.available_providers():
            logger.warning("No LLM providers configured; responses will be fallback messages.")

        return client

    def register_provider(
        self, provider: BaseProvider, config: ProviderConfig | None = None
    ) -> None:
        """Register a provider instance alongside optional configuration metadata."""
        self._providers[provider.name] = provider
        if config:
            self._configs[provider.name] = config
        elif provider.name not in self._configs:
            self._configs[provider.name] = ProviderConfig(name=provider.name)

    def deregister_provider(self, name: str) -> None:
        """Remove a provider from future generation attempts."""
        self._providers.pop(name, None)
        self._configs.pop(name, None)

    def available_providers(self) -> Sequence[str]:
        """Return the currently registered provider names."""
        return list(self._providers.keys())

    async def close(self) -> dict[str, Any]:
        """Best-effort cleanup for registered provider SDK clients.

        Provider SDKs differ in lifecycle support. This method intentionally
        reports cleanup errors instead of raising so callers can preserve the
        original operation result.
        """
        errors: list[dict[str, str]] = []
        for provider_name, provider in self._providers.items():
            errors.extend(await self._close_provider(provider_name, provider))
        return {
            "status": "warning" if errors else "ok",
            "errors": errors,
        }

    async def aclose(self) -> dict[str, Any]:
        """Alias for async context-manager style callers."""
        return await self.close()

    async def _close_provider(self, provider_name: str, provider: BaseProvider) -> list[dict[str, str]]:
        errors: list[dict[str, str]] = []
        targets = [provider]
        provider_client = getattr(provider, "client", None)
        if provider_client is not None and provider_client is not provider:
            targets.append(provider_client)

        seen: set[int] = set()
        for target in targets:
            if id(target) in seen:
                continue
            seen.add(id(target))
            close_method = getattr(target, "aclose", None) or getattr(target, "close", None)
            if close_method is None:
                continue
            try:
                if inspect.iscoroutinefunction(close_method):
                    await close_method()
                else:
                    result = await asyncio.to_thread(close_method)
                    if inspect.isawaitable(result):
                        await result
            except Exception as exc:  # pragma: no cover - defensive diagnostics
                logger.warning("Failed to close provider '%s': %s", provider_name, exc)
                errors.append(
                    {
                        "provider": provider_name,
                        "target": type(target).__name__,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
        return errors

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        provider_order: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Attempt generation with the preferred provider order and fallback if necessary."""

        agent_metadata = kwargs.pop("agent_metadata", None)
        self._annotate_span(agent_metadata)

        # Route to correct provider based on model name if not explicitly specified
        if model and not provider_order:
            # Check if model requires specific provider
            for model_pattern, provider_names in self.MODEL_ROUTING.items():
                if model == model_pattern or model.startswith(model_pattern):
                    # Find first available provider from the routing list
                    for provider_name in provider_names:
                        if provider_name in self._providers:
                            provider_order = [provider_name]
                            logger.debug(f"Routing model '{model}' to provider '{provider_name}'")
                            break
                    if provider_order:
                        break

        order = self._resolve_order(provider_order)
        last_exc: Exception | None = None
        for provider_name in order:
            provider = self._providers.get(provider_name)
            config = self._configs.get(provider_name, ProviderConfig(name=provider_name))
            if not provider or not config.enabled:
                continue
            try:
                # If model is specified but not relevant to this provider (fallback scenario),
                # drop it so the provider uses its default.
                # Simple heuristic: if the model name suggests a different provider family, drop it.
                effective_model = model
                if model:
                    is_mistral_provider = "mistral" in provider_name.lower()
                    is_groq_provider = "groq" in provider_name.lower()
                    is_gemini_provider = (
                        "gemini" in provider_name.lower() or "google" in provider_name.lower()
                    )

                    # Specific checks to drop incompatible models
                    should_drop = False
                    if (
                        (
                            is_groq_provider
                            and ("gemini" in model.lower() or "mistral" in model.lower())
                        )
                        or (
                            is_mistral_provider
                            and ("gemini" in model.lower() or "gpt" in model.lower())
                        )
                        or (
                            is_gemini_provider
                            and ("mistral" in model.lower() or "gpt" in model.lower())
                        )
                    ):
                        should_drop = True

                    if should_drop:
                        effective_model = None
                        logger.debug(
                            "Dropping incompatible model '%s' for provider '%s'",
                            model,
                            provider_name,
                        )

                coro = provider.generate(prompt, model=effective_model, **kwargs)
                response: LLMResponse
                if asyncio.iscoroutine(coro):
                    response = cast(
                        LLMResponse, await asyncio.wait_for(coro, timeout=config.timeout)
                    )
                else:
                    response = cast(
                        LLMResponse,
                        await asyncio.wait_for(
                            asyncio.to_thread(lambda coro=coro: coro), timeout=config.timeout
                        ),
                    )
                if not response.provider:
                    response.provider = provider_name
                return response
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.warning("Provider '%s' failed: %s", provider_name, exc)
                last_exc = exc
                continue

        raise last_exc or RuntimeError("No healthy LLM provider available")

    async def get_embedding(
        self, text: str, model: str | None = None, provider: str | None = None
    ) -> list[float]:
        """Get embedding for text using explicit or OpenRouter-first fail-fast routing."""
        if provider:
            target_provider = self._providers.get(provider)
            if not target_provider:
                raise RuntimeError(f"Requested embedding provider '{provider}' is not configured")
            return await target_provider.get_embedding(text, model=model)

        target_provider = self._providers.get("openrouter")
        if not target_provider:
            raise RuntimeError(
                "OpenRouter provider is required for embeddings but is not configured"
            )

        return await target_provider.get_embedding(text, model=model)

    def _annotate_span(self, agent_metadata: dict[str, Any] | None) -> None:
        """Attach agent metadata to the active trace span if available."""
        if not agent_metadata:
            return
        try:
            from opentelemetry import trace
        except Exception:  # pragma: no cover - optional dependency
            return
        span = trace.get_current_span()
        if not span or not span.is_recording():
            return
        for key, value in agent_metadata.items():
            if value is None:
                continue
            span.set_attribute(str(key), value)

    async def health_check(self) -> dict[str, ProviderHealth]:
        """Return health reports for every registered provider."""

        tasks: dict[str, asyncio.Task[ProviderHealth]] = {}
        for name, provider in self._providers.items():
            tasks[name] = asyncio.create_task(provider.health_check())

        reports: dict[str, ProviderHealth] = {}
        for name, task in tasks.items():
            try:
                reports[name] = await task
            except Exception as exc:  # pragma: no cover - health fallback
                reports[name] = ProviderHealth(
                    name=name, healthy=False, last_error=str(exc), details="health check failure"
                )
        return reports

    def _resolve_order(self, provider_order: Sequence[str] | None = None) -> list[str]:
        """Determine the final provider order by combining config priorities and overrides."""

        if provider_order:
            order = [name for name in provider_order if name in self._providers]
        else:
            order = sorted(
                (
                    name
                    for name, cfg in self._configs.items()
                    if cfg.enabled and name in self._providers
                ),
                key=lambda name: self._configs[name].priority,
            )
        for provider_name in self._providers:
            if (
                provider_name not in order
                and self._configs.get(provider_name, ProviderConfig(name=provider_name)).enabled
            ):
                order.append(provider_name)
        return order


__all__ = [
    "BaseProvider",
    "LLMClient",
    "LLMResponse",
    "ProviderConfig",
    "ProviderHealth",
    "ensure_phoenix_instrumentation",
    "shutdown_phoenix_instrumentation",
]
