# Debug Scripts

One-off debug and verification scripts for development troubleshooting. These scripts are not part of the production workflow but are useful for diagnosing issues during development.

## Scripts

| Script | Purpose |
|--------|---------|
| `check_l2_roundtrip.py` | Verify L2 (WorkingMemory) roundtrip - stores 3 facts and queries them back |
| `check_tier_collection.py` | Verify EpisodicMemoryTier collection configuration matches QdrantAdapter |
| `debug_qdrant_dump.py` | Diagnostic tool to dump/inspect Qdrant collection contents |
| `manual_l3_store.py` | Manual test to store/query an Episode in L3 (Qdrant + Neo4j) |

## Usage

These scripts are typically run manually during development:

```bash
# From repository root
./.venv/bin/python scripts/debug/<script_name>.py
```

## Note

These scripts may require database connections to be available (Redis, PostgreSQL, Qdrant, Neo4j) depending on which tier they test.
