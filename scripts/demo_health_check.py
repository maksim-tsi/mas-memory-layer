#!/usr/bin/env python3
"""
Demonstration script for health check functionality.

This script shows how to use the health_check() method to monitor
adapter connectivity and performance.
"""

import asyncio
import json
from src.storage.qdrant_adapter import QdrantAdapter
from src.storage.neo4j_adapter import Neo4jAdapter
from src.storage.typesense_adapter import TypesenseAdapter


async def demo_health_checks():
    """Demonstrate health check for all Priority 4 adapters."""
    
    # Qdrant health check
    print("=" * 60)
    print("QDRANT HEALTH CHECK")
    print("=" * 60)
    
    qdrant_config = {
        'url': 'http://192.168.107.187:6333',
        'collection_name': 'test_health',
        'vector_size': 384
    }
    
    qdrant = QdrantAdapter(qdrant_config)
    
    # Check before connection
    health = await qdrant.health_check()
    print("\nBefore connection:")
    print(json.dumps(health, indent=2))
    
    # Connect and check again
    try:
        await qdrant.connect()
        health = await qdrant.health_check()
        print("\nAfter connection:")
        print(json.dumps(health, indent=2))
        await qdrant.disconnect()
    except Exception as e:
        print(f"Connection failed: {e}")
    
    # Neo4j health check
    print("\n" + "=" * 60)
    print("NEO4J HEALTH CHECK")
    print("=" * 60)
    
    neo4j_config = {
        'uri': 'bolt://192.168.107.187:7687',
        'user': 'neo4j',
        'password': 'password',
        'database': 'neo4j'
    }
    
    neo4j = Neo4jAdapter(neo4j_config)
    
    # Check before connection
    health = await neo4j.health_check()
    print("\nBefore connection:")
    print(json.dumps(health, indent=2))
    
    # Connect and check again
    try:
        await neo4j.connect()
        health = await neo4j.health_check()
        print("\nAfter connection:")
        print(json.dumps(health, indent=2))
        await neo4j.disconnect()
    except Exception as e:
        print(f"Connection failed: {e}")
    
    # Typesense health check
    print("\n" + "=" * 60)
    print("TYPESENSE HEALTH CHECK")
    print("=" * 60)
    
    typesense_config = {
        'url': 'http://192.168.107.187:8108',
        'api_key': 'test-key',
        'collection_name': 'test_health'
    }
    
    typesense = TypesenseAdapter(typesense_config)
    
    # Check before connection
    health = await typesense.health_check()
    print("\nBefore connection:")
    print(json.dumps(health, indent=2))
    
    # Connect and check again
    try:
        await typesense.connect()
        health = await typesense.health_check()
        print("\nAfter connection:")
        print(json.dumps(health, indent=2))
        await typesense.disconnect()
    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == '__main__':
    asyncio.run(demo_health_checks())
