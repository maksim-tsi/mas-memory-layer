"""Abstract base class for GoodAI-compatible MAS agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from src.agents.models import RunTurnRequest, RunTurnResponse

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class defining the MAS agent interface.

    Args:
        agent_id: Stable identifier for the agent implementation.
        memory_system: Optional reference to the unified memory system.
        config: Optional configuration dictionary.
    """

    def __init__(
        self,
        agent_id: str,
        memory_system: Any | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id must be a non-empty string.")
        self._agent_id = agent_id.strip()
        self._memory_system = memory_system
        self._config = config or {}
        self._initialized = False

    @property
    def agent_id(self) -> str:
        """Return the agent identifier."""
        return self._agent_id

    @property
    def config(self) -> dict[str, Any]:
        """Return the agent configuration dictionary."""
        return self._config

    @property
    def memory_system(self) -> Any | None:
        """Return the memory system reference, if available."""
        return self._memory_system

    async def ensure_initialized(self) -> None:
        """Initialize the agent if not already initialized."""
        if not self._initialized:
            await self.initialize()
            self._initialized = True

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize any required resources for the agent."""

    @abstractmethod
    async def run_turn(
        self, request: RunTurnRequest, history: list[dict[str, Any]] | None = None
    ) -> RunTurnResponse:
        """Process a single conversation turn.

        Args:
            request: Input turn payload.
            history: Optional full conversation history for the session.

        Returns:
            Response payload for the turn.
        """

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Return health status information for the agent and dependencies."""

    @abstractmethod
    async def cleanup_session(self, session_id: str) -> None:
        """Clean up session-specific state.

        Args:
            session_id: Session identifier to clean up.
        """

    async def close(self) -> None:
        """Close agent resources if applicable."""
        logger.debug("Closing agent %s", self._agent_id)
