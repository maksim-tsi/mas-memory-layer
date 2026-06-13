# MCP v1 Guide

YAAM MCP v1 exposes memory read, evidence, curation, trace correlation, and
gated write/lifecycle operations over Model Context Protocol transports. The
same tools, resources, prompts, permission gates, and response contracts are
available through both supported transports:

- **stdio** for local MCP hosts that launch YAAM as a subprocess.
- **Streamable HTTP** for shared lab or production MCP runtimes operated on a
  server such as `local-yaam-host`.

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
http://127.0.0.1:8003/mcp
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

Shared YAAM runtimes export Phoenix spans asynchronously with batch delivery.
MCP callers do not need extra arguments for this; keep propagating
`traceparent` through the scope envelope when an upstream trace exists. Trace
metadata in MCP responses remains available immediately, while Phoenix span
visibility can lag briefly.

Shared runtimes use OpenRouter `tencent/hy3-preview` with an 8192-token output
budget and a 120-second provider timeout for generation-backed operations.
Small direct probes, such as 64-token checks, can be misleading for this
reasoning-heavy model because the response budget may be spent before visible
text is emitted.

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

## Optional Domain Packs

YAAM can expose optional MCP domain packs. Domain packs add read-only resources
and prompts for a specific consumer workflow while keeping the generic MCP v1
tools unchanged.

The first supported pack is `skill-factory`. It is enabled automatically when
the shared runtime is started with:

```bash
YAAM_PROJECT_ID=scm-skill-factory
YAAM_MCP_DOMAIN_PACKS=auto
```

It adds these read-only resources:

- `yaam://skills/{skill_name}`
- `yaam://ctts/{ctt_id}`
- `yaam://runs/{run_id}/episodes`
- `yaam://skill-factory/qa-status/{qa_status}/runs`
- `yaam://skill-factory/active-tool-status/{active_tool_status}/runs`

Skill Factory views work best when existing L2/L3/L4/curation writes include
canonical metadata keys:

```json
{
  "domain": "skill_factory",
  "skill_name": "inventory-router",
  "ctt_id": "ctt-42",
  "run_id": "skill-run-001",
  "qa_status": "failed",
  "active_tool_status": "stale",
  "sandbox_outcome": "schema_error",
  "repair_action": "patched input schema",
  "artifact_kind": "validated_skill_summary"
}
```

The pack is not a separate YAAM version. It does not enable write tools, mutate
memory through resources, or change generic MCP discovery for other project
namespaces.

The `cognitive-sandwich` pack follows the same isolation pattern for SCM
Cognitive Sandwich artifact workflows. It is enabled automatically when the
shared runtime is started with:

```bash
YAAM_PROJECT_ID=scm-cognitive-sandwich
YAAM_MCP_DOMAIN_PACKS=auto
```

The v0.1 Cognitive Sandwich pack adds read-only artifact and evidence views over
canonical metadata already stored through generic L2/L3/L4 write tools:

- `yaam://artifacts/{artifact_id}/lineage`
- `yaam://sessions/{session_id}/artifacts`
- `yaam://runs/{run_id}/artifacts`
- `yaam://runs/{run_id}/evidence`
- `yaam://incidents/{incident_id}/reports`

Cognitive Sandwich views use canonical metadata keys such as:

```json
{
  "domain": "cognitive_sandwich",
  "artifact_id": "artifact-001",
  "revision_id": "revision-001",
  "parent_revision_id": "revision-000",
  "feedback_id": "feedback-001",
  "commit_id": "commit-001",
  "run_id": "run-001",
  "thread_id": "thread-001",
  "incident_id": "incident-001",
  "scenario_id": "scenario-001",
  "artifact_kind": "routing_parameters",
  "artifact_status": "draft",
  "revision_number": 1,
  "verification_state": "infeasible",
  "feedback_type": "solver_iis",
  "source_system": "deterministic_solver",
  "payload_hash": "sha256:example",
  "fatal_status": "FATAL_VALIDATION_ERROR",
  "retry_count": 3
}
```

This pack is not a native artifact lifecycle service. It does not by itself add
mutating `yaam.artifact.*` tools, enforce draft/revision/feedback/commit state
transitions, or validate that only feasible revisions are committed. Those
capabilities remain a separate artifact-service milestone.

## Prompts

Prompt templates are intended to help agent hosts request consistent memory
operations. YAAM 0.10 exposes these prompts:

- `yaam.prompt.evidence_table`
- `yaam.prompt.memory_inspection`
- `yaam.prompt.ciar_explanation`
- `yaam.prompt.retrieval_strategy`

When the Skill Factory domain pack is enabled, prompt discovery also includes:

- `yaam.prompt.repair_pattern_summary`

When the Cognitive Sandwich domain pack is enabled, prompt discovery also
includes:

- `yaam.prompt.artifact_repair_context`
- `yaam.prompt.artifact_lineage_summary`

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
