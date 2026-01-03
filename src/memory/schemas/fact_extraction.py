"""Fact extraction schema and system instruction for Gemini structured output."""

from google.genai import types

FACT_EXTRACTION_SYSTEM_INSTRUCTION = """You are an expert fact extractor for a supply chain memory system.

Your task: Extract significant facts from conversation turns.

For each fact, you must identify:
- content: The actual fact content, written as a complete statement
- type: One of [preference, constraint, entity, mention, relationship, event]
- category: One of [personal, business, technical, operational]
- certainty: Your confidence in this fact's accuracy (0.0-1.0)
- impact: Estimated importance/urgency (0.0-1.0)

Guidelines:
- preference: User likes/dislikes
- constraint: Limitations or requirements
- entity: Person, place, thing, or organization
- mention: Reference to something
- relationship: Connection between entities
- event: Something that happened or will happen

Impact scoring:
- High (0.7-1.0): Critical decisions, urgent requests, cancellation threats
- Medium (0.4-0.7): Status updates, process changes
- Low (0.0-0.4): Routine information, acknowledgments"""

FACT_EXTRACTION_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["facts"],
    properties={
        "facts": types.Schema(
            type=types.Type.ARRAY,
            description="List of extracted facts from the conversation.",
            items=types.Schema(
                type=types.Type.OBJECT,
                required=["content", "type", "category", "certainty", "impact"],
                properties={
                    "content": types.Schema(
                        type=types.Type.STRING,
                        description="The actual fact content, written as a complete statement.",
                    ),
                    "type": types.Schema(
                        type=types.Type.STRING,
                        description="Type of fact: preference (user likes/dislikes), constraint (limitation/requirement), entity (person/place/thing), mention (reference to something), relationship (connection between entities), event (something that happened).",
                        enum=["preference", "constraint", "entity", "mention", "relationship", "event"],
                    ),
                    "category": types.Schema(
                        type=types.Type.STRING,
                        description="Category: personal (individual preferences), business (company/process), technical (software/hardware), operational (day-to-day activities).",
                        enum=["personal", "business", "technical", "operational"],
                    ),
                    "certainty": types.Schema(
                        type=types.Type.NUMBER,
                        description="Confidence in this fact's accuracy, from 0.0 (uncertain) to 1.0 (certain).",
                    ),
                    "impact": types.Schema(
                        type=types.Type.NUMBER,
                        description="Estimated importance/urgency of this fact, from 0.0 (low) to 1.0 (critical).",
                    ),
                },
            ),
        ),
    },
)
