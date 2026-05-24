import sys
from pathlib import Path

import pytest
from mcp.client.stdio import StdioServerParameters, stdio_client

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
