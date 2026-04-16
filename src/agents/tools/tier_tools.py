"""
Tier-Specific Memory Tools for Agent Access (ADR-007).

Provides LangChain-compatible tools for direct access to individual memory
tiers (L2, L3, L4). These tools give agents fine-grained control over which
tier to query when the unified cross-tier search is not appropriate.

Use Cases:
- L2: Fast keyword search for specific SKUs, container IDs, error codes
- L3: Graph traversal for relationship queries (using templates)
- L3: Vector search for "find similar past episodes"
- L4: Full-text search of distilled knowledge base

Tools:
- l2_search_facts: PostgreSQL tsvector keyword search
- l3_query_graph: Template-based Neo4j Cypher queries
- l3_search_episodes: Qdrant vector similarity search
- l4_search_knowledge: Typesense full-text knowledge search
"""

import json
from typing import TYPE_CHECKING, Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig as ToolRuntime
else:
    try:
        from langchain_core.runnables import RunnableConfig as ToolRuntime
    except ImportError:
        ToolRuntime = Any

from src.agents.runtime import MASToolRuntime
from src.memory.graph_templates import get_template, validate_and_execute_template
from src.observability import set_span_attributes, set_span_error, start_span


def _get_memory_component(memory_system: Any, *attribute_names: str) -> Any | None:
    """Resolve a memory-system component across current and legacy attribute names."""
    for attribute_name in attribute_names:
        component = getattr(memory_system, attribute_name, None)
        if component is not None:
            return component
    return None


def _fact_to_retrieval_document(fact: Any) -> dict[str, Any]:
    """Serialize an L2 fact into retriever evidence format."""
    return {
        "document.id": f"L2:{getattr(fact, 'fact_id', 'unknown')}",
        "document.content": getattr(fact, "content", ""),
        "document.score": getattr(fact, "ciar_score", None),
        "document.metadata": {
            "tier": "L2",
            "session_id": getattr(fact, "session_id", None),
            "fact_type": getattr(fact, "fact_type", None),
            "access_count": getattr(fact, "access_count", None),
        },
    }


def _episode_to_retrieval_document(episode: Any) -> dict[str, Any]:
    """Serialize an L3 episode into retriever evidence format."""
    return {
        "document.id": f"L3:{getattr(episode, 'episode_id', 'unknown')}",
        "document.content": getattr(episode, "summary", ""),
        "document.score": float(
            getattr(episode, "metadata", {}).get(
                "similarity_score", getattr(episode, "importance_score", 0.0)
            )
        ),
        "document.metadata": {
            "tier": "L3",
            "session_id": getattr(episode, "session_id", None),
            "fact_count": getattr(episode, "fact_count", None),
            "topics": getattr(episode, "topics", []),
        },
    }


def _knowledge_to_retrieval_document(document: Any) -> dict[str, Any]:
    """Serialize an L4 knowledge document into retriever evidence format."""
    return {
        "document.id": f"L4:{getattr(document, 'knowledge_id', 'unknown')}",
        "document.content": getattr(document, "content", ""),
        "document.score": float(
            getattr(document, "metadata", {}).get(
                "search_score", getattr(document, "confidence_score", 0.0)
            )
        ),
        "document.metadata": {
            "tier": "L4",
            "session_id": getattr(document, "session_id", None),
            "title": getattr(document, "title", None),
            "knowledge_type": getattr(document, "knowledge_type", None),
            "tags": getattr(document, "tags", []),
        },
    }


def _tool_attributes(session_id: str, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Build shared TOOL span attributes."""
    return {
        "session.id": session_id,
        "input.value": payload,
        "yaam.tool.name": tool_name,
    }


def _record_tool_output(span: Any, output_value: str, results_count: int | None = None) -> str:
    """Attach tool output metadata before returning the JSON payload."""
    attributes: dict[str, Any] = {"output.value": output_value}
    if results_count is not None:
        attributes["yaam.results_count"] = results_count
    set_span_attributes(span, attributes)
    return output_value


# ============================================================================
# Input Schemas (Pydantic Models)
# ============================================================================


class L2SearchFactsInput(BaseModel):
    """Input schema for l2_search_facts tool."""

    query: str = Field(
        description="Search query for PostgreSQL tsvector (e.g., 'MAEU1234567', 'Port of Los Angeles', 'customs delay')"
    )
    min_ciar: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Minimum CIAR score (default: tier threshold 0.6)"
    )
    limit: int = Field(default=20, ge=1, le=100, description="Maximum results")


class L3QueryGraphInput(BaseModel):
    """Input schema for l3_query_graph tool."""

    template_name: str = Field(
        description="Template name: 'get_container_journey', 'get_shipment_parties', 'find_delay_causes', 'get_document_flow', 'get_related_episodes', 'get_entity_timeline'"
    )
    parameters: dict[str, Any] = Field(
        description="Template parameters as key-value dict (e.g., {'container_id': 'MAEU1234567', 'max_hops': 15})"
    )


class L3SearchEpisodesInput(BaseModel):
    """Input schema for l3_search_episodes tool."""

    query: str = Field(
        description="Natural language query to find similar episodes (will be embedded)"
    )
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results")
    filters: dict[str, Any] | None = Field(
        default=None, description="Optional Qdrant filters (e.g., {'session_id': 'session-123'})"
    )


class L4SearchKnowledgeInput(BaseModel):
    """Input schema for l4_search_knowledge tool."""

    query: str = Field(description="Search query for knowledge base (full-text search)")
    filters: dict[str, Any] | None = Field(
        default=None,
        description="Optional Typesense filters (e.g., {'knowledge_type': 'pattern', 'category': 'delays'})",
    )
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results")


# ============================================================================
# Tool Implementations
# ============================================================================


@tool(args_schema=L2SearchFactsInput)
async def l2_search_facts(
    query: str, min_ciar: float | None = None, limit: int = 20, runtime: ToolRuntime = None
) -> str:
    """
    Search L2 Working Memory for facts using PostgreSQL full-text search.

    This is the FAST keyword search tool for finding specific entities,
    SKUs, container IDs, error codes, and exact phrases in working memory.
    Uses PostgreSQL tsvector with 'simple' config (no stemming) for exact
    matching in polyglot supply chain context.

    Use this when you need:
    - Exact keyword matches (e.g., "MAEU1234567")
    - Fast lookups without external API calls
    - Current/recent session facts only

    Returns JSON with matching facts, relevance scores, and metadata.
    """
    try:
        mas_runtime = MASToolRuntime(runtime)
        session_id = mas_runtime.get_session_id()
        with start_span(
            tracer_name="yaam.agent.tools",
            span_name="yaam.tool.l2_search_facts",
            kind="TOOL",
            attributes=_tool_attributes(
                session_id,
                "l2_search_facts",
                {"query": query, "min_ciar": min_ciar, "limit": limit},
            ),
        ) as tool_span:
            memory_system = mas_runtime.get_memory_system()

            if not memory_system:
                return _record_tool_output(
                    tool_span, "Error: Memory system not available in runtime context"
                )

            await mas_runtime.stream_status(f"Searching L2 Working Memory for: {query}")

            l2_tier = _get_memory_component(memory_system, "l2_tier", "working_memory")
            if not l2_tier:
                return _record_tool_output(
                    tool_span, "Error: L2 Working Memory tier not initialized"
                )

            with start_span(
                tracer_name="yaam.agent.tools",
                span_name="yaam.retriever.l2",
                kind="RETRIEVER",
                attributes={
                    "session.id": session_id,
                    "input.value": query,
                    "yaam.tool.name": "l2_search_facts",
                    "yaam.retrieval.limit": limit,
                },
            ) as retriever_span:
                facts = await l2_tier.search_facts(
                    query=query, session_id=session_id, min_ciar=min_ciar, limit=limit
                )
                set_span_attributes(
                    retriever_span,
                    {
                        "retrieval.documents": [
                            _fact_to_retrieval_document(fact) for fact in facts
                        ],
                        "yaam.retrieval.result_count": len(facts),
                        "yaam.ciar.threshold": min_ciar or l2_tier.ciar_threshold,
                    },
                )

            if not facts:
                output = json.dumps(
                    {
                        "query": query,
                        "session_id": session_id,
                        "results_count": 0,
                        "message": "No facts found matching query with minimum CIAR threshold",
                        "facts": [],
                    },
                    indent=2,
                )
                return _record_tool_output(tool_span, output, results_count=0)

            results = {
                "query": query,
                "session_id": session_id,
                "min_ciar_threshold": min_ciar or l2_tier.ciar_threshold,
                "results_count": len(facts),
                "facts": [
                    {
                        "fact_id": f.fact_id,
                        "content": f.content,
                        "fact_type": f.fact_type.value
                        if hasattr(f.fact_type, "value")
                        else f.fact_type,
                        "ciar_score": round(f.ciar_score, 4),
                        "certainty": round(f.certainty, 4),
                        "impact": round(f.impact, 4),
                        "created_at": f.created_at.isoformat() if f.created_at else None,
                        "access_count": f.access_count,
                    }
                    for f in facts
                ],
            }

            return _record_tool_output(
                tool_span, json.dumps(results, indent=2), results_count=len(facts)
            )

    except Exception as e:
        set_span_error(locals().get("tool_span"), e)
        return f"Error searching L2 facts: {e!s}"


@tool(args_schema=L3QueryGraphInput)
async def l3_query_graph(
    template_name: str, parameters: dict[str, Any], runtime: ToolRuntime = None
) -> str:
    """
    Query L3 Episodic Memory graph using predefined Neo4j Cypher templates.

    This tool enforces SAFE, template-based graph queries with hard-coded
    temporal validity (factValidTo IS NULL) to prevent temporal amnesia.

    Available templates (for container logistics):
    - get_container_journey: Track container movements through ports/vessels
    - get_shipment_parties: Find shipper, consignee, carrier relationships
    - find_delay_causes: Causal chain of shipment delays
    - get_document_flow: Bill of lading, customs, delivery docs
    - get_related_episodes: Episodes involving entity in time window
    - get_entity_timeline: Chronological events for container/shipment

    All templates use parameter injection ($param) to prevent Cypher injection.
    Raw Cypher queries are NOT allowed for security and temporal correctness.

    Returns JSON with query results and metadata.
    """
    try:
        mas_runtime = MASToolRuntime(runtime)
        session_id = mas_runtime.get_session_id()
        with start_span(
            tracer_name="yaam.agent.tools",
            span_name="yaam.tool.l3_query_graph",
            kind="TOOL",
            attributes=_tool_attributes(
                session_id,
                "l3_query_graph",
                {"template_name": template_name, "parameters": parameters},
            ),
        ) as tool_span:
            memory_system = mas_runtime.get_memory_system()

            if not memory_system:
                return _record_tool_output(
                    tool_span, "Error: Memory system not available in runtime context"
                )

            await mas_runtime.stream_status(f"Executing Neo4j template: {template_name}")

            is_valid, error_msg, cypher_query = validate_and_execute_template(
                name=template_name, params=parameters
            )

            if not is_valid:
                return _record_tool_output(tool_span, f"Error: {error_msg}")

            l3_tier = _get_memory_component(memory_system, "l3_tier", "episodic_memory")
            if not l3_tier:
                return _record_tool_output(
                    tool_span, "Error: L3 Episodic Memory tier not initialized"
                )

            template = get_template(template_name)
            merged_params = template.merge_params(parameters)
            results = await l3_tier.query_graph(cypher_query=cypher_query, parameters=merged_params)

            response = {
                "template": template_name,
                "parameters": merged_params,
                "session_id": session_id,
                "results_count": len(results),
                "results": results,
            }

            set_span_attributes(
                tool_span,
                {
                    "yaam.graph.template": template_name,
                    "yaam.results_count": len(results),
                },
            )
            return _record_tool_output(
                tool_span,
                json.dumps(response, indent=2, default=str),
                results_count=len(results),
            )

    except Exception as e:
        set_span_error(locals().get("tool_span"), e)
        return f"Error querying L3 graph: {e!s}"


@tool(args_schema=L3SearchEpisodesInput)
async def l3_search_episodes(
    query: str,
    limit: int = 10,
    filters: dict[str, Any] | None = None,
    runtime: ToolRuntime = None,
) -> str:
    """
    Search L3 Episodic Memory for similar episodes using vector similarity.

    This tool finds semantically similar past episodes (consolidated fact
    clusters) using Qdrant's approximate nearest neighbor search.

    Use this when you need:
    - "Find similar past situations" queries
    - Semantic search across historical episodes
    - Pattern matching across time

    The query will be embedded and compared against episode embeddings in
    Qdrant's vector index.

    Returns JSON with similar episodes, similarity scores, and summaries.
    """
    try:
        mas_runtime = MASToolRuntime(runtime)
        session_id = mas_runtime.get_session_id()
        with start_span(
            tracer_name="yaam.agent.tools",
            span_name="yaam.tool.l3_search_episodes",
            kind="TOOL",
            attributes=_tool_attributes(
                session_id,
                "l3_search_episodes",
                {"query": query, "limit": limit, "filters": filters},
            ),
        ) as tool_span:
            memory_system = mas_runtime.get_memory_system()

            if not memory_system:
                return _record_tool_output(
                    tool_span, "Error: Memory system not available in runtime context"
                )

            await mas_runtime.stream_status(f"Searching L3 episodes for: {query}")

            l3_tier = _get_memory_component(memory_system, "l3_tier", "episodic_memory")
            if not l3_tier:
                return _record_tool_output(
                    tool_span, "Error: L3 Episodic Memory tier not initialized"
                )

            llm_client = _get_memory_component(memory_system, "llm_client")
            if not llm_client:
                return _record_tool_output(
                    tool_span, "Error: LLM client not available for L3 episode search"
                )

            search_filters = dict(filters or {})
            search_filters["session_id"] = session_id

            with start_span(
                tracer_name="yaam.agent.tools",
                span_name="yaam.retriever.l3",
                kind="RETRIEVER",
                attributes={
                    "session.id": session_id,
                    "input.value": query,
                    "yaam.tool.name": "l3_search_episodes",
                    "yaam.retrieval.limit": limit,
                },
            ) as retriever_span:
                query_embedding = await llm_client.get_embedding(query)
                episodes = await l3_tier.search_similar(
                    query_embedding=query_embedding,
                    limit=limit,
                    filters=search_filters,
                )
                set_span_attributes(
                    retriever_span,
                    {
                        "retrieval.documents": [
                            _episode_to_retrieval_document(episode) for episode in episodes
                        ],
                        "yaam.retrieval.result_count": len(episodes),
                    },
                )

            if not episodes:
                output = json.dumps(
                    {
                        "query": query,
                        "session_id": session_id,
                        "filters": search_filters,
                        "results_count": 0,
                        "message": "No similar episodes found",
                        "episodes": [],
                    },
                    indent=2,
                )
                return _record_tool_output(tool_span, output, results_count=0)

            results = {
                "query": query,
                "session_id": session_id,
                "filters": search_filters,
                "results_count": len(episodes),
                "episodes": [
                    {
                        "episode_id": episode.episode_id,
                        "summary": episode.summary,
                        "narrative": episode.narrative,
                        "fact_count": episode.fact_count,
                        "importance_score": round(episode.importance_score, 4),
                        "similarity_score": round(
                            float(episode.metadata.get("similarity_score", 0.0)), 4
                        ),
                        "topics": episode.topics,
                        "time_window_start": episode.time_window_start.isoformat(),
                        "time_window_end": episode.time_window_end.isoformat(),
                    }
                    for episode in episodes
                ],
            }

            return _record_tool_output(
                tool_span,
                json.dumps(results, indent=2),
                results_count=len(episodes),
            )

    except Exception as e:
        set_span_error(locals().get("tool_span"), e)
        return f"Error searching L3 episodes: {e!s}"


@tool(args_schema=L4SearchKnowledgeInput)
async def l4_search_knowledge(
    query: str,
    filters: dict[str, Any] | None = None,
    limit: int = 10,
    runtime: ToolRuntime = None,
) -> str:
    """
    Search L4 Semantic Memory for distilled knowledge using full-text search.

    This tool searches the permanent knowledge base of generalized patterns,
    rules, and insights distilled from L3 episodes.

    Use this when you need:
    - General knowledge patterns (not specific episodes)
    - Best practices or learned rules
    - Cross-session insights

    Uses Typesense for typo-tolerant, faceted full-text search with ranking.

    Returns JSON with knowledge documents, confidence scores, and provenance.
    """
    try:
        mas_runtime = MASToolRuntime(runtime)
        session_id = mas_runtime.get_session_id()
        with start_span(
            tracer_name="yaam.agent.tools",
            span_name="yaam.tool.l4_search_knowledge",
            kind="TOOL",
            attributes=_tool_attributes(
                session_id,
                "l4_search_knowledge",
                {"query": query, "filters": filters, "limit": limit},
            ),
        ) as tool_span:
            memory_system = mas_runtime.get_memory_system()

            if not memory_system:
                return _record_tool_output(
                    tool_span, "Error: Memory system not available in runtime context"
                )

            await mas_runtime.stream_status(f"Searching L4 knowledge base for: {query}")

            l4_tier = _get_memory_component(memory_system, "l4_tier", "semantic_memory")
            if not l4_tier:
                return _record_tool_output(
                    tool_span, "Error: L4 Semantic Memory tier not initialized"
                )

            with start_span(
                tracer_name="yaam.agent.tools",
                span_name="yaam.retriever.l4",
                kind="RETRIEVER",
                attributes={
                    "session.id": session_id,
                    "input.value": query,
                    "yaam.tool.name": "l4_search_knowledge",
                    "yaam.retrieval.limit": limit,
                },
            ) as retriever_span:
                documents = await l4_tier.search(query_text=query, filters=filters, limit=limit)
                set_span_attributes(
                    retriever_span,
                    {
                        "retrieval.documents": [
                            _knowledge_to_retrieval_document(doc) for doc in documents
                        ],
                        "yaam.retrieval.result_count": len(documents),
                    },
                )

            if not documents:
                output = json.dumps(
                    {
                        "query": query,
                        "filters": filters,
                        "results_count": 0,
                        "message": "No knowledge documents found matching query",
                        "documents": [],
                    },
                    indent=2,
                )
                return _record_tool_output(tool_span, output, results_count=0)

            results = {
                "query": query,
                "filters": filters,
                "results_count": len(documents),
                "documents": [
                    {
                        "knowledge_id": doc.knowledge_id,
                        "title": doc.title,
                        "content": doc.content[:500] + "..."
                        if len(doc.content) > 500
                        else doc.content,
                        "knowledge_type": doc.knowledge_type.value
                        if hasattr(doc.knowledge_type, "value")
                        else doc.knowledge_type,
                        "confidence_score": round(doc.confidence_score, 4),
                        "search_score": round(float(doc.metadata.get("search_score", 0.0)), 4),
                        "episode_count": doc.episode_count,
                        "category": doc.category,
                        "tags": doc.tags,
                        "distilled_at": doc.distilled_at.isoformat() if doc.distilled_at else None,
                    }
                    for doc in documents
                ],
            }

            return _record_tool_output(
                tool_span,
                json.dumps(results, indent=2),
                results_count=len(documents),
            )

    except Exception as e:
        set_span_error(locals().get("tool_span"), e)
        return f"Error searching L4 knowledge: {e!s}"


# ============================================================================
# Tool Metadata (for export)
# ============================================================================

TIER_TOOLS = [l2_search_facts, l3_query_graph, l3_search_episodes, l4_search_knowledge]
