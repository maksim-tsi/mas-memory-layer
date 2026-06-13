# Python Environment Guide (Consolidated)

**Status:** Active reference for Python environment setup and compatibility

This document consolidates the legacy `python-environment-setup.md` and
`python-3.13-compatibility.md` into a single guide. It reflects the repository's
Poetry-based workflow and the external benchmark layout.

---

## Poetry Environments

YAAM and the GoodAI benchmark use isolated Poetry environments:

1. **Root environment (MAS Memory Layer)**
   - Location: this repository root
   - Command: `poetry install --with test,dev`
   - Virtualenv: `.venv/`

2. **Benchmark environment (GoodAI LTM Benchmark for YAAM)**
   - Location: external checkout of `git@github.com-skazo4ny:maksim-tsi/goodai-ltm-benchmark-yaam.git`
   - Command: `poetry install`
   - Virtualenv: `.venv/` inside the benchmark repository

Keep these environments separate to avoid dependency conflicts.

---

## System Prerequisites

### PostgreSQL Client Tools

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install -y postgresql-client
psql --version
```

**macOS:**
```bash
brew install postgresql
psql --version
```

**Windows:**
- Install WSL2 and follow Ubuntu instructions, OR
- Download PostgreSQL from https://www.postgresql.org/download/windows/

---

## Root Environment Setup (MAS Memory Layer)

```bash
# From repository root
poetry install --with test,dev

# Verify interpreter path
./.venv/bin/python -c "import sys; print(sys.executable)"
```

Use `./.venv/bin/python` for deterministic execution in scripts and CI.

---

## Benchmark Environment Setup (GoodAI LTM Benchmark)

```bash
cd ../goodai-ltm-benchmark-yaam
poetry install

# Verify interpreter path
./.venv/bin/python -c "import sys; print(sys.executable)"
```

Run benchmark scripts from within the benchmark repository and use its `.venv`.

---

## Python 3.13 Compatibility Notes

If you encounter build errors when installing dependencies on Python 3.13, this is
likely due to `asyncpg` requiring compilation.

### Error
```
error: command '/usr/bin/gcc' failed with exit code 1
```

### Recommended Approach

This project uses `psycopg[binary]` instead of `asyncpg`, so builds should succeed
without compilation. Keep Poetry dependencies aligned with `pyproject.toml`.

If you need to work with `asyncpg`, install build tools and pin a compatible
version manually, but prefer the default `psycopg` setup.

---

## Smoke Validation

```bash
./.venv/bin/python scripts/test_llm_providers.py --help
./scripts/run_smoke_tests.sh --summary
```

On managed remote hosts, follow `docs/environment-guide.md` for absolute paths.
