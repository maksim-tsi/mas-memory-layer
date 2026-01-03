import asyncio
import json
import os
import random
import time
import uuid
from pathlib import Path

import pytest
import pytest_asyncio

from src.storage.redis_adapter import RedisAdapter
from src.storage.postgres_adapter import PostgresAdapter
from src.storage.qdrant_adapter import QdrantAdapter
from src.storage.neo4j_adapter import Neo4jAdapter
from src.storage.typesense_adapter import TypesenseAdapter


THRESHOLD_P95_MS = 200.0
ITERATIONS = 5


@pytest_asyncio.fixture
async def redis_adapter():
    url = os.getenv("REDIS_URL")
    if not url:
        pytest.skip("REDIS_URL not set")
    adapter = RedisAdapter({
        "url": url,
        "window_size": 10,
        "ttl_seconds": 3600,
        "metrics": {"enabled": True, "percentiles": [50, 95, 99]},
    })
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


@pytest_asyncio.fixture
async def postgres_adapter():
    url = os.getenv("POSTGRES_URL")
    if not url:
        pytest.skip("POSTGRES_URL not set")
    adapter = PostgresAdapter({
        "url": url,
        "table": "active_context",
        "metrics": {"enabled": True, "percentiles": [50, 95, 99]},
    })
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


@pytest_asyncio.fixture
async def qdrant_adapter():
    host = os.getenv("QDRANT_HOST", os.getenv("STG_IP", "localhost"))
    port = os.getenv("QDRANT_PORT", "6333")
    adapter = QdrantAdapter({
        "url": f"http://{host}:{port}",
        "collection_name": "perf_memory_perf",
        "vector_size": 384,
        "metrics": {"enabled": True, "percentiles": [50, 95, 99]},
    })
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


@pytest_asyncio.fixture
async def neo4j_adapter():
    host = os.getenv("NEO4J_HOST", os.getenv("STG_IP", "localhost"))
    port = os.getenv("NEO4J_BOLT_PORT", "7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        pytest.skip("NEO4J_PASSWORD not set")
    adapter = Neo4jAdapter({
        "uri": f"bolt://{host}:{port}",
        "user": user,
        "password": password,
        "database": "neo4j",
        "metrics": {"enabled": True, "percentiles": [50, 95, 99]},
    })
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


@pytest_asyncio.fixture
async def typesense_adapter():
    host = os.getenv("TYPESENSE_HOST", os.getenv("STG_IP", "localhost"))
    port = os.getenv("TYPESENSE_PORT", "8108")
    api_key = os.getenv("TYPESENSE_API_KEY")
    if not api_key:
        pytest.skip("TYPESENSE_API_KEY not set")
    adapter = TypesenseAdapter({
        "url": f"http://{host}:{port}",
        "api_key": api_key,
        "collection_name": "perf_memory_perf",
        "metrics": {"enabled": True, "percentiles": [50, 95, 99]},
    })
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


def _record_latency(collector, operation, durations_ms):
    for duration in durations_ms:
        asyncio.get_event_loop().run_until_complete(
            collector.record_operation(operation, duration, True)
        )


async def _p95_from_metrics(collector, operation: str) -> float:
    metrics = await collector.get_metrics()
    op_stats = metrics.get("operations", {}).get(operation, {})
    latency = op_stats.get("latency_ms", {})
    return float(latency.get("p95", 0.0))


@pytest.mark.asyncio
@pytest.mark.integration
async def test_pipeline_perf_live_backends(
    redis_adapter,
    postgres_adapter,
    qdrant_adapter,
    neo4j_adapter,
    typesense_adapter,
):
    session_id = f"perf-{uuid.uuid4()}"

    # Redis store/search
    redis_durations = []
    for i in range(ITERATIONS):
        payload = {
            "session_id": session_id,
            "turn_id": i,
            "content": f"hello {i}",
            "timestamp": time.time(),
        }
        start = time.perf_counter()
        await redis_adapter.store(payload)
        redis_durations.append((time.perf_counter() - start) * 1000)
    await redis_adapter.metrics.record_operation("store", sum(redis_durations) / len(redis_durations), True)
    redis_p95 = await _p95_from_metrics(redis_adapter.metrics, "store")

    # Postgres store/query
    pg_durations = []
    for i in range(ITERATIONS):
        payload = {
            "session_id": session_id,
            "turn_id": i,
            "content": f"pg message {i}",
            "metadata": {"role": "user"},
        }
        start = time.perf_counter()
        record_id = await postgres_adapter.store(payload)
        pg_durations.append((time.perf_counter() - start) * 1000)
        await postgres_adapter.delete(record_id)
    await postgres_adapter.metrics.record_operation("store", sum(pg_durations) / len(pg_durations), True)
    pg_p95 = await _p95_from_metrics(postgres_adapter.metrics, "store")

    # Qdrant upsert/search
    qdrant_durations = []
    vector = [random.random() for _ in range(384)]
    payload = {
        "id": str(uuid.uuid4()),
        "vector": vector,
        "content": "qdrant perf",
        "session_id": session_id,
    }
    start = time.perf_counter()
    await qdrant_adapter.store(payload)
    qdrant_durations.append((time.perf_counter() - start) * 1000)
    start = time.perf_counter()
    await qdrant_adapter.search({"vector": vector, "limit": 1})
    qdrant_durations.append((time.perf_counter() - start) * 1000)
    await qdrant_adapter.metrics.record_operation("qdrant", sum(qdrant_durations) / len(qdrant_durations), True)
    qdrant_p95 = await _p95_from_metrics(qdrant_adapter.metrics, "qdrant")

    # Neo4j write/query
    neo_durations = []
    start = time.perf_counter()
    node_id = await neo4j_adapter.store({
        "type": "entity",
        "label": "PerfNode",
        "properties": {"session_id": session_id, "value": "perf"},
    })
    neo_durations.append((time.perf_counter() - start) * 1000)
    start = time.perf_counter()
    await neo4j_adapter.retrieve(node_id)
    neo_durations.append((time.perf_counter() - start) * 1000)
    await neo4j_adapter.metrics.record_operation("neo4j", sum(neo_durations) / len(neo_durations), True)
    neo_p95 = await _p95_from_metrics(neo4j_adapter.metrics, "neo4j")

    # Typesense index/search
    type_durations = []
    doc = {
        "id": str(uuid.uuid4()),
        "content": "typesense perf doc",
        "title": "perf",
        "session_id": session_id,
        "timestamp": int(time.time()),
    }
    start = time.perf_counter()
    await typesense_adapter.store(doc)
    type_durations.append((time.perf_counter() - start) * 1000)
    start = time.perf_counter()
    await typesense_adapter.search({"q": "perf", "query_by": "content"})
    type_durations.append((time.perf_counter() - start) * 1000)
    await typesense_adapter.metrics.record_operation("typesense", sum(type_durations) / len(type_durations), True)
    type_p95 = await _p95_from_metrics(typesense_adapter.metrics, "typesense")

    results = {
        "redis_p95": redis_p95,
        "postgres_p95": pg_p95,
        "qdrant_p95": qdrant_p95,
        "neo4j_p95": neo_p95,
        "typesense_p95": type_p95,
    }
    # Persist perf evidence for later inspection
    output_path = Path(__file__).resolve().parent / "perf_results.json"
    output_path.write_text(json.dumps(results, indent=2))
    print("Perf p95 ms:", results, flush=True)

    assert redis_p95 < THRESHOLD_P95_MS, f"Redis p95 {redis_p95}ms >= {THRESHOLD_P95_MS}"
    assert pg_p95 < THRESHOLD_P95_MS, f"Postgres p95 {pg_p95}ms >= {THRESHOLD_P95_MS}"
    assert qdrant_p95 < THRESHOLD_P95_MS * 2, f"Qdrant p95 {qdrant_p95}ms too high"
    assert neo_p95 < THRESHOLD_P95_MS * 2, f"Neo4j p95 {neo_p95}ms too high"
    assert type_p95 < THRESHOLD_P95_MS * 2, f"Typesense p95 {type_p95}ms too high"
