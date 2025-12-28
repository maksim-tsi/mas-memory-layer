"""
Topic segmentation engine for batch compression of conversational turns.

Per ADR-003 (Revised Nov 2, 2025), this component performs batch processing
of L1 turns by compressing noise and segmenting content into coherent topics
using a single LLM call for efficiency.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError

from src.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class TopicSegmentationError(Exception):
    """Raised when topic segmentation fails."""
    pass


class TopicSegment(BaseModel):
    """
    Represents a coherent topic segment extracted from a batch of turns.
    
    Attributes:
        segment_id: Unique identifier for this segment
        topic: Brief topic label (e.g., "Container ETA Query")
        summary: Concise summary of the conversation segment
        key_points: List of significant points discussed
        turn_indices: Indices of source turns in the batch
        certainty: Confidence in segment extraction (0.0-1.0)
        impact: Estimated importance of this topic (0.0-1.0)
        participant_count: Number of distinct participants
        message_count: Number of messages in this segment
        temporal_context: Optional temporal markers (dates, times mentioned)
    """
    
    segment_id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str = Field(..., min_length=3, max_length=200)
    summary: str = Field(..., min_length=10, max_length=2000)
    key_points: List[str] = Field(default_factory=list, max_length=20)
    turn_indices: List[int] = Field(default_factory=list)
    certainty: float = Field(default=0.7, ge=0.0, le=1.0)
    impact: float = Field(default=0.5, ge=0.0, le=1.0)
    participant_count: int = Field(default=0, ge=0)
    message_count: int = Field(default=0, ge=0)
    temporal_context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TopicSegmenter:
    """
    Segments batches of conversation turns into coherent topics using LLM.
    
    This component implements ADR-003's batch compression strategy:
    1. Takes 10-20 raw turns from L1
    2. Makes a single LLM call for efficiency
    3. Compresses conversational noise
    4. Segments into coherent topics
    5. Extracts metadata for CIAR scoring
    
    Attributes:
        llm_client: Client for LLM interactions
        model_name: Name of the LLM model to use (default: Gemini 2.5 Flash per ADR-006)
    """

    DEFAULT_MODEL = "gemini-2.5-flash"
    DEFAULT_MIN_TURNS = 10
    DEFAULT_MAX_TURNS = 20

    def __init__(
        self,
        llm_client: LLMClient,
        model_name: Optional[str] = None,
        min_turns: int = DEFAULT_MIN_TURNS,
        max_turns: int = DEFAULT_MAX_TURNS
    ):
        self.llm_client = llm_client
        self.model_name = model_name or self.DEFAULT_MODEL
        self.min_turns = min_turns
        self.max_turns = max_turns
        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt for topic segmentation."""
        return """You are an expert at analyzing supply chain and logistics conversations.

Your task: Segment a batch of conversation turns into coherent topics.

Instructions:
1. Identify distinct topics or themes discussed in the conversation
2. Group related turns into segments
3. For each segment, extract:
   - topic: Brief descriptive label (3-50 words)
   - summary: Concise narrative of what was discussed (50-500 words)
   - key_points: List of 3-10 significant points from the segment
   - turn_indices: Indices (0-based) of turns belonging to this segment
   - certainty: Your confidence in this segmentation (0.0-1.0)
   - impact: Estimated importance/urgency of this topic (0.0-1.0)
   - participant_count: Number of distinct speakers
   - message_count: Number of messages in segment
   - temporal_context: Any dates, times, deadlines mentioned

Guidelines:
- Compress noise: Skip greetings, acknowledgments, filler
- Merge related sub-topics into one segment
- Assign high impact (0.7-1.0) to: urgent requests, critical alerts, decisions, commitments
- Assign medium impact (0.4-0.7) to: informational queries, status updates
- Assign low impact (0.0-0.4) to: casual discussion, small talk
- Certainty based on: clarity of topic, coherence of discussion

Return JSON: {"segments": [list of segment objects]}"""

    async def segment_turns(
        self,
        turns: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[TopicSegment]:
        """
        Segment a batch of turns into coherent topics.
        
        Args:
            turns: List of conversation turns (dicts with 'role', 'content', 'timestamp')
            metadata: Optional metadata (e.g., session_id, domain context)
            
        Returns:
            List[TopicSegment]: List of extracted topic segments
            
        Raises:
            TopicSegmentationError: If segmentation fails
        """
        if not turns:
            return []
        
        # Enforce batch size constraints
        if len(turns) < self.min_turns:
            logger.info(f"Turn count ({len(turns)}) below minimum ({self.min_turns}). Skipping segmentation.")
            return []
        
        if len(turns) > self.max_turns:
            logger.warning(f"Turn count ({len(turns)}) exceeds maximum ({self.max_turns}). Truncating.")
            turns = turns[-self.max_turns:]  # Take most recent turns
        
        try:
            return await self._segment_with_llm(turns, metadata)
        except Exception as e:
            logger.error(f"Topic segmentation failed: {e}")
            # Fallback: Create a single segment from all turns
            return [self._create_fallback_segment(turns, metadata)]

    async def _segment_with_llm(
        self,
        turns: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[TopicSegment]:
        """Segment turns using LLM."""
        # Format conversation for LLM
        formatted = self._format_conversation(turns)
        
        prompt = f"""Conversation to segment:

{formatted}

Now segment this conversation into coherent topics. Return JSON only."""

        # Make LLM call
        response = await self.llm_client.generate(
            prompt=f"{self._system_prompt}\n\n{prompt}",
            model=self.model_name,
            temperature=0.3  # Lower temperature for consistent structured output
        )

        # Parse response
        try:
            content = response.text.strip()
            
            # Clean markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            data = json.loads(content.strip())
            raw_segments = data.get("segments", [])
            
            if not raw_segments:
                logger.warning("LLM returned no segments. Using fallback.")
                return [self._create_fallback_segment(turns, metadata)]
            
            # Validate and convert to TopicSegment objects
            segments = []
            for rs in raw_segments:
                try:
                    segment = TopicSegment(
                        topic=rs.get("topic"),
                        summary=rs.get("summary"),
                        key_points=rs.get("key_points", []),
                        turn_indices=rs.get("turn_indices", []),
                        certainty=float(rs.get("certainty", 0.7)),
                        impact=float(rs.get("impact", 0.5)),
                        participant_count=int(rs.get("participant_count", 0)),
                        message_count=int(rs.get("message_count", 0)),
                        temporal_context=rs.get("temporal_context", {})
                    )
                    segments.append(segment)
                except ValidationError as ve:
                    logger.warning(f"Skipping invalid segment from LLM: {ve}")
                    continue
            
            if not segments:
                logger.warning("No valid segments after validation. Using fallback.")
                return [self._create_fallback_segment(turns, metadata)]
            
            return segments

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            raise TopicSegmentationError(f"Invalid JSON from LLM: {e}")

    def _format_conversation(self, turns: List[Dict[str, Any]]) -> str:
        """Format turns into readable conversation text."""
        lines = []
        for idx, turn in enumerate(turns):
            role = turn.get("role", "unknown").capitalize()
            content = turn.get("content", "")
            timestamp = turn.get("timestamp", "")
            
            # Format: [idx] Role (timestamp): content
            ts_str = f" ({timestamp})" if timestamp else ""
            lines.append(f"[{idx}] {role}{ts_str}: {content}")
        
        return "\n".join(lines)

    def _create_fallback_segment(
        self,
        turns: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> TopicSegment:
        """Create a single fallback segment when LLM segmentation fails."""
        # Count participants
        participants = set()
        for turn in turns:
            role = turn.get("role", "unknown")
            participants.add(role)
        
        # Extract indices
        indices = list(range(len(turns)))
        
        # Create simple summary
        summary = f"Conversation with {len(turns)} turns discussing various topics."
        
        return TopicSegment(
            topic="General Discussion",
            summary=summary,
            key_points=["Fallback segmentation due to LLM failure"],
            turn_indices=indices,
            certainty=0.3,  # Low certainty for fallback
            impact=0.5,     # Medium impact (unknown)
            participant_count=len(participants),
            message_count=len(turns),
            temporal_context={}
        )
