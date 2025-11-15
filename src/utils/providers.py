"""Provider wrappers for Google Gemini, Groq, and Mistral used by LLMClient.

This file implements minimal wrappers that adapt provider SDKs to the BaseProvider
interface to be used by the `LLMClient`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from .llm_client import BaseProvider, LLMResponse, ProviderHealth

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: str):
        super().__init__(name="gemini")
        from google import genai
        self.client = genai.Client(api_key=api_key)

    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> LLMResponse:
        # Use thread to call blocking SDK functions
        from google.genai import types

        model = model or "gemini-2.5-flash"

        def sync_call():
            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=kwargs.get("temperature", 0.0),
                    max_output_tokens=kwargs.get("max_output_tokens", 256),
                ),
            )
            return response

        response = await asyncio.to_thread(sync_call)

        usage = getattr(response, "usage_metadata", None)
        usage_dict = None
        if usage:
            usage_dict = {
                "prompt_tokens": getattr(usage, "prompt_token_count", None),
                "response_tokens": getattr(usage, "candidates_token_count", None),
                "total": getattr(usage, "total_token_count", None),
            }

        return LLMResponse(text=getattr(response, "text", ""), provider=self.name, model=model, usage=usage_dict)

    async def health_check(self) -> ProviderHealth:
        """Attempt a lightweight call to verify Gemini connectivity.

        This uses the same SDK call path as `generate` but with a fast
        config and a simple prompt. Providers should return a ProviderHealth with
        `healthy=False` when an exception is raised.
        """
        from google.genai import types

        def sync_call():
            # call a minimally expensive empty prompt (SDK may charge tokens; this is a pragmatic choice for health checks)
            return self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Ping",
                config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=1),
            )

        try:
            await asyncio.to_thread(sync_call)
            return ProviderHealth(name=self.name, healthy=True, details="OK")
        except Exception as exc:
            logger.warning("Gemini health check failed: %s", exc)
            return ProviderHealth(name=self.name, healthy=False, last_error=str(exc))


class GroqProvider(BaseProvider):
    def __init__(self, api_key: str):
        super().__init__(name="groq")
        from groq import Groq
        self.client = Groq(api_key=api_key)

    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> LLMResponse:
        model = model or "llama-3.1-8b-instant"

        def sync_call():
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.0),
                max_tokens=kwargs.get("max_output_tokens", 256),
            )
            return response

        response = await asyncio.to_thread(sync_call)

        usage = getattr(response, "usage", None)
        usage_dict = None
        if usage:
            usage_dict = {
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "response_tokens": getattr(usage, "completion_tokens", None),
                "total": getattr(usage, "total_tokens", None),
            }

        text = ""
        try:
            text = response.choices[0].message.content
        except Exception:
            text = getattr(response, "text", "")

        return LLMResponse(text=text, provider=self.name, model=model, usage=usage_dict)

    async def health_check(self) -> ProviderHealth:
        try:
            def sync_call():
                # Minimal call to validate client
                return self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": "Ping"}],
                    temperature=0.0,
                    max_tokens=1,
                )

            await asyncio.to_thread(sync_call)
            return ProviderHealth(name=self.name, healthy=True, details="OK")
        except Exception as exc:
            logger.warning("Groq health check failed: %s", exc)
            return ProviderHealth(name=self.name, healthy=False, last_error=str(exc))


class MistralProvider(BaseProvider):
    def __init__(self, api_key: str):
        super().__init__(name="mistral")
        from mistralai import Mistral
        self.client = Mistral(api_key=api_key)

    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> LLMResponse:
        model = model or "mistral-small-latest"

        def sync_call():
            response = self.client.chat.complete(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.0),
                max_tokens=kwargs.get("max_output_tokens", 256),
            )
            return response

        response = await asyncio.to_thread(sync_call)

        usage = getattr(response, "usage", None)
        usage_dict = None
        if usage:
            usage_dict = {
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "response_tokens": getattr(usage, "completion_tokens", None),
                "total": getattr(usage, "total_tokens", None),
            }

        text = ""
        try:
            text = response.choices[0].message.content
        except Exception:
            text = getattr(response, "text", "")

        return LLMResponse(text=text, provider=self.name, model=model, usage=usage_dict)

    async def health_check(self) -> ProviderHealth:
        try:
            def sync_call():
                return self.client.chat.complete(
                    model="mistral-small-latest",
                    messages=[{"role": "user", "content": "Ping"}],
                    temperature=0.0,
                    max_tokens=1,
                )

            await asyncio.to_thread(sync_call)
            return ProviderHealth(name=self.name, healthy=True, details="OK")
        except Exception as exc:
            logger.warning("Mistral health check failed: %s", exc)
            return ProviderHealth(name=self.name, healthy=False, last_error=str(exc))


__all__ = ["GeminiProvider", "GroqProvider", "MistralProvider"]
