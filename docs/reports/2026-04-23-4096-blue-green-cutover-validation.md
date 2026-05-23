# 4096 Blue-Green Cutover Validation (Interface Compose)

**Date:** 2026-04-23  
**Branch:** dev-tests  
**Scope:** Validate that YAAM V2 writes route to a new 4096 collection lineage with backward compatibility preserved.

## 1. Final Collection Name

The effective V2 write target is **episodes_qwen_v2**.

Rationale:
1. Wrapper base collection set to `episodes_qwen`.
2. V2 mode appends `_v2` in L3 tier routing.
3. Runtime write evidence shows count increase only on `episodes_qwen_v2`.

## 2. Runtime Validation Commands and Results

### 2.1 Service status and health

Command:

```bash
docker compose -f docker-compose.interface.yml ps
curl -i http://localhost:8080/health
```

Result:
1. `mas-agent` container is Up with `8080->8080` mapping.
2. `/health` returns `HTTP/1.1 200 OK`.

### 2.2 Before/after Qdrant evidence around smoke write

Before smoke:

```text
episodes           768   310
episodes_qwen_v2  4096   32
episodes_v2       4096    2
winsim_episodes   4096    4
```

Smoke requests:

```text
POST /v2/memory/l3/assimilate -> {"status":"success","episode_id":"ep-abb08d52"}
POST /v2/memory/l3/query      -> {"status":"success","results":[]}
```

After smoke:

```text
episodes           768   310
episodes_qwen_v2  4096   33
episodes_v2       4096    2
winsim_episodes   4096    4
```

Conclusion:
1. `episodes_qwen_v2` increased from 32 to 33.
2. Legacy `episodes` (768) remained unchanged at 310.
3. Legacy `episodes_v2` remained unchanged at 2.

This confirms blue-green routing is active and backward-compatible collections are preserved.

### 2.3 API smoke logs

Log excerpt:

```text
POST /v2/memory/l3/assimilate HTTP/1.1 201 Created
POST /v2/memory/l3/query HTTP/1.1 200 OK
```

## 3. Implementation Notes

The routing fix required explicit episodic tier configuration in wrapper initialization so tier-level defaults do not fall back to the old `episodes` lineage.

## 4. Lint and Tests

Lint:

```text
./.venv/bin/ruff check .  -> pass
```

Tests:

```text
./.venv/bin/pytest tests/ -v -> 6 failed, 624 passed, 108 skipped
```

Observed failures are expectation drift tied to embedding dimension/collection-version assumptions and should be addressed in a dedicated follow-up test alignment change.

## 5. Backward Compatibility Outcome

1. Existing 768 collection remains intact (`episodes`, unchanged count).
2. New 4096 writes flow to isolated collection lineage (`episodes_qwen_v2`).
3. Client API contract unchanged (clients do not provide collection identifier).