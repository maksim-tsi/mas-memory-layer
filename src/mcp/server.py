"""MCP v1 server wiring for YAAM memory operations."""

import argparse
import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable, Sequence
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from src.evaluation.agent_wrapper import build_config, initialize_state, shutdown_state
from src.memory.ciar_formula import DEFAULT_AGE_DECAY_LAMBDA, DEFAULT_RECENCY_ALPHA
from src.memory.models import Episode, Fact, KnowledgeDocument, SearchWeights
from src.memory.namespace import normalize_project_id
from src.memory.services import (
    CognitiveSandwichDomainViewService,
    MemoryGatewayService,
    PermissionPolicy,
    ScopeEnvelope,
    SkillFactoryDomainViewService,
    YAAMErrorPayload,
    YAAMPermissionError,
)
from src.memory.services.contracts import redact_metadata
from src.observability import (
    current_trace_metadata,
    set_span_attributes,
    set_span_error,
    start_span,
)

MCP_SDK_REQUIREMENT = "mcp>=1.12.4,<1.27.1"

MCP_TOOL_NAMES = (
    "yaam.memory.query",
    "yaam.memory.get_context",
    "yaam.l2.store_fact",
    "yaam.l2.search_facts",
    "yaam.l3.search_episodes",
    "yaam.l3.assimilate_episode",
    "yaam.l4.search_knowledge",
    "yaam.l4.finalize_artifact",
    "yaam.ciar.explain",
    "yaam.evidence.table",
    "yaam.contradiction.review",
    "yaam.health.check",
    "yaam.curation.record_decision",
    "yaam.curation.list_decisions",
    "yaam.trace.record_correlation",
    "yaam.trace.lookup",
)

MCP_RESOURCE_URIS = (
    "yaam://sessions/{session_id}/context",
    "yaam://sessions/{session_id}/facts",
    "yaam://facts/{fact_id}",
    "yaam://episodes/{episode_id}",
    "yaam://knowledge/{knowledge_id}",
    "yaam://health",
    "yaam://config/ciar",
    "yaam://schemas/fact",
    "yaam://schemas/episode",
    "yaam://schemas/knowledge-document",
)

MCP_PROMPT_NAMES = (
    "yaam.prompt.evidence_table",
    "yaam.prompt.memory_inspection",
    "yaam.prompt.ciar_explanation",
    "yaam.prompt.retrieval_strategy",
)

SKILL_FACTORY_MCP_RESOURCE_URIS = (
    "yaam://skills/{skill_name}",
    "yaam://ctts/{ctt_id}",
    "yaam://runs/{run_id}/episodes",
    "yaam://skill-factory/qa-status/{qa_status}/runs",
    "yaam://skill-factory/active-tool-status/{active_tool_status}/runs",
)

SKILL_FACTORY_MCP_PROMPT_NAMES = ("yaam.prompt.repair_pattern_summary",)

COGNITIVE_SANDWICH_MCP_RESOURCE_URIS = (
    "yaam://artifacts/{artifact_id}/lineage",
    "yaam://sessions/{session_id}/artifacts",
    "yaam://runs/{run_id}/artifacts",
    "yaam://runs/{run_id}/evidence",
    "yaam://incidents/{incident_id}/reports",
)

COGNITIVE_SANDWICH_MCP_PROMPT_NAMES = (
    "yaam.prompt.artifact_repair_context",
    "yaam.prompt.artifact_lineage_summary",
)

MCP_STREAMABLE_HTTP_LOGGER = "mcp.server.streamable_http"


def create_mcp_server(
    service: MemoryGatewayService | None = None,
    config_args: argparse.Namespace | None = None,
) -> Any:
    """Create the FastMCP server and register MCP v1 capabilities.

    The SDK import is lazy so documentation and service-layer tests can run
    before the dependency is explicitly approved and installed.

    Raises:
        RuntimeError: If the official MCP SDK is not installed.
    """
    try:
        from mcp.server.fastmcp import FastMCP
        from mcp.server.fastmcp.exceptions import ToolError
    except ImportError as exc:
        raise RuntimeError(
            f"YAAM MCP v1 requires the official Python SDK dependency: {MCP_SDK_REQUIREMENT}."
        ) from exc

    args = config_args or parse_args([])
    streamable_http = args.transport == "streamable-http"
    if streamable_http:
        _install_streamable_http_closed_resource_filter()

    mcp = FastMCP(
        "yaam-mcp-v1",
        host=args.mcp_host,
        port=args.mcp_port,
        streamable_http_path=args.mcp_path,
        stateless_http=streamable_http,
        json_response=streamable_http,
    )
    runtime_service = service

    async def get_service() -> MemoryGatewayService:
        nonlocal runtime_service
        if runtime_service is None:
            runtime_service = await create_service_from_env(config_args)
            mcp._service = runtime_service
        return runtime_service

    if runtime_service is not None:
        mcp._service = runtime_service

    enabled_domain_packs = _enabled_domain_packs(args)

    @mcp.tool(name="yaam.memory.query")
    async def memory_query(
        session_id: str,
        agent_id: str,
        query: str,
        limit: int = 10,
        task_id: str | None = None,
        tenant_id: str | None = None,
        run_id: str | None = None,
        caller_role: str | None = None,
        visibility_scope: str | None = None,
        allowed_fields: list[str] | None = None,
        forbidden_fields: list[str] | None = None,
        require_leakage_guard: bool = False,
        traceparent: str | None = None,
        l2_weight: float = 0.3,
        l3_weight: float = 0.5,
        l4_weight: float = 0.2,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(
                session_id=session_id,
                agent_id=agent_id,
                task_id=task_id,
                tenant_id=tenant_id,
                run_id=run_id,
                caller_role=caller_role,
                visibility_scope=visibility_scope,
                traceparent=traceparent,
            )
            weights = SearchWeights(
                l2_weight=l2_weight,
                l3_weight=l3_weight,
                l4_weight=l4_weight,
            )
            results, leakage_guard = await (await get_service()).query_memory_checked(
                scope,
                query=query,
                limit=limit,
                weights=weights,
                allowed_fields=allowed_fields,
                forbidden_fields=forbidden_fields,
                require_leakage_guard=require_leakage_guard,
            )
            return _response(
                "Memory query complete.",
                {
                    "results": _dump_many(results),
                    "leakage_guard": leakage_guard.model_dump(mode="json"),
                },
            )

        return await _run_mcp_async(
            "tool",
            "yaam.memory.query",
            "read",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.memory.get_context")
    async def memory_get_context(
        session_id: str,
        agent_id: str,
        task_id: str | None = None,
        caller_role: str | None = None,
        visibility_scope: str | None = None,
        allowed_fields: list[str] | None = None,
        forbidden_fields: list[str] | None = None,
        require_leakage_guard: bool = False,
        traceparent: str | None = None,
        min_ciar: float = 0.6,
        max_turns: int = 20,
        max_facts: int = 10,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(
                session_id=session_id,
                agent_id=agent_id,
                task_id=task_id,
                caller_role=caller_role,
                visibility_scope=visibility_scope,
                traceparent=traceparent,
            )
            context = await (await get_service()).get_context(
                scope,
                min_ciar=min_ciar,
                max_turns=max_turns,
                max_facts=max_facts,
                allowed_fields=allowed_fields,
                forbidden_fields=forbidden_fields,
                require_leakage_guard=require_leakage_guard,
            )
            return _response("Context assembled.", {"context": context.model_dump(mode="json")})

        return await _run_mcp_async(
            "tool",
            "yaam.memory.get_context",
            "read",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.l2.store_fact")
    async def l2_store_fact(
        session_id: str,
        agent_id: str,
        content: str,
        task_id: str | None = None,
        caller_role: str | None = None,
        visibility_scope: str | None = None,
        traceparent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(
                session_id=session_id,
                agent_id=agent_id,
                task_id=task_id,
                caller_role=caller_role,
                visibility_scope=visibility_scope,
                traceparent=traceparent,
            )
            ack = await (await get_service()).store_l2_fact(
                scope, content=content, metadata=metadata
            )
            return _response("Fact stored.", {"ack": ack.model_dump(mode="json")})

        return await _run_mcp_async(
            "tool",
            "yaam.l2.store_fact",
            "write",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.l2.search_facts")
    async def l2_search_facts(
        session_id: str,
        agent_id: str,
        query: str | None = None,
        min_ciar: float | None = None,
        limit: int = 20,
        traceparent: str | None = None,
        caller_role: str | None = None,
        visibility_scope: str | None = None,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(
                session_id=session_id,
                agent_id=agent_id,
                caller_role=caller_role,
                visibility_scope=visibility_scope,
                traceparent=traceparent,
            )
            results = await (await get_service()).search_l2_facts(
                scope,
                query=query,
                min_ciar=min_ciar,
                limit=limit,
            )
            return _response("L2 facts retrieved.", {"results": _dump_many(results)})

        return await _run_mcp_async(
            "tool",
            "yaam.l2.search_facts",
            "read",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.l3.search_episodes")
    async def l3_search_episodes(
        session_id: str,
        agent_id: str,
        query: str,
        limit: int = 10,
        traceparent: str | None = None,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(session_id=session_id, agent_id=agent_id, traceparent=traceparent)
            results = await (await get_service()).search_l3_episodes(
                scope, query=query, limit=limit
            )
            return _response("L3 episodes retrieved.", {"results": _dump_many(results)})

        return await _run_mcp_async(
            "tool",
            "yaam.l3.search_episodes",
            "read",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.l3.assimilate_episode")
    async def l3_assimilate_episode(
        session_id: str,
        agent_id: str,
        text_to_assimilate: str,
        task_id: str | None = None,
        caller_role: str | None = None,
        visibility_scope: str | None = None,
        traceparent: str | None = None,
        domain_tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(
                session_id=session_id,
                agent_id=agent_id,
                task_id=task_id,
                caller_role=caller_role,
                visibility_scope=visibility_scope,
                traceparent=traceparent,
            )
            ack = await (await get_service()).assimilate_l3_episode(
                scope,
                text_to_assimilate=text_to_assimilate,
                domain_tags=domain_tags,
                metadata=metadata,
            )
            return _response("Episode assimilated.", {"ack": ack.model_dump(mode="json")})

        return await _run_mcp_async(
            "tool",
            "yaam.l3.assimilate_episode",
            "lifecycle",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.l4.search_knowledge")
    async def l4_search_knowledge(
        session_id: str,
        agent_id: str,
        query: str,
        limit: int = 10,
        traceparent: str | None = None,
        caller_role: str | None = None,
        visibility_scope: str | None = None,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(
                session_id=session_id,
                agent_id=agent_id,
                caller_role=caller_role,
                visibility_scope=visibility_scope,
                traceparent=traceparent,
            )
            results = await (await get_service()).search_l4_knowledge(
                scope, query=query, limit=limit
            )
            return _response("L4 knowledge retrieved.", {"results": _dump_many(results)})

        return await _run_mcp_async(
            "tool",
            "yaam.l4.search_knowledge",
            "read",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.l4.finalize_artifact")
    async def l4_finalize_artifact(
        session_id: str,
        agent_id: str,
        title: str,
        final_artifact: str,
        task_id: str | None = None,
        caller_role: str | None = None,
        visibility_scope: str | None = None,
        traceparent: str | None = None,
        consensus_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(
                session_id=session_id,
                agent_id=agent_id,
                task_id=task_id,
                caller_role=caller_role,
                visibility_scope=visibility_scope,
                traceparent=traceparent,
            )
            ack = await (await get_service()).finalize_l4_artifact(
                scope,
                title=title,
                final_artifact=final_artifact,
                consensus_metadata=consensus_metadata,
            )
            return _response("L4 artifact finalized.", {"ack": ack.model_dump(mode="json")})

        return await _run_mcp_async(
            "tool",
            "yaam.l4.finalize_artifact",
            "lifecycle",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.ciar.explain")
    async def ciar_explain(
        session_id: str,
        agent_id: str,
        certainty: float = 0.0,
        impact: float = 0.0,
        age_decay: float = 1.0,
        recency_boost: float = 1.0,
        caller_role: str | None = None,
        visibility_scope: str | None = None,
        traceparent: str | None = None,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(
                session_id=session_id,
                agent_id=agent_id,
                caller_role=caller_role,
                visibility_scope=visibility_scope,
                traceparent=traceparent,
            )
            explanation = await (await get_service()).explain_ciar(
                scope,
                components={
                    "certainty": certainty,
                    "impact": impact,
                    "age_decay": age_decay,
                    "recency_boost": recency_boost,
                },
            )
            return _response("CIAR explained.", {"explanation": explanation})

        return await _run_mcp_async(
            "tool",
            "yaam.ciar.explain",
            "read",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.evidence.table")
    async def evidence_table(
        session_id: str,
        agent_id: str,
        query: str,
        limit: int = 10,
        caller_role: str | None = None,
        visibility_scope: str | None = None,
        traceparent: str | None = None,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(
                session_id=session_id,
                agent_id=agent_id,
                caller_role=caller_role,
                visibility_scope=visibility_scope,
                traceparent=traceparent,
            )
            table = await (await get_service()).evidence_table(scope, query=query, limit=limit)
            return _response(
                "Evidence table assembled.", {"evidence_table": table.model_dump(mode="json")}
            )

        return await _run_mcp_async(
            "tool",
            "yaam.evidence.table",
            "read",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.contradiction.review")
    async def contradiction_review(
        session_id: str,
        agent_id: str,
        claims: list[str],
        task_id: str | None = None,
        expected_behavior: str | None = None,
        caller_role: str | None = None,
        visibility_scope: str | None = None,
        traceparent: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(
                session_id=session_id,
                agent_id=agent_id,
                task_id=task_id,
                caller_role=caller_role,
                visibility_scope=visibility_scope,
                traceparent=traceparent,
            )
            review = await (await get_service()).review_contradiction(
                scope,
                claims=claims,
                expected_behavior=expected_behavior,
                limit=limit,
            )
            return _response(
                "Contradiction reviewed.",
                {"review": review.model_dump(mode="json")},
            )

        return await _run_mcp_async(
            "tool",
            "yaam.contradiction.review",
            "read",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.health.check")
    async def health_check() -> dict[str, Any]:
        async def action() -> dict[str, Any]:
            health = await (await get_service()).health_check()
            return _response("Health checked.", {"health": health.model_dump(mode="json")})

        return await _run_mcp_async(
            "tool",
            "yaam.health.check",
            "read",
            action,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.curation.record_decision")
    async def curation_record_decision(
        session_id: str,
        agent_id: str,
        task_id: str,
        decision: str,
        reason: str,
        source_triad: dict[str, Any],
        reviewer: str,
        caller_role: str | None = None,
        visibility_scope: str | None = None,
        traceparent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(
                session_id=session_id,
                agent_id=agent_id,
                task_id=task_id,
                caller_role=caller_role,
                visibility_scope=visibility_scope,
                traceparent=traceparent,
            )
            ack = await (await get_service()).record_curation_decision(
                scope,
                task_id=task_id,
                decision=decision,
                reason=reason,
                source_triad=source_triad,
                reviewer=reviewer,
                metadata=metadata,
            )
            return _response("Curation decision recorded.", {"ack": ack.model_dump(mode="json")})

        return await _run_mcp_async(
            "tool",
            "yaam.curation.record_decision",
            "write",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.curation.list_decisions")
    async def curation_list_decisions(
        session_id: str,
        agent_id: str,
        task_id: str | None = None,
        caller_role: str | None = None,
        visibility_scope: str | None = None,
        traceparent: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(
                session_id=session_id,
                agent_id=agent_id,
                task_id=task_id,
                caller_role=caller_role,
                visibility_scope=visibility_scope,
                traceparent=traceparent,
            )
            decisions = await (await get_service()).list_curation_decisions(
                scope, task_id=task_id, limit=limit
            )
            return _response("Curation decisions listed.", {"decisions": _dump_many(decisions)})

        return await _run_mcp_async(
            "tool",
            "yaam.curation.list_decisions",
            "read",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.trace.record_correlation")
    async def trace_record_correlation(
        session_id: str,
        agent_id: str,
        task_id: str | None = None,
        run_id: str | None = None,
        trace_id: str | None = None,
        artifact_ref: str | None = None,
        openrouter_call_id: str | None = None,
        linked_memory_ids: list[str] | None = None,
        error_summary: str | None = None,
        trace_status: str = "unverified",
        caller_role: str | None = None,
        visibility_scope: str | None = None,
        traceparent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(
                session_id=session_id,
                agent_id=agent_id,
                task_id=task_id,
                run_id=run_id,
                caller_role=caller_role,
                visibility_scope=visibility_scope,
                traceparent=traceparent,
            )
            ack = await (await get_service()).record_trace_correlation(
                scope,
                trace_id=trace_id,
                artifact_ref=artifact_ref,
                openrouter_call_id=openrouter_call_id,
                linked_memory_ids=linked_memory_ids,
                error_summary=error_summary,
                trace_status=trace_status,
                metadata=metadata,
            )
            return _response("Trace correlation recorded.", {"ack": ack.model_dump(mode="json")})

        return await _run_mcp_async(
            "tool",
            "yaam.trace.record_correlation",
            "write",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.tool(name="yaam.trace.lookup")
    async def trace_lookup(
        session_id: str,
        agent_id: str,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        task_id: str | None = None,
        run_id: str | None = None,
        caller_role: str | None = None,
        visibility_scope: str | None = None,
        traceparent: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        scope: ScopeEnvelope | None = None

        async def action() -> dict[str, Any]:
            nonlocal scope
            scope = _scope(
                session_id=session_id,
                agent_id=agent_id,
                task_id=task_id,
                run_id=run_id,
                caller_role=caller_role,
                visibility_scope=visibility_scope,
                traceparent=traceparent,
            )
            correlations = await (await get_service()).lookup_trace_correlation(
                scope,
                correlation_id=correlation_id,
                trace_id=trace_id,
                task_id=task_id,
                run_id=run_id,
                limit=limit,
            )
            return _response("Trace correlations listed.", {"correlations": _dump_many(correlations)})

        return await _run_mcp_async(
            "tool",
            "yaam.trace.lookup",
            "read",
            action,
            scope_provider=lambda: scope,
            error_cls=ToolError,
        )

    @mcp.resource("yaam://health")
    async def health_resource() -> str:
        async def action() -> str:
            health = await (await get_service()).health_check()
            return health.model_dump_json()

        return await _run_mcp_async("resource", "yaam://health", "read", action)

    @mcp.resource("yaam://sessions/{session_id}/context")
    async def session_context_resource(session_id: str) -> str:
        scope: ScopeEnvelope | None = None

        async def action() -> str:
            nonlocal scope
            service_instance = await get_service()
            scope = _resource_scope(session_id=session_id)
            context = await service_instance.get_context(scope)
            return context.model_dump_json()

        return await _run_mcp_async(
            "resource",
            "yaam://sessions/{session_id}/context",
            "read",
            action,
            scope_provider=lambda: scope,
        )

    @mcp.resource("yaam://sessions/{session_id}/facts")
    async def session_facts_resource(session_id: str) -> str:
        scope: ScopeEnvelope | None = None

        async def action() -> str:
            nonlocal scope
            service_instance = await get_service()
            scope = _resource_scope(session_id=session_id)
            facts = await service_instance.search_l2_facts(scope)
            return json.dumps(_dump_many(facts))

        return await _run_mcp_async(
            "resource",
            "yaam://sessions/{session_id}/facts",
            "read",
            action,
            scope_provider=lambda: scope,
        )

    @mcp.resource("yaam://facts/{fact_id}")
    async def fact_resource(fact_id: str) -> str:
        scope = _resource_scope()

        async def action() -> str:
            fact = await (await get_service()).get_fact(scope, fact_id)
            return _json_or_not_found(fact, "fact_id", fact_id)

        return await _run_mcp_async("resource", "yaam://facts/{fact_id}", "read", action, scope)

    @mcp.resource("yaam://episodes/{episode_id}")
    async def episode_resource(episode_id: str) -> str:
        scope = _resource_scope()

        async def action() -> str:
            episode = await (await get_service()).get_episode(scope, episode_id)
            return _json_or_not_found(episode, "episode_id", episode_id)

        return await _run_mcp_async(
            "resource", "yaam://episodes/{episode_id}", "read", action, scope
        )

    @mcp.resource("yaam://knowledge/{knowledge_id}")
    async def knowledge_resource(knowledge_id: str) -> str:
        scope = _resource_scope()

        async def action() -> str:
            knowledge = await (await get_service()).get_knowledge(scope, knowledge_id)
            return _json_or_not_found(knowledge, "knowledge_id", knowledge_id)

        return await _run_mcp_async(
            "resource", "yaam://knowledge/{knowledge_id}", "read", action, scope
        )

    @mcp.resource("yaam://config/ciar")
    def ciar_config_resource() -> str:
        return _run_mcp_sync(
            "resource",
            "yaam://config/ciar",
            "read",
            lambda: json.dumps(
                {
                    "formula": "(certainty * impact) * age_decay * recency_boost",
                    "default_age_decay_lambda": DEFAULT_AGE_DECAY_LAMBDA,
                    "default_recency_alpha": DEFAULT_RECENCY_ALPHA,
                }
            ),
        )

    @mcp.resource("yaam://schemas/fact")
    def fact_schema_resource() -> str:
        return _run_mcp_sync(
            "resource",
            "yaam://schemas/fact",
            "read",
            lambda: json.dumps(Fact.model_json_schema()),
        )

    @mcp.resource("yaam://schemas/episode")
    def episode_schema_resource() -> str:
        return _run_mcp_sync(
            "resource",
            "yaam://schemas/episode",
            "read",
            lambda: json.dumps(Episode.model_json_schema()),
        )

    @mcp.resource("yaam://schemas/knowledge-document")
    def knowledge_schema_resource() -> str:
        return _run_mcp_sync(
            "resource",
            "yaam://schemas/knowledge-document",
            "read",
            lambda: json.dumps(KnowledgeDocument.model_json_schema()),
        )

    @mcp.prompt(name="yaam.prompt.evidence_table")
    def evidence_table_prompt(query: str) -> str:
        return _run_mcp_sync(
            "prompt",
            "yaam.prompt.evidence_table",
            "read",
            lambda: (
                "Create a concise evidence table from YAAM memory for this query. "
                "Use source tier, source id, claim, evidence, score, and provenance columns.\n"
                f"Query: {query}"
            ),
        )

    @mcp.prompt(name="yaam.prompt.memory_inspection")
    def memory_inspection_prompt(session_id: str) -> str:
        scope = _resource_scope(session_id=session_id)
        return _run_mcp_sync(
            "prompt",
            "yaam.prompt.memory_inspection",
            "read",
            lambda: (
                "Inspect YAAM memory without mutation. Summarize visible L1/L2/L3/L4 contents, "
                "gaps, stale items, and confidence signals.\n"
                f"Session: {session_id}"
            ),
            scope=scope,
        )

    @mcp.prompt(name="yaam.prompt.ciar_explanation")
    def ciar_explanation_prompt(claim: str) -> str:
        return _run_mcp_sync(
            "prompt",
            "yaam.prompt.ciar_explanation",
            "read",
            lambda: (
                "Explain CIAR selection or suppression using certainty, impact, age decay, "
                "recency boost, provenance, and policy metadata.\n"
                f"Claim: {claim}"
            ),
        )

    @mcp.prompt(name="yaam.prompt.retrieval_strategy")
    def retrieval_strategy_prompt(task: str) -> str:
        return _run_mcp_sync(
            "prompt",
            "yaam.prompt.retrieval_strategy",
            "read",
            lambda: (
                "Recommend a YAAM retrieval strategy. Pick tiers, filters, scope fields, "
                "evidence visibility, and partial-result handling.\n"
                f"Task: {task}"
            ),
        )

    if "skill-factory" in enabled_domain_packs:
        _register_skill_factory_domain_pack(mcp, get_service)
    if "cognitive-sandwich" in enabled_domain_packs:
        _register_cognitive_sandwich_domain_pack(mcp, get_service)

    return mcp


def _register_skill_factory_domain_pack(
    mcp: Any,
    get_service: Callable[[], Awaitable[MemoryGatewayService]],
) -> None:
    """Register optional read-only Skill Factory MCP resources and prompts."""

    async def domain_service() -> SkillFactoryDomainViewService:
        service = await get_service()
        return SkillFactoryDomainViewService(service, project_id=getattr(service, "project_id", None))

    @mcp.resource("yaam://skills/{skill_name}")
    async def skill_factory_skill_resource(skill_name: str) -> str:
        async def action() -> str:
            view = await (await domain_service()).skill_view(skill_name)
            return json.dumps(view)

        return await _run_mcp_async(
            "resource",
            "yaam://skills/{skill_name}",
            "read",
            action,
            scope=_skill_factory_resource_scope({"skill_name": skill_name}),
        )

    @mcp.resource("yaam://ctts/{ctt_id}")
    async def skill_factory_ctt_resource(ctt_id: str) -> str:
        async def action() -> str:
            view = await (await domain_service()).ctt_view(ctt_id)
            return json.dumps(view)

        return await _run_mcp_async(
            "resource",
            "yaam://ctts/{ctt_id}",
            "read",
            action,
            scope=_skill_factory_resource_scope({"ctt_id": ctt_id}),
        )

    @mcp.resource("yaam://runs/{run_id}/episodes")
    async def skill_factory_run_episodes_resource(run_id: str) -> str:
        async def action() -> str:
            view = await (await domain_service()).run_episodes(run_id)
            return json.dumps(view)

        return await _run_mcp_async(
            "resource",
            "yaam://runs/{run_id}/episodes",
            "read",
            action,
            scope=_skill_factory_resource_scope({"run_id": run_id}),
        )

    @mcp.resource("yaam://skill-factory/qa-status/{qa_status}/runs")
    async def skill_factory_qa_status_resource(qa_status: str) -> str:
        async def action() -> str:
            view = await (await domain_service()).qa_status_runs(qa_status)
            return json.dumps(view)

        return await _run_mcp_async(
            "resource",
            "yaam://skill-factory/qa-status/{qa_status}/runs",
            "read",
            action,
            scope=_skill_factory_resource_scope({"qa_status": qa_status}),
        )

    @mcp.resource("yaam://skill-factory/active-tool-status/{active_tool_status}/runs")
    async def skill_factory_active_tool_status_resource(active_tool_status: str) -> str:
        async def action() -> str:
            view = await (await domain_service()).active_tool_status_runs(active_tool_status)
            return json.dumps(view)

        return await _run_mcp_async(
            "resource",
            "yaam://skill-factory/active-tool-status/{active_tool_status}/runs",
            "read",
            action,
            scope=_skill_factory_resource_scope({"active_tool_status": active_tool_status}),
        )

    @mcp.prompt(name="yaam.prompt.repair_pattern_summary")
    def skill_factory_repair_pattern_summary_prompt(
        skill_name: str,
        ctt_id: str | None = None,
        qa_status: str | None = None,
    ) -> str:
        filters = {
            key: value
            for key, value in {
                "skill_name": skill_name,
                "ctt_id": ctt_id,
                "qa_status": qa_status,
            }.items()
            if value
        }
        return _run_mcp_sync(
            "prompt",
            "yaam.prompt.repair_pattern_summary",
            "read",
            lambda: (
                "Summarize repeated SCM Skill Factory repair patterns without mutating YAAM. "
                "Use only scoped evidence from Skill Factory domain resources, group failures by "
                "CTT, QA status, sandbox outcome, active-tool status, and repair action, then "
                "recommend the next verification step.\n"
                f"Filters: {json.dumps(filters, sort_keys=True)}"
            ),
            scope=_skill_factory_resource_scope(filters),
        )


def _register_cognitive_sandwich_domain_pack(
    mcp: Any,
    get_service: Callable[[], Awaitable[MemoryGatewayService]],
) -> None:
    """Register optional read-only Cognitive Sandwich MCP resources and prompts."""

    async def domain_service() -> CognitiveSandwichDomainViewService:
        service = await get_service()
        return CognitiveSandwichDomainViewService(
            service, project_id=getattr(service, "project_id", None)
        )

    @mcp.resource("yaam://artifacts/{artifact_id}/lineage")
    async def cognitive_artifact_lineage_resource(artifact_id: str) -> str:
        async def action() -> str:
            view = await (await domain_service()).artifact_lineage(artifact_id)
            return json.dumps(view)

        return await _run_mcp_async(
            "resource",
            "yaam://artifacts/{artifact_id}/lineage",
            "read",
            action,
            scope=_cognitive_sandwich_resource_scope({"artifact_id": artifact_id}),
        )

    @mcp.resource("yaam://sessions/{session_id}/artifacts")
    async def cognitive_session_artifacts_resource(session_id: str) -> str:
        async def action() -> str:
            view = await (await domain_service()).session_artifacts(session_id)
            return json.dumps(view)

        return await _run_mcp_async(
            "resource",
            "yaam://sessions/{session_id}/artifacts",
            "read",
            action,
            scope=_cognitive_sandwich_resource_scope({"client_session_id": session_id}),
        )

    @mcp.resource("yaam://runs/{run_id}/artifacts")
    async def cognitive_run_artifacts_resource(run_id: str) -> str:
        async def action() -> str:
            view = await (await domain_service()).run_artifacts(run_id)
            return json.dumps(view)

        return await _run_mcp_async(
            "resource",
            "yaam://runs/{run_id}/artifacts",
            "read",
            action,
            scope=_cognitive_sandwich_resource_scope({"run_id": run_id}),
        )

    @mcp.resource("yaam://runs/{run_id}/evidence")
    async def cognitive_run_evidence_resource(run_id: str) -> str:
        async def action() -> str:
            view = await (await domain_service()).run_evidence(run_id)
            return json.dumps(view)

        return await _run_mcp_async(
            "resource",
            "yaam://runs/{run_id}/evidence",
            "read",
            action,
            scope=_cognitive_sandwich_resource_scope({"run_id": run_id}),
        )

    @mcp.resource("yaam://incidents/{incident_id}/reports")
    async def cognitive_incident_reports_resource(incident_id: str) -> str:
        async def action() -> str:
            view = await (await domain_service()).incident_reports(incident_id)
            return json.dumps(view)

        return await _run_mcp_async(
            "resource",
            "yaam://incidents/{incident_id}/reports",
            "read",
            action,
            scope=_cognitive_sandwich_resource_scope({"incident_id": incident_id}),
        )

    @mcp.prompt(name="yaam.prompt.artifact_repair_context")
    def cognitive_artifact_repair_context_prompt(
        artifact_id: str,
        run_id: str | None = None,
        include_feedback: bool = True,
    ) -> str:
        filters = {
            key: value
            for key, value in {
                "artifact_id": artifact_id,
                "run_id": run_id,
                "include_feedback": include_feedback,
            }.items()
            if value is not None
        }
        return _run_mcp_sync(
            "prompt",
            "yaam.prompt.artifact_repair_context",
            "read",
            lambda: (
                "Build a Cognitive Sandwich artifact repair context without mutating YAAM. "
                "Use only scoped artifact lineage, deterministic solver feedback, sandbox "
                "evidence, and committed report records. Highlight infeasible revisions, "
                "payload hashes, feedback ids, and the next repair constraints.\n"
                f"Filters: {json.dumps(filters, sort_keys=True)}"
            ),
            scope=_cognitive_sandwich_resource_scope(
                {key: str(value) for key, value in filters.items()}
            ),
        )

    @mcp.prompt(name="yaam.prompt.artifact_lineage_summary")
    def cognitive_artifact_lineage_summary_prompt(
        artifact_id: str,
        include_payload_hashes: bool = True,
    ) -> str:
        filters = {
            key: value
            for key, value in {
                "artifact_id": artifact_id,
                "include_payload_hashes": include_payload_hashes,
            }.items()
            if value is not None
        }
        return _run_mcp_sync(
            "prompt",
            "yaam.prompt.artifact_lineage_summary",
            "read",
            lambda: (
                "Summarize Cognitive Sandwich artifact lineage without mutating YAAM. "
                "Order draft, feedback, revision, and commit evidence; include verification "
                "states, source systems, payload hashes when available, and any partial-result "
                "warnings.\n"
                f"Filters: {json.dumps(filters, sort_keys=True)}"
            ),
            scope=_cognitive_sandwich_resource_scope(
                {key: str(value) for key, value in filters.items()}
            ),
        )


class _StreamableHTTPClosedResourceFilter(logging.Filter):
    """Suppress benign MCP SDK noise emitted when HTTP clients close sessions."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name != MCP_STREAMABLE_HTTP_LOGGER:
            return True
        if record.getMessage() != "Error in message router":
            return True
        if record.exc_info is None:
            return True
        exc_type = record.exc_info[0]
        if exc_type is None:
            return True
        is_closed_resource = (
            getattr(exc_type, "__name__", "") == "ClosedResourceError"
            and getattr(exc_type, "__module__", "").startswith("anyio")
        )
        return not is_closed_resource


def _install_streamable_http_closed_resource_filter() -> None:
    logger = logging.getLogger(MCP_STREAMABLE_HTTP_LOGGER)
    if any(isinstance(item, _StreamableHTTPClosedResourceFilter) for item in logger.filters):
        return
    logger.addFilter(_StreamableHTTPClosedResourceFilter())


def _shutdown_mcp_tracing() -> None:
    """Flush and shut down YAAM-owned Phoenix tracing resources."""
    try:
        from src.llm.client import shutdown_phoenix_instrumentation
    except Exception:  # pragma: no cover - optional import safety
        return
    shutdown_phoenix_instrumentation()


async def create_service_from_env(
    config_args: argparse.Namespace | None = None,
) -> MemoryGatewayService:
    """Initialize YAAM runtime state and wrap it in the shared memory service."""
    args = config_args or parse_args([])
    state = await initialize_state(build_config(args))
    service = MemoryGatewayService(
        state.memory_system,
        PermissionPolicy.from_env(),
        project_id=getattr(state, "project_id", None),
    )
    service._mcp_state = state
    return service


async def run_stdio(config_args: argparse.Namespace | None = None) -> None:
    """Run the MCP server over stdio."""
    server = create_mcp_server(config_args=config_args)
    try:
        await server.run_stdio_async()
    finally:
        service = getattr(server, "_service", None)
        state = getattr(service, "_mcp_state", None)
        if state is not None:
            await shutdown_state(state)
        _shutdown_mcp_tracing()


async def run_streamable_http(config_args: argparse.Namespace | None = None) -> None:
    """Run the MCP server over Streamable HTTP."""
    server = create_mcp_server(config_args=config_args)
    try:
        await server.run_streamable_http_async()
    finally:
        service = getattr(server, "_service", None)
        state = getattr(service, "_mcp_state", None)
        if state is not None:
            await shutdown_state(state)
        _shutdown_mcp_tracing()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse MCP runtime arguments with environment-backed defaults."""
    parser = argparse.ArgumentParser(description="Run the YAAM MCP v1 stdio server.")
    parser.add_argument("--agent-type", default=os.environ.get("YAAM_AGENT_TYPE", "full"))
    parser.add_argument("--agent-variant", default=os.environ.get("YAAM_AGENT_VARIANT", "mcp"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("YAAM_PORT", "8000")))
    parser.add_argument("--model", default=os.environ.get("YAAM_MODEL", "gpt-4o-mini"))
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default=os.environ.get("YAAM_MCP_TRANSPORT", "stdio"),
        help="MCP transport to run. Defaults to stdio for MCP host subprocess use.",
    )
    parser.add_argument(
        "--mcp-host",
        default=os.environ.get("YAAM_MCP_HOST", "127.0.0.1"),
        help="Host for Streamable HTTP MCP transport.",
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=int(os.environ.get("YAAM_MCP_PORT", "8081")),
        help="Port for Streamable HTTP MCP transport.",
    )
    parser.add_argument(
        "--mcp-path",
        default=os.environ.get("YAAM_MCP_PATH", "/mcp"),
        help="Path for Streamable HTTP MCP transport.",
    )
    parser.add_argument(
        "--mcp-domain-packs",
        default=os.environ.get("YAAM_MCP_DOMAIN_PACKS", "auto"),
        help="Comma-separated MCP domain packs: auto, none, skill-factory, or cognitive-sandwich.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entrypoint for `python -m src.mcp.server`."""
    args = parse_args(argv)
    if args.transport == "streamable-http":
        asyncio.run(run_streamable_http(args))
    else:
        asyncio.run(run_stdio(args))


def _response(summary: str, structured: dict[str, Any]) -> dict[str, Any]:
    return {"summary": summary, **structured}


def _dump_many(items: list[Any]) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in items]


def _scope(
    session_id: str,
    agent_id: str,
    task_id: str | None = None,
    tenant_id: str | None = None,
    run_id: str | None = None,
    caller_role: str | None = None,
    visibility_scope: str | None = None,
    traceparent: str | None = None,
) -> ScopeEnvelope:
    return ScopeEnvelope(
        session_id=session_id,
        agent_id=agent_id,
        caller_role=caller_role,
        visibility_scope=visibility_scope,
        task_id=task_id,
        tenant_id=tenant_id,
        run_id=run_id,
        traceparent=traceparent,
    )


def _resource_scope(session_id: str = "*") -> ScopeEnvelope:
    return _scope(session_id=session_id, agent_id="resource-reader")


def _skill_factory_resource_scope(domain_ids: dict[str, str]) -> ScopeEnvelope:
    return ScopeEnvelope(
        session_id="*",
        agent_id="skill-factory-domain-pack",
        caller_role="benchmark_runtime_agent",
        visibility_scope="benchmark_runtime",
        domain_ids={key: value for key, value in domain_ids.items() if value},
        metadata={"domain": "skill_factory"},
    )


def _cognitive_sandwich_resource_scope(domain_ids: dict[str, str]) -> ScopeEnvelope:
    return ScopeEnvelope(
        session_id="*",
        agent_id="cognitive-sandwich-domain-pack",
        caller_role="benchmark_runtime_agent",
        visibility_scope="benchmark_runtime",
        domain_ids={key: value for key, value in domain_ids.items() if value},
        metadata={"domain": "cognitive_sandwich"},
    )


def _enabled_domain_packs(args: argparse.Namespace) -> set[str]:
    raw = str(getattr(args, "mcp_domain_packs", "auto") or "auto").strip().lower()
    if raw in {"", "none", "off", "disabled"}:
        return set()
    requested = {item.strip() for item in raw.split(",") if item.strip()}
    if "none" in requested:
        return set()
    if "auto" in requested:
        project_id = normalize_project_id(os.environ.get("YAAM_PROJECT_ID", "test"))
        requested.remove("auto")
        if project_id == "scm-skill-factory":
            requested.add("skill-factory")
        if project_id == "scm-cognitive-sandwich":
            requested.add("cognitive-sandwich")
    return {item for item in requested if item in {"skill-factory", "cognitive-sandwich"}}


def _json_or_not_found(item: Any, id_name: str, id_value: str) -> str:
    if item is None:
        return json.dumps({"status": "not_found", id_name: id_value})
    if hasattr(item, "model_dump_json"):
        return item.model_dump_json()
    return json.dumps(item)


async def _run_mcp_async(
    surface: str,
    operation: str,
    operation_mode: str,
    action: Callable[[], Awaitable[Any]],
    scope: ScopeEnvelope | None = None,
    *,
    scope_provider: Callable[[], ScopeEnvelope | None] | None = None,
    error_cls: type[Exception] | None = None,
) -> Any:
    started_at = perf_counter()
    with start_span(
        tracer_name="yaam.mcp",
        span_name=f"yaam.mcp.{surface}.{operation}",
        kind="TOOL",
        attributes=_mcp_trace_attributes(surface, operation, operation_mode, scope),
    ) as span:
        try:
            result = await action()
        except Exception as exc:
            active_scope = _active_scope(scope, scope_provider)
            payload = _mcp_error_payload(exc, operation, active_scope, span)
            set_span_error(span, exc)
            set_span_attributes(
                span,
                {
                    **_mcp_trace_attributes(surface, operation, operation_mode, active_scope),
                    "yaam.status": "error",
                    "yaam.error_code": payload.code,
                    "yaam.partial": payload.partial,
                    "yaam.latency_ms": _elapsed_ms(started_at),
                },
            )
            raise _mcp_exception(payload, error_cls) from exc

        active_scope = _active_scope(scope, scope_provider)
        set_span_attributes(
            span,
            {
                **_mcp_trace_attributes(surface, operation, operation_mode, active_scope),
                **_mcp_result_trace_attributes(result),
                "yaam.status": "success",
                "yaam.latency_ms": _elapsed_ms(started_at),
            },
        )
        return result


def _run_mcp_sync(
    surface: str,
    operation: str,
    operation_mode: str,
    action: Callable[[], Any],
    scope: ScopeEnvelope | None = None,
) -> Any:
    started_at = perf_counter()
    with start_span(
        tracer_name="yaam.mcp",
        span_name=f"yaam.mcp.{surface}.{operation}",
        kind="TOOL",
        attributes=_mcp_trace_attributes(surface, operation, operation_mode, scope),
    ) as span:
        try:
            result = action()
        except Exception as exc:
            payload = _mcp_error_payload(exc, operation, scope, span)
            set_span_error(span, exc)
            set_span_attributes(
                span,
                {
                    **_mcp_trace_attributes(surface, operation, operation_mode, scope),
                    "yaam.status": "error",
                    "yaam.error_code": payload.code,
                    "yaam.partial": payload.partial,
                    "yaam.latency_ms": _elapsed_ms(started_at),
                },
            )
            raise _mcp_exception(payload) from exc

        set_span_attributes(
            span,
            {
                **_mcp_trace_attributes(surface, operation, operation_mode, scope),
                **_mcp_result_trace_attributes(result),
                "yaam.status": "success",
                "yaam.latency_ms": _elapsed_ms(started_at),
            },
        )
        return result


def _mcp_trace_attributes(
    surface: str,
    operation: str,
    operation_mode: str,
    scope: ScopeEnvelope | None = None,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {
        "yaam.interface": "MCP",
        "yaam.mcp.surface": surface,
        "yaam.operation": operation,
        "yaam.operation_mode": operation_mode,
    }
    if scope is None:
        return attributes
    attributes.update(
        {
            "session.id": scope.session_id,
            "yaam.agent_id": scope.agent_id,
            "yaam.caller_role": scope.caller_role or "",
            "yaam.visibility_scope": scope.visibility_scope or "",
            "yaam.task_id": scope.task_id or "",
            "yaam.tenant_id": scope.tenant_id or "",
            "yaam.run_id": scope.run_id or "",
            "yaam.traceparent.present": bool(scope.traceparent),
        }
    )
    return attributes


def _mcp_result_trace_attributes(result: Any) -> dict[str, Any]:
    payload = _payload_for_trace(result)
    attributes: dict[str, Any] = {
        "yaam.partial": _extract_partial(payload),
        "yaam.warning_count": _extract_warning_count(payload),
        "yaam.result_count": _extract_result_count(payload),
    }
    source_ids = _extract_source_ids(payload)
    if source_ids:
        attributes["yaam.source_ids"] = source_ids
    health_status = _extract_health_status(payload)
    if health_status:
        attributes["yaam.health.status"] = health_status
    return attributes


def _payload_for_trace(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return result
    return result


def _extract_partial(payload: Any) -> bool:
    if isinstance(payload, dict):
        for key in ("context", "evidence_table", "health", "review", "leakage_guard"):
            nested = payload.get(key)
            if isinstance(nested, dict) and bool(nested.get("partial")):
                return True
        return bool(payload.get("partial"))
    return False


def _extract_warning_count(payload: Any) -> int:
    if isinstance(payload, dict):
        count = len(payload.get("warnings", [])) if isinstance(payload.get("warnings"), list) else 0
        for key in ("context", "evidence_table", "health", "review", "leakage_guard"):
            nested = payload.get(key)
            if isinstance(nested, dict) and isinstance(nested.get("warnings"), list):
                count += len(nested["warnings"])
        return count
    return 0


def _extract_result_count(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, str):
        return 1
    if not isinstance(payload, dict):
        return 1 if payload is not None else 0
    if isinstance(payload.get("results"), list):
        return len(payload["results"])
    if isinstance(payload.get("decisions"), list):
        return len(payload["decisions"])
    if isinstance(payload.get("correlations"), list):
        return len(payload["correlations"])
    if isinstance(payload.get("items"), list):
        return len(payload["items"])
    if isinstance(payload.get("context"), dict) and isinstance(payload["context"].get("items"), list):
        return len(payload["context"]["items"])
    if isinstance(payload.get("evidence_table"), dict) and isinstance(
        payload["evidence_table"].get("rows"), list
    ):
        return len(payload["evidence_table"]["rows"])
    if isinstance(payload.get("review"), dict):
        return len(payload["review"].get("supporting_evidence", [])) + len(
            payload["review"].get("conflicting_evidence", [])
        )
    if "ack" in payload or "explanation" in payload or "health" in payload or "leakage_guard" in payload:
        return 1
    return 1 if payload else 0


def _extract_source_ids(payload: Any) -> list[str]:
    source_ids: list[str] = []
    _collect_source_ids(payload, source_ids)
    return sorted(set(source_ids))


def _collect_source_ids(payload: Any, source_ids: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_source_ids(item, source_ids)
        return
    if not isinstance(payload, dict):
        return
    source_id = payload.get("source_id")
    if source_id:
        source_ids.append(str(source_id))
    provenance = payload.get("provenance")
    if isinstance(provenance, dict) and provenance.get("source_id"):
        source_ids.append(str(provenance["source_id"]))
    ack = payload.get("ack")
    if isinstance(ack, dict):
        for key in ("created_id", "updated_id"):
            if ack.get(key):
                source_ids.append(str(ack[key]))
    for value in payload.values():
        if isinstance(value, dict | list):
            _collect_source_ids(value, source_ids)


def _extract_health_status(payload: Any) -> str | None:
    if isinstance(payload, dict):
        if isinstance(payload.get("health"), dict):
            return payload["health"].get("status")
        return payload.get("status") if "tiers" in payload else None
    return None


def _mcp_error_payload(
    exc: Exception,
    operation: str,
    scope: ScopeEnvelope | None,
    span: Any,
) -> YAAMErrorPayload:
    trace_metadata = current_trace_metadata(span)
    trace_id = trace_metadata.get("yaam_trace_id")
    if isinstance(exc, YAAMPermissionError):
        payload = exc.payload
        return payload.model_copy(
            update={
                "operation": payload.operation or operation,
                "trace_id": payload.trace_id or trace_id,
            }
        )
    if isinstance(exc, ValidationError):
        return YAAMErrorPayload(
            code="validation.invalid_scope",
            message="MCP request scope or arguments failed validation.",
            retryable=False,
            operation=operation,
            affected_tier="SYSTEM",
            trace_id=trace_id,
            details=redact_metadata({"errors": _json_safe(exc.errors(include_url=False))}),
        )
    details: dict[str, Any] = {"exception_type": type(exc).__name__}
    if scope is not None:
        details["scope"] = scope.model_dump(mode="json", exclude_none=True)
    return YAAMErrorPayload(
        code="mcp.operation_failed",
        message="MCP operation failed.",
        retryable=False,
        operation=operation,
        affected_tier="SYSTEM",
        trace_id=trace_id,
        details=redact_metadata(details),
    )


def _mcp_exception(
    payload: YAAMErrorPayload,
    error_cls: type[Exception] | None = None,
) -> Exception:
    message = json.dumps({"error": payload.model_dump(mode="json")}, separators=(",", ":"))
    if error_cls is not None:
        return error_cls(message)
    return RuntimeError(message)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str, ensure_ascii=True))


def _active_scope(
    scope: ScopeEnvelope | None,
    scope_provider: Callable[[], ScopeEnvelope | None] | None,
) -> ScopeEnvelope | None:
    if scope is not None:
        return scope
    return scope_provider() if scope_provider is not None else None


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)


if __name__ == "__main__":
    main()
