import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from opentelemetry import trace

from src.api.v2_schemas import (
    ContextRequest,
    CurationDecisionCreateRequest,
    L2SemanticFactRequest,
    L3SemanticAssimilateRequest,
    L3SemanticQueryRequest,
    L4SemanticFinalizeRequest,
    MemoryQueryRequest,
    TraceCorrelationCreateRequest,
    TurnCreateRequest,
)
from src.evaluation.agent_wrapper import AgentWrapperState
from src.memory.models import SearchWeights, TurnData
from src.memory.services.contracts import ScopeEnvelope
from src.memory.services.gateway import MemoryGatewayService
from src.memory.services.permissions import PermissionPolicy, YAAMPermissionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/memory", tags=["Memory Gateway v2"])
tracer = trace.get_tracer(__name__)

REST_V2_MUTATING_TOOLS = frozenset(
    {
        "yaam.l2.store_fact",
        "yaam.l3.assimilate_episode",
        "yaam.l4.finalize_artifact",
        "yaam.curation.record_decision",
        "yaam.trace.record_correlation",
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
        project_id=getattr(state, "project_id", None),
    )


def _scope_from_request(
    request: Request,
    *,
    session_id: str,
    agent_id: str,
    task_id: str | None = None,
    tenant_id: str | None = None,
    run_id: str | None = None,
    caller_role: str | None = None,
    visibility_scope: str | None = None,
) -> ScopeEnvelope:
    """Create a service scope from REST v2 request fields and trace headers."""
    return ScopeEnvelope(
        session_id=session_id,
        agent_id=agent_id,
        caller_role=caller_role,
        visibility_scope=visibility_scope,
        task_id=task_id,
        tenant_id=tenant_id,
        run_id=run_id,
        traceparent=request.headers.get("traceparent"),
    )


def _set_scope_span_attributes(span: Any, scope: ScopeEnvelope, operation: str) -> None:
    span.set_attribute("session.id", scope.session_id)
    span.set_attribute("yaam.agent_id", scope.agent_id)
    span.set_attribute("yaam.operation", operation)
    span.set_attribute("yaam.task_id", scope.task_id or "")
    span.set_attribute("yaam.tenant_id", scope.tenant_id or "")
    span.set_attribute("yaam.run_id", scope.run_id or "")
    span.set_attribute("yaam.caller_role", scope.caller_role or "")
    span.set_attribute("yaam.visibility_scope", scope.visibility_scope or "")


def _permission_http_error(exc: YAAMPermissionError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=exc.payload.model_dump(mode="json"),
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


# --- Unified Memory Reads ---


@router.post("/query", status_code=status.HTTP_200_OK)
async def guarded_memory_query(
    request: Request, payload: MemoryQueryRequest
) -> dict[str, Any]:
    state = _get_state(request)
    service = _memory_service_from_state(state)
    scope = _scope_from_request(
        request,
        session_id=payload.session_id,
        agent_id=payload.agent_id,
        task_id=payload.task_id,
        tenant_id=payload.tenant_id,
        run_id=payload.run_id,
        caller_role=payload.caller_role,
        visibility_scope=payload.visibility_scope,
    )
    with tracer.start_as_current_span("yaam.gateway.v2.memory_query") as span:
        _set_scope_span_attributes(span, scope, "yaam.memory.query")
        results, leakage_guard = await service.query_memory_checked(
            scope=scope,
            query=payload.query,
            limit=payload.limit,
            weights=SearchWeights(
                l2_weight=payload.l2_weight,
                l3_weight=payload.l3_weight,
                l4_weight=payload.l4_weight,
            ),
            allowed_fields=payload.allowed_fields,
            forbidden_fields=payload.forbidden_fields,
            require_leakage_guard=payload.require_leakage_guard,
        )
    return {
        "status": "success",
        "results": [result.model_dump(mode="json") for result in results],
        "leakage_guard": leakage_guard.model_dump(mode="json"),
    }


@router.post("/context", status_code=status.HTTP_200_OK)
async def guarded_context(request: Request, payload: ContextRequest) -> dict[str, Any]:
    state = _get_state(request)
    service = _memory_service_from_state(state)
    scope = _scope_from_request(
        request,
        session_id=payload.session_id,
        agent_id=payload.agent_id,
        task_id=payload.task_id,
        tenant_id=payload.tenant_id,
        run_id=payload.run_id,
        caller_role=payload.caller_role,
        visibility_scope=payload.visibility_scope,
    )
    with tracer.start_as_current_span("yaam.gateway.v2.context") as span:
        _set_scope_span_attributes(span, scope, "yaam.memory.get_context")
        context = await service.get_context(
            scope=scope,
            min_ciar=payload.min_ciar,
            max_turns=payload.max_turns,
            max_facts=payload.max_facts,
            allowed_fields=payload.allowed_fields,
            forbidden_fields=payload.forbidden_fields,
            require_leakage_guard=payload.require_leakage_guard,
        )
    return {"status": "success", "context": context.model_dump(mode="json")}


# --- Maintainer Curation And Trace Correlation ---


@router.post("/curation/decisions", status_code=status.HTTP_201_CREATED)
async def create_curation_decision(
    request: Request, payload: CurationDecisionCreateRequest
) -> dict[str, Any]:
    state = _get_state(request)
    if not state.l2_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L2 Working Memory tier is not configured in the current YAAM environment.",
        )
    service = _memory_service_from_state(state)
    scope = _scope_from_request(
        request,
        session_id=payload.session_id,
        agent_id=payload.agent_id,
        task_id=payload.task_id,
        tenant_id=payload.tenant_id,
        run_id=payload.run_id,
        caller_role=payload.caller_role,
        visibility_scope=payload.visibility_scope,
    )
    with tracer.start_as_current_span("yaam.gateway.v2.curation_decision") as span:
        _set_scope_span_attributes(span, scope, "yaam.curation.record_decision")
        try:
            ack = await service.record_curation_decision(
                scope=scope,
                task_id=payload.task_id,
                decision=payload.decision,
                reason=payload.reason,
                source_triad=payload.source_triad,
                reviewer=payload.reviewer,
                metadata=payload.metadata,
            )
        except YAAMPermissionError as exc:
            raise _permission_http_error(exc) from exc
    return {"status": "success", "ack": ack.model_dump(mode="json")}


@router.get("/curation/decisions", status_code=status.HTTP_200_OK)
async def list_curation_decisions(
    request: Request,
    session_id: str,
    agent_id: str,
    caller_role: str,
    task_id: str | None = None,
    tenant_id: str | None = None,
    run_id: str | None = None,
    visibility_scope: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    state = _get_state(request)
    if not state.l2_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L2 Working Memory tier is not configured in the current YAAM environment.",
        )
    service = _memory_service_from_state(state)
    scope = _scope_from_request(
        request,
        session_id=session_id,
        agent_id=agent_id,
        task_id=task_id,
        tenant_id=tenant_id,
        run_id=run_id,
        caller_role=caller_role,
        visibility_scope=visibility_scope,
    )
    with tracer.start_as_current_span("yaam.gateway.v2.curation_list") as span:
        _set_scope_span_attributes(span, scope, "yaam.curation.list_decisions")
        try:
            decisions = await service.list_curation_decisions(
                scope=scope,
                task_id=task_id,
                limit=limit,
            )
        except YAAMPermissionError as exc:
            raise _permission_http_error(exc) from exc
    return {
        "status": "success",
        "decisions": [decision.model_dump(mode="json") for decision in decisions],
    }


@router.post("/trace-correlations", status_code=status.HTTP_201_CREATED)
async def create_trace_correlation(
    request: Request, payload: TraceCorrelationCreateRequest
) -> dict[str, Any]:
    state = _get_state(request)
    if not state.l2_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L2 Working Memory tier is not configured in the current YAAM environment.",
        )
    service = _memory_service_from_state(state)
    scope = _scope_from_request(
        request,
        session_id=payload.session_id,
        agent_id=payload.agent_id,
        task_id=payload.task_id,
        tenant_id=payload.tenant_id,
        run_id=payload.run_id,
        caller_role=payload.caller_role,
        visibility_scope=payload.visibility_scope,
    )
    with tracer.start_as_current_span("yaam.gateway.v2.trace_correlation") as span:
        _set_scope_span_attributes(span, scope, "yaam.trace.record_correlation")
        try:
            ack = await service.record_trace_correlation(
                scope=scope,
                trace_id=payload.trace_id,
                artifact_ref=payload.artifact_ref,
                openrouter_call_id=payload.openrouter_call_id,
                linked_memory_ids=payload.linked_memory_ids,
                error_summary=payload.error_summary,
                trace_status=payload.trace_status,
                metadata=payload.metadata,
            )
        except YAAMPermissionError as exc:
            raise _permission_http_error(exc) from exc
    return {"status": "success", "ack": ack.model_dump(mode="json")}


@router.get("/trace-correlations", status_code=status.HTTP_200_OK)
async def lookup_trace_correlations(
    request: Request,
    session_id: str,
    agent_id: str,
    caller_role: str,
    correlation_id: str | None = None,
    trace_id: str | None = None,
    task_id: str | None = None,
    tenant_id: str | None = None,
    run_id: str | None = None,
    visibility_scope: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    state = _get_state(request)
    if not state.l2_tier:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="L2 Working Memory tier is not configured in the current YAAM environment.",
        )
    service = _memory_service_from_state(state)
    scope = _scope_from_request(
        request,
        session_id=session_id,
        agent_id=agent_id,
        task_id=task_id,
        tenant_id=tenant_id,
        run_id=run_id,
        caller_role=caller_role,
        visibility_scope=visibility_scope,
    )
    with tracer.start_as_current_span("yaam.gateway.v2.trace_lookup") as span:
        _set_scope_span_attributes(span, scope, "yaam.trace.lookup")
        try:
            correlations = await service.lookup_trace_correlation(
                scope=scope,
                correlation_id=correlation_id,
                trace_id=trace_id,
                task_id=task_id,
                run_id=run_id,
                limit=limit,
            )
        except YAAMPermissionError as exc:
            raise _permission_http_error(exc) from exc
    return {
        "status": "success",
        "correlations": [
            correlation.model_dump(mode="json") for correlation in correlations
        ],
    }


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
