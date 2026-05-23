# CIAR Regression Pack Report

Date: 2026-05-23
Status: Complete
Related plan: `docs/plan/2026-05-23-ciar-regression-pack-plan.md`

## Summary

Implemented Batch 7: a canonical local CIAR regression pack for fast
verification before CIAR policy, scoring, contradiction, and experiment-harness
changes.

The change is workflow-only. It does not modify CIAR scoring, promotion policy,
contradiction policy, storage adapters, runtime defaults, dependencies, live
provider behavior, or `.env` handling.

## Behavior Added

- Added `scripts/experiments/run_ciar_regression_pack.py`.
- Added `--list` mode to print commands without running them.
- Added `--skip-ruff` for pytest-only reruns after a separate ruff pass.
- Added script tests covering command listing, command order, skip mode, and
  failure propagation.
- Documented the pack in `scripts/README.md`.
- Recorded the pack as `CIAR-REG-1` in the CIAR coordination plan.

## Verification

Environment verification:

```text
Darwin MacBook-Pro.local 25.5.0 Darwin Kernel Version 25.5.0: Mon Apr 27 20:41:26 PDT 2026; root:xnu-12377.121.6~2/RELEASE_ARM64_T8132 arm64
MacBook-Pro.local
/Users/max/Documents/code/mas-memory-layer
/Users/max/Documents/code/mas-memory-layer/.venv/bin/python
```

Ruff:

```text
./.venv/bin/ruff check .
All checks passed!
```

Runner tests:

```text
./.venv/bin/pytest tests/scripts/test_ciar_regression_pack.py -v
6 passed in 0.02s
```

List mode:

```text
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py --list
```

Printed the expected venv check, ruff command, and focused CIAR pytest command.

Full regression pack:

```text
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
137 passed in 7.12s
```

## Residual Caveats

- The CIAR regression pack is a fast local CIAR gate, not a replacement for
  `./.venv/bin/pytest tests/ -v` after broader `src/` behavior changes.
- The pack intentionally excludes integration tests, `llm_real` tests, live
  OpenRouter/Phoenix/Redis/PostgreSQL checks, and dry-run artifact generation.
