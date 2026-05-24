# Specifications Index

This directory contains normative specifications that define stable contracts and requirements for
YAAM subsystems. Specs are intended to be referenced by ADRs, plans, and skill documentation.

## Mechanism/Policy boundary

- `docs/specs/spec-mechanism-maturity-and-freeze.md` — Defines Connector/Adapter Contract v1 for the
  mechanism layer (`src/storage/`), maturity criteria, evidence requirements, and change control for
  freeze-by-default operation.

## Observability

- `docs/specs/observability/phoenix-span-contract.md` — Defines the OpenInference/Phoenix span contract for YAAM glass-box observability above the mechanism layer.

## Public interfaces

- `docs/specs/spec-mcp-v1-implementation.md` — Defines the MCP v1 stdio adapter,
  service boundary, public tool/resource/prompt surface, permission policy,
  response contracts, and tracing requirements.

## Conventions

- Specs must be precise and testable (requirements should have evidence).
- If an ADR introduces a new contract, it should be formalized in this directory and then enforced
  mechanically where possible.
