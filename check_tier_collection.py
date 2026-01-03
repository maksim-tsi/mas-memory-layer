import asyncio
import os
from src.storage.qdrant_adapter import QdrantAdapter
from src.storage.neo4j_adapter import Neo4jAdapter
from src.memory.tiers.episodic_memory_tier import EpisodicMemoryTier


async def main() -> None:
    q = QdrantAdapter({
        "url": os.getenv("QDRANT_URL", "http://192.168.107.187:6333"),
        "collection_name": os.getenv("QDRANT_COLLECTION", "episodes"),
        "vector_size": int(os.getenv("QDRANT_VECTOR_SIZE", EpisodicMemoryTier.VECTOR_SIZE)),
    })
    await q.connect()
    n = Neo4jAdapter({
        "uri": os.getenv("NEO4J_URI", "bolt://192.168.107.187:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "password"),
    })
    tier = EpisodicMemoryTier(q, n)
    print("Adapter collection:", q.collection_name, "vector_size:", q.vector_size)
    print("Tier collection:", tier.collection_name, "vector_size:", tier.vector_size)
    await q.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
