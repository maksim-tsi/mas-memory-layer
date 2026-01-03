#!/usr/bin/env python3
"""
Test Mistral AI API connectivity and basic chat completion.

This script validates:
- API key is loaded correctly
- Mistral API is accessible
- Basic chat completion works
- Token usage tracking
- Multiple model variants (Large, Small)
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from mistralai import Mistral

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

def test_model(client, model_name: str, description: str) -> bool:
    """Test a specific Mistral model variant."""
    print(f"\n{'='*60}")
    print(f"Testing {description}")
    print(f"Model: {model_name}")
    print(f"{'='*60}")
    
    try:
        # Test basic chat completion
        print("\n1. Testing basic chat completion...")
        test_prompt = "What is 2+2? Answer in one short sentence."
        
        response = client.chat.complete(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": test_prompt
                }
            ],
            temperature=0.0,
            max_tokens=100,
        )
        
        print("   ✓ Response received")
        print(f"   Prompt: {test_prompt}")
        print(f"   Response: {response.choices[0].message.content}")
        
        # Check usage statistics
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            print("\n2. Token Usage:")
            print(f"   Prompt tokens: {usage.prompt_tokens}")
            print(f"   Response tokens: {usage.completion_tokens}")
            print(f"   Total tokens: {usage.total_tokens}")
        
        # Test with system message
        print("\n3. Testing with system message...")
        response = client.chat.complete(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise expert in AI memory architectures."
                },
                {
                    "role": "user",
                    "content": "Explain memory systems in one sentence."
                }
            ],
            temperature=0.0,
            max_tokens=50,
        )
        print(f"   ✓ Response: {response.choices[0].message.content}")
        
        print(f"\n✅ {description} test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR testing {description}: {type(e).__name__}")
        print(f"   {str(e)}")
        
        # Check for rate limit errors
        if "429" in str(e) or "rate" in str(e).lower():
            print("\n   This is a rate limit error.")
            print("   Free tier requires 1-second delay between requests.")
            print("   Try again in a few seconds.")
        
        return False

def test_mistral():
    """Test Mistral API with multiple model variants."""
    
    print("=" * 60)
    print("Testing Mistral AI API (Free Tier)")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("❌ ERROR: MISTRAL_API_KEY not found in .env")
        print("   Get your API key from: https://console.mistral.ai/")
        print("\n   Setup instructions:")
        print("   1. Visit https://console.mistral.ai/api-keys/")
        print("   2. Create a new API key")
        print("   3. Add to .env file: MISTRAL_API_KEY=your_key_here")
        return False
    
    print(f"✓ API key loaded: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        # Initialize client
        print("\nInitializing Mistral client...")
        client = Mistral(api_key=api_key)
        print("✓ Client initialized")
        
        # Test key models
        models = [
            ("mistral-small-latest", "Mistral Small (Fast Tasks)"),
            ("mistral-large-latest", "Mistral Large (Complex Reasoning)"),
        ]
        
        results = {}
        for model_name, description in models:
            results[model_name] = test_model(client, model_name, description)
            # Add 1+ second delay to respect rate limits
            print("\n   Waiting 2 seconds (respecting rate limits)...")
            time.sleep(2)
        
        # Summary
        print("\n" + "=" * 60)
        print("MISTRAL TEST SUMMARY")
        print("=" * 60)
        
        for model_name, description in models:
            status = "✅ PASSED" if results[model_name] else "❌ FAILED"
            print(f"{status} - {description}")
        
        print("\n" + "=" * 60)
        print("Rate Limits (Free Tier):")
        print("  • 1 request per second (RPS) = ~60 RPM")
        print("  • No strict TPM limit for free tier")
        print("  • Fair use policy applies")
        print("\nContext Windows:")
        print("  • Mistral Large: 128k tokens")
        print("  • Mistral Small: 32k tokens")
        print("\n⚠️  Note: Free tier requires 1-second delay between requests")
        print("⚠️  Free tier is for evaluation/prototyping only")
        print("=" * 60)
        
        return all(results.values())
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}")
        print(f"   {str(e)}")
        return False

if __name__ == "__main__":
    success = test_mistral()
    sys.exit(0 if success else 1)
