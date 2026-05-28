import httpx
import pytest
from fastapi import FastAPI

from src.api.v2_router import router
from src.evaluation.agent_wrapper import AgentWrapperState
from src.memory.ciar_formula import calculate_ciar_score
from src.memory.models import Fact


def _build_app(mocker, *, memory_system=None, l2_tier=None, l3_tier=None, l4_tier=None):
    app = FastAPI()
    app.include_router(router)
    app.state.wrapper = AgentWrapperState(
        agent=mocker.Mock(),
        memory_system=memory_system or mocker.Mock(),
        l1_tier=mocker.Mock(),
        l2_tier=l2_tier or mocker.Mock(),
        l3_tier=l3_tier,
        l4_tier=l4_tier,
        redis_client=mocker.Mock(),
        agent_type="test",
        agent_variant="test",
        session_prefix="test",
        rate_limiter=mocker.Mock(),
    )
    return app


@pytest.mark.asyncio
async def test_v2_l2_store_uses_consistent_ciar_components(mocker):
    """The v2 semantic L2 store route should not create contradictory CIAR data."""
    captured = {}
    l2_tier = mocker.Mock()

    async def store_fact(fact):
        captured["fact"] = fact
        return fact.fact_id

    l2_tier.store = mocker.AsyncMock(side_effect=store_fact)
    l2_tier.query_by_session = mocker.AsyncMock(return_value=[])

    app = _build_app(mocker, l2_tier=l2_tier)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v2/memory/l2/facts",
            json={
                "session_id": "session-1",
                "task_id": "task-1",
                "agent_id": "agent-1",
                "action": "store",
                "content": "Important semantic memory assertion.",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    l2_tier.store.assert_awaited_once()

    fact = captured["fact"]
    expected = calculate_ciar_score(
        fact.certainty,
        fact.impact,
        fact.age_decay,
        fact.recency_boost,
    )
    assert fact.ciar_score == expected == 1.0
    assert fact.metadata["agent_id"] == "agent-1"
    assert fact.metadata["task_id"] == "task-1"
    assert fact.metadata["ciar_score_source"] == "v2_semantic_store"


@pytest.mark.asyncio
async def test_v2_l2_store_preserves_traceparent_in_service_metadata(mocker):
    captured = {}
    l2_tier = mocker.Mock()

    async def store_fact(fact):
        captured["fact"] = fact
        return fact.fact_id

    l2_tier.store = mocker.AsyncMock(side_effect=store_fact)
    app = _build_app(mocker, l2_tier=l2_tier)

    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00"
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v2/memory/l2/facts",
            headers={"traceparent": traceparent},
            json={
                "session_id": "session-1",
                "task_id": "task-1",
                "agent_id": "agent-1",
                "action": "store",
                "content": "Traceable semantic memory assertion.",
            },
        )

    assert response.status_code == 200
    assert captured["fact"].metadata["traceparent"] == traceparent


@pytest.mark.asyncio
async def test_v2_l2_retrieve_keeps_legacy_fact_response_shape(mocker):
    l2_tier = mocker.Mock()
    l2_tier.query_by_session = mocker.AsyncMock(
        return_value=[
            Fact(
                fact_id="fact-1",
                session_id="session-1",
                content="Legacy clients still receive facts.",
                ciar_score=1.0,
                certainty=1.0,
                impact=1.0,
                age_decay=1.0,
                recency_boost=1.0,
                metadata={"agent_id": "agent-1"},
            )
        ]
    )
    app = _build_app(mocker, l2_tier=l2_tier)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v2/memory/l2/facts",
            json={
                "session_id": "session-1",
                "task_id": "task-1",
                "agent_id": "agent-1",
                "action": "retrieve",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["facts"][0]["fact_id"] == "fact-1"
    assert body["facts"][0]["content"] == "Legacy clients still receive facts."
    l2_tier.query_by_session.assert_awaited_once_with(session_id="test:session-1")


@pytest.mark.asyncio
async def test_v2_l3_assimilate_uses_shared_service_and_preserves_provider_failure_shape(
    mocker,
):
    captured = {}
    l3_tier = mocker.Mock()

    async def store_episode(episode_input):
        captured["episode_input"] = episode_input
        return "episode-stored"

    l3_tier.store = mocker.AsyncMock(side_effect=store_episode)
    memory_system = mocker.Mock()
    memory_system.l3_tier = l3_tier
    memory_system.llm_client = mocker.Mock()
    memory_system.llm_client.get_embedding = mocker.AsyncMock(return_value=[0.1] * 64)
    memory_system.llm_client.generate = mocker.AsyncMock(return_value="ok")
    app = _build_app(mocker, memory_system=memory_system, l3_tier=l3_tier)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v2/memory/l3/assimilate",
            json={
                "session_id": "session-1",
                "agent_id": "agent-1",
                "text_to_assimilate": "A durable project memory should be captured.",
                "domain_tags": ["engineering"],
            },
        )

    assert response.status_code == 201
    assert response.json() == {"status": "success", "episode_id": "episode-stored"}
    memory_system.llm_client.get_embedding.assert_awaited_once()
    memory_system.llm_client.generate.assert_awaited_once()
    assert captured["episode_input"].episode.metadata["agent_id"] == "agent-1"
    assert captured["episode_input"].entities[0]["name"] == "ExtractedEntity"

    memory_system.llm_client.get_embedding = mocker.AsyncMock(side_effect=RuntimeError("boom"))
    memory_system.llm_client.generate = mocker.AsyncMock()
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        failure = await client.post(
            "/v2/memory/l3/assimilate",
            json={
                "session_id": "session-1",
                "agent_id": "agent-1",
                "text_to_assimilate": "This provider call fails.",
                "domain_tags": [],
            },
        )

    assert failure.status_code == 502
    assert "YAAM internal LLM pipeline failed" in failure.json()["detail"]


@pytest.mark.asyncio
async def test_v2_l4_finalize_uses_shared_service_and_keeps_response_shape(mocker):
    captured = {}
    l4_tier = mocker.Mock()

    async def store_document(document):
        captured["document"] = document
        return "knowledge-stored"

    l4_tier.store = mocker.AsyncMock(side_effect=store_document)
    memory_system = mocker.Mock()
    memory_system.l4_tier = l4_tier
    app = _build_app(mocker, memory_system=memory_system, l4_tier=l4_tier)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v2/memory/l4/finalize",
            json={
                "session_id": "session-1",
                "task_id": "task-1",
                "title": "Consensus Memory",
                "final_artifact": "A sufficiently detailed final artifact.",
                "consensus_metadata": {"reviewed_by": "agent-1"},
            },
        )

    assert response.status_code == 201
    assert response.json() == {"status": "success", "knowledge_id": "knowledge-stored"}
    assert captured["document"].metadata["task_id"] == "task-1"
    assert captured["document"].metadata["agent_id"] == "rest-v2"
    assert captured["document"].metadata["reviewed_by"] == "agent-1"


@pytest.mark.asyncio
async def test_v2_guarded_query_returns_leakage_guard_metadata(mocker):
    memory_system = mocker.Mock()
    memory_system.query_memory = mocker.AsyncMock(
        return_value=[
            {
                "content": "Visible benchmark-safe context.",
                "tier": "L2",
                "score": 0.9,
                "metadata": {"fact_id": "fact-visible", "visibility_scope": "benchmark_runtime"},
            },
            {
                "content": "Hidden gold answer.",
                "tier": "L2",
                "score": 0.9,
                "metadata": {"fact_id": "fact-hidden", "visibility_scope": "maintainer_only"},
            },
        ]
    )
    app = _build_app(mocker, memory_system=memory_system)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v2/memory/query",
            json={
                "session_id": "session-1",
                "agent_id": "agent-1",
                "caller_role": "benchmark_runtime_agent",
                "visibility_scope": "benchmark_runtime",
                "query": "task context",
                "limit": 2,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert [result["source_id"] for result in body["results"]] == ["fact-visible"]
    assert body["leakage_guard"]["leakage_guard_passed"] is True
    assert body["leakage_guard"]["filtered_item_count"] == 1


@pytest.mark.asyncio
async def test_v2_guarded_context_filters_hidden_records_and_summary(mocker):
    visible_fact = Fact(
        fact_id="fact-visible",
        session_id="session-1",
        content="Visible benchmark-safe fact.",
        metadata={"visibility_scope": "benchmark_runtime"},
    )
    hidden_fact = Fact(
        fact_id="fact-hidden",
        session_id="session-1",
        content="Hidden gold answer.",
        metadata={"visibility_scope": "maintainer_only"},
    )
    context = mocker.Mock()
    context.significant_facts = [visible_fact, hidden_fact]
    context.recent_turns = []
    context.estimated_tokens = 42
    context.to_prompt_string = mocker.Mock(
        return_value="Visible benchmark-safe fact.\nHidden gold answer."
    )
    memory_system = mocker.Mock()
    memory_system.get_context_block = mocker.AsyncMock(return_value=context)
    app = _build_app(mocker, memory_system=memory_system)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v2/memory/context",
            json={
                "session_id": "session-1",
                "agent_id": "agent-1",
                "caller_role": "benchmark_runtime_agent",
                "visibility_scope": "benchmark_runtime",
                "require_leakage_guard": True,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert [item["source_id"] for item in body["context"]["items"]] == ["fact-visible"]
    assert body["context"]["leakage_guard_passed"] is True
    assert body["context"]["filtered_item_count"] == 1
    assert body["context"]["context_summary"] == "Visible benchmark-safe fact."


@pytest.mark.asyncio
async def test_v2_curation_denies_runtime_callers_with_structured_error(mocker):
    l2_tier = mocker.Mock()
    l2_tier.store = mocker.AsyncMock()
    app = _build_app(mocker, l2_tier=l2_tier)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v2/memory/curation/decisions",
            json={
                "session_id": "session-1",
                "agent_id": "agent-1",
                "task_id": "task-1",
                "caller_role": "benchmark_runtime_agent",
                "decision": "accepted",
                "reason": "Runtime caller should not write curation.",
                "source_triad": {"prompt": "prompt-1"},
                "reviewer": "reviewer-1",
            },
        )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["code"] == "permission.role_denied"
    assert detail["operation"] == "yaam.curation.record_decision"
    assert detail["affected_tier"] == "SYSTEM"


@pytest.mark.asyncio
async def test_v2_curation_create_and_list_maintainer_records(mocker):
    curation_fact = Fact(
        fact_id="curation-1",
        session_id="session-1",
        content="Curation decision.",
        metadata={
            "record_type": "scm_cert_bench_curation_decision",
            "curation_record_id": "curation-1",
            "task_id": "task-1",
            "decision": "accepted",
            "reason": "Source triad is valid.",
            "source_triad": {"prompt": "prompt-1", "oracle": "oracle-1", "rubric": "rubric-1"},
            "reviewer": "reviewer-1",
            "visibility_scope": "maintainer_only",
        },
    )
    l2_tier = mocker.Mock()
    l2_tier.store = mocker.AsyncMock(return_value=None)
    l2_tier.query_by_session = mocker.AsyncMock(return_value=[curation_fact])
    app = _build_app(mocker, l2_tier=l2_tier)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/v2/memory/curation/decisions",
            json={
                "session_id": "session-1",
                "agent_id": "agent-1",
                "task_id": "task-1",
                "caller_role": "benchmark_maintainer",
                "decision": "accepted",
                "reason": "Source triad is valid.",
                "source_triad": {"prompt": "prompt-1", "oracle": "oracle-1"},
                "reviewer": "reviewer-1",
                "metadata": {"api_token": "secret"},
            },
        )
        listed = await client.get(
            "/v2/memory/curation/decisions",
            params={
                "session_id": "session-1",
                "agent_id": "agent-1",
                "task_id": "task-1",
                "caller_role": "benchmark_maintainer",
            },
        )

    assert created.status_code == 201
    stored_fact = l2_tier.store.await_args.args[0]
    assert stored_fact.metadata["visibility_scope"] == "maintainer_only"
    assert stored_fact.metadata["api_token"] == "[REDACTED]"
    assert created.json()["ack"]["operation"] == "yaam.curation.record_decision"

    assert listed.status_code == 200
    body = listed.json()
    assert body["decisions"][0]["curation_record_id"] == "curation-1"
    assert body["decisions"][0]["visibility_scope"] == "maintainer_only"
    assert body["decisions"][0]["source_triad"]["prompt"] == "prompt-1"


@pytest.mark.asyncio
async def test_v2_trace_correlation_create_and_lookup(mocker):
    trace_fact = Fact(
        fact_id="tracecorr-1",
        session_id="session-1",
        content="Trace correlation.",
        metadata={
            "record_type": "scm_cert_bench_trace_correlation",
            "correlation_id": "tracecorr-1",
            "trace_id": "phoenix-trace-1",
            "task_id": "task-1",
            "run_id": "run-1",
            "artifact_ref": "artifacts/run-1.jsonl",
            "openrouter_call_id": "or-call-1",
            "linked_memory_ids": ["fact-1"],
            "trace_status": "degraded",
        },
    )
    l2_tier = mocker.Mock()
    l2_tier.store = mocker.AsyncMock(return_value=None)
    l2_tier.query_by_session = mocker.AsyncMock(return_value=[trace_fact])
    app = _build_app(mocker, l2_tier=l2_tier)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/v2/memory/trace-correlations",
            json={
                "session_id": "session-1",
                "agent_id": "agent-1",
                "task_id": "task-1",
                "run_id": "run-1",
                "caller_role": "post_run_ingestion_service",
                "trace_id": "phoenix-trace-1",
                "artifact_ref": "artifacts/run-1.jsonl",
                "openrouter_call_id": "or-call-1",
                "linked_memory_ids": ["fact-1"],
                "trace_status": "degraded",
                "metadata": {"password": "secret"},
            },
        )
        listed = await client.get(
            "/v2/memory/trace-correlations",
            params={
                "session_id": "session-1",
                "agent_id": "agent-1",
                "task_id": "task-1",
                "run_id": "run-1",
                "caller_role": "post_run_ingestion_service",
                "trace_id": "phoenix-trace-1",
            },
        )

    assert created.status_code == 201
    stored_fact = l2_tier.store.await_args.args[0]
    assert stored_fact.metadata["password"] == "[REDACTED]"
    assert created.json()["ack"]["operation"] == "yaam.trace.record_correlation"

    assert listed.status_code == 200
    correlation = listed.json()["correlations"][0]
    assert correlation["correlation_id"] == "tracecorr-1"
    assert correlation["trace_id"] == "phoenix-trace-1"
    assert correlation["task_id"] == "task-1"
    assert correlation["run_id"] == "run-1"
    assert correlation["artifact_ref"] == "artifacts/run-1.jsonl"
    assert correlation["openrouter_call_id"] == "or-call-1"
    assert correlation["linked_memory_ids"] == ["fact-1"]
