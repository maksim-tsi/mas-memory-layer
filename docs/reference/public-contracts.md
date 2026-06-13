# Public Contracts Reference

This reference summarizes customer-visible response shapes shared across MCP v1
and REST v2. Adapter-specific wrappers may differ, but the service-layer fields
below are the compatibility target.

## ScopeEnvelope

```json
{
  "session_id": "session-001",
  "agent_id": "agent-001",
  "task_id": "task-001",
  "tenant_id": "tenant-001",
  "run_id": "run-001",
  "user_id": "user-001",
  "caller_role": "benchmark_runtime_agent",
  "visibility_scope": "benchmark_runtime",
  "domain_ids": {
    "benchmark_task_id": "scm-task-001"
  },
  "metadata": {},
  "traceparent": "00-00000000000000000000000000000000-0000000000000000-00"
}
```

## MemoryResult

```json
{
  "content": "Relevant memory text.",
  "tier": "L3",
  "score": 0.91,
  "source_id": "episode-001",
  "metadata": {},
  "provenance": {
    "source_tier": "L3",
    "source_id": "episode-001"
  }
}
```

## ContextResponse

```json
{
  "session_id": "session-001",
  "items": [],
  "context_summary": null,
  "estimated_tokens": 0,
  "partial": false,
  "warnings": [],
  "visibility_scope": "benchmark_runtime",
  "leakage_guard_passed": true,
  "filtered_item_count": 0
}
```

## LeakageGuardResult

```json
{
  "leakage_guard_passed": true,
  "visibility_scope": "benchmark_runtime",
  "forbidden_fields": [],
  "filtered_item_count": 0,
  "checked_item_count": 1,
  "warnings": []
}
```

## WriteAck

```json
{
  "status": "success",
  "operation": "yaam.l2.store_fact",
  "created_id": "fact-001",
  "updated_id": null,
  "provenance": {
    "source_tier": "L2",
    "source_id": "fact-001"
  },
  "audit_id": null
}
```

## YAAMErrorPayload

```json
{
  "code": "permission_denied",
  "message": "Caller is not allowed to perform this operation.",
  "retryable": false,
  "partial": false,
  "operation": "yaam.curation.record_decision",
  "affected_tier": "SYSTEM",
  "trace_id": null,
  "audit_id": null,
  "details": {
    "required_role": "benchmark_maintainer"
  }
}
```

The fields `code`, `operation`, `retryable`, and `affected_tier` are stable
error contract fields.

## CurationDecisionRecord

```json
{
  "curation_record_id": "curation-001",
  "task_id": "scm-task-001",
  "decision": "accepted",
  "reason": "Source triad is valid.",
  "source_triad": {
    "prompt": "prompt-001",
    "oracle": "oracle-001",
    "rubric": "rubric-001"
  },
  "reviewer": "reviewer-001",
  "visibility_scope": "maintainer_only",
  "provenance": {
    "source_tier": "L2",
    "source_id": "curation-001"
  },
  "metadata": {}
}
```

## TraceCorrelationRecord

```json
{
  "correlation_id": "trace-correlation-001",
  "run_id": "run-001",
  "task_id": "task-001",
  "trace_id": "phoenix-trace-001",
  "artifact_ref": "artifacts/run-001/events.jsonl",
  "openrouter_call_id": "openrouter-call-001",
  "linked_memory_ids": ["fact-001"],
  "error_summary": null,
  "trace_status": "verified",
  "provenance": {
    "source_tier": "L2",
    "source_id": "trace-correlation-001"
  },
  "metadata": {}
}
```

## Read Degradation And Write Fail-Fast

Read operations may return partial or degraded results when a backend is
temporarily unavailable. Responses should still preserve scope, provenance, and
structured error or warning metadata.

Write and lifecycle operations are fail-fast. They must not report `success`
unless the requested persistence or lifecycle action completed.

## MCP And REST Compatibility

MCP and REST use different protocol wrappers, but overlapping operations should
preserve the same service-layer meaning for scope, provenance, leakage guard
fields, write acknowledgements, and structured errors.

This reference supports the public-interface requirements tracked in
`YAAM-REQ-0001` through `YAAM-REQ-0038`, including benchmark-safe retrieval
(`YAAM-REQ-0036`), curation records (`YAAM-REQ-0037`), and trace correlation
(`YAAM-REQ-0038`).

## Related Documentation

- [Requirements registry](../requirements/README.md)
- [YAAM 0.10 release notes](../releases/0.10.md)
