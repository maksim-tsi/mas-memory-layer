"""OpenRouter provider implementation using OpenAI Python SDK."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from src.llm.providers.base import BaseProvider, LLMResponse, LLMToolCall, ProviderHealth

logger = logging.getLogger(__name__)

DEFAULT_OPENROUTER_MAX_OUTPUT_TOKENS = 8192
DEFAULT_OPENROUTER_REASONING_EFFORT = "low"
DEFAULT_OPENROUTER_REASONING_EXCLUDE = True


class OpenRouterEmptyCompletionError(RuntimeError):
    """Raised when OpenRouter returns no text because the completion budget was exhausted."""


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
        max_output_tokens = _resolve_max_output_tokens(kwargs.get("max_output_tokens"))
        reasoning_config = _resolve_reasoning_config(model)

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
            request_kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.0),
                "max_completion_tokens": max_output_tokens,
            }
            if reasoning_config:
                request_kwargs["extra_body"] = {"reasoning": reasoning_config}

            try:
                response = await self.client.chat.completions.create(**request_kwargs)
            except Exception as exc:
                if not _looks_like_max_completion_tokens_rejection(exc):
                    raise
                logger.warning(
                    "OpenRouter rejected max_completion_tokens; retrying with deprecated max_tokens."
                )
                request_kwargs.pop("max_completion_tokens", None)
                request_kwargs["max_tokens"] = max_output_tokens
                response = await self.client.chat.completions.create(**request_kwargs)
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
            completion_details = getattr(usage, "completion_tokens_details", None)
            if completion_details is not None:
                usage_dict["completion_tokens_details"] = _sdk_object_to_dict(
                    completion_details
                )
            prompt_details = getattr(usage, "prompt_tokens_details", None)
            if prompt_details is not None:
                usage_dict["prompt_tokens_details"] = _sdk_object_to_dict(prompt_details)

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

        metadata: dict[str, Any] = {
            "model": getattr(response, "model", model),
            "max_completion_tokens": max_output_tokens,
        }
        if finish_reason:
            metadata["finish_reason"] = finish_reason
        if reasoning_config:
            metadata["reasoning"] = reasoning_config

        if not text and not tool_calls and finish_reason == "length":
            raise OpenRouterEmptyCompletionError(
                "OpenRouter returned empty content with finish_reason=length; "
                f"increase MAS_MAX_OUTPUT_TOKENS or reduce reasoning for model '{model}'."
            )

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


def _resolve_max_output_tokens(explicit: Any) -> int:
    if explicit not in (None, ""):
        return int(explicit)
    configured = os.getenv("MAS_MAX_OUTPUT_TOKENS")
    if configured not in (None, ""):
        return int(configured)
    return DEFAULT_OPENROUTER_MAX_OUTPUT_TOKENS


def _resolve_reasoning_config(model: str) -> dict[str, Any] | None:
    if "tencent/hy3-preview" not in model:
        return None

    effort = os.getenv("OPENROUTER_REASONING_EFFORT", DEFAULT_OPENROUTER_REASONING_EFFORT)
    effort = effort.strip().lower()
    exclude = _read_bool_env("OPENROUTER_REASONING_EXCLUDE", DEFAULT_OPENROUTER_REASONING_EXCLUDE)
    config: dict[str, Any] = {"exclude": exclude}
    if effort:
        config["effort"] = effort
    return config


def _read_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _looks_like_max_completion_tokens_rejection(exc: Exception) -> bool:
    message = str(exc).lower()
    return "max_completion_tokens" in message and (
        "unsupported" in message
        or "unrecognized" in message
        or "unknown" in message
        or "extra" in message
        or "not permitted" in message
    )


def _sdk_object_to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        return dumped if isinstance(dumped, dict) else {}
    if hasattr(value, "to_dict"):
        dumped = value.to_dict()
        return dumped if isinstance(dumped, dict) else {}
    if hasattr(value, "__dict__"):
        return {key: item for key, item in vars(value).items() if not key.startswith("_")}
    return {}
