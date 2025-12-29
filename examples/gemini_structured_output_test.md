# Gemini Structured Output Test Examples

This document contains test cases for validating Gemini's structured output with our memory system schemas.

## Test 1: Fact Extraction

### Pydantic Models

```python
from google import genai
from pydantic import BaseModel, Field
from typing import List, Literal

class Fact(BaseModel):
    """A single extracted fact from conversation."""
    content: str = Field(description="The actual fact content, written as a complete statement.")
    type: Literal["preference", "constraint", "entity", "mention", "relationship", "event"] = Field(
        description="Type of fact: preference (user likes/dislikes), constraint (limitation/requirement), "
                    "entity (person/place/thing), mention (reference to something), relationship (connection between entities), "
                    "event (something that happened)."
    )
    category: Literal["personal", "business", "technical", "operational"] = Field(
        description="Category: personal (individual preferences), business (company/process), "
                    "technical (software/hardware), operational (day-to-day activities)."
    )
    certainty: float = Field(
        description="Confidence in this fact's accuracy, from 0.0 (uncertain) to 1.0 (certain).",
        ge=0.0,
        le=1.0
    )
    impact: float = Field(
        description="Estimated importance/urgency of this fact, from 0.0 (low) to 1.0 (critical).",
        ge=0.0,
        le=1.0
    )

class FactExtractionResult(BaseModel):
    """Result of fact extraction from conversation turns."""
    facts: List[Fact] = Field(description="List of extracted facts from the conversation.")
```

### JSON Schema (Generated from Pydantic)

This is the JSON schema that Gemini will use to structure its output:

```json
{
  "type": "object",
  "properties": {
    "facts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "content": {
            "type": "string",
            "description": "The actual fact content, written as a complete statement."
          },
          "type": {
            "type": "string",
            "enum": ["preference", "constraint", "entity", "mention", "relationship", "event"],
            "description": "Type of fact: preference (user likes/dislikes), constraint (limitation/requirement), entity (person/place/thing), mention (reference to something), relationship (connection between entities), event (something that happened)."
          },
          "category": {
            "type": "string",
            "enum": ["personal", "business", "technical", "operational"],
            "description": "Category: personal (individual preferences), business (company/process), technical (software/hardware), operational (day-to-day activities)."
          },
          "certainty": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence in this fact's accuracy, from 0.0 (uncertain) to 1.0 (certain)."
          },
          "impact": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Estimated importance/urgency of this fact, from 0.0 (low) to 1.0 (critical)."
          }
        },
        "required": ["content", "type", "category", "certainty", "impact"]
      },
      "description": "List of extracted facts from the conversation."
    }
  },
  "required": ["facts"]
}
```

### Working Code Example (Verified with Google AI Studio)

```python
import os
from google import genai
from google.genai import types

# Initialize client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# User content (conversation to analyze)
user_content = """Extract significant facts from the following supply chain conversation:

[2024-12-15 09:30] Alice: Hi team, we need to expedite the Shanghai shipment. Customer XYZ is threatening to cancel if we don't deliver by Friday.

[2024-12-15 09:32] Bob: I checked with the warehouse. The container is ready, but we're waiting on customs clearance.

[2024-12-15 09:35] Alice: Can we use the express customs broker we used last month? They were much faster.

[2024-12-15 09:37] Bob: Good idea. I'll contact them immediately. Their name is FastTrack Logistics.

[2024-12-15 09:40] Alice: Perfect. Also, please update the ETA in our system to Friday 17:00 and notify the customer.

Extract all significant facts including preferences, constraints, entities, relationships, and events."""

# Build content with proper types
contents = [
    types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_content)],
    ),
]

# Define response schema using native Gemini types
response_schema = types.Schema(
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

# System instruction as Parts (task-specific)
system_instruction = [
    types.Part.from_text(text="""You are an expert fact extractor for a supply chain memory system.

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
- Low (0.0-0.4): Routine information, acknowledgments"""),
]

# Configure generation with thinking level
generate_config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(
        thinking_level="LOW",  # Use LOW for fast/easy tasks, MEDIUM or HIGH for complex reasoning
    ),
    response_mime_type="application/json",
    response_schema=response_schema,
    system_instruction=system_instruction,
    temperature=0.0,  # Deterministic for structured output
)

# Generate (streaming)
response_text = ""
for chunk in client.models.generate_content_stream(
    model="gemini-3-flash-preview",
    contents=contents,
    config=generate_config,
):
    response_text += chunk.text
    print(chunk.text, end="")

print("\n\n--- Parsed Result ---")
import json
result = json.loads(response_text)
print(json.dumps(result, indent=2))
```

### Expected Output Structure

```json
{
  "facts": [
    {
      "content": "Shanghai shipment needs to be expedited to prevent customer XYZ cancellation",
      "type": "event",
      "category": "operational",
      "certainty": 1.0,
      "impact": 0.95
    },
    {
      "content": "Delivery deadline is Friday",
      "type": "constraint",
      "category": "operational",
      "certainty": 1.0,
      "impact": 0.9
    },
    {
      "content": "Container is ready at warehouse",
      "type": "event",
      "category": "operational",
      "certainty": 1.0,
      "impact": 0.5
    },
    {
      "content": "Shipment is waiting on customs clearance",
      "type": "constraint",
      "category": "operational",
      "certainty": 1.0,
      "impact": 0.8
    },
    {
      "content": "Alice prefers using the express customs broker from last month",
      "type": "preference",
      "category": "operational",
      "certainty": 0.9,
      "impact": 0.7
    },
    {
      "content": "FastTrack Logistics is the express customs broker",
      "type": "entity",
      "category": "business",
      "certainty": 1.0,
      "impact": 0.6
    },
    {
      "content": "ETA should be updated to Friday 17:00 in the system",
      "type": "constraint",
      "category": "operational",
      "certainty": 1.0,
      "impact": 0.7
    }
  ]
}
```

---

## Test 2: Topic Segmentation

### Pydantic Models

```python
from google import genai
from pydantic import BaseModel, Field
from typing import List

class TopicSegment(BaseModel):
    """A coherent topic segment from conversation."""
    topic: str = Field(
        description="Brief descriptive label for this topic (3-50 words).",
        min_length=3,
        max_length=200
    )
    summary: str = Field(
        description="Concise narrative of what was discussed in this segment (50-500 words).",
        min_length=50,
        max_length=2000
    )
    key_points: List[str] = Field(
        description="List of 3-10 significant points from this segment.",
        min_length=3,
        max_length=10
    )
    turn_indices: List[int] = Field(
        description="Zero-based indices of conversation turns belonging to this segment."
    )
    certainty: float = Field(
        description="Confidence in this segmentation, from 0.0 (uncertain) to 1.0 (certain).",
        ge=0.0,
        le=1.0
    )
    impact: float = Field(
        description="Estimated importance/urgency of this topic, from 0.0 (low) to 1.0 (critical). "
                    "High (0.7-1.0): urgent requests, critical alerts, decisions. "
                    "Medium (0.4-0.7): informational queries, status updates. "
                    "Low (0.0-0.4): casual discussion, small talk.",
        ge=0.0,
        le=1.0
    )
    participant_count: int = Field(
        description="Number of distinct speakers in this segment.",
        ge=1
    )
    message_count: int = Field(
        description="Number of messages in this segment.",
        ge=1
    )
    temporal_context: str = Field(
        description="Any dates, times, or deadlines mentioned in this segment. Empty string if none.",
        default=""
    )

class TopicSegmentationResult(BaseModel):
    """Result of segmenting conversation into coherent topics."""
    segments: List[TopicSegment] = Field(
        description="List of topic segments identified in the conversation."
    )
```

### JSON Schema (Generated from Pydantic)

This is the JSON schema that Gemini will use to structure its output:

```json
{
  "type": "object",
  "properties": {
    "segments": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "topic": {
            "type": "string",
            "minLength": 3,
            "maxLength": 200,
            "description": "Brief descriptive label for this topic (3-50 words)."
          },
          "summary": {
            "type": "string",
            "minLength": 50,
            "maxLength": 2000,
            "description": "Concise narrative of what was discussed in this segment (50-500 words)."
          },
          "key_points": {
            "type": "array",
            "items": {
              "type": "string"
            },
            "minItems": 3,
            "maxItems": 10,
            "description": "List of 3-10 significant points from this segment."
          },
          "turn_indices": {
            "type": "array",
            "items": {
              "type": "integer"
            },
            "description": "Zero-based indices of conversation turns belonging to this segment."
          },
          "certainty": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence in this segmentation, from 0.0 (uncertain) to 1.0 (certain)."
          },
          "impact": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Estimated importance/urgency of this topic, from 0.0 (low) to 1.0 (critical). High (0.7-1.0): urgent requests, critical alerts, decisions. Medium (0.4-0.7): informational queries, status updates. Low (0.0-0.4): casual discussion, small talk."
          },
          "participant_count": {
            "type": "integer",
            "minimum": 1,
            "description": "Number of distinct speakers in this segment."
          },
          "message_count": {
            "type": "integer",
            "minimum": 1,
            "description": "Number of messages in this segment."
          },
          "temporal_context": {
            "type": "string",
            "description": "Any dates, times, or deadlines mentioned in this segment. Empty string if none."
          }
        },
        "required": ["topic", "summary", "key_points", "turn_indices", "certainty", "impact", "participant_count", "message_count", "temporal_context"]
      },
      "description": "List of topic segments identified in the conversation."
    }
  },
  "required": ["segments"]
}
```

### System Instruction & User Prompt

```python
client = genai.Client()

# System instruction (separate from user content)
system_instruction = """You are an expert at analyzing supply chain and logistics conversations.

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

# User prompt (actual conversation to process)
user_prompt = """Segment the following supply chain conversation into coherent topics:

[Turn 0] [2024-12-15 09:00] Alice: Good morning team! Hope everyone had a great weekend.

[Turn 1] [2024-12-15 09:02] Bob: Morning Alice! Yes, was very relaxing.

[Turn 2] [2024-12-15 09:05] Alice: Alright, let's get to business. We have a critical situation with the Shanghai shipment. Customer XYZ is threatening to cancel their order if we don't deliver by this Friday.

[Turn 3] [2024-12-15 09:07] Bob: That's concerning. Let me check the status. One moment.

[Turn 4] [2024-12-15 09:10] Bob: I've checked with the warehouse. The container is packed and ready, but we're stuck waiting for customs clearance. It's been in queue for 3 days now.

[Turn 5] [2024-12-15 09:12] Alice: Three days is way too long. Can we escalate this? What about that express customs broker we used last month for the emergency shipment?

[Turn 6] [2024-12-15 09:15] Bob: Good thinking! That was FastTrack Logistics. They cleared that shipment in under 24 hours. I'll contact them right away.

[Turn 7] [2024-12-15 09:17] Alice: Perfect. Please also update the ETA in our tracking system to Friday 17:00 and send a proactive notification to customer XYZ. We need to manage their expectations.

[Turn 8] [2024-12-15 09:20] Bob: Will do. I'm also going to loop in the warehouse manager to ensure they're ready to load immediately once we get clearance.

[Turn 9] [2024-12-15 09:25] Alice: Excellent. On a different note, have you seen the new inventory dashboard? IT deployed it last night.

[Turn 10] [2024-12-15 09:27] Bob: Yes! The real-time stock levels are much more accurate now. It's showing we're low on component SKU-8472.

[Turn 11] [2024-12-15 09:30] Alice: That's the microcontroller for the production line, right? We should reorder immediately. Can you create a PO for 5000 units?

[Turn 12] [2024-12-15 09:32] Bob: On it. I'll also check if we can get expedited shipping on that since we're running low.

"""

response = client.models.generate_content(
    model="gemini-3-flash-preview",  # Use gemini-3 family
    contents=user_prompt,  # User content only
    config={
        "system_instruction": system_instruction,  # System instruction in config
        "response_mime_type": "application/json",
        "response_json_schema": TopicSegmentationResult.model_json_schema(),
    },
)

result = TopicSegmentationResult.model_validate_json(response.text)
print(result.model_dump_json(indent=2))
```

### Expected Output Structure

```json
{
  "segments": [
    {
      "topic": "Critical Shanghai shipment delay and customs clearance escalation",
      "summary": "Customer XYZ is threatening to cancel their order due to delayed Shanghai shipment. The container is ready but stuck in customs for 3 days. Team decides to use FastTrack Logistics, an express customs broker previously used for emergency shipments, to expedite clearance. Alice requests updating the ETA to Friday 17:00 and notifying the customer proactively.",
      "key_points": [
        "Customer XYZ threatening cancellation if delivery not made by Friday",
        "Container ready but waiting 3 days for customs clearance",
        "Decision to use FastTrack Logistics express broker (cleared previous shipment in under 24 hours)",
        "ETA to be updated to Friday 17:00 with proactive customer notification",
        "Warehouse manager to be looped in for immediate loading post-clearance"
      ],
      "turn_indices": [2, 3, 4, 5, 6, 7, 8],
      "certainty": 0.95,
      "impact": 0.95,
      "participant_count": 2,
      "message_count": 7,
      "temporal_context": "Delivery deadline: Friday; Current delay: 3 days in customs; Target ETA: Friday 17:00"
    },
    {
      "topic": "Inventory management: Low stock on SKU-8472 microcontroller",
      "summary": "Discussion about new inventory dashboard deployed by IT. Real-time stock levels show component SKU-8472 (microcontroller for production line) is running low. Bob assigned to create purchase order for 5000 units with expedited shipping due to low inventory levels.",
      "key_points": [
        "New inventory dashboard deployed with improved real-time accuracy",
        "Component SKU-8472 (microcontroller) stock level is low",
        "Purchase order to be created for 5000 units",
        "Expedited shipping requested due to low inventory"
      ],
      "turn_indices": [9, 10, 11, 12],
      "certainty": 0.9,
      "impact": 0.75,
      "participant_count": 2,
      "message_count": 4,
      "temporal_context": "Dashboard deployed last night"
    }
  ]
}
```

---

## Instructions for Testing

1. **Install the new Gemini SDK**:
   ```bash
   pip install google-genai
   ```

2. **Set your API key**:
   ```bash
   export GEMINI_API_KEY="your-api-key"
   ```

3. **Run the test script**:
   - Copy the working code example above into a Python file
   - Run and observe the structured JSON output

4. **Key Configuration Options**:
   - **Temperature**: Use `0.0` for deterministic structured output
   - **Task-Specific Configs**: Each engine should have its own system instruction and schema
   - **Note**: `ThinkingConfig` only supports `include_thoughts` (bool), not `thinking_level` parameter

## Implementation Guidelines for Production

### 1. Task-Specific System Instructions

Create separate system instructions for each memory engine task:

| Task | System Instruction | Configuration |
|------|-------------------|---------------|
| Fact Extraction | Extract facts with CIAR scoring | temperature=0.0, max_output_tokens=8192 |
| Topic Segmentation | Segment conversation into coherent topics | temperature=0.0, max_output_tokens=8192 |
| Episode Consolidation | Cluster related facts into narrative episodes | temperature=0.2, max_output_tokens=16384 |
| Knowledge Synthesis | Distill patterns from multiple episodes | temperature=0.3, max_output_tokens=32768 |

### 2. Native Schema Format

Use `genai.types.Schema` instead of Pydantic `model_json_schema()`:

```python
# Instead of:
"response_json_schema": FactExtractionResult.model_json_schema()

# Use:
response_schema = types.Schema(
    type=types.Type.OBJECT,
    required=["facts"],
    properties={
        "facts": types.Schema(
            type=types.Type.ARRAY,
            items=...
        )
    }
)
```

### 3. Update GeminiProvider

The `GeminiProvider` class needs these enhancements:

```python
async def generate(
    self,
    prompt: str,
    model: Optional[str] = None,
    system_instruction: Optional[str] = None,
    thinking_level: Optional[str] = "LOW",  # LOW, MEDIUM, HIGH
    response_schema: Optional[types.Schema] = None,
    **kwargs
) -> LLMResponse:
    """Generate with structured output support."""
    from google.genai import types
    
    model = model or "gemini-3-flash-preview"
    
    # Build content
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        )
    ]
    
    # Build config
    config_params = {
        "temperature": kwargs.get("temperature", 0.0),
        "max_output_tokens": kwargs.get("max_output_tokens", 8192),
    }
    
    # Note: ThinkingConfig only supports include_thoughts (bool), not thinking_level
    # For controlling reasoning depth, use temperature and max_output_tokens instead
    
    # Add system instruction
    if system_instruction:
        config_params["system_instruction"] = [
            types.Part.from_text(text=system_instruction)
        ]
    
    # Add structured output
    if response_schema:
        config_params["response_mime_type"] = "application/json"
        config_params["response_schema"] = response_schema
    
    config = types.GenerateContentConfig(**config_params)
    
    # Generate (non-streaming for now)
    def sync_call():
        return self.client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
    
    response = await asyncio.to_thread(sync_call)
    # ... rest of implementation
```

### 4. Engine-Specific Schemas

Create schema definitions in `src/memory/schemas/` directory:

```
src/memory/schemas/
  ├── __init__.py
  ├── fact_extraction.py      # Fact schema + system instruction
  ├── topic_segmentation.py   # Segment schema + system instruction
  ├── consolidation.py        # Episode schema + system instruction
  └── synthesis.py            # Knowledge schema + system instruction
```

Each file exports:
- `SYSTEM_INSTRUCTION`: Task-specific prompt
- `RESPONSE_SCHEMA`: Native Gemini schema
- `THINKING_LEVEL`: Recommended level

## Notes

- Model name: `gemini-3-flash-preview` for production (64K output tokens)
- Use `gemini-3-pro-preview` only for complex reasoning requiring multimodal capabilities
- The native `types.Schema` format is required for Gemini's structured output
- Thinking level controls speed vs reasoning depth tradeoff
- System instructions passed as array of `types.Part` objects
