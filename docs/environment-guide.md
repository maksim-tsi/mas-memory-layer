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
- **Remote Ubuntu via SSH** – `uname` prints `Linux`, `hostname` typically includes the jumpbox label (for example, `development-host`), and `pwd` resolves to `<repo>`. Follow the repository instructions that reference `<repo>/.venv/bin/...`.
- **Local Ubuntu desktop/RDP** – `uname` prints `Linux`, `hostname` matches the physical workstation, and `pwd` resolves to `/home/<user>/Documents/code/mas-memory-layer`. Use the relative-path commands from this document to keep scripts portable.

Document the answers in the worklog when switching contexts so that reviewers understand which interpreter produced a given artifact.

## 2. Create or Refresh the Poetry Environments

YAAM and the GoodAI benchmark use isolated Poetry environments:

1. **Root environment (MAS Memory Layer)**  
   - Location: repository root  
   - Command: `poetry install --with test,dev`  
   - Virtualenv: `.venv/`
   - Optional legacy/offline embeddings: add `--with local-embeddings` only when explicitly testing
     the local SentenceTransformer path. Production REST/MCP runtime does not install this group.

2. **Benchmark environment (GoodAI LTM Benchmark for YAAM)**
   - Location: external checkout of `git@github.com-skazo4ny:maksim-tsi/goodai-ltm-benchmark-yaam.git`
   - Command: `poetry install`  
   - Virtualenv: `.venv/` inside the benchmark repository

Keep these environments separate to avoid dependency conflicts.

## 3. Install Dependencies Deterministically

Run the appropriate Poetry install command from the correct directory.

**Root environment:**
```bash
poetry install --with test,dev
```

Do not install the optional local embedding stack by default. Use it only for legacy/offline
SentenceTransformer experiments:

```bash
poetry install --with test,dev,local-embeddings
```

Production YAAM runtime uses provider API embeddings, currently OpenRouter
`qwen/qwen3-embedding-8b` with `EMBEDDING_DIMENSIONS=4096`, and Qdrant through `qdrant-client`.

**Benchmark environment:**
```bash
cd ../goodai-ltm-benchmark-yaam
poetry install
```

## 4. Verify Interpreter Selection

Run the diagnostic below immediately after installing requirements. The printed path must resolve to `.venv/bin/python` within the repository you are touching.

```bash
./.venv/bin/python -c "import sys; print(sys.executable)"
```

When working on the remote Ubuntu host that mandates absolute paths, the equivalent command is:

```bash
<repo>/.venv/bin/python -c "import sys; print(sys.executable)"
```

If the output differs, restart the session and recreate the environment. Continuing with the wrong interpreter will pollute system packages or CI caches.

## 5. Smoke Validation Prior to Development

After the interpreter check passes, run the lightweight diagnostics to confirm that provider credentials and storage clients are visible:

```bash
./.venv/bin/python scripts/test_llm_providers.py --help
./scripts/run_smoke_tests.sh --summary
```

For remote hosts replace the interpreter path with `<repo>/.venv/bin/python` if required by operations.

## 6. Relative vs. Absolute Paths

- Use **relative paths** (`./.venv/bin/python`, `./scripts/...`) in documentation and shared snippets. These commands succeed on macOS, local Ubuntu, and most CI runners.
- Use **absolute paths** only when interacting with the managed remote environment that enforces `<repo>/.venv/bin/...`. When documenting such commands, explicitly note the host requirement.

Maintaining both forms prevents accidental edits to the remote interpreter while still honouring operational safeguards.

## 7. Checklist for Context Switching

1. Probe environment (`uname`, `hostname`, `pwd`).
2. Confirm `.venv/` exists at repository root; recreate if necessary.
3. Install dependencies with Poetry in the correct directory (root or benchmark).
4. Run the interpreter verification command.
5. Execute provider/tests smoke checks relevant to the tasks you intend to perform.
6. Record the host type in commit messages or DEVLOG entries when the environment influences results.

Following this sequence keeps all contributors aligned regardless of platform, which is a prerequisite for shipping the multi-tier LLM lifecycle engines in Phase 2B and beyond.
