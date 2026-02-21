"""Gemini provider implementation using Google GenAI SDK.

This module implements the Gemini provider wrapper that adapts the Google GenAI SDK
to the BaseProvider interface.
"""

from __future__ import annotations

import asyncio
import importlib
import logging

from src.llm.providers.base import BaseProvider, LLMResponse, ProviderHealth

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: str):
        super().__init__(name="gemini")
        genai = importlib.import_module("google.genai")

        self.client = genai.Client(api_key=api_key)

    async def generate(self, prompt: str, model: str | None = None, **kwargs) -> LLMResponse:
        # Use thread to call blocking SDK functions
        types = importlib.import_module("google.genai.types")

        model = model or "gemini-3-flash-preview"

        def sync_call():
            # Build content
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                )
            ]

            # Build config parameters
            config_params = {
                "temperature": kwargs.get("temperature", 0.0),
                "max_output_tokens": kwargs.get("max_output_tokens", 8192),
                "automatic_function_calling": {"disable": True, "maximum_remote_calls": None},
            }

            # Add system instruction if provided
            system_instruction = kwargs.get("system_instruction")
            if system_instruction:
                config_params["system_instruction"] = [
                    types.Part.from_text(text=system_instruction)
                ]

            # Add structured output if response_schema provided
            response_schema = kwargs.get("response_schema")
            if response_schema:
                config_params["response_mime_type"] = "application/json"
                config_params["response_schema"] = response_schema

            config = types.GenerateContentConfig(**config_params)

            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            return response

        try:
            response = await asyncio.to_thread(sync_call)
        except Exception:
            logger.exception("Gemini generation failed")
            raise

        usage = getattr(response, "usage_metadata", None)
        usage_dict = None
        if usage:
            usage_dict = {
                "prompt_tokens": getattr(usage, "prompt_token_count", None),
                "response_tokens": getattr(usage, "candidates_token_count", None),
                "total": getattr(usage, "total_token_count", None),
            }

        return LLMResponse(
            text=getattr(response, "text", ""), provider=self.name, model=model, usage=usage_dict
        )

    async def get_embedding(
        self, text: str, model: str | None = None, output_dimensionality: int = 768
    ) -> list[float]:
        """Generate embedding using Gemini embedding model.

        Args:
            text: Text to embed.
            model: Embedding model name (default: text-embedding-004).
            output_dimensionality: Output vector dimension (default: 768).
                Gemini supports 128-3072; recommended: 768, 1536, 3072.

        Returns:
            List of floats representing the embedding vector.
        """
        types = importlib.import_module("google.genai.types")

        model = model or "text-embedding-004"

        def sync_call():
            response = self.client.models.embed_content(
                model=model,
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=output_dimensionality),
            )
            return response

        try:
            response = await asyncio.to_thread(sync_call)
            logger.debug(
                "Gemini embedding generated: model=%s, dim=%d",
                model,
                len(response.embeddings[0].values),
            )
            # Response structure: response.embeddings[0].values
            return list(response.embeddings[0].values)
        except Exception:
            logger.exception("Gemini embedding failed")
            raise

    async def health_check(self) -> ProviderHealth:
        """Attempt a lightweight call to verify Gemini connectivity.

        This uses the same SDK call path as `generate` but with a fast
        config and a simple prompt. Providers should return a ProviderHealth with
        `healthy=False` when an exception is raised.
        """
        types = importlib.import_module("google.genai.types")

        def sync_call():
            # call a minimally expensive empty prompt (SDK may charge tokens; this is a pragmatic choice for health checks)
            return self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents="Ping",
                config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=1),
            )

        try:
            await asyncio.to_thread(sync_call)
            return ProviderHealth(name=self.name, healthy=True, details="OK")
        except Exception as exc:
            logger.warning("Gemini health check failed: %s", exc)
            return ProviderHealth(name=self.name, healthy=False, last_error=str(exc))
