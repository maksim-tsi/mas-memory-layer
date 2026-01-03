import asyncio
import os
from src.storage.qdrant_adapter import QdrantAdapter


async def main() -> None:
    adapter = QdrantAdapter({
        "url": os.getenv("QDRANT_URL", "http://192.168.107.187:6333"),
        "collection_name": os.getenv("QDRANT_COLLECTION", "episodes"),
        "vector_size": int(os.getenv("QDRANT_VECTOR_SIZE", 768)),
    })
    await adapter.connect()
    created = await adapter.create_collection("episodes")
    print("Episodes collection created or refreshed:", created)
    info = await adapter.client.get_collection(collection_name="episodes")
    size = getattr(info.config.params.vectors, "size", None)
    print("Current vector size:", size)
    await adapter.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
