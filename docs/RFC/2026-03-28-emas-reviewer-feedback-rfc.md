# RFC: EMAS 2026 Reviewer Feedback Response Plan for YAAM

**Status:** Proposed  
**Date:** 2026-05-18  
**Audience:** YAAM maintainers, benchmark operators, paper authors, coding assistants  
**Source feedback:** [docs/notes/28-03-2026-emas-openreview-response.md](../notes/28-03-2026-emas-openreview-response.md)  
**Related:** [ADR-003](../ADR/003-four-layers-memory.md), [ADR-004](../ADR/004-ciar-scoring-formula.md), [ADR-007](../ADR/007-agent-integration-layer.md), [ADR-009](../ADR/009-decoupling-benchmark-api-wall.md), [ADR-010](../ADR/010-mechanism-policy-split-and-skills-v1.md), [GoodAI evaluation protocol](../specs/spec-goodai-agent-variant-evaluation-protocol.md), [Phoenix tracing RFC](phoenix-tracing-rfc.md), [EMAS paper draft](../notes/paper-emas-draft-ru.md)

## 1. Purpose

This RFC translates the EMAS 2026 reviewer feedback into a concrete YAAM research and engineering response plan. It separates paper-level revisions from implementation work, and it grounds every proposed action in the current repository state.

The primary conclusion is that reviewers did not reject the core architecture. They repeatedly recognized the relevance of sovereign multi-agent memory, the mechanism/policy split, the Tool/Skill distinction, and the API Wall. The blocking weaknesses are:

1. insufficient quantitative evidence,
2. missing formal presentation of mechanisms that already exist in the repository,
3. imprecise novelty claims relative to prior work,
4. incomplete treatment of the Agent Skills standard,
5. inconsistent terminology and figure explanations,
6. and incomplete positioning within MAS/AOSE memory literature.

The immediate response should therefore prioritize evidence, formalization, and paper framing before changing mechanism code.

## 2. Source Note

The initially pulled feedback file ended mid-sentence in the third review:

```text
The separation of L3 into 2 different memory syste
```

The full third review was later provided by the author and has been inserted into the source feedback file. This RFC incorporates the complete visible feedback from all three reviews.

## 3. Atomic Feedback Inventory

### 3.1 Empirical evaluation

| ID | Atomic reviewer concern | Frequency | Current repository evidence | Gap |
|---|---|---:|---|---|
| E1 | Results section has no quantitative tables or figures. | R1, R2, R3 | GoodAI reports exist under `docs/reports/`, including provider Smoke5 runs and a YAAM vs pure-LLM comparison. | Results are not consolidated into paper-ready tables with task scores, model columns, and conditions. |
| E2 | Claims such as `>95% recall`, stabilization, token reduction, and hallucination mitigation lack metric definitions. | R1, R2 | `src/evaluation/agent_wrapper.py`, `src/server.py`, and memory tiers record timing/token metadata; Phoenix reports document traceability. | Paper does not define recall, evidence-use accuracy, token efficiency, or stabilization metrics. |
| E3 | GoodAI Smoke5 subset is mentioned but not described. | R2 | `docs/specs/spec-goodai-agent-variant-evaluation-protocol.md` defines run identity and artifacts. | Dataset/task definitions and scoring protocol are not summarized in the paper. |
| E4 | Baselines are insufficient or not clearly presented; comparison is mainly large context / pure LLM. | R1, R2, R3 | Existing comparison: YAAM vs pure LLM across Groq, Gemini, Mistral. Historical plan proposes Standard RAG and Full-Context baselines. | Standard RAG and full-context baselines are not reported as comparable paper tables; YAAM-vs-pure-LLM results are not presented in the paper. |
| E5 | Cross-provider comparison is underdeveloped. | R2 | Smoke5 artifacts exist for Groq, Gemini, and Mistral. Provider parity plans and reports exist. | No inter-provider variance table, task-level matrix, or interpretation is included. |
| E6 | Retrieval-Reasoning Gap is qualitative and not ablated with/without Evidence Table skill. | R1, R2, R3 | Skill-wiring plans and Phoenix evidence reports exist; `src/agents/memory_agent.py` supports variants. | No controlled ablation isolates the Evidence Table / evidence-formatting policy. |
| E7 | Statistical analysis is absent. | R1, R2 | Current Smoke5 artifacts are small and operational. | Need at least confidence intervals or clearly bounded descriptive statistics; otherwise claims must be softened. |
| E8 | Short-paper page limits do not justify omitting comparison results; an appendix could present them. | R3 | Existing docs can host appendices and supplementary tables. | The paper needs either an appendix with YAAM-vs-pure-LLM/provider results or a clear supplementary-material pointer. |

### 3.2 Formal mechanisms

| ID | Atomic reviewer concern | Frequency | Current repository evidence | Gap |
|---|---|---:|---|---|
| F1 | CIAR is not formally defined in the paper. | R1, R2 | ADR-004 and `src/memory/ciar_formula.py` define `CIAR = (certainty x impact) x exp(-lambda x days) x (1 + alpha x access_count)`, clamped to `[0, 1]`. | Paper names CIAR but omits equation, parameter defaults, normalization, threshold, and calibration rationale. |
| F2 | Knowledge lifecycle algorithms are conceptual, not algorithmic. | R1 | `PromotionEngine`, `ConsolidationEngine`, and `DistillationEngine` implement concrete flows. | Paper lacks pseudocode for promotion, consolidation, and distillation. |
| F3 | Tier interactions and schemas are underspecified. | R1 | `src/memory/models.py` defines `TurnData`, `Fact`, `Episode`, `KnowledgeDocument`, `ContextBlock`; v2 Pydantic schemas exist. | Paper lacks compact schema/table definitions for L1-L4 records and lifecycle transitions. |
| F4 | Progressive Disclosure / Skills selection is unclear. | R2 | ADR-010 defines Skills v1 as policy artifacts; ADR-007 links skills to subgraph/tool-bloat mitigation. | Paper does not explain the decision rule or current v1 status: manual/minimal skill selection, no full router yet. |
| F5 | System 2 framing is undeveloped and potentially misleading. | R2, R3 | Architecture docs do not require Kahneman's System 2 as a literal memory type. | Paper should either remove the label or define it narrowly as deliberative memory-use policy, not long-term memory itself. |
| F6 | The split of L3 into Qdrant and Neo4j is not explained clearly enough. | R3 | ADR-003 defines L3 as hybrid episodic memory: vector similarity via Qdrant plus graph/provenance traversal via Neo4j. | Paper needs to explain why L3 has two stores and what each contributes to episodic memory. |

### 3.3 Novelty and related work

| ID | Atomic reviewer concern | Frequency | Current repository evidence | Gap |
|---|---|---:|---|---|
| N1 | Difference from Mem0, Zep, A-Mem, MemGPT, Memory OS, and LightMem is not precise. | R1, R2 | ADR-003 discusses SOTA synthesis; paper draft only has high-level comparison. | Need structured comparison table with dimensions and claims limited to verified differences. |
| N2 | Claim that prior systems are monolithic is asserted, not demonstrated. | R2 | ADR-010 provides mechanism/policy split rationale. | Need either evidence-based wording or softened claim. |
| N3 | Retrieval-Reasoning Gap is framed as discovery but overlaps with known RAG/long-context literature. | R1, R2, R3 | Paper already cites long-context paradox. | Reframe novelty as YAAM's architectural mitigation and instrumentation, not the phenomenon itself; explicitly state how it differs from or extends the long-context paradox. |
| N4 | MAS/AOSE related work is missing. | R2 | YAAM docs focus on LLM agent memory and enterprise systems. | Add BDI belief management, belief revision, agent persistence, and AOSE state-management context. |
| N5 | Prior paper boundary is unclear. | R2 | Paper draft says it builds on prior theoretical framework. | Add a contribution delta paragraph: prior work = theory; this paper = implementation, API Wall, Skills, evidence. |
| N6 | Agent Skills standard is central but not directly cited or explained. | R3 | ADR-010 defines repository-local Skills v1; paper cites a related arXiv skills paper indirectly. | Add direct related-work treatment of `https://agentskills.io/` and distinguish YAAM Skills/SKILL.md from the external standard. |

### 3.4 Terminology, figures, and paper format

| ID | Atomic reviewer concern | Frequency | Current repository evidence | Gap |
|---|---|---:|---|---|
| T1 | Undefined terms: Sovereign AI, Cognitive Memory Barrier, Progressive Disclosure, API Wall, Black Box protocol, Goldfish Effect. | R2 | ADR-009 and ADR-010 define some terms internally. | Paper must introduce terms before use and avoid metaphor-heavy labels where a precise term suffices. |
| T2 | YAAM expansion is inconsistent. | R2 | Paper title/body vary between singular and plural. | Standardize to `Yet Another Agents Memory` or rename consistently across all artifacts. |
| T3 | Figure fonts are too small. | R2 | Figures are placeholders in current draft. | Redraw architecture and lifecycle figures with print-legible labels and clearer Skills-to-Kernel relation. |
| T4 | Neo4j is called relational memory / relational database inconsistently. | R3 | ADR-003 correctly treats Neo4j as graph storage within L3 episodic memory. | Correct paper terminology: Neo4j is graph memory/provenance graph, not relational memory. |
| T5 | PostgreSQL `working memory` label is contested because it persists facts. | R3 | ADR-003 describes L2 as significance-filtered short-term store, implemented in PostgreSQL. | Clarify that `working memory` is a functional tier, not volatile RAM; consider naming it `L2 significant working store`. |
| T6 | SCM use case is introduced but not used in evaluation. | R2 | SCM fixtures and TRA integration exist. | Ground at least one evaluation table or case analysis in SCM scenario data. |
| T7 | Page/category mismatch: 7 pages as regular paper reads like tool/demo. | R2 | Repository has implementation and supplement materials. | Choose either expanded regular-paper revision with evidence or tools/testbeds/demo framing. |
| T8 | Reference [1] appears miscited for lost-in-the-middle. | R2 | Paper draft bibliography is not in this file. | Correct attribution to primary lost-in-the-middle source and use ReflecSched only where relevant. |
| T9 | `Cognitive stabilizer` is used as a result label but is not defined or referenced. | R3 | No stable repository definition found in the inspected architecture docs. | Define the measurable construct or remove the term. |
| T10 | `Cloud-native` is used as a buzzword and appears to conflict with on-premise / anti-cloud-storage claims. | R3 | Repository docs emphasize containerization, API boundaries, and sovereign deployment. | Replace with precise terms such as containerized, API-first, self-hostable, or on-premise-capable; avoid unsupported cloud-native claims. |
| T11 | `Evidence Table` and `retrieval-reasoning-gap-mitigation` may refer to the same skill but use inconsistent names. | R3 | Skill-wiring docs and agent variants exist, but the inspected paper draft does not align names. | Choose one canonical skill name and explain aliases or differences. |

## 4. Current Implementation Assessment

### 4.1 Strengths already supported by the repository

1. **Four-tier memory architecture:** ADR-003, `src/memory/models.py`, tier modules, and `UnifiedMemorySystem` implement L1-L4 as concrete runtime surfaces.
2. **CIAR formalization exists:** ADR-004 and `src/memory/ciar_formula.py` provide the exact formula, defaults, and clamping behavior reviewers asked for.
3. **Lifecycle engines exist:** `PromotionEngine`, `ConsolidationEngine`, and `DistillationEngine` implement asynchronous promotion, consolidation, and distillation flows.
4. **API Wall is a real methodological boundary:** ADR-009 and `src/server.py` support GoodAI-style black-box evaluation rather than benchmark-local internal imports.
5. **Provider and trace instrumentation exists:** `src/evaluation/agent_wrapper.py`, `src/server.py`, Phoenix reports, and provider parity reports show the project has the substrate for reproducible evidence collection.
6. **Skills are an explicit policy layer:** ADR-010 and agent tooling establish the mechanism/policy split reviewers saw as one of the paper's strongest contributions.

### 4.2 Gaps that should be fixed in paper/docs before mechanism code

1. The paper draft does not import formal definitions already present in ADRs and code.
2. Existing benchmark reports are not yet paper-ready comparative evidence.
3. The novelty argument is too broad; it should be narrowed to enforceable differences: API Wall isolation, mechanism/policy split, Skills as declarative policy wrappers, CIAR-driven lifecycle filtering, and sovereign polyglot deployment.
4. The results narrative uses strong causal language that exceeds the current evidence.
5. The paper does not distinguish external Agent Skills work from YAAM's repository-local Skills policy layer.
6. Terminology drift creates avoidable reviewer objections.

### 4.3 Implementation gaps relevant to future code work

1. `ConsolidationEngine._get_unconsolidated_facts()` and `_get_unconsolidated_count()` are placeholders, which limits evidence for trigger-based recovery claims.
2. The current v2 L3 query route returns an empty result placeholder after LLM query generation; it does not yet expose a complete production query path.
3. Existing Smoke5 comparison reports have token and duration summaries, but not standardized task-level correctness tables across YAAM, Standard RAG, and Full-Context baselines.
4. Evidence Table / evidence-use behavior is not isolated as a controlled variant in the current paper-facing report set.
5. A canonical skill name for Retrieval-Reasoning Gap mitigation is not yet reflected consistently in paper figures and prose.

These are not storage-adapter defects. Under ADR-010 and repository instructions, mechanism-layer changes under `src/storage/` remain frozen-by-default.

## 5. Proposed Response Strategy

### Workstream A: Paper claim discipline and terminology

Revise the paper before adding new claims:

1. Define all architectural terms on first use.
2. Remove or narrow `System 2` unless the paper explicitly cites and distinguishes dual-process theory from memory architecture.
3. Replace `relational memory` wording for Neo4j with `graph-structured episodic/provenance memory`.
4. Clarify L2 as `significance-filtered working store` backed by PostgreSQL, with persistence used for fault tolerance and auditability.
5. Standardize the YAAM expansion across title, abstract, repository, and figures.
6. Reframe Retrieval-Reasoning Gap as an observed manifestation of known long-context/RAG evidence-use failures; claim novelty only for YAAM's mitigation and observability.
7. Define `cognitive stabilizer` as a measurable effect, or replace it with the actual measured quantity.
8. Replace unsupported `cloud-native` claims with precise deployment properties: containerized services, API Wall isolation, self-hostable DBMS backends, and optional external LLM providers.
9. Use one name for the Evidence Table / Retrieval-Reasoning Gap mitigation skill across figures, prose, and artifacts.

### Workstream B: Formal CIAR and lifecycle specification

Add a compact formal section to the paper and, if useful, a supporting spec:

1. Present the CIAR equation from ADR-004:

   ```text
   CIAR = clamp_0_1((certainty x impact) x exp(-lambda x days_since_creation) x (1 + alpha x access_count))
   ```

2. Define parameter defaults: `lambda=0.0231`, `alpha=0.1`, `promotion_threshold=0.6`.
3. Define component ranges and sources:
   - `certainty`: LLM-derived or heuristic confidence in `[0, 1]`,
   - `impact`: explicit score or fact-type/domain weight in `[0, 1]`,
   - `age`: exponential decay from creation/extraction timestamp,
   - `recency`: access-count reinforcement.
4. Add pseudocode for:
   - L1 batch segmentation and L2 promotion,
   - L2 fact clustering and L3 episode creation,
   - L3 episode synthesis and L4 knowledge document creation.
5. Include compact schemas for `TurnData`, `Fact`, `Episode`, and `KnowledgeDocument`.
6. Explain the L3 split explicitly: Qdrant provides semantic similarity over episode summaries, while Neo4j represents graph-structured episode provenance, entities, relationships, and temporal links.

### Workstream C: Evaluation evidence package

Produce a paper-ready evaluation package before making stronger empirical claims.

Minimum viable evidence for a revised student/tools paper:

1. Table 1: GoodAI Smoke5 task-level correctness for YAAM vs pure LLM across Groq, Gemini, and Mistral.
2. Table 2: operational cost summary by condition: duration, estimated tokens, per-turn latency if available, storage/LLM timing where available.
3. Table 3: provider variation summary: per-provider pass/fail or score by task.
4. Table 4: retrieval/use gap analysis: retrieved evidence present vs answer correctness for the affected tasks.
5. Appendix A or a supplementary table with YAAM-vs-pure-LLM results across LLM providers.
6. A short methodology paragraph defining Smoke5, run names, model versions, session isolation, API Wall use, and artifact paths.

Preferred evidence for a full regular-paper revision:

1. Add Standard RAG baseline.
2. Add Full-Context baseline where feasible.
3. Run controlled Evidence Table ablation:
   - `baseline` or current memory policy,
   - `v1-min-skillwiring`,
   - `v1-evidence-table` or equivalent explicit evidence-formatting variant.
4. Report descriptive statistics and confidence intervals if repeated runs are available.

If the team cannot generate stronger evidence within the submission window, the paper should be reframed as a tools/testbeds/demo contribution and strong effectiveness claims should be softened.

### Workstream D: Related work and contribution positioning

Add a structured comparison table with conservative dimensions:

| Dimension | YAAM claim to substantiate | Comparison targets |
|---|---|---|
| Deployment boundary | API Wall isolates benchmark/agent and supports sovereign deployment. | MemGPT, Mem0, Zep, Memory OS |
| Policy/mechanism split | Skills are declarative policy wrappers over stable mechanisms. | Agent Skills standard, tool-use frameworks, LangGraph, agent skills/workflows |
| Memory lifecycle | CIAR filters promotion; lifecycle engines consolidate and distill. | Mem0, Zep, A-Mem, LightMem |
| Polyglot persistence | Each tier maps to a query/latency profile. | Vector-only RAG, graph memory, hybrid memory systems |
| MAS orientation | Multi-agent session, provenance, and audit boundaries. | AOSE/BDI belief management, belief revision, agent persistence |

The revised paper should avoid claiming that prior systems are simply monolithic unless the comparison table provides a specific, cited reason.

The related-work section should cite and explain the Agent Skills standard directly, then state whether YAAM adopts it, adapts it, or only uses a compatible concept. This prevents conflating the external standard with YAAM's repository-local `SKILL.md` policy packages.

### Workstream E: Targeted implementation follow-up

Implementation should follow evidence gaps, not paper rhetoric. The first code changes after this RFC should be narrow:

1. Add or finalize an evidence-report generator for existing GoodAI artifacts that outputs paper tables in Markdown/CSV.
2. Add a benchmark report template section for task-level correctness and provider variance.
3. Add an Evidence Table policy variant only if it can be tested without changing `src/storage/`.
4. Implement missing consolidation trigger observability only if paper claims depend on autonomous recovery behavior.
5. Defer v2 L3 production query completion unless the revised paper explicitly claims that endpoint as evaluated behavior.
6. Normalize skill naming in paper figures and any repository skill metadata once the canonical mitigation skill name is selected.

## 6. Acceptance Criteria

The response plan is complete when:

1. Every atomic reviewer concern in section 3 has a disposition: addressed in paper, addressed by existing artifact, planned implementation, deferred, or rejected with rationale.
2. The paper contains a formal CIAR equation and a lifecycle algorithm summary.
3. Quantitative tables replace unsupported prose claims in the results section.
4. Novelty claims are bounded by a structured related-work comparison.
5. The paper uses consistent terms for YAAM, L2, L3, Neo4j, API Wall, Skills, and Progressive Disclosure.
6. The paper directly cites and positions the Agent Skills standard.
7. Figures are redrawn with print-legible text and explain the Skills Registry to Kernel relationship.
8. The final paper states whether it is positioned as a regular paper or a tools/testbeds/demo paper.

## 7. Verification Plan

### Documentation verification

1. Check all internal links in this RFC and the revised paper.
2. Confirm the paper's CIAR formula matches ADR-004 and `src/memory/ciar_formula.py`.
3. Confirm any reported benchmark table links to exact run artifacts and commit hashes.

### Repository commands before code verification

Follow the repository protocol before running lint/tests:

```bash
uname -a && hostname && pwd
./.venv/bin/python -c 'import sys; print(sys.executable)'
./.venv/bin/ruff check .
./.venv/bin/pytest tests/ -v
```

If `.venv/` is missing, run `poetry install --with test,dev` before verification. Dependency changes remain out of scope unless explicitly approved.

### Targeted future tests

1. Unit tests for any evidence-table generation logic.
2. Agent variant tests for any new Evidence Table policy.
3. API Wall smoke runs for each reported provider/model condition.
4. Regression tests for lifecycle behavior if consolidation trigger placeholders are implemented.

## 8. Assumptions and Defaults

1. The immediate artifact is an RFC and analysis roadmap, not a runtime API change.
2. `src/storage/` remains frozen-by-default.
3. No dependency, lockfile, `.github/`, `.env`, or virtualenv changes are required for this RFC.
4. Existing Smoke5 reports can serve as a starting point, but not as sufficient evidence for the strongest paper claims.
5. The third review text has been repaired from the user-provided full review; no missing-review assumption remains.
