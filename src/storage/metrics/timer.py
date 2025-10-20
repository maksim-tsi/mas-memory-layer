"""
Context manager to time and automatically record operations.
"""
import time
from typing import Dict, Any, Optional
from .collector import MetricsCollector


class OperationTimer:
    """
    Context manager to time and automatically record operations.
    
    Usage:
        async with OperationTimer(metrics, 'store', metadata={'has_id': True}):
            # ... perform operation ...
            pass
    """
    
    def __init__(
        self,
        collector: MetricsCollector,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.collector = collector
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time: Optional[float] = None
        self.success = True
    
    async def __aenter__(self):
        self.start_time = time.perf_counter()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not self.collector.enabled:
            return False
        
        if self.start_time is None:
            return False
            
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        success = (exc_type is None)
        
        await self.collector.record_operation(
            self.operation,
            duration_ms,
            success,
            self.metadata
        )
        
        if not success and self.collector.track_errors:
            await self.collector.record_error(
                type(exc_val).__name__,
                self.operation,
                str(exc_val)
            )
        
        return False  # Don't suppress exceptions