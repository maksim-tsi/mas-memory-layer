# **ADR-003 (Revised): Adoption of a Production-Ready, Four-Tier Cognitive Memory Architecture**

**Title:** Adoption of a Production-Ready, Four-Tier Cognitive Memory Architecture with Autonomous Lifecycle Engines
**Status:** Accepted
**Date:** November 02, 2025 (Original: September 14, 2025)

## **1. Context**

This ADR supersedes the previous version of ADR-002. Following an initial design, a comprehensive review of state-of-the-art (SOTA) research—including systems like Zep and Mem0—was conducted. This review validated our core direction but also revealed opportunities to adopt more sophisticated, production-ready patterns. The key drivers for this revision are:
1.  The need for a more nuanced, multi-stage memory hierarchy that better reflects cognitive science models.
2.  The necessity for a formal, interpretable model for managing information significance.
3.  The requirement for robust temporal reasoning and the modeling of complex, higher-order relationships, especially for the SCM domain.
4.  The imperative to design for production, incorporating patterns for performance, reliability, and observability from the outset.

## **2. Decision**

We will officially adopt and implement a **four-tier hierarchical memory architecture (L1-L4)**, governed by three distinct, asynchronous **autonomous lifecycle engines**. The architecture will be production-ready by design, incorporating a bi-temporal data model, hypergraph simulation, and explicit resilience patterns.

This decision formalizes the following architectural commitments for each tier:

---

#### **L1: Active Context (Working Memory Buffer)**

*   **Component:** **Redis**.
*   **Purpose:** To serve as a high-speed, ephemeral cache for the most recent, **raw** conversational turns (approx. 10-20 turns). This layer prioritizes sub-millisecond write latency for the agent's immediate cognitive loop.
*   **Data Model:** Simple key-value store. Key: `session_id`, Value: a list of **raw** message objects.
*   **Procedure (Lifecycle):**
    *   **Ingestion:** New messages are appended directly to the list (Hot Path).
    *   **Eviction:** A strict **Time-To-Live (TTL)** policy (e.g., 24 hours) is enforced to automatically discard stale data.
*   **Architectural Pattern:** **Ephemeral Cache.** No heavy processing occurs at this stage to prevent blocking the agent.

---

### **L2: Working Memory (Significance-Filtered Store)**

*   **Component:** **PostgreSQL**.
*   **Purpose:** To act as an intermediate, short-term store for **significant facts only**. This is the critical filtering stage that protects the more expensive downstream layers from noise.
*   **Data Model:** A relational table (`significant_facts`) with columns for `fact_id`, `content`, `ciar_score`, `certainty`, `impact`, `source_uri`, `timestamp`, etc.
*   **Procedure (Lifecycle - Promotion Engine):**
    1.  **Summarization:** The engine retrieves topic segments from L1 and generates a concise summary for each.
    2.  **Sensory Processing (Batch):** Triggered when the L1 buffer reaches a threshold. The engine retrieves a batch of raw turns and makes a single API call to a **Fast Inference LLM** (e.g., Groq Llama-3.3-70b or Gemini Flash). This model **compresses** conversational noise and **segments** the batch into coherent topics.
    2.  **Scoring:** Each topic segment is scored using the formal **CIAR (Certainty, Impact, Age, Recency) model:** `CIAR = (Certainty * Impact) * Age_Decay * Recency_Boost`.
    3.  **Promotion:** Segmenn:** **Significance-Based Caching.** This is our key differentiator from systems like Mem0. It is an interpretable, cost-saving filter that ensures only high-value information proceeds to deeper processing.

---

#### **L3: Episodic Memory (Hybrid Experience Store)**

*   **Components:** **Qdrant (Vector) & Neo4j (Graph)**.
*   **Purpose:** To create a permanent, rich, and multi-faceted record of consolidated "episodes" or experiences.
*   **Data Model:**
    *   **Neo4j (Bi-Temporal Property Graph):**
        *   **Hypergraph Simulation:** Higher-order events (e.g., shipments) are modeled using a central `:Event` or `:Shipment` node connected to participants, rather than pairwise links.
        *   **Bi-Temporal Schema:** All factual relationships include:
            *   `factValidFrom` / `factValidTo`: Real-world validity (Time).
            *   `sourceObservationTimestamp`: System ingestion time (Provenance).
            *   `validity_type`: Enum (`TIMELESS`, `TIME_BOUND`, `POINT_IN_TIME`) to handle different source types (e.g., Textbooks vs. Live APIs).
    *   **Qdrant:** A vector collection where each vector represents the embedding of a full "episode" summary. The vector payload contains the ID of the corresponding event node in Neo4j.
*   **Procedure (Lifecycle - Consolidation Engine):**
    1.  **Segmented Paging:** On a periodic basis, facts from L2 (PostgreSQL) are clustered by semantic similarity into "segments."
    2.  **Summarization:** An LLM summarizes each segment into a coherent narrative "episode."
    3.  **Temporal Resolution:** The engine compares new facts against existing graph edges. If a contradiction is found, the old edge is **invalidated** (updating `factValidTo`) rather than deleted.
    4.  **Dual-Indexing:** The episode is dually indexed into L3 (Qdrant & Neo4j).
    5.  **Look-back Linking:** After indexing, the system queries for similar *existing* episodes and uses an LLM to create new, emergent relationships between them in the graph.
*   **Architectural Pattern:** **Hybrid Retrieval Model.** This enables two powerful query pathways: semantic similarity search across experiences ("find similar situations") via Qdrant, and precise, structured traversal of relationships ("show me the full history of this container") via Neo4j.

---

### **L4: Semantic Memory (Distilled Knowledge Store)**

*   **Component:** **Typesense**.
*   **Purpose:** To store permanent, generalized, and procedural knowledge that has been "distilled" from patterns across many episodes.
*   **Data Model:** A full-text searchable index of documents. Each document represents a single piece of generalized knowledge (e.g., a user preference, a best practice, a learned rule) and includes provenance metadata linking back to the L3 episodes it was derived from.
*   **Procedure (Lifecycle - Distillation Engine):**
    1.  **Pattern Mining:** A long-running, low-priority background process analyzes multiple episodes in L3 (Neo4j/Qdrant) to identify recurring themes, patterns, and correlations.
    2.  **Synthesis:** An LLM synthesizes these patterns into concise, durable knowledge items (e.g., "User prefers async communication on weekends").
    3.  **Archiving:** These synthesized knowledge documents are indexed in **Typesense** for fast keyword and faceted search.
*   **Architectural Pattern:** **Unsupervised Learning & Knowledge Generalization.** This layer allows the system to move beyond recalling specific events to applying generalized, learned principles.

---

## **3. Rationale**

This four-tier architecture, governed by autonomous lifecycle engines, is a direct synthesis of our internal research and the SOTA patterns observed in the literature.

*   **Addresses Core Research Gaps:** It provides a formal, operational model for the "knowledge lifecycle," a concept that is theoretically discussed but rarely implemented with this level of detail.
*   **Combines SOTA Patterns:** It integrates a bi-temporal data model (inspired by Zep), an interpretable significance filter (our novel CIAR model), and a production-ready, asynchronous design (inspired by Mem0's focus on efficiency) into a single, coherent system.
*   **Optimized for Performance and Cost:** The hierarchical filtering (L1 -> L2 -> L3) ensures that computational and storage costs are only incurred for information that has been deemed significant, making the system more efficient and scalable than architectures that process all raw data.
*   **Production-Ready by Design:** The architecture explicitly includes resilience patterns (circuit breakers, graceful degradation) and a non-blocking, asynchronous design for its lifecycle engines, ensuring that memory management does not impact the real-time responsiveness of the agents.

## **4. Consequences**

*   **Positive:**
    *   The system will be highly capable, supporting nuanced temporal and multi-hop reasoning.
    *   The architecture is more efficient and cost-effective than a monolithic or simpler two-layer model.
    *   Our contribution to the research community is significantly stronger and more novel.
    *   The system is designed for reliability and observability, making it suitable for real-world deployment.
*   **Negative / Trade-offs:**
    *   **Increased Complexity:** The implementation is more complex, requiring the management of four distinct storage backends and three separate background lifecycle processes.
    *   **Data Consistency:** The asynchronous, multi-stage nature of the memory pipeline operates on a principle of eventual consistency. There will be a natural delay between an event occurring in L1 and its final distillation into L4. This is an acceptable trade-off for most conversational AI tasks but must be managed.
    *   **DevOps Overhead:** Managing a distributed, multi-database stack requires more sophisticated monitoring and maintenance than a single-database solution.

This ADR provides the definitive blueprint for the next phase of development. All future implementation work should align with the components, data models, and procedures defined herein.