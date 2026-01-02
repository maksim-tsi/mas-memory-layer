import asyncio
import os
from qdrant_client.http import models
from src.storage.qdrant_adapter import QdrantAdapter


async def main() -> None:
    adapter = QdrantAdapter({
        "url": os.getenv("QDRANT_URL", "http://192.168.107.187:6333"),
        "collection_name": os.getenv("QDRANT_COLLECTION", "episodes"),
    })
    await adapter.connect()
    await adapter.client.create_payload_index(
        collection_name="episodes",
        field_name="session_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    print("Created payload index on session_id for episodes")
    await adapter.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
