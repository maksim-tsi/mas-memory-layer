# YAAM Redis Namespace Audit

## 1. Key Prefixes
YAAM uses a **Redis Cluster Hash Tag** pattern for its key prefixes to ensure cluster safety (guaranteeing related keys collocate to the same cluster slot). There is no single global `yaam:` prefix. Instead, keys are partitioned into session-scoped and system-scoped namespaces.

*   **Session-scoped keys** use the Hash Tag `{session:<session_id>}`:
    *   L1 Active Context: `{session:<session_id>}:turns`
    *   Personal State: `{session:<session_id>}:agent:<agent_id>:state`
    *   Shared Workspace: `{session:<session_id>}:workspace`
    *   L2 Facts Index: `{session:<session_id>}:facts:index`
*   **System-scoped keys** use the Hash Tag `{mas}`:
    *   Lifecycle Stream: `{mas}:lifecycle`

**Relevant Code Snippet (`src/memory/namespace.py`):**
```python
class NamespaceManager:
    @staticmethod
    def l1_turns(session_id: str) -> str:
        return f"{{session:{session_id}}}:turns"

    @staticmethod
    def lifecycle_stream() -> str:
        return "{mas}:lifecycle"
```

## 2. Database Index
YAAM defaults to **logical database index 0** if no specific database is provided in the configuration. It relies primarily on its Hash Tag prefixes for logical separation rather than separate database indices.

**Relevant Code Snippet (`src/storage/redis_adapter.py`):**
```python
    def __init__(self, config: dict[str, Any]):
        # ...
        self.db = config.get("db", 0)
```

## 3. Configuration
The Redis connection is configured via standard environment variables (e.g., in `.env`). The primary variables controlling the connection are `REDIS_URL`, `REDIS_HOST`, and `REDIS_PORT`. 

The key prefix structure is **hardcoded** in the `NamespaceManager` and cannot be overridden via environment variables. The logical database index defaults to 0 but can be overridden by appending the database number to the `REDIS_URL` connection string (e.g., `redis://host:port/1`).

**Relevant Code Snippet (`.env.example`):**
```env
# --- Redis (Dev Node: skz-dev-lv) ---
REDIS_HOST=${DEV_NODE_IP}
REDIS_URL=redis://${DEV_NODE_IP}:${REDIS_PORT}
```
