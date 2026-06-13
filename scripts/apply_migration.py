import asyncio
import os
import sys

import psycopg


async def apply_migration():
    # Load environment variables (assuming they are set in shell or .env)
    db_url = os.getenv("POSTGRES_URL")
    if not db_url:
        print("Error: POSTGRES_URL not set.")
        sys.exit(1)

    migration_file = "migrations/003_add_memory_metrics.sql"
    with open(migration_file) as f:
        sql = f.read()

    print(f"Applying migration: {migration_file}...")
    try:
        async with await psycopg.AsyncConnection.connect(db_url) as conn:  # noqa: SIM117
            async with conn.cursor() as cur:
                await cur.execute(sql)
                await conn.commit()
        print("Migration applied successfully.")
    except Exception as e:
        print(f"Error applying migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(apply_migration())
