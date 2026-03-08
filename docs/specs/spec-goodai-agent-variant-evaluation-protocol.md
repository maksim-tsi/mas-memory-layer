# Specification: GoodAI Agent Variant Evaluation Protocol (API Wall)

**Status:** Draft  
**Date:** February 21, 2026  
**Audience:** Maintainers, benchmark operators, coding assistants  
**Related:** ADR-009, ADR-010, ADR-011

## 1. Scope

This specification defines how YAAM agents are evaluated with the GoodAI LTM Benchmark under an
API Wall constraint, using explicit agent variants.

It covers:

- variant naming and selection,
- entrypoints and environment variables,
- state isolation (session prefixes),
- logging and artifact requirements,
- and the minimum tests required for evaluation correctness.

It does not define benchmark dataset details or scoring; those remain owned by the GoodAI runner.

## 2. Variant Identity

### 2.1 Variant fields

Each evaluation run MUST record:

- `agent_type` (e.g., `full`, `rag`, `full_context`)
- `agent_variant` (e.g., `v1-min-skillwiring`, `v2-adv-toolgated`)
- `agent_id` (runtime identifier; recommended format: `mas-<agent_type>__<agent_variant>`)

### 2.2 Canonical variant slug format (normative)

`agent_variant` MUST be a stable slug with the following constraints:

- lowercase ASCII letters, digits, and hyphens only,
- no spaces,
- versioned when semantics change (e.g., `v1-...`, `v2-...`),
- describes behavior at the policy layer (skills wiring, tool gating, routing), not infrastructure.

Examples:

- `baseline`
- `v1-min-skillwiring`
- `v2-adv-toolgated`

### 2.3 Variant selection without API changes

The benchmark runner selects the variant by choosing a different API Wall base URL. The API
surface remains unchanged; only the deployment target differs.

Recommended pattern:

- Variant A API Wall: `http://<host>:8081/v1/chat/completions`
- Variant B API Wall: `http://<host>:8082/v1/chat/completions`

## 3. Entrypoints

### 3.1 API Wall (OpenAI-compatible)

Primary evaluation endpoint:

- `POST /v1/chat/completions`

Operational endpoints (for test orchestration and cleanup):

- `GET /health`
- `POST /control/session/reset` (requires `X-Session-Id`)

### 3.2 Service entrypoints (YAAM API Wall) (normative)

The recommended operational model is “one variant per service instance”:

- **Instance identity:** `MAS_AGENT_TYPE=<type>`, `MAS_AGENT_VARIANT=<variant>`
- **Selection:** the GoodAI runner selects the instance using `AGENT_URL`
- **Isolation:** each instance prefixes sessions using `<agent_type>__<agent_variant>:...`

Example (two variants of the same agent type):

```bash
# Variant A on port 8081
MAS_PORT=8081 MAS_AGENT_TYPE=full MAS_AGENT_VARIANT=v1-min-skillwiring \
  ./.venv/bin/uvicorn src.server:app --host 0.0.0.0 --port 8081

# Variant B on port 8082
MAS_PORT=8082 MAS_AGENT_TYPE=full MAS_AGENT_VARIANT=v2-adv-toolgated \
  ./.venv/bin/uvicorn src.server:app --host 0.0.0.0 --port 8082
```

### 3.2 Wrapper (optional direct endpoint)

For diagnostic runs, the internal wrapper endpoint may be used:

- `POST /run_turn`

However, official benchmark runs MUST use the API Wall path to preserve ADR-009 semantics.

### 3.3 Benchmark runner entrypoints (GoodAI) (normative)

The benchmark runner MUST be invoked with agent `mas-remote` and MUST set `AGENT_URL` to the
variant-specific API Wall instance.

The runner MUST include `<agent_type>__<agent_variant>` in `--run-name` so that filesystem
artifacts are variant-scoped.

Example:

```bash
cd benchmarks/goodai-ltm-benchmark

AGENT_URL="http://localhost:8081/v1/chat/completions" \
  poetry run python -m runner.run_benchmark \
    -c configurations/mas_remote_test.yml \
    -a mas-remote \
    --run-name "goodai__full__v1-min-skillwiring"
```

For consistent naming, the repository also provides an optional helper entrypoint:
`scripts/run_goodai_remote_variant.sh`.

## 4. Environment Variables (Normative)

The API Wall service MUST support:

- `MAS_AGENT_TYPE` (default: `full`)
- `MAS_AGENT_VARIANT` (default: `baseline`)
- `MAS_PORT` (default: `8080`)
- `MAS_MODEL` (default: `gemini-3-flash-preview`)
- `REDIS_URL` (required)
- `POSTGRES_URL` (required)
- `MAS_L1_WINDOW`, `MAS_L1_TTL_HOURS`, `MAS_MIN_CIAR` (optional)

The benchmark runner MUST support:

- `AGENT_URL` pointing to `http://<host>:<port>/v1/chat/completions`

## 5. State Isolation (Normative)

All session IDs MUST be prefixed using:

`<agent_type>__<agent_variant>:<session_id>`

This requirement prevents cross-run contamination when multiple variants share the same Redis and
Postgres backends.

## 6. Logging and Artifacts (Normative)

Every run MUST produce:

1. **Benchmark outputs** (GoodAI runner native artifacts; store the output directory path in the report).
2. **API Wall logs** including:
   - errors and exceptions (per request),
   - per-turn timing metadata (storage pre/post and LLM time).
3. **Rate limiter JSONL** produced by the wrapper:
   - `logs/rate_limiter_<agent_type>_<agent_variant>_<timestamp>.jsonl`

The report MUST include:

- git commit hash of YAAM code,
- git commit hash/version of GoodAI benchmark runner,
- model name, temperature, and provider,
- and the variant identity fields from §2.

## 7. Execution Modes

### 7.1 Minimal wiring (v1)

Definition:

- load a selected `skill_slug` per turn,
- inject the skill body into the LLM `system_instruction`,
- prepare toolset gating from `allowed-tools` (even if tool calling is not yet enabled),
- do not introduce a dynamic router.

### 7.2 Advanced wiring (v2)

Definition:

- enforce hard tool gating at execution time: the agent can only call tools listed in `allowed-tools`,
- optionally add a manual skill selector node (no automatic router in v2 unless explicitly studied),
- and integrate real tool calling (DBMS calls via adapters exposed as tools, plus LLM calls).

## 8. Required Tests (Minimum Set)

### 8.1 Unit tests

- Variant prefixing and health exposure:
  - `/health` returns `agent_type` and `agent_variant`.
  - session prefix is stable and idempotent.
- Skill loader correctness:
  - list skills, load skill frontmatter/body, and validate `allowed-tools`.

### 8.2 Integration tests (network-enabled host)

- Connectivity and adapters:
  - `./.venv/bin/pytest -v --run-integration tests/integration/test_connectivity.py`
  - `./.venv/bin/pytest -v --run-integration -m integration tests/storage`
- Provider calls (rate-limited):
  - enable `--run-slow` and run a minimal real-provider call suite.

### 8.3 Benchmark smoke test

- Run a single small dataset or reduced manifest against each variant to confirm:
  - the API Wall is reachable,
  - sessions are isolated,
  - and per-turn errors are captured.
