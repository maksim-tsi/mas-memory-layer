# AGENT PROTOCOL 1.1 (Harness-first)

This repository is developed with coding assistants (Codex, GitHub Copilot, Claude Code, Gemini CLI).
Our goal is to maximize agent throughput **without architectural drift** by enforcing a small set of
non-negotiable invariants and by keeping repository knowledge **legible** and **versioned**.

This file is intentionally short. Treat it as a **map** (table of contents + golden rules), not an
encyclopedia. If you need detail, follow the pointers in **Where to look**.

## Instruction Hierarchy (Single Source of Truth)

1. `AGENTS.MD` (this file): canonical workflow + safety invariants.
2. `.github/copilot-instructions.md`: Copilot entrypoint; must not contradict `AGENTS.MD`.
3. `.github/instructions/*.md`: path-scoped implementation guidelines (source/tests/docs/scripts).
4. `docs/`: system-of-record for architecture, ADRs, plans, and runbooks.

If you find a conflict between any of the above, **stop** and ask the user to resolve it, then record
the resolution in `docs/lessons-learned.md`.

## Clarifications for Codex (Sandbox + Network)

These notes exist because the **Codex app/CLI runtime** may be sandboxed differently than VS Code
agents or other CLIs.

- **Network access:** If a command requires network access, Codex may need explicit user approval
  even when it would normally work on your machine.
- **Allowed network usage (user-approved):**
  - Local network access is allowed for DBMS connector integration tests.
  - Public internet access is allowed for LLM provider tests/runtime calls.
  - If you expect to exceed **10 requests/minute** to an LLM provider or **1000 requests/day**,
    stop and ask first.
- **Git operations:** some `git` commands may require explicit approval because they write to `.git/`.

## Where to Look (Progressive Disclosure)

- Architecture: `docs/ADR/003-four-layers-memory.md`, `docs/ADR/007-agent-integration-layer.md`
- Benchmark isolation (“API Wall”): `docs/ADR/009-decoupling-benchmark-api-wall.md`
- Environment expectations: `docs/environment-guide.md`
- Coding patterns (src): `.github/instructions/source.instructions.md`
- Testing patterns (tests): `.github/instructions/testing.instructions.md`
- Documentation patterns (docs): `.github/instructions/documentation.instructions.md`
- Shell script patterns (scripts): `.github/instructions/scripts.instructions.md`
- Incident log: `docs/lessons-learned.md`

## Golden Rules (Do these by default)

### 1) Verify host + choose the correct venv executables

Run (single command):

```bash
uname -a && hostname && pwd
```

- Local checkout: use `./.venv/bin/python`, `./.venv/bin/pytest`, `./.venv/bin/ruff`
- Remote host (`/home/max/code/mas-memory-layer`): use `/home/max/code/mas-memory-layer/.venv/bin/...`

**Stateless shell rule:** do **not** `source .venv/bin/activate`. Activation will not persist.

### 2) Lint before tests; run commands without output redirection

1. `./.venv/bin/ruff check .`
2. `./.venv/bin/pytest tests/ -v`

Do not use output redirection (`> /tmp/...`) as a default pattern.

### 3) Change boundaries (prevent “layer jumping”)

Default expectation:
- **Mechanism (frozen-by-default):** `src/storage/` (DB adapters) and other low-level connectors.
- **Policy / behavior (iterated):** agent prompts, skills, orchestration, benchmark harness, docs.

Do **not** modify the mechanism layer unless the user explicitly asks or explicitly authorizes it for
the current task. If you suspect a mechanism bug, escalate with evidence (tests/logs) and ask.

### 4) Dependency changes require explicit approval

Do not add/remove/update dependencies (Poetry, `pyproject.toml`, lockfiles) unless the user gives
explicit permission for that specific change.

### 5) Test discipline (avoid “fix tests by editing tests”)

- After any code change in `src/`, run the full suite: `./.venv/bin/pytest tests/ -v`
- If tests fail, fix application code in `src/` first.
- Do not modify `tests/` unless the user explicitly tells you to update/fix tests or write new tests.

### 6) Mocking policy

Use `pytest-mock` (`mocker` fixture). Do not import `unittest.mock` directly in tests.

### 7) Secrets boundary

Do not read, write, print, or request the contents of `.env` (or any secret files/keys).

## Environment Verification Sequence (Required before lint/tests)

1. Confirm `.venv/` exists at repo root.
2. If missing: run `poetry install --with test,dev`.
3. Verify interpreter:
   - `./.venv/bin/python -c 'import sys; print(sys.executable)'`
   - Output must point to this repo’s `.venv/bin/python`. If not, stop and escalate.

Two Poetry projects exist by design:
- YAAM root project: Python `>=3.12,<3.14` (see `pyproject.toml`)
- GoodAI benchmark: Python `>=3.11,<3.13` (see `benchmarks/goodai-ltm-benchmark/pyproject.toml`)

## Error Handling (3-attempt loop + escalation)

You may attempt up to **3** autonomous fix iterations per failure.
On each iteration you must:
1. State a hypothesis for the failure.
2. State the exact change you will make.
3. Make the change.
4. Re-run the verification command (ruff/pytest) and inspect output.

Escalate to the user immediately if:
- The problem is ambiguous or under-specified.
- A protected area must be modified (see below) without explicit user authorization.
- You hit a Pydantic `ValidationError` that requires missing/corrected data.
- You cannot find an expected entity and would otherwise create a new one.

## Pydantic v2 ValidationError Protocol

When a `pydantic.ValidationError` occurs:
1. Parse which fields failed and why (missing/type/constraint).
2. Report all invalid fields together.
3. Ask the user for the missing/correct information (do not “retry blindly”).

## Pathing Protocol

- Tools may use absolute filesystem paths when required.
- Repository artifacts (docs/code/config) must not hardcode absolute paths.
- When describing edits, use logical repo paths (relative), not machine-specific absolute paths.

## Protected Areas (require explicit user authorization)

- `.git/`
- `.env`, any `*.key`, `*.pem`, `*.secret`
- `pyproject.toml`, `poetry.lock`
- `.github/` (workflows/instructions)
- `.venv/` and other virtual environments

## Incident Register

Document instruction conflicts and other workflow incidents (and mitigations) in `docs/lessons-learned.md`.
