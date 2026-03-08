# Plans Index

This directory contains execution plans and RFP-style planning documents for YAAM.
Plans are treated as first-class, versioned artifacts to support agent-first development and
progressive disclosure of repository knowledge.

## Active planning artifacts

- `docs/plan/rfp-repository-harness-and-skills-v1.md` — Request for proposal describing the scope,
  goals, and non-goals for repository harness hardening and Skills v1 (feedback-only benchmark posture).
- `docs/plan/adr010-implementation-plan-repository-harness-and-skills-v1.md` — Implementation plan for
  ADR-010 (workstreams, milestones, acceptance criteria).
- `docs/plan/2026-02-22-fast-llm-memory-barrier-provider-parity-plan.md` — Provider parity plan for
  fast-inference models, specifying promotion barriers, artifact-level observability, and replication
  requirements across Groq/Gemini/Mistral.
- `docs/plan/2026-02-22-provider-parity-experiment-matrix.md` — Concrete experiment matrix defining
  provider × promotion mode × model combinations and a normative `--run-name` convention for Smoke5
  and memory-engine validation runs.

## Conventions

- Short, actionable, evidence-oriented steps are preferred over broad narratives.
- Plans should link to relevant ADRs and specs rather than duplicating them.
