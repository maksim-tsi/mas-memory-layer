"""Test-only MCP server backed by an in-memory recording service."""

from __future__ import annotations

import asyncio
import os

from src.mcp.server import create_mcp_server
from src.observability import tracing
from tests.mcp.fixtures import RecordingMCPService, WriteEnabledRecordingMCPService


async def run() -> None:
    """Run the fixture MCP server over the requested test transport."""
    tracing._get_tracer = lambda _tracer_name: None
    service = (
        WriteEnabledRecordingMCPService()
        if os.environ.get("YAAM_MCP_FIXTURE_WRITES") == "1"
        else RecordingMCPService()
    )
    transport = os.environ.get("YAAM_MCP_FIXTURE_TRANSPORT", "stdio")
    if transport == "streamable-http":
        args = [
            "--transport",
            "streamable-http",
            "--mcp-host",
            os.environ.get("YAAM_MCP_FIXTURE_HOST", "127.0.0.1"),
            "--mcp-port",
            os.environ.get("YAAM_MCP_FIXTURE_PORT", "8081"),
            "--mcp-path",
            os.environ.get("YAAM_MCP_FIXTURE_PATH", "/mcp"),
        ]
        from src.mcp.server import parse_args

        server = create_mcp_server(service, parse_args(args))
        await server.run_streamable_http_async()
    else:
        server = create_mcp_server(service)
        await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(run())
