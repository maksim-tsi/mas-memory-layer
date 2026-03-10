"""Gemini provider implementation using Google GenAI SDK.

This module implements the Gemini provider wrapper that adapts the Google GenAI SDK
to the BaseProvider interface.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
from collections.abc import Sequence
from typing import Any

from src.llm.providers.base import BaseProvider, LLMResponse, LLMToolCall, ProviderHealth

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
            contents = kwargs.get("contents")
            if contents is None:
                contents = self._build_contents(
                    types=types,
                    prompt=prompt,
                    previous_response=kwargs.get("previous_response"),
                    tool_results=kwargs.get("tool_results"),
                )

            tool_declarations = self._normalize_tool_declarations(kwargs.get("tools"))
            default_temperature = 1.0 if tool_declarations and model.startswith("gemini-3") else 0.0

            # Build config parameters
            config_params = {
                "temperature": kwargs.get("temperature", default_temperature),
                "max_output_tokens": kwargs.get("max_output_tokens", 8192),
                "automatic_function_calling": {"disable": True, "maximum_remote_calls": None},
            }

            if tool_declarations:
                config_params["tools"] = [types.Tool(function_declarations=tool_declarations)]

            tool_mode = kwargs.get("tool_calling_mode")
            allowed_function_names = kwargs.get("allowed_function_names")
            if tool_mode or allowed_function_names:
                config_params["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=tool_mode or "AUTO",
                        allowed_function_names=allowed_function_names,
                    )
                )

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

        tool_calls = self._extract_tool_calls(response)
        raw_content = self._extract_raw_content(response)
        metadata: dict[str, Any] = {}
        finish_reason = self._extract_finish_reason(response)
        if finish_reason:
            metadata["finish_reason"] = finish_reason

        return LLMResponse(
            text=getattr(response, "text", ""),
            provider=self.name,
            model=model,
            usage=usage_dict,
            metadata=metadata,
            tool_calls=tool_calls,
            raw_content=raw_content,
        )

    def _build_contents(
        self,
        *,
        types: Any,
        prompt: str,
        previous_response: Any | None,
        tool_results: Sequence[dict[str, Any]] | None,
    ) -> list[Any]:
        contents: list[Any] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            )
        ]
        if previous_response is not None:
            contents.append(previous_response)
        for tool_result in tool_results or []:
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=str(tool_result["name"]),
                            response=tool_result.get("response", {}),
                        )
                    ],
                )
            )
        return contents

    def _normalize_tool_declarations(self, tools: Any) -> list[dict[str, Any]]:
        if not tools:
            return []
        if not isinstance(tools, Sequence) or isinstance(tools, str | bytes):
            raise TypeError("Gemini tools must be provided as a sequence of function declarations")

        declarations: list[dict[str, Any]] = []
        for tool in tools:
            if isinstance(tool, dict):
                declarations.append(tool)
                continue

            to_json_dict = getattr(tool, "to_json_dict", None)
            if callable(to_json_dict):
                declaration = to_json_dict()
                if isinstance(declaration, dict):
                    declarations.append(declaration)
                    continue

            raise TypeError("Gemini tools must be dict declarations or SDK declarations")
        return declarations

    def _extract_tool_calls(self, response: Any) -> list[LLMToolCall]:
        function_calls = getattr(response, "function_calls", None)
        if function_calls:
            return [self._build_tool_call(function_call) for function_call in function_calls]

        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return []

        content = getattr(candidates[0], "content", None)
        parts = getattr(content, "parts", None) or []
        tool_calls: list[LLMToolCall] = []
        for part in parts:
            function_call = getattr(part, "function_call", None)
            if function_call:
                tool_calls.append(self._build_tool_call(function_call))
        return tool_calls

    def _build_tool_call(self, function_call: Any) -> LLMToolCall:
        args = getattr(function_call, "args", None) or {}
        if not isinstance(args, dict):
            args = dict(args)

        call_id = (
            getattr(function_call, "id", None)
            or getattr(function_call, "call_id", None)
            or getattr(function_call, "tool_use_id", None)
        )
        return LLMToolCall(
            name=str(getattr(function_call, "name", "")),
            arguments=args,
            call_id=str(call_id) if call_id is not None else None,
        )

    def _extract_raw_content(self, response: Any) -> Any | None:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return None
        return getattr(candidates[0], "content", None)

    def _extract_finish_reason(self, response: Any) -> str | None:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return None
        finish_reason = getattr(candidates[0], "finish_reason", None)
        if finish_reason is None:
            return None
        return str(finish_reason)

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
        health_model = os.getenv("MAS_GEMINI_HEALTH_MODEL", "gemini-3-flash-preview")

        def sync_call():
            # call a minimally expensive empty prompt (SDK may charge tokens; this is a pragmatic choice for health checks)
            return self.client.models.generate_content(
                model=health_model,
                contents="Ping",
                config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=1),
            )

        try:
            await asyncio.to_thread(sync_call)
            return ProviderHealth(name=self.name, healthy=True, details="OK")
        except Exception as exc:
            logger.warning("Gemini health check failed: %s", exc)
            return ProviderHealth(name=self.name, healthy=False, last_error=str(exc))
