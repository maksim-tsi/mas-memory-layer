import asyncio
import os
from datetime import datetime, timezone, timedelta

from src.storage.postgres_adapter import PostgresAdapter
from src.memory.tiers.working_memory_tier import WorkingMemoryTier


async def main() -> None:
    session_id = "l2-roundtrip"
    adapter = PostgresAdapter({
        "url": os.getenv("POSTGRES_URL", "postgresql://pgadmin:password@192.168.107.187:5432/mas_memory"),
    })
    await adapter.connect()
    tier = WorkingMemoryTier(adapter)

    # Insert 3 facts with high CIAR
    for i in range(3):
        await tier.store({
            "session_id": session_id,
            "fact_id": f"fact-{i}",
            "content": f"Roundtrip fact {i}",
            "fact_type": "event",
            "certainty": 0.9,
            "impact": 0.9,
            "ciar_score": 0.81,
            "created_at": datetime.now(timezone.utc) - timedelta(minutes=i),
        })

    facts = await tier.query_by_session(session_id=session_id, limit=10)
    print("Queried facts count:", len(facts))
    for f in facts:
        print(f.fact_id, f.session_id, f.ciar_score)

    await adapter.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
