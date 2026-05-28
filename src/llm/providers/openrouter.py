"""OpenRouter provider implementation using OpenAI Python SDK."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from src.llm.providers.base import BaseProvider, LLMResponse, LLMToolCall, ProviderHealth

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseProvider):
    def __init__(self, api_key: str):
        super().__init__(name="openrouter")
        try:
            from openai import AsyncOpenAI

            self.AsyncOpenAI = AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "Please install the 'openai' package to use OpenRouter provider"
            ) from exc

        self.client = self.AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    async def generate(self, prompt: str, model: str | None = None, **kwargs) -> LLMResponse:
        model = model or os.getenv("OPENROUTER_MODEL", "tencent/hy3-preview")

        system_instruction = kwargs.get("system_instruction")
        response_schema = kwargs.get("response_schema")

        messages: list[dict[str, str]] = []
        if system_instruction:
            messages.append({"role": "system", "content": str(system_instruction)})

        if response_schema:
            try:
                schema_text = json.dumps(response_schema, ensure_ascii=True)
            except Exception:  # pragma: no cover
                schema_text = str(response_schema)
            schema_prompt = (
                "Return ONLY valid JSON (no markdown) that matches this JSON schema:\n"
                f"{schema_text}\n"
            )
            if messages and messages[0]["role"] == "system":
                messages[0]["content"] = f"{messages[0]['content']}\n\n{schema_prompt}"
            else:
                messages.append({"role": "system", "content": schema_prompt})

        messages.append({"role": "user", "content": prompt})

        # Append previous responses mimicking conversational memory if present
        # This is simplified for typical use-cases
        previous_response = kwargs.get("previous_response")
        if previous_response:
            pass  # TODO: properly implement conversational turns if needed by legacy

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                temperature=kwargs.get("temperature", 0.0),
                max_tokens=kwargs.get("max_output_tokens", 4096),
            )
        except Exception as e:
            logger.exception("OpenRouter generation failed")
            raise e from None

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
            if response.choices and len(response.choices) > 0:
                text = response.choices[0].message.content or ""
        except Exception:
            text = ""

        # Extract tool calls if OpenRouter supported and passed them
        tool_calls: list[LLMToolCall] = []
        try:
            if response.choices and response.choices[0].message.tool_calls:
                for tc in response.choices[0].message.tool_calls:
                    if tc.type == "function":
                        tool_calls.append(
                            LLMToolCall(
                                name=tc.function.name,
                                arguments=json.loads(tc.function.arguments)
                                if isinstance(tc.function.arguments, str)
                                else tc.function.arguments,
                                call_id=tc.id,
                            )
                        )
        except Exception:
            pass

        finish_reason = None
        if response.choices:
            finish_reason = getattr(response.choices[0], "finish_reason", None)

        metadata: dict[str, Any] = {}
        if finish_reason:
            metadata["finish_reason"] = finish_reason

        return LLMResponse(
            text=str(text),
            provider=self.name,
            model=model,
            usage=usage_dict,
            metadata=metadata,
            tool_calls=tool_calls,
            raw_content=response,
        )

    async def get_embedding(self, text: str, model: str | None = None) -> list[float]:
        """Generate embedding using OpenRouter."""
        model = model or os.getenv("OPENROUTER_EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")

        try:
            response = await self.client.embeddings.create(input=[text], model=model)
            return response.data[0].embedding
        except Exception as e:
            logger.exception("OpenRouter embedding failed for model '%s'", model)
            raise e from None

    async def health_check(self) -> ProviderHealth:
        """Attempt a lightweight call to verify connectivity."""
        try:
            # We fetch models list as a zero-token overhead healthcheck
            await self.client.models.list()
            return ProviderHealth(name=self.name, healthy=True, details="OK")
        except Exception as exc:
            logger.warning("OpenRouter health check failed: %s", exc)
            return ProviderHealth(name=self.name, healthy=False, last_error=str(exc))
