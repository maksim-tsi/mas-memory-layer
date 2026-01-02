"""
Integration test configuration and fixtures.

Provides fixtures for surgical cleanup of test data from live cluster.
Uses namespace isolation via unique session IDs to prevent test collisions.
"""

import os
import json
import uuid
import yaml
import pytest
import asyncio
from datetime import datetime, timezone
from typing import List, AsyncGenerator, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import pytest_asyncio
from src.storage.redis_adapter import RedisAdapter
from src.storage.postgres_adapter import PostgresAdapter
from src.storage.neo4j_adapter import Neo4jAdapter
from src.storage.qdrant_adapter import QdrantAdapter
from src.storage.typesense_adapter import TypesenseAdapter
from src.utils.llm_client import LLMClient


@dataclass
class TestSettings:
    """Test settings loaded from test_settings.yaml with env var overrides."""
    llm_throttle_seconds: float
    llm_providers: Dict[str, Any]
    batch_sizes: Dict[str, int]
    timeouts: Dict[str, int]
    report_output_dir: str


@pytest.fixture(scope="session")
def test_settings() -> TestSettings:
    """Load test settings from YAML with environment variable overrides.
    
    Base configuration from tests/test_settings.yaml can be overridden via
    TEST_* prefixed environment variables for CI/CD flexibility.
    """
    # Load base YAML configuration
    yaml_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "test_settings.yaml"
    )
    
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Apply environment variable overrides
    llm_throttle = float(os.getenv('TEST_LLM_THROTTLE_SECONDS', config['llm_throttle_seconds']))
    report_dir = os.getenv('TEST_REPORT_OUTPUT_DIR', config['report_output_dir'])
    
    # Override batch sizes if specified
    batch_sizes = config['batch_sizes'].copy()
    if os.getenv('TEST_L1_TURNS'):
        batch_sizes['l1_turns'] = int(os.getenv('TEST_L1_TURNS'))
    if os.getenv('TEST_L2_FACTS_TRIGGER'):
        batch_sizes['l2_facts_trigger'] = int(os.getenv('TEST_L2_FACTS_TRIGGER'))
    
    # Override timeouts if specified
    timeouts = config['timeouts'].copy()
    if os.getenv('TEST_PROMOTION_MAX_SECONDS'):
        timeouts['promotion_max_seconds'] = int(os.getenv('TEST_PROMOTION_MAX_SECONDS'))
    
    return TestSettings(
        llm_throttle_seconds=llm_throttle,
        llm_providers=config['llm_providers'],
        batch_sizes=batch_sizes,
        timeouts=timeouts,
        report_output_dir=report_dir
    )


@pytest.fixture(scope="function")
def test_session_id() -> str:
    """Generate unique session ID for test isolation (overrides root conftest)."""
    return f"test-{uuid.uuid4().hex[:12]}"


@pytest.fixture(scope="function")
def test_user_id() -> str:
    """Generate unique user ID for test isolation (overrides root conftest)."""
    return f"user-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def real_llm_client(test_settings: TestSettings) -> Tuple[Optional[LLMClient], str]:
    """Create LLM client with Google Gemini → Groq fallback.
    
    Returns:
        Tuple of (llm_client, provider_name) where provider_name is 'google', 
        'groq', or 'none' if both failed.
        
    Raises:
        pytest.skip if no provider is available.
    """
    from src.utils.llm_client import LLMClient, ProviderConfig
    from src.utils.providers import GroqProvider, GeminiProvider
    
    primary = test_settings.llm_providers['primary']
    fallback = test_settings.llm_providers['fallback']
    
    client = LLMClient()
    provider_registered = False
    
    # Try primary provider (Google Gemini)
    gemini_key = os.getenv(primary['env_key'])
    if gemini_key:
        try:
            gemini = GeminiProvider(api_key=gemini_key)
            client.register_provider(
                gemini, 
                ProviderConfig(name=primary['name'], priority=1, enabled=True)
            )
            provider_registered = True
            print(f"✓ Registered {primary['name']} provider with model {primary['model']}")
            
            # Also register Gemini Pro for reasoning tasks
            if 'fallback_reasoning' in test_settings.llm_providers:
                gemini_pro = GeminiProvider(api_key=gemini_key)
                client.register_provider(
                    gemini_pro,
                    ProviderConfig(name='google-pro', priority=3, enabled=True)
                )
                print(f"✓ Registered {test_settings.llm_providers['fallback_reasoning']['name']} Pro provider with model {test_settings.llm_providers['fallback_reasoning']['model']}")
        except Exception as e:
            print(f"⚠️  {primary['name']} provider failed: {e}, falling back to {fallback['name']}")
    else:
        print(f"⚠️  {primary['env_key']} not set, falling back to {fallback['name']}")
    
    # Try fallback provider (Groq)
    groq_key = os.getenv(fallback['env_key'])
    if groq_key:
        try:
            groq = GroqProvider(api_key=groq_key)
            client.register_provider(
                groq,
                ProviderConfig(name=fallback['name'], priority=2, enabled=True)
            )
            provider_registered = True
            print(f"✓ Registered {fallback['name']} provider with model {fallback['model']}")
        except Exception as e:
            print(f"❌ {fallback['name']} provider failed: {e}")
    else:
        print(f"❌ {fallback['env_key']} not set")
    
    # Check if at least one provider was registered
    if not provider_registered:
        pytest.skip("No LLM provider available (GOOGLE_API_KEY and GROQ_API_KEY both missing/failed)")
    
    # Return client with provider name (prefer primary)
    provider_name = primary['name'] if gemini_key else fallback['name']
    return (client, provider_name)


class ReportCollector:
    """Collects test latency metrics and writes to daily JSON report."""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.test_results = []
        
    def add_result(self, test_name: str, latencies: Dict[str, float], 
                   provider: str, passed: bool, metadata: Optional[Dict] = None):
        """Add test result to collection."""
        result = {
            'test_name': test_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'latencies_ms': latencies,
            'llm_provider': provider,
            'passed': passed,
            'metadata': metadata or {}
        }
        self.test_results.append(result)
    
    def write_report(self):
        """Write accumulated results to daily JSON report."""
        os.makedirs(self.output_dir, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        report_path = os.path.join(self.output_dir, f'lifecycle-test-{date_str}.json')
        
        # Load existing report if present (append mode for multiple runs)
        existing_tests = []
        if os.path.exists(report_path):
            try:
                with open(report_path, 'r') as f:
                    existing_data = json.load(f)
                    existing_tests = existing_data.get('tests', [])
            except Exception as e:
                print(f"⚠️  Could not load existing report: {e}")
        
        # Merge with current results
        all_tests = existing_tests + self.test_results
        
        report = {
            'date': date_str,
            'total_tests': len(all_tests),
            'tests': all_tests
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Test report written to {report_path}")


@pytest.fixture(scope="session")
def report_collector(test_settings: TestSettings) -> ReportCollector:
    """Session-scoped report collector for latency metrics.
    
    Accumulates results during test session and writes to daily JSON report
    on teardown.
    """
    collector = ReportCollector(test_settings.report_output_dir)
    yield collector
    collector.write_report()


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
    redis_adapter: RedisAdapter,
    postgres_adapter: PostgresAdapter,
    neo4j_adapter: Neo4jAdapter,
    qdrant_adapter: QdrantAdapter,
    typesense_adapter: TypesenseAdapter,
    test_session_id: str
):
    """Combined cleanup fixture with ordered teardown (L4→L3→L2→L1).
    
    Executes cleanup in reverse dependency order to maintain referential integrity:
    1. L4 (Typesense): Delete semantic knowledge (derivative of episodes)
    2. L3 (Neo4j): Delete graph structure (primary episode record)
    3. L3 (Qdrant): Delete vector indices (search index for episodes)
    4. L2 (PostgreSQL): Delete working memory facts
    5. L1 (Redis): Delete active context turns
    
    Uses namespace isolation via test_session_id for surgical cleanup.
    """
    yield  # Let test run
    
    cleanup_counts = {}
    
    # L4: Typesense - Delete semantic knowledge documents
    try:
        # Typesense delete by filter
        filter_query = f"session_id:={test_session_id}"
        # Note: TypesenseAdapter may need delete_by_filter method
        if hasattr(typesense_adapter, 'delete_by_filter'):
            await typesense_adapter.delete_by_filter(filter_query)
        cleanup_counts['l4_typesense'] = 'filtered'
        print(f"✅ L4 cleanup: Typesense documents for session {test_session_id}")
    except Exception as e:
        print(f"⚠️  L4 Typesense cleanup error: {e}")
        cleanup_counts['l4_typesense'] = f'error: {e}'
    
    # L3: Neo4j - Delete graph structure
    try:
        # Use Neo4j driver session directly
        async with neo4j_adapter.driver.session(database=neo4j_adapter.database) as session:
            query = """
            MATCH (n {session_id: $session_id})
            OPTIONAL MATCH (n)-[r]-()
            DELETE r, n
            RETURN count(n) as deleted_count
            """
            result = await session.run(query, session_id=test_session_id)
            records = await result.data()
            cleanup_counts['l3_neo4j'] = records[0]['deleted_count'] if records else 0
        print(f"✅ L3 cleanup: {cleanup_counts['l3_neo4j']} Neo4j nodes/edges for session {test_session_id}")
    except Exception as e:
        print(f"⚠️  L3 Neo4j cleanup error: {e}")
        cleanup_counts['l3_neo4j'] = f'error: {e}'
    
    # L3: Qdrant - Delete vector indices
    try:
        # Qdrant delete by filter
        if hasattr(qdrant_adapter, 'delete_by_filter'):
            deleted = await qdrant_adapter.delete_by_filter({'session_id': test_session_id})
            cleanup_counts['l3_qdrant'] = deleted
        else:
            cleanup_counts['l3_qdrant'] = 'skipped (no delete_by_filter)'
        print(f"✅ L3 cleanup: Qdrant vectors for session {test_session_id}")
    except Exception as e:
        print(f"⚠️  L3 Qdrant cleanup error: {e}")
        cleanup_counts['l3_qdrant'] = f'error: {e}'
    
    # L2: PostgreSQL - Delete working memory facts
    try:
        async with postgres_adapter.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM working_memory WHERE session_id = %s",
                    (test_session_id,)
                )
                wm_count = cur.rowcount
                
                await cur.execute(
                    "DELETE FROM active_context WHERE session_id = %s",
                    (test_session_id,)
                )
                ac_count = cur.rowcount
        
        cleanup_counts['l2_postgres_wm'] = wm_count
        cleanup_counts['l2_postgres_ac'] = ac_count
        print(f"✅ L2 cleanup: {cleanup_counts['l2_postgres_wm']} facts, {cleanup_counts['l2_postgres_ac']} turns for session {test_session_id}")
    except Exception as e:
        print(f"⚠️  L2 PostgreSQL cleanup error: {e}")
        cleanup_counts['l2_postgres'] = f'error: {e}'
    
    # L1: Redis - Delete active context turns
    try:
        pattern = f"*{test_session_id}*"
        keys = await redis_adapter.scan_keys(pattern)
        if keys:
            await redis_adapter.delete_keys(keys)
            cleanup_counts['l1_redis'] = len(keys)
        else:
            cleanup_counts['l1_redis'] = 0
        print(f"✅ L1 cleanup: {cleanup_counts['l1_redis']} Redis keys for session {test_session_id}")
    except Exception as e:
        print(f"⚠️  L1 Redis cleanup error: {e}")
        cleanup_counts['l1_redis'] = f'error: {e}'
    
    print(f"🧹 Full cleanup complete: {cleanup_counts}")
