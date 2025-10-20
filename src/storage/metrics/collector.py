"""
Metrics collector for storage adapters.
"""
from typing import Dict, Any, List, Optional, Union
import time
import random
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
import asyncio
from .storage import MetricsStorage
from .aggregator import MetricsAggregator


class MetricsCollector:
    """
    Base metrics collector for storage adapters.
    
    Provides thread-safe metrics collection with configurable
    history limits and aggregation capabilities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize metrics collector.
        
        Args:
            config: Optional configuration
                - enabled: Enable/disable metrics (default: True)
                - max_history: Max operations to store (default: 1000)
                - track_errors: Track error details (default: True)
                - track_data_volume: Track bytes in/out (default: True)
                - percentiles: Latency percentiles (default: [50, 95, 99])
                - aggregation_window: Window for rate calculations in seconds (default: 60)
                - sampling_rate: Sample rate for operations (default: 1.0)
                - always_sample_errors: Always track errors (default: True)
        """
        config = config or {}
        self.enabled = config.get('enabled', True)
        self.max_history = config.get('max_history', 1000)
        self.track_errors = config.get('track_errors', True)
        self.track_data_volume = config.get('track_data_volume', True)
        self.percentiles = config.get('percentiles', [50, 95, 99])
        self.aggregation_window = config.get('aggregation_window', 60)
        self.sampling_rate = config.get('sampling_rate', 1.0)
        self.always_sample_errors = config.get('always_sample_errors', True)
        
        # Internal storage
        self._storage = MetricsStorage(max_history=self.max_history)
        self._lock = asyncio.Lock()
        self._start_time = time.time()
    
    async def record_operation(
        self,
        operation: str,
        duration_ms: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record an operation with duration and outcome."""
        if not self.enabled:
            return
        
        # Apply sampling
        import random
        if random.random() > self.sampling_rate and not (not success and self.always_sample_errors):
            return
        
        async with self._lock:
            await self._storage.add_operation(operation, {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'duration_ms': duration_ms,
                'success': success,
                'metadata': metadata or {}
            })
            
            # Update counters
            await self._storage.increment_counter(f'operations_total_{operation}')
            if success:
                await self._storage.increment_counter(f'operations_success_{operation}')
            else:
                await self._storage.increment_counter(f'operations_error_{operation}')
    
    async def record_error(
        self,
        error_type: str,
        operation: str,
        details: str
    ) -> None:
        """Record an error event."""
        if not self.enabled or not self.track_errors:
            return
        
        async with self._lock:
            await self._storage.add_error({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'type': error_type,
                'operation': operation,
                'message': details
            })
            
            # Update error counter
            await self._storage.increment_counter(f'errors_total_{error_type}')
    
    async def record_connection_event(
        self,
        event: str,
        duration_ms: Optional[float] = None
    ) -> None:
        """Record connection lifecycle event."""
        if not self.enabled:
            return
        
        async with self._lock:
            await self._storage.add_operation('connection', {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'duration_ms': duration_ms,
                'success': True,
                'metadata': {'event': event}
            })
            
            # Update connection counters
            await self._storage.increment_counter(f'connection_{event}')
    
    async def record_data_volume(
        self,
        operation: str,
        bytes_count: int
    ) -> None:
        """Record data volume for an operation."""
        if not self.enabled or not self.track_data_volume:
            return
        
        async with self._lock:
            await self._storage.increment_counter(f'data_volume_{operation}', bytes_count)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get all collected metrics with aggregations.
        
        Returns:
            Dictionary containing:
            - uptime_seconds: Time since collector started
            - timestamp: ISO timestamp
            - operations: Per-operation statistics
            - connection: Connection metrics
            - errors: Error statistics
        """
        if not self.enabled:
            return {}
        
        async with self._lock:
            all_data = await self._storage.get_all()
            
            # Calculate aggregations
            operations_stats = {}
            for operation, records in all_data.get('operations', {}).items():
                if records:
                    durations = [r['duration_ms'] for r in records]
                    success_count = sum(1 for r in records if r['success'])
                    total_count = len(records)
                    
                    operations_stats[operation] = {
                        'total_count': total_count,
                        'success_count': success_count,
                        'error_count': total_count - success_count,
                        'success_rate': success_count / total_count if total_count > 0 else 0,
                        'latency_ms': MetricsAggregator.calculate_latency_stats(
                            durations, self.percentiles
                        )
                    }
                    
                    # Calculate throughput
                    if durations:
                        time_window = self.aggregation_window
                        recent_records = [
                            r for r in records 
                            if datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')) 
                            > datetime.now(timezone.utc) - timedelta(seconds=time_window)
                        ]
                        ops_per_sec = len(recent_records) / time_window if time_window > 0 else 0
                        
                        operations_stats[operation]['throughput'] = {
                            'ops_per_sec': round(ops_per_sec, 2)
                        }
            
            # Calculate data volume stats
            data_volume_stats = {}
            for key, value in all_data.get('counters', {}).items():
                if key.startswith('data_volume_'):
                    operation = key[len('data_volume_'):]
                    data_volume_stats[operation] = value
            
            if data_volume_stats:
                operations_stats['data_volume'] = data_volume_stats
            
            # Connection stats
            connection_stats = {}
            for key, value in all_data.get('counters', {}).items():
                if key.startswith('connection_'):
                    event = key[len('connection_'):]
                    connection_stats[event] = value
            
            # Error stats
            error_stats = {}
            for key, value in all_data.get('counters', {}).items():
                if key.startswith('errors_total_'):
                    error_type = key[len('errors_total_'):]
                    error_stats[error_type] = value
            
            recent_errors = list(all_data.get('errors', []))
            
            return {
                'uptime_seconds': round(time.time() - self._start_time, 2),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'operations': operations_stats,
                'connection': connection_stats,
                'errors': {
                    'by_type': error_stats,
                    'recent_errors': recent_errors[-10:] if recent_errors else []  # Last 10 errors
                }
            }
    
    async def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        if not self.enabled:
            return
        
        async with self._lock:
            await self._storage.reset()
            self._start_time = time.time()
    
    async def export_metrics(self, format: str = 'dict') -> Union[Dict, str]:
        """
        Export metrics in specified format.
        
        Args:
            format: 'dict', 'json', 'prometheus', 'csv', 'markdown'
            
        Returns:
            Metrics in requested format
        """
        from .exporters import export_metrics
        metrics = await self.get_metrics()
        return export_metrics(metrics, format)


