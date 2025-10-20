# Database Migrations

This directory contains SQL migration scripts for PostgreSQL schema changes.

## Migration Naming Convention

Format: `{number}_{description}.sql`

Example: `001_active_context.sql`

## Applying Migrations

```bash
# Load environment variables
source .env

# Apply migration
psql "$POSTGRES_URL" -f migrations/001_active_context.sql

# Verify tables created
psql "$POSTGRES_URL" -c "\dt"
```

## Current Migrations

- `001_active_context.sql` - L1/L2 memory tables (active_context, working_memory)