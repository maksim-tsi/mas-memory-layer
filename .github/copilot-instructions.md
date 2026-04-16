# MAS Memory Layer (YAAM) — Copilot Entrypoint

This file is optimized for GitHub Copilot. It must remain consistent with `AGENTS.MD`.
If you observe a conflict, stop and ask the user to resolve it, then log the resolution in
`docs/lessons-learned.md`.

## Golden Rules (Read First)

1. **Use the repo venv executables; never activate.**
   - Local: `./.venv/bin/python`, `./.venv/bin/pytest`, `./.venv/bin/ruff`
   - Remote: `/home/max/code/mas-memory-layer/.venv/bin/...`
   - Do not run `source .venv/bin/activate` (stateless shell).

2. **No output redirection by default.**
   - Run commands directly (no `> /tmp/...` chaining).

3. **Lint before tests; run full tests after `src/` changes.**
   - `./.venv/bin/ruff check .`
   - `./.venv/bin/pytest tests/ -v`
   - Fix application code in `src/` first; do not “fix failures” by editing tests unless asked.

4. **Prevent “layer jumping”.**
   - Treat `src/storage/` (DB adapters) as **Mechanism** (frozen-by-default).
   - Treat skills/prompts/agent orchestration as **Policy** (iterated).
   - Do not modify mechanism code unless explicitly requested or explicitly authorized.

5. **Dependencies and secrets are controlled.**
   - Do not modify `pyproject.toml` / `poetry.lock` unless explicitly authorized.
   - Do not read, print, or request `.env` contents.

6. **Mocking policy (tests):**
   - Use `pytest-mock` (`mocker` fixture). Do not import `unittest.mock` directly.

## Clarifications for Codex (Sandbox + Network)

These notes are **Codex-runtime-specific** (the Codex app/CLI may be sandboxed differently than
VS Code or other agent runtimes).

- **Network access:** Codex may require explicit user approval for networked commands.
- **Allowed network usage (user-approved):**
  - Local network access is allowed for DBMS connector integration tests.
  - Public internet access is allowed for LLM provider tests/runtime calls.
  - If you expect to exceed **10 requests/minute** to an LLM provider or **1000 requests/day**,
    stop and ask first.
- **Git operations:** some `git` commands may require explicit approval because they write to `.git/`.

## Repository Map (Progressive Disclosure)

- Canonical harness rules: `AGENTS.MD`
- Architecture (4-tier memory): `docs/ADR/003-four-layers-memory.md`
- LangGraph tool injection (`ToolRuntime`): `docs/ADR/007-agent-integration-layer.md`
- Benchmark isolation (“API Wall”): `docs/ADR/009-decoupling-benchmark-api-wall.md`
- Environment guide: `docs/environment-guide.md`
- Path-scoped guidelines:
  - Source: `.github/instructions/source.instructions.md`
  - Tests: `.github/instructions/testing.instructions.md`
  - Docs: `.github/instructions/documentation.instructions.md`
  - Scripts: `.github/instructions/scripts.instructions.md`

## Python Environments (Poetry)

- YAAM (repo root): Python `>=3.12,<3.14` (see `pyproject.toml`)
- GoodAI benchmark (`benchmarks/goodai-ltm-benchmark/`): Python `>=3.11,<3.13` (separate Poetry project)
