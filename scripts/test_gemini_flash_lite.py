"""Validate GeminiProvider with gemini-2.5-flash-lite model.

Run this script to confirm the native Gemini client returns text and usage metadata.
"""

import asyncio
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


async def main() -> int:
    from src.utils.llm_client import LLMClient, ProviderConfig
    from src.utils.providers import GeminiProvider

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY is not set")
        return 1

    client = LLMClient()
    client.register_provider(
        GeminiProvider(api_key=api_key),
        ProviderConfig(name="gemini", priority=0),
    )

    response = await client.generate(
        prompt="Return only the number 4.",
        model="gemini-2.5-flash-lite",
        temperature=0.0,
        max_output_tokens=8,
    )

    print(f"Model: {response.model}")
    print(f"Text: {response.text}")
    print(f"Usage: {response.usage}")

    if not response.text:
        print("No text returned")
        return 2

    if response.usage is None:
        print("Warning: usage metadata missing")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
