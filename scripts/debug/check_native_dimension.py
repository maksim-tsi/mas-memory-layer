#!/usr/bin/env python3
"""Check native embedding dimensionality returned by OpenRouter."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from src.llm.client import LLMClient


async def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    load_dotenv(dotenv_path=env_path, override=True)

    model = os.environ.get("OPENROUTER_EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
    client = LLMClient.from_env()

    if "openrouter" not in client.available_providers():
        raise RuntimeError("OpenRouter provider is not configured; set OPENROUTER_API_KEY")

    vector = await client.get_embedding("test", model=model, provider="openrouter")

    print("provider=openrouter")
    print(f"model={model}")
    print(f"dimension={len(vector)}")
    print(f"head={vector[:5]}")


if __name__ == "__main__":
    asyncio.run(main())
