"""
Demo script showing metrics collection for storage adapters.
"""
import asyncio
import json
from src.storage.redis_adapter import RedisAdapter


async def demo_metrics():
    """Demonstrate metrics collection."""
    # Configure adapter with metrics enabled
    config = {
        'url': 'redis://localhost:6379/0',
        'window_size': 5,
        'metrics': {
            'enabled': True,
            'max_history': 100,
            'track_errors': True
        }
    }
    
    adapter = RedisAdapter(config)
    
    try:
        # Connect to Redis
        await adapter.connect()
        print("✓ Connected to Redis")
        
        # Store some data
        for i in range(3):
            await adapter.store({
                'session_id': 'demo-session',
                'turn_id': i,
                'content': f'Demo message {i}',
                'metadata': {'demo': True}
            })
            print(f"✓ Stored message {i}")
        
        # Retrieve data
        data = await adapter.retrieve('session:demo-session:turns:1')
        if data:
            print(f"✓ Retrieved: {data['content']}")
        
        # Search data
        results = await adapter.search({
            'session_id': 'demo-session',
            'limit': 2
        })
        print(f"✓ Found {len(results)} results")
        
        # Get metrics
        metrics = await adapter.get_metrics()
        print("\n=== Metrics Summary ===")
        print(f"Uptime: {metrics.get('uptime_seconds', 0)} seconds")
        print(f"Operations recorded: {len(metrics.get('operations', {}))}")
        
        # Export metrics in different formats
        print("\n=== JSON Export ===")
        json_export = await adapter.export_metrics('json')
        print(json_export[:200] + "..." if len(json_export) > 200 else json_export)
        
        print("\n=== Markdown Export ===")
        md_export = await adapter.export_metrics('markdown')
        print(md_export[:200] + "..." if len(md_export) > 200 else md_export)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        await adapter.disconnect()
        print("✓ Disconnected")


if __name__ == "__main__":
    asyncio.run(demo_metrics())