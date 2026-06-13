"""
Consolidation Engine (L2 -> L3).

This engine is responsible for consolidating facts from Working Memory (L2)
into episodes stored in Episodic Memory (L3).

Recovery Triggers (No Cron):
1. Wake-Up Sweep: On startup, process all unconsolidated facts
2. Pressure Valve: Auto-trigger when unconsolidated count >= threshold
3. Session End Signal: Force consolidation on session_status="concluded" event

References:
- docs/research/consolidation-hooks-and-signals.md
- docs/research/redis-global-local-stream.md
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, cast
from uuid import uuid4

from src.llm.client import LLMClient
from src.llm.providers.base import BaseProvider
from src.memory.engines.base_engine import BaseEngine
from src.memory.lifecycle_stream import LifecycleStreamConsumer
from src.memory.models import Episode, EpisodeStoreInput, Fact
from src.memory.tiers.episodic_memory_tier import EpisodicMemoryTier
from src.memory.tiers.working_memory_tier import WorkingMemoryTier

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    async def get_embedding(
        self, text: str, model: str | None = None, output_dimensionality: int | None = None
    ) -> list[float]: ...


class ConsolidationEngine(BaseEngine):
    """
    Consolidates facts from L2 into episodes in L3.

    Flow:
    1. Retrieve facts from WorkingMemoryTier (L2) since last consolidation.
    2. Cluster facts by time windows (default: 24 hours).
    3. Generate episode summary and narrative using LLM.
    4. Generate embedding for episode content.
    5. Store episode in EpisodicMemoryTier (L3) with dual indexing.
    """

    DEFAULT_TIME_WINDOW_HOURS = 24
    DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"
    DEFAULT_SUMMARY_MODEL = "gemini-2.5-flash"
    DEFAULT_PRESSURE_VALVE_THRESHOLD = 50  # Trigger batch consolidation at 50 facts
    DEFAULT_BATCH_SIZE = 100  # Max facts to process in one sweep

    def __init__(
        self,
        l2_tier: WorkingMemoryTier,
        l3_tier: EpisodicMemoryTier,
        llm_provider: LLMClient | None = None,
        stream_consumer: LifecycleStreamConsumer | None = None,
        config: dict[str, Any] | None = None,
        gemini_provider: BaseProvider | None = None,
        telemetry_stream: Any | None = None,
    ):
        super().__init__()
        self.l2 = l2_tier
        self.l3 = l3_tier
        if llm_provider is not None:
            self.llm: LLMClient = llm_provider
        elif gemini_provider is not None:
            if not getattr(gemini_provider, "name", None):
                gemini_provider.name = "gemini"
            self.llm = LLMClient()
            self.llm.register_provider(gemini_provider)
        else:
            self.llm = LLMClient.from_env()
        self.stream_consumer = stream_consumer
        self.config = config or {}
        self.time_window_hours = self.config.get(
            "time_window_hours", self.DEFAULT_TIME_WINDOW_HOURS
        )
        self.embedding_model = self.config.get("embedding_model", self.DEFAULT_EMBEDDING_MODEL)
        self.summary_model = self.config.get("summary_model", self.DEFAULT_SUMMARY_MODEL)
        self.pressure_valve_threshold = self.config.get(
            "pressure_valve_threshold", self.DEFAULT_PRESSURE_VALVE_THRESHOLD
        )
        self.batch_size = self.config.get("batch_size", self.DEFAULT_BATCH_SIZE)
        self._running = False
        self._buffer: list[Fact] = []
        self._stream_task: asyncio.Task[None] | None = None
        self.telemetry_stream = telemetry_stream

    async def start(self) -> None:
        """
        Start the consolidation engine with recovery triggers.

        Triggers:
        1. Wake-Up Sweep: Process all unconsolidated facts on startup
        2. Stream Listener: Process lifecycle events in real-time
        3. Pressure Valve: Auto-trigger when buffer exceeds threshold

        This method should be called during system initialization.
        """
        self._running = True
        logger.info("ConsolidationEngine starting with recovery triggers...")

        # TRIGGER 1: Wake-Up Sweep
        logger.info("Executing Wake-Up Sweep for missed consolidations...")
        await self.run_recovery_sweep()

        # TRIGGER 2: Start stream listener (if configured)
        if self.stream_consumer:
            # Register handlers for lifecycle events
            self.stream_consumer.register_handler("promotion", self._handle_promotion_event)
            self.stream_consumer.register_handler("session_end", self._handle_session_end_event)

            # Start consuming in background
            self._stream_task = asyncio.create_task(self.stream_consumer.start())
            logger.info("Lifecycle stream listener started")

        logger.info("ConsolidationEngine started successfully")

    async def stop(self) -> None:
        """Stop the consolidation engine and stream listener."""
        self._running = False
        if self.stream_consumer:
            await self.stream_consumer.stop()
        logger.info("ConsolidationEngine stopped")

    async def run_recovery_sweep(self) -> dict[str, Any]:
        """
        Wake-Up Sweep: Scan L2 for unconsolidated facts and process them.

        This runs on every system boot to catch facts missed while the
        system was offline. Provides eventual consistency for facts that
        couldn't be consolidated in real-time.

        Returns:
            Stats: sessions_processed, facts_consolidated, episodes_created
        """
        stats: dict[str, int | str] = {
            "sessions_processed": 0,
            "facts_consolidated": 0,
            "episodes_created": 0,
            "errors": 0,
        }

        def inc(key: str, amount: int = 1) -> None:
            """Increment a stats counter."""
            current = stats.get(key, 0)
            if isinstance(current, str):
                current = 0
            stats[key] = int(current) + amount

        try:
            # Query L2 for all unconsolidated facts
            # (Requires L2 tier to track consolidation status)
            unconsolidated = await self._get_unconsolidated_facts()

            if not unconsolidated:
                logger.info("Wake-Up Sweep: No unconsolidated facts found")
                return stats

            logger.info(f"Wake-Up Sweep: Found {len(unconsolidated)} unconsolidated facts")

            # Group facts by session
            sessions: dict[str, list[Fact]] = {}
            for fact in unconsolidated:
                session_id = fact.session_id
                if session_id not in sessions:
                    sessions[session_id] = []
                sessions[session_id].append(fact)

            # Process each session
            for session_id, facts in sessions.items():
                try:
                    result = await self._consolidate_facts(session_id, facts)
                    inc("sessions_processed")
                    inc("facts_consolidated", len(facts))
                    inc("episodes_created", int(result.get("episodes_created", 0)))
                except Exception as e:
                    logger.error(f"Wake-Up Sweep error for session {session_id}: {e}")
                    inc("errors")

            logger.info(f"Wake-Up Sweep completed: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Wake-Up Sweep failed: {e}")
            inc("errors")
            return stats

    async def _handle_promotion_event(self, event: dict[str, Any]) -> None:
        """
        Handle promotion events from lifecycle stream.

        Adds promoted facts to buffer and checks pressure valve threshold.
        """
        session_id = event.get("session_id")
        import json

        data = json.loads(event.get("data", "{}"))
        fact_count = data.get("fact_count", 0)

        logger.debug(f"Promotion event: {fact_count} facts for session {session_id}")

        # Check pressure valve (if buffer grows too large)
        current_count = await self._get_unconsolidated_count()

        # TRIGGER 3: Pressure Valve
        if current_count >= self.pressure_valve_threshold:
            logger.warning(
                f"Pressure Valve triggered: {current_count} unconsolidated facts "
                f"(threshold: {self.pressure_valve_threshold})"
            )
            await self._trigger_batch_consolidation()

    async def _handle_session_end_event(self, event: dict[str, Any]) -> None:
        """
        Handle session_end events from lifecycle stream.

        Forces immediate consolidation for the session regardless of buffer size.
        """
        session_id = event.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            logger.warning("Session end event missing session_id: %s", event)
            return
        logger.info(f"Session end event: Forcing consolidation for {session_id}")

        # Force consolidation for this session
        try:
            stats = await self.process_session(session_id)
            logger.info(f"Session end consolidation completed: {stats}")
        except Exception as e:
            logger.error(f"Session end consolidation failed for {session_id}: {e}")

    async def _trigger_batch_consolidation(self) -> None:
        """
        Pressure Valve: Process a batch of unconsolidated facts immediately.
        """
        try:
            await self.run_recovery_sweep()
        except Exception as e:
            logger.error(f"Batch consolidation failed: {e}")

    async def _get_unconsolidated_facts(self) -> list[Fact]:
        """
        Query L2 for all facts where consolidated=False.

        Returns up to batch_size facts, ordered by extraction time.
        """
        # This requires WorkingMemoryTier to track consolidation status
        # For now, return empty list (will be implemented in WorkingMemoryTier)
        # TODO: Add query_unconsolidated() method to WorkingMemoryTier
        logger.warning("_get_unconsolidated_facts not yet implemented in L2 tier")
        return []

    async def _get_unconsolidated_count(self) -> int:
        """
        Get count of unconsolidated facts in L2.

        Used for pressure valve threshold check.
        """
        # This requires WorkingMemoryTier to track consolidation status
        # For now, return 0 (will be implemented in WorkingMemoryTier)
        # TODO: Add count_unconsolidated() method to WorkingMemoryTier
        return 0

    async def _consolidate_facts(self, session_id: str, facts: list[Fact]) -> dict[str, Any]:
        """
        Consolidate a list of facts into episodes.

        Args:
            session_id: Session ID
            facts: List of facts to consolidate

        Returns:
            Stats: episodes_created, errors
        """
        stats: dict[str, int] = {"episodes_created": 0, "errors": 0}

        # Cluster facts by time windows
        clusters = self._cluster_facts_by_time(facts)

        # Create episodes from clusters
        for cluster in clusters:
            try:
                episode = await self._create_episode_from_facts(session_id, cluster)
                embedding = await self._generate_embedding(episode)

                payload = EpisodeStoreInput(
                    episode=episode,
                    embedding=embedding,
                    entities=[],
                    relationships=[],
                )
                await self.l3.store(payload)

                stats["episodes_created"] = stats.get("episodes_created", 0) + 1

            except Exception as e:
                logger.error(f"Error consolidating fact cluster: {e}")
                stats["errors"] = stats.get("errors", 0) + 1

        return stats

    async def process(self, session_id: str | None = None) -> dict[str, Any]:
        """
        Execute consolidation cycle for a session.

        Args:
            session_id: The session to process.

        Returns:
            Dict with stats (facts_processed, episodes_created, errors).
        """
        if not session_id:
            return {"status": "skipped", "reason": "no_session_id"}

        return await self.process_session(session_id)

    async def process_session(self, session_id: str) -> dict[str, Any]:
        """
        Process a specific session for fact consolidation.
        """
        stats: dict[str, int | str] = {
            "session_id": session_id,
            "facts_retrieved": 0,
            "episodes_created": 0,
            "errors": 0,
        }

        def inc(key: str, amount: int = 1) -> None:
            """Increment a stats counter."""
            current = stats.get(key, 0)
            if isinstance(current, str):
                current = 0
            stats[key] = int(current) + amount

        try:
            # Ensure downstream tier is initialized so collections/constraints exist
            await self.l3.initialize()

            # 1. Determine time range (from last episode or beginning)
            start_time = await self._get_last_consolidation_time(session_id)
            end_time = datetime.now(UTC)

            # Emit consolidation_started event
            if self.telemetry_stream:
                await self.telemetry_stream.publish(
                    event_type="consolidation_started",
                    session_id=session_id,
                    data={
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                    },
                )

            # 2. Retrieve facts from L2 in time range
            facts = await self._get_facts_in_range(session_id, start_time, end_time)
            stats["facts_retrieved"] = len(facts)

            if not facts:
                return stats

            # 3. Cluster facts by time windows
            clusters = self._cluster_facts_by_time(facts)

            # Emit facts_clustered event
            if self.telemetry_stream:
                await self.telemetry_stream.publish(
                    event_type="facts_clustered",
                    session_id=session_id,
                    data={
                        "total_facts": len(facts),
                        "cluster_count": len(clusters),
                        "time_window_hours": self.time_window_hours,
                    },
                )

            # 4. Create episodes from clusters
            for cluster in clusters:
                try:
                    episode = await self._create_episode_from_facts(session_id, cluster)

                    # 5. Generate embedding
                    embedding = await self._generate_embedding(episode)

                    # 6. Store in L3
                    payload = EpisodeStoreInput(
                        episode=episode,
                        embedding=embedding,
                        entities=[],  # Could extract from facts
                        relationships=[],  # Could extract from facts
                    )
                    await self.l3.store(payload)

                    # Emit episode_created event
                    if self.telemetry_stream:
                        await self.telemetry_stream.publish(
                            event_type="episode_created",
                            session_id=session_id,
                            data={
                                "episode_id": episode.episode_id,
                                "fact_count": len(cluster),
                                "summary": episode.summary[:100],
                                "importance_score": episode.importance_score,
                            },
                        )

                    inc("episodes_created")

                except Exception as e:
                    logger.error(f"Error creating episode: {e}")
                    inc("errors")

            # Emit consolidation_completed event
            if self.telemetry_stream:
                await self.telemetry_stream.publish(
                    event_type="consolidation_completed",
                    session_id=session_id,
                    data={
                        "facts_retrieved": stats["facts_retrieved"],
                        "episodes_created": stats["episodes_created"],
                        "errors": stats["errors"],
                    },
                )

            return stats

        except Exception as e:
            logger.error(f"Error consolidating facts for session {session_id}: {e}")
            inc("errors")
            stats["last_error"] = str(e)
            return stats

    async def _get_last_consolidation_time(self, session_id: str) -> datetime:
        """Get the time of the last consolidated episode for this session."""
        # Query L3 for most recent episode
        # For now, return 24 hours ago as default
        return datetime.now(UTC) - timedelta(hours=self.time_window_hours)

    async def _get_facts_in_range(
        self, session_id: str, start_time: datetime, end_time: datetime
    ) -> list[Fact]:
        """Retrieve facts from L2 within time range."""
        facts: list[Fact] = []

        if hasattr(self.l2, "query_by_session"):
            try:
                facts = await self.l2.query_by_session(
                    session_id=session_id, min_ciar_score=0, limit=500
                )
            except Exception:
                facts = []

        if hasattr(self.l2, "query"):
            try:
                additional = await self.l2.query(
                    filters={"session_id": session_id}, limit=500, include_low_ciar=True
                )
                if additional and len(additional) > len(facts):
                    facts = list(additional)
            except Exception:
                # If query fails, keep any facts gathered from query_by_session
                pass

        logger.info("Consolidation L2 fetch: session=%s count=%d", session_id, len(facts))

        if not facts and hasattr(self.l2, "get_recent_cached"):
            cached = self.l2.get_recent_cached(session_id)
            if cached:
                facts = list(cached)
                logger.info(
                    "Consolidation fallback to cache: session=%s cached_count=%d",
                    session_id,
                    len(facts),
                )

        filtered: list[Fact] = []
        for fact_dict in facts:
            fact_data = fact_dict.model_dump() if isinstance(fact_dict, Fact) else dict(fact_dict)

            extracted_at = fact_data.get("extracted_at") or fact_data.get("created_at")
            if isinstance(extracted_at, str):
                extracted_at = datetime.fromisoformat(extracted_at)
            if extracted_at is not None and extracted_at.tzinfo is None:
                # Normalize naive timestamps to UTC for comparison
                extracted_at = extracted_at.replace(tzinfo=UTC)
            if extracted_at is None:
                extracted_at = datetime.now(UTC)
            fact_data["extracted_at"] = extracted_at

            fact = Fact(**fact_data)
            filtered.append(fact)

        return filtered

    def _cluster_facts_by_time(self, facts: list[Fact]) -> list[list[Fact]]:
        """Cluster facts into time windows."""
        if not facts:
            return []

        # Sort by extraction time
        sorted_facts = sorted(facts, key=lambda f: f.extracted_at)

        clusters = []
        current_cluster = [sorted_facts[0]]
        window_start = sorted_facts[0].extracted_at

        for fact in sorted_facts[1:]:
            # Check if fact is within time window
            if (fact.extracted_at - window_start).total_seconds() / 3600 <= self.time_window_hours:
                current_cluster.append(fact)
            else:
                # Start new cluster
                clusters.append(current_cluster)
                current_cluster = [fact]
                window_start = fact.extracted_at

        # Add last cluster
        if current_cluster:
            clusters.append(current_cluster)

        return clusters

    async def _create_episode_from_facts(self, session_id: str, facts: list[Fact]) -> Episode:
        """Create an episode from a cluster of facts using LLM."""
        # Generate summary and narrative
        facts_text = "\n".join(
            [f"- {f.content} (certainty: {f.certainty}, impact: {f.impact})" for f in facts]
        )

        prompt = f"""Given the following facts from a conversation, create a brief summary and narrative:

Facts:
{facts_text}

Provide:
1. A one-sentence summary
2. A brief narrative (2-3 sentences) describing what happened

Format as JSON:
{{
    "summary": "...",
    "narrative": "..."
}}
"""

        response = await self.llm.generate(
            prompt=prompt, model=self.summary_model, temperature=0.3, max_output_tokens=512
        )

        # Parse response
        import json

        try:
            # Clean markdown if present
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]

            data = json.loads(text.strip())
            summary = data.get("summary", "Episode summary")
            narrative = data.get("narrative", "Episode narrative")
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            summary = f"Episode with {len(facts)} facts"
            narrative = "Consolidation of facts from conversation."

        # Create Episode object
        time_window_start = min(f.extracted_at for f in facts)
        time_window_end = max(f.extracted_at for f in facts)
        duration = (time_window_end - time_window_start).total_seconds()

        episode = Episode(
            episode_id=str(uuid4()),
            session_id=session_id,
            summary=summary,
            narrative=narrative,
            source_fact_ids=[f.fact_id for f in facts],
            fact_count=len(facts),
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            duration_seconds=duration,
            fact_valid_from=time_window_start,
            fact_valid_to=None,
            source_observation_timestamp=datetime.now(UTC),
            embedding_model=self.embedding_model,
            topics=[],
            importance_score=sum(f.ciar_score for f in facts) / len(facts),
        )

        return episode

    async def _generate_embedding(self, episode: Episode) -> list[float]:
        """Generate embedding for episode content."""
        # Combine summary and narrative for embedding
        text = f"{episode.summary}. {episode.narrative or ''}"

        provider = self._get_embedding_provider()
        if not provider:
            raise RuntimeError("No embedding-capable provider registered for consolidation")

        try:
            embedding = await provider.get_embedding(text=text, model=self.embedding_model)
            return [float(value) for value in embedding]
        except Exception as e:
            logger.error("Embedding generation failed during consolidation: %s", e)
            raise

    async def health_check(self) -> dict[str, Any]:
        """Check health of dependencies."""
        l2_health = await self.l2.health_check()
        l3_health = await self.l3.health_check()
        llm_health = await self.llm.health_check()

        healthy = (
            l2_health.get("status") == "healthy"
            and l3_health.get("status") == "healthy"
            and all(h.healthy for h in llm_health.values())
        )
        provider_health = {k: v for k, v in llm_health.items()}

        return {
            "status": "healthy" if healthy else "unhealthy",
            "l2": l2_health,
            "l3": l3_health,
            "llm_providers": {k: v.__dict__ for k, v in llm_health.items()},
            **provider_health,
        }

    def _get_embedding_provider(self) -> EmbeddingProvider | None:
        """Select a provider that supports embeddings from the registered LLM client."""
        for provider in self.llm._providers.values():
            if hasattr(provider, "get_embedding"):
                return cast(EmbeddingProvider, provider)
        return None
