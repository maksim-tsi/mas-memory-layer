# CI/CD Maturity Report — `mas-memory-layer` (2026-02-14)

## 1) Executive Summary

The repository contains **documented intent** to keep `main` stable and do day-to-day work on a development branch (e.g., `dev`, and later `dev-mas`), but **the mechanics that make this “best practice” real are not implemented**:

- **No GitHub Actions workflows exist** (there is no `.github/workflows/` directory), so there is **no CI gate** on pull requests or merges.
- There is **no automated promotion path** (dev → QA → prod) implemented in-repo; deployments appear to be **manual**, based on Docker/Docker Compose and runbooks in `docs/IAC/`.
- `origin/HEAD` points to **`main` as the default branch**, which conflicts with the README statement “All development happens on the `dev` branch.”
- The git history shows **multiple long-lived “dev-*” branches** (`dev`, `dev-mas`, `dev-tests`, `dev-codex`), indicating an **evolving but not yet standardized** branching model.

Net: the repo is closer to **“local quality tooling + documented workflow”** than to **“enforced CI + environment promotion + release-only main.”**

## 2) Scope, Method, and Limitations

**Method:** Static analysis of repository contents and local git metadata (branches, tags, recent history), including documentation in `README.md`, `DEVLOG.md`, and planning documents in `docs/`.

**Limitations:** Branch protection rules, required checks, GitHub Environments (QA/prod), deployment secrets, and approval gates are configured in GitHub settings and are **not visible** from the repository checkout alone. Therefore, this report can only assert what is (or is not) present in the repo itself.

## 3) Current State (Observed)

### 3.1 Branching and “Never Develop in Main”

**What is documented**
- `README.md` states: “All development happens on the `dev` branch” and “Keep `main` stable.”
- `DEVLOG.md` (2025-10-20 entry) explicitly states: “All new development should happen on `dev` branch; main remains stable.”
- `docs/plan/implementation_master_plan_version-0.9.md` describes a model where `dev-mas` is an integration branch and `main` is production-ready, including a release process and tagging examples.

**What exists in git**
- Remote default branch: `origin/HEAD -> origin/main` (i.e., `main` is the default branch).
- Long-lived branches exist beyond the “dev + feature/*” model: `dev`, `dev-mas`, `dev-tests`, `dev-codex`, and `main`.
- No `release/*`, `hotfix/*`, `qa/*`, or `prod/*` branches were observed, and **no tags** were observed in the repository.

**Interpretation**
- The project appears to have **migrated from a single `dev` branch** into a **stacked integration approach** (`dev-tests` → `dev` → `dev-mas` → `main`) without codifying/enforcing it as policy.
- “Never develop in main” is **not enforceable** without (a) branch protection and (b) required CI checks; neither is represented in this repo checkout.

### 3.2 CI (Continuous Integration)

**Observed**
- There is **no** `.github/workflows/` directory; multiple docs explicitly mention that GitHub Actions workflows are not present (e.g., `docs/reports/preliminary_readiness_checks_version-0.7_upto10feb2026.md`).
- The repo does include strong **local** quality tooling:
  - `.pre-commit-config.yaml` includes `gitleaks`, `ruff`, `ruff-format`, and a local mypy hook.
  - `scripts/grade_phase5_readiness.sh` provides an orchestrated, repeatable quality run (lint + unit + optional integration + optional real LLM checks).

**Gaps vs “best practices”**
- No centrally enforced checks on PR/merge (lint/typecheck/tests).
- No artifact build, no image publishing, no per-environment deployment jobs.

### 3.3 CD / Deployments (Continuous Delivery/Deployment)

**Observed**
- `Dockerfile` and `docker-compose.yml` exist, and `Makefile` provides docker-compose targets.
- `docs/IAC/` documents a two-node setup (`skz-dev-lv`, `skz-stg-lv`) and operational runbooks (service checks, Docker Compose status, backups).

**Gaps vs “best practices”**
- No repository-defined automated deployment workflow to a QA/staging environment.
- No evidence of a production release mechanism (tags/releases + immutable artifacts + automated rollout/rollback).

### 3.4 Environment Model (dev → QA → prod)

**Observed**
- Documentation names two nodes: a “dev” node and a “stg” node (infrastructure/staging data node), but this is **infrastructure topology**, not a CI/CD promotion pipeline.
- There is no explicit environment promotion mechanism in the repository (no workflows, no environment configs, no deploy scripts).

## 4) CI/CD Maturity Assessment (Repository-Evidenced)

Scale used: **0 = absent**, **1 = ad hoc**, **2 = documented**, **3 = implemented (manual)**, **4 = automated (partial)**, **5 = automated + enforced + observable**.

| Area | Score | Evidence | Summary |
|---|---:|---|---|
| Branching policy | 2 | `README.md`, `DEVLOG.md`, `docs/plan/...` | Policy exists in docs but is inconsistent across documents and not enforced. |
| CI gating | 1 | No `.github/workflows/` | Strong local tooling exists, but no central CI enforcement. |
| Test strategy | 3 | `tests/`, `scripts/grade_phase5_readiness.sh` | Extensive tests and scripts exist; enforcement is manual. |
| Secrets hygiene | 3 | `gitleaks` pre-commit; `.env` forbidden | Local prevention is present; CI-side secret scanning not evidenced. |
| Release management | 1 | No tags, no changelog | Release approach described in docs but not realized in repo state. |
| CD / deployment automation | 1 | No deploy workflow | Deploy appears manual via Docker Compose/runbooks. |
| Environment promotion | 0–1 | No QA/prod pipeline | No repo-defined QA/prod environment promotion. |

Overall: **maturity is strongest in local quality controls and documentation**, weakest in **automation and enforcement**.

## 5) Gap Analysis vs the Referenced “Best Practice”

Target practice (as described): “Never commit/develop in `main`” + develop in `dev`/feature branches + GitHub Actions promotion to `qa` then `prod` + `main` contains only releases and CD.

**Key gaps**
1. **No CI in GitHub Actions** → nothing can be “promoted” automatically.
2. **No QA/prod environment representation** (GitHub Environments, deploy jobs, approvals) → no auditable promotion trail.
3. **No release primitives** (tags, changelog, versioning workflow) → `main` cannot be “release-only” in a controlled way.
4. **Branch model drift** (docs say `dev`; plan says `dev-mas`; reality has multiple `dev-*` long-lived branches) → process ambiguity.

## 6) Recommendations (Prioritized)

### 6.1 Decide and codify the branching model

Two reasonable options (choose one):

**Option A — GitFlow-like (matches your described model)**
- `dev` as integration branch (all feature branches merge here)
- `main` as release branch (only merges from `dev` via PR)
- releases via tags (e.g., `v0.9.0`, `v1.0.0`)
- environment promotion: deploy from `main` (or tags) to QA, then prod, with approvals

**Option B — Trunk-based (simpler, often more reliable)**
- `main` is trunk; all work via short-lived feature branches + PRs
- CI must be strong; releases are tags from `main`
- environments (QA/prod) are promotion stages for the same artifact (Docker image)

If the goal is “main only releases,” Option A is closer, but it increases branch overhead. Option B reduces branch overhead and shifts discipline into CI + release tagging.

### 6.2 Add GitHub Actions CI (minimal, fast, and enforceable)

Create `.github/workflows/ci.yml` to run on:
- `pull_request` (targeting `dev-mas`/`dev`/`main`)
- `push` to `dev`/`main` (optional)

Recommended checks (aligned with existing repo scripts):
- `ruff check .`
- mypy for the strict scopes you already run (`src/memory/`, `src/storage/`)
- `pytest -m "not integration and not llm_real"`

Avoid running integration + real-provider checks on every PR; instead run them:
- nightly, or
- manually (`workflow_dispatch`), or
- as a required check only for release PRs/tags.

### 6.3 Protect the critical branches (in GitHub settings)

For `main` (and the chosen integration branch):
- require PRs (no direct pushes)
- require CI checks to pass
- require up-to-date branch
- optionally require signed commits
- optional: CODEOWNERS + required reviews (if the team grows)

### 6.4 Implement environment promotion (QA → prod) as CD

Minimal pragmatic approach:
- Build a Docker image in CI and push to a registry with immutable tag (commit SHA).
- Deploy that same image to “QA/staging”.
- After approval, deploy the same image to prod.

GitHub Environments can provide:
- approval gates
- environment-specific secrets
- audit trail of what was deployed and when

### 6.5 Bring documentation in sync with reality

Current docs describe multiple, partially conflicting workflows (venv+pip vs Poetry, `dev` vs `dev-mas`):
- align `README.md`, `DEVLOG.md` conventions, and `docs/plan/...` with the chosen branching model and the actual dependency management approach.

## 7) Suggested 30/60/90-Day Roadmap

**0–30 days (Quick wins)**
- Add GitHub Actions CI workflow (lint + mypy + unit/mocked tests).
- Set required checks and branch protections for `main` and the integration branch.
- Add release tags for notable versions (even if retroactive is not desirable, start now).

**31–60 days**
- Add CD to a QA/staging environment using GitHub Environments + approvals.
- Define a “release” workflow (tag triggers build + deploy to QA).

**61–90 days**
- Add production deployment, rollback strategy, and deployment observability (release notes, metrics).
- Add security scanning in CI (dependency audit, container scan) if needed.

## 8) Evidence Index (Files Consulted)

- `README.md` (development guidelines)
- `DEVLOG.md` (branch policy notes)
- `.pre-commit-config.yaml` (local quality gates)
- `scripts/grade_phase5_readiness.sh` (repeatable local CI surrogate)
- `Makefile` (docker-compose + pytest target)
- `docker-compose.yml`, `Dockerfile` (containerization baseline)
- `docs/IAC/*` (infrastructure runbooks)
- `docs/reports/preliminary_readiness_checks_version-0.7_upto10feb2026.md` (explicit CI gap note)
- `docs/plan/implementation_master_plan_version-0.9.md` (intended CI + branching + release process)

