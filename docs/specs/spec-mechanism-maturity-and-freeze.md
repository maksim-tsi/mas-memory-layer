# Specification: Mechanism (Connector/Adapter) Maturity & Freeze

**Status:** Draft  
**Date:** February 18, 2026  
**Scope:** YAAM mechanism layer (`src/storage/`)  
**Audience:** Maintainers, coding assistants (Codex/Copilot/Claude Code/Gemini CLI), skill authors  

## 1. Context

YAAM is developed in an agent-first workflow where coding assistants can produce high throughput but
also amplify architectural drift if boundaries are not explicit and mechanically enforced.

This specification defines:

1. A **public contract** for YAAM connectors/adapters (“Mechanism”), and
2. A **maturity checklist** and required evidence for freezing that mechanism so that iteration
   happens primarily in higher layers (“Policy”: skills, prompts, orchestration, benchmark harness).

The GoodAI benchmark is used as a feedback mechanism for overall system behavior and reliability.
It is **not** the target of prompt overfitting (“train-on-test”).

## 2. Definitions

### 2.1 Mechanism vs Policy

- **Mechanism:** stable, low-level capabilities for data access and durability (DB adapters and
  their contracts). In YAAM, the primary mechanism layer is `src/storage/`.
- **Policy:** skill instructions, prompts, agent orchestration, and evaluation harness logic that
  decides *how* to use the mechanism for a task.

### 2.2 “Frozen-by-default”

“Frozen-by-default” means changes to the mechanism layer are discouraged and require explicit
authorization and change control. It does **not** mean “never change”; it means changes must be
rare, intentional, and reviewed against this specification.

## 3. Connector/Adapter Contract v1 (Public API)

### 3.1 Contract Scope

This contract is the public, stable interface for all YAAM storage adapters under `src/storage/`.
It is intentionally aligned to the existing `StorageAdapter` abstract base class.

**Primary source:** `src/storage/base.py` (interface and exception hierarchy).

### 3.2 Public Methods (Required)

All concrete adapters MUST implement:

- `connect() -> None`  
  Establish connectivity and initialize any pools/resources. MUST set `is_connected=True` on success.

- `disconnect() -> None`  
  Release resources. MUST be safe to call multiple times (idempotent).

- `store(data: dict[str, Any]) -> str`  
  Persist one item. Returns a backend-specific identifier.

- `retrieve(id: str) -> dict[str, Any] | None`  
  Read by identifier. Returns `None` if not found.

- `search(query: dict[str, Any]) -> list[dict[str, Any]]`  
  Query by parameters. MUST accept a **dictionary query pattern** (no required keyword-args API).

- `delete(id: str) -> bool`  
  Delete by identifier. Returns `False` if not found.

All adapters SHOULD implement or inherit (and keep behavior compatible):

- `store_batch(items: list[dict[str, Any]]) -> list[str]`
- `retrieve_batch(ids: list[str]) -> dict[str, dict[str, Any] | None]`
- `delete_batch(ids: list[str]) -> dict[str, bool]`
- `health_check() -> dict[str, Any]` (override recommended)
- `get_metrics() -> dict[str, Any]`

### 3.3 Conceptual “connect/query/store” Mapping (For Skills)

For skill authors, the contract can be referenced using the simplified verbs:

- **connect:** `connect()`, `disconnect()`, `health_check()`
- **store:** `store()`, `store_batch()`
- **query:** `retrieve()`, `search()`, `retrieve_batch()`
- **delete:** `delete()`, `delete_batch()`

Skill documentation SHOULD speak in these conceptual verbs, while tool implementations remain
aligned with the concrete adapter API above.

### 3.4 Error Model (Required)

Adapters MUST raise exceptions from the shared hierarchy in `src/storage/base.py`:

- `StorageConnectionError`: connectivity/pool failures
- `StorageTimeoutError`: connection/query/lock timeouts
- `StorageQueryError`: invalid queries or backend execution failures
- `StorageDataError`: validation/integrity errors (missing fields, wrong types, constraints)
- `StorageNotFoundError`: optional (only when semantically preferable to returning `None`/`False`)

**Requirement:** errors must be:
- deterministic (same failure mode ⇒ same exception class),
- informative (include operation + relevant identifiers),
- safe (must not leak secrets).

### 3.5 Timeouts and Retries (Required)

Adapters MUST provide:

- **Configurable timeouts** for connect and operations (backend-appropriate).
- **Bounded retries** for transient failures (network blips, timeouts), with sane defaults.
- A clear rule for which failures are retried vs not retried (e.g., data validation errors are not retried).

Evidence for timeouts/retries MUST include tests or deterministic simulations (see §4).

### 3.6 Observability (Required)

Adapters MUST be observable by default:

- Use adapter metrics (`get_metrics()`) as the primary mechanism-level telemetry surface.
- Log in a structured, low-noise way (operation name, latency, key identifiers such as `session_id`
  when applicable).

### 3.7 Health Checks (Required)

Adapters MUST provide a meaningful `health_check()` implementation (override the base default where
necessary) that verifies:

- connectivity,
- responsiveness (basic request),
- and backend-specific readiness (e.g., collection existence for vector/search stores).

### 3.8 Dependency Direction (Required)

Mechanism code in `src/storage/` MUST NOT depend on policy layers, including:

- `src/agents/`
- any skill/prompt packages (current or future)
- evaluation harness logic beyond minimal boundary interfaces

Mechanism MAY depend on:

- standard library,
- third-party SDKs for the backend,
- shared infrastructure modules intended for cross-cutting concerns (metrics, logging utilities),
  provided they do not import policy.

This rule MUST be mechanically enforced (see §4).

## 4. Maturity Criteria Checklist (Freeze Readiness)

The checklist below defines the “Definition of Done” for freezing adapters.

| Category | Requirement | Evidence Required | Mechanical Enforcement |
|---|---|---|---|
| Public API stability | Contract v1 methods exist and are used consistently | Interface references in `src/storage/base.py`; adapter docs; no breaking signature drift | Type checking + contract tests |
| Error model | Exceptions map to `Storage*Error` hierarchy; no ambiguous error types | Unit tests that assert exception class per failure mode | Unit tests |
| Timeouts & retries | Timeouts configurable; retries bounded; non-retriable failures documented | Tests for timeout behavior; tests for retry caps | Unit tests (with mocks) |
| Happy path correctness | Core operations succeed with realistic inputs | Adapter-specific tests (store/retrieve/search/delete) | Integration/unit tests |
| Failure correctness | Connection/query/data/timeout failures handled and typed | Tests for each major failure category | Unit tests |
| Observability | Metrics emitted for core operations; logs include operation context | Metrics snapshots in tests; logging assertions where practical | Unit tests / smoke checks |
| Health checks | `health_check()` is meaningful and stable | Health check tests per adapter | Unit tests / smoke tests |
| Dependency direction | No `src/storage/` imports from policy layers | Static import scan + structural test | Structural test |
| Documentation | Minimal adapter contract docs exist; config keys described | Spec references + adapter docstrings | Lint + review |

## 5. Freeze Policy (Post-Maturity Change Control)

Once an adapter is considered mature and the mechanism layer is frozen-by-default:

1. **Breaking changes require an ADR** and a contract version update (e.g., Contract v2).
2. **Non-breaking changes** (bug fixes, performance improvements) must:
   - preserve contract semantics,
   - include regression tests,
   - avoid introducing policy dependencies.
3. **Dependency changes** (adding/updating SDKs) require explicit user authorization and must be
   executed via Poetry workflows (never ad-hoc installs).

## 6. Implementation Notes (How this spec is applied)

This spec is intended to be referenced by:

- An ADR that formally declares the freeze and the dependency-direction constraints.
- A plan that:
  - evaluates current adapter maturity against the checklist,
  - creates missing evidence (tests, health checks, structural enforcement),
  - and only then activates “freeze-by-default” gates.

The specification is intentionally a stable contract. If the repository structure changes
(e.g., introduction of a `skills/` directory), the dependency-direction constraints must be updated
here first, then enforced mechanically.
