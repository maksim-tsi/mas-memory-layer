# Metrics Collection & Observability

This document explains how to use the metrics collection functionality in the storage adapters.

## Overview

The metrics collection system provides observability into the performance and behavior of storage adapters. It collects data on:

- Operation counts and success rates
- Latency statistics (min, max, avg, percentiles)
- Error tracking
- Data volume metrics
- Connection lifecycle events

## Enabling Metrics

Metrics are enabled by default but can be configured through the adapter configuration:

```python
config = {
    'url': 'redis://localhost:6379/0',
    # ... other config options ...
    'metrics': {
        'enabled': True,                    # Enable/disable metrics (default: True)
        'max_history': 1000,                # Max operations to store (default: 1000)
        'track_errors': True,               # Track error details (default: True)
        'track_data_volume': True,          # Track bytes in/out (default: True)
        'percentiles': [50, 95, 99],        # Latency percentiles (default: [50, 95, 99])
        'aggregation_window': 60,           # Rate calculation window in seconds (default: 60)
        'sampling_rate': 1.0,               # Sample rate for operations (default: 1.0)
        'always_sample_errors': True        # Always track errors (default: True)
    }
}

adapter = RedisAdapter(config)
```

## Collecting Metrics

Metrics are automatically collected for all operations when metrics are enabled. The system tracks:

- `store` operations
- `retrieve` operations
- `search` operations
- `delete` operations
- `connect`/`disconnect` events

## Retrieving Metrics

### Get Metrics as Dictionary

```python
metrics = await adapter.get_metrics()
print(f"Uptime: {metrics['uptime_seconds']} seconds")
print(f"Store operations: {metrics['operations']['store']['total_count']}")
```

### Export Metrics in Different Formats

```python
# JSON format
json_metrics = await adapter.export_metrics('json')

# Prometheus format
prometheus_metrics = await adapter.export_metrics('prometheus')

# CSV format
csv_metrics = await adapter.export_metrics('csv')

# Markdown format
markdown_metrics = await adapter.export_metrics('markdown')
```

## Metrics Structure

The metrics dictionary has the following structure:

```python
{
    'adapter_type': 'redis',
    'uptime_seconds': 3600,
    'timestamp': '2025-10-21T12:00:00Z',
    'operations': {
        'store': {
            'total_count': 1500,
            'success_count': 1498,
            'error_count': 2,
            'success_rate': 0.9987,
            'latency_ms': {
                'min': 2.3,
                'max': 145.2,
                'avg': 12.5,
                'p50': 10.2,
                'p95': 35.8,
                'p99': 89.1
            },
            'throughput': {
                'ops_per_sec': 25.0
            }
        },
        # ... other operations
    },
    'connection': {
        'connect_count': 5,
        'disconnect_count': 4
    },
    'errors': {
        'by_type': {
            'StorageConnectionError': 1,
            'StorageQueryError': 1
        },
        'recent_errors': [
            {
                'timestamp': '2025-10-21T11:45:00Z',
                'type': 'StorageQueryError',
                'operation': 'search',
                'message': 'Invalid query syntax'
            }
        ]
    }
}
```

## Performance Considerations

The metrics collection system is designed to have minimal performance impact:

- **Lazy Aggregation**: Calculations are only performed when metrics are requested
- **Circular Buffers**: History is automatically limited to prevent memory growth
- **Sampling**: High-throughput applications can sample operations (e.g., 10% sampling)
- **Async Recording**: Metrics recording doesn't block operations

To reduce overhead in high-throughput scenarios:

```python
config = {
    'metrics': {
        'sampling_rate': 0.1,  # Only track 10% of operations
        'max_history': 100     # Limit history size
    }
}
```

## Resetting Metrics

To reset all collected metrics:

```python
await adapter.reset_metrics()
```

## Example Usage

See `examples/metrics_demo.py` for a complete example of using metrics with the Redis adapter.