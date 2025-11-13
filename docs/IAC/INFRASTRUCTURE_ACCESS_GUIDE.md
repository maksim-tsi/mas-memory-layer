# Infrastructure Access Guide

**Project:** MAS Memory Layer  
**Last Updated:** November 12, 2025  
**Status:** Production-Ready ✅

---

## Overview

This project uses a **two-node distributed infrastructure** as specified in [ADR-002](../ADR/002-infrastructure-architecture.md):

- **skz-dev-lv** (192.168.107.172) - Orchestrator Node
- **skz-stg-lv** (192.168.107.187) - AI Data & Monitoring Node

---

## Infrastructure Architecture

### Node Assignments (per ADR-002)

| Service | Node | Port(s) | Purpose | Storage |
|---------|------|---------|---------|---------|
| **PostgreSQL** | skz-dev-lv | 5432 | L1/L2 Relational Memory | OS Drive |
| **Redis** | skz-dev-lv | 6379 | L1 High-Speed Cache | OS Drive |
| **Qdrant** | skz-stg-lv | 6333-6334 | L3 Vector Search | `/mnt/data` (512GB NVMe) |
| **Neo4j** | skz-stg-lv | 7474, 7687 | L3 Graph Relationships | `/mnt/data` (512GB NVMe) |
| **Typesense** | skz-stg-lv | 8108 | L4 Full-Text Search | `/mnt/data` (512GB NVMe) |
| **Prometheus** | skz-stg-lv | 9090 | Metrics Collection | OS Drive |
| **Grafana** | skz-stg-lv | 3000 | Monitoring Dashboards | OS Drive |

---

## Service Access Points

### 🔒 Authentication Required

All services require authentication. **Credentials are stored in `.env` file** (excluded from git).

#### skz-dev-lv (192.168.107.172)

**PostgreSQL** - L1/L2 Relational Storage
```
Host: 192.168.107.172
Port: 5432
Database: mas_memory
User: postgres
Password: <stored in .env>

Connection String:
postgresql://postgres:${POSTGRES_PASSWORD}@192.168.107.172:5432/mas_memory
```

**Redis** - L1 Cache
```
Host: 192.168.107.172
Port: 6379
Password: None (no auth configured)

Connection String:
redis://192.168.107.172:6379
```

#### skz-stg-lv (192.168.107.187)

**Qdrant** - L3 Vector Database
```
Host: 192.168.107.187
Port: 6333 (HTTP API)
Port: 6334 (gRPC)
API Key: None (no auth configured)

Web UI: http://192.168.107.187:6333/dashboard
API URL: http://192.168.107.187:6333
```

**Neo4j** - L3 Graph Database
```
Host: 192.168.107.187
Port: 7687 (Bolt Protocol)
Port: 7474 (HTTP/Browser)
User: neo4j
Password: <stored in .env>

Browser UI: http://192.168.107.187:7474
Bolt URI: bolt://192.168.107.187:7687
```

**Typesense** - L4 Full-Text Search
```
Host: 192.168.107.187
Port: 8108
Protocol: http
API Key: <stored in .env>

API URL: http://192.168.107.187:8108
```

**Prometheus** - Metrics Collection
```
Host: 192.168.107.187
Port: 9090

Web UI: http://192.168.107.187:9090
```

**Grafana** - Monitoring Dashboards
```
Host: 192.168.107.187
Port: 3000
User: admin
Password: <stored in .env>

Web UI: http://192.168.107.187:3000
```

---

## Storage Architecture

### skz-dev-lv Storage
- **OS Drive:** Single 512GB NVMe
- **PostgreSQL Data:** `/var/lib/postgresql/data`
- **Redis Data:** `/var/lib/redis` (or in-memory)

### skz-stg-lv Storage ✅ **ADR-002 Compliant**

**Dual NVMe Configuration:**
- **nvme1n1 (512GB):** Operating System
- **nvme0n1 (512GB):** AI Database Storage (mounted at `/mnt/data`)

**Data Drive Layout (`/mnt/data` - 458GB usable):**
```
/mnt/data/
├── qdrant/      # 25GB - Vector embeddings for L3
├── neo4j/       # 517MB - Graph data for L3
└── typesense/   # 1.6MB - Full-text indexes for L4

Current Usage: 25GB / 458GB (6%)
```

**Volume Strategy:**
- **AI Databases:** Bind mounts to `/mnt/data` (dedicated I/O)
- **Monitoring:** Named volumes on OS drive (small data, no I/O conflict)

**Rationale:** Separates high-throughput AI database I/O from OS operations for optimal performance.

---

## Connectivity Verification

### Pre-Flight Checklist

Before running tests, verify all services are accessible:

**From skz-dev-lv or development machine:**

```bash
# PostgreSQL
psql -h 192.168.107.172 -U postgres -d mas_memory -c "SELECT 1;"

# Redis
redis-cli -h 192.168.107.172 ping

# Qdrant
curl http://192.168.107.187:6333/collections

# Neo4j (requires auth)
curl -u neo4j:${NEO4J_PASSWORD} http://192.168.107.187:7474/db/neo4j/tx/commit

# Typesense (requires API key)
curl -H "X-TYPESENSE-API-KEY: ${TYPESENSE_API_KEY}" \
  http://192.168.107.187:8108/collections

# Prometheus
curl http://192.168.107.187:9090/api/v1/status/config

# Grafana
curl http://192.168.107.187:3000/api/health
```

### Connectivity Test Results (November 12, 2025)

✅ **All services verified accessible** per infrastructure rollout report:
- PostgreSQL: ✅ Accessible on port 5432
- Redis: ✅ Accessible on port 6379
- Qdrant: ✅ Running on ports 6333-6334
- Neo4j: ✅ Running on ports 7474, 7687
- Typesense: ✅ Running on port 8108
- Prometheus: ✅ Running on port 9090
- Grafana: ✅ Running on port 3000

**Docker Compose Status (skz-stg-lv):**
All services healthy and using correct storage locations as per ADR-002.

---

## Security & Credentials

### 🔒 Credential Management

**ALL credentials are stored in `.env` file** which is:
- ✅ Excluded from git via `.gitignore`
- ✅ Never committed to the repository
- ✅ Stored locally on development machines only

**Required Credentials:**
1. `POSTGRES_PASSWORD` - PostgreSQL database password
2. `NEO4J_PASSWORD` - Neo4j graph database password
3. `TYPESENSE_API_KEY` - Typesense search API key
4. `GF_SECURITY_ADMIN_PASSWORD` - Grafana admin password

### Setting Up Credentials

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and replace placeholder values:**
   ```bash
   nano .env  # or vim .env
   ```

3. **Update these fields:**
   ```bash
   POSTGRES_PASSWORD=your_actual_postgres_password
   NEO4J_PASSWORD=your_actual_neo4j_password
   TYPESENSE_API_KEY=your_actual_typesense_api_key
   GF_SECURITY_ADMIN_PASSWORD=your_actual_grafana_password
   ```

4. **Verify `.env` is in `.gitignore`:**
   ```bash
   cat .gitignore | grep "^.env$"
   # Should output: .env
   ```

### 🚨 NEVER COMMIT CREDENTIALS

- **DO NOT** commit `.env` file
- **DO NOT** hardcode credentials in source code
- **DO NOT** share credentials in documentation
- **DO** use `.env.example` as template (with placeholders only)

---

## Running Integration Tests

### Prerequisites

**System Tools:**
```bash
# Install PostgreSQL client (required for database setup)
sudo apt update && sudo apt install -y postgresql-client

# Verify installation
psql --version  # Should show: psql (PostgreSQL) 16.x
```

**Python Environment:**

1. **Environment configured:**
   ```bash
   # Ensure .env file exists with real credentials
   ls -la .env
   ```

2. **Virtual environment activated:**
   ```bash
   source .venv/bin/activate
   ```

3. **All services running:**
   - Verify via connectivity checklist above

### Running Tests

**Test all storage adapters:**
```bash
./scripts/run_memory_integration_tests.sh
```

**Test specific adapters:**
```bash
./scripts/run_memory_integration_tests.sh postgres
./scripts/run_memory_integration_tests.sh redis
./scripts/run_memory_integration_tests.sh qdrant
./scripts/run_memory_integration_tests.sh neo4j
./scripts/run_memory_integration_tests.sh typesense
```

**Expected Output:**
```
================================================
  Memory Tier Integration Tests
  Testing against real DBMS instances
================================================

[1/5] Checking for .env file...
✓ .env file found

[2/5] Loading environment variables...
✓ Environment variables loaded

[3/5] Activating virtual environment...
✓ Virtual environment activated

[4/5] Connection configuration:
  skz-dev-lv (192.168.107.172):
    - PostgreSQL: 192.168.107.172:5432 (DB: mas_memory)
    - Redis: 192.168.107.172:6379

  skz-stg-lv (192.168.107.187):
    - Qdrant: 192.168.107.187:6333
    - Neo4j: 192.168.107.187:7687
    - Typesense: 192.168.107.187:8108

[5/5] Running integration tests...
```

---

## Monitoring & Observability

### Grafana Dashboards

Access Grafana at: http://192.168.107.187:3000

**Login:**
- Username: `admin`
- Password: `<stored in .env>`

**Setup Guide:** See [docs/grafana-setup-guide.md](grafana-setup-guide.md)

**Recommended Dashboards:**
1. Node Exporter Full (ID: 1860) - System metrics
2. Qdrant Monitoring - Vector database performance
3. Neo4j Metrics - Graph database health
4. PostgreSQL Overview - Database performance

### Prometheus Metrics

Access Prometheus at: http://192.168.107.187:9090

**Configuration:** See [docs/prometheus-configuration.md](prometheus-configuration.md)

**Key Metrics:**
- Storage adapter latency (L1-L4 tiers)
- Memory tier operations per second
- CIAR scoring performance
- Engine processing rates

---

## Troubleshooting

### Common Issues

**1. Cannot connect to PostgreSQL**
```bash
# Check if service is running
systemctl status postgresql

# Check firewall
sudo ufw status
sudo ufw allow 5432/tcp
```

**2. Cannot connect to Redis**
```bash
# Check if service is running
systemctl status redis-server

# Test connection
redis-cli -h 192.168.107.172 ping
```

**3. Docker services not running (skz-stg-lv)**
```bash
# Check service status
docker compose ps

# Restart all services
docker compose restart

# Check logs
docker compose logs [service_name]
```

**4. Permission denied on `/mnt/data`**
```bash
# Check mount status
df -h /mnt/data

# Verify permissions
ls -la /mnt/data/

# Fix if needed (on skz-stg-lv)
sudo chown -R 1000:1000 /mnt/data/qdrant
sudo chown -R 7474:7474 /mnt/data/neo4j
sudo chown -R 2000:2000 /mnt/data/typesense
```

**5. Integration tests failing**
```bash
# Verify .env file exists and has correct values
cat .env | grep PASSWORD

# Test individual service connectivity
curl http://192.168.107.187:6333/collections

# Check test logs
cat integration_test_results.log
```

---

## Maintenance

### Backup Recommendations

**Critical Data Locations:**

**skz-dev-lv:**
- PostgreSQL: Regular dumps via `pg_dump`
- Redis: RDB snapshots (if persistence enabled)

**skz-stg-lv:**
- `/mnt/data/qdrant` - Vector embeddings (25GB)
- `/mnt/data/neo4j` - Graph data (517MB)
- `/mnt/data/typesense` - Search indexes (1.6MB)

**Backup Command (from skz-stg-lv):**
```bash
# Create timestamped backup
sudo tar -czf /backup/ai-databases-$(date +%Y%m%d).tar.gz /mnt/data/

# Keep last 7 days
find /backup/ -name "ai-databases-*.tar.gz" -mtime +7 -delete
```

### Monitoring Storage Usage

**Data drive monitoring (skz-stg-lv):**
```bash
# Check space
df -h /mnt/data

# Check per-service usage
du -sh /mnt/data/*

# Alert threshold: 80% full (367GB used of 458GB)
```

**PostgreSQL monitoring (skz-dev-lv):**
```bash
# Database size
psql -U postgres -d mas_memory -c "SELECT pg_size_pretty(pg_database_size('mas_memory'));"

# Table sizes
psql -U postgres -d mas_memory -c "SELECT tablename, pg_size_pretty(pg_total_relation_size(tablename::regclass)) FROM pg_tables WHERE schemaname = 'public';"
```

---

## References

- **ADR-002:** [Infrastructure Architecture](../ADR/002-infrastructure-architecture.md)
- **ADR-003:** [Four-Tier Memory Architecture](../ADR/003-four-layers-memory.md)
- **Infrastructure Rollout Report:** [November 11, 2025](infra-deploy-report-19102025.md)
- **Grafana Setup:** [Setup Guide](grafana-setup-guide.md)
- **Prometheus Config:** [Configuration Guide](prometheus-configuration.md)

---

## Quick Reference

### Environment Variables (from .env)

```bash
# skz-dev-lv Services
POSTGRES_HOST=192.168.107.172
POSTGRES_PORT=5432
POSTGRES_DB=mas_memory
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<secure_password>

REDIS_HOST=192.168.107.172
REDIS_PORT=6379

# skz-stg-lv Services
QDRANT_HOST=192.168.107.187
QDRANT_PORT=6333
QDRANT_URL=http://192.168.107.187:6333

NEO4J_HOST=192.168.107.187
NEO4J_URI=bolt://192.168.107.187:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secure_password>

TYPESENSE_HOST=192.168.107.187
TYPESENSE_PORT=8108
TYPESENSE_PROTOCOL=http
TYPESENSE_URL=http://192.168.107.187:8108
TYPESENSE_API_KEY=<secure_api_key>

# Monitoring
PROMETHEUS_URL=http://192.168.107.187:9090
GRAFANA_URL=http://192.168.107.187:3000
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=<secure_password>
```

---

**Document Owner:** Infrastructure Team  
**Review Schedule:** Monthly  
**Last Verified:** November 12, 2025
