# Dev Branch MAS-Agent Clean Start Diagnostic Report

**Date:** April 21, 2026
**Branch:** `dev`
**Scope:** Non-destructive restart of `mas-agent` only using `docker-compose.interface.yml`
**Policy Constraints:** No source-code edits; no database reset; no volume deletion; no dependency changes.

## 1. Objective

Validate whether the MAS agent container can be started cleanly on the `dev` branch using the existing environment, and capture reproducible startup diagnostics for branch-to-branch comparison.

## 2. Procedure (Executed)

1. Capture branch and working-tree baseline.
2. Capture pre-restart container state and recent logs.
3. Restart only `mas-agent` with `docker compose -f docker-compose.interface.yml up -d --no-deps mas-agent`.
4. Re-check runtime state and health endpoint on port 8080.
5. Collect post-restart logs and container exit metadata.
6. Compare `docker-compose.yml` and `docker-compose.interface.yml` rendered `mas-agent` environments.
7. Apply minimal compose-only parity fix to interface compose.
8. Re-run interface startup and health checks.

## 3. Command Evidence Summary

| Step | Command | Observed Result |
|---|---|---|
| 1 | `git branch --show-current` | `dev` |
| 2 | `git status --short` | clean working tree |
| 3 | `docker compose -f docker-compose.interface.yml ps -a` | `mas-agent` initially `Exited (3)` |
| 4 | `docker compose -f docker-compose.interface.yml logs --tail=80 mas-agent` | Startup traceback includes Neo4j unauthorized/authentication failure |
| 5 | `docker compose -f docker-compose.interface.yml up -d --no-deps mas-agent` | restart command succeeds; container recreated/started |
| 6 | `docker compose -f docker-compose.interface.yml ps` | transient `Up` state observed |
| 7 | `docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | grep mas-agent` | no running `mas-agent` entry |
| 8 | `curl -sS -m 10 -i http://localhost:8080/health` | connection failure (`curl: (7)`), endpoint unreachable |
| 9 | `docker compose -f docker-compose.interface.yml logs --tail=180 mas-agent` | repeated Neo4j auth failure signature |
| 10 | `docker inspect mas-memory-layer-mas-agent-1 --format '{{.State.ExitCode}} {{.State.Error}} {{.State.FinishedAt}}'` | exit code `3`, finished timestamp recorded |

## 4. Primary Failure Signature

The container fails during application startup with a Neo4j authentication error:

- `Neo.ClientError.Security.Unauthorized`
- message indicates client unauthorized due to authentication failure
- startup abort follows tier initialization failure

## 5. Default vs Interface Comparison

`docker compose config` showed that default compose provided additional `mas-agent` variables that were not present in interface compose during the failing run.

Missing from interface compose before fix:

1. `NEO4J_USER`
2. `NEO4J_PASSWORD`
3. `NEO4J_DATABASE`
4. `OPENROUTER_API_KEY`

This configuration drift explained why default compose started successfully while interface compose failed with Neo4j authentication errors.

## 6. Remediation Applied

A compose-only fix was applied in `docker-compose.interface.yml` to align interface `mas-agent` environment wiring with default compose.

Added keys:

1. `NEO4J_USER: ${NEO4J_USER:-neo4j}`
2. `NEO4J_PASSWORD: ${NEO4J_PASSWORD:-mas-password}`
3. `NEO4J_DATABASE: ${NEO4J_DATABASE:-neo4j}`
4. `OPENROUTER_API_KEY: ${OPENROUTER_API_KEY:-}`

No source-code files were modified.

## 7. Validation After Fix

Post-fix validation sequence:

1. `docker compose -f docker-compose.interface.yml up -d mas-agent`
2. `docker compose -f docker-compose.interface.yml ps`
3. `curl -sS -m 10 http://localhost:8080/health`

Observed result:

1. Container `mas-memory-layer-mas-agent-1` remains `Up`.
2. Port mappings active (`8080->8080`, `8002->8080`).
3. Health endpoint returns `HTTP 200`.

## 8. Outcome

The initial interface compose restart failed, but after environment parity remediation, interface compose became healthy and stable on `dev`.

Final verified state:

1. `mas-agent` running under `docker-compose.interface.yml`
2. `http://localhost:8080/health` reachable (`HTTP 200`)

## 9. Change Control Confirmation

No implementation code was modified during this diagnostic run. Changes were limited to compose configuration and documentation.

## 10. Comparison Checklist for Next Branch

For branch-to-branch comparison, capture the same fields and compare deltas:

1. Pre-restart container state (`ps -a`).
2. Startup log signature (first fatal exception class and message).
3. Health endpoint result on port 8080.
4. Container exit code and finish timestamp.
5. Whether restart remains transient (`Up` then immediate exit) or stable.
