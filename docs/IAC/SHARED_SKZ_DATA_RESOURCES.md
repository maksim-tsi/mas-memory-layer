# Shared skz-data-lv Resources

Last updated: 2026-05-18

This guide is for local projects that use shared data infrastructure on
`skz-data-lv` / `skz-data-local`. It is intended to be copied into project
repos such as YAAM, then adapted only where project-specific names are needed.

Use this document as an application-facing guide. For host operations, the
source of truth remains:

- `.env.example` for supported environment variable names.
- `skz-data-lv/docker-compose.yml` for running service images and ports.
- `docs/MIGRATION_PLAN_DEV_DATA_REBALANCE_2026-05-16.md` for migration history.

Never paste secret values into docs, issues, prompts, logs, screenshots, or
committed files. This document names `.env` keys only.

## Quick Catalog

`skz-data-lv` is the shared AI and data node.

| Item | Value |
| --- | --- |
| Hostnames | `skz-data-lv`, `skz-data-local` |
| LAN IP | `192.168.107.187` |
| Network model | Direct LAN access only |
| Tailscale | Not installed on `skz-data-lv` by design |
| Tailscale gateway | `skz-dev-lv` remains the single Tailscale gateway |
| Data mount | `/data` on the dedicated data NVMe |

Current shared services:

| Service | Image | Ports | Main use |
| --- | --- | --- | --- |
| PostgreSQL | `postgres:18.4-alpine3.23` | `5432` | Relational persistence |
| Redis Stack | `redis/redis-stack-server:7.4.0-v8` | `6379` | Cache, queues, L1 memory |
| Qdrant | `qdrant/qdrant:v1.18.0` | `6333` REST, `6334` gRPC | Vector search |
| Neo4j/DozerDB | `graphstack/dozerdb:5.26.3.0` | `7474` HTTP, `7687` Bolt | Graph relationships |
| Typesense | `typesense/typesense:30.2` | `8108` | Full-text search |
| Phoenix | `arizephoenix/phoenix:version-15.10.0` | `6006` HTTP/OTLP, `4317` OTLP gRPC | Tracing and observability |

## Project Setup

Each project should keep its own `.env` file and read all connection settings
from that file. Do not hardcode IPs, passwords, API keys, database names, or
collection names in application code.

Recommended baseline:

```dotenv
DATA_NODE_IP=192.168.107.187
POSTGRES_PORT=5432
REDIS_PORT=6379
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
NEO4J_BOLT_PORT=7687
NEO4J_HTTP_PORT=7474
TYPESENSE_PORT=8108
PHOENIX_PORT=6006
PHOENIX_GRPC_PORT=4317
```

Then add only the service credentials and project names that the project uses.
Ask the infrastructure owner for secret values and project-specific resources.
Keep real values in untracked `.env` files or a password manager.

## Environment Keys

Use these key names consistently across projects. The values below are names
only, not secrets.

### Node

| Key | Meaning |
| --- | --- |
| `DATA_NODE_IP` | LAN IP for `skz-data-lv`; currently `192.168.107.187` |

### PostgreSQL

| Key | Meaning |
| --- | --- |
| `POSTGRES_HOST` | PostgreSQL host; normally `${DATA_NODE_IP}` |
| `POSTGRES_PORT` | PostgreSQL port; normally `5432` |
| `POSTGRES_DB` | Project database name |
| `POSTGRES_USER` | Project database role |
| `POSTGRES_PASSWORD` | Project database role password |
| `POSTGRES_URL` | Full connection URL for libraries that prefer DSNs |

Policy: use a dedicated database and user per project by default. Application
code should not use the shared admin role unless explicitly approved.

### Redis

| Key | Meaning |
| --- | --- |
| `REDIS_HOST` | Redis host; normally `${DATA_NODE_IP}` |
| `REDIS_PORT` | Redis port; normally `6379` |
| `REDIS_URL` | Redis URL; currently passwordless, usually `redis://${DATA_NODE_IP}:6379` |
| `REDIS_PASSWORD` | Reserved for future auth; currently unset/commented for compatibility |

Redis is currently passwordless to preserve compatibility with existing local
consumers. Treat it as shared infrastructure: use project key prefixes and TTLs.

### Qdrant

| Key | Meaning |
| --- | --- |
| `QDRANT_HOST` | Qdrant host; normally `${DATA_NODE_IP}` |
| `QDRANT_URL` | REST endpoint, normally `http://${DATA_NODE_IP}:6333` |
| `QDRANT_GRPC_URL` | gRPC endpoint, normally `http://${DATA_NODE_IP}:6334` |
| `QDRANT_API_KEY` | Reserved if auth is enabled later |

Use named collections scoped by project and domain.

### Neo4j/DozerDB

| Key | Meaning |
| --- | --- |
| `NEO4J_HOST` | Neo4j host; normally `${DATA_NODE_IP}` |
| `NEO4J_USER` | Neo4j username |
| `NEO4J_PASSWORD` | Neo4j password |
| `NEO4J_URI` | Bolt URI, normally `bolt://${DATA_NODE_IP}:7687` |
| `NEO4J_BOLT` | Bolt URI alias |
| `NEO4J_HTTP` | Browser/API URL, normally `http://${DATA_NODE_IP}:7474` |

Use project-specific labels/properties, or request a project-specific database
when isolation is required and supported by the deployment.

### Typesense

| Key | Meaning |
| --- | --- |
| `TYPESENSE_HOST` | Typesense host; normally `${DATA_NODE_IP}` |
| `TYPESENSE_PORT` | Typesense port; normally `8108` |
| `TYPESENSE_PROTOCOL` | Normally `http` |
| `TYPESENSE_URL` | Full HTTP URL |
| `TYPESENSE_API_KEY` | Typesense API key |

Use collection names scoped by project and index.

### Phoenix

| Key | Meaning |
| --- | --- |
| `PHOENIX_URL` | Phoenix UI/API URL, normally `http://${DATA_NODE_IP}:6006` |
| `PHOENIX_COLLECTOR_ENDPOINT` | OTLP HTTP trace endpoint, normally `http://${DATA_NODE_IP}:6006/v1/traces` |
| `PHOENIX_GRPC_URL` | OTLP gRPC endpoint, normally `http://${DATA_NODE_IP}:4317` |
| `PHOENIX_PROJECT_NAME` | Project/environment name shown in Phoenix |

Phoenix is LAN-only. It is not exposed through Caddy and should not be treated
as a WAN-facing or Tailscale-exposed service.

## Service Usage

### PostgreSQL

Use PostgreSQL for durable relational data, transactional state, application
metadata, and service-owned schemas.

Default policy:

- One database and one role per project.
- Use least privilege for application roles.
- Use migrations for schema changes.
- Use connection pools for long-running services.
- Coordinate before destructive actions such as `DROP DATABASE`, `DROP TABLE`,
  bulk deletes, or large rewrites.

Recommended naming:

| Resource | Pattern | Example |
| --- | --- | --- |
| Database | `<project>_<environment>` | `yaam_dev` |
| User/role | `<project>_<environment>_app` | `yaam_dev_app` |
| Schema | `<domain>` or `<project>_<domain>` | `memory` |

### Redis Stack

Use Redis for cache, queues, locks, short-lived coordination, and L1 memory.
The current endpoint is passwordless for compatibility.

Rules for shared use:

- Prefix keys with the project name.
- Set TTLs for ephemeral data.
- Avoid unbounded key growth.
- Do not use Redis as the only store for data that must survive failures unless
  the project owner explicitly accepts the durability tradeoff.
- Coordinate before running `FLUSHDB`, `FLUSHALL`, mass deletes, or large scans.

Recommended key pattern:

```text
<project>:<domain>:<entity>:<id>
```

Example:

```text
yaam:memory:session:abc123
```

### Qdrant

Use Qdrant for vector search, embedding retrieval, semantic memory, and nearest
neighbor search.

Recommended practices:

- Use one or more project-scoped collections.
- Store project/domain metadata in payloads.
- Version collection names when changing embedding dimensions or model families.
- Prefer the official `qdrant-client` package.
- Coordinate before deleting collections or rebuilding large indexes.

Collection naming:

```text
<project>_<domain>
<project>_<domain>_v<version>
```

Examples:

```text
yaam_memory
yaam_memory_v2
```

### Neo4j/DozerDB

Use Neo4j/DozerDB for graph-shaped relationships, traversals, knowledge graphs,
lineage, dependencies, and relationship-heavy memory.

Recommended practices:

- Use project-specific labels and a `project` property.
- Use indexes/constraints for high-cardinality lookup properties.
- Keep graph writes behind application services or migrations where possible.
- Coordinate before deleting nodes/relationships or changing global constraints.

Label and property examples:

```cypher
(:YaamMemory {project: "yaam", environment: "dev"})
(:YaamEntity {project: "yaam"})
```

### Typesense

Use Typesense for full-text search, faceting, and fast user-facing index lookup.

Recommended practices:

- Scope collection names by project and index.
- Treat Typesense as an index that can usually be rebuilt from source data.
- Keep index definitions in code or migrations.
- Use API keys from `.env`, not hardcoded values.
- Coordinate before deleting collections or rebuilding indexes.

Collection naming:

```text
<project>_<index>
```

Example:

```text
yaam_documents
```

### Phoenix

Use Phoenix for traces, spans, evaluations, prompt/application observability,
and debugging local AI workflows.

Recommended practices:

- Set `PHOENIX_PROJECT_NAME` per project and environment.
- Use OTLP HTTP unless a library requires gRPC.
- Keep Phoenix LAN-only.
- Do not import old Phoenix SQLite traces into the new shared instance.
- Treat trace payloads as potentially sensitive application data.

Project naming:

```text
<project>-<environment>
```

Examples:

```text
yaam-dev
mas-memory-layer-dev
```

## Python Examples

These examples are intentionally small. In production code, wrap clients in
project-specific modules, configure timeouts, and reuse pooled clients instead
of creating new connections for every operation.

### PostgreSQL With psycopg

```python
import os

import psycopg


with psycopg.connect(os.environ["POSTGRES_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute("select current_database(), current_user")
        database, user = cur.fetchone()
        print({"database": database, "user": user})
```

### PostgreSQL With SQLAlchemy

```python
import os

from sqlalchemy import create_engine, text


engine = create_engine(
    os.environ["POSTGRES_URL"],
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
)

with engine.begin() as conn:
    result = conn.execute(text("select 1"))
    print(result.scalar_one())
```

### Redis

```python
import os

import redis


client = redis.Redis.from_url(
    os.environ["REDIS_URL"],
    decode_responses=True,
    socket_timeout=5,
)

client.set("my_project:health:ping", "ok", ex=60)
print(client.get("my_project:health:ping"))
```

### Qdrant

```python
import os

from qdrant_client import QdrantClient


client = QdrantClient(url=os.environ["QDRANT_URL"], timeout=10)

collections = client.get_collections()
print([collection.name for collection in collections.collections])
```

### Neo4j/DozerDB

```python
import os

from neo4j import GraphDatabase


driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
)

with driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j")) as session:
    value = session.run("return 1 as ok").single()["ok"]
    print(value)

driver.close()
```

### Typesense

```python
import os

import typesense


client = typesense.Client(
    {
        "nodes": [
            {
                "host": os.environ["TYPESENSE_HOST"],
                "port": os.environ.get("TYPESENSE_PORT", "8108"),
                "protocol": os.environ.get("TYPESENSE_PROTOCOL", "http"),
            }
        ],
        "api_key": os.environ["TYPESENSE_API_KEY"],
        "connection_timeout_seconds": 5,
    }
)

print(client.collections.retrieve())
```

### Phoenix / OpenTelemetry

```python
import os

from opentelemetry import trace
from phoenix.otel import register


register(
    endpoint=os.environ["PHOENIX_COLLECTOR_ENDPOINT"],
    project_name=os.environ["PHOENIX_PROJECT_NAME"],
    protocol="http/protobuf",
    batch=True,
    auto_instrument=True,
)

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("shared-data-node-smoke-test") as span:
    span.set_attribute("service", "skz-data-lv")
    span.set_attribute("project", os.environ["PHOENIX_PROJECT_NAME"])
```

## Verification From A Project Machine

Run these checks from a machine on the same LAN as `skz-data-lv`, such as the
local MacBook. They should use project `.env` values where possible.

### Redis

```bash
scripts/redis_connectivity_check.sh --host "$DATA_NODE_IP" --port "$REDIS_PORT" --no-auth
```

Expected result: `PING` returns `PONG`.

### PostgreSQL

```bash
psql "$POSTGRES_URL" -c 'select current_database(), current_user;'
```

Expected result: the project database and project user are returned.

### Qdrant

```bash
curl -fsS "$QDRANT_URL/collections"
```

Expected result: JSON response listing collections.

### Neo4j/DozerDB

```bash
cypher-shell -a "$NEO4J_URI" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" 'RETURN 1 AS ok;'
```

Expected result: `ok` is `1`.

### Typesense

```bash
curl -fsS "$TYPESENSE_URL/health" -H "X-TYPESENSE-API-KEY: $TYPESENSE_API_KEY"
```

Expected result: Typesense health response is healthy.

### Phoenix

```bash
curl -fsS "$PHOENIX_URL"
```

Expected result: Phoenix UI HTML is returned. For trace validation, run the
Phoenix/OpenTelemetry smoke example above and check the project in the UI.

## Requesting New Resources

When a project needs a new shared resource, send this information to the
infrastructure owner:

| Field | Example |
| --- | --- |
| Project slug | `yaam` |
| Environment | `dev` |
| Owner/contact | Project maintainer |
| Services needed | PostgreSQL, Redis, Qdrant, Phoenix |
| Data sensitivity | Local development, personal, production-ish |
| Expected size/growth | Rows, vectors, documents, graph size, cache volume |
| Retention expectations | Temporary, rebuildable, durable |
| Backup expectation | Best effort, required, or externally backed up |
| Destructive jobs | Whether the project runs deletes, rebuilds, or compaction |

For PostgreSQL, request a dedicated database and role. For search/vector/graph
services, request or declare a project namespace before creating shared objects.

## Naming Conventions

Prefer lowercase names with clear project ownership.

| Resource | Pattern | Example |
| --- | --- | --- |
| PostgreSQL database | `<project>_<environment>` | `yaam_dev` |
| PostgreSQL user | `<project>_<environment>_app` | `yaam_dev_app` |
| Redis key | `<project>:<domain>:<entity>:<id>` | `yaam:memory:session:abc123` |
| Qdrant collection | `<project>_<domain>` | `yaam_memory` |
| Typesense collection | `<project>_<index>` | `yaam_documents` |
| Neo4j label | `<Project><Entity>` | `YaamMemory` |
| Neo4j property | `project` and `environment` | `project: "yaam"` |
| Phoenix project | `<project>-<environment>` | `yaam-dev` |

When a resource must change in a backward-incompatible way, prefer creating a
versioned replacement such as `yaam_memory_v2`, then cut over clients.

## Security Expectations

- Keep real `.env` files untracked.
- Store shared secrets in the agreed password manager or machine-local `.env`
  files, not in project docs.
- Print env key names in logs only when necessary; do not print values.
- Do not paste secret values into prompts or issue trackers.
- Treat Phoenix traces, Redis values, vector payloads, graph properties, and
  search documents as potentially sensitive.
- Ask before exposing any `skz-data-lv` service beyond the LAN.
- Ask before enabling auth changes on shared services, because consumers may
  need coordinated updates.

## Backup And Durability Expectations

The data services were restored and validated during the 2026-05 data rebalance
migration. Shared infrastructure does not make every project object equally
durable by default. Each project should classify its data:

| Class | Examples | Expected approach |
| --- | --- | --- |
| Rebuildable index | Typesense collections, derived Qdrant collections | Keep source data and rebuild scripts |
| Cache/ephemeral | Redis L1 memory, locks, temporary queues | Use TTLs and tolerate loss |
| Durable app state | PostgreSQL tables, canonical graph data | Use migrations and backup expectations |
| Observability | Phoenix traces | Useful for debugging, not canonical business data |

Before deleting, rebuilding, or compacting shared resources, coordinate with the
owners of affected projects.

## Current Inventory Snapshot

This is a migration snapshot, not an API contract:

- PostgreSQL databases validated during migration include `mas_memory`,
  `n8n_production`, `phoenix`, `postgres`, `scm_bench_db`, and `udacity`.
- Qdrant was validated with `121` collections and `719` points.
- Typesense was validated with `5` collections and `1228` documents.
- Neo4j/DozerDB was validated with `827` nodes and `326` relationships.
- Redis is deployed with persistence enabled and passwordless compatibility.
- Phoenix is deployed fresh on PostgreSQL; old SQLite traces were not imported.

## Deferred Items

- YAAM remains on `skz-dev-lv` at `/home/max/code/mas-memory-layer`.
- YAAM migration/repointing is `TO_BE_PLANNED` and will happen during the YAAM
  redesign, not as part of this completed data-node migration.
- Monitoring on `skz-cloud-lv` is deployed but unused, pending design.
- `skz-data-lv` should remain LAN-only unless the gateway/network design is
  explicitly revisited.
