# SCM Skill Factory YAAM Readiness Retest Report

Date: 2026-05-31
Run timestamp: 2026-05-31T04:52:03Z
Consumer project: `scm-skill-factory`
YAAM project namespace: `scm-skill-factory`
Repository branch: `dev-eval`
Repository commit: `860c71e` (`Record YAAM retest results for run projection gap`)
Runner: MacBook / macOS, project venv Python 3.13

## Verdict

Pass.

After the YAAM fix that preserves metadata `run_id` when scope `run_id` is not
set, the full write-enabled verifier passes end to end. Generic YAAM reads,
MCP discovery, Phoenix reachability, synthetic L2/L3/L4/curation writes, repair
prompt retrieval, and all Skill Factory domain-pack views now work for
`scm-skill-factory`.

## Command

```bash
./.venv/bin/python scripts/verify_yaam.py --include-writes
```

## Result

```text
[OK] environment: YAAM, Phoenix, OpenRouter, embeddings, and DB targets match readiness defaults
[OK] postgres: SCM benchmark PostgreSQL responded to SELECT 1
[OK] yaam-rest-health: REST /health returned status=ok
[OK] yaam-rest-context: context returned with leakage_guard_passed=True
[OK] yaam-mcp-discovery: 16 tools, 5 resources, 10 templates, 5 prompts
[OK] yaam-mcp-read-tools: health, evidence, and CIAR reads passed
[OK] yaam-skill-factory-prompt: repair_pattern_summary prompt returned scoped guidance
[OK] phoenix-api: Phoenix API reachable with 65 projects
[OK] yaam-synthetic-writes: MCP L2/L3/L4 and curation synthetic write checks passed with domain metadata
[OK] yaam-skill-factory-domain-views: Skill, CTT, run, QA-status, and active-tool-status resources returned records
[OK] YAAM readiness verification completed in 15.41s
```

## Requirement Coverage

| Area | Result | Notes |
| --- | --- | --- |
| Environment readiness | Pass | Local `.env` points to `skz-data-lv`, OpenRouter/tencent/qwen defaults, Phoenix, and project namespace. |
| PostgreSQL connectivity | Pass | SCM benchmark PostgreSQL responded to `SELECT 1`. |
| REST health/context | Pass | `/health` returned `status=ok`; context returned leakage guard metadata. |
| MCP discovery | Pass | `16 tools`, `5 resources`, `10 templates`, `5 prompts`. |
| Skill Factory repair prompt | Pass | `yaam.prompt.repair_pattern_summary` resolved through MCP `prompts/get`. |
| Phoenix reachability | Pass | Phoenix API reachable at `skz-data-lv:6006`. |
| Synthetic MCP writes | Pass | L2 fact, L3 episode, L4 artifact, and curation decision writes all succeeded with canonical Skill Factory metadata. |
| Skill Factory domain views | Pass | Skill, CTT, run episodes, QA-status runs, and active-tool-status runs all returned records. |

## Domain-Pack Views Verified

- `yaam://skills/readiness_demo_skill`
- `yaam://ctts/readiness-ctt-001`
- `yaam://runs/skill-run-001/episodes`
- `yaam://skill-factory/qa-status/failed/runs`
- `yaam://skill-factory/active-tool-status/stale/runs`

Each resource passed verifier checks for `domain_pack=skill-factory`, expected
filters, non-empty counts/items or runs, and absence of secret-shaped markers.

## Conclusion

The YAAM Skill Factory domain pack is now ready for `scm-skill-factory`
project-specific testing. The previous run/status projection gap is resolved.
Any new failure after this baseline should be treated as a new regression or as
a changed local repository/configuration state.
