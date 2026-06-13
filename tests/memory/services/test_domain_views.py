from __future__ import annotations

from typing import Any

import pytest

from src.memory.services import MemoryResult, Provenance, ScopeEnvelope
from src.memory.services.domain_views import (
    CognitiveSandwichDomainViewService,
    SkillFactoryDomainViewService,
)


class SkillFactoryGateway:
    def __init__(self) -> None:
        self.project_id = "scm-skill-factory"
        self.calls: list[tuple[str, ScopeEnvelope, str | None]] = []

    async def search_l2_facts(
        self,
        scope: ScopeEnvelope,
        query: str | None = None,
        min_ciar: float | None = None,
        limit: int = 20,
    ) -> list[MemoryResult]:
        self.calls.append(("L2", scope, query))
        return [
            _result(
                "L2",
                "fact-skill-a",
                scope,
                {
                    "domain": "skill_factory",
                    "skill_name": "inventory-router",
                    "run_id": "run-a",
                    "qa_status": "failed",
                    "api_token": "secret",
                },
            ),
            _result("L2", "fact-other", scope, {"skill_name": "other-skill"}),
        ]

    async def search_l3_episodes(
        self,
        scope: ScopeEnvelope,
        query: str,
        limit: int = 10,
    ) -> list[MemoryResult]:
        self.calls.append(("L3", scope, query))
        return [
            _result(
                "L3",
                "episode-a",
                scope,
                {
                    "domain": "skill_factory",
                    "skill_name": "inventory-router",
                    "ctt_id": "ctt-42",
                    "run_id": "run-a",
                    "qa_status": "failed",
                    "active_tool_status": "stale",
                    "repair_action": "schema patch",
                },
            )
        ]

    async def search_l4_knowledge(
        self,
        scope: ScopeEnvelope,
        query: str,
        limit: int = 10,
    ) -> list[MemoryResult]:
        self.calls.append(("L4", scope, query))
        return [
            _result(
                "L4",
                "knowledge-a",
                scope,
                {
                    "domain": "skill_factory",
                    "skill_name": "inventory-router",
                    "ctt_id": "ctt-42",
                    "artifact_kind": "validated_skill_summary",
                },
            )
        ]


class DeterministicSkillFactoryGateway:
    def __init__(self) -> None:
        self.project_id = "scm-skill-factory"
        self.calls: list[tuple[ScopeEnvelope, dict[str, str], int]] = []

    async def list_skill_factory_domain_records(
        self,
        scope: ScopeEnvelope,
        filters: dict[str, str],
        limit: int = 20,
    ) -> list[MemoryResult]:
        self.calls.append((scope, filters, limit))
        return [
            _result(
                "L2",
                "fact-a",
                scope,
                {
                    "domain": "skill_factory",
                    "skill_name": "readiness_demo_skill",
                    "ctt_id": "readiness-ctt-001",
                    "run_id": "skill-run-001",
                    "qa_status": "failed",
                    "active_tool_status": "stale",
                    "api_token": "secret",
                },
            ),
            _result(
                "L3",
                "episode-a",
                scope,
                {
                    "domain": "skill_factory",
                    "skill_name": "readiness_demo_skill",
                    "ctt_id": "readiness-ctt-001",
                    "run_id": "skill-run-001",
                    "qa_status": "failed",
                    "active_tool_status": "stale",
                },
            ),
            _result(
                "L4",
                "knowledge-a",
                scope,
                {
                    "domain": "skill_factory",
                    "skill_name": "readiness_demo_skill",
                    "ctt_id": "readiness-ctt-001",
                    "run_id": "skill-run-001",
                    "qa_status": "failed",
                    "active_tool_status": "stale",
                },
            ),
            _result(
                "L3",
                "episode-other",
                scope,
                {
                    "domain": "skill_factory",
                    "skill_name": "other-skill",
                    "ctt_id": "other-ctt",
                    "run_id": "other-run",
                    "qa_status": "passed",
                    "active_tool_status": "fresh",
                },
            ),
        ]


class DeterministicCognitiveSandwichGateway:
    def __init__(self) -> None:
        self.project_id = "scm-cognitive-sandwich"
        self.calls: list[tuple[ScopeEnvelope, dict[str, str], int]] = []

    async def list_cognitive_sandwich_domain_records(
        self,
        scope: ScopeEnvelope,
        filters: dict[str, str],
        limit: int = 20,
    ) -> list[MemoryResult]:
        self.calls.append((scope, filters, limit))
        metadata = {
            "domain": "cognitive_sandwich",
            "artifact_id": "artifact-readiness-001",
            "run_id": "artifact-run-001",
            "client_session_id": "session-readiness-001",
            "incident_id": "incident-readiness-001",
            "source_system": "deterministic_solver",
            "api_token": "secret",
        }
        return [
            _result(
                "L2",
                "fact-feedback",
                scope,
                {
                    **metadata,
                    "revision_id": "revision-001",
                    "feedback_id": "feedback-001",
                    "revision_number": 1,
                    "verification_state": "infeasible",
                    "feedback_type": "solver_iis",
                    "payload_hash": "sha256:draft",
                },
            ),
            _result(
                "L3",
                "episode-repair",
                scope,
                {
                    **metadata,
                    "revision_id": "revision-002",
                    "parent_revision_id": "revision-001",
                    "revision_number": 2,
                    "verification_state": "feasible",
                    "payload_hash": "sha256:repair",
                },
            ),
            _result(
                "L4",
                "knowledge-report",
                scope,
                {
                    **metadata,
                    "commit_id": "commit-001",
                    "artifact_status": "committed",
                    "revision_id": "revision-002",
                    "revision_number": 2,
                    "payload_hash": "sha256:repair",
                },
            ),
            _result(
                "L3",
                "episode-other",
                scope,
                {
                    **metadata,
                    "artifact_id": "other-artifact",
                    "run_id": "other-run",
                    "incident_id": "other-incident",
                },
            ),
        ]


@pytest.mark.asyncio
async def test_skill_factory_skill_view_filters_and_redacts_metadata() -> None:
    gateway = SkillFactoryGateway()
    service = SkillFactoryDomainViewService(gateway)

    view = await service.skill_view("inventory-router")

    assert view["domain_pack"] == "skill-factory"
    assert view["project_id"] == "scm-skill-factory"
    assert view["filters"] == {"skill_name": "inventory-router"}
    assert view["counts"] == {"items": 3, "l2": 1, "l3": 1, "l4": 1}
    assert {item["source_id"] for item in view["items"]} == {
        "fact-skill-a",
        "episode-a",
        "knowledge-a",
    }
    assert view["items"][0]["metadata"]["api_token"] == "[REDACTED]"
    assert gateway.calls[0][1].domain_ids == {"skill_name": "inventory-router"}
    assert gateway.calls[0][1].visibility_scope == "benchmark_runtime"


@pytest.mark.asyncio
async def test_skill_factory_status_view_returns_run_summaries() -> None:
    service = SkillFactoryDomainViewService(SkillFactoryGateway())

    view = await service.qa_status_runs("failed")

    assert view["counts"]["runs"] == 1
    assert view["runs"] == [
        {
            "run_id": "run-a",
            "skill_names": ["inventory-router"],
            "ctt_ids": ["ctt-42"],
            "qa_statuses": ["failed"],
            "active_tool_statuses": ["stale"],
            "source_ids": ["fact-skill-a", "episode-a"],
        }
    ]


@pytest.mark.asyncio
async def test_skill_factory_run_views_use_deterministic_metadata_projection() -> None:
    gateway = DeterministicSkillFactoryGateway()
    service = SkillFactoryDomainViewService(gateway)

    run_view = await service.run_episodes("skill-run-001")
    qa_view = await service.qa_status_runs("failed")
    active_tool_view = await service.active_tool_status_runs("stale")

    assert run_view["counts"]["items"] == 1
    assert run_view["counts"]["l3"] == 1
    assert run_view["items"][0]["source_id"] == "episode-a"
    assert run_view["items"][0]["metadata"]["run_id"] == "skill-run-001"

    assert qa_view["counts"]["items"] == 3
    assert qa_view["counts"]["runs"] == 1
    assert qa_view["runs"][0]["run_id"] == "skill-run-001"
    assert qa_view["runs"][0]["skill_names"] == ["readiness_demo_skill"]
    assert qa_view["runs"][0]["ctt_ids"] == ["readiness-ctt-001"]
    assert qa_view["runs"][0]["qa_statuses"] == ["failed"]
    assert qa_view["runs"][0]["active_tool_statuses"] == ["stale"]
    assert "episode-other" not in {item["source_id"] for item in qa_view["items"]}

    assert active_tool_view["counts"]["items"] == 3
    assert active_tool_view["counts"]["runs"] == 1
    assert active_tool_view["runs"][0]["run_id"] == "skill-run-001"
    assert active_tool_view["items"][0]["metadata"]["api_token"] == "[REDACTED]"
    assert gateway.calls[0][0].domain_ids == {"run_id": "skill-run-001"}


@pytest.mark.asyncio
async def test_cognitive_sandwich_artifact_lineage_orders_and_redacts_nodes() -> None:
    gateway = DeterministicCognitiveSandwichGateway()
    service = CognitiveSandwichDomainViewService(gateway)

    view = await service.artifact_lineage("artifact-readiness-001")

    assert view["domain_pack"] == "cognitive-sandwich"
    assert view["project_id"] == "scm-cognitive-sandwich"
    assert view["filters"] == {"artifact_id": "artifact-readiness-001"}
    assert view["counts"]["items"] == 3
    assert [node["node_type"] for node in view["nodes"]] == [
        "feedback",
        "revision",
        "commit",
    ]
    assert [node["source_id"] for node in view["nodes"]] == [
        "fact-feedback",
        "episode-repair",
        "knowledge-report",
    ]
    assert view["items"][0]["metadata"]["api_token"] == "[REDACTED]"
    assert gateway.calls[0][0].agent_id == "cognitive-sandwich-domain-pack"
    assert gateway.calls[0][0].domain_ids == {"artifact_id": "artifact-readiness-001"}


@pytest.mark.asyncio
async def test_cognitive_sandwich_artifact_and_evidence_views_filter_records() -> None:
    service = CognitiveSandwichDomainViewService(DeterministicCognitiveSandwichGateway())

    session_view = await service.session_artifacts("session-readiness-001")
    run_view = await service.run_artifacts("artifact-run-001")
    evidence_view = await service.run_evidence("artifact-run-001")
    reports_view = await service.incident_reports("incident-readiness-001")

    assert session_view["counts"]["artifacts"] == 2
    artifact_summary = next(
        item
        for item in session_view["artifacts"]
        if item["artifact_id"] == "artifact-readiness-001"
    )
    assert artifact_summary["feedback_ids"] == ["feedback-001"]
    assert artifact_summary["commit_ids"] == ["commit-001"]
    assert session_view["counts"]["l4"] == 1

    assert run_view["counts"]["items"] == 3
    assert run_view["counts"]["l4"] == 1
    assert "episode-other" not in {item["source_id"] for item in run_view["items"]}

    assert evidence_view["counts"]["evidence"] == 3
    assert evidence_view["counts"]["l4"] == 1
    assert evidence_view["evidence"][0]["artifact_id"] == "artifact-readiness-001"
    assert evidence_view["evidence"][0]["source_system"] == "deterministic_solver"

    assert reports_view["counts"]["items"] == 1
    assert reports_view["counts"]["l4"] == 1
    assert reports_view["items"][0]["source_id"] == "knowledge-report"


def _result(
    tier: str,
    source_id: str,
    scope: ScopeEnvelope,
    metadata: dict[str, Any],
) -> MemoryResult:
    return MemoryResult(
        content=f"{tier} content for {metadata}",
        tier=tier,
        score=0.8,
        source_id=source_id,
        metadata=metadata,
        provenance=Provenance(
            source_tier=tier,
            source_id=source_id,
            session_id=scope.session_id,
            agent_id=scope.agent_id,
            task_id=scope.task_id,
            run_id=metadata.get("run_id"),
            metadata=metadata,
        ),
    )
