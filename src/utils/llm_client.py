"""LLM client scaffolding for multi-provider Phase 2 work.

This module defines an orchestrating LLM client that can register multiple
provider wrappers, execute fallback-aware generations, and surface simple
health indicators for the lifecycle engines that will promote facts across
tiers.

The implementation keeps the core logic simple while still exposing enough APIs
for Phase 2A/2B controllers to scale: configurable provider order, timeout
control, and health checks.

Phoenix/OpenTelemetry Instrumentation:
    If PHOENIX_COLLECTOR_ENDPOINT is set, auto-instrumentors are activated
    at module load time for LLM call observability. This enables embedding
    dimension verification and latency debugging in the Arize Phoenix UI.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, cast

logger = logging.getLogger(__name__)


# Phoenix configuration constants
PHOENIX_DEFAULT_PROJECT = "mlm-mas-dev"
PHOENIX_SERVICE_NAME = "mas-memory-layer"


# Phoenix/OpenTelemetry auto-instrumentation (optional)
def _init_phoenix_instrumentation() -> None:
    """Initialize Phoenix/OpenTelemetry instrumentation if configured.
    
    Environment Variables:
        PHOENIX_COLLECTOR_ENDPOINT: OTLP collector URL (e.g., http://192.168.107.172:6006/v1/traces)
        PHOENIX_PROJECT_NAME: Project name for trace grouping (default: mlm-mas-dev)
    
    Project Naming Convention:
        - mlm-mas-dev: Development environment
        - mlm-mas-test: Testing/CI environment  
        - mlm-mas-prod: Production environment
    """
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
    if not endpoint:
        logger.debug(
            "PHOENIX_COLLECTOR_ENDPOINT not set; Phoenix instrumentation disabled. "
            "Set to http://<host>:6006/v1/traces to enable."
        )
        return
    
    project_name = os.environ.get("PHOENIX_PROJECT_NAME", PHOENIX_DEFAULT_PROJECT)
    
    try:
        from phoenix.otel import register
        
        # Register tracer provider with Phoenix collector
        tracer_provider = register(
            project_name=project_name,
            endpoint=endpoint,
            auto_instrument=True,  # Auto-detect and instrument installed packages
        )
        
        logger.info(
            "Phoenix instrumentation enabled: project=%s, endpoint=%s",
            project_name,
            endpoint
        )
        
        # Explicitly instrument Google GenAI if auto_instrument missed it
        try:
            from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
            instrumentor = GoogleGenAIInstrumentor()
            if not getattr(instrumentor, '_is_instrumented_by_opentelemetry', False):
                instrumentor.instrument(tracer_provider=tracer_provider)
                logger.info("Google GenAI instrumentation enabled (explicit)")
        except ImportError:
            logger.debug(
                "openinference-instrumentation-google-genai not installed; "
                "Google GenAI calls will not be traced"
            )
        except Exception as e:
            logger.warning("Failed to instrument Google GenAI: %s", e)
        
    except ImportError:
        logger.debug(
            "arize-phoenix not installed; run 'pip install arize-phoenix' to enable tracing"
        )
    except Exception as e:
        logger.warning("Failed to initialize Phoenix instrumentation: %s", e)


# Initialize at module load time (idempotent)
_init_phoenix_instrumentation()


@dataclass(frozen=True)
class ProviderHealth:
    """Runtime health report returned by each provider wrapper."""

    name: str
    healthy: bool
    details: Optional[str] = None
    last_error: Optional[str] = None


@dataclass
class LLMResponse:
    """Standardized response returned from every provider."""

    text: str
    provider: str
    model: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderConfig:
    """Configuration metadata used to prioritize and time-bound providers."""

    name: str
    timeout: float = 15.0
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseProvider:
    """Abstract provider wrapper interface for the orchestrating client."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs: Any) -> LLMResponse:
        """Generate text for the supplied prompt."""
        raise NotImplementedError()

    async def health_check(self) -> ProviderHealth:
        """Return a lightweight health signal that lifecycle engines can inspect."""
        return ProviderHealth(name=self.name, healthy=True, details="Provider configured")


class LLMClient:
    """Multi-provider orchestrator with fallback support and health diagnostics."""

    # Model-to-provider routing map
    MODEL_ROUTING = {
        "gemini-3-flash-preview": ["google", "gemini"],  # Try both possible names
        "gemini-3-pro-preview": ["google-pro", "google", "gemini"],
        "gemini-2.5-flash": ["google", "gemini"],
        "gemini-embedding-001": ["google", "gemini"],
        "openai/gpt-oss-120b": ["groq"],
        "mistral-large": ["mistral"],
    }

    def __init__(self, provider_configs: Optional[Iterable[ProviderConfig]] = None) -> None:
        self.name = "llm-client"
        self._providers: Dict[str, BaseProvider] = {}
        self._configs: Dict[str, ProviderConfig] = {}
        if provider_configs:
            for config in provider_configs:
                self._configs[config.name] = config

    def register_provider(self, provider: BaseProvider, config: Optional[ProviderConfig] = None) -> None:
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
        model: Optional[str] = None,
        provider_order: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Attempt generation with the preferred provider order and fallback if necessary."""

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
        last_exc: Optional[Exception] = None
        for provider_name in order:
            provider = self._providers.get(provider_name)
            config = self._configs.get(provider_name, ProviderConfig(name=provider_name))
            if not provider or not config.enabled:
                continue
            try:
                coro = provider.generate(prompt, model=model, **kwargs)
                response: LLMResponse
                if asyncio.iscoroutine(coro):
                    response = cast(LLMResponse, await asyncio.wait_for(coro, timeout=config.timeout))
                else:
                    response = cast(LLMResponse, await asyncio.wait_for(asyncio.to_thread(lambda: coro), timeout=config.timeout))
                if not response.provider:
                    response.provider = provider_name
                return response
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.warning("Provider '%s' failed: %s", provider_name, exc)
                last_exc = exc
                continue

        raise last_exc or RuntimeError("No healthy LLM provider available")

    async def health_check(self) -> Dict[str, ProviderHealth]:
        """Return health reports for every registered provider."""

        tasks: Dict[str, asyncio.Task[ProviderHealth]] = {}
        for name, provider in self._providers.items():
            tasks[name] = asyncio.create_task(provider.health_check())

        reports: Dict[str, ProviderHealth] = {}
        for name, task in tasks.items():
            try:
                reports[name] = await task
            except Exception as exc:  # pragma: no cover - health fallback
                reports[name] = ProviderHealth(name=name, healthy=False, last_error=str(exc), details="health check failure")
        return reports

    def _resolve_order(self, provider_order: Optional[Sequence[str]] = None) -> List[str]:
        """Determine the final provider order by combining config priorities and overrides."""

        if provider_order:
            order = [name for name in provider_order if name in self._providers]
        else:
            order = sorted(
                (name for name, cfg in self._configs.items() if cfg.enabled and name in self._providers),
                key=lambda name: self._configs[name].priority,
            )
        for provider_name in self._providers:
            if provider_name not in order and self._configs.get(provider_name, ProviderConfig(name=provider_name)).enabled:
                order.append(provider_name)
        return order


__all__ = ["BaseProvider", "LLMClient", "LLMResponse", "ProviderConfig", "ProviderHealth"]
