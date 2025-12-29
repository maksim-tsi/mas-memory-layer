"""Test fact extraction with real supply chain document."""

import os
import asyncio
import json
from pathlib import Path

from src.utils.llm_client import LLMClient, ProviderConfig
from src.utils.providers import GeminiProvider
from src.memory.engines.fact_extractor import FactExtractor


async def test_fact_extraction_from_document():
    """Extract facts from supply chain optimization document."""
    
    # Load document
    doc_path = Path(__file__).parent / "fixtures/embedding_test_data/supply_chain_optimization.md"
    with open(doc_path, 'r') as f:
        content = f.read()
    
    # Take first 2000 characters for testing (avoid token limits)
    test_content = content[:2000]
    
    print("=" * 80)
    print("Testing Fact Extraction with Gemini Structured Output")
    print("=" * 80)
    print(f"\nDocument excerpt ({len(test_content)} chars):")
    print("-" * 80)
    print(test_content)
    print("-" * 80)
    
    # Setup LLM client with Gemini
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\n❌ GOOGLE_API_KEY not set. Skipping test.")
        return
    
    gemini = GeminiProvider(api_key=api_key)
    client = LLMClient()
    client.register_provider(
        gemini,
        ProviderConfig(name="google", priority=1, enabled=True)
    )
    
    # Create fact extractor
    extractor = FactExtractor(client, model_name="gemini-3-flash-preview")
    
    # Extract facts
    print("\n⚙️  Extracting facts with Gemini...")
    metadata = {"session_id": "test-doc", "source_uri": str(doc_path)}
    
    try:
        facts = await extractor.extract_facts(test_content, metadata)
        
        print(f"\n✅ Successfully extracted {len(facts)} facts!")
        print("=" * 80)
        
        for i, fact in enumerate(facts, 1):
            print(f"\nFact {i}:")
            print(f"  Content: {fact.content}")
            print(f"  Type: {fact.fact_type}")
            print(f"  Category: {fact.fact_category}")
            print(f"  Certainty: {fact.certainty:.2f}")
            print(f"  Impact: {fact.impact:.2f}")
            print(f"  CIAR Score: {fact.ciar_score:.3f}")
        
        # Export as JSON for inspection
        output_path = Path(__file__).parent.parent / "logs" / "fact_extraction_test.json"
        output_path.parent.mkdir(exist_ok=True)
        
        facts_json = [
            {
                "fact_id": f.fact_id,
                "content": f.content,
                "type": f.fact_type,
                "category": f.fact_category,
                "certainty": f.certainty,
                "impact": f.impact,
                "ciar_score": f.ciar_score,
            }
            for f in facts
        ]
        
        with open(output_path, 'w') as f:
            json.dump(facts_json, f, indent=2)
        
        print(f"\n📄 Full results written to: {output_path}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Fact extraction failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_fact_extraction_from_document())
