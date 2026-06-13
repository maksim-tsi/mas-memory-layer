# YAAM: Yet Another Agents Memory

YAAM is a research prototype for governed long-term memory in LLM-based
agent systems. It exposes a memory layer behind REST and MCP interfaces and
separates volatile working context, episodic records, semantic facts, and
distilled knowledge assets into explicit tiers.

The repository is the public release companion for the YAAM paper. It contains
the implementation, tests, architecture decision records, interface contracts,
and reproducibility notes needed to inspect or extend the system.

## What Is Included

- `src/` - memory tiers, lifecycle engines, REST/MCP interfaces, agent wrappers,
  provider clients, and storage adapters.
- `tests/` - unit, contract, smoke, and integration-oriented test suites.
- `docs/ADR/` - architectural decisions for the memory model, API boundary,
  benchmark isolation, and agent integration layer.
- `docs/specs/` - implementation specifications for storage, memory tiers,
  agent integration, MCP, and observability contracts.
- `docs/reference/public-contracts.md` - public REST/MCP response contracts.
- `docs/research/` - curated research notes and comparative design context.
- `benchmarks/` - benchmark harness configuration and reporting skeletons.

Operational notebooks, raw run logs, private infrastructure notes, local virtual
environments, and customer-specific readiness traces are intentionally excluded
from this public tree.

## Architecture

YAAM is organized around four memory tiers:

1. Working memory for short-lived active state.
2. Episodic memory for durable event records.
3. Semantic memory for extracted facts and graph relationships.
4. Knowledge memory for distilled long-term artifacts.

The agent integration boundary is deliberately explicit: agents call memory
tools through a facade, while storage adapters remain behind tier and service
interfaces. This keeps policy experiments, prompts, retrieval strategy, and
benchmark wiring separate from low-level storage mechanisms.

Start with:

- `docs/ADR/003-four-layers-memory.md`
- `docs/ADR/007-agent-integration-layer.md`
- `docs/ADR/009-decoupling-benchmark-api-wall.md`
- `docs/ADR/011-agent-variant-evaluation-protocol.md`
- `docs/reference/public-contracts.md`

## Setup

YAAM uses Python 3.12+ and Poetry.

```bash
poetry install --with test,dev
```

Create a local `.env` from `.env.example` if you want to run against real
backends or external model providers. Do not commit `.env`.

```bash
cp .env.example .env
```

The default Docker Compose file is intended for local development:

```bash
docker compose up -d
```

## Verification

Use the repository-local virtual environment:

```bash
./.venv/bin/ruff check .
./.venv/bin/pytest tests/ --collect-only -q
./.venv/bin/pytest tests/ -v --ignore=tests/integration --ignore=tests/test_connectivity.py
```

Integration tests require configured Redis, PostgreSQL, Qdrant, Neo4j,
Typesense, and provider credentials. They are intentionally separated from the
default public smoke path.

## Public Release Scope

This public repository is a curated publication snapshot. The complete
development history, private operational notes, raw logs, and deployment
history are maintained separately by the authors.

## License

See `LICENSE`.
