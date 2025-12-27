#!/usr/bin/env python3
"""
Test Groq API connectivity and basic chat completion.

This script validates:
- API key is loaded correctly
- Groq API is accessible
- Basic chat completion works
- Token usage tracking
- Ultra-fast inference speed
- Multiple model variants (Llama 3.1 8B/70B, Mixtral, Gemma 2)
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

def test_model(client, model_name: str, description: str) -> bool:
    """Test a specific Groq model variant."""
    print(f"\n{'='*60}")
    print(f"Testing {description}")
    print(f"Model: {model_name}")
    print(f"{'='*60}")
    
    try:
        # Test basic chat completion with timing
        print("\n1. Testing basic chat completion (with speed measurement)...")
        test_prompt = "What is 2+2? Answer in one short sentence."
        
        start_time = time.time()
        response = client.chat.completions.create(
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
        elapsed = time.time() - start_time
        
        print(f"   ✓ Response received in {elapsed:.3f} seconds")
        print(f"   Prompt: {test_prompt}")
        print(f"   Response: {response.choices[0].message.content}")
        
        # Check usage statistics
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            tokens_per_sec = usage.completion_tokens / elapsed if elapsed > 0 else 0
            print("\n2. Token Usage & Performance:")
            print(f"   Prompt tokens: {usage.prompt_tokens}")
            print(f"   Response tokens: {usage.completion_tokens}")
            print(f"   Total tokens: {usage.total_tokens}")
            print(f"   ⚡ Inference speed: ~{tokens_per_sec:.0f} tokens/second")
        
        # Test with system message
        print("\n3. Testing with system message...")
        response = client.chat.completions.create(
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
            print("\n   This is a rate limit error. Possible causes:")
            print("   • Too many requests in short time")
            print("   • Daily token limit exceeded")
            print("   • Try again in a few seconds")
        
        return False

def test_groq():
    """Test Groq API with multiple model variants."""
    
    print("=" * 60)
    print("Testing Groq API (Ultra-Fast Inference)")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ ERROR: GROQ_API_KEY not found in .env")
        print("   Get your API key from: https://console.groq.com/")
        print("\n   Setup instructions:")
        print("   1. Visit https://console.groq.com/keys")
        print("   2. Create a new API key")
        print("   3. Add to .env file: GROQ_API_KEY=your_key_here")
        return False
    
    print(f"✓ API key loaded: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        # Initialize client
        print("\nInitializing Groq client...")
        client = Groq(api_key=api_key)
        print("✓ Client initialized")
        
        # Test key models (not all to avoid rate limits)
        models = [
            ("llama-3.1-8b-instant", "Llama 3.1 8B Instant (Primary - Fast Tasks)"),
            ("openai/gpt-oss-120b", "GPT OSS 120B (Reasoning Fallback)"),
        ]
        
        results = {}
        for model_name, description in models:
            results[model_name] = test_model(client, model_name, description)
            # Add small delay to avoid rate limits
            time.sleep(2)
        
        # Summary
        print("\n" + "=" * 60)
        print("GROQ TEST SUMMARY")
        print("=" * 60)
        
        for model_name, description in models:
            status = "✅ PASSED" if results[model_name] else "❌ FAILED"
            print(f"{status} - {description}")
        
        print("\n" + "=" * 60)
        print("Rate Limits (Free Tier):")
        print("  • 30 requests per minute (RPM)")
        print("  • 14,400 requests per day (RPD)")
        print("  • 20,000-200,000 tokens per minute (model-dependent)")
        print("  • 1,000,000+ tokens per day")
        print("\n⚡ Ultra-Fast: ~250-800 tokens/sec (custom LPU hardware)")
        print("\nAvailable Models:")
        print("  • llama-3.1-8b-instant - Ultra-fast, 8k context")
        print("  • openai/gpt-oss-120b - Best reasoning, 120B parameters")
        print("  • mixtral-8x7b-32768 - Good reasoning, 32k context")
        print("  • gemma2-9b-it - Fast, efficient, 8k context")
        print("=" * 60)
        
        return all(results.values())
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}")
        print(f"   {str(e)}")
        return False

if __name__ == "__main__":
    success = test_groq()
    sys.exit(0 if success else 1)
