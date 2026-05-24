"""Test-only MCP stdio server backed by an in-memory recording service."""

from __future__ import annotations

import asyncio
import os

from src.mcp.server import create_mcp_server
from src.observability import tracing
from tests.mcp.fixtures import RecordingMCPService, WriteEnabledRecordingMCPService


async def run() -> None:
    """Run the fixture MCP server over stdio."""
    tracing._get_tracer = lambda _tracer_name: None
    service = (
        WriteEnabledRecordingMCPService()
        if os.environ.get("YAAM_MCP_FIXTURE_WRITES") == "1"
        else RecordingMCPService()
    )
    server = create_mcp_server(service)
    await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(run())
