# REST v2 Guide

YAAM REST v2 exposes memory and benchmark support operations under
`/v2/memory`. It is intended for service-to-service integrations, benchmark
harnesses, batch ingestion, and operational smoke checks.

## Request Conventions

- Use JSON request and response bodies.
- Provide stable scope fields such as `session_id`, `agent_id`, `task_id`,
  `tenant_id`, and `run_id` when available.
- Pass W3C trace context with a `traceparent` header or scope field when the
  caller has one.
- Do not send secrets, provider keys, database credentials, or raw sensitive
  reasoning traces in request bodies.

Shared YAAM deployments export Phoenix/OpenTelemetry spans asynchronously with
batch delivery. REST callers do not need to change payloads for this; response
trace metadata remains immediate, while Phoenix UI/API visibility can lag by a
short batch delay.

## Compatibility-Sensitive Endpoints

Existing tier endpoints remain compatibility-sensitive. Customers should not
depend on undocumented shape changes:

- `POST /v2/memory/l2/facts`
- `POST /v2/memory/l3/assimilate`
- `POST /v2/memory/l3/query`
- `POST /v2/memory/l4/finalize`

## Explicit Public Endpoints

YAAM 0.10 also exposes explicit endpoints for public customer workflows:

- `POST /v2/memory/query`
- `POST /v2/memory/context`
- `POST /v2/memory/curation/decisions`
- `GET /v2/memory/curation/decisions`
- `POST /v2/memory/trace-correlations`
- `GET /v2/memory/trace-correlations`

These endpoints use the same service-layer contracts as MCP v1 where the
operations overlap.

## Example: Guarded Context Read

```http
POST /v2/memory/context
Content-Type: application/json
traceparent: 00-00000000000000000000000000000000-0000000000000000-00
```

```json
{
  "query": "Return safe prior implementation notes for this benchmark task.",
  "max_items": 5,
  "scope": {
    "session_id": "rest-session-001",
    "task_id": "scm-task-001",
    "caller_role": "benchmark_runtime_agent",
    "visibility_scope": "benchmark_runtime"
  }
}
```

Example success:

```json
{
  "status": "success",
  "context": {
    "session_id": "rest-session-001",
    "items": [
      {
        "content": "Implementation note safe for benchmark runtime use.",
        "tier": "L3",
        "score": 0.91,
        "source_id": "episode-001",
        "provenance": {
          "source_tier": "L3",
          "source_id": "episode-001"
        }
      }
    ],
    "context_summary": "Implementation note safe for benchmark runtime use.",
    "estimated_tokens": 42,
    "partial": false,
    "warnings": [],
    "visibility_scope": "benchmark_runtime",
    "leakage_guard_passed": true,
    "filtered_item_count": 0
  }
}
```

`POST /v2/memory/query` returns the same leakage guard metadata in a separate
`leakage_guard` object:

```json
{
  "status": "success",
  "results": [
    {
      "content": "Implementation note safe for benchmark runtime use.",
      "tier": "L3",
      "score": 0.91,
      "source_id": "episode-001",
      "provenance": {
        "source_tier": "L3",
        "source_id": "episode-001"
      }
    }
  ],
  "leakage_guard": {
    "leakage_guard_passed": true,
    "visibility_scope": "benchmark_runtime",
    "forbidden_fields": [],
    "filtered_item_count": 0,
    "checked_item_count": 1,
    "warnings": []
  }
}
```

## Example: Curation Decision Write

```http
POST /v2/memory/curation/decisions
Content-Type: application/json
```

```json
{
  "decision": "accepted",
  "reason": "Source triad is valid.",
  "task_id": "scm-task-001",
  "source_triad": {
    "prompt": "prompt-001",
    "oracle": "oracle-001",
    "rubric": "rubric-001"
  },
  "reviewer": "reviewer-001",
  "session_id": "curation-session-001",
  "agent_id": "curation-service-001",
  "caller_role": "benchmark_maintainer",
  "visibility_scope": "maintainer_only"
}
```

Example success:

```json
{
  "status": "success",
  "ack": {
    "status": "success",
    "operation": "yaam.curation.record_decision",
    "created_id": "curation-001",
    "provenance": {
      "source_tier": "L2",
      "source_id": "curation-001"
    }
  }
}
```

## Example: Trace Correlation Write

```http
POST /v2/memory/trace-correlations
Content-Type: application/json
```

```json
{
  "session_id": "post-run-session-001",
  "agent_id": "post-run-ingestion-001",
  "task_id": "scm-task-001",
  "run_id": "run-001",
  "caller_role": "post_run_ingestion_service",
  "visibility_scope": "post_run",
  "trace_id": "phoenix-trace-001",
  "artifact_ref": "artifacts/run-001/events.jsonl",
  "openrouter_call_id": "openrouter-call-001",
  "linked_memory_ids": ["fact-001"],
  "trace_status": "verified"
}
```

Example success:

```json
{
  "status": "success",
  "ack": {
    "status": "success",
    "operation": "yaam.trace.record_correlation",
    "created_id": "trace-correlation-001",
    "provenance": {
      "source_tier": "L2",
      "source_id": "trace-correlation-001"
    }
  }
}
```

## Example: Structured Permission Error

```json
{
  "code": "permission.role_denied",
  "message": "Caller role is not allowed to perform this operation.",
  "operation": "yaam.curation.record_decision",
  "retryable": false,
  "partial": false,
  "affected_tier": "SYSTEM",
  "details": {
    "caller_role": "benchmark_runtime_agent",
    "required_role": "benchmark_maintainer"
  }
}
```

REST callers should treat `code`, `operation`, `retryable`, and
`affected_tier` as stable error contract fields.

## Requirement Coverage

The explicit benchmark-safe REST endpoints support `YAAM-REQ-0029`,
`YAAM-REQ-0036`, `YAAM-REQ-0037`, and `YAAM-REQ-0038`. Customer-specific
SCM-Cert-Bench MCP resources remain deferred under `YAAM-REQ-0039`.

## Related Documentation

- [Requirements registry](../requirements/README.md)
- [YAAM 0.10 release notes](../releases/0.10.md)
