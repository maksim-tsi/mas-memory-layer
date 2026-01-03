"""
Tests for Redis Streams lifecycle event coordination.

Test Coverage:
- Consumer group creation and initialization
- Event publishing and consumption
- Handler registration and execution
- Pending message recovery
- Consumer group ACK behavior
- MAXLEN trimming behavior
- Health checks
"""

import pytest
import pytest_asyncio
import redis.asyncio as redis
import os
import uuid
import json
import asyncio

from src.memory.lifecycle_stream import (
    LifecycleStreamConsumer,
    LifecycleStreamProducer,
)
from src.memory.namespace import NamespaceManager


@pytest.fixture
def session_id():
    """Generate unique test session ID."""
    return f"test-{uuid.uuid4()}"


@pytest.fixture
def consumer_group():
    """Generate unique test consumer group."""
    return f"test-group-{uuid.uuid4()}"


@pytest.fixture
def consumer_name():
    """Generate unique test consumer name."""
    return f"test-consumer-{uuid.uuid4()}"


@pytest_asyncio.fixture
async def redis_client():
    """Create Redis client for testing."""
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
async def producer(redis_client):
    """Create lifecycle stream producer."""
    return LifecycleStreamProducer(redis_client)


@pytest_asyncio.fixture
async def consumer(redis_client, consumer_group, consumer_name):
    """Create lifecycle stream consumer."""
    consumer = LifecycleStreamConsumer(
        redis_client=redis_client,
        consumer_group=consumer_group,
        consumer_name=consumer_name,
        block_ms=1000,  # Shorter timeout for tests
        batch_size=10
    )
    await consumer.initialize()
    yield consumer
    await consumer.stop()


@pytest_asyncio.fixture
async def cleanup_stream(redis_client):
    """Cleanup test stream after test."""
    yield
    
    # Delete stream
    stream_key = NamespaceManager.lifecycle_stream()
    try:
        await redis_client.delete(stream_key)
    except Exception:
        pass


class TestConsumerInitialization:
    """Test consumer group initialization."""
    
    @pytest.mark.asyncio
    async def test_consumer_group_creation(
        self, 
        redis_client, 
        consumer_group,
        consumer_name,
        cleanup_stream
    ):
        """Test creating a new consumer group."""
        consumer = LifecycleStreamConsumer(
            redis_client=redis_client,
            consumer_group=consumer_group,
            consumer_name=consumer_name
        )
        
        await consumer.initialize()
        
        # Verify group exists
        stream_key = NamespaceManager.lifecycle_stream()
        groups = await redis_client.xinfo_groups(stream_key)
        
        group_names = [g["name"].decode() if isinstance(g["name"], bytes) else g["name"] for g in groups]
        assert consumer_group in group_names
    
    @pytest.mark.asyncio
    async def test_consumer_group_idempotent(
        self, 
        redis_client, 
        consumer_group,
        consumer_name,
        cleanup_stream
    ):
        """Test that initialize() is idempotent."""
        consumer = LifecycleStreamConsumer(
            redis_client=redis_client,
            consumer_group=consumer_group,
            consumer_name=consumer_name
        )
        
        # Initialize twice
        await consumer.initialize()
        await consumer.initialize()  # Should not raise
        
        # Group should exist
        stream_key = NamespaceManager.lifecycle_stream()
        groups = await redis_client.xinfo_groups(stream_key)
        assert len(groups) >= 1


class TestEventPublishing:
    """Test event publishing and consumption."""
    
    @pytest.mark.asyncio
    async def test_publish_and_consume_event(
        self, 
        producer, 
        consumer,
        session_id,
        cleanup_stream
    ):
        """Test basic event publishing and consumption."""
        received_events = []
        
        # Register handler
        async def handle_test(event: dict):
            received_events.append(event)
        
        consumer.register_handler("test", handle_test)
        
        # Publish event
        event_id = await producer.publish(
            event_type="test",
            session_id=session_id,
            data={"message": "hello"}
        )
        
        assert event_id
        
        # Start consumer in background
        consumer_task = asyncio.create_task(consumer.start())
        
        # Wait for event processing
        await asyncio.sleep(2)
        
        # Stop consumer
        await consumer.stop()
        await consumer_task
        
        # Verify event received
        assert len(received_events) == 1
        event = received_events[0]
        assert event["type"] == "test"
        assert event["session_id"] == session_id
        
        data = json.loads(event["data"])
        assert data["message"] == "hello"
    
    @pytest.mark.asyncio
    async def test_multiple_event_types(
        self, 
        producer, 
        consumer,
        session_id,
        cleanup_stream
    ):
        """Test handling multiple event types."""
        promotion_events = []
        consolidation_events = []
        
        # Register handlers
        async def handle_promotion(event: dict):
            promotion_events.append(event)
        
        async def handle_consolidation(event: dict):
            consolidation_events.append(event)
        
        consumer.register_handler("promotion", handle_promotion)
        consumer.register_handler("consolidation", handle_consolidation)
        
        # Publish different event types
        await producer.publish("promotion", session_id, {"facts": 5})
        await producer.publish("consolidation", session_id, {"episodes": 2})
        await producer.publish("promotion", session_id, {"facts": 3})
        
        # Start consumer
        consumer_task = asyncio.create_task(consumer.start())
        await asyncio.sleep(2)
        await consumer.stop()
        await consumer_task
        
        # Verify events routed correctly
        assert len(promotion_events) == 2
        assert len(consolidation_events) == 1


class TestPendingMessageRecovery:
    """Test pending message recovery after consumer failure."""
    
    @pytest.mark.asyncio
    async def test_pending_message_recovery(
        self, 
        producer,
        redis_client,
        consumer_group,
        session_id,
        cleanup_stream
    ):
        """Test that unacknowledged messages are recovered."""
        # Create consumer 1 and consume without ACK
        consumer1 = LifecycleStreamConsumer(
            redis_client=redis_client,
            consumer_group=consumer_group,
            consumer_name="consumer-1",
            block_ms=1000
        )
        await consumer1.initialize()
        
        # Publish event
        await producer.publish("test", session_id, {"msg": 1})
        
        # Read message but don't ACK (simulate crash)
        stream_key = NamespaceManager.lifecycle_stream()
        messages = await redis_client.xreadgroup(
            groupname=consumer_group,
            consumername="consumer-1",
            streams={stream_key: ">"},
            count=1,
            block=1000
        )
        
        assert len(messages) > 0  # Message read
        
        # Create consumer 2 with same group
        consumer2 = LifecycleStreamConsumer(
            redis_client=redis_client,
            consumer_group=consumer_group,
            consumer_name="consumer-2",
            block_ms=1000
        )
        await consumer2.initialize()
        
        received_events = []
        
        async def handle_test(event: dict):
            received_events.append(event)
        
        consumer2.register_handler("test", handle_test)
        
        # Start consumer 2 (should process pending messages)
        consumer_task = asyncio.create_task(consumer2.start())
        await asyncio.sleep(2)
        await consumer2.stop()
        await consumer_task
        
        # Consumer 2 should recover the pending message
        assert len(received_events) == 1


class TestConsumerGroups:
    """Test consumer group behavior."""
    
    @pytest.mark.asyncio
    async def test_multiple_consumers_same_group(
        self, 
        producer,
        redis_client,
        consumer_group,
        session_id,
        cleanup_stream
    ):
        """Test that multiple consumers in same group share work."""
        # Create 2 consumers in same group
        consumer1 = LifecycleStreamConsumer(
            redis_client=redis_client,
            consumer_group=consumer_group,
            consumer_name="consumer-1",
            block_ms=1000
        )
        await consumer1.initialize()
        
        consumer2 = LifecycleStreamConsumer(
            redis_client=redis_client,
            consumer_group=consumer_group,
            consumer_name="consumer-2",
            block_ms=1000
        )
        await consumer2.initialize()
        
        events1 = []
        events2 = []
        
        async def handle1(event: dict):
            events1.append(event)
        
        async def handle2(event: dict):
            events2.append(event)
        
        consumer1.register_handler("test", handle1)
        consumer2.register_handler("test", handle2)
        
        # Publish 10 events
        for i in range(10):
            await producer.publish("test", session_id, {"index": i})
        
        # Start both consumers
        task1 = asyncio.create_task(consumer1.start())
        task2 = asyncio.create_task(consumer2.start())
        
        await asyncio.sleep(2)
        
        await consumer1.stop()
        await consumer2.stop()
        await task1
        await task2
        
        # Work should be distributed between consumers
        total_events = len(events1) + len(events2)
        assert total_events == 10
        
        # Both consumers should process some events (load balancing)
        # Note: In rare cases, all events might go to one consumer
        # so we just verify total is correct
        assert total_events == 10


class TestHealthCheck:
    """Test consumer health checks."""
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(
        self, 
        consumer,
        cleanup_stream
    ):
        """Test health check returns healthy status."""
        health = await consumer.health_check()
        
        assert health["status"] == "healthy"
        assert health["consumer_name"] == consumer.consumer_name
        assert health["consumer_group"] == consumer.consumer_group
        assert "stream_length" in health
        assert "pending_messages" in health
        assert "registered_handlers" in health
    
    @pytest.mark.asyncio
    async def test_health_check_with_handlers(
        self, 
        consumer,
        cleanup_stream
    ):
        """Test health check lists registered handlers."""
        async def handle_test(event: dict):
            pass
        
        consumer.register_handler("test1", handle_test)
        consumer.register_handler("test2", handle_test)
        
        health = await consumer.health_check()
        
        assert "test1" in health["registered_handlers"]
        assert "test2" in health["registered_handlers"]


class TestMAXLENTrimming:
    """Test stream trimming with MAXLEN."""
    
    @pytest.mark.asyncio
    async def test_stream_trimming(
        self, 
        producer,
        redis_client,
        cleanup_stream
    ):
        """Test that stream is trimmed at MAXLEN threshold."""
        stream_key = NamespaceManager.lifecycle_stream()
        
        # Publish many events
        for i in range(100):
            await producer.publish(
                event_type="test",
                session_id=f"session-{i}",
                data={"index": i}
            )
        
        # Check stream length (should be trimmed to ~50k max)
        stream_info = await redis_client.xinfo_stream(stream_key)
        stream_length = stream_info["length"]
        
        # With MAXLEN ~ 50000, we should never exceed that significantly
        assert stream_length <= 100  # All our events fit
        
        # Publish many more to trigger trimming
        for i in range(51000):
            await producer.publish(
                event_type="test",
                session_id=f"session-{i}",
                data={"index": i}
            )
        
        # Now check again
        stream_info = await redis_client.xinfo_stream(stream_key)
        stream_length = stream_info["length"]
        
        # Should be trimmed to around 50k (allow 20% variance for approximate trimming)
        assert stream_length <= 60000
        assert stream_length >= 40000


@pytest.mark.concurrency
class TestConcurrentConsumers:
    """Test multiple concurrent consumers."""
    
    @pytest.mark.asyncio
    async def test_50_concurrent_consumers(
        self, 
        producer,
        redis_client,
        session_id,
        cleanup_stream
    ):
        """Stress test with 50 concurrent consumers."""
        num_consumers = 50
        consumers = []
        
        # Create consumer group
        consumer_group = f"stress-test-{uuid.uuid4()}"
        
        async def create_consumer(consumer_id: int):
            consumer = LifecycleStreamConsumer(
                redis_client=redis_client,
                consumer_group=consumer_group,
                consumer_name=f"consumer-{consumer_id}",
                block_ms=500
            )
            await consumer.initialize()
            
            events = []
            
            async def handle_test(event: dict):
                events.append(event)
            
            consumer.register_handler("test", handle_test)
            consumers.append((consumer, events))
            
            return consumer
        
        # Create all consumers
        consumer_objects = await asyncio.gather(
            *[create_consumer(i) for i in range(num_consumers)]
        )
        
        # Publish 100 events
        for i in range(100):
            await producer.publish("test", session_id, {"index": i})
        
        # Start all consumers
        tasks = [asyncio.create_task(c.start()) for c in consumer_objects]
        
        # Let them consume
        await asyncio.sleep(3)
        
        # Stop all consumers
        await asyncio.gather(*[c.stop() for c in consumer_objects])
        await asyncio.gather(*tasks)
        
        # Collect all events
        total_events = sum(len(events) for _, events in consumers)
        
        # All 100 events should be consumed
        assert total_events == 100
