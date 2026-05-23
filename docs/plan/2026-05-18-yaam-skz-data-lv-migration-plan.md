# YAAM skz-data-lv Migration Plan

Date: 2026-05-18
Status: Execution prep
Target branch: `dev-tests`

## Summary

YAAM is moving from `skz-dev-lv` to `skz-data-lv` so the API Wall runtime is
co-located with the shared DBMS services it orchestrates. The MacBook remains
the primary development machine. `skz-data-lv` becomes the runtime/deploy host,
accessed through SSH alias `skz-data-local`.

This is not only a `git clone` operation. The migration must preserve secrets,
avoid unresolved environment placeholders, validate the Docker runtime, and keep
`skz-dev-lv` available as rollback until consumers are confirmed.

## Current Facts

- Local MacBook checkout is on `dev-tests` and aligned with `origin/dev-tests`.
- `skz-data-local` resolves to `192.168.107.187` and logs in as `maxim`.
- `skz-data-local` has Git and Docker Compose available.
- `skz-data-local` already runs PostgreSQL, Redis, Qdrant, Neo4j/DozerDB,
  Typesense, and Phoenix.
- The target checkout path is `/home/maxim/code/yet-another-agents-memory`.
- The old checkout exists on `skz-dev-local` at `/home/max/code/mas-memory-layer`
  and is currently a rollback source.

## Execution Plan

1. Commit this plan together with `docs/IAC/SHARED_SKZ_DATA_RESOURCES.md`.
2. Push `dev-tests` so the data node can clone the documented migration state.
3. On `skz-data-local`, create `/home/maxim/code` if missing.
4. Clone the repository into `/home/maxim/code/yet-another-agents-memory`.
5. Checkout `dev-tests` in the remote clone.
6. Manually copy `.env` from `skz-dev-local` to `skz-data-local` without
   printing or committing secret values.
7. Edit the remote `.env` so runtime-critical service URLs use concrete
   `192.168.107.187` endpoints, not nested `${...}` placeholders.
8. Start the API Wall on `skz-data-local` with:

   ```bash
   docker compose -f docker-compose.interface.yml up -d --build mas-agent
   ```

9. Validate local and MacBook reachability:

   ```bash
   curl -fsS http://127.0.0.1:8002/health
   curl -fsS http://skz-data-local:8002/health
   ```

10. Repoint TRA and SCM Cert bench consumers to `skz-data-local:8002`.
11. Keep `skz-dev-lv` intact until consumer smoke tests pass.

## Secret Boundary

Agents must not read, print, copy, or rewrite `.env` contents. The operator must
perform the secret transfer manually, for example:

```bash
ssh skz-data-local 'mkdir -p /home/maxim/code/yet-another-agents-memory'
scp skz-dev-local:/home/max/code/mas-memory-layer/.env \
  skz-data-local:/home/maxim/code/yet-another-agents-memory/.env
```

After copying, the operator should ensure the remote `.env` contains concrete
service URLs similar to:

```dotenv
REDIS_URL=redis://192.168.107.187:6379/0
QDRANT_URL=http://192.168.107.187:6333
NEO4J_URI=bolt://192.168.107.187:7687
TYPESENSE_URL=http://192.168.107.187:8108
PHOENIX_URL=http://192.168.107.187:6006
PHOENIX_COLLECTOR_ENDPOINT=http://192.168.107.187:6006/v1/traces
```

Do not use unresolved nested placeholders for runtime-critical URLs. Prior
incident records show Docker Compose does not recursively expand such values
inside `.env` reliably.

## Automation Boundary

An agent may:

- commit documentation and non-secret configuration changes;
- create the remote code directory;
- clone, fetch, checkout, and pull the Git repository;
- run Docker Compose;
- inspect non-secret logs and health endpoints;
- verify whether `.env` exists without reading it.

An agent must not:

- read or display `.env`;
- transfer `.env`;
- delete the old checkout on `skz-dev-lv`;
- run destructive DBMS operations;
- force-push or rewrite `dev-tests` history.

## Verification

Run these checks before declaring the migration ready:

- `git status --short` is clean on the MacBook after documentation commit.
- `git status --branch --short` on the remote clone shows `dev-tests` tracking
  `origin/dev-tests`.
- `.env` exists on `skz-data-local` but is not tracked by Git.
- `docker compose -f docker-compose.interface.yml ps` shows `mas-agent` running.
- `curl -fsS http://127.0.0.1:8002/health` succeeds on `skz-data-local`.
- `curl -fsS http://skz-data-local:8002/health` succeeds from the MacBook.
- TRA and SCM Cert bench each complete one smoke request against the new
  endpoint.

## Rollback

If the `skz-data-lv` API Wall fails to start or consumers fail against the new
endpoint, keep TRA and SCM Cert bench pointed at the old endpoint and leave
`skz-dev-lv` untouched. Investigate logs on `skz-data-lv`, fix config or code,
and retry. Delete or archive the old checkout only after a successful consumer
validation window.
