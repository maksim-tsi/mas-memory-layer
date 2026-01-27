"""FullContextAgent implementation using extended context windows."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List

from src.agents.base_agent import BaseAgent
from src.agents.models import RunTurnRequest, RunTurnResponse
from src.memory.models import ContextBlock
from src.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class FullContextAgent(BaseAgent):
    """Agent that uses expanded L1/L2 context for full-context baselines."""

    MAX_TOKENS = 120_000
    MIN_RECENT_TURNS = 10

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
                context_text = self._build_context_from_block(
                    context_block,
                    user_input=request.content,
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

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count using conservative heuristic (4 chars/token)."""
        return int(len(text) * 0.25)

    def _build_context_from_block(self, context_block: ContextBlock, user_input: str) -> str:
        """Build truncated context text from a context block."""
        turn_lines = self._format_turns(context_block.recent_turns)
        fact_lines = self._format_facts(context_block.significant_facts)

        turn_lines = self._truncate_turns_if_needed(turn_lines, fact_lines, user_input)

        sections: List[str] = []
        if turn_lines:
            sections.append("## Recent Conversation")
            sections.extend(turn_lines)
        if fact_lines:
            sections.append("\n## Key Facts (Working Memory)")
            sections.extend(fact_lines)
        return "\n".join(sections)

    def _format_turns(self, recent_turns: List[Dict[str, Any]]) -> List[str]:
        """Format recent turns for full-context prompts."""
        formatted: List[str] = []
        for turn in recent_turns:
            role = turn.get("role", "unknown").upper()
            content = turn.get("content", "")
            if self._include_metadata:
                timestamp = turn.get("timestamp", "N/A")
                formatted.append(f"[{timestamp}] {role}: {content}")
            else:
                formatted.append(f"{role}: {content}")
        return formatted

    def _format_facts(self, facts: List[Any]) -> List[str]:
        """Format fact entries for prompt context."""
        formatted: List[str] = []
        for fact in facts:
            content = getattr(fact, "content", None)
            if content is None and isinstance(fact, dict):
                content = fact.get("content", "")
            if self._include_metadata:
                ciar = getattr(fact, "ciar_score", None)
                ciar_text = f" (CIAR: {ciar:.2f})" if isinstance(ciar, float) else ""
                formatted.append(f"{content}{ciar_text}")
            else:
                formatted.append(f"{content}")
        return formatted

    def _truncate_turns_if_needed(
        self,
        turn_lines: List[str],
        fact_lines: List[str],
        user_input: str,
    ) -> List[str]:
        """Truncate oldest turns if context exceeds max token budget."""
        if not turn_lines:
            return turn_lines

        total_text = "\n".join(turn_lines + fact_lines + [user_input])
        estimated_tokens = self._estimate_tokens(total_text)
        if estimated_tokens <= self.MAX_TOKENS:
            return turn_lines

        truncated = list(turn_lines)
        while (
            len(truncated) > self.MIN_RECENT_TURNS
            and self._estimate_tokens("\n".join(truncated + fact_lines + [user_input])) > self.MAX_TOKENS
        ):
            truncated.pop(0)

        logger.warning(
            "Context overflow: truncated from %d to %d turns (estimated_tokens=%d)",
            len(turn_lines),
            len(truncated),
            estimated_tokens,
        )
        return truncated
