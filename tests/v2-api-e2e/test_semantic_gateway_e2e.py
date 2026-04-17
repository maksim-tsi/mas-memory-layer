# ruff: noqa
import asyncio
import os
from pathlib import Path

import pytest
import pytest_asyncio
import httpx
from dotenv import load_dotenv

# MUST load environment before importing src.server or else missing REDIS_URL will fail initialization
load_dotenv(override=True)

cloud_node_ip = os.environ["CLOUD_NODE_IP"]
dev_node_ip = os.environ["DEV_NODE_IP"]
data_node_ip = os.environ["DATA_NODE_IP"]

redis_port = os.environ["REDIS_PORT"]
postgres_port = os.environ["POSTGRES_PORT"]
postgres_user = os.environ["POSTGRES_USER"]
postgres_password = os.environ["POSTGRES_PASSWORD"]
postgres_db = os.environ["POSTGRES_DB"]

# Fix missing REDIS_URL/POSTGRES_URL if python-dotenv basic interpolation failed
if "REDIS_URL" not in os.environ or "${" in os.environ["REDIS_URL"]:
    os.environ["REDIS_URL"] = f"redis://{dev_node_ip}:{redis_port}"

if "POSTGRES_URL" not in os.environ or "${" in os.environ["POSTGRES_URL"]:
    os.environ["POSTGRES_URL"] = (
        f"postgresql://{postgres_user}:{postgres_password}@{data_node_ip}:{postgres_port}/{postgres_db}"
    )

# Ensure default profiles so KeyError 'tra' is not triggered
if "MAS_AGENT_TYPE" in os.environ:
    del os.environ["MAS_AGENT_TYPE"]
if "AGENT_TYPE" in os.environ:
    del os.environ["AGENT_TYPE"]

# Force v2 behavior for this E2E suite.
os.environ["MAS_V2_MODE"] = "true"
# Enforce empirically verified native dimension for qwen/qwen3-embedding-8b.
os.environ["EMBEDDING_DIMENSIONS"] = os.environ.get("E2E_EMBEDDING_DIMENSIONS", "4096")

from src.server import app
from src.storage.qdrant_adapter import QdrantAdapter
from src.storage.neo4j_adapter import Neo4jAdapter
from src.storage.typesense_adapter import TypesenseAdapter
from src.memory.tiers.episodic_memory_tier import EpisodicMemoryTier
from src.memory.tiers.semantic_memory_tier import SemanticMemoryTier


SCENARIOS_DIR = Path(__file__).parent.parent / "data" / "scm_scenarios"


@pytest_asyncio.fixture(scope="function")
async def client():
    qdrant_url = os.environ["QDRANT_URL"]
    neo4j_uri = os.environ["NEO4J_URI"]
    neo4j_user = os.environ["NEO4J_USER"]
    neo4j_password = os.environ["NEO4J_PASSWORD"]
    typesense_url = os.environ["TYPESENSE_URL"]
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

    qdrant_adapter = QdrantAdapter(
        {
            "url": qdrant_url,
            "vector_size": int(os.environ.get("EMBEDDING_DIMENSIONS", 1024)),
            "collection_name": "test_v2",
        }
    )
    neo4j_adapter = Neo4jAdapter({"uri": neo4j_uri, "user": neo4j_user, "password": neo4j_password})
    typesense_adapter = TypesenseAdapter({"url": typesense_url, "api_key": typesense_key})

    l3 = EpisodicMemoryTier(
        qdrant_adapter,
        neo4j_adapter,
        config={
            "collection_name": "test_v2",
            "vector_size": int(os.environ.get("EMBEDDING_DIMENSIONS", 1024)),
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

    await l3.cleanup()
    await l4.cleanup()
    await qdrant_adapter.disconnect()
    await neo4j_adapter.disconnect()
    await typesense_adapter.disconnect()


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
