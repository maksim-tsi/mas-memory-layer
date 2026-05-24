"""MCP v1 server wiring for YAAM memory operations."""

import argparse
import asyncio
import json
import os
from collections.abc import Sequence
from typing import Any

from src.evaluation.agent_wrapper import build_config, initialize_state, shutdown_state
from src.memory.ciar_formula import DEFAULT_AGE_DECAY_LAMBDA, DEFAULT_RECENCY_ALPHA
from src.memory.models import Episode, Fact, KnowledgeDocument, SearchWeights
from src.memory.services import MemoryGatewayService, PermissionPolicy, ScopeEnvelope

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
    "yaam.health.check",
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
    except ImportError as exc:
        raise RuntimeError(
            f"YAAM MCP v1 requires the official Python SDK dependency: {MCP_SDK_REQUIREMENT}."
        ) from exc

    mcp = FastMCP("yaam-mcp-v1")
    runtime_service = service

    async def get_service() -> MemoryGatewayService:
        nonlocal runtime_service
        if runtime_service is None:
            runtime_service = await create_service_from_env(config_args)
            mcp._service = runtime_service
        return runtime_service

    if runtime_service is not None:
        mcp._service = runtime_service

    @mcp.tool(name="yaam.memory.query")
    async def memory_query(
        session_id: str,
        agent_id: str,
        query: str,
        limit: int = 10,
        task_id: str | None = None,
        tenant_id: str | None = None,
        run_id: str | None = None,
        l2_weight: float = 0.3,
        l3_weight: float = 0.5,
        l4_weight: float = 0.2,
    ) -> dict[str, Any]:
        scope = ScopeEnvelope(
            session_id=session_id,
            agent_id=agent_id,
            task_id=task_id,
            tenant_id=tenant_id,
            run_id=run_id,
        )
        weights = SearchWeights(
            l2_weight=l2_weight,
            l3_weight=l3_weight,
            l4_weight=l4_weight,
        )
        results = await (await get_service()).query_memory(
            scope, query=query, limit=limit, weights=weights
        )
        return _response("Memory query complete.", {"results": _dump_many(results)})

    @mcp.tool(name="yaam.memory.get_context")
    async def memory_get_context(
        session_id: str,
        agent_id: str,
        task_id: str | None = None,
        min_ciar: float = 0.6,
        max_turns: int = 20,
        max_facts: int = 10,
    ) -> dict[str, Any]:
        scope = ScopeEnvelope(session_id=session_id, agent_id=agent_id, task_id=task_id)
        context = await (await get_service()).get_context(
            scope,
            min_ciar=min_ciar,
            max_turns=max_turns,
            max_facts=max_facts,
        )
        return _response("Context assembled.", {"context": context.model_dump(mode="json")})

    @mcp.tool(name="yaam.l2.store_fact")
    async def l2_store_fact(
        session_id: str,
        agent_id: str,
        content: str,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scope = ScopeEnvelope(session_id=session_id, agent_id=agent_id, task_id=task_id)
        ack = await (await get_service()).store_l2_fact(scope, content=content, metadata=metadata)
        return _response("Fact stored.", {"ack": ack.model_dump(mode="json")})

    @mcp.tool(name="yaam.l2.search_facts")
    async def l2_search_facts(
        session_id: str,
        agent_id: str,
        query: str | None = None,
        min_ciar: float | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        scope = ScopeEnvelope(session_id=session_id, agent_id=agent_id)
        results = await (await get_service()).search_l2_facts(
            scope,
            query=query,
            min_ciar=min_ciar,
            limit=limit,
        )
        return _response("L2 facts retrieved.", {"results": _dump_many(results)})

    @mcp.tool(name="yaam.l3.search_episodes")
    async def l3_search_episodes(
        session_id: str,
        agent_id: str,
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        scope = ScopeEnvelope(session_id=session_id, agent_id=agent_id)
        results = await (await get_service()).search_l3_episodes(scope, query=query, limit=limit)
        return _response("L3 episodes retrieved.", {"results": _dump_many(results)})

    @mcp.tool(name="yaam.l3.assimilate_episode")
    async def l3_assimilate_episode(
        session_id: str,
        agent_id: str,
        text_to_assimilate: str,
        task_id: str | None = None,
        domain_tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scope = ScopeEnvelope(session_id=session_id, agent_id=agent_id, task_id=task_id)
        ack = await (await get_service()).assimilate_l3_episode(
            scope,
            text_to_assimilate=text_to_assimilate,
            domain_tags=domain_tags,
            metadata=metadata,
        )
        return _response("Episode assimilated.", {"ack": ack.model_dump(mode="json")})

    @mcp.tool(name="yaam.l4.search_knowledge")
    async def l4_search_knowledge(
        session_id: str,
        agent_id: str,
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        scope = ScopeEnvelope(session_id=session_id, agent_id=agent_id)
        results = await (await get_service()).search_l4_knowledge(scope, query=query, limit=limit)
        return _response("L4 knowledge retrieved.", {"results": _dump_many(results)})

    @mcp.tool(name="yaam.l4.finalize_artifact")
    async def l4_finalize_artifact(
        session_id: str,
        agent_id: str,
        title: str,
        final_artifact: str,
        task_id: str | None = None,
        consensus_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scope = ScopeEnvelope(session_id=session_id, agent_id=agent_id, task_id=task_id)
        ack = await (await get_service()).finalize_l4_artifact(
            scope,
            title=title,
            final_artifact=final_artifact,
            consensus_metadata=consensus_metadata,
        )
        return _response("L4 artifact finalized.", {"ack": ack.model_dump(mode="json")})

    @mcp.tool(name="yaam.ciar.explain")
    async def ciar_explain(
        session_id: str,
        agent_id: str,
        certainty: float = 0.0,
        impact: float = 0.0,
        age_decay: float = 1.0,
        recency_boost: float = 1.0,
    ) -> dict[str, Any]:
        scope = ScopeEnvelope(session_id=session_id, agent_id=agent_id)
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

    @mcp.tool(name="yaam.evidence.table")
    async def evidence_table(
        session_id: str,
        agent_id: str,
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        scope = ScopeEnvelope(session_id=session_id, agent_id=agent_id)
        table = await (await get_service()).evidence_table(scope, query=query, limit=limit)
        return _response(
            "Evidence table assembled.", {"evidence_table": table.model_dump(mode="json")}
        )

    @mcp.tool(name="yaam.health.check")
    async def health_check() -> dict[str, Any]:
        health = await (await get_service()).health_check()
        return _response("Health checked.", {"health": health.model_dump(mode="json")})

    @mcp.resource("yaam://health")
    async def health_resource() -> str:
        health = await (await get_service()).health_check()
        return health.model_dump_json()

    @mcp.resource("yaam://sessions/{session_id}/context")
    async def session_context_resource(session_id: str) -> str:
        service_instance = await get_service()
        scope = ScopeEnvelope(session_id=session_id, agent_id="resource-reader")
        context = await service_instance.get_context(scope)
        return context.model_dump_json()

    @mcp.resource("yaam://sessions/{session_id}/facts")
    async def session_facts_resource(session_id: str) -> str:
        service_instance = await get_service()
        scope = ScopeEnvelope(session_id=session_id, agent_id="resource-reader")
        facts = await service_instance.search_l2_facts(scope)
        return json.dumps(_dump_many(facts))

    @mcp.resource("yaam://facts/{fact_id}")
    async def fact_resource(fact_id: str) -> str:
        fact = await (await get_service()).get_fact(_resource_scope(), fact_id)
        return _json_or_not_found(fact, "fact_id", fact_id)

    @mcp.resource("yaam://episodes/{episode_id}")
    async def episode_resource(episode_id: str) -> str:
        episode = await (await get_service()).get_episode(_resource_scope(), episode_id)
        return _json_or_not_found(episode, "episode_id", episode_id)

    @mcp.resource("yaam://knowledge/{knowledge_id}")
    async def knowledge_resource(knowledge_id: str) -> str:
        knowledge = await (await get_service()).get_knowledge(_resource_scope(), knowledge_id)
        return _json_or_not_found(knowledge, "knowledge_id", knowledge_id)

    @mcp.resource("yaam://config/ciar")
    def ciar_config_resource() -> str:
        return json.dumps(
            {
                "formula": "(certainty * impact) * age_decay * recency_boost",
                "default_age_decay_lambda": DEFAULT_AGE_DECAY_LAMBDA,
                "default_recency_alpha": DEFAULT_RECENCY_ALPHA,
            }
        )

    @mcp.resource("yaam://schemas/fact")
    def fact_schema_resource() -> str:
        return json.dumps(Fact.model_json_schema())

    @mcp.resource("yaam://schemas/episode")
    def episode_schema_resource() -> str:
        return json.dumps(Episode.model_json_schema())

    @mcp.resource("yaam://schemas/knowledge-document")
    def knowledge_schema_resource() -> str:
        return json.dumps(KnowledgeDocument.model_json_schema())

    @mcp.prompt(name="yaam.prompt.evidence_table")
    def evidence_table_prompt(query: str) -> str:
        return (
            "Create a concise evidence table from YAAM memory for this query. "
            "Use source tier, source id, claim, evidence, score, and provenance columns.\n"
            f"Query: {query}"
        )

    @mcp.prompt(name="yaam.prompt.memory_inspection")
    def memory_inspection_prompt(session_id: str) -> str:
        return (
            "Inspect YAAM memory without mutation. Summarize visible L1/L2/L3/L4 contents, "
            "gaps, stale items, and confidence signals.\n"
            f"Session: {session_id}"
        )

    @mcp.prompt(name="yaam.prompt.ciar_explanation")
    def ciar_explanation_prompt(claim: str) -> str:
        return (
            "Explain CIAR selection or suppression using certainty, impact, age decay, "
            "recency boost, provenance, and policy metadata.\n"
            f"Claim: {claim}"
        )

    @mcp.prompt(name="yaam.prompt.retrieval_strategy")
    def retrieval_strategy_prompt(task: str) -> str:
        return (
            "Recommend a YAAM retrieval strategy. Pick tiers, filters, scope fields, "
            "evidence visibility, and partial-result handling.\n"
            f"Task: {task}"
        )

    return mcp


async def create_service_from_env(
    config_args: argparse.Namespace | None = None,
) -> MemoryGatewayService:
    """Initialize YAAM runtime state and wrap it in the shared memory service."""
    args = config_args or parse_args([])
    state = await initialize_state(build_config(args))
    service = MemoryGatewayService(state.memory_system, PermissionPolicy.from_env())
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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse MCP runtime arguments with environment-backed defaults."""
    parser = argparse.ArgumentParser(description="Run the YAAM MCP v1 stdio server.")
    parser.add_argument("--agent-type", default=os.environ.get("YAAM_AGENT_TYPE", "full"))
    parser.add_argument("--agent-variant", default=os.environ.get("YAAM_AGENT_VARIANT", "mcp"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("YAAM_PORT", "8000")))
    parser.add_argument("--model", default=os.environ.get("YAAM_MODEL", "gpt-4o-mini"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entrypoint for `python -m src.mcp.server`."""
    asyncio.run(run_stdio(parse_args(argv)))


def _response(summary: str, structured: dict[str, Any]) -> dict[str, Any]:
    return {"summary": summary, **structured}


def _dump_many(items: list[Any]) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in items]


def _resource_scope() -> ScopeEnvelope:
    return ScopeEnvelope(session_id="*", agent_id="resource-reader")


def _json_or_not_found(item: Any, id_name: str, id_value: str) -> str:
    if item is None:
        return json.dumps({"status": "not_found", id_name: id_value})
    if hasattr(item, "model_dump_json"):
        return item.model_dump_json()
    return json.dumps(item)


if __name__ == "__main__":
    main()
