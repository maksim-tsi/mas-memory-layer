# L3 Embedding Size Precedence + v2 E2E Qdrant Gate Report

Date: 2026-05-23
Status: Complete
Related plan: `docs/plan/2026-05-23-l3-embedding-e2e-qdrant-fix-plan.md`

## Summary

Fixed the default full-suite blockers by separating deterministic unit-tier
configuration from live E2E service access.

- Explicit `EpisodicMemoryTier(config={"vector_size": ...})` now wins over
  ambient `EMBEDDING_DIMENSIONS`.
- v2 semantic gateway E2E tests are now integration-gated and skipped in the
  default suite.
- Live v2 E2E remains runnable explicitly with `--run-integration`.

No storage adapters, DB schemas, provider routing defaults, dependencies, or
`.env` behavior were changed.

## Changed Behavior

- L3 vector-size precedence is now:
  1. explicit `config["vector_size"]`;
  2. numeric `EMBEDDING_DIMENSIONS`;
  3. adapter/default vector size.
- The L3 tier README records this precedence.
- `tests/v2-api-e2e/test_semantic_gateway_e2e.py` is marked as
  `pytest.mark.integration`.
- Explicit live v2 E2E runs preflight the `test_v2` Qdrant collection dimension
  and fail clearly if it differs from the requested embedding dimension.
- Tests do not delete or recreate Qdrant collections.

## Verification

Environment:

```bash
uname -a
hostname
pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
```

Local checks:

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest tests/memory/test_episodic_memory_tier.py -v
./.venv/bin/pytest tests/v2-api-e2e/test_semantic_gateway_e2e.py -v
./.venv/bin/pytest tests/ -v
```

Results:

- Ruff: passed
- L3 episodic tier tests: `22 passed in 0.87s`
- v2 E2E default gate: `4 skipped in 5.07s`
- Full default suite: `659 passed, 139 skipped in 370.40s`

Live checks:

```bash
./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env --service qdrant --json
./.venv/bin/pytest --run-integration tests/v2-api-e2e/test_semantic_gateway_e2e.py -v
```

Results:

- Qdrant diagnostic: passed; sanitized endpoint summary showed TCP and health
  checks OK.
- v2 semantic gateway live E2E: `4 passed in 91.64s`

## Notes

The previous full-suite blockers are resolved:

- The 1536 vs 4096 L3 unit-test mismatch is fixed by explicit config
  precedence.
- The sandboxed Qdrant errors are fixed by integration-gating live v2 E2E
  tests.

The existing YAAM Qdrant collections were already dimension-aligned for this
path: `episodes_v2=4096` and `test_v2=4096`.
