# MCP v1 Guide

YAAM MCP v1 exposes memory read, evidence, curation, trace correlation, and
gated write/lifecycle operations over Model Context Protocol transports. The
same tools, resources, prompts, permission gates, and response contracts are
available through both supported transports:

- **stdio** for local MCP hosts that launch YAAM as a subprocess.
- **Streamable HTTP** for shared lab or production MCP runtimes operated on a
  server such as `skz-data-lv`.

## Launch With Stdio

From the repository root, use the project virtual environment:

```bash
./.venv/bin/python -m src.mcp.server --transport stdio --agent-type full --agent-variant mcp
```

The process is a stdio server. It should be launched by an MCP host, not used
as an interactive terminal command.

## Launch With Streamable HTTP

For shared remote access, run the same MCP server with Streamable HTTP:

```bash
./.venv/bin/python -m src.mcp.server \
  --transport streamable-http \
  --agent-type full \
  --agent-variant mcp \
  --mcp-host 0.0.0.0 \
  --mcp-port 8081 \
  --mcp-path /mcp
```

The lab deployment publishes this as:

```text
http://192.168.107.187:8003/mcp
```

Use Streamable HTTP when the consumer system should connect to a centrally
operated YAAM MCP runtime instead of managing a local checkout, virtual
environment, and backend configuration.

## Scope Envelope

Most calls accept or produce a scope envelope. Provide stable identifiers when
available:

```json
{
  "session_id": "customer-session-001",
  "agent_id": "agent-runtime-001",
  "task_id": "task-001",
  "tenant_id": "tenant-001",
  "run_id": "run-001",
  "caller_role": "benchmark_runtime_agent",
  "visibility_scope": "benchmark_runtime",
  "traceparent": "00-00000000000000000000000000000000-0000000000000000-00"
}
```

Do not include secrets, provider keys, database credentials, or raw private
reasoning traces in MCP arguments.

## Tools

Read and explanation tools:

- `yaam.health.check`
- `yaam.memory.query`
- `yaam.memory.get_context`
- `yaam.l2.search_facts`
- `yaam.l3.search_episodes`
- `yaam.l4.search_knowledge`
- `yaam.ciar.explain`
- `yaam.evidence.table`
- `yaam.contradiction.review`
- `yaam.curation.list_decisions`
- `yaam.trace.lookup`

Write and lifecycle tools are disabled unless explicitly enabled and
allowlisted:

- `yaam.l2.store_fact`
- `yaam.l3.assimilate_episode`
- `yaam.l4.finalize_artifact`
- `yaam.curation.record_decision`
- `yaam.trace.record_correlation`

## Resources

MCP resources are read-only. YAAM 0.10 includes static service resources and
templated runtime resources such as:

- `yaam://health`
- `yaam://config/ciar`
- `yaam://schemas/fact`
- `yaam://schemas/episode`
- `yaam://schemas/knowledge-document`
- `yaam://sessions/{session_id}/context`
- `yaam://sessions/{session_id}/facts`
- `yaam://facts/{fact_id}`
- `yaam://episodes/{episode_id}`
- `yaam://knowledge/{knowledge_id}`

Customer-specific SCM-Cert-Bench resource views remain deferred under
`YAAM-REQ-0039`.

## Prompts

Prompt templates are intended to help agent hosts request consistent memory
operations. YAAM 0.10 exposes these prompts:

- `yaam.prompt.evidence_table`
- `yaam.prompt.memory_inspection`
- `yaam.prompt.ciar_explanation`
- `yaam.prompt.retrieval_strategy`

Hosts should still own task orchestration and final user-facing behavior.

## Write And Lifecycle Gates

MCP write/lifecycle operations require explicit environment gates:

```bash
YAAM_MCP_ENABLE_WRITES=true
YAAM_MCP_ENABLE_LIFECYCLE=true
YAAM_MCP_ALLOWLISTED_TOOLS=yaam.l2.store_fact,yaam.l3.assimilate_episode,yaam.l4.finalize_artifact,yaam.curation.record_decision,yaam.trace.record_correlation
```

Live validation additionally uses test-specific flags such as
`YAAM_MCP_RUN_LIVE_CONTRACT=1` and `YAAM_MCP_RUN_LIVE_WRITE_CONTRACT=1`.
Those flags should be used only for intentional validation with synthetic
records.

## Benchmark Roles

- `benchmark_runtime_agent` may perform leakage-guarded runtime reads.
- `benchmark_maintainer` may write maintainer-only Gold task curation
  decisions.
- `post_run_ingestion_service` may write external trace and artifact
  correlation metadata after a run.

These roles support `YAAM-REQ-0029`, `YAAM-REQ-0036`, `YAAM-REQ-0037`, and
`YAAM-REQ-0038`.

## Example: Leakage-Guarded Context

```json
{
  "tool": "yaam.memory.get_context",
  "arguments": {
    "query": "What prior implementation notes are safe for this benchmark task?",
    "scope": {
      "session_id": "bench-session-001",
      "task_id": "scm-task-001",
      "caller_role": "benchmark_runtime_agent",
      "visibility_scope": "benchmark_runtime"
    },
    "max_items": 5
  }
}
```

Expected payload fields include `items`, `scope`, `provenance`,
`leakage_guard_passed`, and `filtered_item_count`.

## Example: Curation Decision

```json
{
  "tool": "yaam.curation.record_decision",
  "arguments": {
    "decision_type": "gold_task_acceptance",
    "decision": "accepted",
    "task_id": "scm-task-001",
    "source_triad": {
      "benchmark_task_id": "scm-task-001",
      "evidence_id": "evidence-001",
      "maintainer_decision_id": "decision-001"
    },
    "scope": {
      "session_id": "curation-session-001",
      "caller_role": "benchmark_maintainer",
      "visibility_scope": "maintainer_only"
    }
  }
}
```

Successful write tools return `WriteAck` payloads with `status`, `operation`,
`created_id`, `scope`, and `provenance`.

## Common Errors

Unallowlisted writes and unauthorized lifecycle calls return structured YAAM
errors:

```json
{
  "code": "permission_denied",
  "message": "Tool is not allowlisted for MCP write access.",
  "operation": "yaam.l2.store_fact",
  "retryable": false,
  "affected_tier": "SYSTEM",
  "details": {
    "required_gate": "YAAM_MCP_ALLOWLISTED_TOOLS"
  }
}
```

Read operations may degrade with partial results when one backend is
unavailable. Write operations are fail-fast and should not silently report
success when persistence failed.

## Related Documentation

- [Requirements registry](../requirements/README.md)
- [YAAM 0.10 release notes](../releases/0.10.md)
