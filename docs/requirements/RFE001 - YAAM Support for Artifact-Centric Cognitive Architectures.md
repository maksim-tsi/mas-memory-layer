# Request for Enhancement (RFE): YAAM Support for Artifact-Centric "Sandwich" Cognitive Architectures

Initiator: IDWL'26 Research Team (Ilin, Pavlyuk)
Date: 08 March 2026

**1. Context and Business Need**
Our research team is implementing a "Sandwich" Cognitive Architecture (LLM -> OR Solver -> LLM) to handle supply chain disruptions. In this workflow, an LLM generates a decision artifact (JSON routing parameters), a deterministic solver tests it, and if the solver fails (returning an Irreducible Infeasible Subsystem / IIS log), the LLM iteratively revises the artifact until it becomes mathematically feasible.

Currently, YAAM provides excellent multi-tier storage, but it lacks the native conceptual primitives to track the *iterative evolution* of a single artifact and the *causal computational feedback* that drove its changes. We need YAAM to support strict artifact lineage and explicit tier segregation so that we can maintain a fully auditable decision trail.

**2. Target Workflow (The Scenario)**

1. **Drafting:** The agent creates Artifact v1 (routing payload). It is unverified.
2. **Execution & Failure:** An external solver evaluates v1 and fails, producing an IIS error log.
3. **Revision:** The agent reads the IIS log, corrects the payload, and creates Artifact v2.
4. **Validation & Commitment:** The solver evaluates v2 and succeeds. Artifact v2 is finalized as the "Ground Truth" decision.

**3. User Stories (Functional Requirements)**

* **US-1: Transient Draft Storage (Tier Control)**
*As an Agent/Orchestrator, I need the ability to explicitly save unverified draft artifacts to working memory (L1/L2) without them being automatically promoted to semantic/long-term memory (L4), so that experimental or failed payloads do not pollute the finalized knowledge base.*
* **US-2: External Feedback Attachment (Causal Provenance)**
*As an Agent/Orchestrator, I need a mechanism to attach external computational feedback (e.g., a solver's IIS log or execution metrics) directly to a specific draft artifact, so that there is a permanent record of why a specific artifact state was deemed infeasible.*
* **US-3: Artifact Versioning and Lineage (DAG Structure)**
*As an Agent/Orchestrator, I need to create a new version of an artifact (v2) and explicitly link it to its predecessor (v1) and the specific feedback (IIS log) that triggered the change, so that the system maintains a clear, auditable lineage of the decision-making process.*
* **US-4: Explicit Finalization (Commit to Semantic Memory)**
*As an Agent/Orchestrator, I need a specific tool or method to explicitly "commit" a finalized, feasible artifact to semantic memory (L4). This commit process must automatically bundle or reference the artifact's entire historical lineage (v1 -> error -> v2), so that human operators can audit the complete cognitive and mathematical trail.*

**4. Out of Scope (Implementation Details)**

* We do not prescribe *how* the lineage is stored (e.g., whether via Neo4j graph relationships, Postgres foreign keys, or Qdrant metadata).
* We do not prescribe the exact LangChain tool signatures, provided the agent has a clear interface to express "Save Draft," "Attach Feedback," "Revise Artifact," and "Commit Final."
* We do not prescribe the internal schemas for `Fact`, `Episode`, or `KnowledgeDocument`, as long as the concepts of "Lineage" and "Causal Provenance" are retrievable.

**5. Acceptance Criteria for the Research Team**
The enhancement will be considered successful if an LLM agent, using only the tools provided by YAAM, can execute the LLM-Solver-LLM loop and subsequently allow a user to query YAAM to retrieve the final decision *along with the exact mathematical solver logs that caused the agent to abandon its initial hypothesis*.