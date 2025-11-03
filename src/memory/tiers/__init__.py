"""
Memory tier implementations for four-tier cognitive architecture (ADR-003).

This package contains the tier abstraction layer that sits between agents
and storage adapters, implementing tier-specific logic for each memory level:

- L1 (Active Context): Working memory buffer for recent turns
- L2 (Working Memory): Significance-filtered facts with CIAR scoring
- L3 (Episodic Memory): Hybrid vector+graph episode store
- L4 (Semantic Memory): Distilled knowledge patterns

Each tier coordinates one or more storage adapters and implements
tier-specific logic (windowing, filtering, consolidation, etc.)
"""

from .base_tier import BaseTier, MemoryTierError, TierConfigurationError, TierOperationError
from .active_context_tier import ActiveContextTier
from .working_memory_tier import WorkingMemoryTier

__all__ = [
    'BaseTier',
    'MemoryTierError',
    'TierConfigurationError',
    'TierOperationError',
    'ActiveContextTier',
    'WorkingMemoryTier'
]
