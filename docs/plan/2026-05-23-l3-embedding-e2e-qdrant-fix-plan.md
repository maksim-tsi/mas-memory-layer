# L3 Embedding Size Precedence + v2 E2E Qdrant Gate Plan

Date: 2026-05-23
Status: Planned

## Purpose

Fix the remaining default full-suite blockers after CIAR work:

- L3 unit tests should remain deterministic when they pass an explicit
  `EpisodicMemoryTier` vector size.
- Live v2 semantic gateway E2E tests should not run during the default test
  suite without explicit integration approval.

## Scope

This batch changes tier configuration precedence, unit/integration test gating,
and documentation only. It does not change storage adapters, database schemas,
provider routing defaults, dependencies, or `.env` behavior.

## Implementation

- Make explicit `config["vector_size"]` authoritative in
  `EpisodicMemoryTier`.
- Use `EMBEDDING_DIMENSIONS` only when no explicit tier vector size is supplied.
- Keep `_v2` collection suffixing unchanged.
- Mark `tests/v2-api-e2e/test_semantic_gateway_e2e.py` as integration-gated.
- Add a lightweight `test_v2` Qdrant dimension preflight for explicit live E2E
  runs without deleting or recreating collections.

## Acceptance Criteria

- Default `./.venv/bin/pytest tests/ -v` no longer fails on L3 embedding size
  mismatch or sandboxed v2 E2E Qdrant connection errors.
- Explicit config precedence is covered by tests.
- v2 semantic gateway E2E remains runnable with `--run-integration`.
- No Qdrant collection deletion/recreation is performed automatically.

## Verification Commands

```bash
uname -a
hostname
pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/memory/test_episodic_memory_tier.py -v
./.venv/bin/pytest tests/v2-api-e2e/test_semantic_gateway_e2e.py -v
./.venv/bin/pytest tests/ -v
./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env --service qdrant --json
./.venv/bin/pytest --run-integration tests/v2-api-e2e/test_semantic_gateway_e2e.py -v
```
