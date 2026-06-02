import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import AnyUrl

from mcp import ClientSession
from src.mcp.server import MCP_PROMPT_NAMES, MCP_TOOL_NAMES

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-m", "src.mcp.server", "--agent-type", "full", "--agent-variant", "mcp"],
    cwd=REPO_ROOT,
    env={**os.environ},
)
FIXTURE_SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-m", "tests.mcp.stdio_fixture_server"],
    cwd=REPO_ROOT,
)
WRITE_FIXTURE_SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-m", "tests.mcp.stdio_fixture_server"],
    cwd=REPO_ROOT,
    env={**os.environ, "YAAM_MCP_FIXTURE_WRITES": "1"},
)


@pytest.mark.asyncio
async def test_mcp_stdio_discovery_smoke() -> None:
    async with (
        stdio_client(PRODUCTION_SERVER_PARAMS) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()

        tools = await session.list_tools()
        resources = await session.list_resources()
        resource_templates = await session.list_resource_templates()
        prompts = await session.list_prompts()

    assert [tool.name for tool in tools.tools] == list(MCP_TOOL_NAMES)
    assert [resource.uri.unicode_string() for resource in resources.resources] == [
        "yaam://health",
        "yaam://config/ciar",
        "yaam://schemas/fact",
        "yaam://schemas/episode",
        "yaam://schemas/knowledge-document",
    ]
    assert [template.uriTemplate for template in resource_templates.resourceTemplates] == [
        "yaam://sessions/{session_id}/context",
        "yaam://sessions/{session_id}/facts",
        "yaam://facts/{fact_id}",
        "yaam://episodes/{episode_id}",
        "yaam://knowledge/{knowledge_id}",
    ]
    assert [prompt.name for prompt in prompts.prompts] == list(MCP_PROMPT_NAMES)


@pytest.mark.asyncio
async def test_mcp_stdio_static_resource_reads_and_prompt_gets() -> None:
    async with (
        stdio_client(PRODUCTION_SERVER_PARAMS) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()

        ciar = await session.read_resource(AnyUrl("yaam://config/ciar"))
        fact_schema = await session.read_resource(AnyUrl("yaam://schemas/fact"))
        episode_schema = await session.read_resource(AnyUrl("yaam://schemas/episode"))
        knowledge_schema = await session.read_resource(
            AnyUrl("yaam://schemas/knowledge-document")
        )
        prompts = {
            name: await session.get_prompt(name, args)
            for name, args in {
                "yaam.prompt.evidence_table": {"query": "dock status"},
                "yaam.prompt.memory_inspection": {"session_id": "session-a"},
                "yaam.prompt.ciar_explanation": {"claim": "Claim one"},
                "yaam.prompt.retrieval_strategy": {"task": "Plan retrieval"},
            }.items()
        }

    ciar_payload = json.loads(ciar.contents[0].text)
    assert ciar_payload["formula"] == "(certainty * impact) * age_decay * recency_boost"
    assert "api_key" not in ciar.contents[0].text.lower()
    assert "secret" not in ciar.contents[0].text.lower()

    assert json.loads(fact_schema.contents[0].text)["title"] == "Fact"
    assert json.loads(episode_schema.contents[0].text)["title"] == "Episode"
    assert json.loads(knowledge_schema.contents[0].text)["title"] == "KnowledgeDocument"

    assert "dock status" in prompts["yaam.prompt.evidence_table"].messages[0].content.text
    assert "without mutation" in prompts["yaam.prompt.memory_inspection"].messages[0].content.text
    assert "Claim one" in prompts["yaam.prompt.ciar_explanation"].messages[0].content.text
    assert "partial-result" in prompts["yaam.prompt.retrieval_strategy"].messages[0].content.text


@pytest.mark.asyncio
async def test_mcp_stdio_fixture_read_tools_return_structured_contracts() -> None:
    async with (
        stdio_client(FIXTURE_SERVER_PARAMS) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()

        health = _decode_tool_result(await session.call_tool("yaam.health.check", {}))
        memory_query = _decode_tool_result(
            await session.call_tool(
                "yaam.memory.query",
                {
                    "session_id": "session-a",
                    "agent_id": "agent-a",
                    "task_id": "task-a",
                    "tenant_id": "tenant-a",
                    "run_id": "run-a",
                    "query": "dock status",
                    "limit": 2,
                },
            )
        )
        context = _decode_tool_result(
            await session.call_tool(
                "yaam.memory.get_context",
                {
                    "session_id": "session-a",
                    "agent_id": "agent-a",
                    "task_id": "task-a",
                    "caller_role": "benchmark_runtime_agent",
                    "visibility_scope": "benchmark_runtime",
                    "require_leakage_guard": True,
                },
            )
        )
        l2 = _decode_tool_result(
            await session.call_tool(
                "yaam.l2.search_facts",
                {"session_id": "session-a", "agent_id": "agent-a", "query": "dock"},
            )
        )
        l3 = _decode_tool_result(
            await session.call_tool(
                "yaam.l3.search_episodes",
                {"session_id": "session-a", "agent_id": "agent-a", "query": "dock"},
            )
        )
        l4 = _decode_tool_result(
            await session.call_tool(
                "yaam.l4.search_knowledge",
                {"session_id": "session-a", "agent_id": "agent-a", "query": "dock"},
            )
        )
        ciar = _decode_tool_result(
            await session.call_tool(
                "yaam.ciar.explain",
                {"session_id": "session-a", "agent_id": "agent-a", "certainty": 0.7},
            )
        )
        evidence = _decode_tool_result(
            await session.call_tool(
                "yaam.evidence.table",
                {"session_id": "session-a", "agent_id": "agent-a", "query": "dock"},
            )
        )
        review = _decode_tool_result(
            await session.call_tool(
                "yaam.contradiction.review",
                {
                    "session_id": "session-a",
                    "agent_id": "agent-a",
                    "task_id": "task-a",
                    "claims": ["Claim one."],
                    "expected_behavior": "safe refusal",
                },
            )
        )
        curation = _decode_tool_result(
            await session.call_tool(
                "yaam.curation.list_decisions",
                {
                    "session_id": "session-a",
                    "agent_id": "agent-a",
                    "task_id": "task-a",
                    "caller_role": "benchmark_maintainer",
                },
            )
        )
        trace = _decode_tool_result(
            await session.call_tool(
                "yaam.trace.lookup",
                {
                    "session_id": "session-a",
                    "agent_id": "agent-a",
                    "task_id": "task-a",
                    "run_id": "run-a",
                    "caller_role": "post_run_ingestion_service",
                },
            )
        )

    assert health["summary"] == "Health checked."
    assert health["health"]["status"] == "ok"

    result = memory_query["results"][0]
    assert memory_query["summary"] == "Memory query complete."
    assert result["tier"] == "L2"
    assert result["source_id"] == "fact-1"
    assert result["provenance"]["session_id"] == "session-a"
    assert result["provenance"]["agent_id"] == "agent-a"
    assert result["provenance"]["task_id"] == "task-a"
    assert result["provenance"]["tenant_id"] == "tenant-a"
    assert result["provenance"]["run_id"] == "run-a"

    assert context["summary"] == "Context assembled."
    assert context["context"]["session_id"] == "session-a"
    assert context["context"]["items"][0]["source_id"] == "fact-context"
    assert context["context"]["items"][0]["provenance"]["task_id"] == "task-a"
    assert context["context"]["leakage_guard_passed"] is True

    assert l2["summary"] == "L2 facts retrieved."
    assert l2["results"][0]["tier"] == "L2"
    assert l2["results"][0]["source_id"] == "fact-search"

    assert l3["summary"] == "L3 episodes retrieved."
    assert l3["results"][0]["tier"] == "L3"
    assert l3["results"][0]["source_id"] == "episode-search"

    assert l4["summary"] == "L4 knowledge retrieved."
    assert l4["results"][0]["tier"] == "L4"
    assert l4["results"][0]["source_id"] == "knowledge-search"

    assert ciar["summary"] == "CIAR explained."
    assert ciar["explanation"]["score"] == 0.42
    assert ciar["explanation"]["components"]["certainty"] == 0.7
    assert ciar["explanation"]["scope"]["session_id"] == "session-a"

    assert evidence["summary"] == "Evidence table assembled."
    assert evidence["evidence_table"]["rows"][0]["source_id"] == "fact-evidence"
    assert evidence["evidence_table"]["rows"][0]["provenance"]["agent_id"] == "agent-a"

    assert review["summary"] == "Contradiction reviewed."
    assert review["review"]["contradiction_detected"] is True
    assert review["review"]["safe_refusal_rationale"] == "Fixture safe refusal."

    assert curation["summary"] == "Curation decisions listed."
    assert curation["decisions"][0]["task_id"] == "task-a"
    assert curation["decisions"][0]["visibility_scope"] == "maintainer_only"

    assert trace["summary"] == "Trace correlations listed."
    assert trace["correlations"][0]["trace_id"] == "phoenix-trace-fixture"
    assert trace["correlations"][0]["task_id"] == "task-a"


@pytest.mark.asyncio
async def test_mcp_stdio_fixture_templated_resource_is_read_only_json() -> None:
    async with (
        stdio_client(FIXTURE_SERVER_PARAMS) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()

        context = await session.read_resource(AnyUrl("yaam://sessions/session-a/context"))

    payload = json.loads(context.contents[0].text)
    assert payload["session_id"] == "session-a"
    assert payload["items"][0]["source_id"] == "fact-context"
    assert payload["items"][0]["provenance"]["agent_id"] == "resource-reader"
    serialized = json.dumps(payload).lower()
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "secret" not in serialized


@pytest.mark.asyncio
async def test_mcp_stdio_fixture_write_denial_returns_structured_error() -> None:
    async with (
        stdio_client(FIXTURE_SERVER_PARAMS) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()

        result = await session.call_tool(
            "yaam.l2.store_fact",
            {"session_id": "session-a", "agent_id": "agent-a", "content": "Fact."},
        )
        curation_result = await session.call_tool(
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
        )

    payload = _decode_error_payload(result)
    assert payload["code"] == "permission.writes_disabled"
    assert payload["operation"] == "yaam.l2.store_fact"
    assert payload["retryable"] is False
    assert payload["affected_tier"] == "SYSTEM"

    curation_payload = _decode_error_payload(curation_result)
    assert curation_payload["code"] == "permission.writes_disabled"
    assert curation_payload["operation"] == "yaam.curation.record_decision"


@pytest.mark.asyncio
async def test_mcp_stdio_fixture_write_tools_return_acknowledgements() -> None:
    async with (
        stdio_client(WRITE_FIXTURE_SERVER_PARAMS) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()

        l2 = _decode_tool_result(
            await session.call_tool(
                "yaam.l2.store_fact",
                {
                    "session_id": "session-a",
                    "agent_id": "agent-a",
                    "task_id": "task-a",
                    "content": "Fact content.",
                },
            )
        )
        l3 = _decode_tool_result(
            await session.call_tool(
                "yaam.l3.assimilate_episode",
                {
                    "session_id": "session-a",
                    "agent_id": "agent-a",
                    "task_id": "task-a",
                    "text_to_assimilate": "A durable episode should be stored.",
                    "domain_tags": ["engineering"],
                },
            )
        )
        l4 = _decode_tool_result(
            await session.call_tool(
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
        )
        curation = _decode_tool_result(
            await session.call_tool(
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
        )
        trace = _decode_tool_result(
            await session.call_tool(
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
        )

    assert l2["summary"] == "Fact stored."
    assert l2["ack"]["status"] == "success"
    assert l2["ack"]["operation"] == "yaam.l2.store_fact"
    assert l2["ack"]["created_id"] == "fact-written"
    assert l2["ack"]["provenance"]["source_tier"] == "L2"

    assert l3["summary"] == "Episode assimilated."
    assert l3["ack"]["status"] == "success"
    assert l3["ack"]["operation"] == "yaam.l3.assimilate_episode"
    assert l3["ack"]["created_id"] == "episode-written"
    assert l3["ack"]["provenance"]["source_tier"] == "L3"

    assert l4["summary"] == "L4 artifact finalized."
    assert l4["ack"]["status"] == "success"
    assert l4["ack"]["operation"] == "yaam.l4.finalize_artifact"
    assert l4["ack"]["created_id"] == "knowledge-written"
    assert l4["ack"]["provenance"]["source_tier"] == "L4"

    assert curation["summary"] == "Curation decision recorded."
    assert curation["ack"]["status"] == "success"
    assert curation["ack"]["operation"] == "yaam.curation.record_decision"
    assert curation["ack"]["created_id"] == "curation-written"
    assert curation["ack"]["provenance"]["source_tier"] == "L2"

    assert trace["summary"] == "Trace correlation recorded."
    assert trace["ack"]["status"] == "success"
    assert trace["ack"]["operation"] == "yaam.trace.record_correlation"
    assert trace["ack"]["created_id"] == "tracecorr-written"
    assert trace["ack"]["provenance"]["source_tier"] == "L2"


@pytest.mark.asyncio
async def test_mcp_stdio_live_read_contract_is_env_gated() -> None:
    if os.environ.get("YAAM_MCP_RUN_LIVE_CONTRACT") != "1":
        pytest.skip("Set YAAM_MCP_RUN_LIVE_CONTRACT=1 to run live MCP read contract checks.")

    async with (
        stdio_client(PRODUCTION_SERVER_PARAMS) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()

        tools = await session.list_tools()
        health = await session.call_tool("yaam.health.check", {})
        ciar = await session.read_resource(AnyUrl("yaam://config/ciar"))
        prompt = await session.get_prompt(
            "yaam.prompt.memory_inspection", {"session_id": "session-a"}
        )

    assert "yaam.health.check" in {tool.name for tool in tools.tools}
    assert _decode_tool_result(health)["health"]["status"] in {"ok", "degraded", "unavailable"}
    assert json.loads(ciar.contents[0].text)["formula"]
    assert "without mutation" in prompt.messages[0].content.text


@pytest.mark.asyncio
async def test_mcp_stdio_live_write_contract_is_env_gated() -> None:
    if os.environ.get("YAAM_MCP_RUN_LIVE_WRITE_CONTRACT") != "1":
        pytest.skip(
            "Set YAAM_MCP_RUN_LIVE_WRITE_CONTRACT=1 to run live MCP write contract checks."
        )
    if os.environ.get("YAAM_MCP_RUN_LIVE_CONTRACT") != "1":
        pytest.skip("Set YAAM_MCP_RUN_LIVE_CONTRACT=1 before live MCP write checks.")
    if os.environ.get("YAAM_MCP_ENABLE_WRITES", "").lower() not in {"1", "true", "yes", "on"}:
        pytest.skip("Set YAAM_MCP_ENABLE_WRITES=true before live MCP write checks.")
    if os.environ.get("YAAM_MCP_ENABLE_LIFECYCLE", "").lower() not in {"1", "true", "yes", "on"}:
        pytest.skip("Set YAAM_MCP_ENABLE_LIFECYCLE=true before live MCP lifecycle checks.")

    allowlist = {
        item.strip()
        for item in os.environ.get("YAAM_MCP_ALLOWLISTED_TOOLS", "").split(",")
        if item.strip()
    }
    required = {
        "yaam.l2.store_fact",
        "yaam.l3.assimilate_episode",
        "yaam.l4.finalize_artifact",
    }
    if "*" not in allowlist and not required.issubset(allowlist):
        pytest.skip(
            "Set YAAM_MCP_ALLOWLISTED_TOOLS to include all MCP write/lifecycle tools."
        )

    suffix = uuid.uuid4().hex[:8]
    session_id = f"mcp-live-contract-{suffix}"
    task_id = f"mcp-live-contract-task-{suffix}"

    async with (
        stdio_client(PRODUCTION_SERVER_PARAMS) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()

        l2 = _decode_tool_result(
            await session.call_tool(
                "yaam.l2.store_fact",
                {
                    "session_id": session_id,
                    "agent_id": "mcp-live-contract",
                    "task_id": task_id,
                    "content": "Synthetic MCP live write contract fact.",
                },
            )
        )
        l3 = _decode_tool_result(
            await session.call_tool(
                "yaam.l3.assimilate_episode",
                {
                    "session_id": session_id,
                    "agent_id": "mcp-live-contract",
                    "task_id": task_id,
                    "text_to_assimilate": "Synthetic MCP live lifecycle episode.",
                    "domain_tags": ["mcp-contract"],
                },
            )
        )
        l4 = _decode_tool_result(
            await session.call_tool(
                "yaam.l4.finalize_artifact",
                {
                    "session_id": session_id,
                    "agent_id": "mcp-live-contract",
                    "task_id": task_id,
                    "title": "Synthetic MCP Live Contract Artifact",
                    "final_artifact": "Synthetic MCP live lifecycle artifact content.",
                    "consensus_metadata": {"source": "mcp-live-contract"},
                },
            )
        )

    for payload, operation, source_tier in (
        (l2, "yaam.l2.store_fact", "L2"),
        (l3, "yaam.l3.assimilate_episode", "L3"),
        (l4, "yaam.l4.finalize_artifact", "L4"),
    ):
        assert payload["ack"]["status"] == "success"
        assert payload["ack"]["operation"] == operation
        assert payload["ack"]["created_id"]
        assert payload["ack"]["provenance"]["source_tier"] == source_tier
        assert payload["ack"]["provenance"]["session_id"] == session_id
        assert payload["ack"]["provenance"]["agent_id"] == "mcp-live-contract"
        assert payload["ack"]["provenance"]["task_id"] == task_id


def _decode_tool_result(result: Any) -> dict[str, Any]:
    assert not result.isError
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured
    return _decode_first_text_json(result)


def _decode_error_payload(result: Any) -> dict[str, Any]:
    assert result.isError
    return _extract_error_payload(_first_text(result))


def _decode_first_text_json(result: Any) -> dict[str, Any]:
    return json.loads(_first_text(result))


def _first_text(result: Any) -> str:
    assert result.content
    content = result.content[0]
    assert hasattr(content, "text")
    return content.text


def _extract_error_payload(message: str) -> dict[str, Any]:
    return json.loads(message[message.index("{") :])["error"]
