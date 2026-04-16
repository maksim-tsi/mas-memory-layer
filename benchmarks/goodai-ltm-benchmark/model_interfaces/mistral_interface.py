import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from openai import OpenAI
from openai.types.chat import ChatCompletion

from model_interfaces.interface import ChatSession

DEFAULT_MISTRAL_BASE_URL = "https://api.mistral.ai/v1"
DEFAULT_MISTRAL_MODEL = "mistral-large"


@dataclass
class MistralChatSession(ChatSession):
    """OpenAI-compatible Mistral chat session for baseline (no YAAM)."""

    is_local: bool = True
    model: str = field(
        default_factory=lambda: os.getenv("MISTRAL_MODEL", DEFAULT_MISTRAL_MODEL)
    )
    base_url: str = field(
        default_factory=lambda: os.getenv("MISTRAL_API_BASE", DEFAULT_MISTRAL_BASE_URL)
    )
    max_response_tokens: int = field(
        default_factory=lambda: int(os.getenv("MISTRAL_MAX_OUTPUT_TOKENS", "1024"))
    )
    temperature: float = field(
        default_factory=lambda: float(os.getenv("MISTRAL_TEMPERATURE", "0.0"))
    )
    client: OpenAI = field(init=False)
    context: list[dict[str, str]] = field(default_factory=list)

    @property
    def history_path(self) -> Path:
        return self.save_path.joinpath("history.json")

    def __post_init__(self) -> None:
        super().__post_init__()
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY environment variable not set")
        self.client = OpenAI(base_url=self.base_url, api_key=api_key)
        self.reset()

    def reply(self, user_message: str, agent_response: str | None = None) -> str:
        self.context.append({"role": "user", "content": user_message})
        if agent_response is None:
            completion = self._generate_with_retry(self.context)
            response = completion.choices[0].message.content or ""
            self._update_costs(completion)
        else:
            response = agent_response
        self.context.append({"role": "assistant", "content": response})
        time.sleep(0.1)
        return response

    def _generate_with_retry(self, history: list[dict[str, str]]) -> ChatCompletion:
        max_retries = 3
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=cast(Any, history),
                    max_tokens=self.max_response_tokens,
                    temperature=self.temperature,
                )
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    raise
        raise last_exc or RuntimeError("Mistral request failed")

    def _update_costs(self, completion: ChatCompletion) -> None:
        usage = completion.usage
        if not usage:
            return
        cost_in = float(os.getenv("MISTRAL_COST_IN", "0.0"))
        cost_out = float(os.getenv("MISTRAL_COST_OUT", "0.0"))
        prompt_tokens = usage.prompt_tokens or 0
        completion_tokens = usage.completion_tokens or 0
        self.costs_usd += (prompt_tokens * cost_in) + (completion_tokens * cost_out)

    def reset(self) -> None:
        self.context = []

    def save(self) -> None:
        with open(self.history_path, "w", encoding="utf-8") as fd:
            json.dump(self.context, fd)

    def load(self) -> None:
        if self.history_path.exists():
            with open(self.history_path, encoding="utf-8") as fd:
                self.context = cast(list[dict[str, str]], json.load(fd))

    def token_len(self, text: str) -> int:
        return max(1, len(text.split()))
