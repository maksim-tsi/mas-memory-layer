"""
Knowledge Synthesis Tools for Agent L4 Distillation (ADR-007).

Provides LangChain-compatible tools for synthesizing knowledge from L4
Semantic Memory. These tools wrap the KnowledgeSynthesizer for query-time
knowledge retrieval and LLM-powered synthesis.

Tools:
- synthesize_knowledge: Retrieve and synthesize knowledge documents with conflict detection
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


# ============================================================================
# Input Schemas (Pydantic Models)
# ============================================================================

class SynthesizeKnowledgeInput(BaseModel):
    """Input schema for synthesize_knowledge tool."""
    query: str = Field(
        description="Query or context for knowledge synthesis (e.g., 'What are common causes of port delays?')"
    )
    metadata_filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Domain-specific metadata filters (e.g., {'port_code': 'USLAX', 'carrier': 'MAERSK'})"
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum knowledge documents to synthesize"
    )


# ============================================================================
# Tool Implementations
# ============================================================================

@tool(args_schema=SynthesizeKnowledgeInput)
async def synthesize_knowledge(
    query: str,
    metadata_filters: Optional[Dict[str, Any]] = None,
    max_results: int = 5,
    runtime: ToolRuntime = None
) -> str:
    """
    Synthesize knowledge from L4 Semantic Memory using LLM-powered synthesis.
    
    This tool retrieves relevant knowledge documents from L4 (distilled
    patterns, rules, insights) and uses an LLM to synthesize a coherent
    response tailored to your query.
    
    Features:
    - Metadata-first filtering for domain-specific knowledge
    - Cosine similarity ranking within filtered groups
    - Conflict detection (surfaces contradictory knowledge)
    - Short-TTL caching (1 hour) for repeated queries
    - Provenance tracking (shows source episodes)
    
    Use this when you need:
    - General knowledge about patterns or rules
    - Synthesized insights across multiple episodes
    - Understanding of contradictions in knowledge base
    
    Returns JSON with synthesized text, source documents, conflicts, and metadata.
    """
    try:
        mas_runtime = MASToolRuntime(runtime)
        memory_system = mas_runtime.get_memory_system()
        
        if not memory_system:
            return "Error: Memory system not available in runtime context"
        
        await mas_runtime.stream_status(f"Synthesizing knowledge for: {query[:50]}...")
        
        # Check if memory system has knowledge synthesizer
        if not hasattr(memory_system, 'knowledge_synthesizer'):
            return json.dumps({
                'error': 'Knowledge synthesizer not available',
                'message': 'The memory system does not have a knowledge synthesizer configured. This requires L4 tier and LLM provider setup.',
                'workaround': 'Use l4_search_knowledge tool for direct L4 queries without synthesis'
            }, indent=2)
        
        # Get knowledge synthesizer
        synthesizer = memory_system.knowledge_synthesizer
        
        # Execute synthesis
        result = await synthesizer.synthesize(
            query=query,
            metadata_filters=metadata_filters,
            max_results=max_results
        )
        
        # Check for errors
        if result.get('status') == 'error':
            return json.dumps({
                'error': result.get('error'),
                'query': query,
                'metadata_filters': metadata_filters
            }, indent=2)
        
        # Format successful response
        response = {
            'query': query,
            'metadata_filters': metadata_filters,
            'synthesized_text': result.get('synthesized_text'),
            'source': result.get('source'),  # 'synthesized' or 'cached'
            'candidates': result.get('candidates'),
            'has_conflicts': result.get('has_conflicts', False),
            'conflicts': result.get('conflicts', []),
            'elapsed_ms': result.get('elapsed_ms'),
            'cache_hit': result.get('source') == 'cached'
        }
        
        # Add conflict warning if present
        if response['has_conflicts']:
            response['warning'] = (
                f"⚠️  {len(response['conflicts'])} conflicting knowledge documents detected. "
                "Review 'conflicts' field for details."
            )
        
        return json.dumps(response, indent=2, default=str)
        
    except Exception as e:
        return f"Error synthesizing knowledge: {str(e)}"


# ============================================================================
# Tool Metadata (for export)
# ============================================================================

SYNTHESIS_TOOLS = [synthesize_knowledge]
