# Memory Tiers

Implementation of the 4-tier memory architecture.

## Tier Hierarchy

```
L1 (Active Context)     → Short-term, session-scoped
    ↓ Promotion
L2 (Working Memory)     → Fact-based, CIAR-scored
    ↓ Consolidation  
L3 (Episodic Memory)    → Episode clusters with embeddings
    ↓ Distillation
L4 (Semantic Memory)    → Synthesized knowledge documents
```

## Files

| File | Tier | Storage Backend |
|------|------|-----------------|
| `base_tier.py` | Abstract base | - |
| `active_context_tier.py` | L1 | Redis |
| `working_memory_tier.py` | L2 | PostgreSQL |
| `episodic_memory_tier.py` | L3 | Qdrant + Neo4j |
| `semantic_memory_tier.py` | L4 | Typesense + Neo4j |

## Common Interface

All tiers implement:
- `store(data)` - Store data in the tier
- `retrieve(session_id, query)` - Retrieve data
- `query(filters, limit)` - Query with filters
- `health_check()` - Check tier health

## Telemetry

Each tier accepts an optional `telemetry_stream` parameter for Glass Box observability:

```python
tier = WorkingMemoryTier(
    postgres_adapter=pg,
    telemetry_stream=producer,
)
```

## V2 Collection Versioning and Embedding Dimensions

The L3/L4 tiers support environment-driven collection isolation for embedding migrations.

- Current production REST/MCP runtime uses OpenRouter API embeddings:
  `qwen/qwen3-embedding-8b`, `EMBEDDING_DIMENSIONS=4096`, and
  `YAAM_PROJECT_ID=test`.
- Project-scoped default collections are derived from `YAAM_PROJECT_ID`.
    - L3 default: `yaam-test-episodes`
    - L4 default: `yaam-test`
- Explicit `MAS_L3_COLLECTION` / `MAS_L4_COLLECTION` values still override
  project-derived defaults for migrations and one-off admin runs.
- `EMBEDDING_DIMENSIONS` controls the effective vector size used by L3/Qdrant operations.
- Explicit tier config wins over the environment. For example,
  `EpisodicMemoryTier(..., config={"vector_size": 1536})` uses 1536 even when
  `EMBEDDING_DIMENSIONS=4096`.

For dimension-safe blue-green migrations, use a clean L3 base collection name or recreate the target
collection so the immutable Qdrant vector schema matches the configured embedding dimensions.

This configuration prevents dimensionality collisions when changing embedding providers
(for example, migrating from 768-dimension embeddings to 4096-dimension embeddings).

Qdrant remains a production L3 backend through `qdrant-client`. Local SentenceTransformer embeddings
are a legacy/offline path only and require `poetry install --with local-embeddings`; do not treat the
local embedding stack as required for production L3.
