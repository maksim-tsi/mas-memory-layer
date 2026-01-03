"""
Connectivity tests for live cluster infrastructure.

Verifies all 5 storage adapters can connect to the 3-node research cluster:
- Node 1 (192.168.107.172): Redis L1
- Node 2 (192.168.107.187): PostgreSQL L2, Qdrant L3, Neo4j L3, Typesense L4
"""

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_l2_schema_verification(verify_l2_schema):
    """Verify migration 002 (content_tsv) has been applied to PostgreSQL."""
    # Fixture handles verification - if we get here, schema is correct
    assert True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_connectivity(redis_adapter, test_session_id):
    """Verify Redis L1 connectivity on Node 1 (192.168.107.172:6379)."""
    # Test basic operations
    data = {
        'session_id': test_session_id,
        'turn_id': 1,
        'content': 'connectivity test'
    }
    record_id = await redis_adapter.store(data)
    assert record_id is not None
    
    result = await redis_adapter.retrieve(record_id)
    assert result is not None
    assert result['content'] == 'connectivity test'


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_connectivity(postgres_adapter, test_session_id):
    """Verify PostgreSQL L2 connectivity on Node 2 (192.168.107.187:5432)."""
    # Test basic store/retrieve operations
    # Note: PostgreSQL adapter defaults to 'active_context' table
    data = {
        'session_id': test_session_id,
        'turn_id': 1,
        'content': 'connectivity test'
    }
    record_id = await postgres_adapter.store(data)
    assert record_id is not None
    
    result = await postgres_adapter.retrieve(record_id)
    assert result is not None
    assert result['content'] == 'connectivity test'


@pytest.mark.integration
@pytest.mark.asyncio
async def test_neo4j_connectivity(neo4j_adapter, test_session_id):
    """Verify Neo4j L3 connectivity on Node 2 (192.168.107.187:7687)."""
    # Test basic store/retrieve operations
    data = {
        'type': 'entity',  # Neo4j expects 'entity' or 'relationship'
        'label': 'Episode',
        'properties': {
            'session_id': test_session_id,
            'summary': 'connectivity test',
            'created_at': '2024-01-01T00:00:00Z'
        }
    }
    record_id = await neo4j_adapter.store(data)
    assert record_id is not None
    
    result = await neo4j_adapter.retrieve(record_id)
    assert result is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_qdrant_connectivity(qdrant_adapter):
    """Verify Qdrant L3 connectivity on Node 2 (192.168.107.187:6333)."""
    # Adapter connection is verified by fixture
    # Additional checks can be added here
    assert qdrant_adapter is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_typesense_connectivity(typesense_adapter):
    """Verify Typesense L4 connectivity on Node 2 (192.168.107.187:8108)."""
    # Adapter connection is verified by fixture
    # Additional checks can be added here
    assert typesense_adapter is not None
