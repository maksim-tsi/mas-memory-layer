# Reports Directory

This directory contains technical reports, status updates, and debugging documentation for the MAS Memory Layer project.

## Report Categories

### Phase Readiness & Status
| Report | Description |
|--------|-------------|
| [preliminary_readiness_checks_version-0.7_upto10feb2026.md](preliminary_readiness_checks_version-0.7_upto10feb2026.md) | Consolidated readiness checks (version-0.7) |
| [adr-003-architecture-review.md](adr-003-architecture-review.md) | Gap analysis against ADR-003 architecture |

### Debugging & Incident Reports
| Report | Date | Issue | Status |
|--------|------|-------|--------|
| [qdrant-scroll-vs-search-debugging-2026-01-03.md](qdrant-scroll-vs-search-debugging-2026-01-03.md) | 2026-01-03 | Qdrant search returning 0 results with filters | ✅ Resolved |

### Implementation Reports
| Report | Description |
|--------|-------------|
| [metrics_program_overview_version-0.9_upto10feb2026.md](metrics_program_overview_version-0.9_upto10feb2026.md) | Metrics program overview (version-0.9) |
| [neo4j-refactor-option-a-success.md](neo4j-refactor-option-a-success.md) | Neo4j adapter refactoring outcome |
| [implementation_consolidated_version-0.9_upto10feb2026.md](implementation_consolidated_version-0.9_upto10feb2026.md) | Consolidated implementation reports (version-0.9) |
| [phase2_3_consolidated_version-0.9_upto10feb2026.md](phase2_3_consolidated_version-0.9_upto10feb2026.md) | Phase 2/3 consolidated plan and prereq notes |
| [memory_inspector_consolidated_version-0.9_upto10feb2026.md](memory_inspector_consolidated_version-0.9_upto10feb2026.md) | Memory inspector consolidated reports (version-0.9) |
| [dependency_analysis_consolidated_version-0.9_upto10feb2026.md](dependency_analysis_consolidated_version-0.9_upto10feb2026.md) | Dependency analysis consolidated reports (version-0.9) |

### Code Review Reports
| Report | Description |
|--------|-------------|
| [code_review_consolidated_version-0.9_upto10feb2026.md](code_review_consolidated_version-0.9_upto10feb2026.md) | Consolidated code reviews (version-0.9) |
| [priority_6_consolidated_version-0.9_upto10feb2026.md](priority_6_consolidated_version-0.9_upto10feb2026.md) | Priority 6 consolidated reports (version-0.9) |

### Benchmark & Validation
| Report | Description |
|--------|-------------|
| [goodai_ltm_benchmark_reports_version-0.9_upto10feb2026.md](goodai_ltm_benchmark_reports_version-0.9_upto10feb2026.md) | Consolidated benchmark reports (version-0.9) |
| [integration-tests-2025-11-12.md](integration-tests-2025-11-12.md) | Integration test results |
| [goodai_ltm_benchmark_troubleshooting_upto10feb2026.md](goodai_ltm_benchmark_troubleshooting_upto10feb2026.md) | Consolidated benchmark troubleshooting notes |
| [template-goodai-agent-variant-report.md](template-goodai-agent-variant-report.md) | Standard template for variant-based benchmark runs (ADR-011), including Variant A (`v1-min-skillwiring`) skill-level aggregation tables (`skill_slug`, latency/tokens, error distribution) |
| [2026-02-21-variant-a-smoke-runs.md](2026-02-21-variant-a-smoke-runs.md) | Variant A smoke run attempts (5 datasets x 1 example), observed failures, mitigations, and next iterations |

## Naming Conventions

- **Date-prefixed:** `YYYY-MM-DD-topic.md` for time-specific reports
- **Topic-date:** `topic-YYYY-MM-DD.md` for debugging/incident reports
- **JSON artifacts:** `lifecycle_test_history_version-0.9.jsonl` for machine-readable test results

## Related Documentation

- [Plan Directory](../plan/) - Implementation plans and checklists
- [ADR Directory](../ADR/) - Architecture Decision Records
- [Lessons Learned](../lessons-learned.md) - Incident register with mitigations
