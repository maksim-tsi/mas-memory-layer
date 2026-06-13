# RFC: H-Mem-Inspired Hybrid L3 Retrieval Scoring

**Date:** 2026-06-03
**Status:** Proposed experiment
**Decision:** Do not implement full H-Mem adoption; evaluate a bounded L3
scoring experiment using existing YAAM storage.

## Motivation

H-Mem shows that long-term memory QA can benefit from combining semantic,
temporal, graph, and robustness signals. Graphiti/Zep shows the value of
temporal graph memory. A-MEM shows the value of inspectable linked memory.

YAAM already has compatible ingredients:

- Qdrant-backed L3 semantic episode retrieval;
- Neo4j-backed relational episode design;
- episode timestamps and validity metadata;
- CIAR and lifetime decision provenance;
- Phoenix trace evidence.

The opportunity is retrieval ranking and evaluation, not a new storage stack.

## Proposed Experiment

Add an experimental L3 retrieval scorer that computes a diagnostic score from
existing data:

- semantic similarity from Qdrant;
- relationship support from Neo4j where available;
- temporal alignment from episode timestamps or validity windows;
- governance-aware robustness from CIAR/lifetime provenance;
- optional evidence-gap flags for missing or low-provenance retrieval.

The scorer should be introduced as an experiment or analyzer path first, not as
the default retrieval policy.

## Non-Goals

Do not implement:

- H-Mem's full temporal-semantic tree;
- new DBMS backends;
- storage schema changes without a separate ADR;
- query-planner LLM calls in the hot path;
- changes to public REST or MCP contracts.

## Evaluation

Compare current L3 retrieval against the hybrid scorer on synthetic
customer-like scenarios:

- operational correction and supersession;
- artifact lineage;
- Skill Factory repair patterns;
- stale preference;
- urgent event with chatter;
- benchmark leakage-sensitive queries.

Metrics:

- memory precision;
- memory recall;
- temporal correctness;
- provenance completeness;
- leakage guard behavior;
- latency and provider-call count;
- Phoenix trace completeness.

## Acceptance Criteria

The experiment is worth advancing only if it improves retrieval inspectability
or correctness without weakening YAAM's public-contract and governance posture.
Task-performance improvement must not be claimed until benchmarked.

## Related Requirements

- `YAAM-REQ-0007`: L3 semantic episode query.
- `YAAM-REQ-0009`: provenance on reads and writes.
- `YAAM-REQ-0016`: Evidence Table generation.
- `YAAM-REQ-0017`: CIAR explanation.
- `YAAM-REQ-0029`: contradiction/supersession review.
- `YAAM-REQ-0036`: benchmark leakage guards.
- `YAAM-REQ-0038`: trace and artifact correlation metadata.
