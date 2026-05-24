from src.mcp.server import (
    MCP_PROMPT_NAMES,
    MCP_RESOURCE_URIS,
    MCP_SDK_REQUIREMENT,
    MCP_TOOL_NAMES,
    create_mcp_server,
    parse_args,
)


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
