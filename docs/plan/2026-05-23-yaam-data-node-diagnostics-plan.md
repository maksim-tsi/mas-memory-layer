# YAAM Data-Node Diagnostics + CIAR Setup Failure Observability Plan

Date: 2026-05-23
Status: Planned

## Purpose

Add a small operational diagnostics batch that separates three failure classes:
bad local `.env` service targeting, unavailable YAAM data-node services, and
failures inside CIAR live `setup_runtime`.

The batch stays in scripts, tests, and docs. It must not change CIAR scoring,
promotion policy, contradiction policy, storage adapters, DB schemas,
dependencies, or runtime defaults.

## Scope

- Add a read-only YAAM data-node diagnostic script for local `.env` targets.
- Improve CIAR live setup artifacts so setup failures leave actionable
  `run_manifest.json` and `run_error.json` evidence.
- Document the workflow and current findings.

Out of scope:

- SSH/Docker automation inside the committed diagnostic script.
- Storage adapter mechanism changes.
- Live LLM calls.
- Data migrations, cleanup, or service mutation.

## Acceptance Criteria

- A developer can run one command to verify local `.env` service endpoints
  without exposing secret values.
- CIAR setup failures record the failed setup phase, error type, sanitized error
  message, and `incomplete` operational classification.
- Redis timeout symptoms can be distinguished from wrong host, closed port,
  provider health failure, and Phoenix reachability failure.
- Existing CIAR dry regression behavior remains unchanged.

## Verification Commands

```bash
uname -a && hostname && pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/scripts/test_check_yaam_data_node.py tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_challenge_with_env.py -v
./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env --json
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
```
