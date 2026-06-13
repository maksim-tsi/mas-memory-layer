import json
import logging

import anyio
import pytest
from mcp.server.fastmcp.exceptions import ToolError

from src.mcp.server import (
    COGNITIVE_SANDWICH_MCP_PROMPT_NAMES,
    COGNITIVE_SANDWICH_MCP_RESOURCE_URIS,
    MCP_PROMPT_NAMES,
    MCP_RESOURCE_URIS,
    MCP_SDK_REQUIREMENT,
    MCP_STREAMABLE_HTTP_LOGGER,
    MCP_TOOL_NAMES,
    SKILL_FACTORY_MCP_PROMPT_NAMES,
    SKILL_FACTORY_MCP_RESOURCE_URIS,
    _StreamableHTTPClosedResourceFilter,
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
        "yaam.contradiction.review",
        "yaam.health.check",
        "yaam.curation.record_decision",
        "yaam.curation.list_decisions",
        "yaam.trace.record_correlation",
        "yaam.trace.lookup",
    )
    assert "yaam://health" in MCP_RESOURCE_URIS
    assert "yaam://schemas/fact" in MCP_RESOURCE_URIS
    assert "yaam://schemas/episode" in MCP_RESOURCE_URIS
    assert "yaam://schemas/knowledge-document" in MCP_RESOURCE_URIS
    assert "yaam.prompt.evidence_table" in MCP_PROMPT_NAMES


def test_create_mcp_server_registers_fastmcp_capabilities() -> None:
    server = create_mcp_server()

    assert server.name == "yaam-mcp-v1"
    assert server.settings.stateless_http is False
    assert server.settings.json_response is False
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


def test_skill_factory_domain_pack_is_not_registered_by_default(monkeypatch) -> None:
    monkeypatch.delenv("YAAM_PROJECT_ID", raising=False)
    monkeypatch.delenv("YAAM_MCP_DOMAIN_PACKS", raising=False)

    server = create_mcp_server()

    prompts = [prompt.name for prompt in server._prompt_manager.list_prompts()]
    templates = [template.uri_template for template in server._resource_manager.list_templates()]
    assert "yaam.prompt.repair_pattern_summary" not in prompts
    assert "yaam.prompt.artifact_repair_context" not in prompts
    assert "yaam://skills/{skill_name}" not in templates
    assert "yaam://artifacts/{artifact_id}/lineage" not in templates


def test_skill_factory_domain_pack_registers_when_enabled() -> None:
    args = parse_args(["--mcp-domain-packs", "skill-factory"])

    server = create_mcp_server(config_args=args)

    prompts = [prompt.name for prompt in server._prompt_manager.list_prompts()]
    templates = [template.uri_template for template in server._resource_manager.list_templates()]
    for prompt_name in SKILL_FACTORY_MCP_PROMPT_NAMES:
        assert prompt_name in prompts
    for resource_uri in SKILL_FACTORY_MCP_RESOURCE_URIS:
        assert resource_uri in templates


def test_cognitive_sandwich_domain_pack_registers_when_enabled() -> None:
    args = parse_args(["--mcp-domain-packs", "cognitive-sandwich"])

    server = create_mcp_server(config_args=args)

    prompts = [prompt.name for prompt in server._prompt_manager.list_prompts()]
    templates = [template.uri_template for template in server._resource_manager.list_templates()]
    for prompt_name in COGNITIVE_SANDWICH_MCP_PROMPT_NAMES:
        assert prompt_name in prompts
    for resource_uri in COGNITIVE_SANDWICH_MCP_RESOURCE_URIS:
        assert resource_uri in templates


def test_skill_factory_domain_pack_auto_enables_for_project(monkeypatch) -> None:
    monkeypatch.setenv("YAAM_PROJECT_ID", "scm-skill-factory")
    args = parse_args([])

    server = create_mcp_server(config_args=args)

    templates = [template.uri_template for template in server._resource_manager.list_templates()]
    assert "yaam://skills/{skill_name}" in templates


def test_cognitive_sandwich_domain_pack_auto_enables_for_project(monkeypatch) -> None:
    monkeypatch.setenv("YAAM_PROJECT_ID", "scm-cognitive-sandwich")
    args = parse_args([])

    server = create_mcp_server(config_args=args)

    templates = [template.uri_template for template in server._resource_manager.list_templates()]
    assert "yaam://artifacts/{artifact_id}/lineage" in templates


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
            "--transport",
            "streamable-http",
            "--mcp-host",
            "0.0.0.0",
            "--mcp-port",
            "8081",
            "--mcp-path",
            "/mcp",
            "--mcp-domain-packs",
            "skill-factory,cognitive-sandwich",
        ]
    )

    assert args.agent_type == "full"
    assert args.agent_variant == "baseline"
    assert args.port == 9000
    assert args.model == "test-model"
    assert args.transport == "streamable-http"
    assert args.mcp_host == "0.0.0.0"
    assert args.mcp_port == 8081
    assert args.mcp_path == "/mcp"
    assert args.mcp_domain_packs == "skill-factory,cognitive-sandwich"


def test_create_mcp_server_configures_streamable_http_transport() -> None:
    args = parse_args(
        [
            "--transport",
            "streamable-http",
            "--mcp-host",
            "0.0.0.0",
            "--mcp-port",
            "8081",
            "--mcp-path",
            "/mcp",
        ]
    )
    server = create_mcp_server(config_args=args)

    assert server.settings.host == "0.0.0.0"
    assert server.settings.port == 8081
    assert server.settings.streamable_http_path == "/mcp"
    assert server.settings.stateless_http is True
    assert server.settings.json_response is True
    assert [tool.name for tool in server._tool_manager.list_tools()] == list(MCP_TOOL_NAMES)


def test_streamable_http_closed_resource_filter_is_narrow() -> None:
    log_filter = _StreamableHTTPClosedResourceFilter()

    closed_record = _mcp_sdk_log_record(anyio.ClosedResourceError)
    assert log_filter.filter(closed_record) is False

    runtime_record = _mcp_sdk_log_record(RuntimeError)
    assert log_filter.filter(runtime_record) is True

    unrelated_record = logging.LogRecord(
        name=MCP_STREAMABLE_HTTP_LOGGER,
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Unexpected MCP transport error",
        args=(),
        exc_info=(anyio.ClosedResourceError, anyio.ClosedResourceError(), None),
    )
    assert log_filter.filter(unrelated_record) is True


def test_streamable_http_server_installs_closed_resource_filter_once() -> None:
    logger = logging.getLogger(MCP_STREAMABLE_HTTP_LOGGER)
    original_filters = list(logger.filters)
    logger.filters = [
        item for item in logger.filters if not isinstance(item, _StreamableHTTPClosedResourceFilter)
    ]
    try:
        args = parse_args(["--transport", "streamable-http"])
        create_mcp_server(config_args=args)
        create_mcp_server(config_args=args)

        installed = [
            item
            for item in logger.filters
            if isinstance(item, _StreamableHTTPClosedResourceFilter)
        ]
        assert len(installed) == 1
    finally:
        logger.filters = original_filters


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
    assert memory_query["leakage_guard"]["checked_item_count"] == 1
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
        {
            "session_id": "session-a",
            "agent_id": "agent-a",
            "task_id": "task-a",
            "caller_role": "benchmark_runtime_agent",
            "visibility_scope": "benchmark_runtime",
            "forbidden_fields": ["ground_truth_answer"],
            "require_leakage_guard": True,
        },
    )
    assert context["summary"] == "Context assembled."
    assert context["context"]["context_summary"] == "Context summary."
    assert context["context"]["leakage_guard_passed"] is True
    assert context["context"]["visibility_scope"] == "benchmark_runtime"

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

    review = await _call_tool(
        server,
        "yaam.contradiction.review",
        {
            "session_id": "session-a",
            "agent_id": "agent-a",
            "task_id": "task-a",
            "claims": ["Claim one."],
            "expected_behavior": "safe refusal",
        },
    )
    assert review["summary"] == "Contradiction reviewed."
    assert review["review"]["contradiction_detected"] is True

    health = await _call_tool(server, "yaam.health.check", {})
    assert health["health"]["status"] == "ok"

    curation = await _call_tool(
        server,
        "yaam.curation.list_decisions",
        {
            "session_id": "session-a",
            "agent_id": "agent-a",
            "task_id": "task-a",
            "caller_role": "benchmark_maintainer",
        },
    )
    assert curation["decisions"][0]["task_id"] == "task-a"
    assert curation["decisions"][0]["visibility_scope"] == "maintainer_only"

    trace = await _call_tool(
        server,
        "yaam.trace.lookup",
        {
            "session_id": "session-a",
            "agent_id": "agent-a",
            "task_id": "task-a",
            "run_id": "run-a",
            "caller_role": "post_run_ingestion_service",
            "trace_id": "phoenix-trace-fixture",
        },
    )
    assert trace["correlations"][0]["trace_id"] == "phoenix-trace-fixture"


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
        (
            "yaam.curation.record_decision",
            {
                "session_id": "session-a",
                "agent_id": "agent-a",
                "task_id": "task-a",
                "decision": "accepted",
                "reason": "Maintainer review.",
                "source_triad": {"prompt": "prompt-a"},
                "reviewer": "reviewer-a",
                "caller_role": "benchmark_maintainer",
            },
        ),
        (
            "yaam.trace.record_correlation",
            {
                "session_id": "session-a",
                "agent_id": "agent-a",
                "task_id": "task-a",
                "trace_id": "phoenix-trace-a",
                "caller_role": "post_run_ingestion_service",
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
                    "yaam.curation.record_decision",
                    "yaam.trace.record_correlation",
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

    curation = await _call_tool(
        server,
        "yaam.curation.record_decision",
        {
            "session_id": "session-a",
            "agent_id": "agent-a",
            "task_id": "task-a",
            "decision": "accepted",
            "reason": "Maintainer review.",
            "source_triad": {"prompt": "prompt-a", "oracle": "oracle-a"},
            "reviewer": "reviewer-a",
            "caller_role": "benchmark_maintainer",
        },
    )
    assert curation["ack"]["operation"] == "yaam.curation.record_decision"
    assert curation["ack"]["provenance"]["source_tier"] == "L2"

    trace = await _call_tool(
        server,
        "yaam.trace.record_correlation",
        {
            "session_id": "session-a",
            "agent_id": "agent-a",
            "task_id": "task-a",
            "run_id": "run-a",
            "trace_id": "phoenix-trace-a",
            "artifact_ref": "artifacts/run-a.jsonl",
            "caller_role": "post_run_ingestion_service",
        },
    )
    assert trace["ack"]["operation"] == "yaam.trace.record_correlation"
    assert trace["ack"]["provenance"]["source_tier"] == "L2"


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

    missing_fact = json.loads(await _read_template(server, "yaam://facts/nonexistent-fact"))
    assert missing_fact == {"status": "not_found", "fact_id": "nonexistent-fact"}

    episode = json.loads(await _read_template(server, "yaam://episodes/episode-a"))
    assert episode["tier"] == "L3"

    knowledge = json.loads(await _read_template(server, "yaam://knowledge/knowledge-a"))
    assert knowledge["tier"] == "L4"

    assert [call[0] for call in service.calls] == [
        "get_context",
        "search_l2_facts",
        "get_fact",
        "get_fact",
        "get_episode",
        "get_knowledge",
    ]
    assert service.calls[2][1][0].session_id == "*"
    assert service.calls[2][1][0].agent_id == "resource-reader"


@pytest.mark.asyncio
async def test_skill_factory_domain_resources_are_read_only_service_views() -> None:
    args = parse_args(["--mcp-domain-packs", "skill-factory"])
    service = RecordingMCPService()
    server = create_mcp_server(service, args)

    payload = json.loads(await _read_template(server, "yaam://skills/inventory-router"))

    assert payload["domain_pack"] == "skill-factory"
    assert payload["view"] == "skill"
    assert payload["filters"] == {"skill_name": "inventory-router"}
    assert payload["partial"] is False
    assert [call[0] for call in service.calls] == [
        "search_l2_facts",
        "search_l3_episodes",
        "search_l4_knowledge",
    ]
    assert service.calls[0][1][0].session_id == "*"
    assert service.calls[0][1][0].agent_id == "skill-factory-domain-pack"
    assert service.calls[0][1][0].domain_ids == {"skill_name": "inventory-router"}


@pytest.mark.asyncio
async def test_cognitive_sandwich_domain_resources_are_read_only_service_views() -> None:
    args = parse_args(["--mcp-domain-packs", "cognitive-sandwich"])
    service = RecordingMCPService()
    server = create_mcp_server(service, args)

    payload = json.loads(
        await _read_template(server, "yaam://artifacts/artifact-readiness-001/lineage")
    )

    assert payload["domain_pack"] == "cognitive-sandwich"
    assert payload["view"] == "artifact_lineage"
    assert payload["filters"] == {"artifact_id": "artifact-readiness-001"}
    assert payload["partial"] is False
    assert payload["counts"]["nodes"] == 1
    assert payload["nodes"][0]["feedback_id"] == "feedback-001"
    assert service.calls[-1][0] == "list_cognitive_sandwich_domain_records"
    assert service.calls[-1][1][0].session_id == "*"
    assert service.calls[-1][1][0].agent_id == "cognitive-sandwich-domain-pack"
    assert service.calls[-1][1][0].domain_ids == {
        "artifact_id": "artifact-readiness-001"
    }


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
async def test_skill_factory_repair_pattern_prompt_renders_without_mutation() -> None:
    args = parse_args(["--mcp-domain-packs", "skill-factory"])
    server = create_mcp_server(RecordingMCPService(), args)
    prompts = {prompt.name: prompt for prompt in server._prompt_manager.list_prompts()}

    rendered = await prompts["yaam.prompt.repair_pattern_summary"].render(
        {
            "skill_name": "inventory-router",
            "ctt_id": "ctt-42",
            "qa_status": "failed",
        }
    )

    text = rendered[0].content.text
    assert "without mutating YAAM" in text
    assert "inventory-router" in text
    assert "ctt-42" in text
    assert "failed" in text


@pytest.mark.asyncio
async def test_cognitive_sandwich_artifact_prompts_render_without_mutation() -> None:
    args = parse_args(["--mcp-domain-packs", "cognitive-sandwich"])
    server = create_mcp_server(RecordingMCPService(), args)
    prompts = {prompt.name: prompt for prompt in server._prompt_manager.list_prompts()}

    repair = await prompts["yaam.prompt.artifact_repair_context"].render(
        {
            "artifact_id": "artifact-readiness-001",
            "run_id": "artifact-run-001",
        }
    )
    lineage = await prompts["yaam.prompt.artifact_lineage_summary"].render(
        {"artifact_id": "artifact-readiness-001"}
    )

    assert "without mutating YAAM" in repair[0].content.text
    assert "artifact-readiness-001" in repair[0].content.text
    assert "artifact-run-001" in repair[0].content.text
    assert "without mutating YAAM" in lineage[0].content.text
    assert "artifact-readiness-001" in lineage[0].content.text


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


def _mcp_sdk_log_record(exc_type: type[BaseException]) -> logging.LogRecord:
    return logging.LogRecord(
        name=MCP_STREAMABLE_HTTP_LOGGER,
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Error in message router",
        args=(),
        exc_info=(exc_type, exc_type(), None),
    )


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
