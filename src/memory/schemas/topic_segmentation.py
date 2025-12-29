"""Topic segmentation schema and system instruction for Gemini structured output."""

from google.genai import types

TOPIC_SEGMENTATION_SYSTEM_INSTRUCTION = """You are an expert at analyzing supply chain and logistics conversations.

Your task: Segment a batch of conversation turns into coherent topics.

For each segment, you must extract:
- topic: Brief descriptive label (3-50 words)
- summary: Concise narrative of what was discussed (50-500 words)
- key_points: List of 3-10 significant points from the segment
- turn_indices: Zero-based indices of turns belonging to this segment
- certainty: Your confidence in this segmentation (0.0-1.0)
- impact: Estimated importance/urgency of this topic (0.0-1.0)
- participant_count: Number of distinct speakers
- message_count: Number of messages in segment
- temporal_context: Any dates, times, deadlines mentioned

Guidelines:
- Compress noise: Skip greetings, acknowledgments, filler conversation
- Merge related sub-topics into one coherent segment
- Assign high impact (0.7-1.0) to: urgent requests, critical alerts, decisions, commitments
- Assign medium impact (0.4-0.7) to: informational queries, status updates
- Assign low impact (0.0-0.4) to: casual discussion, small talk
- Base certainty on: clarity of topic, coherence of discussion"""

TOPIC_SEGMENTATION_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["segments"],
    properties={
        "segments": types.Schema(
            type=types.Type.ARRAY,
            description="List of topic segments identified in the conversation.",
            items=types.Schema(
                type=types.Type.OBJECT,
                required=["topic", "summary", "key_points", "turn_indices", "certainty", "impact", "participant_count", "message_count", "temporal_context"],
                properties={
                    "topic": types.Schema(
                        type=types.Type.STRING,
                        description="Brief descriptive label for this topic (3-50 words).",
                    ),
                    "summary": types.Schema(
                        type=types.Type.STRING,
                        description="Concise narrative of what was discussed in this segment (50-500 words).",
                    ),
                    "key_points": types.Schema(
                        type=types.Type.ARRAY,
                        description="List of 3-10 significant points from this segment.",
                        items=types.Schema(type=types.Type.STRING),
                    ),
                    "turn_indices": types.Schema(
                        type=types.Type.ARRAY,
                        description="Zero-based indices of conversation turns belonging to this segment.",
                        items=types.Schema(type=types.Type.NUMBER),
                    ),
                    "certainty": types.Schema(
                        type=types.Type.NUMBER,
                        description="Confidence in this segmentation, from 0.0 (uncertain) to 1.0 (certain).",
                    ),
                    "impact": types.Schema(
                        type=types.Type.NUMBER,
                        description="Estimated importance/urgency of this topic, from 0.0 (low) to 1.0 (critical).",
                    ),
                    "participant_count": types.Schema(
                        type=types.Type.NUMBER,
                        description="Number of distinct speakers in this segment.",
                    ),
                    "message_count": types.Schema(
                        type=types.Type.NUMBER,
                        description="Number of messages in this segment.",
                    ),
                    "temporal_context": types.Schema(
                        type=types.Type.STRING,
                        description="Any dates, times, or deadlines mentioned in this segment. Empty string if none.",
                    ),
                },
            ),
        ),
    },
)
