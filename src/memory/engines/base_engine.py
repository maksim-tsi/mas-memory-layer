"""
Base engine interface for all lifecycle engines.

This module defines the abstract BaseEngine class that all concrete engines
(Promotion, Consolidation, Distillation) must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

from src.storage.metrics.collector import MetricsCollector

logger = logging.getLogger(__name__)


class EngineError(Exception):
    """Base exception for engine operations."""
    pass


class BaseEngine(ABC):
    """
    Abstract base class for all lifecycle engines.

    Engines are responsible for moving data between tiers:
    - PromotionEngine: L1 -> L2
    - ConsolidationEngine: L2 -> L3
    - DistillationEngine: L3 -> L4
    """

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        self.metrics = metrics_collector or MetricsCollector()
        self._is_running = False

    @abstractmethod
    async def process(self) -> Dict[str, Any]:
        """
        Execute one cycle of the engine's logic.

        Returns:
            Dict[str, Any]: Summary of the operation (e.g., items processed).
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the engine and its dependencies.

        Returns:
            Dict[str, Any]: Health status report.
        """
        pass

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Retrieve current metrics for the engine.

        Returns:
            Dict[str, Any]: Current metrics.
        """
        return await self.metrics.get_metrics()
