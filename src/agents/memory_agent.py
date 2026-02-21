"""MemoryAgent implementation for GoodAI-compatible runs."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, cast

from langgraph.graph import END, StateGraph

from src.agents.base_agent import BaseAgent
from src.agents.models import RunTurnRequest, RunTurnResponse
from src.agents.runtime import AgentState
from src.agents.tools.unified_tools import UNIFIED_TOOLS
from src.llm.client import LLMClient
from src.memory.models import ContextBlock, TurnData
from src.skills.loader import SkillLoadError, filter_tools_by_allowed_names, load_skill

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    """Agent that uses LangGraph state to retrieve and reason over memory tiers."""

    def __init__(
        self,
        agent_id: str,
        llm_client: LLMClient | None = None,
        memory_system: Any | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(agent_id=agent_id, memory_system=memory_system, config=config)
        self._llm_client = llm_client
        self._model = self._config.get("model", "gemini-2.5-flash-lite")
        self._agent_variant = str(self._config.get("agent_variant", "baseline"))
        self._skill_wiring_enabled = self._agent_variant.startswith("v1-")
        self._base_system_instruction = self._config.get("system_instruction") or (
            "You are the MAS Memory Agent. You have access to a user's long-term memory. "
            "Always answer the user's questions based on the provided context. "
            "Be direct and helpful."
        )
        self._config["system_instruction"] = self._base_system_instruction
        self._min_ciar = float(self._config.get("min_ciar", 0.6))
        self._max_turns = int(self._config.get("max_turns", 20))
        self._max_facts = int(self._config.get("max_facts", 10))
        self._tools = list(UNIFIED_TOOLS)
        self._graph = self._build_graph()
        self._promotion_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        """Initialize MemoryAgent resources."""
        logger.info("Initializing MemoryAgent '%s'", self.agent_id)

    async def run_turn(
        self, request: RunTurnRequest, history: list[dict[str, Any]] | None = None
    ) -> RunTurnResponse:
        """Process a single conversation turn with memory retrieval and updates."""
        await self.ensure_initialized()

        messages = (
            list(history) if history else [{"role": request.role, "content": request.content}]
        )
        initial_state: AgentState = {
            "messages": messages,
            "session_id": request.session_id,
            "turn_id": request.turn_id,
            "metadata": dict(request.metadata or {}),
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
            metadata=result_state.get("metadata"),
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
            state["active_context"] = self._format_recent_turns(
                getattr(context_block, "recent_turns", [])
            )
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
        skill_context = self._prepare_skill_context(user_input=user_input, state=state)
        context_text = self._format_context(state)
        turn_id = int(state.get("turn_id", 0))
        prompt = self._build_prompt(
            context_text=context_text, user_input=user_input, turn_id=turn_id
        )
        response_text = await self._generate_response(
            prompt,
            agent_metadata=self._build_agent_metadata(state),
            system_instruction=skill_context["system_instruction"],
        )
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
        metadata = state.get("metadata", {})
        if metadata.get("skip_l1_write"):
            return state
        user_message = self._extract_user_message(state)
        assistant_response = state.get("response", "")

        timestamp = datetime.now(UTC)
        user_turn_id = self._encode_turn_id(turn_id, role="user")
        assistant_turn_id = self._encode_turn_id(turn_id, role="assistant")

        user_turn = TurnData(
            session_id=session_id,
            turn_id=str(user_turn_id),
            role="user",
            content=user_message,
            timestamp=timestamp,
        )
        assistant_turn = TurnData(
            session_id=session_id,
            turn_id=str(assistant_turn_id),
            role="assistant",
            content=assistant_response,
            timestamp=timestamp,
        )
        await self._memory_system.l1_tier.store(user_turn)
        await self._memory_system.l1_tier.store(assistant_turn)

        if hasattr(self._memory_system, "run_promotion_cycle"):
            try:
                logger.info(f"DEBUG: Spawning promotion task for session {session_id}")
                self._promotion_task = asyncio.create_task(
                    self._memory_system.run_promotion_cycle(session_id)
                )
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.warning("Failed to start promotion cycle: %s", exc)

        return state

    async def _respond_node(self, state: AgentState) -> AgentState:
        """Finalize response state."""
        return self._ensure_state_defaults(state)

    async def _generate_response(
        self,
        prompt: str,
        agent_metadata: dict[str, Any] | None = None,
        system_instruction: str | None = None,
    ) -> str:
        if not self._llm_client:
            logger.warning("No LLM client configured for MemoryAgent '%s'", self.agent_id)
            return "I'm unable to respond right now."
        llm_response = await self._llm_client.generate(
            prompt,
            model=self._model,
            agent_metadata=agent_metadata,
            system_instruction=system_instruction or self._config.get("system_instruction"),
        )
        return llm_response.text

    def _prepare_skill_context(self, user_input: str, state: AgentState) -> dict[str, Any]:
        """Select/load a skill for v1 variants and record toolset gating metadata."""
        metadata = state.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
            state["metadata"] = metadata

        metadata["agent_variant"] = self._agent_variant
        if not self._skill_wiring_enabled:
            return {"system_instruction": self._base_system_instruction}

        selected_slug = self._select_skill_slug(metadata=metadata)
        metadata["skill_slug"] = selected_slug

        try:
            skill = load_skill(selected_slug)
        except SkillLoadError as exc:
            logger.warning("Failed to load skill '%s': %s", selected_slug, exc)
            metadata["skill_load_error"] = str(exc)
            return {"system_instruction": self._base_system_instruction}

        allowed_tools = list(skill.manifest.allowed_tools)
        gated_tools = filter_tools_by_allowed_names(self._tools, allowed_tools)
        gated_tool_names = [getattr(tool, "name", str(tool)) for tool in gated_tools]

        metadata["skill_name"] = skill.manifest.name
        metadata["skill_namespace"] = skill.namespace
        metadata["allowed_tools"] = allowed_tools
        metadata["gated_tool_names"] = gated_tool_names
        metadata["skill_wiring_mode"] = "v1-min-skillwiring"

        system_instruction = (
            f"{self._base_system_instruction}\n\n"
            "## Active Skill\n"
            f"Skill slug: {selected_slug}\n"
            f"Skill name: {skill.manifest.name}\n"
            f"Allowed tools: {', '.join(allowed_tools) if allowed_tools else '(none)'}\n\n"
            "## Skill Body\n"
            f"{skill.body}"
        )
        return {"system_instruction": system_instruction}

    def _select_skill_slug(self, metadata: dict[str, Any]) -> str:
        """Select a runtime skill slug for the current user turn.

        v1 uses explicit executive-function routing by default (`skill-selection`).
        Callers can override by providing `skill_slug` in metadata.
        """
        requested_slug = metadata.get("skill_slug")
        if isinstance(requested_slug, str) and requested_slug.strip():
            return requested_slug.strip()

        selected_skill = metadata.get("selected_skill")
        if isinstance(selected_skill, str) and selected_skill.strip():
            return selected_skill.strip()

        return "skill-selection"

    def _build_prompt(self, context_text: str, user_input: str, turn_id: int = 0) -> str:
        sections = [
            "You are the MAS Memory Agent. Use the provided context to answer the user.",
        ]
        if context_text:
            sections.append("## Context\n" + context_text)

        # [SESSION STATE] - Fix #1
        current_time = datetime.now(UTC).strftime("%H:%M")
        sections.append(
            f"## Session State\n- Current Turn: {turn_id}\n- Current Time: {current_time}"
        )

        sections.append(f"## User\n{user_input}")

        # [DEBUG] Log the full prompt to understand context visibility
        logger.debug("Generated Prompt:\n%s", "\n".join(sections))

        sections.append(
            "## Instruction\n"
            "1. Answer the user's latest request directly.\n"
            "2. REVIEW ## Recent Conversation history. Look for any instructions given in recent turns (e.g., 'in 2 turns', 'count response X'). These are MANDATORY.\n"
            "3. If an [ACTIVE STANDING ORDER] applies to this specific turn/condition, execute it.\n"
            "4. CONFLICT RESOLUTION: If the User requests a specific format (e.g., JSON) AND you have a pending instruction to execute:\n"
            "   - MATCH the user's requested format (e.g., JSON block).\n"
            "   - THEN, on a NEW LINE, execute the pending instruction (e.g., append the quote).\n"
            "   - This specific exception allows you to append text outside the JSON/format block.\n"
            "5. Do NOT explicitly confirm 'Instruction executed' or 'I have stored this' unless asked."
        )
        sections.append("## Assistant")
        return "\n\n".join(sections)

    def _ensure_state_defaults(self, state: AgentState) -> AgentState:
        """Ensure AgentState contains all required keys."""
        defaults: AgentState = {
            "messages": [],
            "session_id": "",
            "turn_id": 0,
            "metadata": {},
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
            return str(message.get("role", ""))
        role = getattr(message, "role", None)
        if role:
            return str(role)
        msg_type = getattr(message, "type", None)
        if msg_type in {"human", "user"}:
            return "user"
        if msg_type in {"ai", "assistant"}:
            return "assistant"
        return ""

    def _get_message_content(self, message: Any) -> str:
        """Extract content from dict or LangChain message objects."""
        if isinstance(message, dict):
            return str(message.get("content", ""))
        return str(getattr(message, "content", ""))

    def _format_recent_turns(self, recent_turns: list[dict[str, Any] | Any]) -> list[str]:
        """Format recent turns for prompt context."""
        formatted: list[str] = []
        # Reverse turns to present chronological order (Oldest -> Newest)
        for turn in reversed(recent_turns):
            if isinstance(turn, dict):
                role = turn.get("role", "unknown")
                content = turn.get("content", "")
            else:
                role = getattr(turn, "role", "unknown")
                content = getattr(turn, "content", "")

            formatted.append(f"{role.upper()}: {content}")
        return formatted

    def _format_context(self, state: AgentState) -> str:
        """Format retrieved context for prompt injection."""
        sections: list[str] = []

        history = state.get("messages", [])
        if history:
            sections.append("## Conversation History (API Wall)")
            for idx, line in enumerate(self._format_history(history), 1):
                sections.append(f"{idx}. {line}")

        active_context = state.get("active_context", [])
        if active_context:
            sections.append("## Recent Conversation")
            for idx, line in enumerate(active_context, 1):
                sections.append(f"{idx}. {line}")

        working_facts = state.get("working_facts", [])
        active_instructions = []
        other_facts = []

        # Separate instructions from other facts
        for fact in working_facts:
            # Handle both dictionary and object access
            f_type = (
                fact.get("fact_type")
                if isinstance(fact, dict)
                else getattr(fact, "fact_type", None)
            )
            if f_type == "instruction":
                active_instructions.append(fact)
            else:
                other_facts.append(fact)

        if active_instructions:
            sections.append("\n## [ACTIVE STANDING ORDERS]")
            sections.append("You MUST obey these user-defined constraints above all else:")
            for _idx, fact in enumerate(active_instructions, 1):
                content = fact.get("content") if isinstance(fact, dict) else fact.content
                sections.append(f"- {content}")

        if other_facts:
            sections.append("\n## Key Facts (Working Memory)")
            for idx, fact in enumerate(other_facts, 1):
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

    def _format_history(self, history: list[dict[str, Any] | Any]) -> list[str]:
        """Format API-provided conversation history for prompt context."""
        formatted: list[str] = []
        for message in history:
            if isinstance(message, dict):
                role = str(message.get("role", "unknown")).upper()
                content = str(message.get("content", ""))
            else:
                role = str(getattr(message, "role", "unknown")).upper()
                content = str(getattr(message, "content", ""))
            formatted.append(f"{role}: {content}")
        return formatted

    def _merge_query_results(self, state: AgentState, results: list[dict[str, Any]]) -> None:
        """Merge query results into the agent state by tier."""
        for result in results:
            tier = result.get("tier")
            content = result.get("content", "")
            if tier == "L2":
                state["working_facts"].append(result)
            elif tier == "L3":
                if content:
                    state["episodic_chunks"].append(content)
            elif tier == "L4" and content:
                state["semantic_knowledge"].append(content)

    def _encode_turn_id(self, turn_id: int, role: str) -> int:
        """Encode turn IDs to avoid user/assistant collisions in L1 storage."""
        return turn_id * 2 if role == "user" else (turn_id * 2) + 1

    def _build_agent_metadata(self, state: AgentState) -> dict[str, Any]:
        """Build trace metadata for Phoenix span attributes."""
        metadata = state.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        return {
            "agent.type": "full",
            "agent.session_id": state.get("session_id"),
            "agent.turn_id": state.get("turn_id"),
            "agent.variant": self._agent_variant,
            "agent.skill_slug": metadata.get("skill_slug"),
            "agent.allowed_tools": metadata.get("allowed_tools"),
            "agent.gated_tools": metadata.get("gated_tool_names"),
        }
