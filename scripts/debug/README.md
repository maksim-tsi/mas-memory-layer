# Debug Scripts

One-off debug and verification scripts for development troubleshooting. These scripts are not part of the production workflow but are useful for diagnosing issues during development.

## Scripts

| Script | Purpose |
|--------|---------|
| `check_yaam_data_node.py` | Verify local `.env` YAAM data-node endpoints without printing secrets |
| `check_l2_roundtrip.py` | Verify L2 (WorkingMemory) roundtrip - stores 3 facts and queries them back |
| `check_tier_collection.py` | Verify EpisodicMemoryTier collection naming and vector size match QdrantAdapter (including V2 mode and embedding dimensions) |
| `debug_qdrant_dump.py` | Diagnostic tool to dump/inspect Qdrant collection contents |
| `manual_l3_store.py` | Manual test to store/query an Episode in L3 (Qdrant + Neo4j) |

## Usage

These scripts are typically run manually during development:

```bash
# From repository root
./.venv/bin/python scripts/debug/<script_name>.py

# Check YAAM data-node endpoints from .env without exposing secret values
./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env
./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env --json
./.venv/bin/python scripts/debug/check_yaam_data_node.py --env-file .env --service redis --service postgres

# For environment-sensitive checks (recommended for V2 validation)
set -a && . ./.env && set +a && ./.venv/bin/python scripts/debug/check_tier_collection.py
```

Expected V2 output pattern when OpenRouter embeddings are configured:

```text
Adapter collection: episodes_v2 vector_size: 1024
Tier collection: episodes_v2 vector_size: 1024
```

## Note

These scripts may require database connections to be available (Redis, PostgreSQL, Qdrant, Neo4j) depending on which tier they test.
