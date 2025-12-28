"""
Tests for TopicSegmenter component.

Tests the batch compression and topic segmentation functionality
per ADR-003 requirements.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.memory.engines.topic_segmenter import (
    TopicSegmenter,
    TopicSegment,
    TopicSegmentationError
)
from src.utils.llm_client import LLMClient


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = MagicMock(spec=LLMClient)
    return client


@pytest.fixture
def sample_turns():
    """Sample conversation turns for testing."""
    return [
        {
            "role": "user",
            "content": "What's the ETA for container MSCU1234567?",
            "timestamp": "2025-12-28T10:00:00Z"
        },
        {
            "role": "assistant",
            "content": "Let me check the tracking system for you.",
            "timestamp": "2025-12-28T10:00:05Z"
        },
        {
            "role": "assistant",
            "content": "Container MSCU1234567 is currently en route. ETA is December 30, 2025 at Port of Los Angeles.",
            "timestamp": "2025-12-28T10:00:10Z"
        },
        {
            "role": "user",
            "content": "Thanks! Also, can you send me the customs documentation?",
            "timestamp": "2025-12-28T10:01:00Z"
        },
        {
            "role": "assistant",
            "content": "I'll email the customs documentation to you within the next hour.",
            "timestamp": "2025-12-28T10:01:10Z"
        },
        {
            "role": "user",
            "content": "Perfect, thanks for your help!",
            "timestamp": "2025-12-28T10:01:20Z"
        },
        {
            "role": "assistant",
            "content": "You're welcome! Let me know if you need anything else.",
            "timestamp": "2025-12-28T10:01:25Z"
        },
        {
            "role": "user",
            "content": "Actually, I need to update the delivery address for this shipment.",
            "timestamp": "2025-12-28T10:02:00Z"
        },
        {
            "role": "assistant",
            "content": "I can help with that. What's the new delivery address?",
            "timestamp": "2025-12-28T10:02:05Z"
        },
        {
            "role": "user",
            "content": "New address is 123 Warehouse Lane, Commerce, CA 90040",
            "timestamp": "2025-12-28T10:02:20Z"
        }
    ]


@pytest.fixture
def mock_llm_response_multi_segment():
    """Mock LLM response with multiple segments."""
    mock_response = MagicMock()
    mock_response.text = '''```json
{
  "segments": [
    {
      "topic": "Container ETA Query",
      "summary": "User requested ETA for container MSCU1234567. Assistant provided ETA of Dec 30 at Port of LA.",
      "key_points": [
        "Container: MSCU1234567",
        "ETA: December 30, 2025",
        "Destination: Port of Los Angeles"
      ],
      "turn_indices": [0, 1, 2],
      "certainty": 0.9,
      "impact": 0.8,
      "participant_count": 2,
      "message_count": 3,
      "temporal_context": {"eta_date": "2025-12-30"}
    },
    {
      "topic": "Customs Documentation Request",
      "summary": "User requested customs documentation. Assistant committed to emailing within one hour.",
      "key_points": [
        "Documentation request: customs",
        "Delivery method: email",
        "Timeline: within one hour"
      ],
      "turn_indices": [3, 4, 5, 6],
      "certainty": 0.85,
      "impact": 0.7,
      "participant_count": 2,
      "message_count": 4,
      "temporal_context": {}
    },
    {
      "topic": "Delivery Address Update",
      "summary": "User requested to update delivery address to 123 Warehouse Lane, Commerce, CA 90040.",
      "key_points": [
        "Action: Update delivery address",
        "New address: 123 Warehouse Lane, Commerce, CA 90040",
        "Related shipment: MSCU1234567"
      ],
      "turn_indices": [7, 8, 9],
      "certainty": 0.95,
      "impact": 0.9,
      "participant_count": 2,
      "message_count": 3,
      "temporal_context": {}
    }
  ]
}
```'''
    return mock_response


@pytest.fixture
def mock_llm_response_single_segment():
    """Mock LLM response with single segment."""
    mock_response = MagicMock()
    mock_response.text = '''{
  "segments": [
    {
      "topic": "General Supply Chain Discussion",
      "summary": "Mixed conversation covering container tracking and documentation requests.",
      "key_points": ["Container tracking", "Documentation"],
      "turn_indices": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
      "certainty": 0.6,
      "impact": 0.5,
      "participant_count": 2,
      "message_count": 10
    }
  ]
}'''
    return mock_response


class TestTopicSegment:
    """Test TopicSegment data model."""
    
    def test_topic_segment_creation(self):
        """Test creating a valid TopicSegment."""
        segment = TopicSegment(
            topic="Container ETA Query",
            summary="User asked about container ETA.",
            key_points=["Container tracking", "ETA request"],
            turn_indices=[0, 1, 2],
            certainty=0.9,
            impact=0.8,
            participant_count=2,
            message_count=3
        )
        
        assert segment.topic == "Container ETA Query"
        assert segment.certainty == 0.9
        assert segment.impact == 0.8
        assert len(segment.turn_indices) == 3
        assert segment.segment_id  # Auto-generated UUID
    
    def test_topic_segment_validation_topic_too_short(self):
        """Test validation fails for topic that's too short."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            TopicSegment(
                topic="AB",  # Too short (< 3 chars)
                summary="This should fail validation.",
                certainty=0.5,
                impact=0.5
            )
    
    def test_topic_segment_validation_summary_too_short(self):
        """Test validation fails for summary that's too short."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            TopicSegment(
                topic="Valid Topic",
                summary="Short",  # Too short (< 10 chars)
                certainty=0.5,
                impact=0.5
            )


class TestTopicSegmenter:
    """Test TopicSegmenter functionality."""
    
    @pytest.mark.asyncio
    async def test_segmenter_initialization(self, mock_llm_client):
        """Test TopicSegmenter initialization."""
        segmenter = TopicSegmenter(
            llm_client=mock_llm_client,
            model_name="gemini-2.5-flash",
            min_turns=5,
            max_turns=15
        )
        
        assert segmenter.llm_client == mock_llm_client
        assert segmenter.model_name == "gemini-2.5-flash"
        assert segmenter.min_turns == 5
        assert segmenter.max_turns == 15
    
    @pytest.mark.asyncio
    async def test_segment_turns_below_minimum(self, mock_llm_client):
        """Test segmentation skips when turn count below minimum."""
        segmenter = TopicSegmenter(
            llm_client=mock_llm_client,
            min_turns=10
        )
        
        # Only 5 turns (below minimum of 10)
        few_turns = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "Good"},
            {"role": "user", "content": "Bye"}
        ]
        
        segments = await segmenter.segment_turns(few_turns)
        
        assert len(segments) == 0
        mock_llm_client.generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_segment_turns_empty_list(self, mock_llm_client):
        """Test segmentation with empty turn list."""
        segmenter = TopicSegmenter(llm_client=mock_llm_client)
        segments = await segmenter.segment_turns([])
        
        assert len(segments) == 0
        mock_llm_client.generate.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_segment_turns_multi_segment(
        self,
        mock_llm_client,
        sample_turns,
        mock_llm_response_multi_segment
    ):
        """Test successful multi-segment extraction."""
        mock_llm_client.generate = AsyncMock(return_value=mock_llm_response_multi_segment)
        
        segmenter = TopicSegmenter(
            llm_client=mock_llm_client,
            min_turns=5,
            max_turns=20
        )
        
        segments = await segmenter.segment_turns(sample_turns)
        
        assert len(segments) == 3
        
        # Verify first segment
        seg1 = segments[0]
        assert seg1.topic == "Container ETA Query"
        assert seg1.certainty == 0.9
        assert seg1.impact == 0.8
        assert seg1.turn_indices == [0, 1, 2]
        assert seg1.message_count == 3
        
        # Verify second segment
        seg2 = segments[1]
        assert seg2.topic == "Customs Documentation Request"
        assert seg2.certainty == 0.85
        assert seg2.impact == 0.7
        
        # Verify third segment
        seg3 = segments[2]
        assert seg3.topic == "Delivery Address Update"
        assert seg3.certainty == 0.95
        assert seg3.impact == 0.9
        
        # Verify LLM was called
        mock_llm_client.generate.assert_called_once()
        call_args = mock_llm_client.generate.call_args
        assert call_args.kwargs["model"] == "gemini-2.5-flash"
        assert call_args.kwargs["temperature"] == 0.3
    
    @pytest.mark.asyncio
    async def test_segment_turns_single_segment(
        self,
        mock_llm_client,
        sample_turns,
        mock_llm_response_single_segment
    ):
        """Test extraction with single segment."""
        mock_llm_client.generate = AsyncMock(return_value=mock_llm_response_single_segment)
        
        segmenter = TopicSegmenter(llm_client=mock_llm_client, min_turns=5)
        segments = await segmenter.segment_turns(sample_turns)
        
        assert len(segments) == 1
        assert segments[0].topic == "General Supply Chain Discussion"
        assert segments[0].certainty == 0.6
        assert segments[0].impact == 0.5
    
    @pytest.mark.asyncio
    async def test_segment_turns_llm_failure_fallback(
        self,
        mock_llm_client,
        sample_turns
    ):
        """Test fallback when LLM fails."""
        # Simulate LLM failure
        mock_llm_client.generate = AsyncMock(side_effect=Exception("LLM API error"))
        
        segmenter = TopicSegmenter(llm_client=mock_llm_client, min_turns=5)
        segments = await segmenter.segment_turns(sample_turns)
        
        # Should return single fallback segment
        assert len(segments) == 1
        assert segments[0].topic == "General Discussion"
        assert segments[0].certainty == 0.3  # Low certainty for fallback
        assert segments[0].impact == 0.5
        assert len(segments[0].turn_indices) == len(sample_turns)
    
    @pytest.mark.asyncio
    async def test_segment_turns_invalid_json_fallback(
        self,
        mock_llm_client,
        sample_turns
    ):
        """Test fallback when LLM returns invalid JSON."""
        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON at all!"
        mock_llm_client.generate = AsyncMock(return_value=mock_response)
        
        segmenter = TopicSegmenter(llm_client=mock_llm_client, min_turns=5)
        segments = await segmenter.segment_turns(sample_turns)
        
        # Should fallback to single segment
        assert len(segments) == 1
        assert segments[0].topic == "General Discussion"
    
    @pytest.mark.asyncio
    async def test_segment_turns_no_segments_in_response(
        self,
        mock_llm_client,
        sample_turns
    ):
        """Test fallback when LLM returns empty segments list."""
        mock_response = MagicMock()
        mock_response.text = '{"segments": []}'
        mock_llm_client.generate = AsyncMock(return_value=mock_response)
        
        segmenter = TopicSegmenter(llm_client=mock_llm_client, min_turns=5)
        segments = await segmenter.segment_turns(sample_turns)
        
        assert len(segments) == 1
        assert segments[0].topic == "General Discussion"
    
    @pytest.mark.asyncio
    async def test_segment_turns_truncates_if_exceeds_max(
        self,
        mock_llm_client,
        mock_llm_response_single_segment
    ):
        """Test that turns exceeding max_turns are truncated."""
        mock_llm_client.generate = AsyncMock(return_value=mock_llm_response_single_segment)
        
        segmenter = TopicSegmenter(
            llm_client=mock_llm_client,
            min_turns=5,
            max_turns=8
        )
        
        # Create 10 turns (exceeds max of 8)
        many_turns = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(10)
        ]
        
        segments = await segmenter.segment_turns(many_turns)
        
        # Should still work (truncated to 8 most recent)
        assert len(segments) == 1
        mock_llm_client.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_format_conversation(self, mock_llm_client, sample_turns):
        """Test conversation formatting for LLM."""
        segmenter = TopicSegmenter(llm_client=mock_llm_client)
        formatted = segmenter._format_conversation(sample_turns)
        
        # Check formatting includes indices and roles
        assert "[0] User" in formatted
        assert "[1] Assistant" in formatted
        assert "MSCU1234567" in formatted
        assert "customs documentation" in formatted.lower()
    
    @pytest.mark.asyncio
    async def test_create_fallback_segment(self, mock_llm_client, sample_turns):
        """Test fallback segment creation."""
        segmenter = TopicSegmenter(llm_client=mock_llm_client)
        segment = segmenter._create_fallback_segment(sample_turns)
        
        assert segment.topic == "General Discussion"
        assert segment.certainty == 0.3
        assert segment.impact == 0.5
        assert segment.participant_count == 2  # user and assistant
        assert segment.message_count == len(sample_turns)
        assert len(segment.turn_indices) == len(sample_turns)
        assert "Fallback segmentation" in segment.key_points[0]
