# RFC: YAAM Multi-Customer Runtime Isolation Path

**Date:** 2026-06-03
**Status:** Proposed staged architecture path
**Decision:** Treat simultaneous multi-customer YAAM as future work. Current
supported shared-endpoint model remains sequential project windows or separate
YAAM instances.

## Current State

YAAM already supports customer-specific runtime initialization:

- `YAAM_PROJECT_ID` selects the runtime project namespace.
- L3 Qdrant and L4 Typesense names derive from the project id.
- Redis namespace helpers include project-scoped keys.
- service-layer `ScopeEnvelope` includes `tenant_id`.
- MCP domain packs auto-enable based on `YAAM_PROJECT_ID`.
- Phoenix project names can be set per customer window.

The 2026-06-03 live validation confirmed:

- Skill Factory and Cognitive Sandwich domain packs appear under their matching
  project ids;
- project-derived L3/L4 collection names are selected correctly;
- the same client `session_id` did not expose a Skill Factory L2 fact through
  a Cognitive Sandwich project window.

This is project-window isolation evidence, not complete multi-tenant evidence.

## Staged Path

### Stage 1: Sequential Project Windows

Use one shared endpoint for one customer project at a time.

This is the current recommended model because it:

- keeps Phoenix evidence clear;
- keeps MCP domain-pack discovery unambiguous;
- reduces accidental mixed project data;
- requires no storage or public-contract changes.

### Stage 2: Parallel Instance-Per-Customer

Run one YAAM interface instance per customer:

- separate REST port;
- separate MCP port;
- separate `YAAM_PROJECT_ID`;
- separate `PHOENIX_PROJECT_NAME`;
- `YAAM_MCP_DOMAIN_PACKS=auto`;
- shared backend DBMS only when namespaces are verified.

Experimental acceptance:

- two customer instances can write and read concurrently;
- same client `session_id` cannot cross project boundaries;
- MCP discovery shows only each customer domain pack;
- Phoenix spans are attributable by project;
- no unexpected backend health degradation;
- operator runbook is clear enough for repeat use.

### Stage 3: Shared-Runtime Multi-Tenant YAAM

Design only after Stage 2 evidence passes.

Open design decisions:

- whether `tenant_id` becomes a mandatory hard isolation key;
- how tenant authorization maps to MCP tools/resources and REST routes;
- whether storage uses separate physical collections or mandatory tenant
  filters;
- how deletion, retention, audit export, and quotas work per tenant;
- how Phoenix traces separate tenant evidence without leaking metadata;
- how benchmark leakage guards interact with tenant and visibility scope.

## Required Experiments

Before shared-runtime multi-tenancy can be claimed, run isolation tests across:

- REST L2/L3/L4 reads and writes;
- MCP resources, prompts, tools, and write-denial behavior;
- Skill Factory and Cognitive Sandwich domain views;
- CIAR artifacts and lifetime decision outputs;
- Evidence Table outputs;
- Phoenix traces;
- benchmark leakage guards;
- deletion and retention once those policies are specified.

## Non-Goals

This RFC does not approve:

- exposing a shared multi-tenant endpoint now;
- changing storage schemas;
- changing public REST/MCP contracts;
- treating `tenant_id` as hard isolation before implementation and tests prove
  it;
- weakening sequential project-window support.

## Related Requirements

- `YAAM-REQ-0001`: interface separation.
- `YAAM-REQ-0009`: provenance.
- `YAAM-REQ-0010`: session/task/tenant/run scoping.
- `YAAM-REQ-0011` to `YAAM-REQ-0013`: MCP safety and redaction.
- `YAAM-REQ-0014`: Phoenix observability.
- `YAAM-REQ-0018`: degraded read semantics.
- `YAAM-REQ-0022` to `YAAM-REQ-0025`: domain-specific memory views.
- `YAAM-REQ-0036`: benchmark leakage guards.
- `YAAM-REQ-0038`: trace and artifact correlation metadata.
