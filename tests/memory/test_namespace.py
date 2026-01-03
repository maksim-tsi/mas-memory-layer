"""
Tests for Redis namespace management with Hash Tags.

Covers:
- Key generation and Hash Tag consistency
- Lifecycle event publishing
- MAXLEN trimming behavior (approximate)
- Fire-and-forget resilience
- Cluster slot safety (no external crc16 dependency)
- Optional performance benchmarks (skipped if pytest-benchmark missing)
"""

import json
import os
import uuid

import pytest
import pytest_asyncio
import redis.asyncio as redis

from src.memory.namespace import NamespaceManager

try:
    import pytest_benchmark  # noqa: F401
    BENCHMARK_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    BENCHMARK_AVAILABLE = False


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
    """Create Redis client for testing (skips if REDIS_URL missing/unavailable)."""
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

    if keys_to_clean:
        await redis_client.delete(*keys_to_clean)


class TestKeyGeneration:
    """Test key generation methods."""

    def test_l1_turns_key_format(self, session_id):
        key = NamespaceManager.l1_turns(session_id)
        assert key == f"{{session:{session_id}}}:turns"
        assert "{" in key and "}" in key

    def test_personal_state_key_format(self, session_id, agent_id):
        key = NamespaceManager.personal_state(agent_id, session_id)
        assert key == f"{{session:{session_id}}}:agent:{agent_id}:state"
        assert f"{{session:{session_id}}}" in key

    def test_shared_workspace_key_format(self, session_id):
        key = NamespaceManager.shared_workspace(session_id)
        assert key == f"{{session:{session_id}}}:workspace"
        assert f"{{session:{session_id}}}" in key

    def test_l2_facts_index_key_format(self, session_id):
        key = NamespaceManager.l2_facts_index(session_id)
        assert key == f"{{session:{session_id}}}:facts:index"
        assert f"{{session:{session_id}}}" in key

    def test_lifecycle_stream_key_format(self):
        key = NamespaceManager.lifecycle_stream()
        assert key == "{mas}:lifecycle"
        assert "{mas}" in key

    def test_hash_tag_extraction(self, session_id):
        key = NamespaceManager.l1_turns(session_id)
        start = key.index("{")
        end = key.index("}", start)
        hash_tag = key[start + 1 : end]
        assert hash_tag == f"session:{session_id}"

    def test_consistent_hash_tag_across_session_keys(self, session_id, agent_id):
        l1_key = NamespaceManager.l1_turns(session_id)
        personal_key = NamespaceManager.personal_state(agent_id, session_id)
        workspace_key = NamespaceManager.shared_workspace(session_id)
        facts_key = NamespaceManager.l2_facts_index(session_id)

        def extract_hash_tag(key: str) -> str:
            start = key.index("{")
            end = key.index("}", start)
            return key[start + 1 : end]

        tags = [extract_hash_tag(k) for k in [l1_key, personal_key, workspace_key, facts_key]]
        assert len(set(tags)) == 1
        assert tags[0] == f"session:{session_id}"


class TestLifecycleEventPublishing:
    """Test lifecycle event publishing to global stream."""

    @pytest.mark.asyncio
    async def test_publish_lifecycle_event(self, namespace_manager, session_id, cleanup_keys):
        stream_key = NamespaceManager.lifecycle_stream()
        cleanup_keys(stream_key)

        event_id = await namespace_manager.publish_lifecycle_event(
            event_type="promotion",
            session_id=session_id,
            data={"fact_count": 5, "ciar_threshold": 0.6}
        )

        assert event_id and isinstance(event_id, str)

    @pytest.mark.asyncio
    async def test_event_contains_metadata(self, namespace_manager, redis_client, session_id, cleanup_keys):
        stream_key = NamespaceManager.lifecycle_stream()
        cleanup_keys(stream_key)

        event_id = await namespace_manager.publish_lifecycle_event(
            event_type="consolidation",
            session_id=session_id,
            data={"episodes_created": 3}
        )

        events = await redis_client.xrange(stream_key, min=event_id, max=event_id)
        assert len(events) == 1
        _, fields = events[0]

        assert fields["type"] == "consolidation"
        assert fields["session_id"] == session_id
        assert "timestamp" in fields

        data = json.loads(fields["data"])
        assert data["episodes_created"] == 3

    @pytest.mark.asyncio
    async def test_maxlen_trimming(self, namespace_manager, redis_client, cleanup_keys):
        stream_key = NamespaceManager.lifecycle_stream()
        cleanup_keys(stream_key)

        max_length = 10
        for i in range(20):
            await namespace_manager.publish_lifecycle_event(
                event_type="test",
                session_id=f"session-{i}",
                data={"index": i},
                max_length=max_length
            )

        stream_info = await redis_client.xinfo_stream(stream_key)
        stream_length = stream_info["length"]

        assert stream_length >= max_length
        assert stream_length <= max_length * 3

    @pytest.mark.asyncio
    async def test_fire_and_forget_resilience(self, session_id):
        bad_client = redis.from_url("redis://invalid:6379", decode_responses=True)
        bad_manager = NamespaceManager(bad_client)

        event_id = await bad_manager.publish_lifecycle_event(
            event_type="test",
            session_id=session_id,
            data={"test": "data"}
        )

        assert event_id == ""
        await bad_client.aclose()


class TestHashTagClusterSafety:
    """Test Hash Tag properties for Redis Cluster safety."""

    def test_same_session_keys_have_same_slot(self, session_id, agent_id):
        keys = [
            NamespaceManager.l1_turns(session_id),
            NamespaceManager.personal_state(agent_id, session_id),
            NamespaceManager.shared_workspace(session_id),
            NamespaceManager.l2_facts_index(session_id),
        ]

        def calculate_slot(key: str) -> int:
            start = key.index("{")
            end = key.index("}", start)
            hash_tag = key[start + 1 : end]
            return NamespaceManager.compute_slot(hash_tag)

        slots = [calculate_slot(key) for key in keys]
        assert len(set(slots)) == 1, "All session keys must hash to same slot"

    def test_different_sessions_different_slots(self):
        session1 = str(uuid.uuid4())
        session2 = str(uuid.uuid4())

        key1 = NamespaceManager.l1_turns(session1)
        key2 = NamespaceManager.l1_turns(session2)

        def extract_hash_tag(key: str) -> str:
            start = key.index("{")
            end = key.index("}", start)
            return key[start + 1 : end]

        tag1 = extract_hash_tag(key1)
        tag2 = extract_hash_tag(key2)
        assert tag1 != tag2

    def test_global_stream_has_consistent_slot(self):
        key1 = NamespaceManager.lifecycle_stream()
        key2 = NamespaceManager.lifecycle_stream()
        assert key1 == key2 == "{mas}:lifecycle"


class TestNamespacePerformance:
    """Benchmark namespace operations (skipped if pytest-benchmark missing)."""

    if BENCHMARK_AVAILABLE:
        pytestmark = pytest.mark.benchmark
    else:
        pytestmark = pytest.mark.skip(reason="pytest-benchmark not installed")

    def test_key_generation_performance(self, benchmark):
        session_id = str(uuid.uuid4())

        def generate_keys():
            NamespaceManager.l1_turns(session_id)
            NamespaceManager.shared_workspace(session_id)
            NamespaceManager.l2_facts_index(session_id)

        result = benchmark(generate_keys)
        assert result is None

    @pytest.mark.asyncio
    async def test_event_publishing_throughput(self, namespace_manager, cleanup_keys):
        stream_key = NamespaceManager.lifecycle_stream()
        cleanup_keys(stream_key)

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
        assert ops_per_sec > 100, f"Only {ops_per_sec:.0f} ops/sec"
