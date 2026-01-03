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

from typing import Any, Dict, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
import json

from langchain_core.tools import tool

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig as ToolRuntime
else:
    try:
        from langchain_core.runnables import RunnableConfig as ToolRuntime
    except ImportError:
        ToolRuntime = Any

from src.agents.runtime import MASToolRuntime
from src.memory.graph_templates import get_template, validate_and_execute_template


# ============================================================================
# Input Schemas (Pydantic Models)
# ============================================================================

class L2SearchFactsInput(BaseModel):
    """Input schema for l2_search_facts tool."""
    query: str = Field(
        description="Search query for PostgreSQL tsvector (e.g., 'MAEU1234567', 'Port of Los Angeles', 'customs delay')"
    )
    min_ciar: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum CIAR score (default: tier threshold 0.6)"
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum results"
    )


class L3QueryGraphInput(BaseModel):
    """Input schema for l3_query_graph tool."""
    template_name: str = Field(
        description="Template name: 'get_container_journey', 'get_shipment_parties', 'find_delay_causes', 'get_document_flow', 'get_related_episodes', 'get_entity_timeline'"
    )
    parameters: Dict[str, Any] = Field(
        description="Template parameters as key-value dict (e.g., {'container_id': 'MAEU1234567', 'max_hops': 15})"
    )


class L3SearchEpisodesInput(BaseModel):
    """Input schema for l3_search_episodes tool."""
    query: str = Field(
        description="Natural language query to find similar episodes (will be embedded)"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum results"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional Qdrant filters (e.g., {'session_id': 'session-123'})"
    )


class L4SearchKnowledgeInput(BaseModel):
    """Input schema for l4_search_knowledge tool."""
    query: str = Field(
        description="Search query for knowledge base (full-text search)"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional Typesense filters (e.g., {'knowledge_type': 'pattern', 'category': 'delays'})"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum results"
    )


# ============================================================================
# Tool Implementations
# ============================================================================

@tool(args_schema=L2SearchFactsInput)
async def l2_search_facts(
    query: str,
    min_ciar: Optional[float] = None,
    limit: int = 20,
    runtime: ToolRuntime = None
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
        memory_system = mas_runtime.get_memory_system()
        
        if not memory_system:
            return "Error: Memory system not available in runtime context"
        
        await mas_runtime.stream_status(f"Searching L2 Working Memory for: {query}")
        
        # Get L2 tier
        l2_tier = memory_system.working_memory
        if not l2_tier:
            return "Error: L2 Working Memory tier not initialized"
        
        # Execute tsvector search
        facts = await l2_tier.search_facts(
            query=query,
            session_id=session_id,
            min_ciar=min_ciar,
            limit=limit
        )
        
        # Format results
        if not facts:
            return json.dumps({
                'query': query,
                'session_id': session_id,
                'results_count': 0,
                'message': 'No facts found matching query with minimum CIAR threshold',
                'facts': []
            }, indent=2)
        
        results = {
            'query': query,
            'session_id': session_id,
            'min_ciar_threshold': min_ciar or l2_tier.ciar_threshold,
            'results_count': len(facts),
            'facts': [
                {
                    'fact_id': f.fact_id,
                    'content': f.content,
                    'fact_type': f.fact_type.value if hasattr(f.fact_type, 'value') else f.fact_type,
                    'ciar_score': round(f.ciar_score, 4),
                    'certainty': round(f.certainty, 4),
                    'impact': round(f.impact, 4),
                    'created_at': f.created_at.isoformat() if f.created_at else None,
                    'access_count': f.access_count
                }
                for f in facts
            ]
        }
        
        return json.dumps(results, indent=2)
        
    except Exception as e:
        return f"Error searching L2 facts: {str(e)}"


@tool(args_schema=L3QueryGraphInput)
async def l3_query_graph(
    template_name: str,
    parameters: Dict[str, Any],
    runtime: ToolRuntime = None
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
        memory_system = mas_runtime.get_memory_system()
        
        if not memory_system:
            return "Error: Memory system not available in runtime context"
        
        await mas_runtime.stream_status(f"Executing Neo4j template: {template_name}")
        
        # Validate template and parameters
        is_valid, error_msg, cypher_query = validate_and_execute_template(
            name=template_name,
            params=parameters
        )
        
        if not is_valid:
            return f"Error: {error_msg}"
        
        # Get L3 tier
        l3_tier = memory_system.episodic_memory
        if not l3_tier:
            return "Error: L3 Episodic Memory tier not initialized"
        
        # Get template for parameter merging
        template = get_template(template_name)
        merged_params = template.merge_params(parameters)
        
        # Execute query
        results = await l3_tier.query_graph(
            cypher_query=cypher_query,
            parameters=merged_params
        )
        
        # Format response
        response = {
            'template': template_name,
            'parameters': merged_params,
            'session_id': session_id,
            'results_count': len(results),
            'results': results
        }
        
        return json.dumps(response, indent=2, default=str)
        
    except Exception as e:
        return f"Error querying L3 graph: {str(e)}"


@tool(args_schema=L3SearchEpisodesInput)
async def l3_search_episodes(
    query: str,
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    runtime: ToolRuntime = None
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
        memory_system = mas_runtime.get_memory_system()
        
        if not memory_system:
            return "Error: Memory system not available in runtime context"
        
        await mas_runtime.stream_status(f"Searching L3 episodes for: {query}")
        
        # Get L3 tier
        l3_tier = memory_system.episodic_memory
        if not l3_tier:
            return "Error: L3 Episodic Memory tier not initialized"
        
        # Note: This requires embedding generation which is not yet implemented
        # For now, return a placeholder error
        return json.dumps({
            'error': 'Episode embedding search not yet implemented',
            'message': 'This tool requires LLM embedding generation which will be added in Phase 3 Week 4',
            'query': query,
            'session_id': session_id,
            'workaround': 'Use l3_query_graph with get_related_episodes template for now'
        }, indent=2)
        
    except Exception as e:
        return f"Error searching L3 episodes: {str(e)}"


@tool(args_schema=L4SearchKnowledgeInput)
async def l4_search_knowledge(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 10,
    runtime: ToolRuntime = None
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
        memory_system = mas_runtime.get_memory_system()
        
        if not memory_system:
            return "Error: Memory system not available in runtime context"
        
        await mas_runtime.stream_status(f"Searching L4 knowledge base for: {query}")
        
        # Get L4 tier
        l4_tier = memory_system.semantic_memory
        if not l4_tier:
            return "Error: L4 Semantic Memory tier not initialized"
        
        # Execute search
        documents = await l4_tier.search(
            query_text=query,
            filters=filters,
            limit=limit
        )
        
        # Format results
        if not documents:
            return json.dumps({
                'query': query,
                'filters': filters,
                'results_count': 0,
                'message': 'No knowledge documents found matching query',
                'documents': []
            }, indent=2)
        
        results = {
            'query': query,
            'filters': filters,
            'results_count': len(documents),
            'documents': [
                {
                    'knowledge_id': doc.knowledge_id,
                    'title': doc.title,
                    'content': doc.content[:500] + '...' if len(doc.content) > 500 else doc.content,
                    'knowledge_type': doc.knowledge_type.value if hasattr(doc.knowledge_type, 'value') else doc.knowledge_type,
                    'confidence_score': round(doc.confidence_score, 4),
                    'episode_count': doc.episode_count,
                    'category': doc.category,
                    'tags': doc.tags,
                    'created_at': doc.created_at.isoformat() if doc.created_at else None
                }
                for doc in documents
            ]
        }
        
        return json.dumps(results, indent=2)
        
    except Exception as e:
        return f"Error searching L4 knowledge: {str(e)}"


# ============================================================================
# Tool Metadata (for export)
# ============================================================================

TIER_TOOLS = [l2_search_facts, l3_query_graph, l3_search_episodes, l4_search_knowledge]
