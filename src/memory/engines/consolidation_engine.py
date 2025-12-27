"""
Consolidation Engine (L2 -> L3).

This engine is responsible for consolidating facts from Working Memory (L2)
into episodes stored in Episodic Memory (L3).
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.memory.engines.base_engine import BaseEngine
from src.memory.tiers.working_memory_tier import WorkingMemoryTier
from src.memory.tiers.episodic_memory_tier import EpisodicMemoryTier
from src.memory.models import Episode, Fact
from src.utils.providers import GeminiProvider

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        l2_tier: WorkingMemoryTier,
        l3_tier: EpisodicMemoryTier,
        gemini_provider: GeminiProvider,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__()
        self.l2 = l2_tier
        self.l3 = l3_tier
        self.gemini = gemini_provider
        self.config = config or {}
        self.time_window_hours = self.config.get(
            'time_window_hours', self.DEFAULT_TIME_WINDOW_HOURS
        )
        self.embedding_model = self.config.get(
            'embedding_model', self.DEFAULT_EMBEDDING_MODEL
        )
        self.summary_model = self.config.get(
            'summary_model', self.DEFAULT_SUMMARY_MODEL
        )

    async def process(self, session_id: Optional[str] = None) -> Dict[str, Any]:
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

    async def process_session(self, session_id: str) -> Dict[str, Any]:
        """
        Process a specific session for fact consolidation.
        """
        stats = {
            "session_id": session_id,
            "facts_retrieved": 0,
            "episodes_created": 0,
            "errors": 0
        }

        try:
            # 1. Determine time range (from last episode or beginning)
            start_time = await self._get_last_consolidation_time(session_id)
            end_time = datetime.now(timezone.utc)
            
            # 2. Retrieve facts from L2 in time range
            facts = await self._get_facts_in_range(session_id, start_time, end_time)
            stats["facts_retrieved"] = len(facts)
            
            if not facts:
                return stats
            
            # 3. Cluster facts by time windows
            clusters = self._cluster_facts_by_time(facts)
            
            # 4. Create episodes from clusters
            for cluster in clusters:
                try:
                    episode = await self._create_episode_from_facts(
                        session_id, cluster
                    )
                    
                    # 5. Generate embedding
                    embedding = await self._generate_embedding(episode)
                    
                    # 6. Store in L3
                    await self.l3.store({
                        'episode': episode,
                        'embedding': embedding,
                        'entities': [],  # Could extract from facts
                        'relationships': []  # Could extract from facts
                    })
                    
                    stats["episodes_created"] += 1
                    
                except Exception as e:
                    logger.error(f"Error creating episode: {e}")
                    stats["errors"] += 1
                    
            return stats

        except Exception as e:
            logger.error(f"Error consolidating facts for session {session_id}: {e}")
            stats["errors"] += 1
            stats["last_error"] = str(e)
            return stats

    async def _get_last_consolidation_time(self, session_id: str) -> datetime:
        """Get the time of the last consolidated episode for this session."""
        # Query L3 for most recent episode
        # For now, return 24 hours ago as default
        return datetime.now(timezone.utc) - timedelta(hours=self.time_window_hours)

    async def _get_facts_in_range(
        self, 
        session_id: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Fact]:
        """Retrieve facts from L2 within time range."""
        # WorkingMemoryTier needs a method to query by time range
        # For now, get all facts and filter
        all_facts = await self.l2.query_by_session(session_id)
        
        filtered = []
        for fact_dict in all_facts:
            extracted_at = fact_dict.get('extracted_at')
            if isinstance(extracted_at, str):
                extracted_at = datetime.fromisoformat(extracted_at)
            
            if start_time <= extracted_at <= end_time:
                # Convert dict to Fact object
                fact = Fact(**fact_dict)
                filtered.append(fact)
        
        return filtered

    def _cluster_facts_by_time(self, facts: List[Fact]) -> List[List[Fact]]:
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

    async def _create_episode_from_facts(
        self, 
        session_id: str, 
        facts: List[Fact]
    ) -> Episode:
        """Create an episode from a cluster of facts using LLM."""
        # Generate summary and narrative
        facts_text = "\n".join([
            f"- {f.content} (certainty: {f.certainty}, impact: {f.impact})"
            for f in facts
        ])
        
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
        
        response = await self.gemini.generate(
            prompt=prompt,
            model=self.summary_model,
            temperature=0.3,
            max_output_tokens=512
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
            source_observation_timestamp=datetime.now(timezone.utc),
            embedding_model=self.embedding_model,
            topics=[],
            importance_score=sum(f.ciar_score for f in facts) / len(facts)
        )
        
        return episode

    async def _generate_embedding(self, episode: Episode) -> List[float]:
        """Generate embedding for episode content."""
        # Combine summary and narrative for embedding
        text = f"{episode.summary}. {episode.narrative or ''}"
        
        embedding = await self.gemini.get_embedding(
            text=text,
            model=self.embedding_model
        )
        
        return embedding

    async def health_check(self) -> Dict[str, Any]:
        """Check health of dependencies."""
        l2_health = await self.l2.health_check()
        l3_health = await self.l3.health_check()
        gemini_health = await self.gemini.health_check()
        
        healthy = (
            l2_health.get("status") == "healthy" and 
            l3_health.get("status") == "healthy" and
            gemini_health.healthy
        )
        
        return {
            "status": "healthy" if healthy else "unhealthy",
            "l2": l2_health,
            "l3": l3_health,
            "gemini": gemini_health
        }
