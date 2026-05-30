# YAAM User Guide

YAAM is a memory layer for agent systems. It provides public interfaces for
querying memory, assembling context, explaining evidence, recording curated
benchmark decisions, and correlating external traces without exposing raw
storage backends to customers.

## Memory Model

YAAM organizes memory into four layers:

- **L1 session memory**: short-lived working context associated with a session,
  task, run, or agent.
- **L2 facts**: durable factual records with provenance and scope.
- **L3 episodes**: richer experience records and observations, including
  provider-assisted assimilation where configured.
- **L4 knowledge artifacts**: finalized, higher-level knowledge documents or
  artifacts derived from lower layers.

Public interfaces return scoped and provenance-aware results. Callers should
provide stable scope fields such as `session_id`, `agent_id`, `task_id`,
`tenant_id`, and `run_id` when they are available.

## Public Interfaces

- **MCP v1 stdio**: best for agent hosts, desktop tools, coding assistants, and
  integrations that speak the Model Context Protocol.
- **REST v2**: best for service-to-service integrations, batch workflows,
  benchmark infrastructure, and systems that need HTTP APIs.
- **API Wall**: best for OpenAI-compatible benchmark/chat flows where benchmark
  isolation matters.

## Provenance And Scope

YAAM responses are designed to carry provenance, scope, and trace metadata.
Customers should treat those fields as part of the product contract rather than
debug-only decoration. They are used to explain where memory came from, why a
result was included or filtered, and how a result relates to external traces or
benchmark artifacts.

On shared deployments, YAAM exports Phoenix/OpenTelemetry spans asynchronously
with batch delivery. This does not change caller behavior: continue passing
`traceparent` when available and reading trace metadata from REST/MCP responses.
Phoenix UI/API visibility may lag the request by a short batch delay.

For benchmark-sensitive flows, callers should declare their role. The main
roles are:

- `benchmark_runtime_agent`: runtime retrieval that must not leak benchmark
  answer material.
- `benchmark_maintainer`: maintainer-only curation and Gold task decisions.
- `post_run_ingestion_service`: post-run trace and artifact ingestion.

## What YAAM Is Not

YAAM is not:

- A raw database gateway.
- An arbitrary SQL, Cypher, vector, or search query execution surface.
- A replacement for customer orchestration logic.
- An always-autonomous lifecycle system.
- A place to store secrets, provider keys, or raw sensitive reasoning traces.

## Choosing An Interface

| Use case | Recommended interface |
| --- | --- |
| Agent host needs memory tools | MCP v1 stdio |
| Service or benchmark harness needs HTTP | REST v2 |
| OpenAI-compatible chat or benchmark runtime | API Wall |
| Operator validation of MCP contracts | MCP stdio validation tests |
| Batch ingestion of curation or trace metadata | REST v2 |

## Next Steps

- Use the [MCP v1 stdio guide](mcp-v1.md) for tool/resource/prompt integration.
- Use the [REST v2 guide](rest-v2.md) for HTTP integration.
- Use the [public contracts reference](../reference/public-contracts.md) when
  mapping response fields into customer systems.
- Review the [requirements registry](../requirements/README.md) and
  [YAAM 0.10 release notes](../releases/0.10.md) for current coverage and
  deferred items.
