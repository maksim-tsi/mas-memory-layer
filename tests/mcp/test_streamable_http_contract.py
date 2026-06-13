import json
import os
from typing import Any

import httpx
import pytest
from mcp.client.streamable_http import streamablehttp_client
from pydantic import AnyUrl

from mcp import ClientSession
from src.mcp.server import MCP_PROMPT_NAMES, MCP_TOOL_NAMES, create_mcp_server, parse_args
from tests.mcp.fixtures import RecordingMCPService


@pytest.mark.asyncio
async def test_mcp_streamable_http_fixture_discovery_and_read_contract() -> None:
    app = create_mcp_server(
        RecordingMCPService(), parse_args(["--transport", "streamable-http"])
    ).streamable_http_app()

    async with app.router.lifespan_context(app):
        async with (
            streamablehttp_client(
                "http://testserver/mcp", httpx_client_factory=_asgi_client_factory(app)
            ) as (read_stream, write_stream, _get_session_id),
            ClientSession(read_stream, write_stream) as session,
        ):
            (
                tools,
                resources,
                resource_templates,
                prompts,
                health,
                ciar,
                prompt,
                denied,
            ) = await _read_contract(session)

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
        assert [item.name for item in prompts.prompts] == list(MCP_PROMPT_NAMES)
        assert health["summary"] == "Health checked."
        assert health["health"]["status"] == "ok"
        assert json.loads(ciar.contents[0].text)["formula"]
        assert "without mutation" in prompt.messages[0].content.text
        error = _decode_error_payload(denied)
        assert error["code"] == "permission.writes_disabled"
        assert error["operation"] == "yaam.l2.store_fact"


@pytest.mark.asyncio
async def test_mcp_streamable_http_live_read_contract_is_env_gated() -> None:
    if os.environ.get("YAAM_MCP_RUN_LIVE_HTTP_CONTRACT") != "1":
        pytest.skip(
            "Set YAAM_MCP_RUN_LIVE_HTTP_CONTRACT=1 to run live MCP Streamable HTTP checks."
        )

    url = os.environ.get("YAAM_MCP_HTTP_URL", "http://192.168.107.187:8003/mcp")
    async with (
        streamablehttp_client(url) as (read_stream, write_stream, _get_session_id),
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


async def _read_contract(session: ClientSession) -> tuple[Any, ...]:
    await session.initialize()
    tools = await session.list_tools()
    resources = await session.list_resources()
    resource_templates = await session.list_resource_templates()
    prompts = await session.list_prompts()
    health = _decode_tool_result(await session.call_tool("yaam.health.check", {}))
    ciar = await session.read_resource(AnyUrl("yaam://config/ciar"))
    prompt = await session.get_prompt(
        "yaam.prompt.memory_inspection", {"session_id": "session-a"}
    )
    denied = await session.call_tool(
        "yaam.l2.store_fact",
        {"session_id": "session-a", "agent_id": "agent-a", "content": "Fact."},
    )
    return tools, resources, resource_templates, prompts, health, ciar, prompt, denied


def _asgi_client_factory(app: Any):
    def factory(
        headers: dict[str, str] | None = None,
        timeout: httpx.Timeout | None = None,
        auth: httpx.Auth | None = None,
    ) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            headers=headers,
            timeout=timeout,
            auth=auth,
        )

    return factory


def _decode_tool_result(result: Any) -> dict[str, Any]:
    assert not result.isError
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured
    return json.loads(_first_text(result))


def _decode_error_payload(result: Any) -> dict[str, Any]:
    assert result.isError
    message = _first_text(result)
    return json.loads(message[message.index("{") :])["error"]


def _first_text(result: Any) -> str:
    assert result.content
    content = result.content[0]
    assert hasattr(content, "text")
    return content.text
