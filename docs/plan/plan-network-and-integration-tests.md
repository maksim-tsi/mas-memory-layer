# Plan: Network and Integration Test Execution (Offline-by-Default)

**Status:** Draft  
**Date:** February 19, 2026  
**Scope:** `tests/` integration tests and real-provider tests  
**Related:** `docs/ADR/010-mechanism-policy-split-and-skills-v1.md`; `docs/specs/spec-mechanism-maturity-and-freeze.md`

## 1. Context

The repository contains a substantial set of integration tests that exercise:

1. External storage services (Redis, PostgreSQL, Qdrant, Neo4j, Typesense), and
2. Real model-provider APIs (e.g., Gemini).

In constrained execution environments (e.g., agent sandboxes without network access, or local
workstations without access to the internal service cluster), these tests fail due to connection
errors rather than mechanism defects. This increases iteration friction for policy-layer work.

Accordingly, development-time harness behavior must support an **offline-by-default** mode that:

- keeps unit and mocked tests executable locally, and
- explicitly gates networked tests behind opt-in flags.

## 2. Observed Failure Modes (Representative)

The dominant failures are network connectivity issues, including:

- DNS resolution failures for provider endpoints (e.g., `generativelanguage.googleapis.com`).
- TCP connection failures to storage backends when the configured endpoints are not reachable.
- Sandbox-level socket restrictions (e.g., “Operation not permitted”) when connecting to localhost.

These failure modes are consistent with environment constraints and should not be treated as
evidence of mechanism-layer regressions.

## 3. Local-Only Default Policy

Default execution of:

```bash
./.venv/bin/pytest tests/ -v
```

MUST:

- pass without requiring any external services, and
- skip tests marked as `integration`, `slow`, or `llm_real` unless explicitly enabled.

## 4. Opt-In Execution for Networked Environments

### 4.1 Integration tests (external storage services)

To run integration tests, execute:

```bash
./.venv/bin/pytest tests/ -v --run-integration
```

Prerequisites (environment-dependent):

- Reachability of the configured service endpoints.
- Correct environment variables for service URLs and credentials.

Common variables referenced by tests include:

- `REDIS_URL`
- `POSTGRES_URL`
- `QDRANT_URL`
- `NEO4J_BOLT`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `TYPESENSE_URL`, `TYPESENSE_API_KEY`

Note: `tests/conftest.py` loads `.env` with `override=True`. In networked CI or developer machines,
ensure that `.env` (or process environment) is aligned with the intended target environment.

### 4.2 Real provider tests (model endpoints)

To run real-provider tests, execute:

```bash
./.venv/bin/pytest tests/ -v --run-slow
```

Prerequisites include provider API keys (e.g., `GOOGLE_API_KEY`) and Internet connectivity.

## 5. Follow-Up Debugging Tasks (For Network-Enabled Maintainers)

1. Validate that the service endpoints referenced by `.env` are routable from the execution host.
2. Run the full suite with `--run-integration` and triage failures by backend:
   - `tests/storage/test_redis_adapter.py`
   - `tests/storage/test_postgres_adapter.py`
   - `tests/storage/test_qdrant_adapter.py`
   - `tests/storage/test_neo4j_adapter.py`
   - `tests/storage/test_typesense_adapter.py`
   - `tests/test_connectivity.py` and `tests/integration/`
3. Run real-provider tests with `--run-slow` and confirm:
   - credential provisioning,
   - deterministic timeouts and retry caps,
   - non-leakage of secrets in logs and exceptions.
4. If persistent failures occur, classify whether remediation belongs to:
   - environment provisioning (service availability, routing, DNS),
   - policy-layer test harness (marker coverage, gating rules), or
   - mechanism-layer adapters (contract or error-model defects), per `docs/specs/spec-mechanism-maturity-and-freeze.md`.

## 6. Suggested Enhancements (Optional)

If maintainers observe recurring accidental network usage during “local-only” runs, consider:

- conditioning `.env` loading in `tests/conftest.py` on `--run-integration` / `--run-slow`, and/or
- introducing a dedicated marker (e.g., `network`) to separate LAN services from public provider APIs.

These enhancements should be evaluated against the repository harness objectives in ADR-010 and
implemented with minimal drift risk.
