# scm-skill-factory YAAM Readiness Instructions

**Consumer project:** `scm-skill-factory`  
**YAAM project namespace:** `YAAM_PROJECT_ID=scm-skill-factory`  
**Primary interfaces:** REST v2 and MCP v1  
**Report file:** `docs/integrations/consumer-readiness-2026-05-30/reports/YYYY-MM-DD-scm-skill-factory-readiness-report.md`

## What This Project Should Validate

Skill Factory requires memory around skill generation, QA, curation, repair attempts, and validated
facts. YAAM provides generic memory, evidence, curation, and trace-correlation primitives plus an
optional Skill Factory MCP domain pack for skill/CTT/run inspection views.

| Requirement | Expected current coverage |
| --- | --- |
| `YAAM-REQ-0002` MCP memory query | implemented |
| `YAAM-REQ-0003` MCP context assembly | implemented |
| `YAAM-REQ-0004` REST v2 for batch/scripts | implemented |
| `YAAM-REQ-0005` L2 scoped facts | implemented |
| `YAAM-REQ-0006` L3 episode assimilation | implemented |
| `YAAM-REQ-0008` L4 durable skill artifacts | implemented generically |
| `YAAM-REQ-0011` read-only MCP resources by default | implemented |
| `YAAM-REQ-0012` allowlisted MCP writes | implemented |
| `YAAM-REQ-0016` Evidence Table | mixed; verify usefulness |
| `YAAM-REQ-0017` CIAR explanation | mixed; audit/debug use |
| `YAAM-REQ-0021` deterministic feedback/sandbox evidence | implemented generically |
| `YAAM-REQ-0022` skill generation/QA/curation memory views | implemented by Skill Factory MCP domain pack; verify usefulness |
| `YAAM-REQ-0023` skill/CTT/run MCP resources | implemented by Skill Factory MCP domain pack |
| `YAAM-REQ-0029` contradiction/supersession review | mixed |
| `YAAM-REQ-0031` common MCP prompts | implemented |
| `YAAM-REQ-0032` domain-specific Skill Factory prompts | implemented by Skill Factory MCP domain pack |

## Skill Factory Domain Pack

The Skill Factory pack is enabled when the shared runtime is started with:

```bash
YAAM_PROJECT_ID=scm-skill-factory
YAAM_MCP_DOMAIN_PACKS=auto
```

Expected MCP discovery includes:

- `yaam://skills/{skill_name}`
- `yaam://ctts/{ctt_id}`
- `yaam://runs/{run_id}/episodes`
- `yaam://skill-factory/qa-status/{qa_status}/runs`
- `yaam://skill-factory/active-tool-status/{active_tool_status}/runs`
- `yaam.prompt.repair_pattern_summary`

Use these metadata keys in existing L2/L3/L4/curation writes so the domain views
can project the right records:

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

## Required Checks

### 1. MCP Discovery And Health

Against `http://192.168.107.187:8003/mcp`, verify:

- tools list includes `yaam.memory.query`, `yaam.memory.get_context`, `yaam.evidence.table`,
  `yaam.ciar.explain`, `yaam.curation.record_decision`, and `yaam.curation.list_decisions`;
- resources include generic health/config/schemas/session resources and the Skill Factory domain
  resources listed above;
- prompts include common inspection/evidence/CIAR prompts and
  `yaam.prompt.repair_pattern_summary`;
- `yaam.health.check` succeeds.

### 2. Pre-Generation Context

Call `yaam.memory.get_context` or `POST /v2/memory/context` with a synthetic skill generation scope:

```json
{
  "session_id": "scm-skill-factory-readiness-<timestamp>",
  "task_id": "skill-generation-readiness",
  "run_id": "skill-run-001",
  "caller_role": "benchmark_runtime_agent",
  "visibility_scope": "benchmark_runtime"
}
```

Expected: context response includes scope, provenance, leakage guard metadata, and either relevant
items or an empty result with no error.

### 3. Store Sandbox Failure Or Repair Episode

Use REST L3 assimilation or the allowlisted MCP `yaam.l3.assimilate_episode` during a write window
to store a synthetic failed skill generation attempt, including:

- skill name;
- CTT id;
- sandbox or QA failure summary;
- repair action taken;
- result status.

Expected: episode id and provenance are returned; later L3 query can retrieve the scenario.

### 4. Store Validated Skill Fact

Use L2 to store a validated skill fact such as a tool invocation constraint, schema rule, or QA
decision. Retrieve from the same session and verify it does not appear in another session.

### 5. Curation And Evidence

Run curation/evidence checks through REST or MCP:

- create a synthetic curation decision with `benchmark_maintainer` role;
- list curation decisions;
- generate an Evidence Table for a simple claim about the skill result;
- call `yaam.ciar.explain` for an audit/debug explanation if available in the harness.

### 6. L4 Durable Skill Artifact

Use `POST /v2/memory/l4/finalize` or allowlisted `yaam.l4.finalize_artifact` to store a short
synthetic skill artifact or validation summary.

### 7. Domain Pack Views

After synthetic writes, read:

- `yaam://skills/<skill-name>`
- `yaam://ctts/<ctt-id>`
- `yaam://runs/<run-id>/episodes`
- `yaam://skill-factory/qa-status/<qa-status>/runs`
- `yaam://skill-factory/active-tool-status/<active-tool-status>/runs`

Expected: each resource returns JSON with `domain_pack=skill-factory`, filters, counts, visible
items or runs, and no secrets. Empty results are acceptable only if the synthetic writes did not use
the canonical metadata keys.

## Report Focus

Skill Factory should answer:

- Are generic YAAM memory primitives enough for a first integration?
- Which skill-specific views are necessary before production use?
- Does curation/evidence behavior preserve scope and provenance?
- Are default MCP write gates acceptable for agent-host safety?
- Are Skill Factory domain pack resources enough for debugging and replaying failed
  skill-generation/repair loops?
