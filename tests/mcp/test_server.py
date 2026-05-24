import json

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from src.mcp.server import (
    MCP_PROMPT_NAMES,
    MCP_RESOURCE_URIS,
    MCP_SDK_REQUIREMENT,
    MCP_TOOL_NAMES,
    create_mcp_server,
    parse_args,
)
from src.memory.services import (
    MemoryGatewayService,
    PermissionPolicy,
)
from src.memory.services.permissions import YAAMPermissionError
from tests.helpers.fake_tracing import FakeTracer
from tests.mcp.fixtures import PartialContextService, RecordingMCPService


@pytest.fixture(autouse=True)
def disable_real_tracing(mocker) -> None:
    mocker.patch("src.observability.tracing._get_tracer", return_value=None)


def test_mcp_v1_names_match_planning_freeze() -> None:
    assert MCP_SDK_REQUIREMENT == "mcp>=1.12.4,<1.27.1"
    assert MCP_TOOL_NAMES == (
        "yaam.memory.query",
        "yaam.memory.get_context",
        "yaam.l2.store_fact",
        "yaam.l2.search_facts",
        "yaam.l3.search_episodes",
        "yaam.l3.assimilate_episode",
        "yaam.l4.search_knowledge",
        "yaam.l4.finalize_artifact",
        "yaam.ciar.explain",
        "yaam.evidence.table",
        "yaam.health.check",
    )
    assert "yaam://health" in MCP_RESOURCE_URIS
    assert "yaam://schemas/fact" in MCP_RESOURCE_URIS
    assert "yaam://schemas/episode" in MCP_RESOURCE_URIS
    assert "yaam://schemas/knowledge-document" in MCP_RESOURCE_URIS
    assert "yaam.prompt.evidence_table" in MCP_PROMPT_NAMES


def test_create_mcp_server_registers_fastmcp_capabilities() -> None:
    server = create_mcp_server()

    assert server.name == "yaam-mcp-v1"
    assert [tool.name for tool in server._tool_manager.list_tools()] == list(MCP_TOOL_NAMES)
    assert [prompt.name for prompt in server._prompt_manager.list_prompts()] == list(
        MCP_PROMPT_NAMES
    )
    assert [str(resource.uri) for resource in server._resource_manager.list_resources()] == [
        "yaam://health",
        "yaam://config/ciar",
        "yaam://schemas/fact",
        "yaam://schemas/episode",
        "yaam://schemas/knowledge-document",
    ]
    assert [template.uri_template for template in server._resource_manager.list_templates()] == [
        "yaam://sessions/{session_id}/context",
        "yaam://sessions/{session_id}/facts",
        "yaam://facts/{fact_id}",
        "yaam://episodes/{episode_id}",
        "yaam://knowledge/{knowledge_id}",
    ]


def test_parse_args_supports_documented_cli_flags() -> None:
    args = parse_args(
        [
            "--agent-type",
            "full",
            "--agent-variant",
            "baseline",
            "--port",
            "9000",
            "--model",
            "test-model",
        ]
    )

    assert args.agent_type == "full"
    assert args.agent_variant == "baseline"
    assert args.port == 9000
    assert args.model == "test-model"


@pytest.mark.asyncio
async def test_mcp_read_tools_delegate_to_service_with_scope_and_structured_payloads() -> None:
    service = RecordingMCPService()
    server = create_mcp_server(service)

    memory_query = await _call_tool(
        server,
        "yaam.memory.query",
        {
            "session_id": "session-a",
            "agent_id": "agent-a",
            "task_id": "task-a",
            "tenant_id": "tenant-a",
            "run_id": "run-a",
            "query": "dock status",
            "limit": 3,
            "l2_weight": 0.2,
            "l3_weight": 0.3,
            "l4_weight": 0.5,
        },
    )
    assert memory_query["summary"] == "Memory query complete."
    assert memory_query["results"][0]["provenance"]["session_id"] == "session-a"
    query_call = service.calls[-1]
    scope = query_call[1][0]
    weights = query_call[1][3]
    assert scope.task_id == "task-a"
    assert scope.tenant_id == "tenant-a"
    assert weights.l2_weight == 0.2
    assert weights.l3_weight == 0.3
    assert weights.l4_weight == 0.5

    context = await _call_tool(
        server,
        "yaam.memory.get_context",
        {"session_id": "session-a", "agent_id": "agent-a", "task_id": "task-a"},
    )
    assert context["summary"] == "Context assembled."
    assert context["context"]["context_summary"] == "Context summary."

    l2 = await _call_tool(
        server,
        "yaam.l2.search_facts",
        {"session_id": "session-a", "agent_id": "agent-a", "query": "dock", "limit": 2},
    )
    assert l2["results"][0]["tier"] == "L2"

    l3 = await _call_tool(
        server,
        "yaam.l3.search_episodes",
        {"session_id": "session-a", "agent_id": "agent-a", "query": "dock", "limit": 2},
    )
    assert l3["results"][0]["tier"] == "L3"

    l4 = await _call_tool(
        server,
        "yaam.l4.search_knowledge",
        {"session_id": "session-a", "agent_id": "agent-a", "query": "dock", "limit": 2},
    )
    assert l4["results"][0]["tier"] == "L4"

    ciar = await _call_tool(
        server,
        "yaam.ciar.explain",
        {"session_id": "session-a", "agent_id": "agent-a", "certainty": 0.7},
    )
    assert ciar["summary"] == "CIAR explained."
    assert ciar["explanation"]["components"]["certainty"] == 0.7

    evidence = await _call_tool(
        server,
        "yaam.evidence.table",
        {"session_id": "session-a", "agent_id": "agent-a", "query": "dock"},
    )
    assert evidence["evidence_table"]["rows"][0]["source_id"] == "fact-evidence"

    health = await _call_tool(server, "yaam.health.check", {})
    assert health["health"]["status"] == "ok"


@pytest.mark.asyncio
async def test_mcp_mutating_tools_are_denied_by_default(mocker) -> None:
    memory_system = mocker.Mock()
    memory_system.l2_tier = mocker.Mock()
    memory_system.l3_tier = mocker.Mock()
    memory_system.l4_tier = mocker.Mock()
    memory_system.llm_client = mocker.Mock()
    service = MemoryGatewayService(memory_system)
    server = create_mcp_server(service)

    write_calls = [
        (
            "yaam.l2.store_fact",
            {"session_id": "session-a", "agent_id": "agent-a", "content": "Fact."},
        ),
        (
            "yaam.l3.assimilate_episode",
            {
                "session_id": "session-a",
                "agent_id": "agent-a",
                "text_to_assimilate": "Episode text.",
            },
        ),
        (
            "yaam.l4.finalize_artifact",
            {
                "session_id": "session-a",
                "agent_id": "agent-a",
                "title": "Final Artifact",
                "final_artifact": "A final artifact with enough content.",
            },
        ),
    ]

    for tool_name, arguments in write_calls:
        with pytest.raises(ToolError) as exc_info:
            await _call_tool(server, tool_name, arguments)
        assert isinstance(exc_info.value.__cause__, ToolError)
        assert isinstance(exc_info.value.__cause__.__cause__, YAAMPermissionError)
        payload = _tool_error_payload(exc_info.value)
        assert payload["code"].startswith("permission.")
        assert payload["operation"] == tool_name
        assert payload["retryable"] is False
        assert payload["affected_tier"] == "SYSTEM"


@pytest.mark.asyncio
async def test_mcp_allowlisted_write_tools_persist_and_return_acknowledgements(mocker) -> None:
    memory_system = mocker.Mock()
    memory_system.l2_tier = mocker.Mock()
    memory_system.l2_tier.store = mocker.AsyncMock(return_value="fact-stored")
    memory_system.l3_tier = mocker.Mock()
    memory_system.l3_tier.store = mocker.AsyncMock(return_value="episode-stored")
    memory_system.l4_tier = mocker.Mock()
    memory_system.l4_tier.store = mocker.AsyncMock(return_value="knowledge-stored")
    memory_system.llm_client = mocker.Mock()
    memory_system.llm_client.get_embedding = mocker.AsyncMock(return_value=[0.1] * 64)
    memory_system.llm_client.generate = mocker.AsyncMock(return_value="ok")
    service = MemoryGatewayService(
        memory_system,
        PermissionPolicy(
            enable_writes=True,
            enable_lifecycle=True,
            allowlisted_tools=frozenset(
                {
                    "yaam.l2.store_fact",
                    "yaam.l3.assimilate_episode",
                    "yaam.l4.finalize_artifact",
                }
            ),
        ),
    )
    server = create_mcp_server(service)

    l2 = await _call_tool(
        server,
        "yaam.l2.store_fact",
        {
            "session_id": "session-a",
            "agent_id": "agent-a",
            "task_id": "task-a",
            "content": "Fact content.",
        },
    )
    assert l2["ack"]["created_id"] == "fact-stored"
    assert l2["ack"]["provenance"]["source_tier"] == "L2"

    l3 = await _call_tool(
        server,
        "yaam.l3.assimilate_episode",
        {
            "session_id": "session-a",
            "agent_id": "agent-a",
            "task_id": "task-a",
            "text_to_assimilate": "A durable episode should be stored.",
            "domain_tags": ["engineering"],
        },
    )
    assert l3["ack"]["created_id"] == "episode-stored"
    memory_system.llm_client.generate.assert_awaited_once()

    l4 = await _call_tool(
        server,
        "yaam.l4.finalize_artifact",
        {
            "session_id": "session-a",
            "agent_id": "agent-a",
            "task_id": "task-a",
            "title": "Final Artifact",
            "final_artifact": "A final artifact with enough content.",
            "consensus_metadata": {"reviewed_by": "agent-a"},
        },
    )
    assert l4["ack"]["created_id"] == "knowledge-stored"
    assert l4["ack"]["provenance"]["source_tier"] == "L4"


@pytest.mark.asyncio
async def test_mcp_static_resources_return_json_without_secret_shaped_keys() -> None:
    server = create_mcp_server(RecordingMCPService())

    for uri in (
        "yaam://health",
        "yaam://config/ciar",
        "yaam://schemas/fact",
        "yaam://schemas/episode",
        "yaam://schemas/knowledge-document",
    ):
        resource = await server._resource_manager.get_resource(uri)
        assert resource is not None
        payload = json.loads(await resource.read())
        serialized = json.dumps(payload).lower()
        assert "api_key" not in serialized
        assert "password" not in serialized
        assert "secret" not in serialized

    ciar_resource = await server._resource_manager.get_resource("yaam://config/ciar")
    assert ciar_resource is not None
    ciar = json.loads(await ciar_resource.read())
    assert ciar["formula"] == "(certainty * impact) * age_decay * recency_boost"


@pytest.mark.asyncio
async def test_mcp_templated_resources_are_read_only_service_views() -> None:
    service = RecordingMCPService()
    server = create_mcp_server(service)

    context = json.loads(await _read_template(server, "yaam://sessions/session-a/context"))
    assert context["session_id"] == "session-a"

    facts = json.loads(await _read_template(server, "yaam://sessions/session-a/facts"))
    assert facts[0]["source_id"] == "fact-search"

    fact = json.loads(await _read_template(server, "yaam://facts/fact-a"))
    assert fact["source_id"] == "fact-a"

    episode = json.loads(await _read_template(server, "yaam://episodes/episode-a"))
    assert episode["tier"] == "L3"

    knowledge = json.loads(await _read_template(server, "yaam://knowledge/knowledge-a"))
    assert knowledge["tier"] == "L4"

    assert [call[0] for call in service.calls] == [
        "get_context",
        "search_l2_facts",
        "get_fact",
        "get_episode",
        "get_knowledge",
    ]
    assert service.calls[2][1][0].session_id == "*"
    assert service.calls[2][1][0].agent_id == "resource-reader"


@pytest.mark.asyncio
async def test_mcp_prompts_render_frozen_inspection_templates() -> None:
    server = create_mcp_server(RecordingMCPService())
    prompts = {prompt.name: prompt for prompt in server._prompt_manager.list_prompts()}

    evidence = await prompts["yaam.prompt.evidence_table"].render({"query": "dock status"})
    assert "evidence table" in evidence[0].content.text.lower()
    assert "dock status" in evidence[0].content.text

    inspection = await prompts["yaam.prompt.memory_inspection"].render({"session_id": "session-a"})
    assert "without mutation" in inspection[0].content.text
    assert "session-a" in inspection[0].content.text

    ciar = await prompts["yaam.prompt.ciar_explanation"].render({"claim": "Claim one"})
    assert "certainty" in ciar[0].content.text
    assert "Claim one" in ciar[0].content.text

    strategy = await prompts["yaam.prompt.retrieval_strategy"].render({"task": "Plan retrieval"})
    assert "partial-result" in strategy[0].content.text
    assert "Plan retrieval" in strategy[0].content.text


@pytest.mark.asyncio
async def test_mcp_tool_observability_records_attrs_and_traceparent(mocker) -> None:
    fake_tracer = FakeTracer()
    mocker.patch("src.observability.tracing._get_tracer", return_value=fake_tracer)
    service = RecordingMCPService()
    server = create_mcp_server(service)

    await _call_tool(
        server,
        "yaam.memory.query",
        {
            "session_id": "session-a",
            "agent_id": "agent-a",
            "task_id": "task-a",
            "tenant_id": "tenant-a",
            "run_id": "run-a",
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00",
            "query": "dock status",
        },
    )

    scope = service.calls[-1][1][0]
    assert scope.traceparent == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00"
    span = fake_tracer.spans[-1]
    assert span.name == "yaam.mcp.tool.yaam.memory.query"
    assert span.attributes["yaam.interface"] == "MCP"
    assert span.attributes["yaam.mcp.surface"] == "tool"
    assert span.attributes["yaam.operation"] == "yaam.memory.query"
    assert span.attributes["yaam.operation_mode"] == "read"
    assert span.attributes["session.id"] == "session-a"
    assert span.attributes["yaam.agent_id"] == "agent-a"
    assert span.attributes["yaam.task_id"] == "task-a"
    assert span.attributes["yaam.tenant_id"] == "tenant-a"
    assert span.attributes["yaam.run_id"] == "run-a"
    assert span.attributes["yaam.traceparent.present"] is True
    assert span.attributes["yaam.status"] == "success"
    assert span.attributes["yaam.result_count"] == 1
    assert json.loads(span.attributes["yaam.source_ids"]) == ["fact-1"]
    assert span.attributes["yaam.partial"] is False
    assert span.attributes["yaam.warning_count"] == 0
    assert span.attributes["yaam.latency_ms"] >= 0


@pytest.mark.asyncio
async def test_mcp_partial_read_records_warning_metadata(mocker) -> None:
    fake_tracer = FakeTracer()
    mocker.patch("src.observability.tracing._get_tracer", return_value=fake_tracer)
    server = create_mcp_server(PartialContextService())

    context = await _call_tool(
        server,
        "yaam.memory.get_context",
        {"session_id": "session-a", "agent_id": "agent-a"},
    )

    assert context["context"]["partial"] is True
    span = fake_tracer.spans[-1]
    assert span.attributes["yaam.partial"] is True
    assert span.attributes["yaam.warning_count"] == 1
    assert json.loads(span.attributes["yaam.source_ids"]) == ["fact-context"]


@pytest.mark.asyncio
async def test_mcp_validation_errors_are_structured_protocol_errors(mocker) -> None:
    fake_tracer = FakeTracer()
    mocker.patch("src.observability.tracing._get_tracer", return_value=fake_tracer)
    server = create_mcp_server(RecordingMCPService())

    with pytest.raises(ToolError) as exc_info:
        await _call_tool(
            server,
            "yaam.memory.query",
            {
                "session_id": "session-a",
                "agent_id": "agent-a",
                "query": "dock status",
                "traceparent": " ",
            },
        )

    payload = _tool_error_payload(exc_info.value)
    assert payload["code"] == "validation.invalid_scope"
    assert payload["operation"] == "yaam.memory.query"
    assert payload["retryable"] is False
    assert payload["affected_tier"] == "SYSTEM"
    assert payload["trace_id"] == "00000000000000000000000000000001"
    assert fake_tracer.spans[-1].attributes["yaam.status"] == "error"
    assert fake_tracer.spans[-1].attributes["yaam.error_code"] == "validation.invalid_scope"


@pytest.mark.asyncio
async def test_mcp_resources_and_prompts_emit_spans(mocker) -> None:
    fake_tracer = FakeTracer()
    mocker.patch("src.observability.tracing._get_tracer", return_value=fake_tracer)
    server = create_mcp_server(RecordingMCPService())

    resource = await server._resource_manager.get_resource("yaam://health")
    assert resource is not None
    await resource.read()

    prompts = {prompt.name: prompt for prompt in server._prompt_manager.list_prompts()}
    await prompts["yaam.prompt.memory_inspection"].render({"session_id": "session-a"})

    spans = {span.name: span for span in fake_tracer.spans}
    resource_span = spans["yaam.mcp.resource.yaam://health"]
    assert resource_span.attributes["yaam.interface"] == "MCP"
    assert resource_span.attributes["yaam.mcp.surface"] == "resource"
    assert resource_span.attributes["yaam.operation"] == "yaam://health"
    assert resource_span.attributes["yaam.status"] == "success"
    assert resource_span.attributes["yaam.health.status"] == "ok"

    prompt_span = spans["yaam.mcp.prompt.yaam.prompt.memory_inspection"]
    assert prompt_span.attributes["yaam.interface"] == "MCP"
    assert prompt_span.attributes["yaam.mcp.surface"] == "prompt"
    assert prompt_span.attributes["yaam.operation"] == "yaam.prompt.memory_inspection"
    assert prompt_span.attributes["session.id"] == "session-a"
    assert prompt_span.attributes["yaam.agent_id"] == "resource-reader"
    assert prompt_span.attributes["yaam.result_count"] == 1


async def _call_tool(server, name: str, arguments: dict) -> dict:
    return await server._tool_manager.call_tool(name, arguments, convert_result=False)


async def _read_template(server, uri: str) -> str:
    for template in server._resource_manager.list_templates():
        params = template.matches(uri)
        if params is not None:
            resource = await template.create_resource(uri, params)
            return await resource.read()
    raise AssertionError(f"No MCP resource template matched {uri}")


def _tool_error_payload(error: ToolError) -> dict:
    message = str(error)
    return json.loads(message[message.index("{") :])["error"]
