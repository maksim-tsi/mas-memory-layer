# agentic-scm-tra26 YAAM Readiness Instructions

**Consumer project:** `agentic-scm-tra26`  
**YAAM project namespace:** `YAAM_PROJECT_ID=agentic-scm-tra26`  
**Primary interface:** REST v2  
**Secondary interface:** MCP v1 read/discovery checks  
**Report file:** `docs/integrations/consumer-readiness-2026-05-30/reports/YYYY-MM-DD-agentic-scm-tra26-readiness-report.md`

## What This Project Should Validate

TRA asked for benchmark-safe memory integration through public YAAM interfaces, with no dependency
on LangChain tools or YAAM internal storage libraries. The current YAAM surface should be tested
against these requirement groups:

| Requirement | Expected current coverage |
| --- | --- |
| `YAAM-REQ-0001` API Wall, REST v2, and MCP remain distinct | implemented |
| `YAAM-REQ-0004` REST v2 for service and batch integration | implemented |
| `YAAM-REQ-0005` L2 scoped fact store/retrieve | implemented |
| `YAAM-REQ-0006` L3 episode assimilation | implemented |
| `YAAM-REQ-0007` L3 semantic query | implemented |
| `YAAM-REQ-0008` L4 final artifact storage | implemented |
| `YAAM-REQ-0009` provenance on reads/writes | implemented; verify evidence quality |
| `YAAM-REQ-0010` session/task/run scoping | implemented; verify no leakage |
| `YAAM-REQ-0014` trace/Phoenix observability | implemented; verify trace ids |
| `YAAM-REQ-0016` Evidence Table | mixed; verify usefulness for TRA debug |
| `YAAM-REQ-0017` CIAR explanation | mixed; audit/debug use |
| `YAAM-REQ-0026` no LangChain customer contract | implemented |
| `YAAM-REQ-0027` no direct YAAM internals | implemented |
| `YAAM-REQ-0033` fail-fast writes | implemented; verify negative scenario |

## Required Checks

Run these from the MacBook or the actual TRA runtime that can reach the LAN endpoint.

### 1. Health

```bash
curl -fsS http://192.168.107.187:8002/health
```

Record status, response summary, timestamp, and whether all required tiers are healthy.

### 2. L2 Deterministic Tool Output

Use `POST /v2/memory/l2/facts` with `action: store` to store a synthetic deterministic TRA fact,
for example a planner/executor observation. Then retrieve it from the same `session_id`.

Use a session id shaped like:

```text
agentic-scm-tra26-readiness-<timestamp>
```

Expected: store returns a fact id; retrieve returns the fact only in the same session.

### 3. L2 Session Isolation

Retrieve from a different session id and verify the fact is not accidentally returned. This is the
most important TRA safety check because benchmark tasks must not leak into each other.

### 4. L3 Planner Query And Episode Assimilation

Run:

- `POST /v2/memory/l3/query` before assimilation with a realistic planner question.
- `POST /v2/memory/l3/assimilate` with a synthetic TRA episode describing task state, tool output,
  and decision context.
- `POST /v2/memory/l3/query` again and verify ranked results, provenance, and no Qdrant dimension
  errors.

Expected: L3 uses OpenRouter Qwen embeddings through YAAM and the project-scoped Qdrant namespace.
TRA should not compute embeddings itself.

### 5. L4 Final Artifact

Run `POST /v2/memory/l4/finalize` with a short synthetic final answer/evidence artifact. Verify a
knowledge id, provenance, and durable retrieval through L4 search if available in the TRA test
harness.

### 6. MCP Readiness Smoke

Use MCP Streamable HTTP as an agent-host compatibility check:

- discover tools, resources, and prompts;
- call `yaam.health.check`;
- call `yaam.memory.get_context` or `yaam.memory.query` with the same TRA scope;
- call `yaam.evidence.table` if the test harness can construct a simple claim/evidence request;
- verify `yaam.l2.store_fact` is denied when write gates are disabled.

Mutating MCP tools should be tested only during an allowlisted synthetic write window.

### 7. Negative Scenario

Send L2 `action: store` without valid `content`. Expected: structured HTTP `400` rather than a
silent success.

## Report Focus

TRA should answer:

- Can the benchmark runtime use REST v2 without depending on YAAM internals?
- Does session/task scoping prevent cross-task leakage?
- Are trace ids and Phoenix evidence sufficient for benchmark debugging?
- Are L3/L4 failures surfaced as explicit, retryable/non-retryable errors?
- Is Evidence Table/CIAR useful enough for audit, or only partially implemented for TRA?

