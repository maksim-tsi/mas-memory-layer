# Database Setup - mas-memory-layer

**Date:** October 20, 2025  
**Database Name:** `mas_memory`  
**Purpose:** Dedicated PostgreSQL database for the multi-layered memory system

---

## Overview

This project uses a **dedicated PostgreSQL database** named `mas_memory` to ensure complete isolation from other projects and prevent any interference with existing databases.

## Prerequisites

### PostgreSQL Client Installation

The PostgreSQL client tools (including `psql`) are **required** for database setup and migrations.

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install -y postgresql-client

# Verify installation
psql --version  # Should show: psql (PostgreSQL) 16.x
```

**macOS:**
```bash
brew install postgresql

# Verify installation
psql --version
```

**Windows:**
- Download PostgreSQL installer from https://www.postgresql.org/download/windows/
- Or use WSL2 with Ubuntu and follow Ubuntu instructions above

## Database Configuration

- **Database Name:** `mas_memory`
- **Host:** `skz-dev-lv` (192.168.107.172)
- **Port:** 5432
- **Owner:** See `.env` file for credentials
- **Connection URL:** `postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@192.168.107.172:5432/mas_memory`

## Initial Database Creation

Before running any migrations, the `mas_memory` database must be created. This is a **one-time setup** operation.

### Option 1: Using psql

```bash
# Load environment variables
set -a; source .env; set +a

# Connect to default postgres database and create mas_memory database
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DEV_IP}:${POSTGRES_PORT}/postgres" -c "CREATE DATABASE mas_memory;"

# Verify database exists
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DEV_IP}:${POSTGRES_PORT}/postgres" -c "\l" | grep mas_memory
```

### Option 2: Using the setup script

```bash
# Run the automated setup script
./scripts/setup_database.sh
```

## Schema Management

All schema migrations are stored in the `migrations/` directory and should be applied in numerical order:

```bash
# Load environment variables
set -a; source .env; set +a

# Apply migration 001
psql "$POSTGRES_URL" -f migrations/001_active_context.sql

# Apply future migrations
psql "$POSTGRES_URL" -f migrations/002_episodic_memory.sql
# ... etc
```

## Database Tables

The `mas_memory` database contains the following tables:

### L1 Memory (Active Context)
- **active_context**: Recent conversation turns (10-20 turns, 24h TTL)
  - Columns: `id`, `session_id`, `turn_id`, `content`, `metadata`, `created_at`, `ttl_expires_at`

### L2 Memory (Working Memory)
- **working_memory**: Session-scoped facts and entities (7 days TTL)
  - Columns: `id`, `session_id`, `fact_type`, `content`, `confidence`, `source_turn_ids`, `created_at`, `updated_at`, `ttl_expires_at`

### Future Tables
- **consolidated_events**: Archive of resolved events (for knowledge distillation)
- **audit_log**: System-wide audit trail for compliance

## Database Cleanup

To remove the database (⚠️ **DESTRUCTIVE OPERATION**):

```bash
# Drop the database (will delete ALL data)
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DEV_IP}:${POSTGRES_PORT}/postgres" -c "DROP DATABASE mas_memory;"
```

## Backup & Restore

### Backup
```bash
# Full database backup
pg_dump "$POSTGRES_URL" > backups/mas_memory_$(date +%Y%m%d_%H%M%S).sql

# Schema-only backup
pg_dump "$POSTGRES_URL" --schema-only > backups/mas_memory_schema.sql
```

### Restore
```bash
# Restore from backup
psql "$POSTGRES_URL" < backups/mas_memory_20251020_120000.sql
```

## Connection Testing

Verify connection to the dedicated database:

```bash
# Load environment variables
set -a; source .env; set +a

# Test connection
psql "$POSTGRES_URL" -c "SELECT current_database(), version();"

# Should output:
# current_database |              version              
# ------------------+----------------------------------
# mas_memory       | PostgreSQL 16.x ...
```

## Environment Variables

Update your `.env` file to use the dedicated database:

```bash
# PostgreSQL Configuration (mas-memory-layer project)
POSTGRES_DB=mas_memory
POSTGRES_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DEV_IP}:${POSTGRES_PORT}/mas_memory
```

## Security Notes

1. **Isolation**: The `mas_memory` database is completely separate from other projects
2. **Access Control**: Only grant necessary permissions to application users
3. **Backup**: Regular backups should be automated (see backup section)
4. **Credentials**: Never commit real passwords to version control

## Troubleshooting

### Database doesn't exist
```bash
# Error: database "mas_memory" does not exist
# Solution: Run the database creation step above
```

### Permission denied
```bash
# Error: permission denied for database
# Solution: Ensure POSTGRES_USER has CREATE DATABASE privilege
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${DEV_IP}:${POSTGRES_PORT}/postgres" \
  -c "ALTER USER ${POSTGRES_USER} CREATEDB;"
```

### Connection refused
```bash
# Error: connection refused
# Solution: Verify PostgreSQL is running and firewall allows connections
systemctl status postgresql  # On the server
```

---

## References

- Implementation Plan: `docs/plan/implementation-plan-20102025.md`
- Connectivity Cheatsheet: `docs/IAC/connectivity-cheatsheet.md`
- Migration Files: `migrations/`
