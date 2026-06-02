import pytest

from src.memory.models import Fact
from src.memory.services import MemoryGatewayService, PermissionPolicy, ScopeEnvelope
from src.memory.services.permissions import YAAMPermissionError


@pytest.mark.asyncio
async def test_query_memory_normalizes_unified_results(mocker) -> None:
    memory_system = mocker.Mock()
    memory_system.query_memory = mocker.AsyncMock(
        return_value=[
            {
                "content": "Crane maintenance affects dock three.",
                "tier": "L2",
                "score": 0.7,
                "metadata": {"fact_id": "fact-a", "api_token": "secret"},
            }
        ]
    )
    service = MemoryGatewayService(memory_system)
    scope = ScopeEnvelope(session_id="session-a", agent_id="agent-a")

    results = await service.query_memory(scope, query="dock status", limit=1)

    assert len(results) == 1
    assert results[0].source_id == "fact-a"
    assert results[0].metadata["api_token"] == "[REDACTED]"
    memory_system.query_memory.assert_awaited_once()


@pytest.mark.asyncio
async def test_store_l2_fact_denies_writes_by_default(mocker) -> None:
    memory_system = mocker.Mock()
    memory_system.l2_tier = mocker.Mock()
    service = MemoryGatewayService(memory_system)
    scope = ScopeEnvelope(session_id="session-a", agent_id="agent-a")

    with pytest.raises(YAAMPermissionError):
        await service.store_l2_fact(scope, content="A scoped fact.")


@pytest.mark.asyncio
async def test_store_l2_fact_persists_when_allowlisted(mocker) -> None:
    l2_tier = mocker.Mock()
    l2_tier.store = mocker.AsyncMock(return_value="fact-stored")
    memory_system = mocker.Mock()
    memory_system.l2_tier = l2_tier
    service = MemoryGatewayService(
        memory_system,
        PermissionPolicy(
            enable_writes=True,
            allowlisted_tools=frozenset({"yaam.l2.store_fact"}),
        ),
    )
    scope = ScopeEnvelope(session_id="session-a", agent_id="agent-a", task_id="task-a")

    ack = await service.store_l2_fact(
        scope,
        content="A scoped fact.",
        metadata={"password": "secret", "source": "test"},
    )

    assert ack.created_id == "fact-stored"
    assert ack.provenance is not None
    assert ack.provenance.agent_id == "agent-a"
    stored_fact = l2_tier.store.await_args.args[0]
    assert stored_fact.session_id == "test:session-a"
    assert stored_fact.metadata["client_session_id"] == "session-a"
    assert stored_fact.metadata["project_id"] == "test"
    assert stored_fact.metadata["password"] == "[REDACTED]"
    assert stored_fact.metadata["task_id"] == "task-a"


@pytest.mark.asyncio
async def test_assimilate_l3_episode_preserves_metadata_run_id_when_scope_omits_it(
    mocker,
) -> None:
    l3_tier = mocker.Mock()
    l3_tier.store = mocker.AsyncMock(return_value="episode-stored")
    llm_client = mocker.Mock()
    llm_client.get_embedding = mocker.AsyncMock(return_value=[0.1] * 64)
    llm_client.generate = mocker.AsyncMock(return_value="{}")
    memory_system = mocker.Mock()
    memory_system.l3_tier = l3_tier
    memory_system.llm_client = llm_client
    service = MemoryGatewayService(
        memory_system,
        PermissionPolicy(
            enable_writes=True,
            enable_lifecycle=True,
            allowlisted_tools=frozenset({"yaam.l3.assimilate_episode"}),
        ),
        project_id="scm-skill-factory",
    )
    scope = ScopeEnvelope(
        session_id="readiness-session",
        agent_id="skill-factory-verifier",
        caller_role="benchmark_runtime_agent",
        visibility_scope="benchmark_runtime",
    )

    ack = await service.assimilate_l3_episode(
        scope,
        text_to_assimilate="Synthetic Skill Factory repair episode for readiness.",
        metadata={
            "domain": "skill_factory",
            "run_id": "skill-run-001",
            "task_id": "metadata-task",
            "qa_status": "failed",
        },
    )

    stored_input = l3_tier.store.await_args.args[0]
    assert ack.created_id == "episode-stored"
    assert stored_input.episode.metadata["run_id"] == "skill-run-001"
    assert stored_input.episode.metadata["task_id"] == "metadata-task"
    assert stored_input.episode.metadata["client_session_id"] == "readiness-session"
    assert stored_input.episode.metadata["project_id"] == "scm-skill-factory"
    assert ack.provenance.metadata["run_id"] == "skill-run-001"


@pytest.mark.asyncio
async def test_write_metadata_scope_values_override_metadata_when_present(mocker) -> None:
    l2_tier = mocker.Mock()
    l2_tier.store = mocker.AsyncMock(return_value="fact-stored")
    memory_system = mocker.Mock()
    memory_system.l2_tier = l2_tier
    service = MemoryGatewayService(
        memory_system,
        PermissionPolicy(
            enable_writes=True,
            allowlisted_tools=frozenset({"yaam.l2.store_fact"}),
        ),
    )
    scope = ScopeEnvelope(
        session_id="session-a",
        agent_id="agent-a",
        task_id="scope-task",
        run_id="scope-run",
    )

    await service.store_l2_fact(
        scope,
        content="A scoped fact.",
        metadata={"task_id": "metadata-task", "run_id": "metadata-run"},
    )

    stored_fact = l2_tier.store.await_args.args[0]
    assert stored_fact.metadata["task_id"] == "scope-task"
    assert stored_fact.metadata["run_id"] == "scope-run"


@pytest.mark.asyncio
async def test_health_check_redacts_tier_health(mocker) -> None:
    l2_tier = mocker.Mock()
    l2_tier.health_check = mocker.AsyncMock(
        return_value={"status": "ok", "connection_token": "secret"}
    )
    memory_system = mocker.Mock()
    memory_system.l1_tier = None
    memory_system.l2_tier = l2_tier
    memory_system.l3_tier = None
    memory_system.l4_tier = None
    service = MemoryGatewayService(memory_system)

    health = await service.health_check()

    assert health.status == "ok"
    assert health.tiers["L2"]["connection_token"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_get_fact_allows_wildcard_resource_scope(mocker) -> None:
    l2_tier = mocker.Mock()
    l2_tier.retrieve = mocker.AsyncMock(
        return_value=mocker.Mock(
            fact_id="fact-a",
            session_id="session-a",
            content="A scoped fact.",
            ciar_score=0.9,
            metadata={},
            extracted_at=None,
            created_at=None,
        )
    )
    memory_system = mocker.Mock()
    memory_system.l2_tier = l2_tier
    service = MemoryGatewayService(memory_system)

    result = await service.get_fact(ScopeEnvelope(session_id="*", agent_id="reader"), "fact-a")

    assert result is not None
    assert result.source_id == "fact-a"


@pytest.mark.asyncio
async def test_get_fact_rejects_lookup_mismatch_and_other_project(mocker) -> None:
    l2_tier = mocker.Mock()
    l2_tier.retrieve = mocker.AsyncMock(
        return_value=mocker.Mock(
            fact_id="fact-b",
            session_id="scm-skill-factory:session-a",
            content="A different project fact.",
            ciar_score=0.9,
            metadata={"project_id": "scm-skill-factory"},
            extracted_at=None,
            created_at=None,
        )
    )
    memory_system = mocker.Mock()
    memory_system.l2_tier = l2_tier
    service = MemoryGatewayService(memory_system, project_id="scm-cognitive-sandwich")

    result = await service.get_fact(
        ScopeEnvelope(session_id="*", agent_id="reader"),
        "nonexistent-readiness-fact",
    )

    assert result is None


@pytest.mark.asyncio
async def test_benchmark_query_filters_hidden_records(mocker) -> None:
    memory_system = mocker.Mock()
    memory_system.query_memory = mocker.AsyncMock(
        return_value=[
            {
                "content": "Visible benchmark-safe evidence.",
                "tier": "L2",
                "score": 0.9,
                "metadata": {"fact_id": "fact-visible", "visibility_scope": "benchmark_runtime"},
            },
            {
                "content": "Hidden gold answer should never reach runtime retrieval.",
                "tier": "L2",
                "score": 0.9,
                "metadata": {"fact_id": "fact-hidden", "visibility_scope": "maintainer_only"},
            },
        ]
    )
    service = MemoryGatewayService(memory_system)
    scope = ScopeEnvelope(
        session_id="session-a",
        agent_id="agent-a",
        caller_role="benchmark_runtime_agent",
        visibility_scope="benchmark_runtime",
    )

    results, guard = await service.query_memory_checked(
        scope,
        query="certification task context",
        limit=2,
    )

    assert [result.source_id for result in results] == ["fact-visible"]
    assert guard.leakage_guard_passed is True
    assert guard.filtered_item_count == 1
    assert guard.warnings[0].code == "leakage_guard.filtered"


@pytest.mark.asyncio
async def test_generic_query_does_not_apply_benchmark_guard(mocker) -> None:
    memory_system = mocker.Mock()
    memory_system.query_memory = mocker.AsyncMock(
        return_value=[
            {
                "content": "Maintainer-only operational note.",
                "tier": "L2",
                "score": 0.9,
                "metadata": {"fact_id": "fact-hidden", "visibility_scope": "maintainer_only"},
            }
        ]
    )
    service = MemoryGatewayService(memory_system)
    scope = ScopeEnvelope(session_id="session-a", agent_id="agent-a")

    results, guard = await service.query_memory_checked(scope, query="ops note", limit=1)

    assert [result.source_id for result in results] == ["fact-hidden"]
    assert guard.leakage_guard_passed is False
    assert guard.checked_item_count == 0


@pytest.mark.asyncio
async def test_curation_write_requires_maintainer_role_even_when_allowlisted(mocker) -> None:
    memory_system = mocker.Mock()
    memory_system.l2_tier = mocker.Mock()
    service = MemoryGatewayService(
        memory_system,
        PermissionPolicy(
            enable_writes=True,
            allowlisted_tools=frozenset({"yaam.curation.record_decision"}),
        ),
    )
    scope = ScopeEnvelope(
        session_id="session-a",
        agent_id="agent-a",
        caller_role="benchmark_runtime_agent",
    )

    with pytest.raises(YAAMPermissionError) as exc_info:
        await service.record_curation_decision(
            scope,
            task_id="task-a",
            decision="accepted",
            reason="Maintainer-only source triad review.",
            source_triad={"prompt": "prompt-a", "oracle": "oracle-a", "rubric": "rubric-a"},
            reviewer="reviewer-a",
        )

    assert exc_info.value.payload.code == "permission.role_denied"
    assert exc_info.value.payload.operation == "yaam.curation.record_decision"


@pytest.mark.asyncio
async def test_curation_write_stores_maintainer_only_metadata(mocker) -> None:
    l2_tier = mocker.Mock()
    l2_tier.store = mocker.AsyncMock(return_value=None)
    memory_system = mocker.Mock()
    memory_system.l2_tier = l2_tier
    service = MemoryGatewayService(
        memory_system,
        PermissionPolicy(
            enable_writes=True,
            allowlisted_tools=frozenset({"yaam.curation.record_decision"}),
        ),
    )
    scope = ScopeEnvelope(
        session_id="session-a",
        agent_id="agent-a",
        caller_role="benchmark_maintainer",
    )

    ack = await service.record_curation_decision(
        scope,
        task_id="task-a",
        decision="rejected",
        reason="Task leaks gold answer.",
        source_triad={"prompt": "prompt-a", "oracle": "oracle-a", "rubric": "rubric-a"},
        reviewer="reviewer-a",
        metadata={"api_token": "secret"},
    )

    stored_fact = l2_tier.store.await_args.args[0]
    assert ack.operation == "yaam.curation.record_decision"
    assert ack.created_id.startswith("curation-")
    assert stored_fact.metadata["record_type"] == "scm_cert_bench_curation_decision"
    assert stored_fact.metadata["visibility_scope"] == "maintainer_only"
    assert stored_fact.metadata["reviewer"] == "reviewer-a"
    assert stored_fact.metadata["api_token"] == "[REDACTED]"
    assert ack.provenance.metadata["visibility_scope"] == "maintainer_only"


@pytest.mark.asyncio
async def test_trace_correlation_write_and_lookup_use_redacted_l2_records(mocker) -> None:
    trace_fact = Fact(
        fact_id="tracecorr-a",
        session_id="session-a",
        content="Trace correlation.",
        metadata={
            "record_type": "scm_cert_bench_trace_correlation",
            "correlation_id": "tracecorr-a",
            "trace_id": "phoenix-trace-a",
            "task_id": "task-a",
            "run_id": "run-a",
            "artifact_ref": "artifacts/run-a.jsonl",
            "openrouter_call_id": "or-call-a",
            "linked_memory_ids": ["fact-a"],
            "trace_status": "verified",
        },
    )
    l2_tier = mocker.Mock()
    l2_tier.store = mocker.AsyncMock(return_value=None)
    l2_tier.query_by_session = mocker.AsyncMock(return_value=[trace_fact])
    memory_system = mocker.Mock()
    memory_system.l2_tier = l2_tier
    service = MemoryGatewayService(
        memory_system,
        PermissionPolicy(
            enable_writes=True,
            allowlisted_tools=frozenset({"yaam.trace.record_correlation"}),
        ),
    )
    scope = ScopeEnvelope(
        session_id="session-a",
        agent_id="agent-a",
        task_id="task-a",
        run_id="run-a",
        caller_role="post_run_ingestion_service",
    )

    ack = await service.record_trace_correlation(
        scope,
        trace_id="phoenix-trace-a",
        artifact_ref="artifacts/run-a.jsonl",
        openrouter_call_id="or-call-a",
        linked_memory_ids=["fact-a"],
        metadata={"password": "secret"},
    )
    records = await service.lookup_trace_correlation(scope, trace_id="phoenix-trace-a")

    stored_fact = l2_tier.store.await_args.args[0]
    assert ack.operation == "yaam.trace.record_correlation"
    assert stored_fact.metadata["password"] == "[REDACTED]"
    assert records[0].correlation_id == "tracecorr-a"
    assert records[0].trace_id == "phoenix-trace-a"
    assert records[0].openrouter_call_id == "or-call-a"
    assert records[0].linked_memory_ids == ["fact-a"]


@pytest.mark.asyncio
async def test_contradiction_review_uses_explicit_evidence_relations(mocker) -> None:
    memory_system = mocker.Mock()
    memory_system.query_memory = mocker.AsyncMock(
        return_value=[
            {
                "content": "Evidence supports claim A.",
                "tier": "L2",
                "score": 0.8,
                "metadata": {"fact_id": "support-a", "evidence_relation": "support"},
            },
            {
                "content": "Evidence refutes claim A.",
                "tier": "L2",
                "score": 0.8,
                "metadata": {"fact_id": "conflict-a", "evidence_relation": "refutes"},
            },
        ]
    )
    service = MemoryGatewayService(memory_system)
    scope = ScopeEnvelope(session_id="session-a", agent_id="agent-a")

    review = await service.review_contradiction(
        scope,
        claims=["claim A"],
        expected_behavior="refuse unsafe answer",
    )

    assert review.contradiction_detected is True
    assert review.infeasibility_reason is not None
    assert review.safe_refusal_rationale is not None
    assert [item.source_id for item in review.supporting_evidence] == ["support-a"]
    assert [item.source_id for item in review.conflicting_evidence] == ["conflict-a"]


@pytest.mark.asyncio
async def test_list_skill_factory_domain_records_projects_and_filters_metadata(mocker) -> None:
    skill_metadata = {
        "project_id": "scm-skill-factory",
        "domain": "skill_factory",
        "skill_name": "readiness_demo_skill",
        "ctt_id": "readiness-ctt-001",
        "run_id": "skill-run-001",
        "qa_status": "failed",
        "active_tool_status": "stale",
    }
    l2_tier = mocker.Mock()
    l2_tier.query = mocker.AsyncMock(
        return_value=[
            Fact(
                fact_id="fact-skill",
                session_id="scm-skill-factory:session-a",
                content="Skill Factory run skill-run-001 failed QA.",
                metadata={**skill_metadata, "api_token": "secret"},
            ),
            Fact(
                fact_id="fact-other-domain",
                session_id="scm-skill-factory:session-a",
                content="Unrelated run skill-run-001.",
                metadata={**skill_metadata, "domain": "other"},
            ),
            Fact(
                fact_id="fact-other-project",
                session_id="other-project:session-a",
                content="Skill Factory run skill-run-001 from another project.",
                metadata={**skill_metadata, "project_id": "other-project"},
            ),
        ]
    )
    qdrant = mocker.Mock()
    qdrant.scroll = mocker.AsyncMock(
        return_value=[
            {
                "episode_id": "episode-skill",
                "session_id": "scm-skill-factory:session-a",
                "summary": (
                    "Skill Factory episode skill_name=readiness_demo_skill "
                    "ctt_id=readiness-ctt-001 run_id=skill-run-001 "
                    "qa_status=failed active_tool_status=stale."
                ),
                "importance_score": 0.8,
                "metadata": {"project_id": "scm-skill-factory"},
            },
            {
                "episode_id": "episode-other-run",
                "session_id": "scm-skill-factory:session-a",
                "summary": "Skill Factory episode for another run.",
                "importance_score": 0.7,
                "metadata": {**skill_metadata, "run_id": "other-run"},
            },
        ]
    )
    l3_tier = mocker.Mock()
    l3_tier.collection_name = "yaam-scm-skill-factory-episodes_v2"
    l3_tier.qdrant = qdrant
    l4_tier = mocker.Mock()
    l4_tier.search = mocker.AsyncMock(
        return_value=[
            {
                "knowledge_id": "knowledge-skill",
                "session_id": "scm-skill-factory:session-a",
                "content": "Skill Factory knowledge for skill-run-001.",
                "confidence_score": 0.9,
                "metadata": skill_metadata,
            }
        ]
    )
    memory_system = mocker.Mock()
    memory_system.l2_tier = l2_tier
    memory_system.l3_tier = l3_tier
    memory_system.l4_tier = l4_tier
    service = MemoryGatewayService(memory_system, project_id="scm-skill-factory")
    scope = ScopeEnvelope(session_id="*", agent_id="skill-factory-domain-pack")

    records = await service.list_skill_factory_domain_records(
        scope,
        filters={"run_id": "skill-run-001"},
        limit=10,
    )

    assert [record.source_id for record in records] == [
        "fact-skill",
        "episode-skill",
        "knowledge-skill",
    ]
    assert records[0].metadata["api_token"] == "[REDACTED]"
    qdrant.scroll.assert_awaited_once()
    assert qdrant.scroll.await_args.kwargs["filter_dict"] == {
        "must": [
            {"key": "project_id", "match": {"value": "scm-skill-factory"}},
        ]
    }


@pytest.mark.asyncio
async def test_list_cognitive_sandwich_domain_records_projects_and_filters_metadata(
    mocker,
) -> None:
    artifact_metadata = {
        "project_id": "scm-cognitive-sandwich",
        "domain": "cognitive_sandwich",
        "artifact_id": "artifact-readiness-001",
        "revision_id": "revision-001",
        "feedback_id": "feedback-001",
        "run_id": "artifact-run-001",
        "thread_id": "thread-001",
        "incident_id": "incident-readiness-001",
        "verification_state": "infeasible",
        "source_system": "deterministic_solver",
    }
    l2_tier = mocker.Mock()
    l2_tier.query = mocker.AsyncMock(
        return_value=[
            Fact(
                fact_id="fact-feedback",
                session_id="scm-cognitive-sandwich:session-a",
                content="Cognitive Sandwich solver feedback for artifact-readiness-001.",
                metadata={**artifact_metadata, "api_token": "secret"},
            ),
            Fact(
                fact_id="fact-other-domain",
                session_id="scm-cognitive-sandwich:session-a",
                content="Unrelated artifact-readiness-001.",
                metadata={**artifact_metadata, "domain": "other"},
            ),
            Fact(
                fact_id="fact-other-project",
                session_id="other-project:session-a",
                content="Cognitive Sandwich artifact artifact-readiness-001 from another project.",
                metadata={**artifact_metadata, "project_id": "other-project"},
            ),
        ]
    )
    qdrant = mocker.Mock()
    qdrant.scroll = mocker.AsyncMock(
        return_value=[
            {
                "episode_id": "episode-artifact",
                "session_id": "scm-cognitive-sandwich:session-a",
                "summary": (
                    "Cognitive Sandwich repair episode artifact_id=artifact-readiness-001 "
                    "run_id=artifact-run-001 incident_id=incident-readiness-001."
                ),
                "importance_score": 0.8,
                "metadata": {"project_id": "scm-cognitive-sandwich"},
            },
            {
                "episode_id": "episode-other-artifact",
                "session_id": "scm-cognitive-sandwich:session-a",
                "summary": "Cognitive Sandwich episode for another artifact.",
                "importance_score": 0.7,
                "metadata": {**artifact_metadata, "artifact_id": "other-artifact"},
            },
        ]
    )
    l3_tier = mocker.Mock()
    l3_tier.collection_name = "yaam-scm-cognitive-sandwich-episodes"
    l3_tier.qdrant = qdrant
    l4_tier = mocker.Mock()
    l4_tier.search = mocker.AsyncMock(
        return_value=[
            {
                "knowledge_id": "knowledge-report",
                "session_id": "scm-cognitive-sandwich:session-a",
                "content": "Cognitive Sandwich final report for artifact-readiness-001.",
                "confidence_score": 0.9,
                "metadata": {
                    **artifact_metadata,
                    "commit_id": "commit-001",
                    "artifact_status": "committed",
                },
            }
        ]
    )
    memory_system = mocker.Mock()
    memory_system.l2_tier = l2_tier
    memory_system.l3_tier = l3_tier
    memory_system.l4_tier = l4_tier
    service = MemoryGatewayService(memory_system, project_id="scm-cognitive-sandwich")
    scope = ScopeEnvelope(session_id="*", agent_id="cognitive-sandwich-domain-pack")

    records = await service.list_cognitive_sandwich_domain_records(
        scope,
        filters={"artifact_id": "artifact-readiness-001"},
        limit=10,
    )

    assert [record.source_id for record in records] == [
        "fact-feedback",
        "episode-artifact",
        "knowledge-report",
    ]
    assert records[0].metadata["api_token"] == "[REDACTED]"
    first_l4_call = l4_tier.search.await_args_list[0]
    assert first_l4_call.kwargs["query_text"] == "*"
    assert (
        first_l4_call.kwargs["filter_by"]
        == "project_id:=`scm-cognitive-sandwich` && domain:=`cognitive_sandwich` "
        "&& artifact_id:=`artifact-readiness-001`"
    )
    qdrant.scroll.assert_awaited_once()
    assert qdrant.scroll.await_args.kwargs["filter_dict"] == {
        "must": [
            {"key": "project_id", "match": {"value": "scm-cognitive-sandwich"}},
        ]
    }


@pytest.mark.asyncio
async def test_cognitive_sandwich_l4_exact_metadata_projection_for_session_and_incident(
    mocker,
) -> None:
    metadata = {
        "project_id": "scm-cognitive-sandwich",
        "domain": "cognitive_sandwich",
        "client_session_id": "session-readiness-001",
        "artifact_id": "artifact-readiness-001",
        "run_id": "artifact-run-001",
        "incident_id": "incident-readiness-001",
        "commit_id": "commit-001",
        "artifact_status": "committed",
    }
    l2_tier = mocker.Mock()
    l2_tier.query = mocker.AsyncMock(return_value=[])
    qdrant = mocker.Mock()
    qdrant.scroll = mocker.AsyncMock(return_value=[])
    l3_tier = mocker.Mock()
    l3_tier.collection_name = "yaam-scm-cognitive-sandwich-episodes"
    l3_tier.qdrant = qdrant
    l4_tier = mocker.Mock()

    async def l4_exact_search(**kwargs):
        filter_by = kwargs.get("filter_by", "")
        if "artifact_id:=`artifact-readiness-001`" in filter_by:
            return [
                {
                    "knowledge_id": "knowledge-artifact-report",
                    "session_id": "scm-cognitive-sandwich:session-readiness-001",
                    "content": "Artifact report for artifact-readiness-001.",
                    "confidence_score": 0.9,
                    "metadata": metadata,
                }
            ]
        if "client_session_id:=`session-readiness-001`" in filter_by:
            return [
                {
                    "knowledge_id": "knowledge-session-report",
                    "session_id": "scm-cognitive-sandwich:session-readiness-001",
                    "content": "Final report stored for session-readiness-001.",
                    "confidence_score": 0.9,
                    "metadata": metadata,
                }
            ]
        if "run_id:=`artifact-run-001`" in filter_by:
            return [
                {
                    "knowledge_id": "knowledge-run-report",
                    "session_id": "scm-cognitive-sandwich:session-readiness-001",
                    "content": "Run report for artifact-run-001.",
                    "confidence_score": 0.9,
                    "metadata": metadata,
                }
            ]
        if "incident_id:=`incident-readiness-001`" in filter_by:
            return [
                {
                    "knowledge_id": "knowledge-incident-report",
                    "session_id": "scm-cognitive-sandwich:session-readiness-001",
                    "content": "Incident report for incident-readiness-001.",
                    "confidence_score": 0.9,
                    "metadata": metadata,
                }
            ]
        return []

    l4_tier.search_by_exact_metadata = mocker.AsyncMock(side_effect=l4_exact_search)
    l4_tier.search = mocker.AsyncMock(return_value=[])
    memory_system = mocker.Mock()
    memory_system.l2_tier = l2_tier
    memory_system.l3_tier = l3_tier
    memory_system.l4_tier = l4_tier
    service = MemoryGatewayService(memory_system, project_id="scm-cognitive-sandwich")
    scope = ScopeEnvelope(session_id="*", agent_id="cognitive-sandwich-domain-pack")

    artifact_records = await service.list_cognitive_sandwich_domain_records(
        scope,
        filters={"artifact_id": "artifact-readiness-001"},
        limit=10,
    )
    session_records = await service.list_cognitive_sandwich_domain_records(
        scope,
        filters={"client_session_id": "session-readiness-001"},
        limit=10,
    )
    run_records = await service.list_cognitive_sandwich_domain_records(
        scope,
        filters={"run_id": "artifact-run-001"},
        limit=10,
    )
    incident_records = await service.list_cognitive_sandwich_domain_records(
        scope,
        filters={"incident_id": "incident-readiness-001"},
        limit=10,
    )

    assert [record.source_id for record in artifact_records] == ["knowledge-artifact-report"]
    assert [record.source_id for record in session_records] == ["knowledge-session-report"]
    assert [record.source_id for record in run_records] == ["knowledge-run-report"]
    assert [record.source_id for record in incident_records] == ["knowledge-incident-report"]
    filter_by_values = [
        call.kwargs.get("filter_by")
        for call in l4_tier.search_by_exact_metadata.await_args_list
        if call.kwargs.get("filter_by")
    ]
    assert any("artifact_id:=`artifact-readiness-001`" in item for item in filter_by_values)
    assert any("client_session_id:=`session-readiness-001`" in item for item in filter_by_values)
    assert any("run_id:=`artifact-run-001`" in item for item in filter_by_values)
    assert any("incident_id:=`incident-readiness-001`" in item for item in filter_by_values)
