Dear Maksim Ilin,

This is to inform you that the reviews for your submission #44, "YAAM (Yet Another Agents Memory): Hybrid Architecture for Cognitive State Management in Multi-Agent Systems", to EMAS 2026 are now available below.

review: The paper proposes YAAM, a hybrid architecture for long-term memory in multi-agent systems. The authors frame the system as a “Memory OS” that separates storage mechanisms from policy through a layered architecture consisting of Redis, PostgreSQL, Qdrant, Neo4j, and Typesense. The architecture also introduces a knowledge lifecycle pipeline with promotion and distillation processes and a CIAR score intended to filter information as it moves across memory tiers. The system is evaluated through a black-box protocol using the GoodAI LTM benchmark and tested with several LLM providers.

The paper addresses a relevant problem, since persistent memory and state management remain major challenges for agent systems. The architectural perspective is clearly presented and the system design is easy to follow. The emphasis on deployment considerations such as containerized infrastructure and separation between runtime and persistence layers is also useful for practical systems. The observation described as the retrieval–reasoning gap, where models retrieve correct information but fail to use it correctly, is also potentially interesting.

However, the technical description remains quite high level. Several core mechanisms are introduced but not sufficiently specified. For example, the CIAR score used for memory promotion is mentioned but the exact computation, normalization, and parameter selection are not described. The interaction between memory tiers is also only described conceptually, and no schema, algorithms, or formal definitions are provided. This limits reproducibility.

Another limitation is the limited discussion of how the proposed system relates to existing agent memory frameworks. Recent work such as Mem0, Zep, A-Mem, and MemGPT has explored similar ideas including long-term memory management, hybrid storage structures, and OS-inspired abstractions for LLM agents. While some of these works are cited, the paper does not clearly explain how the proposed architecture differs from or improves upon them. A clearer comparison would help better position the contribution with respect to the current literature.

The empirical validation is also very limited. The evaluation section does not include quantitative tables, statistical analysis, or detailed benchmark settings. Claims such as more than 95 percent recall from memory tiers are presented without a precise definition of the metric or an explanation of how it was measured. The experimental comparison is limited to a baseline using a large context window, and the system is not compared against other recent agent memory frameworks.

Several conclusions therefore appear insufficiently supported by the presented evidence. Statements regarding reasoning stabilization, prompt token reduction, or hallucination mitigation are made without accompanying measurements. As a result, the paper reads more like an architectural proposal than a fully validated system.

The paper could be strengthened by providing formal definitions of the proposed mechanisms, clearer descriptions of the knowledge lifecycle algorithms, and a more rigorous empirical evaluation including quantitative results and comparisons with existing memory architectures.

Overall the idea is interesting and relevant, but the current presentation lacks sufficient technical depth and experimental support to fully substantiate its claims. While this is a short paper and therefore subject to space limitations, several strong claims are made about the system’s effectiveness and behavior. When such claims are presented, some form of empirical evidence or clearer methodological detail is generally expected, even within the constraints of a short submission.
rating: 4

review: YAAM proposes a microservices reference architecture for long-term memory management in enterprise multi-agent systems. The core contribution is a hexagonal architecture that separates storage mechanisms (polyglot persistence across Redis, PostgreSQL, Qdrant, Neo4j, and Typesense) from policy (a Skills layer enabling progressive tool disclosure). The system operationalises a Knowledge Lifecycle through asynchronous promotion and distillation pipelines governed by a multi-factor CIAR score. Empirical validation uses an adapted GoodAI LTM benchmark under a "Black Box" API Wall protocol across three LLM providers, identifying a Retrieval-Reasoning Gap as a key finding. The paper is practically motivated and the architecture is coherent, but the empirical evaluation is severely underspecified, the writing is often imprecise, and the novelty relative to prior work is not adequately justified. At 7 content pages it is submitted as a regular paper but is substantially below the 16-page limit; it fits the tools/testbeds/demo category more naturally.

Quality
The architectural design of YAAM is competent and reflects genuine engineering
experience. The hexagonal architecture pattern, the separation of Mechanism and
Policy, the event-driven knowledge lifecycle, and the polyglot persistence stack
are all reasonable choices for a production-grade enterprise memory system. The
distinction between Tools (atomic functions) and Skills (declarative cognitive
wrappers with trigger conditions and allowed-tools arrays) is a useful
abstraction that is underexplored in the LLM agent literature.

The empirical quality, however, is significantly below the standard expected
even for a student paper. The results section (Section 5) is the paper's most
serious weakness. The paper states that YAAM "functions as a cognitive
stabilizer" and demonstrates ">95% Recall from L2/L3 tiers," but no quantitative
tables, figures, or statistical comparisons are provided. The GoodAI benchmark
results are described entirely in prose, with no reported scores for any condition,
model, or task category. The reader cannot verify the claimed recall figure,
cannot assess the magnitude of any improvement over the pure-LLM baseline,
and cannot determine whether the differences observed are meaningful or
consistent across models.

The Retrieval-Reasoning Gap — framed as the paper's key empirical discovery —
is described qualitatively: agents sometimes ignored retrieved facts due to
parametric priors or formatting rubric failures. This is a known phenomenon in
the RAG literature (the long-context paradox, cited as [9]) rather than a novel
discovery. The paper's contribution here is the specific architectural mitigation
(the Evidence Table skill), but no quantitative comparison of agent performance
with and without this skill is provided.

The CIAR score (Certainty × Impact × Age × Recency) is central to the
Promotion Engine but is never formally defined. The paper states that promotion
occurs when "CIAR Score > 0.6" but does not explain how each factor is computed,
what their ranges are, how they are combined multiplicatively (if they are), or
how the 0.6 threshold was determined. Without this definition, the mechanism
cannot be reproduced or evaluated.

The student paper format requires that the paper "clearly describe the problem
tackled and why it is important, the research method, the (expected) contributions
of the research, and the evaluation." The problem and contributions are described
adequately. The research method (architecture design and benchmark evaluation)
is described in structural terms but lacks the quantitative detail needed to
assess the evaluation. The student paper framing also requires that the lead
author be the student, which appears to be the case.

Clarity
The paper is written with confidence and uses domain vocabulary consistently,
but clarity suffers in several important places.

The CIAR score is the paper's central algorithmic contribution, yet it receives
no formal definition beyond its acronym expansion. A student paper that
introduces a "multi-factor semantic scoring" mechanism as a key contribution
must define that mechanism precisely. Even a single equation with definitions
of each term would substantially improve the paper.

The results section reads more like an architectural narrative than an empirical
report. Statements such as "YAAM acts as a stabilizing memory substrate" and
"YAAM is critical for performance leveling on complex reasoning paths" appear
without supporting numbers. The paper describes what the evaluation setup looks
like (Figure 4 is clear and useful) but does not report what the evaluation found
in quantifiable terms.

The connection to the prior paper [5] is mentioned briefly ("This paper builds
upon our foundational theoretical framework") but the scope of that prior work
and what specifically is new in this submission is not clearly delineated. For a
student paper building on a prior conference contribution, this boundary should
be explicit.

Several terms introduced without definition — "Goldfish Effect", "Progressive
Disclosure", "Cognitive Memory Barrier" — are evocative but would benefit from
brief formal definitions rather than relying on intuitive reading. The System 2
framing (from dual-process theory) is invoked in the abstract and title but
not developed or connected to the architecture in any substantive way.

Figure 1 (architecture diagram) is useful but the relationship between the
Skills Registry and the Kernel layers could be made clearer, particularly how
the "Progressive Disclosure" mechanism determines which tools are exposed to
which agents.

Originality
The originality of the paper is moderate. The combination of hexagonal
architecture, polyglot persistence, and event-driven knowledge lifecycle for
LLM agent memory is a reasonable engineering contribution, and the explicit
data sovereignty framing (on-premise deployment, network isolation of
persistence layer) is a practically important angle that is underrepresented
in the academic literature. The Tool vs. Skill distinction (atomic function vs.
declarative cognitive wrapper) is a useful conceptual refinement.

However, the paper's positioning relative to prior work is at times imprecise.
MemGPT [10], Memory OS [7], Mem0 [3], and Zep [12] are cited and compared
at a high level, but the specific technical differences between YAAM and these
systems are not analyzed with sufficient precision. The claim that prior systems
are "largely monolithic" is asserted rather than demonstrated. The Retrieval-
Reasoning Gap is presented as a discovery, but the phenomenon is described and
partially addressed in the cited long-context literature [9]; the novelty is the
specific architectural response (Evidence Table skill), not the observation itself.

The CIAR score, if properly defined and validated, could be the paper's most
original contribution. Without a formal definition, it is difficult to assess
whether it is genuinely novel or a relabeling of existing information-theoretic
or utility-based scoring approaches.

Significance
The motivating context — enterprise multi-agent systems requiring persistent,
auditable, sovereignty-preserving memory — is practically important and
underserved in the academic literature, which tends to focus on cloud-native
or single-agent settings. The Supply Chain Management application context
(mentioned in the keywords but not developed in the paper) is a compelling
use case. The open-source release of the full implementation and container
orchestration configurations is a meaningful practical contribution.

The significance is currently limited by the absence of quantitative results.
The paper's central claims — that YAAM achieves deterministic recall, stabilizes
performance across model providers, and mitigates the Retrieval-Reasoning Gap —
cannot be assessed without numbers. A follow-up version of this paper that
provides full benchmark tables, ablation results for the Evidence Table skill,
and a formal definition of CIAR would be considerably more impactful.

The student paper format is appropriate for work at this stage of development,
but even within that format, the expected contributions include a description
of the evaluation and its results. The current paper describes the evaluation
setup in detail but omits the results almost entirely.

Strengths
Practically motivated and coherent architecture. The separation of Mechanism and Policy via hexagonal architecture is a principled engineering choice, and the polyglot persistence stack is well-matched to the distinct latency and query profiles of different memory tiers.
Relevant to EMAS 2026 theme. The work directly addresses hybrid agent architectures, sovereign AI constraints, and enterprise MAS engineering — all central to the workshop's special theme.
Retrieval-Reasoning Gap. The empirical finding that >95% recall does not translate to correct reasoning is a genuine and useful observation, and the Evidence Table skill proposed as mitigation is a concrete engineering response.
Reproducibility. Public GitHub repository and Docker Compose configurations are provided; the API Wall protocol is a reasonable attempt at black-box isolation to prevent train-on-test contamination.
Progressive Disclosure. The Tool/Skill distinction and the notion of binding allowed-tools per cognitive context is a practically useful contribution for managing agent complexity.
Weaknesses
Empirical evaluation is critically underspecified. The results section reports no quantitative scores, tables, or statistical comparisons. Claims such as "YAAM functions as a cognitive stabilizer" and "significantly reduced token consumption" are asserted without numbers. The GoodAI benchmark subset used ("Smoke5") is mentioned but not described. Without concrete metrics it is impossible to assess whether YAAM actually improves performance, by how much, or under what conditions.
Novelty is insufficiently distinguished from prior work. The paper claims to unify MemGPT, Mem0, Zep, A-Mem, and LightMem but does not provide a structured comparison showing what YAAM does that these systems cannot. The CIAR score formula and its components are not formally defined. The Skills/SKILL.md mechanism is not compared to existing tool-use frameworks.
Writing is imprecise and occasionally inconsistent. Several key terms are undefined or poorly introduced: "Sovereign AI", "Cognitive Memory Barrier", "Progressive Disclosure", "API Wall", and "Black Box protocol" are used before being explained. The abstract refers to "System 2" without prior definition. Section headers and figure captions sometimes substitute for prose explanation.
Page length and category mismatch. At 7 content pages, the paper is well below the regular paper limit (16 pages) and reads as an architecture description and preliminary demo rather than a complete research contribution. It would be better suited to the tools/testbeds/demo category (4 pages), which explicitly welcomes early prototypes and requires a link to supplementary material — a condition the GitHub repository already satisfies.
CIAR score is inadequately formalised. The formula (Certainty × Impact × Age × Recency) is named but never formally defined. How each factor is computed, normalised, or calibrated is not explained, making the Promotion Engine's core logic unreproducible from the paper alone.
Cross-provider comparison is underdeveloped. Three LLM providers are used but no analysis of inter-provider variation is presented. It is unclear whether YAAM's benefit is consistent across providers or concentrated in one.
Related work coverage has gaps. The paper does not engage with agent memory work from the MAS/AOSE literature (e.g., BDI belief management, belief revision, agent persistence frameworks), which are directly relevant given the EMAS venue and would contextualise YAAM's contribution more precisely.
Reference [1] appears miscited. The "lost in the middle" paradox is attributed partly to a 2025 scheduling preprint (ReflecSched) rather than the primary source (Liu et al. [9]), which is also cited. This should be corrected.
Minor Comments
Fig. 1 and Fig. 2 are informative but the fonts are very small; they should be redrawn for legibility in print.
The acronym YAAM is introduced in the title and abstract but the expansion ("Yet Another Agent Memory" vs. "Yet Another Agents Memory") is inconsistent between the title and body.
The SCM motivating use case is mentioned in the introduction but does not reappear in the evaluation; grounding the empirical work in the stated application domain would strengthen coherence.
rating: 5
review: The article proposes a system for combining different types of memory for agents and enabling their progressive disclosure. The limitations to current approaches to memory motivate the need for new polyglot memory systems conceived specifically for agents and a system to control the agent's access to the different memory systems. The use of agent skills to control the access to control access to a polyglot memory system is the main original contribution of the article. The approach is well illustrated but the explanations are not always complete or consistent.

The abstract describes long-term memory as "System 2" but this concept is never explained further in the text. If this is a reference to Kahneman's theory, this should be explained and cited. However, while probably related, the meaning of Kahneman's System 2 seems different than long-term memory because Kahneman's System 2 is a mode of thought, not a type of memory.

There are some issues with the proposed model for memory. For example, the role given to the PostgreSQL database is working memory. However, it seems to be a long-term memory so it is not a working memory. Additionally, the Neo4j database is indicated as a relational memory in Figure 1 and an episodic memory in Figure 2. However, Neo4j is a graph database, not a relational database, so it does not seem to be the most suitable type of database for implementing a relational memory. It does not seems so well suited for episodic memory either even though it is probably doable to implement an episodic memory using this technology. The separation of L3 into 2 different memory systems should be explained.

The approach relies heavily on skills as part of its main contribution. In this context, this refers to the agent skills (https://agentskills.io/) standard. However, this standard is not explicitly identified in the related work or anywhere else in the article, which is an important omission. It is referenced only indirectly through "Li, X.: When single-agent with skills replace multi-agent systems and when they fail. arXiv preprint arXiv:2601.04748 (2026)". A direct reference and explanation would be a significant improvement to explain the approach.

Your evaluation relies on the GoodAI LTM benchmark with a comparison between your proposed system with different LLM backends and these pure LLMs. However, comparison of the results between the proposed system and the pure LLMs is not presented. Despite the size limitations of the short paper format, an Appendix could have been added to present these results.

The first result in Section 5.2 is that YAAM is a "cognitive stabilizer". However, this concept is not defined or referenced.

The second result in Section 5.3 is the "Retrieval-Reasoning Gap". This gap is defined as "an extension of the long-context paradox" in Section 2 but it is not explained how it differs from or extends this paradox. It is therefore not possible to evaluate whether this gap is indeed a novel contribution or a mere restatement of that paradox. The results in Section 5.3 are not enough to indicate whether this gap is properly identified and mitigated as claimed in the abstract. A skill called "Evidence Table" is proposed in Section 5.3 to mitigate the gap. It should be clarified whether this skill is the same as "retrieval-reasoning-gap-mitigation" skill in Figure 1. If yes, the right name should be used for both. Otherwise, it should be explained how they differ.

The general writing of the paper relies on buzzwords that do not provide meaningful explanations. For example: "The architecture is inherently Cloud-Native." in Section 4. It is never explained how the architecture is "cloud-native" besides publishing the source code online and relying on cloud providers for LLMs; none of which really qualifies the architecture as "cloud-native". This specific example also seems to contradict an earlier claim: "Furthermore, dependency on black-box cloud storage is unacceptable for on-premise, secure perimeters.", which is used to design the approach.
rating: 3
