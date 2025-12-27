"""
Base tier interface for all memory tiers in ADR-003 architecture.

This module defines the abstract BaseTier class that all concrete memory
tiers (L1-L4) must implement. It provides a uniform API for agents to
interact with memory without knowing the underlying storage details.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from src.storage.base import StorageAdapter
from src.storage.metrics.collector import MetricsCollector


logger = logging.getLogger(__name__)


class MemoryTierError(Exception):
    """Base exception for memory tier operations."""
    pass


class TierConfigurationError(MemoryTierError):
    """Raised when tier configuration is invalid."""
    pass


class TierOperationError(MemoryTierError):
    """Raised when tier operation fails."""
    pass


class BaseTier(ABC):
    """
    Abstract base class for all memory tiers.
    
    Each tier wraps one or more storage adapters and implements
    tier-specific logic such as:
    - Turn windowing (L1)
    - CIAR significance filtering (L2)
    - Dual-indexing coordination (L3)
    - Knowledge provenance (L4)
    
    All methods are async to support non-blocking operations.
    
    Usage Example:
        ```python
        tier = ConcreteMemoryTier(
            storage_adapters={'redis': redis_adapter},
            metrics_collector=metrics,
            config={'window_size': 20}
        )
        
        # Store data
        id = await tier.store(data)
        
        # Retrieve data
        result = await tier.retrieve(id)
        
        # Check health
        health = await tier.health_check()
        ```
    """
    
    def __init__(
        self,
        storage_adapters: Dict[str, StorageAdapter],
        metrics_collector: Optional[MetricsCollector] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize base tier.
        
        Args:
            storage_adapters: Dict mapping storage names to adapter instances
                Example: {'redis': redis_adapter, 'postgres': postgres_adapter}
            metrics_collector: Optional metrics collector for observability
            config: Tier-specific configuration parameters
                Example: {'window_size': 20, 'ttl_hours': 24}
        
        Raises:
            TierConfigurationError: If configuration is invalid
        """
        if not storage_adapters:
            raise TierConfigurationError("At least one storage adapter is required")
        
        self.storage_adapters = storage_adapters
        self.metrics = metrics_collector or MetricsCollector()
        self.config = config or {}
        self._initialized = False
        
        logger.info(
            f"Initialized {self.__class__.__name__} with storage: "
            f"{list(storage_adapters.keys())}"
        )
    
    @abstractmethod
    async def store(self, data: Dict[str, Any]) -> str:
        """
        Store data in this tier.
        
        Args:
            data: Data to store (format varies by tier)
                L1: {'session_id', 'turn_id', 'role', 'content', ...}
                L2: {'fact_id', 'content', 'ciar_score', ...}
                L3: {'episode_id', 'summary', 'embedding', ...}
                L4: {'knowledge_id', 'pattern', 'confidence', ...}
        
        Returns:
            Unique identifier for stored data
        
        Raises:
            TierOperationError: If storage operation fails
            StorageError: If underlying storage fails
        """
        pass
    
    @abstractmethod
    async def retrieve(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data by identifier.
        
        Args:
            identifier: Unique identifier (format varies by tier)
                L1: session_id
                L2: fact_id
                L3: episode_id
                L4: knowledge_id
        
        Returns:
            Retrieved data or None if not found
        
        Raises:
            TierOperationError: If retrieval operation fails
        """
        pass
    
    @abstractmethod
    async def query(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Query data with optional filters.
        
        Args:
            filters: Query filters (format varies by tier)
                L1: {'session_id': str, 'role': str}
                L2: {'ciar_score_gt': float, 'age_hours_lt': int}
                L3: {'time_window_start': datetime, 'entity_type': str}
                L4: {'knowledge_type': str, 'confidence_gt': float}
            limit: Maximum number of results
            **kwargs: Additional tier-specific parameters
                - order_by: Sort field
                - offset: Pagination offset
                - include_metadata: Include extended metadata
        
        Returns:
            List of matching records (newest first by default)
        
        Raises:
            TierOperationError: If query operation fails
        """
        pass
    
    @abstractmethod
    async def delete(self, identifier: str) -> bool:
        """
        Delete data by identifier.
        
        Args:
            identifier: Unique identifier to delete
        
        Returns:
            True if deleted, False if not found
        
        Raises:
            TierOperationError: If deletion fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all underlying storage adapters.
        
        Returns:
            Health status dictionary with format:
            {
                'tier': str,  # Tier name (e.g., 'L1_active_context')
                'status': str,  # 'healthy' | 'degraded' | 'unhealthy'
                'timestamp': str,  # ISO timestamp
                'storage': {
                    'adapter_name': {
                        'status': str,
                        'latency_ms': float,
                        'message': str (optional)
                    },
                    ...
                }
            }
        """
        pass
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get tier-specific metrics.
        
        Returns:
            Metrics dictionary with tier operations and performance data:
            {
                'operations': {
                    'total_count': int,
                    'success_count': int,
                    'error_count': int,
                    'success_rate': float
                },
                'latency': {
                    'avg_ms': float,
                    'p50_ms': float,
                    'p95_ms': float,
                    'p99_ms': float
                },
                'tier_specific': Dict  # Tier-specific metrics
            }
        """
        base_metrics = await self.metrics.get_metrics()
        
        return {
            'tier': self.__class__.__name__,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metrics': base_metrics
        }
    
    async def initialize(self) -> None:
        """
        Initialize tier and all storage adapters.
        
        This method should be called before using the tier for the first time.
        It ensures all storage connections are established and ready.
        
        Raises:
            TierOperationError: If initialization fails
        """
        if self._initialized:
            logger.warning(f"{self.__class__.__name__} already initialized")
            return
        
        try:
            logger.info(f"Initializing {self.__class__.__name__}...")
            
            # Connect all storage adapters
            for name, adapter in self.storage_adapters.items():
                logger.debug(f"Connecting to {name}...")
                await adapter.connect()
            
            self._initialized = True
            logger.info(f"{self.__class__.__name__} initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.__class__.__name__}: {e}")
            raise TierOperationError(f"Initialization failed: {e}") from e
    
    async def cleanup(self) -> None:
        """
        Clean up tier resources and disconnect storage adapters.
        
        This method should be called when the tier is no longer needed.
        It ensures all connections are properly closed.
        """
        if not self._initialized:
            return
        
        try:
            logger.info(f"Cleaning up {self.__class__.__name__}...")
            
            # Disconnect all storage adapters
            for name, adapter in self.storage_adapters.items():
                logger.debug(f"Disconnecting from {name}...")
                await adapter.disconnect()
            
            self._initialized = False
            logger.info(f"{self.__class__.__name__} cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during {self.__class__.__name__} cleanup: {e}")
            raise TierOperationError(f"Cleanup failed: {e}") from e
    
    def is_initialized(self) -> bool:
        """Check if tier is initialized and ready for use."""
        return self._initialized
    
    def get_storage_adapter(self, name: str) -> Optional[StorageAdapter]:
        """
        Get a specific storage adapter by name.
        
        Args:
            name: Storage adapter name (e.g., 'redis', 'postgres')
        
        Returns:
            Storage adapter instance or None if not found
        """
        return self.storage_adapters.get(name)
    
    async def __aenter__(self):
        """Context manager entry - initialize tier."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup tier."""
        await self.cleanup()
        return False
