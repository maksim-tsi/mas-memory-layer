# YAAM Consumer Readiness Test Assignment

**Date:** 2026-05-28  
**Status:** Active test assignment  
**Audience:** YAAM downstream consumer systems that previously provided integration requirements  
**Primary runtime:** `skz-data-lv`  
**Primary endpoint:** `http://192.168.107.187:8002`

## 1. Objective

This assignment asks each consumer system to evaluate the current readiness of YAAM against its
own previously stated requirements and against the currently implemented YAAM public interface.
The expected result is not only a pass/fail verdict, but an evidence-backed report that can be
converted into prioritised implementation, documentation, deployment, or compatibility tasks.

The first readiness wave uses `skz-data-lv` as the canonical YAAM runtime. Consumers should call
YAAM from the same host or runtime from which they would normally integrate. This topology avoids
MacBook-local assumptions and exercises the production-like network boundary between consumer
systems and YAAM.

## 2. Recommended Topology

Use the following target unless the YAAM maintainers explicitly provide another endpoint for a
specific run:

```text
YAAM base URL: http://192.168.107.187:8002
Health check:  GET  /health
REST v2 API:   POST /v2/memory/*
MCP stdio:     ./.venv/bin/python -m src.mcp.server --transport stdio --agent-type full --agent-variant mcp
MCP HTTP:      http://192.168.107.187:8003/mcp
```

The active REST contract is `/v2/memory/*`. Do not use the older `/v2/semantic/*` examples as the
active endpoint contract.

MCP is an executable readiness target. YAAM supports two MCP v1 transports over the same tool,
resource, prompt, permission, and response contracts:

- stdio for MCP hosts that launch YAAM as a subprocess;
- Streamable HTTP for consumer systems that connect to the shared `skz-data-lv` runtime.

If `http://192.168.107.187:8003/mcp` is unavailable during a scheduled readiness run, record the
MCP HTTP result as a deployment blocker and still run the stdio checks when the consumer host can
launch the YAAM checkout or container locally.

## 3. Documentation References

If the consumer test runs on the MacBook checkout, use these absolute paths:

- `/Users/max/Documents/code/mas-memory-layer/docs/api/TRA_Integration_Guide_v2.md`
- `/Users/max/Documents/code/mas-memory-layer/docs/integrations/yaam_v2_connection_policy.md`
- `/Users/max/Documents/code/mas-memory-layer/docs/RFC/2026-05-18-yaam-mcp-and-memory-policy-evolution.md`
- `/Users/max/Documents/code/mas-memory-layer/docs/reports/2026-05-18-yaam-skz-data-lv-migration-execution-report.md`
- `/Users/max/Documents/code/mas-memory-layer/docs/integrations/consumer-readiness-2026-05-28/mcp-readiness-implementation-spec.md`

If the consumer test runs from another host, use the embedded contract summary in this document as
the required minimum reference. The maintainers can copy the source documents separately when a
consumer needs full context.

## 4. Embedded Contract Summary

Every request should include a unique `session_id`. Write operations should include `agent_id` and,
where the endpoint requires it, `task_id`. Consumers should send a W3C `traceparent` header for
correlation with YAAM/Phoenix traces when their runtime can generate one.

### Health

```http
GET http://192.168.107.187:8002/health
```

Expected readiness signal: HTTP `200` and a response indicating YAAM service health. Record any
unhealthy tier reported by the response.

### L2 Working Memory

Store:

```http
POST /v2/memory/l2/facts
Content-Type: application/json
traceparent: 00-11111111111111111111111111111111-2222222222222222-01
```

```json
{
  "session_id": "consumer-name-readiness-001",
  "task_id": "consumer-readiness-task-001",
  "agent_id": "consumer-agent-001",
  "action": "store",
  "content": "A readiness fact written by the consumer system."
}
```

Retrieve:

```json
{
  "session_id": "consumer-name-readiness-001",
  "task_id": "consumer-readiness-task-001",
  "agent_id": "consumer-agent-001",
  "action": "retrieve"
}
```

Expected result: store returns `status: success` and a `fact_id`; retrieve returns `status: success`
and a `facts` collection.

### L3 Episodic Memory

Assimilate:

```json
{
  "session_id": "consumer-name-readiness-001",
  "agent_id": "consumer-agent-001",
  "text_to_assimilate": "The consumer observed a supply-chain readiness event that should be available for later semantic retrieval.",
  "domain_tags": ["consumer-readiness", "supply-chain"]
}
```

Query:

```json
{
  "session_id": "consumer-name-readiness-001",
  "agent_id": "consumer-agent-001",
  "nl_query": "Which supply-chain readiness event was observed by this consumer?",
  "top_k": 3,
  "filters": {}
}
```

Expected result: assimilate returns HTTP `201` and an `episode_id`; query returns HTTP `200`,
`results`, and `provenance`. A `502` from L3 should be recorded with provider/timing evidence
because L3 depends on YAAM's internal LLM and embedding pipeline.

### L4 Semantic Memory

Finalize:

```json
{
  "task_id": "consumer-readiness-task-001",
  "session_id": "consumer-name-readiness-001",
  "title": "Consumer Readiness Smoke Artifact",
  "final_artifact": "A short final artifact produced by the consumer readiness test.",
  "consensus_metadata": {
    "consumer": "consumer-name",
    "votes": 1,
    "disagreements": "none"
  }
}
```

Expected result: HTTP `201`, `status: success`, and a `knowledge_id`.

### MCP v1 Surface

Required MCP readiness checks:

- discover tools, resources, and prompts;
- call `yaam.health.check`;
- read `yaam://config/ciar`;
- render `yaam.prompt.memory_inspection`;
- verify a default write denial for `yaam.l2.store_fact` when write gates are disabled.

Core MCP v1 tools:

```text
yaam.memory.query
yaam.memory.get_context
yaam.l2.store_fact
yaam.l2.search_facts
yaam.l3.search_episodes
yaam.l3.assimilate_episode
yaam.l4.search_knowledge
yaam.l4.finalize_artifact
yaam.ciar.explain
yaam.evidence.table
yaam.contradiction.review
yaam.health.check
yaam.curation.record_decision
yaam.curation.list_decisions
yaam.trace.record_correlation
yaam.trace.lookup
```

## 5. Required Test Tasks

Each consumer system must execute the following checks against its actual integration environment:

| ID | Check | Minimum evidence |
| --- | --- | --- |
| CR-001 | Confirm network reachability and `GET /health`. | Status code, response summary, timestamp, host. |
| CR-002 | Store and retrieve an L2 fact in a consumer-specific session. | Request payload without secrets, response, `fact_id`. |
| CR-003 | Verify L2 session isolation by retrieving from a different session. | Response showing no accidental cross-session leakage. |
| CR-004 | Run L3 assimilate with realistic domain text. | Status code, `episode_id` or full sanitized error. |
| CR-005 | Run L3 query for the assimilated content. | Status code, `results`, `provenance`, trace id if available. |
| CR-006 | Run L4 finalize with a short representative artifact. | Status code and `knowledge_id`. |
| CR-007 | Execute at least one negative scenario. | Expected `400`, `501`, or `502` classification and whether handling is acceptable. |
| CR-008 | Map the consumer's own requirements to observed YAAM behavior. | Requirement coverage table with evidence. |
| CR-009 | Assess MCP readiness from the consumer perspective. | MCP discovery/read/prompt evidence and default write-denial evidence. |

Consumers may add domain-specific scenarios beyond this list. Those scenarios are especially useful
when they exercise requirements not covered by the generic smoke checks.

## 6. Negative Scenarios

Run at least one of the following:

- L2 store with `action: "store"` and missing or empty `content`; expected: HTTP `400`.
- L1 call if the consumer requires server-side turn storage; expected may be HTTP `201` if enabled
  or HTTP `501` if L1 is not configured for the current runtime.
- L3 request during provider or embedding failure; expected: HTTP `502`, classified as retryable
  or provider-side depending on the observed detail.

Do not intentionally load-test or exceed reasonable provider limits during this readiness wave.

## 7. Requirement Coverage Classification

For every consumer-owned requirement, use exactly one status:

| Status | Meaning |
| --- | --- |
| `implemented` | The requirement is satisfied by observed YAAM behavior. |
| `partially implemented` | The requirement is usable only with limitations or workaround. |
| `missing` | The required capability is not available through the tested interface. |
| `unclear` | The test did not produce enough evidence to classify the requirement. |

Every non-`implemented` row should include a finding in the report.

## 8. Report Location

If the test is executed on the MacBook checkout, write the report directly under:

```text
/Users/max/Documents/code/mas-memory-layer/docs/integrations/consumer-readiness-2026-05-28/reports/
```

Use this naming convention:

```text
YYYY-MM-DD-<consumer-name>-readiness-report.md
```

If the test is executed from `skz-dev-lv` or another host, save the report locally in the consumer
project and provide the path or artifact so the maintainers can transfer it into the YAAM repository.

## 9. Report Template

```markdown
# <Consumer Name> YAAM Readiness Report

**Date:** YYYY-MM-DD
**Consumer system:** <name>
**Tester/runtime:** <host, branch, commit if available>
**YAAM endpoint:** http://192.168.107.187:8002
**Overall verdict:** pass | pass-with-findings | blocked | fail

## Summary

<One paragraph stating whether the consumer can integrate with YAAM now, with the most important
blockers or limitations.>

## Environment

| Field | Value |
| --- | --- |
| Consumer host |  |
| Consumer repository/path |  |
| Consumer commit/branch |  |
| YAAM endpoint |  |
| Test timestamp and timezone |  |
| Trace ids used |  |

## Documentation Used

| Document | Path or copied reference | Notes |
| --- | --- | --- |
| TRA Integration Guide v2 |  |  |
| YAAM v2 Connection Policy |  |  |
| MCP Readiness Spec |  |  |

## Executed Checks

| Check ID | Result | Evidence | Notes |
| --- | --- | --- | --- |
| CR-001 | pass/fail/blocked |  |  |
| CR-002 | pass/fail/blocked |  |  |
| CR-003 | pass/fail/blocked |  |  |
| CR-004 | pass/fail/blocked |  |  |
| CR-005 | pass/fail/blocked |  |  |
| CR-006 | pass/fail/blocked |  |  |
| CR-007 | pass/fail/blocked |  |  |
| CR-008 | pass/fail/blocked |  |  |
| CR-009 | pass/fail/blocked |  |  |

## Requirement Coverage

| Requirement ID | Requirement | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
|  |  | implemented/partially implemented/missing/unclear |  |  |

## Findings

| Finding ID | Priority | Category | Title | Evidence | Suggested action |
| --- | --- | --- | --- | --- | --- |
|  | P0/P1/P2/P3 | contract/deployment/documentation/MCP/observability/performance/security/data-correctness/UX |  |  |  |

## Blockers

<List any issue that prevents meaningful integration. If none, write "None".>

## Recommended Next Actions

<Prioritised actions for YAAM maintainers and/or the consumer team.>

## Raw Evidence

<Include sanitized request/response snippets, logs, trace ids, artifact paths, and command outputs.
Do not include secrets, tokens, API keys, passwords, or full `.env` contents.>
```

## 10. Evidence and Secret Handling

Reports must not include secrets, tokens, database passwords, provider keys, private `.env` content,
or unredacted authorization headers. Include enough request and response evidence to reproduce a
finding, but redact all sensitive values before submitting the report.
