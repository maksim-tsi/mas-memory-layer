"""
Agent tools package.

High-level tools for LangGraph agents interacting with the
MAS Memory Layer.
"""

from .unified_tools import memory_query, get_context_block, memory_store, UNIFIED_TOOLS
from .ciar_tools import ciar_calculate, ciar_filter, ciar_explain, CIAR_TOOLS
from .tier_tools import l2_search_facts, l3_query_graph, l3_search_episodes, l4_search_knowledge, TIER_TOOLS
from .synthesis_tools import synthesize_knowledge, SYNTHESIS_TOOLS

__all__ = [
    # Unified tools (Week 2)
    'memory_query',
    'get_context_block',
    'memory_store',
    'UNIFIED_TOOLS',
    # CIAR tools (Week 3)
    'ciar_calculate',
    'ciar_filter',
    'ciar_explain',
    'CIAR_TOOLS',
    # Tier-specific tools (Week 3)
    'l2_search_facts',
    'l3_query_graph',
    'l3_search_episodes',
    'l4_search_knowledge',
    'TIER_TOOLS',
    # Synthesis tools (Week 3)
    'synthesize_knowledge',
    'SYNTHESIS_TOOLS',
]

# All tools combined for easy registration
ALL_TOOLS = UNIFIED_TOOLS + CIAR_TOOLS + TIER_TOOLS + SYNTHESIS_TOOLS

