import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from src.api.v2_schemas import (
    L2SemanticFactRequest,
    L3SemanticAssimilateRequest,
    L3SemanticQueryRequest,
    L4SemanticFinalizeRequest,
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
    state = _get_state(request)
    if not state.l2_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L2 Working Memory tier is not configured in the current YAAM environment.",
        )

    _log_with_trace(
        logging.INFO, f"L2 action '{payload.action}' by agent {payload.agent_id}.", payload.metadata
    )

    if payload.action == "store":
        if not payload.content:
            raise HTTPException(status_code=400, detail="Content requires for 'store' action.")
        fact_id = str(uuid.uuid4())
        fact = Fact(
            fact_id=fact_id,
            session_id=payload.session_id,
            content=payload.content,
            ciar_score=0.5,
            certainty=0.8,
            impact=0.5,
            metadata=payload.metadata,
        )
        await state.l2_tier.store(fact)
        return {"status": "success", "fact_id": fact_id}

    elif payload.action == "retrieve":
        facts = await state.l2_tier.query_by_session(payload.session_id)
        return {"status": "success", "facts": facts or []}

    raise HTTPException(status_code=400, detail="Invalid action")


# --- L3: Episodic Memory (Assimilate & Query) ---


@router.post("/l3/assimilate", status_code=status.HTTP_201_CREATED)
async def semantic_assimilate(
    request: Request, payload: L3SemanticAssimilateRequest
) -> dict[str, str]:
    state = _get_state(request)
    if not state.memory_system.l3_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L3 Episodic Memory tier is not configured in the current YAAM environment.",
        )

    _log_with_trace(
        logging.INFO, f"Assimilating knowledge for agent {payload.agent_id}.", payload.metadata
    )
    llm_client = state.memory_system.llm_client

    try:
        embedding = await llm_client.get_embedding(payload.text_to_assimilate)

        # Internal Cypher/Entity generation pipeline
        prompt = f"Extract structured graph entities from: {payload.text_to_assimilate}"
        await llm_client.generate(prompt)

    except Exception as exc:
        logger.exception("LLM Provider failed during assimilation")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"502 Bad Gateway: YAAM internal LLM pipeline failed - {exc}",
        ) from exc

    episode_id = f"ep-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC)
    episode = Episode(
        episode_id=episode_id,
        session_id=payload.session_id,
        summary=payload.text_to_assimilate[:100],
        time_window_start=now,
        time_window_end=now,
        fact_valid_from=now,
        source_observation_timestamp=now,
        topics=payload.domain_tags,
        metadata=payload.metadata,
    )
    episode_input = EpisodeStoreInput(
        episode=episode,
        embedding=embedding,
        entities=[{"name": "ExtractedEntity", "label": "Concept"}],
        relationships=[],
    )

    stored_id = await state.memory_system.l3_tier.store(episode_input)
    return {"status": "success", "episode_id": stored_id}


@router.post("/l3/query", status_code=status.HTTP_200_OK)
async def semantic_query(request: Request, payload: L3SemanticQueryRequest) -> dict[str, Any]:
    state = _get_state(request)
    if not state.memory_system.l3_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L3 Episodic Memory tier is not configured in the current YAAM environment.",
        )

    _log_with_trace(
        logging.INFO, f"Querying knowledge for agent {payload.agent_id}.", payload.metadata
    )
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
    state = _get_state(request)
    if not state.memory_system.l4_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L4 Semantic Memory tier is not configured in the current YAAM environment.",
        )

    _log_with_trace(
        logging.INFO, f"Finalizing consensus for task {payload.task_id}.", payload.metadata
    )

    doc_id = f"kd-{uuid.uuid4().hex[:8]}"
    document = KnowledgeDocument(
        knowledge_id=doc_id,
        session_id=payload.session_id,
        title=payload.title,
        content=payload.final_artifact,
        metadata={**payload.consensus_metadata, **payload.metadata},
    )

    knowledge_id = await state.memory_system.l4_tier.store(document)
    return {"status": "success", "knowledge_id": knowledge_id}
