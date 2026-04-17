#!/usr/bin/env python3
"""Recreate only v2 Qdrant collections with configured embedding dimensions."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from src.llm.client import LLMClient

V2_COLLECTIONS = ("episodes_v2", "test_v2")


def _resolve_qdrant_url() -> str:
    data_node_ip = os.environ["DATA_NODE_IP"]
    qdrant_port = os.environ["QDRANT_PORT"]
    return (
        os.environ["QDRANT_URL"]
        .replace("${DATA_NODE_IP}", data_node_ip)
        .replace("${QDRANT_PORT}", qdrant_port)
    )


def _get_collection_dimension(client: QdrantClient, collection: str) -> int | None:
    try:
        info = client.get_collection(collection)
        return int(info.config.params.vectors.size)
    except Exception:
        return None


async def _discover_native_dimension() -> int:
    model = os.environ.get("OPENROUTER_EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
    client = LLMClient.from_env()
    vector = await client.get_embedding("test", model=model, provider="openrouter")
    return len(vector)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dimension",
        type=int,
        default=None,
        help="Explicit vector dimension to use. If omitted, auto-discovers via OpenRouter.",
    )
    return parser.parse_args()


def main() -> None:
    import asyncio

    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    args = _parse_args()

    vector_size = args.dimension or asyncio.run(_discover_native_dimension())
    url = _resolve_qdrant_url()

    client = QdrantClient(url=url)

    print(f"qdrant_url={url}")
    print(f"target_dimension={vector_size}")

    existing = {collection.name for collection in client.get_collections().collections}

    for collection in V2_COLLECTIONS:
        before = _get_collection_dimension(client, collection)
        print(f"before {collection}: {before}")

        if collection in existing:
            client.delete_collection(collection_name=collection)
            print(f"deleted {collection}")

        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        after = _get_collection_dimension(client, collection)
        print(f"after {collection}: {after}")


if __name__ == "__main__":
    main()
