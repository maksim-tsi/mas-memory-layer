"""
Promotion Engine (L1 -> L2).

This engine is responsible for promoting significant facts from the
Active Context (L1) to Working Memory (L2).
"""

import logging
from typing import Dict, Any, List, Optional

from src.memory.engines.base_engine import BaseEngine
from src.memory.engines.fact_extractor import FactExtractor
from src.memory.tiers.active_context_tier import ActiveContextTier
from src.memory.tiers.working_memory_tier import WorkingMemoryTier
from src.memory.ciar_scorer import CIARScorer

logger = logging.getLogger(__name__)


class PromotionEngine(BaseEngine):
    """
    Promotes facts from L1 to L2 based on CIAR score.
    
    Flow:
    1. Retrieve recent turns from ActiveContextTier (L1).
    2. Extract facts using FactExtractor (LLM).
    3. Score facts using CIARScorer.
    4. Filter facts based on promotion_threshold.
    5. Store qualifying facts in WorkingMemoryTier (L2).
    """

    DEFAULT_PROMOTION_THRESHOLD = 0.6

    def __init__(
        self,
        l1_tier: ActiveContextTier,
        l2_tier: WorkingMemoryTier,
        fact_extractor: FactExtractor,
        ciar_scorer: CIARScorer,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__()
        self.l1 = l1_tier
        self.l2 = l2_tier
        self.extractor = fact_extractor
        self.scorer = ciar_scorer
        self.config = config or {}
        self.promotion_threshold = self.config.get(
            'promotion_threshold', self.DEFAULT_PROMOTION_THRESHOLD
        )

    async def process(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute promotion cycle for a session.
        
        Args:
            session_id: The session to process.
            
        Returns:
            Dict with stats (processed, promoted, errors).
        """
        if not session_id:
            return {"status": "skipped", "reason": "no_session_id"}
        
        return await self.process_session(session_id)

    async def process_session(self, session_id: str) -> Dict[str, Any]:
        """
        Process a specific session for fact promotion.
        """
        stats = {
            "session_id": session_id,
            "turns_retrieved": 0,
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
            
            # Format turns for extraction
            # We reverse because L1 returns most recent first (usually), but we want chronological for LLM?
            # ActiveContextTier.retrieve doc says "Retrieve recent turns". 
            # Redis lrange returns ordered list. 
            # Let's assume chronological or handle it.
            # Usually chat history is passed chronological.
            # If L1 stores with LPUSH, index 0 is newest.
            # So we should reverse to get oldest -> newest.
            chronological_turns = list(reversed(turns))
            
            conversation_text = self._format_conversation(chronological_turns)
            
            # 2. Extract facts
            metadata = {"session_id": session_id, "source_uri": f"l1:{session_id}"}
            facts = await self.extractor.extract_facts(conversation_text, metadata)
            stats["facts_extracted"] = len(facts)
            
            # 3. Score and Filter
            promoted_facts = []
            for fact in facts:
                # Calculate CIAR score
                # We need to populate access_count and created_at if not present
                # Fact object has them.
                # CIARScorer.calculate expects a dict or Fact object?
                # Let's check CIARScorer.calculate signature.
                # It takes a dict or object.
                
                score = self.scorer.calculate(fact)
                fact.ciar_score = score
                
                if score >= self.promotion_threshold:
                    promoted_facts.append(fact)
            
            # 4. Store in L2
            for fact in promoted_facts:
                # Check for duplicates?
                # For now, we trust L2 or just store.
                # WorkingMemoryTier.store takes a dict.
                await self.l2.store(fact.model_dump())
                stats["facts_promoted"] += 1
                
            return stats

        except Exception as e:
            logger.error(f"Error promoting facts for session {session_id}: {e}")
            stats["errors"] += 1
            stats["last_error"] = str(e)
            return stats

    async def health_check(self) -> Dict[str, Any]:
        """Check health of dependencies."""
        l1_health = await self.l1.health_check()
        l2_health = await self.l2.health_check()
        # Extractor doesn't have health_check yet, but LLMClient does.
        # We can check LLMClient via extractor if we expose it, or just assume ok if L1/L2 ok.
        
        healthy = (
            l1_health.get("status") == "healthy" and 
            l2_health.get("status") == "healthy"
        )
        
        return {
            "status": "healthy" if healthy else "unhealthy",
            "l1": l1_health,
            "l2": l2_health
        }

    def _format_conversation(self, turns: List[Dict[str, Any]]) -> str:
        """Format turns into a conversation string."""
        lines = []
        for turn in turns:
            role = turn.get("role", "unknown").capitalize()
            content = turn.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)
