# Environment Detection and Bootstrap Guide

**Status:** Living document (last updated: 2025-11-15)

This guide documents the workflow required to keep development environments consistent across macOS laptops, local Ubuntu workstations, and remote Ubuntu hosts accessed over SSH. The goal is to ensure every contributor executes the same commands regardless of their entry point, preventing the class of bugs caused by installing dependencies into the wrong interpreter or running scripts outside the repository root.

## 1. Identify the Host Context

Begin every session by executing the short probe below. The responses reveal whether the shell is running on macOS (`Darwin`), a remote Ubuntu VM, or a local Ubuntu desktop session.

```bash
uname -a
hostname
pwd
```

Interpretation:

- **macOS local checkout** – `uname` prints `Darwin` and `pwd` resolves to `/Users/<name>/Documents/code/mas-memory-layer` (or similar). Use the `./.venv/bin/...` commands documented below.
- **Remote Ubuntu via SSH** – `uname` prints `Linux`, `hostname` typically includes the jumpbox label (for example, `skz-dev-lv`), and `pwd` resolves to `/home/max/code/mas-memory-layer`. Follow the repository instructions that reference `/home/max/code/mas-memory-layer/.venv/bin/...`.
- **Local Ubuntu desktop/RDP** – `uname` prints `Linux`, `hostname` matches the physical workstation, and `pwd` resolves to `/home/<user>/Documents/code/mas-memory-layer`. Use the relative-path commands from this document to keep scripts portable.

Document the answers in the worklog when switching contexts so that reviewers understand which interpreter produced a given artifact.

## 2. Create or Refresh the Virtual Environment

Regardless of platform, the virtual environment belongs at the repository root and should be created via a relative path. This guarantees that both macOS and Linux instructions remain valid.

```bash
python3 -m venv .venv
```

If you must recreate the environment, delete `.venv/` completely (`rm -rf .venv`) before rerunning the command above.

## 3. Install Dependencies Deterministically

Install requirements using the interpreter that lives inside `.venv`. Never rely on whichever `pip` happens to be on the `PATH`.

```bash
./.venv/bin/pip install -r requirements.txt
./.venv/bin/pip install -r requirements-test.txt
```

This sequence ensures:

1. Runtime packages such as `python-dotenv`, `psycopg_pool`, and the storage/LLM clients are always present.
2. Test infrastructure (`pytest`, `pytest-asyncio`) is available before executing any suite.
3. The installation log is confined to the repository, which simplifies reproducibility checks.

## 4. Verify Interpreter Selection

Run the diagnostic below immediately after installing requirements. The printed path must resolve to `.venv/bin/python` within the repository you are touching.

```bash
./.venv/bin/python -c "import sys; print(sys.executable)"
```

When working on the remote Ubuntu host that mandates absolute paths, the equivalent command is:

```bash
/home/max/code/mas-memory-layer/.venv/bin/python -c "import sys; print(sys.executable)"
```

If the output differs, restart the session and recreate the environment. Continuing with the wrong interpreter will pollute system packages or CI caches.

## 5. Smoke Validation Prior to Development

After the interpreter check passes, run the lightweight diagnostics to confirm that provider credentials and storage clients are visible:

```bash
./.venv/bin/python scripts/test_llm_providers.py --help
./scripts/run_smoke_tests.sh --summary
```

For remote hosts replace the interpreter path with `/home/max/code/mas-memory-layer/.venv/bin/python` if required by operations.

## 6. Relative vs. Absolute Paths

- Use **relative paths** (`./.venv/bin/python`, `./scripts/...`) in documentation and shared snippets. These commands succeed on macOS, local Ubuntu, and most CI runners.
- Use **absolute paths** only when interacting with the managed remote environment that enforces `/home/max/code/mas-memory-layer/.venv/bin/...`. When documenting such commands, explicitly note the host requirement.

Maintaining both forms prevents accidental edits to the remote interpreter while still honouring operational safeguards.

## 7. Checklist for Context Switching

1. Probe environment (`uname`, `hostname`, `pwd`).
2. Confirm `.venv/` exists at repository root; recreate if necessary.
3. Install `requirements.txt` and `requirements-test.txt` via the `.venv` interpreter.
4. Run the interpreter verification command.
5. Execute provider/tests smoke checks relevant to the tasks you intend to perform.
6. Record the host type in commit messages or DEVLOG entries when the environment influences results.

Following this sequence keeps all contributors aligned regardless of platform, which is a prerequisite for shipping the multi-tier LLM lifecycle engines in Phase 2B and beyond.
