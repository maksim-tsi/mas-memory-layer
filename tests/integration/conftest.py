"""
Integration test configuration and fixtures.

Provides fixtures for surgical cleanup of test data from live cluster.
Uses namespace isolation via unique session IDs to prevent test collisions.
"""

import pytest
import asyncio
from typing import List


@pytest.fixture
async def cleanup_redis_keys(test_session_id: str):
    """Surgical cleanup of Redis keys for test session.
    
    Deletes only keys associated with the test session ID, preserving
    all other data in the live cluster.
    """
    from src.storage.redis_adapter import RedisAdapter
    
    adapter = RedisAdapter()
    await adapter.connect()
    
    # Pattern for all test keys
    pattern = f"*{test_session_id}*"
    
    yield  # Let test run
    
    # Cleanup after test
    try:
        keys = await adapter.scan_keys(pattern)
        if keys:
            await adapter.delete_keys(keys)
            print(f"Cleaned up {len(keys)} Redis keys for session {test_session_id}")
    finally:
        await adapter.disconnect()


@pytest.fixture
async def cleanup_postgres_facts(test_session_id: str):
    """Surgical cleanup of PostgreSQL facts for test session."""
    from src.storage.postgres_adapter import PostgresAdapter
    
    adapter = PostgresAdapter()
    await adapter.connect()
    
    yield  # Let test run
    
    # Cleanup after test
    try:
        await adapter.execute(
            "DELETE FROM working_memory WHERE session_id = $1",
            test_session_id
        )
        await adapter.execute(
            "DELETE FROM active_context WHERE session_id = $1",
            test_session_id
        )
        print(f"Cleaned up PostgreSQL facts for session {test_session_id}")
    finally:
        await adapter.disconnect()


@pytest.fixture
async def cleanup_neo4j_episodes(test_session_id: str):
    """Surgical cleanup of Neo4j episodes for test session."""
    from src.storage.neo4j_adapter import Neo4jAdapter
    
    adapter = Neo4jAdapter()
    await adapter.connect()
    
    yield  # Let test run
    
    # Cleanup after test
    try:
        query = """
        MATCH (e:Episode {sessionId: $session_id})
        OPTIONAL MATCH (e)-[r]-()
        DELETE r, e
        """
        await adapter.execute_query(query, {'session_id': test_session_id})
        print(f"Cleaned up Neo4j episodes for session {test_session_id}")
    finally:
        await adapter.close()


@pytest.fixture
async def cleanup_qdrant_episodes(test_session_id: str):
    """Surgical cleanup of Qdrant vectors for test session."""
    from src.storage.qdrant_adapter import QdrantAdapter
    
    adapter = QdrantAdapter()
    # Note: Qdrant adapter may not have async cleanup implemented yet
    # This is a placeholder for future implementation
    
    yield  # Let test run
    
    # Cleanup after test
    try:
        # Filter by session_id in metadata and delete matching vectors
        # await adapter.delete_by_filter(
        #     collection_name="episodes",
        #     filter={"session_id": test_session_id}
        # )
        print(f"Qdrant cleanup for session {test_session_id} - not yet implemented")
    except Exception as e:
        print(f"Qdrant cleanup error: {e}")


@pytest.fixture
async def cleanup_typesense_knowledge(test_session_id: str):
    """Surgical cleanup of Typesense knowledge documents for test session."""
    from src.storage.typesense_adapter import TypesenseAdapter
    
    adapter = TypesenseAdapter()
    
    yield  # Let test run
    
    # Cleanup after test
    try:
        # Filter by session_id or test tag and delete matching documents
        # await adapter.delete_by_filter(
        #     collection_name="knowledge_base",
        #     filter={"session_id": test_session_id}
        # )
        print(f"Typesense cleanup for session {test_session_id} - not yet implemented")
    except Exception as e:
        print(f"Typesense cleanup error: {e}")


@pytest.fixture
async def full_cleanup(
    cleanup_redis_keys,
    cleanup_postgres_facts,
    cleanup_neo4j_episodes,
    cleanup_qdrant_episodes,
    cleanup_typesense_knowledge
):
    """Combined cleanup fixture for full lifecycle tests.
    
    Uses all storage adapter cleanup fixtures to ensure complete
    removal of test data from live cluster.
    """
    yield  # All cleanup happens via individual fixtures
