import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from src.api.v2_schemas import (
    EpisodeCreateRequest,
    FactCreateRequest,
    KnowledgeCreateRequest,
    TurnCreateRequest,
)
from src.evaluation.agent_wrapper import AgentWrapperState
from src.memory.models import Episode, EpisodeStoreInput, Fact, KnowledgeDocument, TurnData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/memory", tags=["Memory Gateway v2"])


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
            detail="L1 Active Context tier is not configured in the current YAAM environment.",
        )

    turns = await state.l1_tier.retrieve_session(session_id)
    return {"session_id": session_id, "turns": turns or []}


@router.delete("/l1/turns/{session_id}")
async def delete_session_turns(request: Request, session_id: str) -> dict[str, Any]:
    state = _get_state(request)
    if not state.l1_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L1 Active Context tier is not configured in the current YAAM environment.",
        )

    deleted = await state.l1_tier.delete(session_id)
    return {"session_id": session_id, "deleted": deleted}


# --- L2: Working Memory (Facts) ---


@router.post("/l2/facts", status_code=status.HTTP_201_CREATED)
async def create_fact(request: Request, payload: FactCreateRequest) -> dict[str, str]:
    state = _get_state(request)
    if not state.l2_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L2 Working Memory tier is not configured in the current YAAM environment.",
        )

    _log_with_trace(logging.INFO, f"Inserting fact {payload.fact_id} into L2.", payload.metadata)

    fact = Fact(
        fact_id=payload.fact_id,
        session_id=payload.session_id,
        content=payload.content,
        ciar_score=payload.ciar_score,
        certainty=payload.certainty,
        impact=payload.impact,
        fact_type=payload.fact_type,  # type: ignore
        fact_category=payload.fact_category,  # type: ignore
        metadata=payload.metadata,
    )
    fact_id = await state.l2_tier.store(fact)
    return {"status": "success", "fact_id": fact_id}


@router.get("/l2/facts/{session_id}")
async def get_facts(request: Request, session_id: str) -> dict[str, Any]:
    state = _get_state(request)
    if not state.l2_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L2 Working Memory tier is not configured in the current YAAM environment.",
        )

    facts = await state.l2_tier.query_by_session(session_id)
    return {"session_id": session_id, "facts": facts or []}


@router.delete("/l2/facts/{fact_id}")
async def delete_fact(request: Request, fact_id: str) -> dict[str, Any]:
    state = _get_state(request)
    if not state.l2_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L2 Working Memory tier is not configured in the current YAAM environment.",
        )

    deleted = await state.l2_tier.delete(fact_id)
    return {"fact_id": fact_id, "deleted": deleted}


# --- L3: Episodic Memory (Episodes & Entities) ---


@router.post("/l3/entities", status_code=status.HTTP_201_CREATED)
async def create_episode(request: Request, payload: EpisodeCreateRequest) -> dict[str, str]:
    state = _get_state(request)
    if not state.memory_system.l3_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L3 Episodic Memory tier is not configured in the current YAAM environment.",
        )

    _log_with_trace(
        logging.INFO, f"Inserting episode {payload.episode_id} into L3.", payload.metadata
    )

    episode = Episode(
        episode_id=payload.episode_id,
        session_id=payload.session_id,
        summary=payload.summary,
        narrative=payload.narrative,
        time_window_start=payload.time_window_start,
        time_window_end=payload.time_window_end,
        fact_valid_from=payload.fact_valid_from,
        source_observation_timestamp=payload.source_observation_timestamp,
        importance_score=payload.importance_score,
        metadata=payload.metadata,
        topics=payload.topics,
        fact_count=len(payload.entities) + len(payload.relationships),
    )

    episode_input = EpisodeStoreInput(
        episode=episode,
        embedding=payload.vector_embedding,
        entities=payload.entities,
        relationships=payload.relationships,
    )

    episode_id = await state.memory_system.l3_tier.store(episode_input)
    return {"status": "success", "episode_id": episode_id}


# --- L4: Semantic Memory (Knowledge Documents) ---


@router.post("/l4/documents", status_code=status.HTTP_201_CREATED)
async def create_knowledge_document(
    request: Request, payload: KnowledgeCreateRequest
) -> dict[str, str]:
    state = _get_state(request)
    if not state.memory_system.l4_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L4 Semantic Memory tier is not configured in the current YAAM environment.",
        )

    _log_with_trace(
        logging.INFO,
        f"Inserting knowledge document {payload.knowledge_id} into L4.",
        payload.metadata,
    )

    document = KnowledgeDocument(
        knowledge_id=payload.knowledge_id,
        session_id=payload.session_id,
        title=payload.title,
        content=payload.content,
        knowledge_type=payload.knowledge_type,
        confidence_score=payload.confidence_score,
        category=payload.category,
        tags=payload.tags,
        metadata=payload.metadata,
    )

    knowledge_id = await state.memory_system.l4_tier.store(document)
    return {"status": "success", "knowledge_id": knowledge_id}
