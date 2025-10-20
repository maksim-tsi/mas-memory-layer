"""
Storage layer for multi-layered memory system.

This package provides abstract interfaces and concrete implementations
for all backend storage services (PostgreSQL, Redis, Qdrant, Neo4j, Typesense).
"""

__version__ = "0.1.0"

# Base interface will be imported here after Priority 1
# from .base import StorageAdapter

# Concrete adapters will be imported after their implementation
# from .postgres_adapter import PostgresAdapter
# from .redis_adapter import RedisAdapter
# from .qdrant_adapter import QdrantAdapter
# from .neo4j_adapter import Neo4jAdapter
# from .typesense_adapter import TypesenseAdapter

__all__ = [
    # "StorageAdapter",
    # "PostgresAdapter",
    # "RedisAdapter",
    # "QdrantAdapter",
    # "Neo4jAdapter",
    # "TypesenseAdapter",
]