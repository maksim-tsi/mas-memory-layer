# Connectivity Cheat Sheet (Local Home Lab)

Date: October 19, 2025

This document summarizes the key connectivity details for the main components in the home lab deployment. Use this as a quick reference for configuring applications and verifying connectivity.

---

## Hosts

- Orchestrator Node: `skz-dev-lv` — ${DEV_IP}
- Data Node: `skz-stg-lv` — ${STG_IP}

## Services on Orchestrator Node (skz-dev-lv)

- PostgreSQL: ${DEV_IP}:${POSTGRES_PORT} (psql)
- Redis: ${DEV_IP}:${REDIS_PORT} (redis-cli)
- n8n: http://${DEV_IP}:${N8N_PORT} (Web UI)
- Arize Phoenix: http://${DEV_IP}:${PHOENIX_PORT} (Web UI)

## Services on Data Node (skz-stg-lv)

- Qdrant: ${QDRANT_URL} (REST API, dashboard at /dashboard)
- Neo4j (Bolt): ${NEO4J_BOLT} (UI at ${NEO4J_HTTP})
- Typesense: ${TYPESENSE_URL} (REST API)

## Usage & Verification

Load environment variables (zsh):

```zsh
set -a; source .env; set +a
```

Verify connectivity:

```zsh
curl "$QDRANT_URL" | grep -i title
curl "$TYPESENSE_URL/health"
redis-cli -u "$REDIS_URL" PING
psql "$POSTGRES_URL" -c "SELECT 1;"
```

## Credentials

- Managed via per-service `.env` files. Request keys/passwords as needed:
  - POSTGRES_PASSWORD
  - NEO4J_PASSWORD
  - TYPESENSE_API_KEY

## Notes

- NAS share is currently disabled. Store raw PDF artifacts locally on the Mac. PDFs are excluded from version control (see .gitignore).
- All services are configured to restart on boot via Docker Compose.
