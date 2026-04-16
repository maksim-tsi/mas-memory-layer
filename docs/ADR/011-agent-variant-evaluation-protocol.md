# ADR-011: Agent Variant Evaluation Protocol (GoodAI Benchmark via API Wall)

**Status:** Accepted  
**Date:** February 21, 2026  
**Related:** ADR-009, ADR-010, ADR-001; `docs/specs/spec-mechanism-maturity-and-freeze.md`

## 1. Context

YAAM is evaluated using the GoodAI LTM Benchmark under an “API Wall” constraint (ADR-009). The
benchmark runner must observe the system as a black box over HTTP and must not import YAAM internal
modules or access storage backends directly.

As YAAM evolves, we expect multiple agent implementations to coexist (e.g., minimal skills wiring
versus tool-gated skills execution). For academic validity and engineering reliability, benchmark
results must be comparable across variants with minimal ambiguity regarding what changed.

The key risks to avoid are:

- **Configuration drift:** results depend on implicit flags rather than a stable variant identity.
- **State contamination:** multiple runs share Redis/Postgres namespaces and influence each other.
- **Uncontrolled degrees of freedom:** “variants” differ in multiple untracked dimensions.

## 2. Decision

### 2.1 Use explicit, versioned agent variants for evaluation

We represent evaluation conditions as **explicit agent variants** (versioned implementations), not
as a single agent whose behavior changes via ad-hoc configuration flags.

Each variant MUST expose a stable identifier used in:

- `agent_id` (returned by the agent’s health check),
- session prefixing for storage isolation, and
- benchmark reporting.

### 2.2 Select variants by service instance (URL/port), without changing the HTTP API

The benchmark runner selects a variant by targeting a specific API Wall URL (e.g., different port
or host). The HTTP API surface remains unchanged.

This preserves ADR-009 (evaluation via HTTP) while enabling rigorous A/B comparisons.

### 2.3 Enforce state isolation using variant-qualified session prefixes

Every service instance uses a session prefix of the form:

`<agent_type>__<agent_variant>`

This prefix is applied to all session IDs, ensuring that Redis/Postgres namespaces are isolated
between variants even when they share the same backing services.

### 2.4 Adopt canonical naming and runner entrypoints

To minimize ambiguity across repeated runs, we adopt:

- **Variant slug format:** lowercase, hyphen-separated, versioned (e.g., `baseline`, `v1-min-skillwiring`,
  `v2-adv-toolgated`).
- **Agent ID format:** `mas-<agent_type>__<agent_variant>` (exposed via `/health`).
- **Benchmark selection mechanism:** choose the variant by setting `AGENT_URL` to the corresponding
  API Wall instance (URL/port), without changing the HTTP API.
- **Benchmark run naming:** include `<agent_type>__<agent_variant>` in the GoodAI `--run-name` to ensure
  filesystem artifacts are variant-scoped.

## 3. Consequences

### Positive

- **Academic clarity:** variant A vs variant B comparisons are interpretable and reproducible.
- **Engineering safety:** isolates state and reduces accidental cross-run interference.
- **Operational simplicity:** benchmark runner uses only `AGENT_URL` changes; no API changes.

### Negative

- **More artifacts:** multiple service instances and multiple reports must be tracked.
- **More code surface:** variant implementations can increase code duplication if not disciplined.

### Neutral

- Shared infrastructure (Redis/Postgres/LLM providers) remains a dependency; runs must record
  environment details and rate limiting to support reproducibility.

## 4. Implementation Plan (High Level)

1. Implement minimal variant plumbing: `MAS_AGENT_TYPE`, `MAS_AGENT_VARIANT`, and variant-qualified
   session prefixes.
2. Introduce a minimal skills wiring variant (skill body injection + toolset gating preparation).
3. Introduce an advanced variant (tool-gated execution with explicit tool calling) and re-run the
   same benchmark manifest under identical non-variant conditions.
4. Publish comparative reports using a standard report template.

## 5. Alternatives Considered

### A) Single agent with a `mode=minimal|advanced` configuration flag

**Pros:** fewer classes; easier initial implementation.  
**Cons:** higher risk of configuration drift and unclear experimental boundaries.  
**Why rejected:** insufficient academic clarity for controlled comparisons.
