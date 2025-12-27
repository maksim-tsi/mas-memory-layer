"""
Unit tests for metrics collection components.
"""
import pytest
import asyncio
from src.storage.metrics import MetricsCollector, OperationTimer, MetricsStorage, MetricsAggregator


@pytest.mark.asyncio
class TestMetricsStorage:
    """Test MetricsStorage class."""
    
    async def test_add_operation(self):
        """Test adding operations to storage."""
        storage = MetricsStorage(max_history=5)
        
        # Add operations
        await storage.add_operation('store', {'duration_ms': 10.5, 'success': True})
        await storage.add_operation('store', {'duration_ms': 15.2, 'success': True})
        await storage.add_operation('retrieve', {'duration_ms': 8.3, 'success': False})
        
        # Get all data
        data = await storage.get_all()
        
        assert 'operations' in data
        assert len(data['operations']['store']) == 2
        assert len(data['operations']['retrieve']) == 1
        assert data['operations']['store'][0]['duration_ms'] == 10.5
    
    async def test_increment_counter(self):
        """Test incrementing counters."""
        storage = MetricsStorage()
        
        # Increment counters
        await storage.increment_counter('test_counter', 5)
        await storage.increment_counter('test_counter', 3)
        await storage.increment_counter('other_counter', 1)
        
        # Get all data
        data = await storage.get_all()
        
        assert data['counters']['test_counter'] == 8
        assert data['counters']['other_counter'] == 1
    
    async def test_add_error(self):
        """Test adding errors."""
        storage = MetricsStorage()
        
        # Add errors
        await storage.add_error({'type': 'TestError', 'message': 'Test message'})
        await storage.add_error({'type': 'AnotherError', 'message': 'Another message'})
        
        # Get all data
        data = await storage.get_all()
        
        assert len(data['errors']) == 2
        assert data['errors'][0]['type'] == 'TestError'
        assert data['errors'][1]['type'] == 'AnotherError'
    
    async def test_history_limiting(self):
        """Test that history is limited."""
        storage = MetricsStorage(max_history=3)
        
        # Add more operations than limit
        for i in range(5):
            await storage.add_operation('test', {'duration_ms': i, 'success': True})
        
        # Get all data
        data = await storage.get_all()
        
        # Should only have last 3 operations
        assert len(data['operations']['test']) == 3
        assert data['operations']['test'][0]['duration_ms'] == 2  # Oldest kept
        assert data['operations']['test'][2]['duration_ms'] == 4  # Newest
    
    async def test_reset(self):
        """Test resetting storage."""
        storage = MetricsStorage()
        
        # Add some data
        await storage.add_operation('store', {'duration_ms': 10.5, 'success': True})
        await storage.increment_counter('test_counter', 5)
        await storage.add_error({'type': 'TestError', 'message': 'Test message'})
        
        # Reset
        await storage.reset()
        
        # Get all data
        data = await storage.get_all()
        
        assert len(data['operations']) == 0
        assert len(data['counters']) == 0
        assert len(data['errors']) == 0


class TestMetricsAggregator:
    """Test MetricsAggregator class."""
    
    def test_calculate_percentiles(self):
        """Test percentile calculations."""
        values = [1.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 100.0]
        percentiles = MetricsAggregator.calculate_percentiles(values, [50, 95, 99])
        
        assert 'p50' in percentiles
        assert 'p95' in percentiles
        assert 'p99' in percentiles
        assert percentiles['p50'] >= 15
        assert percentiles['p95'] >= 35
    
    def test_calculate_latency_stats(self):
        """Test latency statistics calculation."""
        durations = [1.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 100.0]
        stats = MetricsAggregator.calculate_latency_stats(durations, [50, 95, 99])
        
        assert 'min' in stats
        assert 'max' in stats
        assert 'avg' in stats
        assert 'p50' in stats
        assert 'p95' in stats
        assert 'p99' in stats
        assert stats['min'] == 1.0
        assert stats['max'] == 100.0
        assert stats['avg'] > 0
    
    def test_calculate_latency_stats_empty(self):
        """Test latency statistics with empty data."""
        stats = MetricsAggregator.calculate_latency_stats([])
        assert stats['min'] == 0.0
        assert stats['max'] == 0.0
        assert stats['avg'] == 0.0
    
    def test_calculate_rates_with_bytes(self):
        """Test rate calculations including bytes."""
        from datetime import datetime, timezone, timedelta
        
        now = datetime.now(timezone.utc)
        operations = [
            {
                'timestamp': (now - timedelta(seconds=30)).isoformat(),
                'metadata': {'bytes': 1000}
            },
            {
                'timestamp': (now - timedelta(seconds=20)).isoformat(),
                'metadata': {'bytes': 2000}
            },
            {
                'timestamp': (now - timedelta(seconds=10)).isoformat(),
                'metadata': {'bytes': 1500}
            }
        ]
        
        rates = MetricsAggregator.calculate_rates(operations, window_seconds=60)
        
        assert 'ops_per_sec' in rates
        assert 'bytes_per_sec' in rates
        assert rates['ops_per_sec'] > 0
        assert rates['bytes_per_sec'] > 0
        # 3 operations in 60 seconds = 0.05 ops/sec
        assert rates['ops_per_sec'] == 0.05
        # 4500 bytes in 60 seconds = 75 bytes/sec
        assert rates['bytes_per_sec'] == 75.0


@pytest.mark.asyncio
class TestMetricsCollector:
    """Test MetricsCollector class."""
    
    async def test_init_with_config(self):
        """Test initialization with configuration."""
        config = {
            'enabled': False,
            'max_history': 500,
            'track_errors': False,
            'percentiles': [50, 90, 99]
        }
        
        collector = MetricsCollector(config)
        
        assert collector.enabled == False
        assert collector.max_history == 500
        assert collector.track_errors == False
        assert collector.percentiles == [50, 90, 99]
    
    async def test_record_operation(self):
        """Test recording operations."""
        collector = MetricsCollector()
        
        # Record operations
        await collector.record_operation('store', 10.5, True)
        await collector.record_operation('store', 15.2, True)
        await collector.record_operation('store', 8.3, False)
        
        # Get metrics
        metrics = await collector.get_metrics()
        
        assert 'operations' in metrics
        assert 'store' in metrics['operations']
        store_stats = metrics['operations']['store']
        assert store_stats['total_count'] == 3
        assert store_stats['success_count'] == 2
        assert store_stats['error_count'] == 1
        assert store_stats['success_rate'] == 2/3
    
    async def test_record_error(self):
        """Test recording errors."""
        collector = MetricsCollector()
        
        # Record errors
        await collector.record_error('TestError', 'store', 'Test error message')
        await collector.record_error('AnotherError', 'retrieve', 'Another error message')
        
        # Get metrics
        metrics = await collector.get_metrics()
        
        assert 'errors' in metrics
        assert 'by_type' in metrics['errors']
        assert metrics['errors']['by_type']['TestError'] == 1
        assert metrics['errors']['by_type']['AnotherError'] == 1
    
    async def test_disabled_metrics(self):
        """Test that disabled metrics don't record data."""
        collector = MetricsCollector({'enabled': False})
        
        # Try to record data
        await collector.record_operation('store', 10.5, True)
        await collector.record_error('TestError', 'store', 'Test error message')
        
        # Get metrics
        metrics = await collector.get_metrics()
        
        assert metrics == {}
    
    async def test_export_metrics(self):
        """Test exporting metrics in different formats."""
        collector = MetricsCollector()
        
        # Record some data
        await collector.record_operation('store', 10.5, True)
        
        # Test different export formats
        dict_metrics = await collector.export_metrics('dict')
        json_metrics = await collector.export_metrics('json')
        prometheus_metrics = await collector.export_metrics('prometheus')
        csv_metrics = await collector.export_metrics('csv')
        markdown_metrics = await collector.export_metrics('markdown')
        
        assert isinstance(dict_metrics, dict)
        assert isinstance(json_metrics, str)
        assert isinstance(prometheus_metrics, str)
        assert isinstance(csv_metrics, str)
        assert isinstance(markdown_metrics, str)


@pytest.mark.asyncio
class TestOperationTimer:
    """Test OperationTimer context manager."""
    
    async def test_timer_success(self):
        """Test timer with successful operation."""
        collector = MetricsCollector()
        
        # Use timer
        async with OperationTimer(collector, 'test_op'):
            # Simulate work
            await asyncio.sleep(0.01)
        
        # Get metrics
        metrics = await collector.get_metrics()
        
        assert 'test_op' in metrics['operations']
        assert metrics['operations']['test_op']['total_count'] == 1
        assert metrics['operations']['test_op']['success_count'] == 1
    
    async def test_timer_error(self):
        """Test timer with error."""
        collector = MetricsCollector()
        
        # Use timer that raises exception
        try:
            async with OperationTimer(collector, 'test_op'):
                # Simulate work that raises exception
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected
        
        # Get metrics
        metrics = await collector.get_metrics()
        
        assert 'test_op' in metrics['operations']
        assert metrics['operations']['test_op']['total_count'] == 1
        assert metrics['operations']['test_op']['success_count'] == 0
        assert metrics['operations']['test_op']['error_count'] == 1
    
    async def test_concurrent_operations(self):
        """Test metrics collection under concurrent load."""
        collector = MetricsCollector()
        
        async def worker(worker_id: int):
            for i in range(100):
                async with OperationTimer(collector, f'op_{worker_id}'):
                    # Simulate some work
                    await asyncio.sleep(0.001)
        
        # Run 10 workers concurrently
        await asyncio.gather(*[worker(i) for i in range(10)])
        
        # Verify all operations recorded
        metrics = await collector.get_metrics()
        total_ops = sum(
            stats['total_count'] 
            for stats in metrics['operations'].values()
        )
        assert total_ops == 1000  # 10 workers * 100 ops each
