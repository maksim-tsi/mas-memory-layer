# Phoenix Retriever Live Validation Report

**Date:** March 10, 2026  
**Status:** Implemented, live validation completed  
**Audience:** Maintainers, observability owners, benchmark operators  
**Phoenix Project:** `mlm-mas-dev-phoenix-retriever-live-20260310-200425`

**Operational Note:** This report records one dated live-validation run for the new retriever
instrumentation. For the repeatable procedure, use
`docs/runbooks/phoenix-experiment-reproducibility.md`.

## 1. Executive Summary

This report documents a live Phoenix validation run for the first retriever-instrumented request
path after the March 10 tracing implementation pass. The principal outcome is that the expected
trace hierarchy is now visible end to end through the API Wall: `yaam.api_wall.chat_completions`
contains `yaam.agent.run_turn`, which contains `yaam.workflow.retrieve`, which in turn contains a
retriever span (`yaam.retriever.l2`) for the evaluated request.

The validation also exposed an operational boundary in the current request path. The API-Wall
endpoint applies `skip_l1_write = true` by default when constructing request metadata. As a result,
this live run validated span reachability, parent-child nesting, session propagation, and query
attribute propagation, but it did not produce non-empty `retrieval.documents` payloads for the live
request because the route did not persist new retrievable content during the same session.

## 2. Runtime Baseline

The live baseline during this run was as follows:

1. Host: `skz-dev-lv`
2. Repository path: `/home/max/code/mas-memory-layer`
3. Phoenix deployment: standalone Docker container named `phoenix`
4. Phoenix image: `arizephoenix/phoenix:latest`
5. Phoenix HTTP endpoint: `http://localhost:6006`
6. Phoenix server header version: `12.14.2`
7. Repository `docker compose ps`: no running Phoenix service in the repository compose stack

These observations confirm that the experiment used the local standalone Phoenix service rather than
any repository-managed compose deployment.

## 3. Validation Procedure

The execution followed the repository runbook with one fresh project name:

1. Verified Phoenix reachability at `/`, `/docs`, and `/openapi.json`.
2. Started the API Wall with `PHOENIX_PROJECT_NAME=mlm-mas-dev-phoenix-retriever-live-20260310-200425`.
3. Sent a priming request in session `phoenix-retriever-20260310-200425` containing an operational
   lesson about customs-clearance delays.
4. Sent a retrieval-oriented follow-up request in the same session asking for similar past episodes
   and the reusable lesson.
5. Replayed one correlation request in the same session and captured the response metadata:
   - `yaam_trace_id = 4d2e28be4158acf972b13268cedaab07`
   - `yaam_span_id = 94a715aad4f8cc3e`
   - `client_session_id = phoenix-retriever-20260310-200425`
   - `yaam_session_id = full__baseline:phoenix-retriever-20260310-200425`
6. Queried `GET /v1/projects/{project_identifier}/spans?limit=500` from the local Phoenix API and
   filtered the response by the captured trace id.

## 4. Observed Spans

Phoenix returned four spans for the traced request:

1. `yaam.api_wall.chat_completions`
2. `yaam.agent.run_turn`
3. `yaam.workflow.retrieve`
4. `yaam.retriever.l2`

The observed parent chain was:

1. `yaam.api_wall.chat_completions` as the root span
2. `yaam.agent.run_turn` with parent `yaam.api_wall.chat_completions`
3. `yaam.workflow.retrieve` with parent `yaam.agent.run_turn`
4. `yaam.retriever.l2` with parent `yaam.workflow.retrieve`

This result demonstrates that the first retriever instrumentation pass is active in the live API-Wall
request path and that span nesting is coherent in Phoenix.

## 5. Attribute-Level Findings

The live Phoenix payload preserved the most important runtime-correlation fields:

1. `session.id` was present on `yaam.agent.run_turn`, `yaam.workflow.retrieve`, and
   `yaam.retriever.l2` as `full__baseline:phoenix-retriever-20260310-200425`.
2. `input.value` was present on the same spans and matched the retrieval-oriented prompt.
3. `output.value` was present on `yaam.agent.run_turn`.
4. `retrieval.documents` was present on `yaam.retriever.l2`, but its value for this trace was the
   serialized empty payload `[]`.

The live request metadata also reported:

1. `recent_turns_count = 5`
2. `working_facts_count = 0`
3. `episodic_chunks_count = 0`
4. `semantic_knowledge_count = 0`

These counters are consistent with a session that exercised retrieval logic but did not have stored
L2, L3, or L4 evidence available for return.

## 6. Phoenix API Representation Notes

The Phoenix `GET /v1/projects/{project_identifier}/spans` response on server version `12.14.2`
showed two behavior details that are operationally relevant for future evidence collection:

1. The response preserved the span names, context ids, parent ids, and YAAM attributes needed for
   validation.
2. The payload did not expose `openinference.span.kind` in the returned span attributes for this
   trace, even though the local tracing helper sets span kind during emission.

For current repository validation, the practical implication is that span-name and attribute checks
through the raw spans endpoint are reliable, whereas semantic-kind validation may require either a
different Phoenix endpoint or acceptance that this server version does not surface that field in the
same representation.

## 7. Interpretation

The live evidence supports three conclusions.

First, the March 10 retriever instrumentation is functioning in the API-Wall path. The span tree is
present in Phoenix, and the live trace can be correlated from API response metadata to Phoenix span
records without ambiguity.

Second, the request path validated retriever-span structure rather than rich retrieval evidence. The
reason is not a tracing defect but a request-path policy decision: `src/server.py` currently applies
`skip_l1_write = true` by default before constructing the `RunTurnRequest`. This suppresses the
normal persistence path that would otherwise make a freshly primed API session more likely to yield
non-empty retrieval payloads on the immediately following request.

Third, the current live boundary remains consistent with the previously documented tool boundary.
This run validated request, agent, workflow, and retriever spans end to end. It did not validate
`yaam.tool.*` spans in a normal request because the request path still does not execute tier-tool
coroutines directly.

## 8. Recommended Next Actions

The next actions should be ordered as follows:

1. Preserve this report as the dated evidence artifact for the first retriever live-validation run.
2. Treat the API-Wall `skip_l1_write` default as the primary blocker to observing richer
   `retrieval.documents` payloads in a simple same-session live rerun.
3. Plan a narrow follow-on change if richer live retrieval evidence is required from the API-Wall
   route itself. That change should be reviewed separately because it affects runtime write policy,
   not only observability.
4. Plan the larger memory-agent tool-execution path as a separate follow-on task if `yaam.tool.*`
   spans must become visible in normal API-Wall traffic.

## 9. Reference Artifacts

- Runbook: [phoenix-experiment-reproducibility.md](../runbooks/phoenix-experiment-reproducibility.md)
- Span contract: [phoenix-span-contract.md](../specs/observability/phoenix-span-contract.md)
- Prior API-Wall report: [2026-03-09-phoenix-api-wall-observability-progress-report.md](2026-03-09-phoenix-api-wall-observability-progress-report.md)
- API Wall implementation: [src/server.py](../../src/server.py)
- Agent runtime: [src/agents/memory_agent.py](../../src/agents/memory_agent.py)
- Retriever runtime: [src/memory/unified_memory_system.py](../../src/memory/unified_memory_system.py)