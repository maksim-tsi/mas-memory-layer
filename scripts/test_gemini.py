#!/usr/bin/env python3
"""
Test Google Gemini API connectivity and basic chat completion.

This script validates:
- API key is loaded correctly
- Gemini API is accessible
- Basic chat completion works
- Token usage tracking
- Multiple model variants (2.5 Flash, 2.0 Flash, 2.5 Flash-Lite)
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

def test_model(client, model_name: str, description: str) -> bool:
    """Test a specific Gemini model variant."""
    print(f"\n{'='*60}")
    print(f"Testing {description}")
    print(f"Model: {model_name}")
    print(f"{'='*60}")
    
    try:
        # Test basic chat completion
        print("\n1. Testing basic chat completion...")
        test_prompt = "What is 2+2? Answer in one short sentence."
        
        response = client.models.generate_content(
            model=model_name,
            contents=test_prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=100,
            )
        )
        
        print(f"   ✓ Response received")
        print(f"   Prompt: {test_prompt}")
        print(f"   Response: {response.text}")
        
        # Check usage statistics
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            print(f"\n2. Token Usage:")
            print(f"   Prompt tokens: {usage.prompt_token_count}")
            print(f"   Response tokens: {usage.candidates_token_count}")
            print(f"   Total tokens: {usage.total_token_count}")
        
        # Test with system instruction
        print("\n3. Testing with system instruction...")
        response = client.models.generate_content(
            model=model_name,
            contents="Explain memory systems in one sentence.",
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=50,
                system_instruction="You are a concise expert in AI memory architectures.",
            )
        )
        print(f"   ✓ Response: {response.text}")
        
        print(f"\n✅ {description} test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR testing {description}: {type(e).__name__}")
        print(f"   {str(e)}")
        return False

def test_gemini():
    """Test all Gemini model variants."""
    
    print("=" * 60)
    print("Testing Google Gemini API (Multi-Model)")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not found in .env")
        print("   Get your API key from: https://ai.google.dev/")
        print("\n   Setup instructions:")
        print("   1. Visit https://aistudio.google.com/app/apikey")
        print("   2. Create a new API key")
        print("   3. Add to .env file: GOOGLE_API_KEY=your_key_here")
        return False
    
    print(f"✓ API key loaded: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        # Initialize client
        print("\nInitializing Gemini client...")
        client = genai.Client(api_key=api_key)
        print("✓ Client initialized")
        
        # Test each model variant
        models = [
            ("gemini-2.5-flash", "Gemini 2.5 Flash (Primary - Complex Tasks)"),
            ("gemini-2.0-flash-exp", "Gemini 2.0 Flash (High-Volume Tasks)"),
            ("gemini-2.5-flash-lite", "Gemini 2.5 Flash-Lite (Fast Tasks)"),
        ]
        
        results = {}
        for model_name, description in models:
            results[model_name] = test_model(client, model_name, description)
        
        # Summary
        print("\n" + "=" * 60)
        print("GEMINI TEST SUMMARY")
        print("=" * 60)
        
        for model_name, description in models:
            status = "✅ PASSED" if results[model_name] else "❌ FAILED"
            print(f"{status} - {description}")
        
        print("\n" + "=" * 60)
        print("Rate Limits (Free Tier - Per Model):")
        print("  Gemini 2.5 Flash:")
        print("    • 10 requests per minute")
        print("    • 250,000 tokens per minute")
        print("    • 1,000,000 token context window")
        print("  Gemini 2.0 Flash:")
        print("    • 15 requests per minute")
        print("    • 1,000,000 tokens per minute")
        print("    • 1,000,000 token context window")
        print("  Gemini 2.5 Flash-Lite:")
        print("    • 15 requests per minute")
        print("    • 250,000 tokens per minute")
        print("    • 1,000,000 token context window")
        print("=" * 60)
        
        return all(results.values())
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}")
        print(f"   {str(e)}")
        return False

if __name__ == "__main__":
    success = test_gemini()
    sys.exit(0 if success else 1)
