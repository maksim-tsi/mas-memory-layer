from datetime import UTC, datetime

from src.memory.models import Fact
from src.memory.services.contracts import (
    ScopeEnvelope,
    memory_result_from_fact,
    memory_result_from_unified,
    redact_metadata,
)


def test_redact_metadata_removes_secret_shaped_values() -> None:
    metadata = {
        "agent_id": "agent-a",
        "api_token": "secret-token",
        "nested": {"password": "secret-password", "safe": "visible"},
    }

    redacted = redact_metadata(metadata)

    assert redacted["agent_id"] == "agent-a"
    assert redacted["api_token"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert redacted["nested"]["safe"] == "visible"


def test_memory_result_from_fact_includes_scope_and_provenance() -> None:
    scope = ScopeEnvelope(
        session_id="session-a",
        agent_id="agent-a",
        task_id="task-a",
        tenant_id="tenant-a",
    )
    fact = Fact(
        fact_id="fact-a",
        session_id="session-a",
        content="Berth B is unavailable.",
        ciar_score=0.8,
        certainty=0.8,
        impact=1.0,
        age_decay=1.0,
        recency_boost=1.0,
        created_at=datetime.now(UTC),
        metadata={"api_key": "secret", "audit_id": "audit-a"},
    )

    result = memory_result_from_fact(fact, scope)

    assert result.tier == "L2"
    assert result.source_id == "fact-a"
    assert result.score == 0.8
    assert result.metadata["api_key"] == "[REDACTED]"
    assert result.provenance is not None
    assert result.provenance.agent_id == "agent-a"
    assert result.provenance.task_id == "task-a"
    assert result.provenance.audit_id == "audit-a"


def test_memory_result_from_unified_maps_tier_source_ids() -> None:
    scope = ScopeEnvelope(session_id="session-a", agent_id="agent-a")
    result = memory_result_from_unified(
        {
            "content": "Known routing constraint.",
            "tier": "L4",
            "score": 0.5,
            "metadata": {"knowledge_id": "kd-a", "token": "secret"},
        },
        scope,
    )

    assert result.tier == "L4"
    assert result.source_id == "kd-a"
    assert result.provenance is not None
    assert result.provenance.source_id == "kd-a"
    assert result.metadata["token"] == "[REDACTED]"
