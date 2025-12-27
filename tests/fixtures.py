"""
Shared test fixtures for storage adapter tests.

Provides common fixtures, test data generators, and utilities
used across all storage adapter test suites.
"""
import pytest
import uuid
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock

# ============================================================================
# Sample Test Data
# ============================================================================

@pytest.fixture
def sample_session_id():
    """Generate consistent test session ID."""
    return f"test-session-{uuid.uuid4()}"


@pytest.fixture
def sample_turn_data():
    """Generate sample conversation turn data."""
    return {
        "turn_id": 1,
        "content": "Hello, how are you?",
        "metadata": {
            "role": "user",
            "tokens": 5,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }


@pytest.fixture
def sample_working_memory_data():
    """Generate sample working memory fact."""
    return {
        "fact_type": "preference",
        "content": "User prefers dark mode",
        "confidence": 0.95,
        "source_turn_ids": [1, 3]
    }


@pytest.fixture
def sample_vector_embedding():
    """Generate sample 384-dimensional embedding vector."""
    return [random.random() for _ in range(384)]


@pytest.fixture
def sample_vector_data(sample_vector_embedding):
    """Generate complete vector storage data."""
    return {
        "id": str(uuid.uuid4()),
        "vector": sample_vector_embedding,
        "content": "User discussed preference for dark mode in UI settings",
        "session_id": f"test-session-{uuid.uuid4()}",
        "metadata": {
            "fact_type": "preference",
            "confidence": 0.95
        }
    }


@pytest.fixture
def sample_graph_entity():
    """Generate sample Neo4j entity data."""
    return {
        "type": "entity",
        "label": "Person",
        "properties": {
            "name": "Alice",
            "age": 30,
            "session_id": f"test-session-{uuid.uuid4()}"
        }
    }


@pytest.fixture
def sample_graph_relationship():
    """Generate sample Neo4j relationship data."""
    return {
        "type": "relationship",
        "from": "entity-1-uuid",
        "to": "entity-2-uuid",
        "relationship": "KNOWS",
        "properties": {
            "since": "2023-01-01",
            "session_id": f"test-session-{uuid.uuid4()}"
        }
    }


@pytest.fixture
def sample_search_document():
    """Generate sample Typesense document."""
    return {
        "id": str(uuid.uuid4()),
        "content": "This is a test document for full-text search",
        "title": "Test Document",
        "session_id": f"test-session-{uuid.uuid4()}",
        "timestamp": int(datetime.now(timezone.utc).timestamp())
    }


# ============================================================================
# Test Data Generators
# ============================================================================

def generate_random_text(min_words: int = 5, max_words: int = 20) -> str:
    """Generate random text with specified word count."""
    num_words = random.randint(min_words, max_words)
    words = []
    for _ in range(num_words):
        word_len = random.randint(3, 12)
        words.append(''.join(random.choices(string.ascii_lowercase, k=word_len)))
    return ' '.join(words)


def generate_conversation_turns(session_id: str, count: int = 10) -> List[Dict[str, Any]]:
    """Generate multiple conversation turns for testing."""
    turns = []
    for i in range(count):
        turns.append({
            "session_id": session_id,
            "turn_id": i,
            "content": generate_random_text(10, 50),
            "role": "user" if i % 2 == 0 else "assistant",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    return turns


def generate_vector_batch(count: int = 10) -> List[Dict[str, Any]]:
    """Generate batch of vectors for testing."""
    vectors = []
    for _ in range(count):
        vectors.append({
            "id": str(uuid.uuid4()),
            "vector": [random.random() for _ in range(384)],
            "content": generate_random_text(20, 100),
            "session_id": f"test-session-{uuid.uuid4()}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    return vectors


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_postgres_pool():
    """Mock PostgreSQL connection pool."""
    pool = AsyncMock()
    connection = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = connection
    pool.acquire.return_value.__aexit__.return_value = None
    return pool


@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    client = AsyncMock()
    client.ping.return_value = True
    client.keys.return_value = []
    client.get.return_value = None
    client.set.return_value = True
    client.delete.return_value = 1
    client.zadd.return_value = 1
    client.zrange.return_value = []
    return client


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client."""
    
    client = AsyncMock()
    client.get_collections.return_value.collections = []
    client.upsert.return_value = None
    client.retrieve.return_value = []
    client.search.return_value = []
    client.delete.return_value = None
    return client


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver."""
    driver = Mock()
    session = AsyncMock()
    driver.session.return_value.__aenter__.return_value = session
    driver.session.return_value.__aexit__.return_value = None
    session.run.return_value = AsyncMock()
    return driver


@pytest.fixture
def mock_typesense_client():
    """Mock Typesense HTTP client."""
    client = AsyncMock()
    response = AsyncMock()
    response.status_code = 200
    response.json.return_value = {"id": "test-id"}
    client.get.return_value = response
    client.post.return_value = response
    client.delete.return_value = response
    return client


# ============================================================================
# Cleanup Utilities
# ============================================================================

@pytest.fixture
def cleanup_postgres_session():
    """Cleanup PostgreSQL test data after test."""
    session_ids = []
    
    def register_session(session_id: str):
        session_ids.append(session_id)
    
    yield register_session
    
    # Cleanup logic would go here
    # Note: Actual cleanup requires adapter access


@pytest.fixture
def cleanup_redis_session():
    """Cleanup Redis test data after test."""
    session_ids = []
    
    def register_session(session_id: str):
        session_ids.append(session_id)
    
    yield register_session
    
    # Cleanup logic would go here


# ============================================================================
# TTL and Time-Related Fixtures
# ============================================================================

@pytest.fixture
def future_timestamp():
    """Generate timestamp 1 hour in the future."""
    return datetime.now(timezone.utc) + timedelta(hours=1)


@pytest.fixture
def past_timestamp():
    """Generate timestamp 1 hour in the past."""
    return datetime.now(timezone.utc) - timedelta(hours=1)


@pytest.fixture
def ttl_24_hours():
    """TTL expiration 24 hours from now."""
    return datetime.now(timezone.utc) + timedelta(hours=24)


@pytest.fixture
def ttl_7_days():
    """TTL expiration 7 days from now."""
    return datetime.now(timezone.utc) + timedelta(days=7)


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def postgres_config():
    """PostgreSQL adapter configuration for testing."""
    import os
    return {
        'url': os.getenv('POSTGRES_URL', 'postgresql://localhost:5432/mas_memory'),
        'table': 'active_context',
        'metrics': {'enabled': True}
    }


@pytest.fixture
def redis_config():
    """Redis adapter configuration for testing."""
    import os
    return {
        'url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        'window_size': 10,
        'ttl_seconds': 86400,
        'metrics': {'enabled': True}
    }


@pytest.fixture
def qdrant_config():
    """Qdrant adapter configuration for testing."""
    import os
    stg_ip = os.getenv('STG_IP', 'localhost')
    qdrant_port = os.getenv('QDRANT_PORT', '6333')
    return {
        'url': f'http://{stg_ip}:{qdrant_port}',
        'collection_name': 'test_semantic_memory',
        'vector_size': 384,
        'metrics': {'enabled': True}
    }


@pytest.fixture
def neo4j_config():
    """Neo4j adapter configuration for testing."""
    import os
    stg_ip = os.getenv('STG_IP', 'localhost')
    neo4j_port = os.getenv('NEO4J_BOLT_PORT', '7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
    return {
        'uri': f'bolt://{stg_ip}:{neo4j_port}',
        'user': neo4j_user,
        'password': neo4j_password,
        'database': 'neo4j',
        'metrics': {'enabled': True}
    }


@pytest.fixture
def typesense_config():
    """Typesense adapter configuration for testing."""
    import os
    stg_ip = os.getenv('STG_IP', 'localhost')
    typesense_port = os.getenv('TYPESENSE_PORT', '8108')
    typesense_api_key = os.getenv('TYPESENSE_API_KEY', 'xyz')
    return {
        'url': f'http://{stg_ip}:{typesense_port}',
        'api_key': typesense_api_key,
        'collection_name': 'test_search_memory',
        'metrics': {'enabled': True}
    }
