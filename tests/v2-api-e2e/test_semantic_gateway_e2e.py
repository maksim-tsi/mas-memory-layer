# ruff: noqa
import asyncio
import os
from pathlib import Path

import pytest
import pytest_asyncio
import httpx
from dotenv import load_dotenv
from qdrant_client import AsyncQdrantClient

pytestmark = pytest.mark.integration

# MUST load environment before importing src.server or else missing REDIS_URL will fail initialization
load_dotenv(override=True)

_SCOPED_ENV_KEYS = ("MAS_V2_MODE", "EMBEDDING_DIMENSIONS")
_ORIGINAL_SCOPED_ENV = {key: os.environ.get(key) for key in _SCOPED_ENV_KEYS}

data_node_ip = os.environ.get("DATA_NODE_IP", "192.168.107.187")
# skz-dev-lv and skz-cloud-lv may be powered off; current E2E topology uses
# skz-data-lv for Redis, PostgreSQL, Qdrant, Neo4j, Typesense, and Phoenix.
dev_node_ip = os.environ.get("DEV_NODE_IP", data_node_ip)
cloud_node_ip = os.environ.get("CLOUD_NODE_IP", data_node_ip)

redis_port = os.environ.get("REDIS_PORT", "6379")
postgres_port = os.environ.get("POSTGRES_PORT", "5432")
postgres_user = os.environ.get("POSTGRES_USER", "postgres")
postgres_password = os.environ.get("POSTGRES_PASSWORD", "postgres")
postgres_db = os.environ.get("POSTGRES_DB", "postgres")

# Fix missing REDIS_URL/POSTGRES_URL if python-dotenv basic interpolation failed
if "REDIS_URL" not in os.environ or "${" in os.environ["REDIS_URL"]:
    os.environ["REDIS_URL"] = f"redis://{data_node_ip}:{redis_port}/0"

if "POSTGRES_URL" not in os.environ or "${" in os.environ["POSTGRES_URL"]:
    os.environ["POSTGRES_URL"] = (
        f"postgresql://{postgres_user}:{postgres_password}@{data_node_ip}:{postgres_port}/{postgres_db}"
    )

# Ensure default profiles so KeyError 'tra' is not triggered
if "MAS_AGENT_TYPE" in os.environ:
    del os.environ["MAS_AGENT_TYPE"]
if "AGENT_TYPE" in os.environ:
    del os.environ["AGENT_TYPE"]

# Force v2 behavior for app import, then restore so collection does not
# contaminate unrelated unit tests.
os.environ["MAS_V2_MODE"] = "true"
# Enforce empirically verified native dimension for qwen/qwen3-embedding-8b.
e2e_embedding_dimensions = os.environ.get("E2E_EMBEDDING_DIMENSIONS", "4096")
os.environ["EMBEDDING_DIMENSIONS"] = e2e_embedding_dimensions

from src.server import app
from src.storage.qdrant_adapter import QdrantAdapter
from src.storage.neo4j_adapter import Neo4jAdapter
from src.storage.typesense_adapter import TypesenseAdapter
from src.memory.tiers.episodic_memory_tier import EpisodicMemoryTier
from src.memory.tiers.semantic_memory_tier import SemanticMemoryTier

for key, value in _ORIGINAL_SCOPED_ENV.items():
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value


SCENARIOS_DIR = Path(__file__).parent.parent / "data" / "scm_scenarios"
QDRANT_E2E_COLLECTION = "test_v2"


async def _assert_qdrant_collection_dimension(
    qdrant_url: str, collection_name: str, expected_dimension: int
) -> None:
    """Fail clearly when the live E2E collection exists with a stale dimension."""
    client = AsyncQdrantClient(url=qdrant_url)
    try:
        try:
            info = await client.get_collection(collection_name)
        except Exception as exc:
            message = str(exc).lower()
            if "not found" in message or "doesn't exist" in message:
                return
            raise RuntimeError(
                f"Qdrant preflight failed for collection {collection_name}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        actual_dimension = int(info.config.params.vectors.size)
        if actual_dimension != expected_dimension:
            raise RuntimeError(
                f"Qdrant collection {collection_name} has vector size "
                f"{actual_dimension}, expected {expected_dimension}. Recreate the "
                "YAAM v2 test collection before running live E2E tests."
            )
    finally:
        await client.close()


@pytest_asyncio.fixture(scope="function")
async def client():
    missing = [
        key
        for key in ("NEO4J_USER", "NEO4J_PASSWORD", "TYPESENSE_API_KEY")
        if not os.environ.get(key)
    ]
    if missing:
        pytest.skip(f"Live skz-data-lv E2E credentials not configured: {', '.join(missing)}")

    scoped_env = {key: os.environ.get(key) for key in _SCOPED_ENV_KEYS}
    os.environ["MAS_V2_MODE"] = "true"
    os.environ["EMBEDDING_DIMENSIONS"] = e2e_embedding_dimensions

    qdrant_url = os.environ.get("QDRANT_URL", f"http://{data_node_ip}:6333")
    neo4j_uri = os.environ.get("NEO4J_URI", f"bolt://{data_node_ip}:7687")
    neo4j_user = os.environ["NEO4J_USER"]
    neo4j_password = os.environ["NEO4J_PASSWORD"]
    typesense_url = os.environ.get("TYPESENSE_URL", f"http://{data_node_ip}:8108")
    typesense_key = os.environ["TYPESENSE_API_KEY"]

    # Expand variables if needed
    qdrant_url = qdrant_url.replace("${DATA_NODE_IP}", data_node_ip).replace(
        "${QDRANT_PORT}", os.environ["QDRANT_PORT"]
    )
    neo4j_uri = neo4j_uri.replace("${DATA_NODE_IP}", data_node_ip).replace(
        "${NEO4J_BOLT_PORT}", os.environ["NEO4J_BOLT_PORT"]
    )
    typesense_url = typesense_url.replace("${DATA_NODE_IP}", data_node_ip).replace(
        "${TYPESENSE_PORT}", os.environ["TYPESENSE_PORT"]
    )

    qdrant_adapter = None
    neo4j_adapter = None
    typesense_adapter = None
    l3 = None
    l4 = None
    try:
        e2e_vector_size = int(os.environ.get("EMBEDDING_DIMENSIONS", 1024))
        await _assert_qdrant_collection_dimension(
            qdrant_url, QDRANT_E2E_COLLECTION, e2e_vector_size
        )

        qdrant_adapter = QdrantAdapter(
            {
                "url": qdrant_url,
                "vector_size": e2e_vector_size,
                "collection_name": QDRANT_E2E_COLLECTION,
            }
        )
        neo4j_adapter = Neo4jAdapter(
            {"uri": neo4j_uri, "user": neo4j_user, "password": neo4j_password}
        )
        typesense_adapter = TypesenseAdapter({"url": typesense_url, "api_key": typesense_key})

        l3 = EpisodicMemoryTier(
            qdrant_adapter,
            neo4j_adapter,
            config={
                "collection_name": QDRANT_E2E_COLLECTION,
                "vector_size": e2e_vector_size,
            },
        )
        l4 = SemanticMemoryTier(typesense_adapter)

        await qdrant_adapter.connect()
        await neo4j_adapter.connect()
        await typesense_adapter.connect()
        await l3.initialize()
        await l4.initialize()

        # Emulate the fastAPI lifespan so L1 and L2 initialize correctly
        async with app.router.lifespan_context(app):
            # Override the L3 and L4 tiers with our live adapters
            state = app.state.wrapper
            state.memory_system.l3_tier = l3
            state.memory_system.l4_tier = l4

            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
                yield c
    finally:
        if l3:
            await l3.cleanup()
        if l4:
            await l4.cleanup()
        if qdrant_adapter:
            await qdrant_adapter.disconnect()
        if neo4j_adapter:
            await neo4j_adapter.disconnect()
        if typesense_adapter:
            await typesense_adapter.disconnect()
        for key, value in scoped_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@pytest.fixture
def session_id():
    return "scm_live_e2e_test_001"


@pytest.fixture
def agent_id():
    return "test_orchestrator"


@pytest.mark.asyncio
async def test_l2_semantic_fact_flow(client, session_id, agent_id):
    """E2E Test for L2 Semantic Fact storing and retrieval."""
    payload_store = {
        "session_id": session_id,
        "task_id": "audit_task_01",
        "agent_id": agent_id,
        "action": "store",
        "content": "A localized EOQ audit revealed major inconsistencies in calculation.",
    }
    resp = await client.post("/v2/memory/l2/facts", json=payload_store)
    assert resp.status_code == 200, f"Expected 200, got {resp.text}"
    assert resp.json()["status"] == "success"

    payload_retrieve = {
        "session_id": session_id,
        "task_id": "audit_task_01",
        "agent_id": agent_id,
        "action": "retrieve",
    }
    resp_retrieve = await client.post("/v2/memory/l2/facts", json=payload_retrieve)
    assert resp_retrieve.status_code == 200
    r_json = resp_retrieve.json()
    assert "facts" in r_json
    assert r_json["status"] == "success"


@pytest.mark.asyncio
async def test_l3_semantic_assimilate(client, session_id, agent_id):
    """E2E Test for L3 Knowledge Assimilation (Live LLM Pipeline)."""
    file_path = SCENARIOS_DIR / "01_port_strike.md"
    assert file_path.exists(), "SCM scenario file missing!"

    payload = {
        "session_id": session_id,
        "agent_id": agent_id,
        "text_to_assimilate": file_path.read_text(),
        "domain_tags": ["EMEA", "logistics", "strike"],
    }

    resp = await client.post("/v2/memory/l3/assimilate", json=payload)

    assert resp.status_code == 201, f"Expected 201, got {resp.text}"
    assert "episode_id" in resp.json()


@pytest.mark.asyncio
async def test_l3_semantic_query(client, session_id, agent_id):
    """E2E Test for L3 Semantic Querying."""
    # Delay to allow eventual consistency in Qdrant (vector index settling)
    await asyncio.sleep(2)

    payload = {
        "session_id": session_id,
        "agent_id": agent_id,
        "nl_query": "What happens if our suppliers in Asia go bankrupt?",
        "top_k": 3,
        "filters": {"importance": "high"},
    }

    resp = await client.post("/v2/memory/l3/query", json=payload)

    assert resp.status_code == 200, f"Expected 200, got {resp.text}"
    r_json = resp.json()
    assert "results" in r_json
    assert "provenance" in r_json
    assert r_json["provenance"]["session_id"] == session_id


@pytest.mark.asyncio
async def test_l4_semantic_finalize(client, session_id, agent_id):
    """E2E Test for L4 Risk Pooling Finalization document."""
    file_path = SCENARIOS_DIR / "05_risk_pooling.md"
    assert file_path.exists(), "SCM scenario file missing!"

    payload = {
        "task_id": "task_rp_final_09a",
        "session_id": session_id,
        "title": "Consensus Report: Regional Risk Pooling Optimization",
        "final_artifact": file_path.read_text(),
        "consensus_metadata": {"votes": 3, "disagreements": "None, full MAS alignment achieved."},
    }

    resp = await client.post("/v2/memory/l4/finalize", json=payload)
    assert resp.status_code == 201, f"Expected 201, got {resp.text}"
    assert "knowledge_id" in resp.json()
