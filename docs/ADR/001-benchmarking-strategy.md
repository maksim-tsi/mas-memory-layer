
### **ADR-001: Benchmarking Strategy for the Hybrid Memory Architecture**

**Title:** Selection of a Phased, Capability-Specific Benchmarking Protocol for the Initial Publication
**Status:** Accepted
**Date:** September 14, 2025

#### **1. Context**

The project has developed a novel, hybrid multi-layered memory architecture for Multi-Agent Systems. The initial research paper, submitted to the AIMS 2025 conference, received reviewer feedback that was universally positive about the conceptual contribution but unanimously critical of the lack of quantitative evaluation. To address this, a comprehensive deep-research report ("Hybrid Memory Benchmark Evaluation Protocol") was commissioned, which proposed an extensive, multi-benchmark, multi-configuration experimental plan.

The current decision is to define a feasible, high-impact subset of this "gold standard" protocol that can be executed within the time and resource constraints of a conference paper revision, while still generating the necessary evidence to satisfy the reviewers.

#### **2. Decision**

We will adopt a **phased evaluation strategy**. For the immediate purpose of the AIMS 2025 paper revision, we will:

1.  **Select a Single, Primary Benchmark:** We will focus exclusively on the **GoodAI LTM Benchmark**.
2.  **Implement a Minimal Set of High-Impact Configurations:** We will test three configurations: our **Full Hybrid System**, a **Standard RAG Baseline**, and a **Full-Context Baseline**.
3.  **Use a Focused Set of Models and Spans:** The evaluation will be conducted on two representative LLMs (**Mistral Small 3.2** and **Claude Haiku 4.5**) across two memory spans (**32k** and **200k**).

The more extensive evaluation involving the HotpotQA benchmark and the full suite of ablation studies is deferred to a future, long-form journal paper.

#### **3. Rationale**

This decision is based on a trade-off between comprehensiveness, feasibility, and strategic impact.

1.  **Strategic Alignment with Core Contribution:** The GoodAI LTM Benchmark is uniquely suited to test the most novel aspect of our architecture: the **information lifecycle over time**. Its dynamic, conversational nature and use of "distraction segments" directly stress-test our Promotion (Consolidation) and Conflict Resolution mechanisms. This provides the most direct validation of our core thesis.

2.  **Directly Addresses Reviewer Feedback:** The proposed experiment directly answers the reviewers' primary demand for quantitative data. It allows us to generate two high-impact tables comparing our system's **Functional Correctness** (GoodAI LTM Score) and **Operational Efficiency** (Latency, Cost) against credible baselines.

3.  **Feasibility:** The full protocol proposed in the deep-research report, involving over 100 benchmark runs, is not achievable within the revision timeline. The selected subset of 12 runs (`2 LLMs * 2 Spans * 3 Configs`) is a manageable and realistic target that still provides statistically significant results.

4.  **Methodological Rigor:** The choice to use a capability-specific benchmark (GoodAI LTM) over a composite one (like GAIA or AgentBench) for this initial evaluation is a methodologically sound decision, as argued in the research report. It allows us to isolate the performance of the memory subsystem, yielding clear and unambiguous results.

5.  **Compelling Narrative:** The selection of a context-limited model (Mistral Small 3.2) and a memory span that exceeds its native capacity (200k) creates the perfect conditions to demonstrate our architecture's primary value proposition: enabling smaller, more efficient models to overcome context limitations. A strong result here provides a powerful and memorable narrative for the paper.

#### **4. Consequences**

*   **Positive:**
    *   The plan is focused, achievable, and directly addresses the critical reviewer feedback, maximizing the chance of acceptance.
    *   It generates clear, quantitative evidence of our architecture's value in a rigorous and defensible manner.
    *   It establishes a clear and logical path for a more extensive follow-up publication (the "Phase B" involving HotpotQA).

*   **Negative:**
    *   The initial paper will not provide a quantitative evaluation of the multi-modal retrieval capabilities of the L3 Persistent Knowledge Layer (which HotpotQA would have tested). This is a known and accepted trade-off.
    *   The full suite of ablation studies (e.g., "No-Cache," "No-Consolidation") will not be included in the initial paper, deferring the granular quantification of each individual component's contribution.

#### **5. Alternatives Considered**

1.  **Executing the Full Protocol:** Considered but rejected due to being infeasible within the time and resource constraints for the conference revision.
2.  **Using a Composite Benchmark (e.g., GAIA):** Considered but rejected due to the methodological issue of confounding variables. It would be impossible to isolate the performance of the memory system from the agent's planning and tool-use capabilities, leading to ambiguous results.
3.  **Using Only the HotpotQA Benchmark:** Considered but rejected because, while it tests the L3 layer well, it does not test the dynamic, longitudinal information lifecycle mechanisms (Promotion, Consolidation, Conflict Resolution) which are the most novel part of our contribution. The GoodAI LTM benchmark provides a more direct test of our core thesis.