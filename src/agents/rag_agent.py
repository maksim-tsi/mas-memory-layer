"""RAGAgent implementation with hybrid memory retrieval."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.agents.models import RunTurnRequest, RunTurnResponse
from src.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class RAGAgent(BaseAgent):
    """Agent that performs retrieval-augmented generation over memory tiers."""

    def __init__(
        self,
        agent_id: str,
        llm_client: Optional[LLMClient] = None,
        memory_system: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(agent_id=agent_id, memory_system=memory_system, config=config)
        self._llm_client = llm_client
        self._model = self._config.get("model", "gemini-2.5-flash-lite")
        self._top_k = int(self._config.get("top_k", 8))

    async def initialize(self) -> None:
        """Initialize RAGAgent resources."""
        logger.info("Initializing RAGAgent '%s'", self.agent_id)

    async def run_turn(self, request: RunTurnRequest) -> RunTurnResponse:
        """Process a single turn with retrieval-augmented context."""
        await self.ensure_initialized()

        retrievals: List[Dict[str, Any]] = []
        if self._memory_system and hasattr(self._memory_system, "query_memory"):
            retrievals = await self._memory_system.query_memory(
                session_id=request.session_id,
                query=request.content,
                limit=self._top_k,
            )

        prompt = self._build_prompt(retrievals=retrievals, user_input=request.content)
        response_text = await self._generate_response(prompt)

        return RunTurnResponse(
            session_id=request.session_id,
            role="assistant",
            content=response_text,
            turn_id=request.turn_id,
        )

    async def health_check(self) -> Dict[str, Any]:
        """Return health status for the agent."""
        providers = []
        if self._llm_client:
            providers = list(self._llm_client.available_providers())
        return {
            "status": "healthy",
            "agent_id": self.agent_id,
            "llm_providers": providers,
            "memory_system": self._memory_system is not None,
        }

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up session-specific state if supported by memory system."""
        if self._memory_system and hasattr(self._memory_system, "cleanup_session"):
            await self._memory_system.cleanup_session(session_id)

    async def _generate_response(self, prompt: str) -> str:
        if not self._llm_client:
            logger.warning("No LLM client configured for RAGAgent '%s'", self.agent_id)
            return "I'm unable to respond right now."
        llm_response = await self._llm_client.generate(prompt, model=self._model)
        return llm_response.text

    def _build_prompt(self, retrievals: List[Dict[str, Any]], user_input: str) -> str:
        sections = [
            "You are the MAS RAG Agent. Use retrieved memory snippets to answer the user.",
        ]
        if retrievals:
            snippets = []
            for item in retrievals:
                content = item.get("content") or item.get("summary") or str(item)
                snippets.append(f"- {content}")
            sections.append("## Retrieved Memory\n" + "\n".join(snippets))
        sections.append(f"## User\n{user_input}")
        sections.append("## Assistant")
        return "\n\n".join(sections)
