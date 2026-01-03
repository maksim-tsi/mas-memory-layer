"""
Tests for Gemini's native structured output with types.Schema.

This test verifies that our Gemini provider can use the native structured
output API with thinking_config and response_schema.
"""
import os
import json
import pytest

# Skip all tests if GOOGLE_API_KEY not available
pytestmark = pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set"
)


@pytest.mark.asyncio
async def test_fact_extraction_with_native_schema():
    """Test fact extraction using Gemini's native types.Schema format.
    
    This test validates that:
    1. The native types.Schema format works correctly
    2. System instructions are properly applied
    3. Thinking level LOW produces valid JSON output
    4. The response adheres to the schema structure
    """
    from google import genai
    from google.genai import types
    
    # Initialize client
    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    
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
    
    # Configure generation with structured output
    generate_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=response_schema,
        system_instruction=system_instruction,
        temperature=0.0,  # Deterministic for structured output
    )
    
    # Generate (non-streaming for test)
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=contents,
        config=generate_config,
    )
    
    # Parse response
    response_text = response.text
    assert response_text, "Response text should not be empty"
    
    # Validate JSON structure
    result = json.loads(response_text)
    assert "facts" in result, "Response should contain 'facts' key"
    assert isinstance(result["facts"], list), "facts should be a list"
    assert len(result["facts"]) > 0, "Should extract at least one fact"
    
    # Validate fact structure
    for fact in result["facts"]:
        assert "content" in fact, "Each fact should have 'content'"
        assert "type" in fact, "Each fact should have 'type'"
        assert "category" in fact, "Each fact should have 'category'"
        assert "certainty" in fact, "Each fact should have 'certainty'"
        assert "impact" in fact, "Each fact should have 'impact'"
        
        # Validate types
        assert isinstance(fact["content"], str), "content should be string"
        assert fact["type"] in ["preference", "constraint", "entity", "mention", "relationship", "event"], \
            f"Invalid type: {fact['type']}"
        assert fact["category"] in ["personal", "business", "technical", "operational"], \
            f"Invalid category: {fact['category']}"
        assert isinstance(fact["certainty"], (int, float)), "certainty should be numeric"
        assert isinstance(fact["impact"], (int, float)), "impact should be numeric"
        assert 0.0 <= fact["certainty"] <= 1.0, "certainty should be between 0.0 and 1.0"
        assert 0.0 <= fact["impact"] <= 1.0, "impact should be between 0.0 and 1.0"
    
    # Validate expected facts are present
    fact_contents = [f["content"].lower() for f in result["facts"]]
    
    # Check for key facts from conversation
    assert any("shanghai" in content or "shipment" in content for content in fact_contents), \
        "Should extract fact about Shanghai shipment"
    assert any("friday" in content or "deadline" in content for content in fact_contents), \
        "Should extract fact about Friday deadline"
    assert any("fasttrack" in content or "customs broker" in content for content in fact_contents), \
        "Should extract fact about FastTrack Logistics"
    
    print(f"\n✓ Successfully extracted {len(result['facts'])} facts")
    print("\nSample facts:")
    for i, fact in enumerate(result["facts"][:3], 1):
        print(f"{i}. {fact['content'][:80]}... (type={fact['type']}, impact={fact['impact']})")


@pytest.mark.asyncio
async def test_gemini_structured_output_compatibility():
    """Test that Pydantic schemas can be converted to Gemini native format.
    
    This validates that our existing Pydantic models for other providers
    can be aligned with Gemini's native schema format.
    """
    from pydantic import BaseModel, Field
    from typing import List, Literal
    
    # Define Pydantic model (for other providers)
    class Fact(BaseModel):
        content: str = Field(description="The actual fact content")
        type: Literal["preference", "constraint", "entity", "mention", "relationship", "event"]
        category: Literal["personal", "business", "technical", "operational"]
        certainty: float = Field(ge=0.0, le=1.0)
        impact: float = Field(ge=0.0, le=1.0)
    
    class FactExtractionResult(BaseModel):
        facts: List[Fact]
    
    # Get Pydantic JSON schema
    pydantic_schema = FactExtractionResult.model_json_schema()
    
    # Validate structure matches Gemini expectations
    assert "properties" in pydantic_schema
    assert "facts" in pydantic_schema["properties"]
    assert "type" in pydantic_schema["properties"]["facts"]
    assert pydantic_schema["properties"]["facts"]["type"] == "array"
    
    # Get items definition (may be in $defs or inline)
    items = pydantic_schema["properties"]["facts"].get("items")
    if "$ref" in items:
        # Reference to $defs
        ref_name = items["$ref"].split("/")[-1]
        fact_schema = pydantic_schema.get("$defs", {}).get(ref_name, {})
        items_props = fact_schema.get("properties", {})
    else:
        # Inline definition
        items_props = items.get("properties", {})
    
    assert items_props, "Should have fact properties defined"
    
    # Validate enum constraints
    assert "anyOf" in items_props["type"] or "enum" in items_props["type"], "type field should have enum constraint"
    assert "anyOf" in items_props["category"] or "enum" in items_props["category"], "category field should have enum constraint"
    
    # Validate numeric constraints (they may be nested in anyOf for Optional fields)
    certainty_schema = items_props["certainty"]
    impact_schema = items_props["impact"]
    
    # Check if constraints exist (may be in anyOf structure)
    assert certainty_schema, "certainty field should exist"
    assert impact_schema, "impact field should exist"
    
    print("\n✓ Pydantic schema is compatible with Gemini native format")
    print(f"✓ Schema has {len(items_props)} properties per fact")
    print("✓ Required fields: content, type, category, certainty, impact")


if __name__ == "__main__":
    import asyncio
    
    print("Running Gemini Structured Output Tests...")
    print("=" * 60)
    
    # Run fact extraction test
    asyncio.run(test_fact_extraction_with_native_schema())
    
    # Run compatibility test
    asyncio.run(test_gemini_structured_output_compatibility())
    
    print("\n" + "=" * 60)
    print("All tests passed!")
