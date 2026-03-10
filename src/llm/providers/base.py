"""Base provider interface for the orchestrating client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMToolCall:
    """Structured tool call returned by a provider."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str | None = None


@dataclass
class LLMResponse:
    """Standardized response returned from every provider."""

    text: str
    provider: str
    model: str | None = None
    usage: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    raw_content: Any | None = None


@dataclass(frozen=True)
class ProviderHealth:
    """Runtime health report returned by each provider wrapper."""

    name: str
    healthy: bool
    details: str | None = None
    last_error: str | None = None


class BaseProvider:
    """Abstract provider wrapper interface for the orchestrating client."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def generate(self, prompt: str, model: str | None = None, **kwargs: Any) -> LLMResponse:
        """Generate text for the supplied prompt."""
        raise NotImplementedError()

    async def get_embedding(
        self, text: str, model: str | None = None, output_dimensionality: int = 768
    ) -> list[float]:
        """Generate embedding for the supplied text.

        Optional method; not all providers support embeddings.
        """
        raise NotImplementedError("This provider does not support embeddings.")

    async def health_check(self) -> ProviderHealth:
        """Return a lightweight health signal that lifecycle engines can inspect."""
        return ProviderHealth(name=self.name, healthy=True, details="Provider configured")
