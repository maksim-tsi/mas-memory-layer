"""MemoryAgent implementation for GoodAI-compatible runs."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List, cast

from langgraph.graph import StateGraph, END

from src.agents.base_agent import BaseAgent
from src.agents.models import RunTurnRequest, RunTurnResponse
from src.agents.runtime import AgentState
from src.agents.tools.unified_tools import UNIFIED_TOOLS
from src.memory.models import ContextBlock
from src.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    """Agent that uses LangGraph state to retrieve and reason over memory tiers."""

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
        self._min_ciar = float(self._config.get("min_ciar", 0.6))
        self._max_turns = int(self._config.get("max_turns", 20))
        self._max_facts = int(self._config.get("max_facts", 10))
        self._tools = list(UNIFIED_TOOLS)
        self._graph = self._build_graph()

    async def initialize(self) -> None:
        """Initialize MemoryAgent resources."""
        logger.info("Initializing MemoryAgent '%s'", self.agent_id)

    async def run_turn(self, request: RunTurnRequest) -> RunTurnResponse:
        """Process a single conversation turn with memory retrieval and updates."""
        await self.ensure_initialized()

        initial_state: AgentState = {
            "messages": [{"role": request.role, "content": request.content}],
            "session_id": request.session_id,
            "turn_id": request.turn_id,
            "active_context": [],
            "working_facts": [],
            "episodic_chunks": [],
            "entity_graph": {},
            "semantic_knowledge": [],
            "response": "",
            "confidence": 0.0,
        }

        result_state = await self._run_graph(initial_state)
        response_text = result_state.get("response") or "I'm unable to respond right now."

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

    def _build_graph(self) -> Any:
        """Build the LangGraph execution graph for the agent."""
        workflow = StateGraph(AgentState)
        workflow.add_node("perceive", self._perceive_node)
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("reason", self._reason_node)
        workflow.add_node("update", self._update_node)
        workflow.add_node("respond", self._respond_node)

        workflow.set_entry_point("perceive")
        workflow.add_edge("perceive", "retrieve")
        workflow.add_edge("retrieve", "reason")
        workflow.add_edge("reason", "update")
        workflow.add_edge("update", "respond")
        workflow.add_edge("respond", END)

        return workflow.compile()

    async def _run_graph(self, state: AgentState) -> AgentState:
        """Execute the LangGraph pipeline asynchronously."""
        if hasattr(self._graph, "ainvoke"):
            return cast(AgentState, await self._graph.ainvoke(state))
        return cast(AgentState, await asyncio.to_thread(self._graph.invoke, state))

    async def _perceive_node(self, state: AgentState) -> AgentState:
        """Parse incoming message and ensure state defaults."""
        return self._ensure_state_defaults(state)

    async def _retrieve_node(self, state: AgentState) -> AgentState:
        """Retrieve L1/L2/L3/L4 context for the current session."""
        state = self._ensure_state_defaults(state)
        if not self._memory_system:
            return state

        session_id = state.get("session_id", "")
        user_query = self._extract_user_message(state)

        context_block = None
        if hasattr(self._memory_system, "get_context_block"):
            try:
                context_block = await self._memory_system.get_context_block(
                    session_id=session_id,
                    min_ciar=self._min_ciar,
                    max_turns=self._max_turns,
                    max_facts=self._max_facts,
                )
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.warning("Failed to retrieve context block: %s", exc)

        if isinstance(context_block, ContextBlock):
            state["active_context"] = self._format_recent_turns(context_block.recent_turns)
            state["working_facts"] = list(context_block.significant_facts)
            state["episodic_chunks"] = list(context_block.episode_summaries)
            state["semantic_knowledge"] = list(context_block.knowledge_snippets)
        elif context_block and hasattr(context_block, "recent_turns"):
            state["active_context"] = self._format_recent_turns(getattr(context_block, "recent_turns", []))
            state["working_facts"] = list(getattr(context_block, "significant_facts", []))
            state["episodic_chunks"] = list(getattr(context_block, "episode_summaries", []))
            state["semantic_knowledge"] = list(getattr(context_block, "knowledge_snippets", []))

        if user_query and hasattr(self._memory_system, "query_memory"):
            try:
                results = await self._memory_system.query_memory(
                    session_id=session_id,
                    query=user_query,
                    limit=self._max_facts,
                )
                self._merge_query_results(state, results)
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.warning("Failed to query memory tiers: %s", exc)

        return state

    async def _reason_node(self, state: AgentState) -> AgentState:
        """Synthesize context and generate response via LLM."""
        state = self._ensure_state_defaults(state)
        user_input = self._extract_user_message(state)
        context_text = self._format_context(state)
        prompt = self._build_prompt(context_text=context_text, user_input=user_input)
        response_text = await self._generate_response(prompt)
        state["response"] = response_text
        state["confidence"] = 0.0
        return state

    async def _update_node(self, state: AgentState) -> AgentState:
        """Write to L1 and trigger promotion cycle if configured."""
        state = self._ensure_state_defaults(state)
        if not self._memory_system or not getattr(self._memory_system, "l1_tier", None):
            return state

        session_id = state.get("session_id", "")
        turn_id = int(state.get("turn_id", 0))
        user_message = self._extract_user_message(state)
        assistant_response = state.get("response", "")

        timestamp = datetime.now(timezone.utc)
        user_turn_id = self._encode_turn_id(turn_id, role="user")
        assistant_turn_id = self._encode_turn_id(turn_id, role="assistant")

        await self._memory_system.l1_tier.store(
            {
                "session_id": session_id,
                "turn_id": user_turn_id,
                "role": "user",
                "content": user_message,
                "timestamp": timestamp,
            }
        )
        await self._memory_system.l1_tier.store(
            {
                "session_id": session_id,
                "turn_id": assistant_turn_id,
                "role": "assistant",
                "content": assistant_response,
                "timestamp": timestamp,
            }
        )

        if hasattr(self._memory_system, "run_promotion_cycle"):
            try:
                asyncio.create_task(self._memory_system.run_promotion_cycle(session_id))
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.warning("Failed to start promotion cycle: %s", exc)

        return state

    async def _respond_node(self, state: AgentState) -> AgentState:
        """Finalize response state."""
        return self._ensure_state_defaults(state)

    async def _generate_response(self, prompt: str) -> str:
        if not self._llm_client:
            logger.warning("No LLM client configured for MemoryAgent '%s'", self.agent_id)
            return "I'm unable to respond right now."
        llm_response = await self._llm_client.generate(prompt, model=self._model)
        return llm_response.text

    def _build_prompt(self, context_text: str, user_input: str) -> str:
        sections = [
            "You are the MAS Memory Agent. Use the provided context to answer the user.",
        ]
        if context_text:
            sections.append("## Context\n" + context_text)
        sections.append(f"## User\n{user_input}")
        sections.append("## Assistant")
        return "\n\n".join(sections)

    def _ensure_state_defaults(self, state: AgentState) -> AgentState:
        """Ensure AgentState contains all required keys."""
        defaults: AgentState = {
            "messages": [],
            "session_id": "",
            "turn_id": 0,
            "active_context": [],
            "working_facts": [],
            "episodic_chunks": [],
            "entity_graph": {},
            "semantic_knowledge": [],
            "response": "",
            "confidence": 0.0,
        }
        merged = {**defaults, **state}
        return cast(AgentState, merged)

    def _extract_user_message(self, state: AgentState) -> str:
        """Extract latest user message from state."""
        messages = state.get("messages", [])
        for message in reversed(messages):
            role = self._get_message_role(message)
            if role == "user":
                return self._get_message_content(message)
        if messages:
            return self._get_message_content(messages[-1])
        return ""

    def _get_message_role(self, message: Any) -> str:
        """Normalize role/type for dict or LangChain message objects."""
        if isinstance(message, dict):
            return message.get("role", "")
        role = getattr(message, "role", None)
        if role:
            return role
        msg_type = getattr(message, "type", None)
        if msg_type in {"human", "user"}:
            return "user"
        if msg_type in {"ai", "assistant"}:
            return "assistant"
        return ""

    def _get_message_content(self, message: Any) -> str:
        """Extract content from dict or LangChain message objects."""
        if isinstance(message, dict):
            return message.get("content", "")
        return getattr(message, "content", "")

    def _format_recent_turns(self, recent_turns: List[Dict[str, Any]]) -> List[str]:
        """Format recent turns for prompt context."""
        formatted: List[str] = []
        for turn in recent_turns:
            role = turn.get("role", "unknown").upper()
            content = turn.get("content", "")
            formatted.append(f"{role}: {content}")
        return formatted

    def _format_context(self, state: AgentState) -> str:
        """Format retrieved context for prompt injection."""
        sections: List[str] = []

        active_context = state.get("active_context", [])
        if active_context:
            sections.append("## Recent Conversation")
            for idx, line in enumerate(active_context, 1):
                sections.append(f"{idx}. {line}")

        working_facts = state.get("working_facts", [])
        if working_facts:
            sections.append("\n## Key Facts (Working Memory)")
            for idx, fact in enumerate(working_facts, 1):
                content = getattr(fact, "content", None)
                if content is None and isinstance(fact, dict):
                    content = fact.get("content", "")
                sections.append(f"{idx}. {content}")

        episodic_chunks = state.get("episodic_chunks", [])
        if episodic_chunks:
            sections.append("\n## Related Episodes (Episodic Memory)")
            for idx, chunk in enumerate(episodic_chunks, 1):
                sections.append(f"{idx}. {chunk}")

        semantic_knowledge = state.get("semantic_knowledge", [])
        if semantic_knowledge:
            sections.append("\n## Relevant Knowledge (Semantic Memory)")
            for idx, knowledge in enumerate(semantic_knowledge, 1):
                content = getattr(knowledge, "content", None)
                if content is None and isinstance(knowledge, dict):
                    content = knowledge.get("content", "")
                sections.append(f"{idx}. {content}")

        return "\n".join(sections)

    def _merge_query_results(self, state: AgentState, results: List[Dict[str, Any]]) -> None:
        """Merge query results into the agent state by tier."""
        for result in results:
            tier = result.get("tier")
            content = result.get("content", "")
            if tier == "L2":
                state["working_facts"].append(result)
            elif tier == "L3":
                if content:
                    state["episodic_chunks"].append(content)
            elif tier == "L4":
                if content:
                    state["semantic_knowledge"].append(content)

    def _encode_turn_id(self, turn_id: int, role: str) -> int:
        """Encode turn IDs to avoid user/assistant collisions in L1 storage."""
        return turn_id * 2 if role == "user" else (turn_id * 2) + 1
