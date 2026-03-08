# Smoke Tests Documentation

## Overview

Smoke tests verify basic connectivity to all infrastructure services. These tests can be run from any machine with network access to the services.

## Services Tested

1. **PostgreSQL** (`mas_memory` database) - Operating Memory Layer
2. **Redis** - Cache and Active Context
3. **Qdrant** - Vector Store for embeddings
4. **Neo4j** - Graph Database for relationships
5. **Typesense** - Full-text search engine

## Quick Start

### Prerequisites

```bash
# Install dependencies into the repository-managed virtual environment
poetry install --with test,dev

# Provide credentials via environment variables (recommended).
# If you use a local `.env` file, treat it as a secret:
# - do not commit it
# - do not print its contents in logs
# - do not paste it into chat transcripts
```

### Run All Tests

```bash
# Simple run
./scripts/run_smoke_tests.sh

# Verbose output
./scripts/run_smoke_tests.sh --verbose

# Using pytest directly
./.venv/bin/pytest tests/test_connectivity.py -v
```

### Run Specific Service Tests

```bash
# Test only PostgreSQL
./scripts/run_smoke_tests.sh --service postgres

# Test only Redis
./scripts/run_smoke_tests.sh --service redis

# Test only Qdrant
./scripts/run_smoke_tests.sh --service qdrant

# Test only Neo4j
./scripts/run_smoke_tests.sh --service neo4j

# Test only Typesense
./scripts/run_smoke_tests.sh --service typesense
```

### Quick Summary

```bash
# Show only connectivity summary (fast)
./scripts/run_smoke_tests.sh --summary
```

## Configuration

Tests use environment variables from `.env` file:

```bash
# Orchestrator Node (PostgreSQL, Redis)
DEV_IP=192.168.107.172

# Data Node (Qdrant, Neo4j, Typesense)
STG_IP=192.168.107.187

# Credentials (required)
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=mas_memory
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
TYPESENSE_API_KEY=your_api_key
```

## Running from Different Machines

These tests are designed to be run from any machine:

### From Orchestrator Node (skz-dev-lv)
```bash
cd ~/code/mas-memory-layer
./scripts/run_smoke_tests.sh
```

### From Development Machine
```bash
# Ensure .env has correct IPs and credentials
./scripts/run_smoke_tests.sh
```

### From CI/CD Pipeline
```bash
# Set environment variables
export DEV_IP=192.168.107.172
export STG_IP=192.168.107.187
export POSTGRES_USER=...
export POSTGRES_PASSWORD=...
# ... etc

# Run tests
./.venv/bin/pytest tests/test_connectivity.py -v
```

## Test Coverage

### PostgreSQL Tests
- ✓ Connection to `mas_memory` database
- ✓ Database version check
- ✓ Basic query execution

### Redis Tests
- ✓ PING command
- ✓ SET/GET operations
- ✓ Key expiration

### Qdrant Tests
- ✓ Connection and health check
- ✓ Collections list
- ✓ API availability

### Neo4j Tests
- ✓ Bolt protocol connection
- ✓ Authentication
- ✓ Basic Cypher query

### Typesense Tests
- ✓ HTTP API availability
- ✓ Health endpoint
- ✓ Authentication
- ✓ Collections access

## Troubleshooting

### Connection Refused

```bash
# Check if services are running
systemctl status postgresql  # On orchestrator
systemctl status redis       # On orchestrator

# Check with Docker (if using Docker)
docker ps | grep qdrant
docker ps | grep neo4j
docker ps | grep typesense
```

### Authentication Failed

```bash
# Test PostgreSQL manually
psql "$POSTGRES_URL" -c "SELECT 1;"

# Test Neo4j manually
cypher-shell -a bolt://$STG_IP:7687 -u neo4j -p $NEO4J_PASSWORD "RETURN 1;"
```

### Network Issues

```bash
# Test basic connectivity
ping 192.168.107.172  # Orchestrator
ping 192.168.107.187  # Data node

# Test specific ports
nc -zv 192.168.107.172 5432  # PostgreSQL
nc -zv 192.168.107.172 6379  # Redis
nc -zv 192.168.107.187 6333  # Qdrant
nc -zv 192.168.107.187 7687  # Neo4j Bolt
nc -zv 192.168.107.187 8108  # Typesense
```

### Missing Dependencies

```bash
# Install/update dependencies in the repo virtual environment
poetry install --with test,dev
```

## Integration with Development Workflow

### Before Starting Development
```bash
# Verify infrastructure is ready
./scripts/run_smoke_tests.sh --summary
```

### After Infrastructure Changes
```bash
# Run full connectivity tests
./scripts/run_smoke_tests.sh --verbose
```

### In CI/CD Pipeline
```yaml
# Example GitHub Actions workflow
- name: Run Smoke Tests
  run: |
    poetry install --with test,dev
    ./.venv/bin/pytest tests/test_connectivity.py -v
```

## Adding New Service Tests

To add tests for a new service:

1. Add test functions to `tests/test_connectivity.py`:
```python
def test_newservice_connection(config):
    """Test NewService connection"""
    # Your test code here
    pass
```

2. Update the summary test in `test_all_services_summary()`

3. Add configuration to `.env.example`

4. Update this documentation

## References

- **Main Documentation**: `README.md`
- **Database Setup**: `docs/IAC/database-setup.md`
- **Connectivity**: `docs/IAC/connectivity-cheatsheet.md`
- **Implementation Plan**: `docs/plan/implementation_master_plan_version-0.9.md`
