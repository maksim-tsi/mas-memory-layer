# Archived Legacy Code

This directory contains legacy code that has been superseded by the current architecture but is preserved for historical reference.

## Why Archived?

These files were created during early development but conflict with the current project architecture (ADR-003):

| File | Issue | Replacement |
|------|-------|-------------|
| `graph_store_client.py` | Synchronous Neo4j client | `src/storage/neo4j_adapter.py` (async) |
| `vector_store_client.py` | Synchronous Qdrant client | `src/storage/qdrant_adapter.py` (async) |
| `search_store_client.py` | Uses Meilisearch | `src/storage/typesense_adapter.py` (Typesense per ADR-003) |
| `knowledge_store_manager.py` | Facade using all above legacy clients | Tier-specific adapters in `src/storage/` |

## Architectural Decisions

1. **Async-first**: All storage adapters in `src/storage/` use async interfaces for better performance in the multi-agent system.

2. **Typesense over Meilisearch**: ADR-003 specifies Typesense for L4 semantic memory due to its better support for the project's search requirements.

3. **Proper module structure**: Storage adapters belong in `src/storage/` with consistent interfaces, not as standalone root-level scripts.

## Dependencies

Note: `knowledge_store_manager.py` depends on the other three files in this directory. It is still imported by `src/memory/unified_memory_system.py` via path manipulation for backward compatibility.

## Do Not Use

These files should NOT be used for new development. Use the canonical adapters in `src/storage/` instead.
