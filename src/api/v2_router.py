import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from opentelemetry import trace

from src.api.v2_schemas import (
    L2SemanticFactRequest,
    L3SemanticAssimilateRequest,
    L3SemanticQueryRequest,
    L4SemanticFinalizeRequest,
    TurnCreateRequest,
)
from src.evaluation.agent_wrapper import AgentWrapperState
from src.memory.models import TurnData
from src.memory.services.contracts import ScopeEnvelope
from src.memory.services.gateway import MemoryGatewayService
from src.memory.services.permissions import PermissionPolicy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/memory", tags=["Memory Gateway v2"])
tracer = trace.get_tracer(__name__)

REST_V2_MUTATING_TOOLS = frozenset(
    {
        "yaam.l2.store_fact",
        "yaam.l3.assimilate_episode",
        "yaam.l4.finalize_artifact",
    }
)


def _log_with_trace(level: int, msg: str, metadata: dict[str, Any] | None = None) -> None:
    """Helper to inject trace_id into standard logging if present."""
    if metadata and "trace_id" in metadata:
        trace_id = metadata["trace_id"]
        logger.log(level, f"[trace_id={trace_id}] {msg}")
    else:
        logger.log(level, msg)


def _get_state(request: Request) -> AgentWrapperState:
    """Retrieve AgentWrapperState from FastAPI app state."""
    state = getattr(request.app.state, "wrapper", None)
    if not isinstance(state, AgentWrapperState):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent wrapper state not initialized.",
        )
    return state


def _rest_v2_permission_policy() -> PermissionPolicy:
    """Allow legacy REST v2 writes without inheriting MCP environment gates."""
    return PermissionPolicy(
        enable_writes=True,
        enable_lifecycle=True,
        allowlisted_tools=REST_V2_MUTATING_TOOLS,
    )


def _memory_service_from_state(state: AgentWrapperState) -> MemoryGatewayService:
    """Build the shared service while preserving wrapper tier aliases used by v2."""
    memory_system = state.memory_system
    for attr_name in ("l1_tier", "l2_tier", "l3_tier", "l4_tier"):
        tier = getattr(state, attr_name, None)
        if tier is not None:
            setattr(memory_system, attr_name, tier)
    return MemoryGatewayService(
        memory_system=memory_system,
        permission_policy=_rest_v2_permission_policy(),
    )


def _scope_from_request(
    request: Request,
    *,
    session_id: str,
    agent_id: str,
    task_id: str | None = None,
) -> ScopeEnvelope:
    """Create a service scope from REST v2 request fields and trace headers."""
    return ScopeEnvelope(
        session_id=session_id,
        agent_id=agent_id,
        task_id=task_id,
        traceparent=request.headers.get("traceparent"),
    )


# --- L1: Active Context (Turns) ---


@router.post("/l1/turns", status_code=status.HTTP_201_CREATED)
async def create_turn(request: Request, payload: TurnCreateRequest) -> dict[str, str]:
    state = _get_state(request)
    if not state.l1_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L1 Active Context tier is not configured in the current YAAM environment.",
        )

    _log_with_trace(logging.INFO, f"Inserting turn {payload.turn_id} into L1.", payload.metadata)

    turn = TurnData(
        session_id=payload.session_id,
        turn_id=payload.turn_id,
        role=payload.role,
        content=payload.content,
        metadata=payload.metadata,
    )
    turn_id = await state.l1_tier.store(turn)
    return {"status": "success", "turn_id": turn_id}


@router.get("/l1/turns/{session_id}")
async def get_turns(request: Request, session_id: str) -> dict[str, Any]:
    state = _get_state(request)
    if not state.l1_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L1 Active Context tier is not configured.",
        )

    turns = await state.l1_tier.retrieve_session(session_id)
    return {"session_id": session_id, "turns": turns or []}


@router.delete("/l1/turns/{session_id}")
async def delete_session_turns(request: Request, session_id: str) -> dict[str, Any]:
    state = _get_state(request)
    if not state.l1_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L1 Active Context tier is not configured.",
        )

    deleted = await state.l1_tier.delete(session_id)
    return {"session_id": session_id, "deleted": deleted}


# --- L2: Working Memory (Facts) ---


@router.post("/l2/facts", status_code=status.HTTP_200_OK)
async def semantic_l2_fact(request: Request, payload: L2SemanticFactRequest) -> dict[str, Any]:
    with tracer.start_as_current_span("yaam.gateway.v2.facts") as span:
        span.set_attribute("session.id", payload.session_id)
        span.set_attribute("yaam.agent_id", payload.agent_id)

        state = _get_state(request)
        if not state.l2_tier:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="L2 Working Memory tier is not configured in the current YAAM environment.",
            )

        _log_with_trace(logging.INFO, f"L2 action '{payload.action}' by agent {payload.agent_id}.")
        service = _memory_service_from_state(state)
        scope = _scope_from_request(
            request,
            session_id=payload.session_id,
            agent_id=payload.agent_id,
            task_id=payload.task_id,
        )

        if payload.action == "store":
            if not payload.content:
                raise HTTPException(status_code=400, detail="Content requires for 'store' action.")
            ack = await service.store_l2_fact(
                scope=scope,
                content=payload.content,
                metadata={
                    "ciar_score_source": "v2_semantic_store",
                },
            )
            return {"status": "success", "fact_id": ack.created_id}

        elif payload.action == "retrieve":
            facts = await service.list_l2_facts(scope)
            return {"status": "success", "facts": facts or []}

        raise HTTPException(status_code=400, detail="Invalid action")


# --- L3: Episodic Memory (Assimilate & Query) ---


@router.post("/l3/assimilate", status_code=status.HTTP_201_CREATED)
async def semantic_assimilate(
    request: Request, payload: L3SemanticAssimilateRequest
) -> dict[str, str]:
    with tracer.start_as_current_span("yaam.gateway.v2.assimilate") as span:
        span.set_attribute("session.id", payload.session_id)
        span.set_attribute("yaam.agent_id", payload.agent_id)

        state = _get_state(request)
        if not state.memory_system.l3_tier:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="L3 Episodic Memory tier is not configured in the current YAAM environment.",
            )

        _log_with_trace(logging.INFO, f"Assimilating knowledge for agent {payload.agent_id}.")
        service = _memory_service_from_state(state)
        scope = _scope_from_request(
            request,
            session_id=payload.session_id,
            agent_id=payload.agent_id,
        )

        try:
            ack = await service.assimilate_l3_episode(
                scope=scope,
                text_to_assimilate=payload.text_to_assimilate,
                domain_tags=payload.domain_tags,
            )
        except Exception as exc:
            logger.exception("LLM Provider failed during assimilation")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"502 Bad Gateway: YAAM internal LLM pipeline failed - {exc}",
            ) from exc

        return {"status": "success", "episode_id": ack.created_id or ""}


@router.post("/l3/query", status_code=status.HTTP_200_OK)
async def semantic_query(request: Request, payload: L3SemanticQueryRequest) -> dict[str, Any]:
    with tracer.start_as_current_span("yaam.gateway.v2.query") as span:
        span.set_attribute("session.id", payload.session_id)
        span.set_attribute("yaam.agent_id", payload.agent_id)

        state = _get_state(request)
        if not state.memory_system.l3_tier:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="L3 Episodic Memory tier is not configured in the current YAAM environment.",
            )

        _log_with_trace(logging.INFO, f"Querying knowledge for agent {payload.agent_id}.")
        llm_client = state.memory_system.llm_client

        try:
            _ = await llm_client.get_embedding(payload.nl_query)
            prompt = f"Translate to Cypher query: {payload.nl_query}"
            await llm_client.generate(prompt)
        except Exception as exc:
            logger.exception("LLM Provider failed during query")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"502 Bad Gateway: YAAM internal LLM pipeline failed - {exc}",
            ) from exc

        # In a fully integrated system we would call l3_tier.search(embedding, cypher_query)
        # Simulating standard response adherence below.
        return {
            "status": "success",
            "results": [],
            "provenance": {"agent_id": payload.agent_id, "session_id": payload.session_id},
        }


# --- L4: Semantic Memory (Finalize) ---


@router.post("/l4/finalize", status_code=status.HTTP_201_CREATED)
async def semantic_finalize(request: Request, payload: L4SemanticFinalizeRequest) -> dict[str, str]:
    with tracer.start_as_current_span("yaam.gateway.v2.finalize") as span:
        span.set_attribute("session.id", payload.session_id)
        # User requested mapping the session, for finalize we don't have agent_id in schema, so we skip it.

        state = _get_state(request)
        if not state.memory_system.l4_tier:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="L4 Semantic Memory tier is not configured in the current YAAM environment.",
            )

        _log_with_trace(logging.INFO, f"Finalizing consensus for task {payload.task_id}.")
        service = _memory_service_from_state(state)
        scope = _scope_from_request(
            request,
            session_id=payload.session_id,
            agent_id="rest-v2",
            task_id=payload.task_id,
        )
        ack = await service.finalize_l4_artifact(
            scope=scope,
            title=payload.title,
            final_artifact=payload.final_artifact,
            consensus_metadata=payload.consensus_metadata,
        )
        return {"status": "success", "knowledge_id": ack.created_id or ""}
