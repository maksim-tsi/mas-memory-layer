from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.server import app

client = TestClient(app)

SCENARIOS_DIR = Path(__file__).parent.parent / "data" / "scm_scenarios"


@pytest.fixture
def session_id():
    return "scm_e2e_session_999"


@pytest.fixture
def agent_id():
    return "tra_orchestrator"


def test_l2_semantic_fact_flow(session_id, agent_id):
    """E2E Test for L2 Semantic Fact storing and retrieval."""
    # 1. Store Fact
    payload_store = {
        "session_id": session_id,
        "task_id": "audit_task_01",
        "agent_id": agent_id,
        "action": "store",
        "content": "A localized EOQ audit revealed major inconsistencies in calculation.",
        "metadata": {"trace_id": "trace-test-l2-store"},
    }
    resp = client.post("/v2/memory/l2/facts", json=payload_store)
    assert resp.status_code == 200, f"Expected 200, got {resp.text}"
    assert resp.json()["status"] == "success"

    # 2. Retrieve Fact
    payload_retrieve = {
        "session_id": session_id,
        "task_id": "audit_task_01",
        "agent_id": agent_id,
        "action": "retrieve",
        "metadata": {"trace_id": "trace-test-l2-retrieve"},
    }
    resp_retrieve = client.post("/v2/memory/l2/facts", json=payload_retrieve)
    assert resp_retrieve.status_code == 200
    r_json = resp_retrieve.json()
    assert "facts" in r_json
    assert r_json["status"] == "success"


def test_l3_semantic_assimilate(session_id, agent_id):
    """E2E Test for L3 Knowledge Assimilation (intercepting LLM Pipeline)."""
    file_path = SCENARIOS_DIR / "01_port_strike.md"
    assert file_path.exists(), "SCM scenario file missing!"

    payload = {
        "session_id": session_id,
        "agent_id": agent_id,
        "text_to_assimilate": file_path.read_text(),
        "domain_tags": ["EMEA", "logistics", "strike"],
        "metadata": {"trace_id": "trace-test-l3-assimilate"},
    }

    resp = client.post("/v2/memory/l3/assimilate", json=payload)

    # Due to live integration testing, if LLM provider returns a 502 or timeouts, gracefully pass
    if resp.status_code == 502:
        pytest.skip(
            "Skipped: Internal YAAM LLM returned 502 Bad Gateway (keys not present/timeout)"
        )

    assert resp.status_code == 201, f"Expected 201, got {resp.text}"
    assert "episode_id" in resp.json()


def test_l3_semantic_query(session_id, agent_id):
    """E2E Test for L3 Semantic Querying."""
    payload = {
        "session_id": session_id,
        "agent_id": agent_id,
        "nl_query": "What happens if our suppliers in Asia go bankrupt?",
        "top_k": 3,
        "filters": {"importance": "high"},
        "metadata": {"trace_id": "trace-test-l3-query"},
    }

    resp = client.post("/v2/memory/l3/query", json=payload)

    if resp.status_code == 502:
        pytest.skip(
            "Skipped: Internal YAAM LLM returned 502 Bad Gateway (keys not present/timeout)"
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.text}"
    r_json = resp.json()
    assert "results" in r_json
    assert "provenance" in r_json
    assert r_json["provenance"]["session_id"] == session_id


def test_l4_semantic_finalize(session_id, agent_id):
    """E2E Test for L4 Risk Pooling Finalization document."""
    file_path = SCENARIOS_DIR / "05_risk_pooling.md"
    assert file_path.exists(), "SCM scenario file missing!"

    payload = {
        "task_id": "task_rp_final_09a",
        "session_id": session_id,
        "title": "Consensus Report: Regional Risk Pooling Optimization",
        "final_artifact": file_path.read_text(),
        "consensus_metadata": {"votes": 3, "disagreements": "None, full MAS alignment achieved."},
        "metadata": {"trace_id": "trace-test-l4-finalize"},
    }

    resp = client.post("/v2/memory/l4/finalize", json=payload)
    assert resp.status_code == 201, f"Expected 201, got {resp.text}"
    assert "knowledge_id" in resp.json()
