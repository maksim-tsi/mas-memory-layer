"""
Unified memory tools for MAS agents.

These tools provide high-level memory operations that abstract
over the four-tier architecture. All tools use ToolRuntime for
context injection (session_id, user_id) per ADR-007.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.agents.runtime import MASToolRuntime
from src.memory.models import SearchWeights

if TYPE_CHECKING:
    # For type hints only - actual tool decorator will be from langchain-core
    from langchain_core.tools import tool, ToolRuntime
else:
    try:
        from langchain_core.tools import tool
        # ToolRuntime will be injected by LangGraph at execution time
        ToolRuntime = Any
    except ImportError:
        # Fallback for environments without langchain-core
        def tool(*args, **kwargs):
            """Fallback tool decorator."""
            def decorator(func):
                func.name = func.__name__
                func.description = func.__doc__ or ""
                func.args_schema = kwargs.get('args_schema')
                func.func = func
                return func
            if args and callable(args[0]):
                return decorator(args[0])
            return decorator
        ToolRuntime = Any


# --- Tool Input Schemas ---

class MemoryQueryInput(BaseModel):
    """Input schema for memory_query tool."""
    query: str = Field(description="Natural language query to search memory")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    l2_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight for L2 Working Memory (default: 0.3)")
    l3_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Weight for L3 Episodic Memory (default: 0.5)")
    l4_weight: float = Field(default=0.2, ge=0.0, le=1.0, description="Weight for L4 Semantic Memory (default: 0.2)")


class GetContextBlockInput(BaseModel):
    """Input schema for get_context_block tool."""
    min_ciar: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum CIAR score for facts (0.0-1.0, default: 0.6)"
    )
    max_turns: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum recent turns to include (default: 20)"
    )
    max_facts: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum facts to include (default: 10)"
    )
    format: str = Field(
        default="structured",
        description="Output format: 'structured' (dict) or 'text' (formatted string)"
    )


class MemoryStoreInput(BaseModel):
    """Input schema for memory_store tool."""
    content: str = Field(description="Content to store in memory")
    tier: str = Field(
        default="auto",
        description="Target tier: 'auto' (system decides), 'L1' (active context), 'L2' (working memory)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata for the memory item"
    )


# --- Unified Tools ---

@tool(args_schema=MemoryQueryInput)
async def memory_query(
    query: str,
    limit: int = 10,
    l2_weight: float = 0.3,
    l3_weight: float = 0.5,
    l4_weight: float = 0.2,
    runtime: ToolRuntime = None
) -> str:
    """
    Search across all memory tiers for information matching the query.
    
    This tool performs hybrid semantic search across Working Memory (L2),
    Episodic Memory (L3), and Semantic Memory (L4), returning ranked results
    based on configurable weights.
    
    Use this when you need to:
    - Find past information relevant to the current conversation
    - Retrieve facts, episodes, or knowledge related to a topic
    - Search the agent's long-term memory
    
    Args:
        query: Natural language search query
        limit: Maximum number of results to return (1-50)
        l2_weight: Importance weight for recent facts (0.0-1.0)
        l3_weight: Importance weight for past episodes (0.0-1.0)
        l4_weight: Importance weight for distilled knowledge (0.0-1.0)
    
    Returns:
        Formatted search results with content, source tier, and relevance scores
    """
    # Wrap runtime in MAS helper
    mas_runtime = MASToolRuntime(runtime)
    session_id = mas_runtime.get_session_id()
    memory_system = mas_runtime.get_memory_system()
    
    if not memory_system:
        return "Error: Memory system not available"
    
    # Stream status update
    await mas_runtime.stream_status(f"Searching memory for: {query}")
    
    # Validate weights sum to 1.0
    total_weight = l2_weight + l3_weight + l4_weight
    if abs(total_weight - 1.0) > 0.01:
        # Normalize weights
        l2_weight = l2_weight / total_weight
        l3_weight = l3_weight / total_weight
        l4_weight = l4_weight / total_weight
    
    # Create weights config
    weights = SearchWeights(
        l2_weight=l2_weight,
        l3_weight=l3_weight,
        l4_weight=l4_weight
    )
    
    try:
        # Execute hybrid search
        results = await memory_system.query_memory(
            session_id=session_id,
            query=query,
            limit=limit,
            weights=weights
        )
        
        if not results:
            return f"No results found for query: {query}"
        
        # Format results for LLM
        formatted_results = [f"# Memory Search Results ({len(results)} found)\n"]
        formatted_results.append(f"Query: {query}\n")
        
        for i, result in enumerate(results, 1):
            tier = result['tier']
            score = result['score']
            content = result['content']
            
            # Truncate long content
            if len(content) > 200:
                content = content[:197] + "..."
            
            formatted_results.append(f"\n{i}. [{tier}] (score: {score:.3f})")
            formatted_results.append(f"   {content}")
            
            # Add relevant metadata
            metadata = result.get('metadata', {})
            if tier == 'L2' and 'fact_type' in metadata:
                formatted_results.append(f"   Type: {metadata['fact_type']}, CIAR: {metadata.get('ciar_score', 'N/A')}")
            elif tier == 'L3' and 'topics' in metadata:
                topics = ', '.join(metadata['topics'][:3])
                formatted_results.append(f"   Topics: {topics}, Facts: {metadata.get('fact_count', 0)}")
            elif tier == 'L4' and 'knowledge_type' in metadata:
                formatted_results.append(f"   Type: {metadata['knowledge_type']}, Confidence: {metadata.get('confidence_score', 'N/A')}")
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Error searching memory: {str(e)}"


@tool(args_schema=GetContextBlockInput)
async def get_context_block(
    min_ciar: float = 0.6,
    max_turns: int = 20,
    max_facts: int = 10,
    format: str = "structured",
    runtime: ToolRuntime = None
) -> str:
    """
    Retrieve a focused context block for the current conversation.
    
    This tool assembles recent conversation turns and high-importance facts
    into a structured context block suitable for prompt injection or review.
    
    Use this when you need to:
    - Summarize the current conversation context
    - Get recent turns and important facts in one call
    - Prepare context for complex reasoning tasks
    
    Args:
        min_ciar: Minimum CIAR score for facts (0.0-1.0, higher = more important)
        max_turns: Maximum recent turns to include
        max_facts: Maximum facts to include
        format: Output format ('structured' or 'text')
    
    Returns:
        Context block in requested format
    """
    mas_runtime = MASToolRuntime(runtime)
    session_id = mas_runtime.get_session_id()
    memory_system = mas_runtime.get_memory_system()
    
    if not memory_system:
        return "Error: Memory system not available"
    
    await mas_runtime.stream_status("Assembling context block...")
    
    try:
        # Retrieve context block
        context = await memory_system.get_context_block(
            session_id=session_id,
            min_ciar=min_ciar,
            max_turns=max_turns,
            max_facts=max_facts
        )
        
        if format == "text":
            # Return formatted text for prompt injection
            return context.to_prompt_string(include_metadata=True)
        else:
            # Return structured summary
            summary = [
                f"# Context Block (Session: {session_id[:8]}...)",
                f"\nRecent Turns: {context.turn_count}",
                f"Significant Facts: {context.fact_count} (min CIAR: {min_ciar})",
                f"Estimated Tokens: {context.estimated_tokens or 'N/A'}",
                f"\nAssembled: {context.assembled_at.isoformat()}"
            ]
            
            if context.significant_facts:
                summary.append("\n## Top Facts:")
                for i, fact in enumerate(context.significant_facts[:5], 1):
                    fact_preview = fact.content[:100] + "..." if len(fact.content) > 100 else fact.content
                    summary.append(f"{i}. [{fact.fact_type or 'N/A'}] {fact_preview} (CIAR: {fact.ciar_score:.2f})")
            
            return "\n".join(summary)
        
    except Exception as e:
        return f"Error retrieving context block: {str(e)}"


@tool(args_schema=MemoryStoreInput)
async def memory_store(
    content: str,
    tier: str = "auto",
    metadata: Optional[Dict[str, Any]] = None,
    runtime: ToolRuntime = None
) -> str:
    """
    Store information in memory for future retrieval.
    
    This tool stores content in the appropriate memory tier based on
    the tier parameter. Use 'auto' to let the system decide the best tier.
    
    Use this when you need to:
    - Remember important information from the conversation
    - Store user preferences or constraints
    - Cache computed results for later use
    
    Args:
        content: The information to store
        tier: Target tier ('auto', 'L1', or 'L2')
        metadata: Optional metadata dict (tags, type, etc.)
    
    Returns:
        Confirmation message with storage location
    """
    mas_runtime = MASToolRuntime(runtime)
    session_id = mas_runtime.get_session_id()
    memory_system = mas_runtime.get_memory_system()
    
    if not memory_system:
        return "Error: Memory system not available"
    
    await mas_runtime.stream_status(f"Storing content in tier {tier}...")
    
    try:
        # Determine target tier
        if tier == "auto":
            # Simple heuristic: short content -> L1, longer -> L2
            tier = "L1" if len(content) < 200 else "L2"
        
        tier = tier.upper()
        
        if tier == "L1":
            # Store in Active Context (L1)
            if memory_system.l1_tier:
                # Create turn-like structure
                turn_data = {
                    "role": "system",
                    "content": content,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": metadata or {}
                }
                await memory_system.l1_tier.store(session_id, turn_data)
                return f"Stored in L1 Active Context (session: {session_id[:8]}...)"
            else:
                return "Error: L1 tier not available"
        
        elif tier == "L2":
            # Store in Working Memory (L2) - requires promotion/extraction
            # For now, store via L1 and let promotion engine handle it
            if memory_system.l1_tier:
                turn_data = {
                    "role": "system",
                    "content": f"[STORE] {content}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {**(metadata or {}), "store_request": True}
                }
                await memory_system.l1_tier.store(session_id, turn_data)
                return "Queued for L2 storage (will be promoted via next cycle)"
            else:
                return "Error: L1 tier not available for L2 promotion queue"
        
        else:
            return f"Error: Invalid tier '{tier}'. Use 'auto', 'L1', or 'L2'"
        
    except Exception as e:
        return f"Error storing content: {str(e)}"


# Export tools
UNIFIED_TOOLS = [memory_query, get_context_block, memory_store]

__all__ = [
    'memory_query',
    'get_context_block',
    'memory_store',
    'UNIFIED_TOOLS',
    'MemoryQueryInput',
    'GetContextBlockInput',
    'MemoryStoreInput'
]

