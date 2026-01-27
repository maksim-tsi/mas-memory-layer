"""Integration test for Neo4j distributed lock renewal."""

import asyncio
import os

import pytest
import redis.asyncio as redis

from src.storage.neo4j_adapter import Neo4jLockManager


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_lock_renewal_prevents_expiration():
    """Verify Redis lock remains valid after renewal interval."""
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        pytest.skip("REDIS_URL not set; skipping lock renewal test.")

    redis_client = redis.from_url(redis_url, decode_responses=True)
    lock_manager = Neo4jLockManager(redis_client, ttl_seconds=30, renewal_interval=10)
    session_id = "test_long_operation"
    lock_key = f"neo4j:{session_id}"

    try:
        await redis_client.delete(lock_key)
        await lock_manager.start()

        await lock_manager.acquire(session_id)
        assert await redis_client.exists(lock_key) == 1

        await asyncio.sleep(35)
        assert await redis_client.exists(lock_key) == 1

        await lock_manager.release(session_id)
        assert await redis_client.exists(lock_key) == 0
    finally:
        await lock_manager.stop()
        await redis_client.aclose()
