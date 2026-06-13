"""
Distillation Engine: L3 → L4 Knowledge Creation

Responsible for generating domain-specific knowledge documents from episodes
and storing them in Semantic Memory (L4).

Architecture:
- Trigger-based processing (episode count threshold)
- LLM-powered knowledge synthesis
- Rich metadata extraction
- Multiple knowledge types (summary, insight, pattern, recommendation, rule)
- No deduplication (allow multiple perspectives)
"""

import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import yaml

from ...llm.client import LLMClient
from ...llm.providers.base import BaseProvider
from ...storage.metrics.collector import MetricsCollector
from ..models import Episode, KnowledgeDocument
from ..tiers.episodic_memory_tier import EpisodicMemoryTier
from ..tiers.semantic_memory_tier import SemanticMemoryTier
from .base_engine import BaseEngine

logger = logging.getLogger(__name__)


class DistillationEngine(BaseEngine):
    """
    Distillation Engine: Transforms episodes into knowledge documents.

    Workflow:
    1. Monitor episode count in L3 (EpisodicMemoryTier)
    2. When threshold reached, retrieve relevant episodes
    3. For each knowledge type, use LLM to synthesize content
    4. Extract rich metadata from episodes
    5. Store KnowledgeDocument in L4 (SemanticMemoryTier)
    6. Maintain provenance links to source episodes
    """

    def __init__(
        self,
        episodic_tier: EpisodicMemoryTier | None = None,
        semantic_tier: SemanticMemoryTier | None = None,
        llm_provider: BaseProvider | LLMClient | None = None,
        domain_config_path: str | None = None,
        episode_threshold: int = 5,
        metrics_enabled: bool = True,
        config: dict[str, Any] | None = None,
        l3_tier: EpisodicMemoryTier | None = None,
        l4_tier: SemanticMemoryTier | None = None,
        telemetry_stream: Any | None = None,
        **_: Any,
    ):
        """
        Initialize the Distillation Engine.

        Args:
            episodic_tier: L3 tier for reading episodes
            semantic_tier: L4 tier for storing knowledge documents
            llm_provider: LLM provider for knowledge synthesis
            domain_config_path: Path to domain configuration YAML
            episode_threshold: Minimum episodes before triggering distillation
            metrics_enabled: Enable metrics collection
        """
        self.config = config or {}
        resolved_episode_threshold = self.config.get("distillation_threshold", episode_threshold)
        resolved_metrics_enabled = self.config.get("metrics_enabled", metrics_enabled)
        metrics_config = {"enabled": resolved_metrics_enabled}
        collector = MetricsCollector(config=metrics_config)
        super().__init__(metrics_collector=collector)
        episodic_tier_resolved = episodic_tier or l3_tier
        semantic_tier_resolved = semantic_tier or l4_tier
        if episodic_tier_resolved is None or semantic_tier_resolved is None:
            raise ValueError("episodic_tier/l3_tier and semantic_tier/l4_tier are required")
        self.episodic_tier: EpisodicMemoryTier = episodic_tier_resolved
        self.semantic_tier: SemanticMemoryTier = semantic_tier_resolved
        # Accept either a provider or a fully-configured LLMClient
        if llm_provider is None:
            self.llm_client: LLMClient = LLMClient.from_env()
        elif isinstance(llm_provider, LLMClient):
            self.llm_client = llm_provider
        else:
            self.llm_client = LLMClient()
            self.llm_client.register_provider(llm_provider)
        self.episode_threshold = resolved_episode_threshold

        # Load domain configuration
        self.domain_config = self._load_domain_config(domain_config_path)

        logger.info(
            f"DistillationEngine initialized with episode_threshold={episode_threshold}, "
            f"domain={self.domain_config.get('domain', {}).get('name', 'default')}"
        )
        self.telemetry_stream = telemetry_stream

    def _load_domain_config(self, config_path: str | None) -> dict[str, Any]:
        """Load domain configuration from YAML file."""
        if config_path is None:
            # Default to container logistics domain
            config_path = "config/domains/container_logistics.yaml"

        try:
            path = Path(config_path)
            if not path.exists():
                logger.warning(f"Domain config not found: {config_path}, using defaults")
                return self._get_default_config()

            with open(path) as f:
                config = yaml.safe_load(f)
                if isinstance(config, dict):
                    logger.info(
                        "Loaded domain config: %s",
                        config.get("domain", {}).get("name"),
                    )
                    return cast(dict[str, Any], config)
                logger.warning("Domain config is not a dict: %s", config_path)
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Failed to load domain config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """Return default configuration if config file is not available."""
        return {
            "domain": {"name": "default"},
            "knowledge_types": {
                "summary": {
                    "description": "Condensed overview of episode(s)",
                    "llm_instruction": "Summarize the key facts and outcomes from these episodes in 2-3 sentences.",
                },
                "insight": {
                    "description": "Deeper analysis or pattern recognition",
                    "llm_instruction": "Identify non-obvious patterns, correlations, or insights from these episodes.",
                },
                "pattern": {
                    "description": "Recurring behavior or trend",
                    "llm_instruction": "Describe recurring patterns, common sequences, or typical workflows observed.",
                },
                "recommendation": {
                    "description": "Actionable advice or best practice",
                    "llm_instruction": "Based on these episodes, what recommendations or best practices can be extracted?",
                },
                "rule": {
                    "description": "Explicit rule or constraint",
                    "llm_instruction": "Extract any explicit rules, policies, or constraints mentioned or implied.",
                },
            },
        }

    async def process(self, **kwargs: Any) -> dict[str, Any]:
        """
        Main processing method: Check for episodes and create knowledge documents.

        Args:
            **kwargs: Additional parameters (e.g., force_process=True, session_id=str)

        Returns:
            Dict with processing results and metrics
        """
        async with self.metrics.start_timer("distillation") as timer:
            try:
                # Extract parameters
                force_process = kwargs.get("force_process", False)
                session_id = kwargs.get("session_id")
                time_range = kwargs.get("time_range")  # Optional temporal filtering

                # Step 1: Check if we should trigger distillation
                episode_count = await self._count_episodes(session_id, time_range)

                if not force_process and episode_count < self.episode_threshold:
                    logger.info(
                        f"Episode count ({episode_count}) below threshold ({self.episode_threshold}), "
                        "skipping distillation"
                    )
                    return {
                        "status": "skipped",
                        "reason": "below_threshold",
                        "episode_count": episode_count,
                        "threshold": self.episode_threshold,
                    }

                # Step 2: Retrieve episodes from L3
                logger.info(f"Retrieving {episode_count} episodes for distillation")
                episodes = await self._retrieve_episodes(session_id, time_range)

                if not episodes:
                    logger.warning("No episodes retrieved for distillation")
                    return {"status": "skipped", "reason": "no_episodes", "episode_count": 0}

                # Emit distillation_started event
                if self.telemetry_stream:
                    await self.telemetry_stream.publish(
                        event_type="distillation_started",
                        session_id=session_id or "global",
                        data={
                            "episode_count": len(episodes),
                            "threshold": self.episode_threshold,
                            "force_process": force_process,
                        },
                    )

                # Step 3: Generate knowledge documents for each type
                knowledge_types = self.domain_config.get("knowledge_types", {})
                created_docs = []

                for knowledge_type, type_config in knowledge_types.items():
                    try:
                        doc = await self._create_knowledge_document(
                            episodes=episodes,
                            knowledge_type=knowledge_type,
                            type_config=type_config,
                            session_id=session_id,
                        )

                        if doc:
                            # Step 4: Store in L4
                            doc_id = await self.semantic_tier.store(doc)
                            created_docs.append(
                                {
                                    "id": doc_id,
                                    "type": knowledge_type,
                                    "episode_count": len(episodes),
                                }
                            )
                            logger.info(f"Created {knowledge_type} document: {doc_id}")

                            # Emit knowledge_created event
                            if self.telemetry_stream:
                                await self.telemetry_stream.publish(
                                    event_type="knowledge_created",
                                    session_id=session_id or "global",
                                    data={
                                        "knowledge_id": doc_id,
                                        "knowledge_type": knowledge_type,
                                        "title": doc.title[:100] if doc.title else None,
                                        "episode_count": len(episodes),
                                    },
                                )

                    except Exception as e:
                        logger.error(f"Failed to create {knowledge_type} document: {e}")
                        # Continue with other knowledge types
                        continue

                if timer.start_time is None:
                    elapsed_ms = 0.0
                else:
                    elapsed_ms = (time.perf_counter() - timer.start_time) * 1000

                result = {
                    "status": "success",
                    "processed_episodes": len(episodes),
                    "created_documents": len(created_docs),
                    "knowledge_documents_created": len(created_docs),
                    "documents": created_docs,
                    "elapsed_ms": elapsed_ms,
                }

                # Emit distillation_completed event
                if self.telemetry_stream:
                    await self.telemetry_stream.publish(
                        event_type="distillation_completed",
                        session_id=session_id or "global",
                        data={
                            "processed_episodes": len(episodes),
                            "created_documents": len(created_docs),
                            "elapsed_ms": elapsed_ms,
                        },
                    )

                return result

            except Exception as e:
                timer.success = False
                logger.error(f"Distillation processing failed: {e}")
                return {"status": "error", "error": str(e)}
        raise AssertionError("Unreachable: process should return or raise.")

    async def distill(
        self,
        session_id: str | None = None,
        track_provenance: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Backwards-compatible alias for process()."""
        return await self.process(
            session_id=session_id, track_provenance=track_provenance, force_process=True, **kwargs
        )

    async def _count_episodes(
        self, session_id: str | None = None, time_range: tuple[datetime, datetime] | None = None
    ) -> int:
        """
        Count episodes in L3 that match the criteria.

        Args:
            session_id: Optional session filter
            time_range: Optional (start_time, end_time) tuple

        Returns:
            Number of episodes
        """
        try:
            # Use EpisodicMemoryTier's query method to count episodes
            # For simplicity, retrieve episodes and count them
            episodes = await self._retrieve_episodes(session_id, time_range, limit=1000)
            return len(episodes)
        except Exception as e:
            logger.error(f"Failed to count episodes: {e}")
            return 0

    async def _retrieve_episodes(
        self,
        session_id: str | None = None,
        time_range: tuple[datetime, datetime] | None = None,
        limit: int = 100,
    ) -> list[Episode]:
        """
        Retrieve episodes from L3 for knowledge synthesis.

        Args:
            session_id: Optional session filter
            time_range: Optional (start_time, end_time) tuple
            limit: Maximum episodes to retrieve

        Returns:
            List of Episode objects
        """
        try:
            if time_range:
                _start_time, _end_time = time_range
                episodes = await self.episodic_tier.query(filters=None, limit=limit)
            else:
                episodes = await self.episodic_tier.query(
                    filters={"session_id": session_id} if session_id else None, limit=limit
                )

            pre_filter_count = len(episodes)

            # Filter by session_id if provided
            if session_id:
                episodes = [ep for ep in episodes if ep.session_id == session_id]

            logger.info(
                "Distillation episode retrieval: session=%s, pre_filter=%d, post_filter=%d, limit=%d",
                session_id,
                pre_filter_count,
                len(episodes),
                limit,
            )

            return episodes

        except Exception as e:
            logger.error(f"Failed to retrieve episodes: {e}")
            return []

    async def _create_knowledge_document(
        self,
        episodes: list[Episode],
        knowledge_type: str,
        type_config: dict[str, Any],
        session_id: str | None = None,
    ) -> KnowledgeDocument | None:
        """
        Create a knowledge document from episodes using LLM.

        Args:
            episodes: Source episodes
            knowledge_type: Type of knowledge (summary, insight, pattern, etc.)
            type_config: Configuration for this knowledge type
            session_id: Optional session identifier

        Returns:
            KnowledgeDocument or None if synthesis fails
        """
        try:
            llm_instruction = type_config.get(
                "llm_instruction", "Synthesize knowledge from these episodes."
            )

            episode_context = "\n\n".join(
                [
                    f"Episode {i + 1} (ID: {ep.episode_id}):\n"
                    f"Summary: {ep.summary}\n"
                    f"Facts: {len(ep.source_fact_ids)} facts\n"
                    f"Entities: {', '.join([str(e.get('name', e)) for e in ep.entities[:5]])}"  # First 5 entities
                    for i, ep in enumerate(episodes)
                ]
            )

            prompt = f"""{llm_instruction}

Context from {len(episodes)} episode(s):

{episode_context}

Provide a structured response with the following fields:
- content: The main knowledge content
- title: A concise title (max 100 characters)
- key_points: List of 3-5 key points (as bullet points)
"""

            response = await self.llm_client.generate(prompt=prompt, temperature=0.3)

            try:
                content, title, key_points = self._parse_llm_response(response.text, knowledge_type)
            except Exception as parse_error:
                logger.warning(
                    "LLM parse failed for knowledge_type=%s: %s. Falling back to rule-based synthesis.",
                    knowledge_type,
                    parse_error,
                )
                return self._create_rule_based_document(episodes, knowledge_type, session_id)

            metadata = self._extract_metadata(episodes)
            source_episodes = [ep.episode_id for ep in episodes]

            doc = KnowledgeDocument(
                knowledge_id=str(uuid.uuid4()),
                session_id=session_id or (episodes[0].session_id if episodes else None),
                knowledge_type=knowledge_type,
                content=content,
                title=title,
                metadata={**metadata, "key_points": key_points},
                source_episode_ids=source_episodes,
                episode_count=len(source_episodes),
            )

            return doc

        except Exception as e:
            logger.error(f"Failed to create knowledge document: {e}")
            return None

    def _create_rule_based_document(
        self, episodes: list[Episode], knowledge_type: str, session_id: str | None
    ) -> KnowledgeDocument:
        """Fallback synthesis when LLM output cannot be parsed."""
        summaries = [ep.summary for ep in episodes if getattr(ep, "summary", "")]
        content = " \n".join(summaries) or "Distilled knowledge from episodes"
        title = f"{knowledge_type.title()} summary"[:100]
        return KnowledgeDocument(
            knowledge_id=str(uuid.uuid4()),
            session_id=session_id or (episodes[0].session_id if episodes else None),
            title=title,
            content=content,
            knowledge_type=knowledge_type,
            confidence_score=0.5,
            source_episode_ids=[ep.episode_id for ep in episodes],
            episode_count=len(episodes),
            tags=[knowledge_type],
            domain=self.domain_config.get("domain", {}).get("name"),
        )

    def _parse_llm_response(self, response: str, knowledge_type: str) -> tuple[str, str, list[str]]:
        """
        Parse LLM response into structured components.

        Args:
            response: Raw LLM response
            knowledge_type: Type of knowledge being created

        Returns:
            Tuple of (content, title, key_points)
        """
        # Simple parsing logic - can be enhanced with structured output
        lines = response.strip().split("\n")

        content = response
        title = f"{knowledge_type.capitalize()} Knowledge"
        key_points = []

        # Extract title if present
        for line in lines:
            if line.lower().startswith("title:"):
                title = line.split(":", 1)[1].strip()
                break

        # Extract key points if present
        in_key_points = False
        for line in lines:
            if "key_points:" in line.lower() or "key points:" in line.lower():
                in_key_points = True
                continue

            if in_key_points:
                if line.strip().startswith("-") or line.strip().startswith("•"):
                    point = line.strip().lstrip("-•").strip()
                    if point:
                        key_points.append(point)
                elif line.strip() and not line.strip().startswith(" "):
                    # End of key points section
                    break

        return content, title, key_points

    def _extract_metadata(self, episodes: list[Episode]) -> dict[str, Any]:
        """
        Extract rich metadata from episodes.

        Args:
            episodes: Source episodes

        Returns:
            Metadata dictionary with domain-specific fields
        """
        metadata: dict[str, Any] = {}

        # Get metadata schema from domain config
        schema = self.domain_config.get("metadata_schema", {})

        # Extract each metadata field from episodes
        for field_name, field_config in schema.items():
            # Aggregate field values across episodes
            values: list[Any] = []
            for episode in episodes:
                if episode.metadata and field_name in episode.metadata:
                    value = episode.metadata[field_name]
                    if value and value not in values:
                        values.append(value)

            # Store most common value or list of values
            if values:
                if len(values) == 1:
                    metadata[field_name] = values[0]
                else:
                    # For indexed fields, take most common
                    # For non-indexed, keep all unique values
                    if field_config.get("indexed", False):
                        metadata[field_name] = values[0]  # First occurrence
                    else:
                        metadata[field_name] = values

        # Add aggregate metadata
        metadata["source_episode_count"] = len(episodes)

        # Collect and deduplicate entities
        all_entities = [entity for ep in episodes for entity in ep.entities]
        unique_entities = []
        seen_hashes = set()

        for entity in all_entities:
            try:
                # Create a hashable representation for deduplication
                # Convert values to strings to handle unhashable types like lists
                entity_hash = tuple(sorted((k, str(v)) for k, v in entity.items()))

                if entity_hash not in seen_hashes:
                    seen_hashes.add(entity_hash)
                    unique_entities.append(entity)
            except Exception:
                # If something goes wrong, just include it to be safe
                unique_entities.append(entity)

        metadata["entities"] = unique_entities[:20]  # Top 20 unique entities

        return metadata

    async def health_check(self) -> dict[str, Any]:
        """
        Check health of distillation engine components.

        Returns:
            Health status dictionary
        """
        checks: dict[str, bool] = {}
        health: dict[str, Any] = {
            "service": "DistillationEngine",
            "status": "healthy",
            "checks": checks,
        }

        try:
            # Check L3 tier connectivity
            l3_health = await self.episodic_tier.health_check()
            checks["episodic_tier"] = l3_health.get("status") == "healthy"

            # Check L4 tier connectivity
            l4_health = await self.semantic_tier.health_check()
            checks["semantic_tier"] = l4_health.get("status") == "healthy"

            # Check LLM client availability
            checks["llm_client"] = self.llm_client is not None

            # Overall status
            if not all(checks.values()):
                health["status"] = "degraded"

        except Exception as e:
            health["status"] = "unhealthy"
            health["error"] = str(e)

        return health
