# Connectivity Cheat Sheet (Local Home Lab)

Date: October 19, 2025

This document summarizes the key connectivity details for the main components in the home lab deployment. Use this as a quick reference for configuring applications and verifying connectivity.

---

## Hosts

- Orchestrator Node: `skz-dev-lv` — 192.168.107.172
- Data Node: `skz-data-lv` — 192.168.107.187

## Services on Orchestrator Node (skz-dev-lv)

- PostgreSQL: 192.168.107.172:5432 (psql) - **Database:** `mas_memory`
- Redis: 192.168.107.172:6379 (redis-cli)
- n8n: http://192.168.107.172:5678 (Web UI)
- Arize Phoenix: http://192.168.107.172:6006 (Web UI)

## Services on Data Node (skz-data-lv)

- Qdrant: http://192.168.107.187:6333 (REST API, dashboard at /dashboard)
- Neo4j (Bolt): bolt://192.168.107.187:7687 (UI at http://192.168.107.187:7474)
- Typesense: http://192.168.107.187:8108 (REST API)

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

- **Managed via `.env` file in repository root (NOT committed to public repo)**
- Required environment variables:
  - `POSTGRES_USER` and `POSTGRES_PASSWORD`
  - `NEO4J_USER` and `NEO4J_PASSWORD`
  - `TYPESENSE_API_KEY`
- See `.env.example` for template

## Notes

- NAS share is currently disabled. Store raw PDF artifacts locally on the Mac. PDFs are excluded from version control (see .gitignore).
- All services are configured to restart on boot via Docker Compose.
