import json
import sys
from pathlib import Path

import pytest
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import AnyUrl

from mcp import ClientSession
from src.mcp.server import MCP_PROMPT_NAMES, MCP_TOOL_NAMES

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_mcp_stdio_discovery_smoke() -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp.server", "--agent-type", "full", "--agent-variant", "mcp"],
        cwd=REPO_ROOT,
    )

    async with (
        stdio_client(server_params) as (read_stream, write_stream),
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
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp.server", "--agent-type", "full", "--agent-variant", "mcp"],
        cwd=REPO_ROOT,
    )

    async with (
        stdio_client(server_params) as (read_stream, write_stream),
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
