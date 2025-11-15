"""Minimal multi-provider LLM client used by lifecycle engines.

This is a lightweight, extensible wrapper that supports provider
registration, async `generate()` calls, and a simple fallback policy.

It is intentionally minimal for Phase 2B scaffolding.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseProvider:
    """Abstract provider wrapper interface.

    Concrete provider wrappers should implement `generate()` which returns
    a mapping containing the response text plus optional usage/metadata.
    """

    def __init__(self, name: str):
        self.name = name

    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> LLMResponse:
        raise NotImplementedError()


class LLMClient:
    """Minimal LLM client with provider management and fallback.

    Example usage:
        client = LLMClient()
        client.register_provider('gemini', GeminiProvider(api_key))
        client.register_provider('groq', GroqProvider(api_key))

        resp = await client.generate('What is 2+2?')
        print(resp.text)
    """

    def __init__(self, providers: Optional[Dict[str, BaseProvider]] = None):
        self.providers: Dict[str, BaseProvider] = {}
        # Default preference order (used for fallback)
        self.provider_order = ["gemini", "groq", "mistral"]
        if providers:
            for name, p in providers.items():
                self.register_provider(name, p)

    def register_provider(self, name: str, provider: BaseProvider) -> None:
        self.providers[name] = provider
        if name not in self.provider_order:
            self.provider_order.append(name)

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        provider_priority: Optional[str] = None,
        timeout: Optional[float] = 10.0,
        **kwargs,
    ) -> LLMResponse:
        """Try to generate text using provider priority, fallbacking to other providers.

        Returns first successful response (LLMResponse).
        Raises the last exception if all providers fail.
        """
        order = []
        if provider_priority:
            # ensure priority provider is tried first
            order.append(provider_priority)
        # extend with remaining configured providers in preference order
        order.extend([p for p in self.provider_order if p not in order and p in self.providers])

        last_exc = None
        for name in order:
            provider = self.providers.get(name)
            if not provider:
                continue
            try:
                # Run provider.generate in an executor in case it is sync
                coro = provider.generate(prompt, model=model, **kwargs)
                if asyncio.iscoroutine(coro):
                    task = asyncio.wait_for(coro, timeout=timeout)
                else:
                    # provider.generate returned non-coroutine, wrap with to_thread
                    task = asyncio.wait_for(asyncio.to_thread(lambda: coro), timeout=timeout)

                result: LLMResponse = await task  # type: ignore[assignment]
                # Attach provider name if not present
                if not result.provider:
                    result.provider = name
                return result
            except Exception as e:
                logger.warning("Provider '%s' failed: %s", name, e)
                last_exc = e
                continue

        # If no provider succeeded
        raise last_exc or RuntimeError("No LLM providers configured")


__all__ = ["LLMClient", "BaseProvider", "LLMResponse"]
