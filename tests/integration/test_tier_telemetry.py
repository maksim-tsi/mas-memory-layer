"""
Integration Tests for Tier-Level Telemetry (Glass Box Observability).

Verifies that all memory tiers (L1-L4) emit 'tier_access' events with correct
structure and metadata during standard operations.
"""

import asyncio
import contextlib
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import pytest

from src.memory.lifecycle_stream import LifecycleStreamConsumer
from src.memory.models import (
    Episode,
    EpisodeStoreInput,
    Fact,
    FactCategory,
    FactType,
    KnowledgeDocument,
    TurnData,
)
from src.memory.system import UnifiedMemorySystem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration


class TestTierTelemetry:
    """Verify 'tier_access' telemetry events from all tiers."""

    @pytest.fixture
    async def unified_system(
        self,
        redis_adapter,
        postgres_adapter,
        neo4j_adapter,
        qdrant_adapter,
        typesense_adapter,
        real_llm_client,
    ) -> AsyncGenerator[UnifiedMemorySystem, None]:
        """Create a fully wired UnifiedMemorySystem with telemetry enabled."""
        llm, _ = real_llm_client

        system = UnifiedMemorySystem(
            redis_client=redis_adapter,
            postgres_adapter=postgres_adapter,
            neo4j_adapter=neo4j_adapter,
            qdrant_adapter=qdrant_adapter,
            typesense_adapter=typesense_adapter,
            llm_client=llm,
            enable_telemetry=True,
        )
        yield system

    @pytest.mark.asyncio
    async def test_tier_telemetry_flow(
        self,
        test_session_id: str,
        unified_system: UnifiedMemorySystem,
        redis_adapter: Any,
    ):
        """
        Verify that all tiers emit 'tier_access' events.
        """
        # 1. Setup Telemetry Consumer
        received_events: list[dict[str, Any]] = []

        # LifecycleStreamConsumer needs raw redis.Redis
        raw_redis = getattr(redis_adapter, "client", redis_adapter)
        consumer = LifecycleStreamConsumer(
            raw_redis, consumer_group="test-tier-telemetry-group", consumer_name="test-worker"
        )

        async def event_handler(event: dict[str, Any]):
            if isinstance(event.get("data"), str):
                with contextlib.suppress(Exception):
                    event["data"] = json.loads(event["data"])

            if event.get("type") == "tier_access":
                received_events.append(event)

        consumer.register_handler("tier_access", event_handler)
        await consumer.initialize()
        consumer_task = asyncio.create_task(consumer.start())

        try:
            # --- L1 Active Context ---
            logger.info("Testing L1 Telemetry...")
            turn = TurnData(
                session_id=test_session_id,
                turn_id="1",
                role="user",
                content="L1 telemetry test",
                timestamp=datetime.utcnow(),
            )
            await unified_system.l1_tier.store(turn)
            await unified_system.l1_tier.retrieve_session(test_session_id)

            # --- L2 Working Memory ---
            logger.info("Testing L2 Telemetry...")
            fact = Fact(
                fact_id=str(uuid.uuid4()),
                session_id=test_session_id,
                content="L2 telemetry test fact",
                fact_type=FactType.PREFERENCE,
                fact_category=FactCategory.PERSONAL,
                extracted_at=datetime.utcnow(),
                certainty=1.0,
                impact=0.8,
                ciar_score=0.8,
            )
            await unified_system.l2_tier.store(fact)
            await unified_system.l2_tier.retrieve(fact.fact_id)

            # --- L3 Episodic Memory ---
            logger.info("Testing L3 Telemetry...")
            episode_id = str(uuid.uuid4())
            episode = Episode(
                episode_id=episode_id,
                session_id=test_session_id,
                summary="L3 telemetry test episode",
                time_window_start=datetime.utcnow(),
                time_window_end=datetime.utcnow(),
                fact_valid_from=datetime.utcnow(),
                source_observation_timestamp=datetime.utcnow(),
                importance_score=0.9,
            )
            episode_input = EpisodeStoreInput(
                episode=episode, embedding=[0.1] * 768, entities=[], relationships=[]
            )
            await unified_system.l3_tier.store(episode_input)
            await unified_system.l3_tier.retrieve(episode_id)

            # --- L4 Semantic Memory ---
            logger.info("Testing L4 Telemetry...")
            knowledge_id = str(uuid.uuid4())
            knowledge = KnowledgeDocument(
                knowledge_id=knowledge_id,
                title="L4 Telemetry Test",
                content="Testing L4 telemetry emission.",
                knowledge_type="pattern",
                confidence_score=0.95,
                episode_count=1,
                distilled_at=datetime.utcnow(),
                access_count=0,
                usefulness_score=0.0,
                validation_count=0,
            )
            await unified_system.l4_tier.store(knowledge)
            await unified_system.l4_tier.retrieve(knowledge_id)

            # Wait for events
            await asyncio.sleep(2)

            # NOTE: L1 emits 4 events: STORE(Redis), STORE(Postgres), RETRIEVE(Redis), RETRIEVE(Postgres - if miss in redis, but here it's hit)
            # Actually store() stores in both. retrieve_session() tries redis first.

            l1_events = [e for e in received_events if e["data"].get("tier") == "L1_Active"]
            l2_events = [e for e in received_events if e["data"].get("tier") == "L2_Working"]
            l3_events = [e for e in received_events if e["data"].get("tier") == "L3_Episodic"]
            l4_events = [e for e in received_events if e["data"].get("tier") == "L4_Semantic"]

            logger.info(f"Received events: {len(received_events)}")
            logger.info(
                f"L1: {len(l1_events)}, L2: {len(l2_events)}, L3: {len(l3_events)}, L4: {len(l4_events)}"
            )

            assert len(l1_events) >= 2, f"L1 expected >=2 events, got {len(l1_events)}"
            assert len(l2_events) >= 2, f"L2 expected >=2 events, got {len(l2_events)}"
            assert len(l3_events) >= 2, f"L3 expected >=2 events, got {len(l3_events)}"
            assert len(l4_events) >= 2, f"L4 expected >=2 events, got {len(l4_events)}"

            # Verify L1 structure
            l1_store = next(e for e in l1_events if e["data"]["operation"] == "STORE")
            assert l1_store["data"]["status"] == "HIT"
            assert "latency_ms" in l1_store["data"]
            assert "turn_id" in l1_store["data"]["metadata"]

            # Verify L2 structure
            l2_store = next(e for e in l2_events if e["data"]["operation"] == "STORE")
            assert l2_store["data"]["status"] == "HIT"
            assert l2_store["session_id"] == test_session_id
            assert "fact_type" in l2_store["data"]["metadata"]

            # Verify L3 structure
            l3_store = next(e for e in l3_events if e["data"]["operation"] == "STORE")
            assert l3_store["data"]["metadata"]["modality"] == "dual"
            assert l3_store["data"]["item_count"] == 1

            # Verify L4 structure
            l4_retrieve = next(e for e in l4_events if e["data"]["operation"] == "RETRIEVE")
            assert l4_retrieve["data"]["status"] == "HIT"
            assert l4_retrieve["data"]["metadata"]["knowledge_id"] == knowledge_id

        finally:
            consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await consumer_task
