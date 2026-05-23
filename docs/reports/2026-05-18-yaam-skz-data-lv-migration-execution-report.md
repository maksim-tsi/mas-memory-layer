# YAAM skz-data-lv Migration Execution Report

Date: 2026-05-18
Branch: `dev-tests`
Operator context: MacBook Pro active, `skz-data-lv` active, `skz-dev-lv` powered off

## Summary

YAAM was prepared and started on `skz-data-lv` (`skz-data-local`,
`192.168.107.187`) as a Docker Compose API Wall runtime. The MacBook remains
the primary development/control machine. The old `skz-dev-lv` host is currently
offline, so it should not be treated as an available rollback target until it is
powered back on and validated.

The API Wall is currently reachable at:

```text
http://192.168.107.187:8002
```

Use the IP address for consumers. `skz-data-local` is an SSH alias on the
MacBook, not a general DNS name for applications.

## Work Completed

- Added and pushed the shared resource guide:
  `docs/IAC/SHARED_SKZ_DATA_RESOURCES.md`.
- Added and pushed the migration plan:
  `docs/plan/2026-05-18-yaam-skz-data-lv-migration-plan.md`.
- Created `/home/maxim/code` on `skz-data-lv`.
- Cloned the YAAM repository to:
  `/home/maxim/code/yet-another-agents-memory`.
- Checked out `dev-tests` in the remote clone.
- Confirmed the remote clone tracks `origin/dev-tests`.
- Confirmed shared DBMS containers are running on `skz-data-lv`:
  PostgreSQL, Redis, Qdrant, Neo4j/DozerDB, Typesense, and Phoenix.
- The operator manually copied `.env` from `skz-dev-lv` to `skz-data-lv`.
  Secret contents were not read, printed, edited, or transferred by the agent.
- Built the YAAM Docker image on `skz-data-lv`.
- Started `mas-agent` through `docker-compose.interface.yml`.
- Restarted `mas-agent` with non-secret runtime endpoint overrides pointing to
  `192.168.107.187` after startup initially failed against old Redis endpoint
  `192.168.107.172:6379`.
- Added `docker-compose.skz-data.yml` as a committed runtime override for
  non-secret `skz-data-lv` service endpoints. This avoids relying on ad hoc
  shell overrides while preserving the `.env` secret boundary.

## Current Runtime State

`mas-agent` is running on `skz-data-lv` with host ports:

```text
8080 -> container 8080
8002 -> container 8080
```

Verified health checks:

```bash
ssh skz-data-local curl -fsS http://127.0.0.1:8002/health
curl -fsS http://192.168.107.187:8002/health
```

Both checks returned `status: ok`. The health response reported Redis,
PostgreSQL, L1 active context, L2 working memory, and the agent as healthy.

## Runtime Configuration

The successful runtime should be managed with both Compose files:

```bash
docker compose -f docker-compose.interface.yml -f docker-compose.skz-data.yml up -d --force-recreate mas-agent
```

`docker-compose.skz-data.yml` contains only non-secret endpoint overrides. It
does not contain database passwords, provider keys, or API keys. Secrets remain
in the untracked remote `.env`.

The copied remote `.env` may still contain stale `skz-dev-lv` endpoint values.
That is acceptable for now as long as the `skz-data` override file is used for
runtime. When the operator is back at a trusted workstation, the remote `.env`
can still be cleaned up manually to match the data-node endpoints:

```dotenv
REDIS_HOST=192.168.107.187
REDIS_URL=redis://192.168.107.187:6379/0
QDRANT_URL=http://192.168.107.187:6333
NEO4J_URI=bolt://192.168.107.187:7687
TYPESENSE_URL=http://192.168.107.187:8108
PHOENIX_URL=http://192.168.107.187:6006
PHOENIX_COLLECTOR_ENDPOINT=http://192.168.107.187:6006/v1/traces
```

Do not use nested `${...}` placeholders for runtime-critical URLs. Prior
incidents showed Docker Compose does not reliably expand nested placeholders in
`.env` values.

## What To Do Before GoodAI Decoupling

Before starting the separate GoodAI LTM benchmark decoupling work, stabilize the
new YAAM runtime boundary:

- Keep the MacBook Pro and `skz-data-lv` powered on.
- If `mas-agent` needs a restart before the remote `.env` is cleaned up, always
  include `docker-compose.skz-data.yml`.
- Treat `http://192.168.107.187:8002` as the active YAAM API Wall endpoint.
- Run one smoke request from each consumer project that will depend on YAAM,
  especially TRA and SCM Cert bench.
- Record consumer endpoint changes in those repositories or their local
  environment files.
- Do not delete or clean `skz-dev-lv` resources while it is offline. Once it is
  powered on again, inspect it first and archive deliberately.
- After the permanent `.env` correction, restart `mas-agent` without shell
  overrides and re-run health checks.

## Smartphone-Safe Guidance

While the operator is on a smartphone only:

- Avoid editing `.env` from the phone unless there is no alternative.
- Avoid destructive commands on `skz-dev-lv`; it is offline anyway.
- Keep all follow-up actions limited to read-only checks, health checks, and
  consumer endpoint configuration that can be reviewed safely.
- If YAAM needs a restart before the permanent `.env` fix, use the committed
  `docker-compose.skz-data.yml` override rather than relying on the copied
  `.env`.
- Do not begin repository surgery for GoodAI decoupling from the phone. That
  work should start from a clean MacBook checkout in a separate chat/session.

## Recommended Next Steps

1. Keep monitoring `http://192.168.107.187:8002/health` until the consumer smoke
   checks are complete.
2. When back at the MacBook, edit the remote `.env` on `skz-data-lv` to replace
   stale `192.168.107.172` endpoints with `192.168.107.187`. This is cleanup,
   not an urgent runtime blocker while `docker-compose.skz-data.yml` is used.
3. Restart with the committed `skz-data` override:

   ```bash
   ssh skz-data-local 'cd /home/maxim/code/yet-another-agents-memory && docker compose -f docker-compose.interface.yml -f docker-compose.skz-data.yml up -d --force-recreate mas-agent'
   ```

4. Re-run:

   ```bash
   curl -fsS http://192.168.107.187:8002/health
   ```

5. Only after YAAM is stable on `skz-data-lv`, start the GoodAI decoupling work
   from a clean branch and separate chat.
