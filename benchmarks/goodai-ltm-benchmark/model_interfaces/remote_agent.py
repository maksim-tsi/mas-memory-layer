import json
import os
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, cast

import requests
from utils.llm import count_tokens_for_model

from model_interfaces.interface import ChatSession


@dataclass
class RemoteMASAgentSession(ChatSession):
    """Chat session that talks to MAS API Wall via OpenAI-compatible endpoint."""

    endpoint: str = field(
        default_factory=lambda: os.environ.get(
            "AGENT_URL", "http://localhost:8080/v1/chat/completions"
        )
    )
    request_timeout: float = 90.0
    max_retries: int = 3
    backoff_seconds: float = 0.5
    model: str = "gemini"
    model_for_cost: str = "gemini-2.5-flash-lite"
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    history: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        env_timeout = os.environ.get("MAS_WRAPPER_TIMEOUT")
        if env_timeout:
            self.request_timeout = float(env_timeout)

    @property
    def name(self) -> str:
        return f"{super().name} - remote"

    def _base_url(self) -> str:
        if self.endpoint.endswith("/v1/chat/completions"):
            return self.endpoint.removesuffix("/v1/chat/completions")
        return self.endpoint.rstrip("/")

    def reply(
        self, user_message: str, agent_response: str | None = None
    ) -> str | tuple[str, dict[str, Any]]:
        if agent_response is not None:
            return agent_response

        self.history.append({"role": "user", "content": user_message})
        payload = {"messages": self.history, "model": self.model}

        response_json = self._post_with_retry(self.endpoint, payload)
        response_text = self._extract_response_text(response_json)
        self.history.append({"role": "assistant", "content": response_text})

        metadata = cast(dict[str, Any], response_json.get("metadata") or {})
        self.last_metadata = metadata
        self._update_costs(user_message, response_text, response_json)
        return response_text, metadata

    def _post_with_retry(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        backoff = self.backoff_seconds
        headers = {"X-Session-Id": self.session_id}

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url, json=payload, headers=headers, timeout=self.request_timeout
                )
                if response.status_code >= 500:
                    raise RuntimeError(f"Server error {response.status_code}: {response.text}")
                if response.status_code >= 400:
                    raise RuntimeError(f"Request failed {response.status_code}: {response.text}")
                return cast(dict[str, Any], response.json())
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries - 1:
                    break
                time.sleep(backoff)
                backoff *= 2

        raise RuntimeError(f"Failed to call MAS API Wall: {last_error}")

    def _extract_response_text(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            return str(content)
        return str(payload.get("content", ""))

    def _update_costs(self, prompt: str, response: str, payload: dict[str, Any]) -> None:
        if self.is_local:
            return

        usage = payload.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens")
        response_tokens = usage.get("completion_tokens")
        if prompt_tokens is None or response_tokens is None:
            try:
                prompt_tokens = count_tokens_for_model(text=prompt)
                response_tokens = count_tokens_for_model(text=response)
            except Exception:
                prompt_tokens = len(prompt.split())
                response_tokens = len(response.split())

        cost_in = float(os.environ.get("MAS_WRAPPER_COST_IN", "0.000001"))
        cost_out = float(os.environ.get("MAS_WRAPPER_COST_OUT", "0.000001"))
        estimated = (float(prompt_tokens) * cost_in) + (float(response_tokens) * cost_out)
        self.costs_usd += max(estimated, 1e-9)

    def reset(self) -> None:
        self.session_id = uuid.uuid4().hex
        self.history = []
        reset_url = f"{self._base_url()}/control/session/reset"
        headers = {"X-Session-Id": self.session_id}
        with suppress(Exception):
            requests.post(reset_url, headers=headers, timeout=self.request_timeout)

    def save(self) -> None:
        fname = self.save_path.joinpath("session.json")
        payload = {
            "session_id": self.session_id,
            "endpoint": self.endpoint,
            "model": self.model,
            "history": self.history,
        }
        with open(fname, "w") as fd:
            json.dump(payload, fd)

    def load(self) -> None:
        fname = self.save_path.joinpath("session.json")
        if not fname.exists():
            return
        with open(fname) as fd:
            payload = json.load(fd)
        self.session_id = payload.get("session_id", self.session_id)
        self.endpoint = payload.get("endpoint", self.endpoint)
        self.model = payload.get("model", self.model)
        self.history = payload.get("history", self.history)
