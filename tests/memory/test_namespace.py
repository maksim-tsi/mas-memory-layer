"""
Tests for Redis namespace management with Hash Tags.

Test Coverage:
- Key generation for all namespace types
- Hash Tag extraction and validation
- Lifecycle event publishing
- MAXLEN stream trimming behavior
- Fire-and-forget resilience
"""

import pytest
import pytest_asyncio
import redis.asyncio as redis
import os
import uuid
import json
from datetime import datetime, timezone

from src.memory.namespace import NamespaceManager


@pytest.fixture
def session_id():
    """Generate unique test session ID."""
    return f"test-{uuid.uuid4()}"


@pytest.fixture
def agent_id():
    """Generate unique test agent ID."""
    return f"agent-{uuid.uuid4()}"


@pytest_asyncio.fixture
async def redis_client():
    """
    Create Redis client for testing.
    
    Skips tests if REDIS_URL environment variable not set.
    """
    redis_url = os.getenv('REDIS_URL')
    if not redis_url:
        pytest.skip("REDIS_URL environment variable not set")
    
    client = redis.from_url(redis_url, decode_responses=True)
    
    try:
        await client.ping()
    except redis.RedisError:
        pytest.skip("Redis server not available")
    
    yield client
    
    await client.aclose()


@pytest_asyncio.fixture
async def namespace_manager(redis_client):
    """Create namespace manager with Redis client."""
    return NamespaceManager(redis_client)


@pytest_asyncio.fixture
async def cleanup_keys(redis_client):
    """Cleanup test keys after test."""
    keys_to_clean = []
    
    def register(key: str):
        keys_to_clean.append(key)
    
    yield register
    
    # Cleanup
    if keys_to_clean:
        await redis_client.delete(*keys_to_clean)


class TestKeyGeneration:
    """Test key generation methods."""
    
    def test_l1_turns_key_format(self, session_id):
        """Test L1 turns key format with Hash Tag."""
        key = NamespaceManager.l1_turns(session_id)
        
        assert key == f"{{session:{session_id}}}:turns"
        assert "{" in key
        assert "}" in key
    
    def test_personal_state_key_format(self, session_id, agent_id):
        """Test personal state key format with Hash Tag."""
        key = NamespaceManager.personal_state(agent_id, session_id)
        
        assert key == f"{{session:{session_id}}}:agent:{agent_id}:state"
        assert f"{{session:{session_id}}}" in key
    
    def test_shared_workspace_key_format(self, session_id):
        """Test shared workspace key format with Hash Tag."""
        key = NamespaceManager.shared_workspace(session_id)
        
        assert key == f"{{session:{session_id}}}:workspace"
        assert f"{{session:{session_id}}}" in key
    
    def test_l2_facts_index_key_format(self, session_id):
        """Test L2 facts index key format with Hash Tag."""
        key = NamespaceManager.l2_facts_index(session_id)
        
        assert key == f"{{session:{session_id}}}:facts:index"
        assert f"{{session:{session_id}}}" in key
    
    def test_lifecycle_stream_key_format(self):
        """Test global lifecycle stream key format."""
        key = NamespaceManager.lifecycle_stream()
        
        assert key == "{mas}:lifecycle"
        assert "{mas}" in key
    
    def test_hash_tag_extraction(self, session_id):
        """Test that Hash Tags can be extracted for slot calculation."""
        key = NamespaceManager.l1_turns(session_id)
        
        # Extract Hash Tag (substring between { and })
        start = key.index("{")
        end = key.index("}", start)
        hash_tag = key[start+1:end]
        
        assert hash_tag == f"session:{session_id}"
    
    def test_consistent_hash_tag_across_session_keys(self, session_id, agent_id):
        """Test that all session keys use the same Hash Tag value."""
        l1_key = NamespaceManager.l1_turns(session_id)
        personal_key = NamespaceManager.personal_state(agent_id, session_id)
        workspace_key = NamespaceManager.shared_workspace(session_id)
        facts_key = NamespaceManager.l2_facts_index(session_id)
        
        # Extract Hash Tags
        def extract_hash_tag(key):
            start = key.index("{")
            end = key.index("}", start)
            return key[start+1:end]
        
        l1_tag = extract_hash_tag(l1_key)
        personal_tag = extract_hash_tag(personal_key)
        workspace_tag = extract_hash_tag(workspace_key)
        facts_tag = extract_hash_tag(facts_key)
        
        # All should have the same Hash Tag value
        assert l1_tag == personal_tag == workspace_tag == facts_tag
        assert l1_tag == f"session:{session_id}"


class TestLifecycleEventPublishing:
    """Test lifecycle event publishing to global stream."""
    
    @pytest.mark.asyncio
    async def test_publish_lifecycle_event(
        self, 
        namespace_manager, 
        session_id,
        cleanup_keys
    ):
        """Test publishing a lifecycle event."""
        stream_key = NamespaceManager.lifecycle_stream()
        cleanup_keys(stream_key)
        
        event_id = await namespace_manager.publish_lifecycle_event(
            event_type="promotion",
            session_id=session_id,
            data={"fact_count": 5, "ciar_threshold": 0.6}
        )
        
        assert event_id  # Non-empty event ID
        assert isinstance(event_id, str)
    
    @pytest.mark.asyncio
    async def test_event_contains_metadata(
        self, 
        namespace_manager, 
        redis_client,
        session_id,
        cleanup_keys
    ):
        """Test that published events contain proper metadata."""
        stream_key = NamespaceManager.lifecycle_stream()
        cleanup_keys(stream_key)
        
        event_id = await namespace_manager.publish_lifecycle_event(
            event_type="consolidation",
            session_id=session_id,
            data={"episodes_created": 3}
        )
        
        # Read the event back
        events = await redis_client.xrange(stream_key, min=event_id, max=event_id)
        
        assert len(events) == 1
        _, fields = events[0]
        
        assert fields["type"] == "consolidation"
        assert fields["session_id"] == session_id
        assert "timestamp" in fields
        
        # Data should be JSON-encoded
        data = json.loads(fields["data"])
        assert data["episodes_created"] == 3
    
    @pytest.mark.asyncio
    async def test_maxlen_trimming(
        self, 
        namespace_manager, 
        redis_client,
        cleanup_keys
    ):
        """Test that stream is trimmed at MAXLEN threshold."""
        stream_key = NamespaceManager.lifecycle_stream()
        cleanup_keys(stream_key)
        
        # Publish with small MAXLEN for testing
        max_length = 10
        
        # Publish 20 events (should trim to ~10)
        for i in range(20):
            await namespace_manager.publish_lifecycle_event(
                event_type="test",
                session_id=f"session-{i}",
                data={"index": i},
                max_length=max_length
            )
        
        # Check stream length
        stream_info = await redis_client.xinfo_stream(stream_key)
        stream_length = stream_info["length"]
        
        # With approximate trimming (~), length should be close to max_length
        # but not exactly (lazy trimming on macro-node boundaries)
        assert stream_length <= max_length * 1.2  # Allow 20% variance
    
    @pytest.mark.asyncio
    async def test_fire_and_forget_resilience(
        self, 
        namespace_manager, 
        session_id
    ):
        """Test that publishing doesn't raise even if Redis fails."""
        # Create manager with invalid client (simulates connection failure)
        bad_client = redis.from_url("redis://invalid:6379", decode_responses=True)
        bad_manager = NamespaceManager(bad_client)
        
        # Should not raise exception (fire-and-forget)
        event_id = await bad_manager.publish_lifecycle_event(
            event_type="test",
            session_id=session_id,
            data={"test": "data"}
        )
        
        # Returns empty string on failure
        assert event_id == ""
        
        await bad_client.aclose()
    
    @pytest.mark.asyncio
    async def test_publish_without_redis_client_raises(self, session_id):
        """Test that publishing without Redis client raises ValueError."""
        manager = NamespaceManager()  # No Redis client
        
        with pytest.raises(ValueError, match="requires redis_client"):
            await manager.publish_lifecycle_event(
                event_type="test",
                session_id=session_id,
                data={}
            )


class TestHashTagClusterSafety:
    """Test Hash Tag properties for Redis Cluster safety."""
    
    def test_same_session_keys_have_same_slot(self, session_id, agent_id):
        """Test that all keys for a session would hash to the same slot."""
        import crc16  # Redis uses CRC16 for slot calculation
        
        keys = [
            NamespaceManager.l1_turns(session_id),
            NamespaceManager.personal_state(agent_id, session_id),
            NamespaceManager.shared_workspace(session_id),
            NamespaceManager.l2_facts_index(session_id),
        ]
        
        # Extract Hash Tag and calculate slot for each
        def calculate_slot(key):
            start = key.index("{")
            end = key.index("}", start)
            hash_tag = key[start+1:end]
            # Redis Cluster uses CRC16 % 16384
            return crc16.crc16xmodem(hash_tag.encode()) % 16384
        
        slots = [calculate_slot(key) for key in keys]
        
        # All slots should be identical
        assert len(set(slots)) == 1, "All session keys must hash to same slot"
    
    def test_different_sessions_different_slots(self):
        """Test that different sessions likely hash to different slots."""
        session1 = str(uuid.uuid4())
        session2 = str(uuid.uuid4())
        
        key1 = NamespaceManager.l1_turns(session1)
        key2 = NamespaceManager.l1_turns(session2)
        
        # Extract Hash Tags
        def extract_hash_tag(key):
            start = key.index("{")
            end = key.index("}", start)
            return key[start+1:end]
        
        tag1 = extract_hash_tag(key1)
        tag2 = extract_hash_tag(key2)
        
        # Tags should be different
        assert tag1 != tag2
    
    def test_global_stream_has_consistent_slot(self):
        """Test that global lifecycle stream key has consistent Hash Tag."""
        key1 = NamespaceManager.lifecycle_stream()
        key2 = NamespaceManager.lifecycle_stream()
        
        assert key1 == key2
        assert key1 == "{mas}:lifecycle"


@pytest.mark.benchmark
class TestNamespacePerformance:
    """Benchmark namespace operations."""
    
    def test_key_generation_performance(self, benchmark):
        """Benchmark key generation speed."""
        session_id = str(uuid.uuid4())
        
        def generate_keys():
            NamespaceManager.l1_turns(session_id)
            NamespaceManager.shared_workspace(session_id)
            NamespaceManager.l2_facts_index(session_id)
        
        # Should be sub-microsecond (pure string formatting)
        result = benchmark(generate_keys)
        assert result is None  # No return value
    
    @pytest.mark.asyncio
    async def test_event_publishing_throughput(
        self, 
        namespace_manager,
        cleanup_keys
    ):
        """Test event publishing throughput."""
        stream_key = NamespaceManager.lifecycle_stream()
        cleanup_keys(stream_key)
        
        # Publish 100 events and measure time
        import time
        start = time.time()
        
        for i in range(100):
            await namespace_manager.publish_lifecycle_event(
                event_type="benchmark",
                session_id=f"session-{i}",
                data={"index": i}
            )
        
        duration = time.time() - start
        ops_per_sec = 100 / duration
        
        # Should achieve >100 ops/sec
        assert ops_per_sec > 100, f"Only {ops_per_sec:.0f} ops/sec"
