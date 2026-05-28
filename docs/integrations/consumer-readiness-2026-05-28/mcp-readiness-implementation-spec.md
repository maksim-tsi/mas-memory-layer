# YAAM MCP v0.1 Readiness Implementation Specification

**Date:** 2026-05-28  
**Status:** Proposed implementation specification  
**Scope:** Minimum MCP surface required before consumer systems can perform MCP readiness testing  
**Related RFC:** `docs/RFC/2026-05-18-yaam-mcp-and-memory-policy-evolution.md`

## 1. Summary

YAAM's first consumer readiness wave includes MCP as an explicit integration goal. The current
repository state documents MCP as an intended product interface, but does not expose a deployed MCP
server for consumers. This specification defines the minimum MCP v0.1 implementation required
before MCP can be assigned to consumers as an executable test rather than a provider-side blocker.

MCP v0.1 must be a separate adapter. It must not replace REST v2, and it must not introduce direct
storage-adapter access. The implementation should call the same YAAM public/service contract used
by REST v2 so that MCP behavior cannot drift away from `/v2/memory/*`.

## 2. Runtime and Transport

The first transport should be remote-friendly HTTP on `skz-data-lv`. Stdio can be added later for
local developer convenience, but it should not be the only transport for consumer readiness because
several consumers run from separate hosts.

Required runtime properties:

- expose a documented MCP endpoint reachable from consumer hosts;
- run as a separate `yaam-mcp` service or a clearly separate entrypoint;
- target the existing YAAM runtime at `http://192.168.107.187:8002`;
- keep secrets in runtime configuration only;
- never print `.env` contents, provider keys, database passwords, bearer tokens, or private
  authorization headers;
- support enough logging to correlate MCP calls with REST v2 requests and `traceparent` values.

If an MCP SDK, dependency, or lockfile update is required, obtain explicit dependency-change
approval before modifying `pyproject.toml`, `poetry.lock`, or any equivalent dependency manifest.

## 3. Capability Boundary

MCP v0.1 exposes a thin tool layer over the implemented REST v2 contract. It does not implement new
memory semantics.

Allowed:

- translate MCP tool inputs into REST v2 requests;
- return MCP `structuredContent` plus a compact text summary;
- pass through session, task, agent, provenance, and trace fields;
- surface REST status/error classifications in a stable structured form.

Not allowed in v0.1:

- direct reads or writes through `src/storage/`;
- arbitrary Cypher, SQL, Redis commands, Qdrant queries, or Typesense queries from MCP clients;
- autonomous lifecycle operations not already represented by the REST v2 readiness contract;
- secret exposure through MCP resources, logs, or error responses.

## 4. Required Tools

Tool names should be stable ASCII identifiers.

| Tool | Purpose | REST backing behavior |
| --- | --- | --- |
| `yaam.health` | Report YAAM service health. | `GET /health` |
| `yaam.l2.store_fact` | Store a working-memory fact. | `POST /v2/memory/l2/facts` with `action: store` |
| `yaam.l2.retrieve_facts` | Retrieve working-memory facts by session. | `POST /v2/memory/l2/facts` with `action: retrieve` |
| `yaam.l3.assimilate` | Assimilate natural-language text into episodic memory. | `POST /v2/memory/l3/assimilate` |
| `yaam.l3.query` | Query episodic memory using natural language. | `POST /v2/memory/l3/query` |
| `yaam.l4.finalize` | Store a final artifact in semantic memory. | `POST /v2/memory/l4/finalize` |

## 5. Input Schema Requirements

Every write or query tool must require `session_id` and `agent_id` unless the backing REST endpoint
does not support `agent_id`. `yaam.l4.finalize` must require `task_id`, `session_id`, `title`,
`final_artifact`, and `consensus_metadata`.

Minimum schemas:

```text
yaam.health:
  input: {}

yaam.l2.store_fact:
  session_id: string
  task_id: string
  agent_id: string
  content: string
  traceparent: optional string

yaam.l2.retrieve_facts:
  session_id: string
  task_id: string
  agent_id: string
  traceparent: optional string

yaam.l3.assimilate:
  session_id: string
  agent_id: string
  text_to_assimilate: string
  domain_tags: array[string], default []
  traceparent: optional string

yaam.l3.query:
  session_id: string
  agent_id: string
  nl_query: string
  top_k: integer, default 3, minimum 1
  filters: object, default {}
  traceparent: optional string

yaam.l4.finalize:
  task_id: string
  session_id: string
  title: string
  final_artifact: string
  consensus_metadata: object
  traceparent: optional string
```

The implementation should validate schemas before calling REST v2. Validation failures should be
returned as MCP tool errors with structured field information.

## 6. Output Shape

Each tool result must include structured content and a short text summary.

Minimum structured fields:

```json
{
  "ok": true,
  "tool": "yaam.l2.store_fact",
  "http_status": 200,
  "yaam_endpoint": "http://192.168.107.187:8002/v2/memory/l2/facts",
  "traceparent": "optional original traceparent",
  "data": {}
}
```

For failures:

```json
{
  "ok": false,
  "tool": "yaam.l3.assimilate",
  "http_status": 502,
  "error_class": "provider_failure",
  "retryable": true,
  "detail": "sanitized detail",
  "data": {}
}
```

Suggested error classes:

- `validation_error`
- `not_configured`
- `provider_failure`
- `network_error`
- `timeout`
- `unexpected_response`

## 7. Docker and Deployment Expectations

The deployment should support a separate MCP runtime on `skz-data-lv`.

Recommended shape:

```text
service name: yaam-mcp
target REST base URL: http://mas-agent:8080 or http://192.168.107.187:8002
published endpoint: documented after implementation
```

The MCP service may share the same Docker network as `mas-agent`, but it must have a separately
documented start/restart command. The runtime documentation must state which endpoint consumers
should configure and how to verify tool discovery.

## 8. Acceptance Criteria

MCP v0.1 is ready for consumer testing when all of the following are true:

- consumers can connect to the MCP endpoint from a non-YAAM host;
- tool discovery returns all six required tools;
- each tool exposes a stable JSON schema;
- write and query tools require `session_id` and provenance fields as specified;
- each tool returns structured content and a compact text summary;
- REST v2 errors are mapped to stable MCP error classes;
- no tool exposes secrets or raw `.env` contents;
- contract tests pass locally;
- smoke tests pass against the `skz-data-lv` deployment;
- the consumer assignment is updated with the real MCP endpoint and no longer marks MCP as provider-side pending.

## 9. Test Plan

Before asking consumers to test MCP:

1. Run schema discovery tests for all required tools.
2. Run validation tests for missing required fields.
3. Run local tool calls against a local or test YAAM REST v2 instance.
4. Run remote smoke calls against `http://192.168.107.187:8002`.
5. Verify that error mappings preserve useful detail without exposing secrets.
6. Verify that `traceparent` values are forwarded to REST v2 calls when supplied.
7. Run a consumer-style smoke test from MacBook and, if available, from `skz-dev-lv`.

After implementation touches `src/`, follow repository verification discipline:

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest tests/ -v
```

## 10. Non-Goals for v0.1

- no replacement of REST v2;
- no direct storage adapter API;
- no arbitrary graph or SQL query tool;
- no lifecycle promotion/consolidation/distillation tools;
- no Evidence Table or CIAR MCP tools until the shared service layer is ready;
- no dependency changes without explicit approval.

