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
- MCP Streamable HTTP is used for shared lab or production access from remote
  consumer systems.
- REST v2 is used by service-to-service and benchmark integrations.

## Configuration Areas

- Storage and environment variables:
  [environment guide](../environment-guide.md).
- Backend connectivity:
  [connectivity cheatsheet](../IAC/connectivity-cheatsheet.md).
- LLM provider configuration:
  [LLM provider guide](../llm_provider_guide.md).
- MCP operation:
  [MCP v1 stdio runbook](../runbooks/mcp-v1-stdio-server.md).
- Validation:
  [admin validation guide](validation.md).

## OpenRouter Runtime Defaults

Shared REST/MCP runtimes use OpenRouter `tencent/hy3-preview` for generation and
`qwen/qwen3-embedding-8b` for embeddings by default. Tencent Hy3 is
reasoning-heavy, so production-like probes and L3 assimilation runs should use
the configured YAAM budget instead of tiny connectivity budgets:

```bash
OPENROUTER_MODEL=tencent/hy3-preview
OPENROUTER_EMBEDDING_MODEL=qwen/qwen3-embedding-8b
MAS_MAX_OUTPUT_TOKENS=8192
MAS_OPENROUTER_TIMEOUT=120.0
OPENROUTER_REASONING_EFFORT=low
OPENROUTER_REASONING_EXCLUDE=true
```

Avoid `max_tokens=64` style probes for Tencent Hy3 readiness. They can exhaust
the completion budget on reasoning and return empty text even when OpenRouter
connectivity is healthy.

## Phoenix Span Export

Shared REST/MCP runtimes use Phoenix/OpenTelemetry batch span exporting by
default:

```bash
YAAM_OTEL_SPAN_PROCESSOR=batch
YAAM_OTEL_FORCE_FLUSH_TIMEOUT_MS=5000
OTEL_BSP_MAX_QUEUE_SIZE=2048
OTEL_BSP_MAX_EXPORT_BATCH_SIZE=512
OTEL_BSP_SCHEDULE_DELAY=1000
OTEL_BSP_EXPORT_TIMEOUT=30000
```

Use `YAAM_OTEL_SPAN_PROCESSOR=simple` only for local debugging. Consumer
requests and responses are unchanged; callers still provide `traceparent` and
scope fields through the documented REST/MCP contracts.

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

## MCP Streamable HTTP Runtime

For shared consumer testing, run the dedicated `yaam-mcp` Compose service. The
service uses the same MCP tool surface as stdio and publishes Streamable HTTP on:

```text
http://192.168.107.187:8003/mcp
```

The service should remain read-only by default:

```bash
YAAM_MCP_ENABLE_WRITES=false
YAAM_MCP_ENABLE_LIFECYCLE=false
YAAM_MCP_ALLOWLISTED_TOOLS=
```

Do not expose write or lifecycle tools to consumer systems unless the validation
run explicitly requires synthetic writes and the target tools are allowlisted.

## MCP Domain Packs

YAAM MCP can expose optional read-only domain packs in addition to the generic
MCP v1 surface:

```bash
YAAM_MCP_DOMAIN_PACKS=auto
```

Supported values are currently `auto`, `none`, and `skill-factory`. The default
`auto` enables the Skill Factory pack only when
`YAAM_PROJECT_ID=scm-skill-factory`. Other project namespaces keep the generic
MCP resource and prompt discovery surface unless a pack is explicitly enabled.

The Skill Factory pack adds read-only resources for skills, CTTs, run episodes,
QA status, active-tool status, and the `yaam.prompt.repair_pattern_summary`
prompt. It does not enable MCP writes or change REST behavior.

The planned `cognitive-sandwich` pack should use the same operational model
after implementation:

```bash
YAAM_PROJECT_ID=scm-cognitive-sandwich
YAAM_MCP_DOMAIN_PACKS=auto
```

It is intended to add read-only artifact/evidence resources and artifact repair
prompts over canonical metadata written through existing L2/L3/L4 tools. It is
not expected to expose mutating `yaam.artifact.*` lifecycle tools in v0.1.

When validating Cognitive Sandwich, operators should:

- switch the shared endpoint to `YAAM_PROJECT_ID=scm-cognitive-sandwich`;
- keep `YAAM_MCP_ENABLE_WRITES=false`, `YAAM_MCP_ENABLE_LIFECYCLE=false`, and an
  empty allowlist by default;
- verify generic MCP discovery first;
- verify Cognitive Sandwich resources and prompts only after the pack is
  implemented and enabled;
- open a short allowlisted write window only for synthetic L2/L3/L4 records with
  canonical artifact metadata.

If Cognitive Sandwich resources return empty results after implementation, first
check whether the synthetic records include `domain="cognitive_sandwich"` plus
artifact/run identifiers. Empty resources are usually a metadata issue, not a
DBMS outage.

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

Supported public surfaces for YAAM 0.10 are MCP v1 stdio, MCP v1 Streamable
HTTP, REST v2, API Wall benchmark/chat flows, documented validation commands,
and the public contracts reference.

Unsupported surfaces include direct database mutation, arbitrary SQL/Cypher,
undocumented provider-specific traces, and customer-specific MCP resources that
are not part of the generic surface or an explicitly enabled domain pack.

## Related Documentation

- [Requirements registry](../requirements/README.md)
- [YAAM 0.10 release notes](../releases/0.10.md)
