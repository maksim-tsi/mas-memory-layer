#!/usr/bin/env python3
"""
Master test script for all LLM provider connectivity.

Tests all providers configured in ADR-006:
- Google Gemini (3 models)
- Groq (2 models)
- Mistral AI (2 models)

This script provides a comprehensive overview of which providers
are accessible and ready for use in the memory system.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import individual test modules
import test_gemini
import test_groq
import test_mistral


def print_header():
    """Print test suite header."""
    print("\n" + "=" * 70)
    print(" " * 15 + "MAS MEMORY LAYER - LLM PROVIDER TESTS")
    print("=" * 70)
    print("\nTesting connectivity for all providers defined in ADR-006:")
    print("  1. Google Gemini (2.5 Flash, 2.0 Flash, 2.5 Flash-Lite)")
    print("  2. Groq (Llama 3.1 8B/70B)")
    print("  3. Mistral AI (Large, Small)")
    print("\n" + "=" * 70)


def check_api_keys():
    """Check which API keys are configured."""
    print("\nChecking API Key Configuration:")
    print("-" * 70)
    
    keys = {
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "MISTRAL_API_KEY": os.getenv("MISTRAL_API_KEY"),
    }
    
    configured = []
    missing = []
    
    for key_name, key_value in keys.items():
        if key_value:
            print(f"  ✓ {key_name}: {key_value[:10]}...{key_value[-4:]}")
            configured.append(key_name)
        else:
            print(f"  ✗ {key_name}: NOT CONFIGURED")
            missing.append(key_name)
    
    print("-" * 70)
    
    if missing:
        print(f"\n⚠️  Missing API keys: {', '.join(missing)}")
        print("   These providers will be skipped.\n")
        print("   To configure:")
        if "GOOGLE_API_KEY" in missing:
            print("   • Google Gemini: https://aistudio.google.com/app/apikey")
        if "GROQ_API_KEY" in missing:
            print("   • Groq: https://console.groq.com/keys")
        if "MISTRAL_API_KEY" in missing:
            print("   • Mistral AI: https://console.mistral.ai/api-keys/")
        print()
    
    return configured, missing


def run_provider_tests():
    """Run tests for all configured providers."""
    
    results = {}
    
    # Test Gemini
    print("\n" + "🔷" * 35)
    print("PROVIDER 1/3: Google Gemini")
    print("🔷" * 35)
    if os.getenv("GOOGLE_API_KEY"):
        results["Gemini"] = test_gemini.test_gemini()
    else:
        print("⚠️  Skipping Gemini - API key not configured")
        results["Gemini"] = None
    
    # Test Groq
    print("\n" + "🔷" * 35)
    print("PROVIDER 2/3: Groq")
    print("🔷" * 35)
    if os.getenv("GROQ_API_KEY"):
        results["Groq"] = test_groq.test_groq()
    else:
        print("⚠️  Skipping Groq - API key not configured")
        results["Groq"] = None
    
    # Test Mistral
    print("\n" + "🔷" * 35)
    print("PROVIDER 3/3: Mistral AI")
    print("🔷" * 35)
    if os.getenv("MISTRAL_API_KEY"):
        results["Mistral"] = test_mistral.test_mistral()
    else:
        print("⚠️  Skipping Mistral AI - API key not configured")
        results["Mistral"] = None
    
    return results


def print_summary(results):
    """Print comprehensive test summary."""
    print("\n" + "=" * 70)
    print(" " * 20 + "COMPREHENSIVE TEST SUMMARY")
    print("=" * 70)
    
    print("\nProvider Status:")
    print("-" * 70)
    
    for provider, result in results.items():
        if result is None:
            status = "⚠️  SKIPPED (no API key)"
        elif result:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        print(f"  {status} - {provider}")
    
    print("-" * 70)
    
    # Count results
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    
    print(f"\nResults: {passed} passed, {failed} failed, {skipped} skipped")
    
    # Recommendations
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS:")
    print("=" * 70)
    
    if passed == 0:
        print("\n⚠️  No providers are currently working!")
        print("   Action: Configure at least one API key to proceed.")
        print("   Priority: Start with Google Gemini (easiest to set up)")
    elif passed == 1:
        print("\n✓ One provider is working, but consider adding more for:")
        print("  • Fallback resilience (if primary provider fails)")
        print("  • Task-specific optimization (different models for different tasks)")
        print("  • Rate limit distribution (spread load across providers)")
    elif passed == 2:
        print("\n✓ Two providers are working - good resilience!")
        print("  Consider adding the remaining provider for maximum flexibility.")
    else:
        print("\n✅ All providers are working - excellent setup!")
        print("   You have maximum resilience and task optimization options.")
    
    print("\nNext Steps:")
    if passed > 0:
        print("  1. Review ADR-006 for task-to-provider mappings")
        print("  2. Implement multi-provider LLM client (src/utils/llm_client.py)")
        print("  3. Integrate with memory lifecycle engines (Week 4-10)")
    else:
        print("  1. Configure API keys in .env file")
        print("  2. Run this test script again")
        print("  3. Proceed with LLM client implementation")
    
    print("=" * 70 + "\n")


def main():
    """Main test execution."""
    print_header()
    
    configured, missing = check_api_keys()
    
    if not configured:
        print("\n❌ ERROR: No API keys configured!")
        print("   Please add at least one API key to .env file.")
        print("   See .env.example for required variables.")
        return False
    
    print(f"\nProceeding with {len(configured)} configured provider(s)...")
    input("\nPress Enter to start tests (or Ctrl+C to cancel)...")
    
    results = run_provider_tests()
    
    print_summary(results)
    
    # Return success if at least one provider works
    return any(r is True for r in results.values())


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}")
        print(f"   {str(e)}")
        sys.exit(1)
