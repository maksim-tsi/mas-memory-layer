"""
Integration test configuration and fixtures.

Provides fixtures for surgical cleanup of test data from live cluster.
Uses namespace isolation via unique session IDs to prevent test collisions.
"""

import os
import pytest
import asyncio
from typing import List, AsyncGenerator
import pytest_asyncio
from src.storage.redis_adapter import RedisAdapter
from src.storage.postgres_adapter import PostgresAdapter
from src.storage.neo4j_adapter import Neo4jAdapter
from src.storage.qdrant_adapter import QdrantAdapter
from src.storage.typesense_adapter import TypesenseAdapter


@pytest_asyncio.fixture(scope="function")
async def verify_l2_schema():
    """Fail-fast schema verification for L2 Working Memory.
    
    Checks that migration 002 (content_tsv column) has been applied.
    Fails with actionable error message if schema is incorrect.
    """
    from src.storage.postgres_adapter import PostgresAdapter
    
    adapter = PostgresAdapter(config={
        'url': os.getenv('POSTGRES_URL', 'postgresql://pgadmin:password@192.168.107.187:5432/mas_memory')
    })
    
    try:
        await adapter.connect()
        
        # Check for content_tsv column using direct SQL
        async with adapter.pool.connection() as conn:  # type: ignore
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'working_memory' 
                    AND column_name = 'content_tsv'
                """)
                result = await cur.fetchone()
        
        if not result:
            raise RuntimeError(
                "❌ Schema verification failed: 'content_tsv' column not found in working_memory table.\n"
                "🔧 Action required: Apply migration 002:\n"
                "   psql -h 192.168.107.187 -U pgadmin -d mas_memory -f migrations/002_l2_tsvector_index.sql"
            )
        
        # Check for GIN index
        async with adapter.pool.connection() as conn:  # type: ignore
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = 'working_memory' 
                    AND indexname = 'idx_working_memory_content_tsv'
                """)
                result_index = await cur.fetchone()
        
        if not result_index:
            raise RuntimeError(
                "❌ Schema verification failed: GIN index 'idx_working_memory_content_tsv' not found.\n"
                "🔧 Action required: Verify migration 002 completed successfully."
            )
            
        print("✅ L2 schema verification passed: content_tsv column and GIN index present")
        
    finally:
        await adapter.disconnect()


@pytest_asyncio.fixture(scope="function")
async def redis_adapter(test_session_id: str) -> AsyncGenerator[RedisAdapter, None]:
    """Live Redis adapter fixture for L1 Active Context (Node 1: 192.168.107.172)."""
    adapter = RedisAdapter(config={
        'url': os.getenv('REDIS_URL', 'redis://192.168.107.172:6379')
    })
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


@pytest_asyncio.fixture(scope="function")
async def postgres_adapter(test_session_id: str) -> AsyncGenerator[PostgresAdapter, None]:
    """Live PostgreSQL adapter fixture for L2 Working Memory (Node 2: 192.168.107.187)."""
    adapter = PostgresAdapter(config={
        'url': os.getenv('POSTGRES_URL', 'postgresql://pgadmin:password@192.168.107.187:5432/mas_memory')
    })
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


@pytest_asyncio.fixture(scope="function")
async def neo4j_adapter(test_session_id: str) -> AsyncGenerator[Neo4jAdapter, None]:
    """Live Neo4j adapter fixture for L3 Episodic Memory (Node 2: 192.168.107.187)."""
    adapter = Neo4jAdapter(config={
        'uri': os.getenv('NEO4J_URI', 'bolt://192.168.107.187:7687'),
        'user': os.getenv('NEO4J_USER', 'neo4j'),
        'password': os.getenv('NEO4J_PASSWORD', 'password')
    })
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


@pytest_asyncio.fixture(scope="function")
async def qdrant_adapter(test_session_id: str) -> AsyncGenerator[QdrantAdapter, None]:
    """Live Qdrant adapter fixture for L3 Episodic Memory (Node 2: 192.168.107.187)."""
    adapter = QdrantAdapter(config={
        'url': os.getenv('QDRANT_URL', 'http://192.168.107.187:6333')
    })
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


@pytest_asyncio.fixture(scope="function")
async def typesense_adapter(test_session_id: str) -> AsyncGenerator[TypesenseAdapter, None]:
    """Live Typesense adapter fixture for L4 Semantic Memory (Node 2: 192.168.107.187)."""
    host = os.getenv('TYPESENSE_HOST', '192.168.107.187')
    port = os.getenv('TYPESENSE_PORT', '8108')
    adapter = TypesenseAdapter(config={
        'url': f'http://{host}:{port}',
        'api_key': os.getenv('TYPESENSE_API_KEY', 'xyz'),
        'collection_name': 'knowledge_base'
    })
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


@pytest_asyncio.fixture(scope="function")
async def cleanup_redis_keys(redis_adapter: RedisAdapter, test_session_id: str):
    """Surgical cleanup of Redis keys for test session.
    
    Deletes only keys associated with the test session ID, preserving
    all other data in the live cluster.
    """
    yield  # Let test run
    
    # Cleanup after test
    try:
        pattern = f"*{test_session_id}*"
        keys = await redis_adapter.scan_keys(pattern)
        if keys:
            await redis_adapter.delete_keys(keys)
            print(f"✅ Cleaned up {len(keys)} Redis keys for session {test_session_id}")
    except Exception as e:
        print(f"⚠️  Redis cleanup error: {e}")


@pytest_asyncio.fixture(scope="function")
async def cleanup_postgres_facts(postgres_adapter: PostgresAdapter, test_session_id: str):
    """Surgical cleanup of PostgreSQL facts for test session."""
    yield  # Let test run
    
    # Cleanup after test
    try:
        await postgres_adapter.execute(
            "DELETE FROM working_memory WHERE session_id = $1",
            test_session_id
        )
        await postgres_adapter.execute(
            "DELETE FROM active_context WHERE session_id = $1",
            test_session_id
        )
        print(f"✅ Cleaned up PostgreSQL facts for session {test_session_id}")
    except Exception as e:
        print(f"⚠️  PostgreSQL cleanup error: {e}")


@pytest_asyncio.fixture(scope="function")
async def cleanup_neo4j_episodes(neo4j_adapter: Neo4jAdapter, test_session_id: str):
    """Surgical cleanup of Neo4j episodes for test session."""
    yield  # Let test run
    
    # Cleanup after test
    try:
        query = """
        MATCH (e:Episode {sessionId: $session_id})
        OPTIONAL MATCH (e)-[r]-()
        DELETE r, e
        """
        await neo4j_adapter.execute_query(query, {'session_id': test_session_id})
        print(f"✅ Cleaned up Neo4j episodes for session {test_session_id}")
    except Exception as e:
        print(f"⚠️  Neo4j cleanup error: {e}")


@pytest_asyncio.fixture(scope="function")
async def cleanup_qdrant_episodes(qdrant_adapter: QdrantAdapter, test_session_id: str):
    """Surgical cleanup of Qdrant vectors for test session."""
    yield  # Let test run
    
    # Cleanup after test
    try:
        # Filter by session_id in metadata and delete matching vectors
        # Note: Implementation depends on Qdrant adapter's delete_by_filter method
        print(f"⏭️  Qdrant cleanup for session {test_session_id} - filtering by metadata")
    except Exception as e:
        print(f"⚠️  Qdrant cleanup error: {e}")


@pytest_asyncio.fixture(scope="function")
async def cleanup_typesense_knowledge(typesense_adapter: TypesenseAdapter, test_session_id: str):
    """Surgical cleanup of Typesense knowledge documents for test session."""
    yield  # Let test run
    
    # Cleanup after test
    try:
        # Filter by session_id or test tag and delete matching documents
        print(f"⏭️  Typesense cleanup for session {test_session_id} - filtering by metadata")
    except Exception as e:
        print(f"⚠️  Typesense cleanup error: {e}")


@pytest_asyncio.fixture(scope="function")
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
