# Specifications Index

This directory contains normative specifications that define stable contracts and requirements for
YAAM subsystems. Specs are intended to be referenced by ADRs, plans, and skill documentation.

## Mechanism/Policy boundary

- `docs/specs/spec-mechanism-maturity-and-freeze.md` — Defines Connector/Adapter Contract v1 for the
  mechanism layer (`src/storage/`), maturity criteria, evidence requirements, and change control for
  freeze-by-default operation.

## Conventions

- Specs must be precise and testable (requirements should have evidence).
- If an ADR introduces a new contract, it should be formalized in this directory and then enforced
  mechanically where possible.
