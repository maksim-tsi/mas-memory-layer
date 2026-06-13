"""
Storage layer for multi-layered memory system.

This package provides abstract interfaces and concrete implementations
for all backend storage services (PostgreSQL, Redis, Qdrant, Neo4j, Typesense).
"""

__version__ = "0.1.0"

# Base interface
from .base import (
    StorageAdapter,
    StorageConnectionError,
    StorageDataError,
    StorageError,
    StorageNotFoundError,
    StorageQueryError,
    StorageTimeoutError,
    validate_field_types,
    validate_required_fields,
)

# Metrics components
from .metrics import (
    MetricsAggregator,
    MetricsCollector,
    MetricsStorage,
    OperationTimer,
    export_metrics,
)
from .neo4j_adapter import Neo4jAdapter

# Concrete adapters
from .postgres_adapter import PostgresAdapter
from .qdrant_adapter import QdrantAdapter

# Future adapters will be imported after their implementation
from .redis_adapter import RedisAdapter
from .typesense_adapter import TypesenseAdapter

__all__ = [
    "MetricsAggregator",
    "MetricsCollector",
    "MetricsStorage",
    "Neo4jAdapter",
    "OperationTimer",
    "PostgresAdapter",
    "QdrantAdapter",
    "RedisAdapter",
    "StorageAdapter",
    "StorageConnectionError",
    "StorageDataError",
    "StorageError",
    "StorageNotFoundError",
    "StorageQueryError",
    "StorageTimeoutError",
    "TypesenseAdapter",
    "export_metrics",
    "validate_field_types",
    "validate_required_fields",
]
