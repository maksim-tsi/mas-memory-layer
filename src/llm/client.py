"""LLM client scaffolding for multi-provider Phase 2 work.

This module defines an orchestrating LLM client that can register multiple
provider wrappers, execute fallback-aware generations, and surface simple
health indicators for the lifecycle engines that will promote facts across
tiers.
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar, cast

from src.llm.providers.base import BaseProvider, LLMResponse, ProviderHealth

logger = logging.getLogger(__name__)


# Phoenix configuration constants
PHOENIX_DEFAULT_PROJECT = "mlm-mas-dev"
PHOENIX_SERVICE_NAME = "mas-memory-layer"

_PHOENIX_INITIALIZED = False
_PHOENIX_PROJECT_NAME: str | None = None


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
        # Mark as initialized immediately to prevent retries on partial failures
        _PHOENIX_INITIALIZED = True
        _PHOENIX_PROJECT_NAME = project_name

        # Register tracer provider with Phoenix collector
        # Check if tracer provider is already registered to avoid "Overriding of current TracerProvider" warning
        from opentelemetry import trace
        from phoenix.otel import register

        if isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
            # Only register if no real provider is set
            tracer_provider = register(
                project_name=project_name,
                endpoint=endpoint,
                auto_instrument=True,  # Auto-detect and instrument installed packages
            )

            logger.info(
                "Phoenix instrumentation enabled: project=%s, endpoint=%s", project_name, endpoint
            )
        else:
            logger.debug("Phoenix instrumentation skipped: TracerProvider already set")
            tracer_provider = trace.get_tracer_provider()  # type: ignore

        # Explicitly instrument Google GenAI if auto_instrument missed it
        try:
            # Check if google.genai is actually installed first to avoid "Could not import" warning from instrumentor
            if importlib.util.find_spec("google.genai"):
                from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

                instrumentor = GoogleGenAIInstrumentor()
                if not getattr(instrumentor, "_is_instrumented_by_opentelemetry", False):
                    instrumentor.instrument(tracer_provider=tracer_provider)
                    logger.info("Google GenAI instrumentation enabled (explicit)")
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
            from openinference.instrumentation.openai import OpenAIInstrumentor

            instrumentor = OpenAIInstrumentor()
            if not getattr(instrumentor, "_is_instrumented_by_opentelemetry", False):
                instrumentor.instrument(tracer_provider=tracer_provider)
                logger.info("OpenAI instrumentation enabled")
        except ImportError:
            logger.debug(
                "openinference-instrumentation-openai not installed; OpenAI calls will not be traced"
            )
        except Exception as e:
            logger.warning("Failed to instrument OpenAI: %s", e)

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
        "gemini-3-flash-preview": ["google", "gemini"],  # Try both possible names
        "gemini-3-pro-preview": ["google-pro", "google", "gemini"],
        "gemini-2.5-flash": ["google", "gemini"],
        "gemini-embedding-001": ["google", "gemini"],
        "text-embedding-004": ["google", "gemini"],
        "openai/gpt-oss-120b": ["groq"],
        "mistral-large": ["mistral"],
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

        ensure_phoenix_instrumentation()

        client = cls(
            provider_configs=[
                ProviderConfig(name="gemini", timeout=30.0, priority=0),
                ProviderConfig(name="groq", timeout=30.0, priority=1),
                ProviderConfig(name="mistral", timeout=30.0, priority=2),
            ]
        )

        google_key = os.environ.get("GOOGLE_API_KEY")
        if google_key:
            client.register_provider(GeminiProvider(api_key=google_key))
        else:
            logger.warning("GOOGLE_API_KEY not set; Gemini provider disabled.")

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
        """Get embedding for text from specified or default provider."""
        # Simple routing for now - default to gemini if available, otherwise first available
        target_provider = None

        if provider and provider in self._providers:
            target_provider = self._providers[provider]
        elif "gemini" in self._providers:
            target_provider = self._providers["gemini"]
        elif self._providers:
            target_provider = next(iter(self._providers.values()))

        if not target_provider:
            raise RuntimeError("No LLM provider available for embeddings")

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
]
