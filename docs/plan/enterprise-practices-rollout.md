# Enterprise Practices Rollout Plan

## 1. Purpose
This document defines a staged adoption plan for enterprise software development practices in the MAS Memory Layer repository. The plan prioritizes reproducibility, test-driven development, and operational safety, while keeping the GoodAI benchmark integration academically rigorous and non-invasive.

## 2. Guiding Principles
- **Test-first adoption**: New features, including benchmark visibility improvements, require tests to be authored before implementation.
- **Local-first enforcement**: Quality gates (linting, coverage, type checks) run through local scripts to avoid remote CI dependency.
- **Incremental hardening**: Type safety and coverage enforcement are introduced in stages to avoid destabilizing ongoing work.
- **Academic integrity**: Benchmark datasets and evaluation logic remain unchanged.

## 3. Staged Rollout

### Stage 1 — Foundation (Target: 2026-02-10)
**Objective:** Establish configuration baselines and lightweight safeguards.

**Planned actions:**
- [x] Add unified tool configuration in `pyproject.toml`.
- [x] Add pre-commit hooks for large-file protection, ruff, and staged mypy.
- [x] Update local test script to enforce coverage minimums.
- [x] Enforce 80% coverage in local test scripts.
- [ ] Generate a reproducible dependency lock file (`requirements-lock.txt`).

**Tracking notes:**
- Coverage enforcement must be added to all local test entrypoints.
- Lock file generation requires approval before dependency changes.

### Stage 2 — Type Safety (Core Modules) (Target: 2026-02-17)
**Objective:** Introduce mypy in core memory and storage modules.

**Planned actions:**
- [ ] Enable mypy enforcement on `src/memory/`.
- [ ] Enable mypy enforcement on `src/storage/`.
- [ ] Remediate identified typing defects.

### Stage 3 — Type Safety (Agent Modules) (Target: 2026-02-24)
**Objective:** Extend mypy coverage to agent and evaluation layers.

**Planned actions:**
- [ ] Expand mypy scope to `src/agents/`.
- [ ] Expand mypy scope to `src/evaluation/`.
- [ ] Remediate typing defects introduced by expanded scope.

### Stage 4 — Benchmark Visibility Tests (Target: 2026-03-03)
**Objective:** Apply TDD to the GoodAI benchmark visibility improvements.

**Planned actions:**
- [ ] Add pytest tests for `tqdm` headless progress output.
- [ ] Add tests for per-turn JSONL telemetry output.
- [ ] Add tests for the stuck-run watchdog and `run_error.json` emission.

### Stage 5 — Coverage Enforcement (Target: 2026-03-10)
**Objective:** Enforce coverage gates across local test scripts.

**Planned actions:**
- [ ] Require `--cov-fail-under=80` across local scripts.
- [ ] Document coverage expectations in developer docs.

## 4. Tracking Table

| Stage | Status | Completed | Notes |
|------:|:------:|:---------:|------|
| 1. Foundation | 🚧 In Progress | 2026-02-04 | Configuration and hooks established; coverage enforced in local test scripts |
| 2. Type Safety (Core) | ⏳ Pending | - | Scoped to memory/storage modules |
| 3. Type Safety (Agents) | ⏳ Pending | - | Expand to agents/evaluation |
| 4. Benchmark Visibility Tests | ⏳ Pending | - | TDD for progress/telemetry/watchdog |
| 5. Coverage Enforcement | ⏳ Pending | - | 80% minimum across scripts |

## 5. Evidence and References
- Configuration baseline: `pyproject.toml`
- Pre-commit hooks: `.pre-commit-config.yaml`
- Test scripts: `scripts/run_tests.sh`, `scripts/run_smoke_tests.sh`, `scripts/run_memory_integration_tests.sh`
- Benchmark visibility docs: external `goodai-ltm-benchmark-yaam` repository, `docs/visibility-analysis.md` and `docs/improvement-plan.md`

## 6. Implementation Log

### 2026-02-04
- Created `pyproject.toml` with pytest, ruff, mypy, and coverage settings.
- Extended `.pre-commit-config.yaml` with ruff and staged mypy checks.
- Updated `scripts/run_tests.sh` to use absolute venv executables and enforce `--cov-fail-under=80`.
- Updated `scripts/run_smoke_tests.sh`, `scripts/run_memory_integration_tests.sh`, `scripts/run_wrapper_tests.sh`, and `scripts/run_redis_tests.sh` to enforce coverage and avoid virtual environment activation.
- Added TDD placeholder tests for benchmark visibility features in the external benchmark repository.
