# Runbooks Index

This directory contains operational procedures for running and validating YAAM
interfaces, experiments, and supporting observability infrastructure.

## Active runbooks

- [Admin validation guide](../admin-guide/validation.md) - Local, live, MCP,
  REST, and customer validation checklist for YAAM 0.10.
- [MCP v1 stdio guide](../user-guide/mcp-v1.md) - Customer-facing MCP tool,
  resource, prompt, and permission guide.
- [REST v2 guide](../user-guide/rest-v2.md) - Customer-facing REST API guide for
  `/v2/memory` endpoints and benchmark controls.
- [MCP v1 stdio server](mcp-v1-stdio-server.md) - Launch, inspect, and validate
  the YAAM MCP v1 stdio adapter, including read-only defaults and opt-in
  write/lifecycle contract checks.
- [Phoenix experiment reproducibility](phoenix-experiment-reproducibility.md) -
  Validate YAAM traces against a live local Phoenix server.
- [Variant A smoke run](runbook-variant-a-smoke-macbook-to-skz.md) - Run a
  GoodAI LTM smoke benchmark from an external benchmark checkout against the
  YAAM API Wall.
