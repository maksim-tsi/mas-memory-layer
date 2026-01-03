"""
Smoke Tests for Infrastructure Connectivity

This module provides connectivity tests for all infrastructure services:
- PostgreSQL (mas_memory database)
- Redis
- Qdrant (vector store)
- Neo4j (graph database)
- Typesense (search engine)

These tests can be run from any machine with network access to the services.
Configuration is loaded from environment variables (.env file).

Usage:
    pytest tests/test_connectivity.py -v
    
    # Run specific test
    pytest tests/test_connectivity.py::test_postgres_connection -v
    
    # Run with detailed output
    pytest tests/test_connectivity.py -v -s
"""

import os
import pytest

# Import clients for each service
try:
    import redis
except ImportError:
    redis = None

try:
    import asyncpg
except ImportError:
    asyncpg = None

try:
    import psycopg
except ImportError:
    psycopg = None

try:
    from qdrant_client import QdrantClient
except ImportError:
    QdrantClient = None

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None

try:
    import requests
except ImportError:
    requests = None


# ============================================================================
# Fixtures for Configuration
# ============================================================================

@pytest.fixture(scope="session")
def config():
    """Load configuration from environment variables"""
    # Load from .env file if it exists
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Don't override existing env vars
                    if key not in os.environ:
                        os.environ[key] = value
    
    return {
        # PostgreSQL
        'postgres_host': os.getenv('DATA_NODE_IP', '192.168.107.187'),
        'postgres_port': int(os.getenv('POSTGRES_PORT', '5432')),
        'postgres_user': os.getenv('POSTGRES_USER', 'postgres'),
        'postgres_password': os.getenv('POSTGRES_PASSWORD'),
        'postgres_db': os.getenv('POSTGRES_DB', 'mas_memory'),
        
        # Redis
        'redis_host': os.getenv('DEV_NODE_IP', '192.168.107.172'),
        'redis_port': int(os.getenv('REDIS_PORT', '6379')),
        
        # Qdrant
        'qdrant_host': os.getenv('DATA_NODE_IP', '192.168.107.187'),
        'qdrant_port': int(os.getenv('QDRANT_PORT', '6333')),
        
        # Neo4j
        'neo4j_host': os.getenv('DATA_NODE_IP', '192.168.107.187'),
        'neo4j_bolt_port': int(os.getenv('NEO4J_BOLT_PORT', '7687')),
        'neo4j_user': os.getenv('NEO4J_USER', 'neo4j'),
        'neo4j_password': os.getenv('NEO4J_PASSWORD'),
        
        # Typesense
        'typesense_host': os.getenv('DATA_NODE_IP', '192.168.107.187'),
        'typesense_port': int(os.getenv('TYPESENSE_PORT', '8108')),
        'typesense_api_key': os.getenv('TYPESENSE_API_KEY'),
    }


# ============================================================================
# PostgreSQL Tests
# ============================================================================

@pytest.mark.skipif(
    asyncpg is None and psycopg is None, 
    reason="asyncpg or psycopg not installed"
)
@pytest.mark.asyncio
async def test_postgres_connection(config):
    """Test PostgreSQL connection"""
    if asyncpg is not None:
        # Use asyncpg if available
        conn = None
        try:
            conn = await asyncpg.connect(
                host=config['postgres_host'],
                port=config['postgres_port'],
                user=config['postgres_user'],
                password=config['postgres_password'],
                database=config['postgres_db'],
                timeout=5
            )
            
            # Verify we're connected to the right database
            db_name = await conn.fetchval('SELECT current_database()')
            assert db_name == 'mas_memory', f"Expected 'mas_memory' database, got '{db_name}'"
            
            print(f"✓ PostgreSQL connected (asyncpg): {config['postgres_host']}:{config['postgres_port']}/{db_name}")
            
        finally:
            if conn:
                await conn.close()
    else:
        # Use psycopg[binary]
        import psycopg
        conn = None
        try:
            conn = psycopg.connect(
                host=config['postgres_host'],
                port=config['postgres_port'],
                user=config['postgres_user'],
                password=config['postgres_password'],
                dbname=config['postgres_db'],
                connect_timeout=5
            )
            
            # Verify we're connected to the right database
            with conn.cursor() as cur:
                cur.execute('SELECT current_database()')
                db_name = cur.fetchone()[0]
                assert db_name == 'mas_memory', f"Expected 'mas_memory' database, got '{db_name}'"
            
            print(f"✓ PostgreSQL connected (psycopg): {config['postgres_host']}:{config['postgres_port']}/{db_name}")
            
        finally:
            if conn:
                conn.close()


@pytest.mark.skipif(
    asyncpg is None and psycopg is None,
    reason="asyncpg or psycopg not installed"
)
@pytest.mark.asyncio
async def test_postgres_version(config):
    """Test PostgreSQL version and basic query"""
    if asyncpg is not None:
        # Use asyncpg if available
        conn = None
        try:
            conn = await asyncpg.connect(
                host=config['postgres_host'],
                port=config['postgres_port'],
                user=config['postgres_user'],
                password=config['postgres_password'],
                database=config['postgres_db'],
                timeout=5
            )
            
            version = await conn.fetchval('SELECT version()')
            assert 'PostgreSQL' in version
            
            # Test basic query
            result = await conn.fetchval('SELECT 1 + 1')
            assert result == 2
            
            print(f"✓ PostgreSQL version (asyncpg): {version.split(',')[0]}")
            
        finally:
            if conn:
                await conn.close()
    else:
        # Use psycopg[binary]
        import psycopg
        conn = None
        try:
            conn = psycopg.connect(
                host=config['postgres_host'],
                port=config['postgres_port'],
                user=config['postgres_user'],
                password=config['postgres_password'],
                dbname=config['postgres_db'],
                connect_timeout=5
            )
            
            with conn.cursor() as cur:
                cur.execute('SELECT version()')
                version = cur.fetchone()[0]
                assert 'PostgreSQL' in version
                
                cur.execute('SELECT 1 + 1')
                result = cur.fetchone()[0]
                assert result == 2
            
            print(f"✓ PostgreSQL version (psycopg): {version.split(',')[0]}")
            
        finally:
            if conn:
                conn.close()


# ============================================================================
# Redis Tests
# ============================================================================

@pytest.mark.skipif(redis is None, reason="redis not installed")
def test_redis_connection(config):
    """Test Redis connection"""
    client = None
    try:
        client = redis.Redis(
            host=config['redis_host'],
            port=config['redis_port'],
            socket_connect_timeout=5,
            decode_responses=True
        )
        
        # Test PING
        assert client.ping() is True
        
        print(f"✓ Redis connected: {config['redis_host']}:{config['redis_port']}")
        
    finally:
        if client:
            client.close()


@pytest.mark.skipif(redis is None, reason="redis not installed")
def test_redis_operations(config):
    """Test basic Redis operations"""
    client = None
    try:
        client = redis.Redis(
            host=config['redis_host'],
            port=config['redis_port'],
            socket_connect_timeout=5,
            decode_responses=True
        )
        
        # Set and get a test key
        test_key = 'smoke_test:connectivity'
        test_value = 'test_value_12345'
        
        client.set(test_key, test_value, ex=60)  # Expire in 60 seconds
        retrieved = client.get(test_key)
        assert retrieved == test_value
        
        # Clean up
        client.delete(test_key)
        
        print("✓ Redis operations: SET/GET working")
        
    finally:
        if client:
            client.close()


# ============================================================================
# Qdrant Tests
# ============================================================================

@pytest.mark.skipif(QdrantClient is None, reason="qdrant-client not installed")
def test_qdrant_connection(config):
    """Test Qdrant connection"""
    client = None
    try:
        client = QdrantClient(
            host=config['qdrant_host'],
            port=config['qdrant_port'],
            timeout=5
        )
        
        # Test basic health check
        collections = client.get_collections()
        assert collections is not None
        
        print(f"✓ Qdrant connected: {config['qdrant_host']}:{config['qdrant_port']}")
        print(f"  Collections: {len(collections.collections)}")
        
    except Exception as e:
        pytest.fail(f"Qdrant connection failed: {e}")


@pytest.mark.skipif(QdrantClient is None, reason="qdrant-client not installed")
def test_qdrant_health(config):
    """Test Qdrant health status"""
    client = None
    try:
        client = QdrantClient(
            host=config['qdrant_host'],
            port=config['qdrant_port'],
            timeout=5
        )
        
        # Test that we can get collections (indicates service is healthy)
        collections = client.get_collections()
        assert collections is not None
        
        print("✓ Qdrant health check passed")
        
    except Exception as e:
        pytest.fail(f"Qdrant health check failed: {e}")


# ============================================================================
# Neo4j Tests
# ============================================================================

@pytest.mark.skipif(GraphDatabase is None, reason="neo4j not installed")
def test_neo4j_connection(config):
    """Test Neo4j connection"""
    driver = None
    try:
        uri = f"bolt://{config['neo4j_host']}:{config['neo4j_bolt_port']}"
        driver = GraphDatabase.driver(
            uri,
            auth=(config['neo4j_user'], config['neo4j_password']),
            connection_timeout=5
        )
        
        # Verify connection
        driver.verify_connectivity()
        
        print(f"✓ Neo4j connected: {uri}")
        
    finally:
        if driver:
            driver.close()


@pytest.mark.skipif(GraphDatabase is None, reason="neo4j not installed")
def test_neo4j_query(config):
    """Test basic Neo4j query"""
    driver = None
    try:
        uri = f"bolt://{config['neo4j_host']}:{config['neo4j_bolt_port']}"
        driver = GraphDatabase.driver(
            uri,
            auth=(config['neo4j_user'], config['neo4j_password'])
        )
        
        with driver.session() as session:
            # Simple test query
            result = session.run("RETURN 1 AS num")
            record = result.single()
            assert record['num'] == 1
            
            print("✓ Neo4j query execution working")
        
    finally:
        if driver:
            driver.close()


# ============================================================================
# Typesense Tests
# ============================================================================

@pytest.mark.skipif(requests is None, reason="requests not installed")
def test_typesense_connection(config):
    """Test Typesense connection via HTTP"""
    url = f"http://{config['typesense_host']}:{config['typesense_port']}/health"
    
    try:
        response = requests.get(url, timeout=5)
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data.get('ok') is True
        
        print(f"✓ Typesense connected: {config['typesense_host']}:{config['typesense_port']}")
        
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Typesense connection failed: {e}")


@pytest.mark.skipif(requests is None, reason="requests not installed")
def test_typesense_auth(config):
    """Test Typesense authentication"""
    url = f"http://{config['typesense_host']}:{config['typesense_port']}/collections"
    
    headers = {
        'X-TYPESENSE-API-KEY': config['typesense_api_key']
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        
        # Should get 200 with valid auth
        assert response.status_code == 200
        
        collections = response.json()
        assert isinstance(collections, list)
        
        print("✓ Typesense authentication working")
        print(f"  Collections: {len(collections)}")
        
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Typesense authentication test failed: {e}")


# ============================================================================
# Summary Test
# ============================================================================

@pytest.mark.skipif(
    not all([redis, asyncpg, QdrantClient, GraphDatabase, requests]),
    reason="Some dependencies not installed"
)
def test_all_services_summary(config):
    """
    Summary test - reports on all services
    This test always passes but provides visibility into overall connectivity
    """
    services_status = {}
    
    # Test each service
    try:
        r = redis.Redis(host=config['redis_host'], port=config['redis_port'], socket_connect_timeout=2)
        services_status['Redis'] = '✓' if r.ping() else '✗'
        r.close()
    except Exception:
        services_status['Redis'] = '✗'
    
    try:
        q = QdrantClient(host=config['qdrant_host'], port=config['qdrant_port'], timeout=2)
        q.get_collections()
        services_status['Qdrant'] = '✓'
    except Exception:
        services_status['Qdrant'] = '✗'
    
    try:
        uri = f"bolt://{config['neo4j_host']}:{config['neo4j_bolt_port']}"
        driver = GraphDatabase.driver(uri, auth=(config['neo4j_user'], config['neo4j_password']))
        driver.verify_connectivity()
        services_status['Neo4j'] = '✓'
        driver.close()
    except Exception:
        services_status['Neo4j'] = '✗'
    
    try:
        url = f"http://{config['typesense_host']}:{config['typesense_port']}/health"
        resp = requests.get(url, timeout=2)
        services_status['Typesense'] = '✓' if resp.status_code == 200 else '✗'
    except Exception:
        services_status['Typesense'] = '✗'
    
    print("\n" + "="*60)
    print("INFRASTRUCTURE CONNECTIVITY SUMMARY")
    print("="*60)
    for service, status in services_status.items():
        print(f"{status} {service}")
    print("="*60)
    
    # Test passes if printed (it's just a summary)
    assert True
