"""
Memory module for multi-layered cognitive memory system.

This module contains:
- Memory tier implementations (L1-L4)
- Data models (Fact, Episode, Knowledge)
- Memory engines (Promotion, Consolidation, Distillation) - Coming in Phase 2B-D
"""

from .models import Fact, FactType, FactCategory, FactQuery

__all__ = [
    'Fact',
    'FactType',
    'FactCategory',
    'FactQuery'
]
