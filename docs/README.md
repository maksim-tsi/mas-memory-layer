# YAAM 0.10 Documentation

Current customer-facing release: **YAAM 0.10**.

This portal is the starting point for using, operating, and extending YAAM. It
links the public interface guides, operational runbooks, public response
contracts, requirements registry, and release notes.

## Start Here

- Users integrating agents or services should start with the
  [user guide](user-guide/README.md).
- Admins and operators should start with the
  [admin guide](admin-guide/README.md) and
  [validation guide](admin-guide/validation.md).
- Developers and maintainers should review the
  [requirements registry](requirements/README.md), the
  [technical specifications](specs/README.md), and the relevant ADRs.

## Public Interfaces

- [MCP v1 stdio guide](user-guide/mcp-v1.md) for agent-host and tool-based
  integrations.
- [REST v2 guide](user-guide/rest-v2.md) for service-to-service, batch, and
  benchmark support integrations.
- [Public contracts reference](reference/public-contracts.md) for shared
  response shapes and compatibility expectations.
- [MCP v1 implementation spec](specs/spec-mcp-v1-implementation.md) for the
  normative technical MCP contract.

## Operations And Validation

- [Admin guide](admin-guide/README.md) for installation assumptions, storage
  backends, LLM provider configuration, and support boundaries.
- [Validation guide](admin-guide/validation.md) for local, live, MCP, REST, and
  customer validation checklists.
- [Environment guide](environment-guide.md) for environment variables and local
  setup expectations.
- [Connectivity cheatsheet](IAC/connectivity-cheatsheet.md) for backend
  connectivity checks.
- [Runbooks](runbooks/README.md) for operational procedures.

## Requirements And Releases

- [Requirements registry](requirements/README.md) tracks normalized customer
  requirements and their implementation status.
- [Release notes](releases/README.md) record customer-facing changes and known
  deferred work.

## What To Expect From YAAM 0.10

YAAM 0.10 exposes memory retrieval, contextual assembly, provenance-aware
evidence, benchmark-safe reads, curation records, trace correlation, and gated
write/lifecycle operations through MCP v1 stdio and REST v2.

YAAM is not a raw database gateway, not an arbitrary SQL/Cypher execution
surface, not a replacement for customer orchestration logic, and not an
always-autonomous lifecycle manager. Public interfaces are intentionally scoped
around memory operations, traceability, safety, and compatibility.
