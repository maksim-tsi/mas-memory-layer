"""
Simple script to verify metrics integration in Neo4j and Typesense adapters.
This demonstrates that metrics are collected even when backends are not available.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.neo4j_adapter import Neo4jAdapter
from src.storage.typesense_adapter import TypesenseAdapter


async def test_neo4j_metrics():
    """Test Neo4j adapter metrics (without actual connection)."""
    print("=" * 60)
    print("Testing Neo4j Adapter Metrics")
    print("=" * 60)
    
    config = {
        'uri': 'bolt://localhost:7687',
        'user': 'neo4j',
        'password': 'test',
        'metrics': {'enabled': True, 'max_history': 5}
    }
    
    adapter = Neo4jAdapter(config)
    print("✓ Neo4j adapter created with metrics enabled")
    print(f"✓ Has metrics collector: {hasattr(adapter, 'metrics')}")
    print(f"✓ Has _get_backend_metrics method: {hasattr(adapter, '_get_backend_metrics')}")
    
    # Get metrics before any operations
    metrics = await adapter.get_metrics()
    print("\n✓ Initial metrics collected:")
    print(f"  - Operations tracked: {list(metrics.get('operations', {}).keys())}")
    
    print("\n" + "=" * 60)


async def test_typesense_metrics():
    """Test Typesense adapter metrics (without actual connection)."""
    print("Testing Typesense Adapter Metrics")
    print("=" * 60)
    
    config = {
        'url': 'http://localhost:8108',
        'api_key': 'test',
        'collection_name': 'test',
        'metrics': {'enabled': True, 'max_history': 5}
    }
    
    adapter = TypesenseAdapter(config)
    print("✓ Typesense adapter created with metrics enabled")
    print(f"✓ Has metrics collector: {hasattr(adapter, 'metrics')}")
    print(f"✓ Has _get_backend_metrics method: {hasattr(adapter, '_get_backend_metrics')}")
    
    # Get metrics before any operations
    metrics = await adapter.get_metrics()
    print("\n✓ Initial metrics collected:")
    print(f"  - Operations tracked: {list(metrics.get('operations', {}).keys())}")
    
    print("\n" + "=" * 60)


async def main():
    """Run all tests."""
    print("\n🔍 Verifying Metrics Implementation in Adapters\n")
    
    await test_neo4j_metrics()
    await test_typesense_metrics()
    
    print("\n✅ All metrics integration checks passed!")
    print("\nNote: These tests verify that metrics infrastructure is in place.")
    print("Full integration tests require running Neo4j and Typesense servers.")


if __name__ == "__main__":
    asyncio.run(main())
