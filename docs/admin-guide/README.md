# YAAM Admin Guide

This guide is for operators and administrators responsible for running and
validating YAAM 0.10.

## Operating Assumptions

- YAAM runs from a checked-out repository with a project virtual environment.
- Use `./.venv/bin/python`, `./.venv/bin/pytest`, and `./.venv/bin/ruff` from
  the repository root.
- Storage backends and LLM provider configuration are supplied through the
  local environment.
- MCP stdio is normally launched by an MCP host as a subprocess.
- REST v2 is used by service-to-service and benchmark integrations.

## Configuration Areas

- Storage and environment variables:
  [environment guide](../environment-guide.md).
- Backend connectivity:
  [connectivity cheatsheet](../IAC/connectivity-cheatsheet.md).
- LLM provider configuration:
  [LLM provider guide](../llm_provider_guide.md).
- MCP stdio operation:
  [MCP v1 stdio runbook](../runbooks/mcp-v1-stdio-server.md).
- Validation:
  [admin validation guide](validation.md).

## MCP Write And Lifecycle Controls

MCP write/lifecycle tools are disabled by default. Enable them only for
explicitly intended environments and allowlist the exact tools required:

```bash
YAAM_MCP_ENABLE_WRITES=true
YAAM_MCP_ENABLE_LIFECYCLE=true
YAAM_MCP_ALLOWLISTED_TOOLS=yaam.l2.store_fact,yaam.l3.assimilate_episode,yaam.l4.finalize_artifact,yaam.curation.record_decision,yaam.trace.record_correlation
```

REST v2 authorization and role checks are separate from MCP stdio launch flags.
Do not assume enabling an MCP tool changes REST behavior.

## Secret Handling Policy

Do not expose or paste:

- `.env` contents.
- Provider keys.
- Database credentials.
- Raw Phoenix credentials.
- Raw sensitive LLM reasoning traces.
- Private customer benchmark answer material.

Use secret names in documentation and support tickets, not secret values.

## Support Boundaries

Supported public surfaces for YAAM 0.10 are MCP v1 stdio, REST v2, API Wall
benchmark/chat flows, documented validation commands, and the public contracts
reference.

Unsupported surfaces include direct database mutation, arbitrary SQL/Cypher,
undocumented provider-specific traces, and customer-specific SCM-Cert-Bench MCP
resource views deferred under `YAAM-REQ-0039`.

## Related Documentation

- [Requirements registry](../requirements/README.md)
- [YAAM 0.10 release notes](../releases/0.10.md)
