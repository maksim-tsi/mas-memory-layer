# scm-cognitive-sandwich YAAM Readiness Instructions

**Consumer project:** `scm-cognitive-sandwich`  
**YAAM project namespace:** `YAAM_PROJECT_ID=scm-cognitive-sandwich`  
**Primary interface:** MCP v1  
**Secondary interface:** REST v2 smoke checks  
**Report file:** `docs/integrations/consumer-readiness-2026-05-30/reports/YYYY-MM-DD-scm-cognitive-sandwich-readiness-report.md`

## What This Project Should Validate

SCM Cognitive Sandwich is artifact-centric and MCP-first. Current YAAM should be evaluated for
generic memory, evidence, and durable artifact support. If the Cognitive Sandwich MCP domain pack is
enabled, also verify its read-only artifact/evidence resources and prompts. Native mutating artifact
lifecycle tools remain expected product gaps until a separate artifact-service milestone exists.

| Requirement | Expected current coverage |
| --- | --- |
| `YAAM-REQ-0002` MCP memory query | implemented |
| `YAAM-REQ-0003` MCP context assembly | implemented |
| `YAAM-REQ-0006` L3 episode assimilation | implemented |
| `YAAM-REQ-0007` L3 semantic query | implemented |
| `YAAM-REQ-0008` L4 final artifact storage | implemented generically |
| `YAAM-REQ-0009` provenance | implemented; verify evidence quality |
| `YAAM-REQ-0010` scoping | implemented; verify no leakage |
| `YAAM-REQ-0011` read-only MCP resources | implemented |
| `YAAM-REQ-0012` allowlisted MCP writes | implemented |
| `YAAM-REQ-0016` Evidence Table | mixed; verify artifact usefulness |
| `YAAM-REQ-0019` artifact draft/revision/feedback/commit lineage | partial at most; v0.1 domain pack may reconstruct lineage from metadata but does not enforce lifecycle transitions |
| `YAAM-REQ-0020` artifact lineage resources | implemented through Cognitive Sandwich domain pack as metadata-derived read-only views |
| `YAAM-REQ-0021` deterministic feedback/solver evidence | implemented generically |
| `YAAM-REQ-0028` transitional facade until MCP parity | partially implemented by generic MCP surface |
| `YAAM-REQ-0030` autonomous lifecycle consolidation | deferred |
| `YAAM-REQ-0032` domain-specific artifact prompts | implemented through Cognitive Sandwich domain pack |

## Required Checks

### 1. MCP Discovery And Health

Against `http://192.168.107.187:8003/mcp`, verify:

- tool/resource/prompt discovery works;
- `yaam.health.check` succeeds;
- `yaam://config/ciar` is readable;
- common prompts render.

When the Cognitive Sandwich domain pack is enabled for
`YAAM_PROJECT_ID=scm-cognitive-sandwich`, discovery should also include:

- `yaam://artifacts/{artifact_id}/lineage`
- `yaam://sessions/{session_id}/artifacts`
- `yaam://runs/{run_id}/artifacts`
- `yaam://runs/{run_id}/evidence`
- `yaam://incidents/{incident_id}/reports`
- `yaam.prompt.artifact_repair_context`
- `yaam.prompt.artifact_lineage_summary`

If these resources are absent in the current test window, record this under
`YAAM-REQ-0020` and `YAAM-REQ-0032`; generic MCP may still be healthy, but the
domain pack is not ready.

### 2. Artifact Context Query

Call `yaam.memory.get_context` or `yaam.memory.query` with an artifact-oriented scope:

```json
{
  "session_id": "scm-cognitive-sandwich-readiness-<timestamp>",
  "task_id": "artifact-repair-readiness",
  "run_id": "artifact-run-001",
  "caller_role": "benchmark_runtime_agent",
  "visibility_scope": "benchmark_runtime"
}
```

Expected: structured response with provenance, leakage guard metadata, and no secret exposure.
An empty result is acceptable for a fresh namespace.

### 3. Store Deterministic Feedback

During an allowlisted write window, use one of the generic write paths to store synthetic
deterministic feedback:

- L2 fact for a small solver/verifier observation;
- L3 episode for a failed or repaired artifact attempt;
- L4 finalization for the final artifact or report.

Expected: writes return created ids and provenance. Later reads should retrieve the same evidence
within the project namespace.

Use canonical metadata so generic reads and any Cognitive Sandwich domain views can project artifact
lineage:

```json
{
  "domain": "cognitive_sandwich",
  "artifact_id": "artifact-readiness-001",
  "revision_id": "revision-001",
  "parent_revision_id": "revision-000",
  "feedback_id": "feedback-001",
  "commit_id": "commit-001",
  "run_id": "artifact-run-001",
  "thread_id": "scm-cognitive-sandwich-readiness-<timestamp>",
  "incident_id": "incident-readiness-001",
  "scenario_id": "scenario-readiness-001",
  "artifact_kind": "routing_parameters",
  "artifact_status": "draft",
  "revision_number": 1,
  "verification_state": "infeasible",
  "feedback_type": "solver_iis",
  "source_system": "deterministic_solver",
  "payload_hash": "sha256:synthetic-readiness",
  "fatal_status": "FATAL_VALIDATION_ERROR",
  "retry_count": 1
}
```

If the domain pack is enabled, read back the synthetic records through the artifact resources above.
The domain pack should return read-only projections; it should not mutate YAAM.

### 4. Evidence Table

Call `yaam.evidence.table` or the REST equivalent if used by the project. Use a simple claim such
as:

```text
The artifact repair pass corrected the synthetic validation failure.
```

Expected: evidence rows include source/provenance metadata and warnings when evidence is partial.

### 5. REST v2 Smoke

Even though SCM Cognitive Sandwich is MCP-first, run at least one REST smoke:

- `GET /health`;
- L3 query or L4 finalize with synthetic data;
- one negative scenario such as missing L2 content.

This confirms the same backend service layer behaves consistently across interfaces.

### 6. Expected Gap Classification

Do not treat these as surprise failures. Record them as product gaps:

- dedicated mutating `yaam.artifact.*` lifecycle tools: `missing`;
- `yaam://artifacts/{artifact_id}/lineage` resource: `implemented` or `partial` only if the
  Cognitive Sandwich domain pack returns metadata-derived lineage;
- first-class draft/revision/feedback/commit graph model: `missing` or `partially implemented`;
- domain-specific artifact repair prompts: `implemented` or `partial` only if
  `yaam.prompt.artifact_repair_context` and `yaam.prompt.artifact_lineage_summary` render;
- autonomous consolidation/distillation: `deferred`.

In the report, classify requirements as follows:

- `YAAM-REQ-0020`: implemented/partial based on artifact lineage resource evidence.
- `YAAM-REQ-0021`: implemented/partial based on deterministic feedback write/read evidence.
- `YAAM-REQ-0032`: implemented/partial based on artifact prompt evidence.
- `YAAM-REQ-0019`: partial unless YAAM provides native draft/revision/feedback/commit lifecycle
  semantics, not only metadata-derived projections.

## Report Focus

SCM Cognitive Sandwich should answer:

- Is generic MCP memory/context enough for a temporary integration?
- Which artifact lifecycle primitive is the first blocker for production use?
- Does generic L3/L4 storage preserve enough provenance for artifact repair audit?
- If the domain pack is enabled, do artifact resources and prompts materially reduce dependence on
  the transitional facade?
- Are write gates and read-only resources acceptable for agent safety?
- Can the project migrate away from transitional facade usage with the current MCP surface, or is
  dedicated artifact MCP still required?
