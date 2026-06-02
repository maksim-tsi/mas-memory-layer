# YAAM Requirements Registry

**Status:** Active  
**Last updated:** 2026-05-24  
**Scope:** Customer requirements, interface requirements, registry governance, and implementation traceability.

## Purpose

This directory is the system of record for YAAM requirements. Customer
submissions, internal RFEs, registry entries, and analysis reports should be
kept here so architectural and implementation work can be traced to explicit
requirements.

The registry is intentionally separate from implementation plans. Requirements
describe what customer systems need; plans describe how YAAM will satisfy a
selected subset.

## YAAM 0.10 Documentation Coverage

The [YAAM 0.10 documentation portal](../README.md) covers accepted
public-interface requirements through `YAAM-REQ-0038`, including MCP v1 stdio,
REST v2, benchmark-safe retrieval, curation records, and trace correlation.
Deferred requirements remain tracked in the registry and release notes.

## Current Registry Artifacts

| Artifact | Purpose |
|---|---|
| [yaam-requirements-registry.md](yaam-requirements-registry.md) | Human-readable canonical requirements registry. |
| [yaam-requirements-registry.csv](yaam-requirements-registry.csv) | Machine-sortable mirror of the registry. |
| [2026-05-24-customer-requirements-analysis.md](2026-05-24-customer-requirements-analysis.md) | Initial cross-customer analysis, priority themes, and impact discussion agenda. |
| [external_requirements/](external_requirements/) | Original customer requirement submissions. |
| [2026-05-24-yaam-customer-interface-requirements-request.md](2026-05-24-yaam-customer-interface-requirements-request.md) | Template used to request customer requirements. |

## Requirement ID Scheme

Requirement IDs use the format `YAAM-REQ-NNNN`.

Rules:

- IDs are stable and must not be reused.
- Superseded or rejected requirements remain in the registry with updated
  status.
- New implementation plans must reference relevant requirement IDs.
- Customer submissions remain source evidence; normalized interpretation lives
  in the registry and analysis reports.

## Registry Fields

The Markdown and CSV registries use the same conceptual fields:

- `id`
- `title`
- `description`
- `source_customers`
- `source_files`
- `source_section`
- `capability_tier`
- `memory_tier`
- `interface`
- `operation_type`
- `mvp`
- `priority`
- `status`
- `implementation_area`
- `acceptance_evidence`
- `notes`

## Priority Model

The first registry pass uses customer consensus as the primary priority model.

| Priority | Definition |
|---|---|
| `P0` | Required by at least three customer systems, or required by MVP plus security, isolation, or traceability risk. |
| `P1` | Required by two customer systems, or required by one core customer for MVP and aligned with YAAM's current REST/MCP direction. |
| `P2` | Single-customer MVP requirement or multi-customer non-MVP requirement. |
| `P3` | Optional, research-only, future automation, or unresolved open question. |

## Status Values

| Status | Meaning |
|---|---|
| `Proposed` | Captured from source material, not yet accepted for implementation. |
| `Accepted` | Accepted as a YAAM requirement and eligible for planning. |
| `Needs discussion` | Requires product or architecture decision before acceptance. |
| `Deferred` | Valid requirement but not in the current planning horizon. |
| `Rejected` | Explicitly out of scope or incompatible with YAAM direction. |

## Maintenance Rules

When adding or changing requirements:

1. Add or update a registry row in both Markdown and CSV.
2. Preserve source file and section references.
3. Classify the requirement by capability tier, interface, operation type, and
   MVP status.
4. Add security notes for every mutating or lifecycle requirement.
5. Add acceptance evidence for every `P0` and `P1` requirement.
6. Reference requirement IDs from implementation plans, RFCs, and reports.
