"""FullContextAgent implementation using extended context windows."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.agents.base_agent import BaseAgent
from src.agents.models import RunTurnRequest, RunTurnResponse
from src.memory.models import ContextBlock
from src.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class FullContextAgent(BaseAgent):
    """Agent that uses expanded L1/L2 context for full-context baselines."""

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
        self._max_turns = int(self._config.get("max_turns", 100))
        self._max_facts = int(self._config.get("max_facts", 20))
        self._min_ciar = float(self._config.get("min_ciar", 0.4))
        self._include_metadata = bool(self._config.get("include_metadata", False))

    async def initialize(self) -> None:
        """Initialize FullContextAgent resources."""
        logger.info("Initializing FullContextAgent '%s'", self.agent_id)

    async def run_turn(self, request: RunTurnRequest) -> RunTurnResponse:
        """Process a single turn with expanded context retrieval."""
        await self.ensure_initialized()

        context_text = ""
        if self._memory_system and hasattr(self._memory_system, "get_context_block"):
            context_block = await self._memory_system.get_context_block(
                session_id=request.session_id,
                min_ciar=self._min_ciar,
                max_turns=self._max_turns,
                max_facts=self._max_facts,
            )
            if isinstance(context_block, ContextBlock):
                context_text = context_block.to_prompt_string(
                    include_metadata=self._include_metadata
                )
            elif hasattr(context_block, "to_prompt_string"):
                context_text = context_block.to_prompt_string(
                    include_metadata=self._include_metadata
                )

        prompt = self._build_prompt(context_text=context_text, user_input=request.content)
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
            logger.warning("No LLM client configured for FullContextAgent '%s'", self.agent_id)
            return "I'm unable to respond right now."
        llm_response = await self._llm_client.generate(prompt, model=self._model)
        return llm_response.text

    def _build_prompt(self, context_text: str, user_input: str) -> str:
        sections = [
            "You are the MAS Full-Context Agent. Use the complete context to answer.",
        ]
        if context_text:
            sections.append("## Full Context\n" + context_text)
        sections.append(f"## User\n{user_input}")
        sections.append("## Assistant")
        return "\n\n".join(sections)
