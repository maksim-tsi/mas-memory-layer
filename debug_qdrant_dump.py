import asyncio
import os
from src.storage.qdrant_adapter import QdrantAdapter


async def main() -> None:
    url = os.getenv("QDRANT_URL", "http://192.168.107.187:6333")
    collection = os.getenv("QDRANT_COLLECTION", "episodes")

    adapter = QdrantAdapter({
        "url": url,
        "collection_name": collection,
        "metrics": {"enabled": False},
    })
    await adapter.connect()

    print(f"--- Checking Collection: {adapter.collection_name} ---")

    count = None
    try:
        count = await adapter.client.count(collection_name=adapter.collection_name)
        print(f"Total Points: {count.count}")
    except Exception as exc:  # pragma: no cover - diagnostic helper
        print(f"Error checking count: {exc}")

    try:
        if count and getattr(count, "count", 0) > 0:
            res = await adapter.client.scroll(
                collection_name=adapter.collection_name,
                limit=5,
                with_payload=True,
                with_vectors=False,
            )
            print("\n--- Payload Structure Sample ---")
            for point in res[0]:
                payload = point.payload or {}
                print(f"ID: {point.id}")
                print(f"Payload keys: {list(payload.keys())}")
                print(f"Session ID: {payload.get('session_id')}")
                print(f"Metadata: {payload.get('metadata')}")
                print("-" * 20)
    except Exception as exc:  # pragma: no cover - diagnostic helper
        print(f"Error during scroll: {exc}")

    await adapter.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
