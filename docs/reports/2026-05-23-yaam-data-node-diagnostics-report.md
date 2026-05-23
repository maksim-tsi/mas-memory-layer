# YAAM Data-Node Diagnostics + CIAR Setup Failure Observability Report

Date: 2026-05-23
Status: Complete locally
Related plan: `docs/plan/2026-05-23-yaam-data-node-diagnostics-plan.md`

## Summary

Implemented a read-only YAAM data-node diagnostic script and improved CIAR live
setup failure artifacts. The batch stays in scripts, tests, and docs; it does
not change CIAR scoring, promotion policy, contradiction policy, storage
adapters, DB schemas, dependencies, or runtime defaults.

The diagnostic script verifies local `.env` service targets without printing
secret values. The CIAR harness now records live setup phases and writes
`run_error.json` when setup fails before policy artifacts are usable.

## Changed Behavior

- Added `scripts/debug/check_yaam_data_node.py`.
  - Parses `.env` without shell expansion.
  - Reports only sanitized endpoint metadata: scheme, host, port, and
    path/user/password presence.
  - Checks TCP reachability for Redis, PostgreSQL, Phoenix, Qdrant, Neo4j, and
    Typesense.
  - Performs cheap protocol checks for Redis `PING`, Phoenix UI GET, Qdrant
    `/healthz`, and Typesense `/health`.
  - Supports `--json` and repeated `--service` filters.

- Updated CIAR live `setup_runtime` artifacts.
  - `run_manifest.json` now records `runtime_setup` before L1/L2
    initialization.
  - Setup phases include Redis adapter creation, L1 initialization start/ok, and
    L2 initialization start/ok.
  - Service endpoints are summarized without exposing credentials.
  - Setup failures write `run_error.json`, classify the run as `incomplete`,
    and preserve existing non-zero failure behavior.

- Updated script documentation in `scripts/README.md` and
  `scripts/debug/README.md`.

## Data-Node Findings

Pre-implementation diagnostics confirmed:

- SSH alias `skz-data-local` resolves to host `skz-data-lv`.
- Docker containers were running for Redis, PostgreSQL, Phoenix, Qdrant, Neo4j,
  and Typesense.
- Required ports were listening on `0.0.0.0`.
- Redis was healthy and responded to local and remote `PING`.
- PostgreSQL, Phoenix, Qdrant, and Typesense responded to read-only health
  checks.

Post-implementation local `.env` diagnostic result:

```text
overall_ok=true
redis: tcp ok, protocol PONG
postgres: tcp ok
phoenix: tcp ok, HTTP 200
qdrant: tcp ok, HTTP 200
neo4j: tcp ok
typesense: tcp ok, HTTP 200
```

## Verification

Passed:

```bash
uname -a && hostname && pwd
test -d .venv
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/scripts/test_check_yaam_data_node.py tests/scripts/test_ciar_challenge_experiment.py tests/scripts/test_ciar_challenge_with_env.py -v
./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env --json
./.venv/bin/python scripts/experiments/run_ciar_regression_pack.py
```

Results:

- Targeted tests: `29 passed in 64.05s`
- CIAR regression pack: `143 passed in 181.75s`
- Data-node diagnostic: all selected default services passed

## Recommendation

Before the next live CIAR checkpoint, run:

```bash
./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env --json
```

If the diagnostic remains green, rerun one replacement live checkpoint run
instead of repeating the full three-run matrix immediately. If setup fails
again, inspect `run_error.json` and `runtime_setup` in `run_manifest.json` to
identify whether the failure is Redis connect, L1 initialization, L2
initialization, or a later harness phase.
