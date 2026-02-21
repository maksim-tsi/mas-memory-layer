"""RAGAgent implementation with hybrid memory retrieval."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from src.agents.base_agent import BaseAgent
from src.agents.models import RunTurnRequest, RunTurnResponse
from src.llm.client import LLMClient

logger = logging.getLogger(__name__)


class RAGAgent(BaseAgent):
    """Agent that performs retrieval-augmented generation over memory tiers."""

    def __init__(
        self,
        agent_id: str,
        llm_client: LLMClient | None = None,
        memory_system: Any | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(agent_id=agent_id, memory_system=memory_system, config=config)
        self._llm_client = llm_client
        self._model = self._config.get("model", "gemini-3-flash-preview")
        self._top_k = int(self._config.get("top_k", 8))

    async def initialize(self) -> None:
        """Initialize RAGAgent resources."""
        logger.info("Initializing RAGAgent '%s'", self.agent_id)

    async def run_turn(
        self, request: RunTurnRequest, history: list[dict[str, Any]] | None = None
    ) -> RunTurnResponse:
        """Process a single turn with retrieval-augmented context."""
        await self.ensure_initialized()

        user_input = self._extract_latest_user_message(history) or request.content
        retrievals: list[dict[str, Any]] = []
        vector_store = self._get_vector_store()
        if vector_store:
            await self._index_turn(vector_store, request)
            retrievals = await self._query_similar(vector_store, request)
        elif self._memory_system and hasattr(self._memory_system, "query_memory"):
            retrievals = await self._memory_system.query_memory(
                session_id=request.session_id,
                query=user_input,
                limit=self._top_k,
            )
        else:
            logger.warning("No vector store available for RAGAgent '%s'", self.agent_id)

        prompt = self._build_prompt(
            retrievals=retrievals,
            history_text=self._format_history(history),
            user_input=user_input,
        )
        response_text = await self._generate_response(
            prompt,
            agent_metadata={
                "agent.type": "rag",
                "agent.session_id": request.session_id,
                "agent.turn_id": request.turn_id,
            },
        )

        return RunTurnResponse(
            session_id=request.session_id,
            role="assistant",
            content=response_text,
            turn_id=request.turn_id,
        )

    async def health_check(self) -> dict[str, Any]:
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

    async def _generate_response(
        self,
        prompt: str,
        agent_metadata: dict[str, Any] | None = None,
    ) -> str:
        if not self._llm_client:
            logger.warning("No LLM client configured for RAGAgent '%s'", self.agent_id)
            return "I'm unable to respond right now."
        llm_response = await self._llm_client.generate(
            prompt,
            model=self._model,
            agent_metadata=agent_metadata,
        )
        return llm_response.text

    def _build_prompt(
        self, retrievals: list[dict[str, Any]], history_text: str, user_input: str
    ) -> str:
        sections = [
            "You are the MAS RAG Agent. Use retrieved memory snippets to answer the user.",
        ]
        if history_text:
            sections.append("## Conversation History (API Wall)\n" + history_text)
        if retrievals:
            snippets = []
            for item in retrievals:
                content = item.get("content") or item.get("summary") or str(item)
                snippets.append(f"- {content}")
            sections.append("## Retrieved Memory\n" + "\n".join(snippets))
        sections.append(f"## User\n{user_input}")
        sections.append("## Assistant")
        return "\n\n".join(sections)

    def _get_vector_store(self) -> Any | None:
        """Return vector store client for RAG indexing if available."""
        if not self._memory_system:
            return None
        knowledge_manager = getattr(self._memory_system, "knowledge_manager", None)
        if knowledge_manager and hasattr(knowledge_manager, "vector_store"):
            return knowledge_manager.vector_store
        return None

    async def _index_turn(self, vector_store: Any, request: RunTurnRequest) -> None:
        """Index the current turn into the vector store."""
        document = {
            "id": f"{request.session_id}:{request.turn_id}",
            "content": request.content,
            "session_id": request.session_id,
            "role": request.role,
            "turn_id": request.turn_id,
            "created_at": datetime.now(UTC).isoformat(),
        }
        try:
            vector_store.add_documents([document])
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("Failed to index turn in vector store: %s", exc)

    async def _query_similar(
        self, vector_store: Any, request: RunTurnRequest
    ) -> list[dict[str, Any]]:
        """Retrieve similar documents from the vector store."""
        try:
            return vector_store.query_similar(
                query_text=request.content,
                top_k=self._top_k,
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("Vector store query failed: %s", exc)
            return []

    def _format_history(self, history: list[dict[str, Any]] | None) -> str:
        """Format API-provided conversation history for prompt context."""
        if not history:
            return ""
        lines: list[str] = []
        for message in history:
            role = str(message.get("role", "unknown")).upper()
            content = str(message.get("content", ""))
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _extract_latest_user_message(self, history: list[dict[str, Any]] | None) -> str:
        """Extract the most recent user message from history."""
        if not history:
            return ""
        for message in reversed(history):
            if str(message.get("role", "")).lower() == "user":
                return str(message.get("content", ""))
        return str(history[-1].get("content", ""))
