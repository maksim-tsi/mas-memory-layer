# CIAR Regression Pack Plan

Date: 2026-05-23
Status: Implementation planned
Scope: CIAR local regression workflow and documentation

## Purpose

Create a canonical, fast CIAR regression pack so future CIAR batches have one
documented local verification command. The pack is a workflow gate for CIAR
policy/scoring/harness changes, not a replacement for the full repository test
suite when shared `src/` behavior changes.

## Scope

In scope:

- Add a lightweight script runner for the fixed CIAR regression command set.
- Document the command in `scripts/README.md`.
- Record the CIAR regression pack in the CIAR coordination plan.
- Add script-level tests for command ordering, list mode, skip mode, and
  failure propagation.

Out of scope:

- CIAR scoring changes.
- Promotion or contradiction policy changes.
- Storage adapter changes.
- Dependency changes.
- Live provider, Phoenix, Redis, PostgreSQL, or `.env` behavior.

## Planned Command Set

Default command:

```bash
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
```

The runner will:

1. Verify it is running from the repository root.
2. Verify `./.venv/bin/python`.
3. Run `./.venv/bin/ruff check .`.
4. Run the fixed CIAR pytest pack:

```bash
./.venv/bin/pytest \
  tests/memory/test_ciar_scorer.py \
  tests/agents/tools/test_ciar_tools.py \
  tests/api/test_v2_router_ciar.py \
  tests/memory/test_working_memory_tier.py \
  tests/memory/engines/test_promotion_engine.py \
  tests/memory/test_contradiction_policy.py \
  tests/memory/test_unified_memory_system.py \
  tests/scripts/test_ciar_challenge_experiment.py \
  tests/scripts/test_ciar_challenge_with_env.py \
  tests/scripts/test_ciar_policy_analysis.py \
  -v
```

Supported options:

- `--list`: print commands without executing them.
- `--skip-ruff`: run only the pytest pack after a separate ruff pass.

## Acceptance Criteria

- `--list` prints the exact ruff and pytest commands without executing
  subprocesses.
- Default mode runs ruff before pytest.
- `--skip-ruff` runs pytest only.
- A non-zero ruff or pytest exit code is returned and stops later commands.
- The pack does not invoke integration markers, `llm_real`, live providers,
  `.env` loading, or dry-run artifact generation.

## Verification Commands

```bash
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/scripts/test_ciar_regression_pack.py -v
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py --list
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
```
