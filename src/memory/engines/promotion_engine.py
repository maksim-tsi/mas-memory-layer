"""
Promotion Engine (L1 -> L2).

This engine implements ADR-003's batch processing strategy:
- Triggers when L1 buffer reaches threshold (10-20 turns)
- Uses TopicSegmenter for batch compression and segmentation
- Scores topic segments (not individual facts) using CIAR
- Promotes significant segments to L2 Working Memory
"""

import logging
from typing import Dict, Any, List, Optional

from src.memory.engines.base_engine import BaseEngine
from src.memory.engines.topic_segmenter import TopicSegmenter, TopicSegment
from src.memory.engines.fact_extractor import FactExtractor
from src.memory.tiers.active_context_tier import ActiveContextTier
from src.memory.tiers.working_memory_tier import WorkingMemoryTier
from src.memory.ciar_scorer import CIARScorer
from src.memory.models import Fact

logger = logging.getLogger(__name__)


class PromotionEngine(BaseEngine):
    """
    Promotes topic segments from L1 to L2 based on CIAR score.
    
    ADR-003 Batch Processing Flow:
    1. Check L1 turn count against threshold (10-20 turns)
    2. If threshold met, retrieve batch from ActiveContextTier
    3. Use TopicSegmenter for batch compression and segmentation
    4. Score each segment using CIAR (Certainty × Impact × Age × Recency)
    5. Extract facts from significant segments
    6. Store facts with segment metadata in WorkingMemoryTier (L2)
    """

    DEFAULT_PROMOTION_THRESHOLD = 0.6
    DEFAULT_BATCH_MIN_TURNS = 10
    DEFAULT_BATCH_MAX_TURNS = 20

    def __init__(
        self,
        l1_tier: ActiveContextTier,
        l2_tier: WorkingMemoryTier,
        topic_segmenter: TopicSegmenter,
        fact_extractor: FactExtractor,
        ciar_scorer: CIARScorer,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__()
        self.l1 = l1_tier
        self.l2 = l2_tier
        self.segmenter = topic_segmenter
        self.extractor = fact_extractor
        self.scorer = ciar_scorer
        self.config = config or {}
        self.promotion_threshold = self.config.get(
            'promotion_threshold', self.DEFAULT_PROMOTION_THRESHOLD
        )
        self.batch_min_turns = self.config.get(
            'batch_min_turns', self.DEFAULT_BATCH_MIN_TURNS
        )
        self.batch_max_turns = self.config.get(
            'batch_max_turns', self.DEFAULT_BATCH_MAX_TURNS
        )

    async def process(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute batch promotion cycle for a session.
        
        Args:
            session_id: The session to process.
            
        Returns:
            Dict with stats (turns_retrieved, segments_created, facts_promoted, etc.).
        """
        if not session_id:
            return {"status": "skipped", "reason": "no_session_id"}
        
        return await self.process_session(session_id)

    async def process_session(self, session_id: str) -> Dict[str, Any]:
        """
        Process a specific session for batch topic segmentation and promotion.
        
        This implements ADR-003's batch processing strategy.
        """
        stats = {
            "session_id": session_id,
            "turns_retrieved": 0,
            "segments_created": 0,
            "segments_promoted": 0,
            "facts_extracted": 0,
            "facts_promoted": 0,
            "errors": 0
        }

        try:
            # 1. Retrieve turns from L1
            turns = await self.l1.retrieve(session_id)
            if not turns:
                return stats
            
            stats["turns_retrieved"] = len(turns)
            
            # 2. Check batch threshold
            if len(turns) < self.batch_min_turns:
                logger.info(
                    f"Session {session_id} has {len(turns)} turns, "
                    f"below minimum threshold {self.batch_min_turns}. Skipping promotion."
                )
                return stats
            
            # 3. Format turns chronologically for segmentation
            # Assume L1 stores with LPUSH (newest first), so reverse for chronological
            chronological_turns = list(reversed(turns))
            
            # 4. Segment into topics using batch compression
            metadata = {"session_id": session_id, "source": "l1_batch"}
            segments = await self.segmenter.segment_turns(chronological_turns, metadata)
            stats["segments_created"] = len(segments)
            
            if not segments:
                logger.warning(f"No segments created for session {session_id}")
                return stats
            
            # 5. Score and process each segment
            for segment in segments:
                try:
                    # Calculate segment-level CIAR score
                    # The segment provides certainty and impact from LLM analysis
                    segment_score = await self._score_segment(segment)
                    
                    if segment_score < self.promotion_threshold:
                        logger.debug(
                            f"Segment '{segment.topic}' scored {segment_score:.3f}, "
                            f"below threshold {self.promotion_threshold}. Skipping."
                        )
                        continue
                    
                    stats["segments_promoted"] += 1
                    
                    # 6. Extract facts from significant segment
                    # Use segment summary as input to fact extractor
                    segment_text = self._format_segment_for_extraction(segment, chronological_turns)
                    fact_metadata = {
                        "session_id": session_id,
                        "source_uri": f"l1:{session_id}:segment:{segment.segment_id}",
                        "topic_segment_id": segment.segment_id,
                        "topic_label": segment.topic
                    }
                    
                    facts = await self.extractor.extract_facts(segment_text, fact_metadata)
                    stats["facts_extracted"] += len(facts)
                    
                    # 7. Store facts with segment context in L2
                    for fact in facts:
                        # Inherit segment's certainty/impact if fact doesn't have strong values
                        if fact.certainty < segment.certainty:
                            fact.certainty = segment.certainty
                        if fact.impact < segment.impact:
                            fact.impact = segment.impact
                        
                        # Recalculate CIAR with inherited values
                        fact.ciar_score = self.scorer.calculate(fact)
                        
                        # Store in L2
                        await self.l2.store(fact.model_dump())
                        stats["facts_promoted"] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing segment '{segment.topic}': {e}")
                    stats["errors"] += 1
                    continue
                
            return stats

        except Exception as e:
            logger.error(f"Error in batch promotion for session {session_id}: {e}")
            stats["errors"] += 1
            stats["last_error"] = str(e)
            return stats

    async def _score_segment(self, segment: TopicSegment) -> float:
        """
        Calculate CIAR score for a topic segment.
        
        Since segments are recent (from L1 batch), age_decay ≈ 1.0 and recency_boost ≈ 1.0.
        The primary factors are segment-level certainty and impact from LLM analysis.
        
        Args:
            segment: The TopicSegment to score
            
        Returns:
            float: CIAR score (0.0-1.0)
        """
        # For fresh segments: age_decay = 1.0, recency_boost = 1.0
        # CIAR = (Certainty × Impact) × Age × Recency
        ciar_score = (segment.certainty * segment.impact) * 1.0 * 1.0
        return round(ciar_score, 4)

    def _format_segment_for_extraction(
        self,
        segment: TopicSegment,
        turns: List[Dict[str, Any]]
    ) -> str:
        """
        Format a segment for fact extraction.
        
        Combines segment summary with relevant turn content.
        """
        lines = [
            f"Topic: {segment.topic}",
            f"Summary: {segment.summary}",
            "",
            "Key Points:",
        ]
        for point in segment.key_points:
            lines.append(f"- {point}")
        
        lines.append("")
        lines.append("Relevant Conversation:")
        
        # Include turns from this segment
        for idx in segment.turn_indices:
            if idx < len(turns):
                turn = turns[idx]
                role = turn.get("role", "unknown").capitalize()
                content = turn.get("content", "")
                lines.append(f"{role}: {content}")
        
        return "\n".join(lines)

    async def health_check(self) -> Dict[str, Any]:
        """Check health of dependencies."""
        l1_health = await self.l1.health_check()
        l2_health = await self.l2.health_check()
        
        healthy = (
            l1_health.get("status") == "healthy" and 
            l2_health.get("status") == "healthy"
        )
        
        return {
            "status": "healthy" if healthy else "unhealthy",
            "l1": l1_health,
            "l2": l2_health,
            "config": {
                "promotion_threshold": self.promotion_threshold,
                "batch_min_turns": self.batch_min_turns,
                "batch_max_turns": self.batch_max_turns
            }
        }
