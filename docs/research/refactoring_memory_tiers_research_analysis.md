# **Architectural Transformation of Multi-Agent Cognitive Memory Systems: A Comprehensive Analysis of Type-Safe Generic Implementations versus Dynamic Dictionary Architectures**

The rapid advancement of Multi-Agent Systems (MAS) has necessitated a fundamental shift in the architectural paradigms governing memory persistence and retrieval. As autonomous agents evolve from stateless request-response engines into persistent, reasoning entities capable of long-horizon tasks, the underlying infrastructure must support increasingly complex data contracts. The MAS Memory Layer project, currently preparing for submission to the AIMS 2025 conference, stands at a critical architectural juncture. The system leverages a sophisticated four-tier memory architecture—comprising Active Context (L1), Working Memory (L2), Episodic Memory (L3), and Semantic Memory (L4)—to facilitate high-stakes decision support in logistics and supply chain management.1 Central to this architecture is the BaseTier interface, the polymorphic boundary that governs interaction across diverse storage backends including Redis, PostgreSQL, Qdrant, Neo4j, and Typesense.1

This report provides an exhaustive, expert-level analysis of the proposed refactoring of the BaseTier class. The core proposition involves transitioning from the current flexible but opaque dict\[str, Any\] return type to a strict, type-safe implementation utilizing Python generics (Generic) bound to Pydantic domain models. This analysis synthesizes evidence from the project's codebase, architectural decision records (ADRs), performance benchmarks, and broader software engineering literature regarding static typing in dynamic languages. The evaluation criteria encompass system reliability, developer velocity, runtime performance, cognitive fidelity for agent reasoning, and alignment with modern Site Reliability Engineering (SRE) principles.

## **Part I: Theoretical Framework and Architectural Context**

To rigorously evaluate the proposed refactoring, one must first establish the theoretical and architectural context in which the MAS Memory Layer operates. The system is not merely a data store; it is a cognitive architecture designed to emulate human memory processes, specifically the Atkinson-Shiffrin and Tulving models, adapted for distributed computational efficiency.1

### **1.1 The Evolution of Type Systems in Python**

Python has historically relied on dynamic typing (duck typing), offering flexibility that accelerates early-stage prototyping. However, as systems scale in complexity, this flexibility often incurs a debt in maintainability and reliability.2 The introduction of PEP 484 and subsequent typing enhancements (PEP 483, PEP 526\) signaled a paradigm shift toward gradual typing, allowing developers to introduce static analysis into dynamic codebases.3

In the context of the MAS Memory Layer, the tension between dynamic flexibility and static safety is palpable. The current implementation relies on dict\[str, Any\] returns, a pattern that mirrors the unstructured nature of early Python development. While this allows for heterogeneous data to flow easily between storage adapters and logic tiers, it obscures the data contract from the developer and the static analysis tooling (mypy).2 The proposed refactoring leverages Python's support for Generics (Generic) and Type Variables (TypeVar), mechanisms that allow classes to define behavior over a range of types while maintaining strict boundary checks.5

The theoretical advantage of this approach lies in the formal verification of data flows. By binding the BaseTier to a specific Pydantic model (![][image1]), the architecture enforces a contract that guarantees not just the presence of data, but its structure, validity, and type-correctness at compile time.5 This aligns with the "Robustness Principle" in distributed systems, where rigorous validation of internal interfaces prevents cascading failures—a critical consideration for a system managing the cognitive state of autonomous agents.8

### **1.2 The ADR-003 Four-Tier Cognitive Architecture**

The MAS Memory Layer is governed by Architecture Decision Record 003 (ADR-003), which mandates a four-tier hierarchy to balance immediate recall with long-term pattern synthesis.1 Understanding the distinct characteristics of these tiers is essential for evaluating the impact of the proposed refactoring.

#### **Tier 1: Active Context (Redis)**

The L1 tier serves as the high-speed "prefrontal cortex" of the system, maintaining a raw buffer of recent conversation turns (10-20 turns) with a 24-hour Time-To-Live (TTL).1 It utilizes Redis for sub-millisecond access, targeting \<5ms retrieval latencies.1 The data structure here is primarily sequential and ephemeral. The current implementation returns raw dictionaries representing turns, which must then be manually parsed by consumers.1

#### **Tier 2: Working Memory (PostgreSQL)**

L2 represents the system's "working memory," storing significant facts filtered by the CIAR (Certainty, Impact, Age, Recency) scoring algorithm.1 It persists data in PostgreSQL, enforcing a 7-day TTL. The Fact model governing this tier is complex, containing logic for score recalculation and access tracking.1 The use of dict returns here creates a disconnection between the rich logic encapsulated in the Fact class (e.g., validate\_ciar\_score, mark\_accessed) and the data retrieval process, forcing consumers to re-instantiate models to access this logic.1

#### **Tier 3: Episodic Memory (Qdrant \+ Neo4j)**

This tier consolidates facts into coherent narrative "episodes".1 It employs a dual-indexing strategy: vector embeddings in Qdrant for semantic similarity and graph structures in Neo4j for relationship traversal.1 The data complexity here is high, involving bi-temporal validity windows (fact\_valid\_from, fact\_valid\_to) and cross-references between vector and graph IDs.1 Passing this data as unstructured dictionaries risks "temporal amnesia," where validity windows are ignored or malformed downstream.1

#### **Tier 4: Semantic Memory (Typesense)**

L4 stores distilled knowledge patterns and generalized insights.1 It uses Typesense for full-text and faceted search. The KnowledgeDocument model includes lineage tracking (provenance\_links) and confidence scores that are critical for agent decision-making.1

### **1.3 The "Stringly Typed" Bottleneck**

The current architecture relies on what is colloquially known as "stringly typed" programming at the tier boundaries. Methods like query(filters: dict) \-\> List\[dict\] rely on string keys to convey semantic meaning.1 This introduces several vectors for failure:

1. **Silent Failures:** A typo in a dictionary key (e.g., ciar\_score vs score) will not be caught until runtime, potentially causing an agent to act on zero-value defaults.2  
2. **Documentation Drift:** The shape of the returned dictionary is defined only by the implementation code, not the interface signature. As the system evolves (e.g., adding topic\_segment\_id to facts), the implicit contract changes without warning.1  
3. **Toil:** Developers must constantly refer to implementation details to understand the data structure, increasing cognitive load and "toil"—a metric Google SREs strive to minimize.9

Refactoring to BaseTier addresses these issues by making the data contract explicit, enforceable, and self-documenting.5

## **Part II: Technical Implementation Analysis**

The proposed refactoring is not a trivial change; it requires a deep understanding of Python's generic protocols and the specific constraints of the Pydantic library.

### **2.1 Implementing Generic Base Classes**

The implementation of generics in Python 3.12+ (and compatible with the project's Python 3.13.5 environment 1) allows for cleaner syntax, but the fundamental mechanics rely on TypeVar.6 The BaseTier would be redefined to accept a type variable ![][image1] bound to BaseModel:

Python

from typing import Generic, TypeVar, List, Optional  
from pydantic import BaseModel

T \= TypeVar("T", bound=BaseModel)

class BaseTier(ABC, Generic):  
    @abstractmethod  
    async def retrieve(self, id: str) \-\> Optional:  
        """Retrieve an item by ID, returning a validated domain model."""  
        pass  
      
    @abstractmethod  
    async def query(self, filters: dict) \-\> List:  
        """Search for items, returning a list of domain models."""  
        pass

This definition ensures that any concrete implementation (e.g., class WorkingMemoryTier(BaseTier\[Fact\])) is statically guaranteed to return Fact objects.10 This solves the covariance problem where static analyzers struggle to infer return types from abstract methods.11

### **2.2 Integration with Storage Adapters**

The MAS Memory Layer utilizes a set of robust storage adapters (RedisAdapter, PostgresAdapter, etc.) that currently return raw data formats—JSON strings, tuples, or client-specific objects like PointStruct.1 The refactoring does *not* require changing these adapters to return Pydantic models directly, which would violate the separation of concerns. Instead, the Tier classes act as the translation layer.1

For example, in WorkingMemoryTier, the retrieve method currently fetches data from PostgresAdapter and returns a dictionary.1 In the refactored design, it would instantiate the Fact model immediately:

Python

\# Refactored WorkingMemoryTier  
async def retrieve(self, fact\_id: str) \-\> Optional\[Fact\]:  
    data \= await self.adapter.retrieve(fact\_id)  
    if not data:  
        return None  
    \# Validate and return strong type  
    model \= Fact.model\_validate(data)  
    await self.\_update\_access\_tracking(model)  
    return model

This pattern ensures that the "boundary of uncertainty" is pushed as deep into the infrastructure as possible. Once data leaves the Tier layer, it is guaranteed to be valid according to the schema.13

### **2.3 Handling Covariance and Mypy Constraints**

One technical challenge in this refactoring is handling covariance in list returns. Mypy can be strict about overriding methods with covariant return types.14 For instance, if BaseTier.query returns List, then WorkingMemoryTier.query must return List\[Fact\]. Since Fact is a subtype of BaseModel (the bound of ![][image1]), this is generally safe, but explicit type hinting is required to prevent "incompatible override" errors.11

The project's use of Pydantic v2 helps mitigate some of these issues, as Pydantic models are designed to play well with static analysis tools when the mypy plugin is enabled.16 The use of TypeVar with a bound ensures that the type checker understands the relationship between the generic base and the concrete implementation.7

## **Part III: Reliability and SRE Implications**

The decision to refactor extends beyond code style; it is a reliability engineering decision. The Google SRE book defines reliability as a fundamental feature of any system.9 In the context of the MAS Memory Layer, reliability means ensuring that agents can access accurate, consistent memory states without causing system crashes or logic errors.

### **3.1 Reducing the Error Budget Consumption**

In an SRE framework, every uncaught exception or malformed data return consumes the "error budget".9 The current dict return type relies on runtime keys-existence checks (e.g., if 'ciar\_score' in fact:). If a storage migration renames a column or a Redis corruption results in missing keys, these checks might fail deeply within the agent's reasoning loop, potentially causing a cascading failure where an agent makes a decision based on incomplete information.1

By enforcing type safety at the tier level, the system implements a "fail-fast" mechanism. If the data retrieved from Postgres does not match the Fact schema, Fact.model\_validate will raise a ValidationError immediately at the retrieval point.13 This allows the system to catch data corruption early, log it, and potentially trigger self-healing mechanisms (like attempting to reconstruct the fact from L1 backup) before the corrupted data propagates to the agent.1 This containment of failure domains is a core tenet of building reliable distributed systems.9

### **3.2 Cognitive Reliability and CIAR Integrity**

The MAS Memory Layer's unique value proposition is its CIAR scoring system—a mathematical model for significance.1 The formula involves exponential decay and linear reinforcement:

![][image2]  
The integrity of this calculation is paramount. In a dictionary-based system, ciar\_score is just a number. It can be inadvertently overwritten with an invalid value (e.g., \>1.0) or calculated using stale components. The Pydantic Fact model includes a validator validate\_ciar\_score that enforces the mathematical relationship between the components and the final score.1

If the system passes around dictionaries, this validation logic is bypassed unless explicitly invoked. By refactoring to return Fact objects, the system guarantees that every memory item accessed by an agent adheres to the CIAR invariants. This "Cognitive Integrity" is analogous to data integrity in database systems—it ensures the agent's worldview is consistent and mathematically sound.1

### **3.3 Observability and Toil Reduction**

The project utilizes Arize Phoenix for observability.1 Structured objects improve observability by ensuring that logs and traces contain consistent schemas. When an object is logged, its model\_dump() output provides a predictable structure for analysis.18 Furthermore, type hints significantly reduce "toil" for developers. The cognitive load of remembering the exact schema of an L3 Episode dictionary is high; the IDE support provided by generics (autocomplete, type checking) offloads this burden to the tooling, allowing developers to focus on higher-order logic.5

## **Part IV: Performance Analysis**

A critical concern in any high-throughput system is the performance overhead of object instantiation. The MAS Memory Layer targets aggressive latency goals: \<5ms for L1 retrieval and \<100ms for L3 search.1

### **4.1 Pydantic V2 Benchmarks**

The project uses Pydantic v2 (specifically 2.8.2), which features a core rewritten in Rust.1 Benchmarks indicate that Pydantic v2 is 4x to 50x faster than v1, with model validation overhead reduced to microseconds.19

| Operation | Implementation | Mean Latency (ms) | Overhead Impact |
| :---- | :---- | :---- | :---- |
| **L1 Retrieval** | Redis Raw | 0.24ms 1 | Baseline |
| **Model Validation** | Pydantic v2 | \~0.01-0.05ms 21 | Negligible |
| **Total L1 Read** | Generic Tier | \~0.30ms | Acceptable (\<1ms target) |

For L1 (Active Context), where throughput is highest (3400+ ops/sec 1), the overhead of validating a simple Turn model is negligible compared to the network I/O of the Redis call. For L2 and L3, which involve complex SQL or Vector queries taking 10-50ms, the microsecond-level overhead of Pydantic is statistically irrelevant.1

### **4.2 Serialization vs. Attribute Access**

The current dict approach requires dictionary lookups (data\['key'\]), which are fast in Python. However, accessing attributes on a Pydantic model (model.key) is also highly optimized in v2. The real cost comes from model\_dump() when serializing back to JSON for the API.18 However, the benchmarks show that even comprehensive serialization of complex nested models is performant enough for the system's needs.13

The critical insight here is that the **safety** gained by validation outweighs the nanosecond-scale performance cost. In a system designed for "complex decision support" 1, correctness is more valuable than raw throughput, provided latency remains within interactive limits (\<100ms).1

## **Part V: Agent Integration and Reasoning Implications**

The ultimate consumer of this memory system is the AI Agent, orchestrated via LangGraph.1 The interface between the agent and the memory tiers is mediated by tools defined in unified\_tools.py.1

### **5.1 Structured Output and "Reasoning-First" Schemas**

Recent research (RT2) validates that LLMs like Gemini 1.5 Pro excel at generating structured output when constrained by schemas.1 The BaseTier refactoring aligns perfectly with this capability. When an agent invokes a tool like memory\_store, it provides structured arguments defined by Pydantic models (MemoryStoreInput).1 If the internal logic also operates on Pydantic models, the entire pipeline—from LLM output to storage—is strongly typed.

### **5.2 Enhancing Agent Metacognition**

Research Topic 5 (RT5) demonstrates that exposing agents to CIAR metadata improves decision-making by 10-20%.1 Agents can reason about the "Certainty" or "Age" of a fact to resolve conflicts.

* *Current State:* The agent receives a dictionary. It must "guess" the keys or rely on prompt descriptions to understand that ciar\_score exists.  
* *Refactored State:* The agent receives a structured object representation (serialized to JSON). The schema of this object can be injected into the system prompt, giving the agent an explicit "manual" for its own memory.1

By returning typed objects, the system can automatically generate precise JSON schemas for the agent's context window using model\_json\_schema().22 This ensures that the agent's understanding of its memory structure is always synchronized with the actual implementation, preventing hallucinations about non-existent metadata fields.1

### **5.3 LangGraph Integration**

LangGraph orchestrates agents as state machines.1 The state is typically a TypedDict or Pydantic model.23 If the memory tools return BaseModel instances, they can be directly embedded into the LangGraph state without conversion. This simplifies the "Unified Tooling" architecture proposed in ADR-007, where tools like memory\_query need to aggregate results from multiple tiers.1 With generics, the aggregator can polymorphically treat L2 Facts and L3 Episodes as MemoryItems, normalizing their scores (as done in UnifiedMemorySystem.query\_memory) with type safety.1

## **Part VI: Implementation Roadmap and Infrastructure Impact**

Implementing this refactor requires a surgical approach to avoid disrupting the 98% complete codebase.1

### **6.1 Refactoring Steps**

1. **Update BaseTier**: Modify src/memory/tiers/base\_tier.py to inherit from Generic and define abstract methods using ![][image1].  
2. **Update Concrete Tiers**:  
   * ActiveContextTier (L1) ![][image3] BaseTier  
   * WorkingMemoryTier (L2) ![][image3] BaseTier\[Fact\]  
   * EpisodicMemoryTier (L3) ![][image3] BaseTier\[Episode\]  
   * SemanticMemoryTier (L4) ![][image3] BaseTier  
3. **Refactor Return Logic**: In each tier's retrieve and query methods, replace return data with return Model.model\_validate(data).  
4. **Update Lifecycle Engines**: Ensure PromotionEngine, ConsolidationEngine, and DistillationEngine expect objects instead of dicts. This simplifies their logic, as they can access fact.content instead of fact\['content'\].1

### **6.2 Infrastructure Considerations**

The project runs on a distributed cluster: development-host (Orchestrator) and local-yaam-host (Data Node).1 The refactoring is purely application-level and does not require changes to the underlying infrastructure (PostgreSQL schemas, Redis keys, etc.). However, it improves the robustness of the interactions *with* this infrastructure. For example, the RedisAdapter uses Hash Tags ({session:ID}) for cluster compatibility.1 The ActiveContextTier can now enforce that the session\_id in the Turn object matches the hash tag in the key, adding a layer of application-side verification to the distributed storage logic.

## **Part VII: Conclusion and Recommendations**

The analysis overwhelmingly supports the refactoring of BaseTier to use Python generics for type-safe return values. While the current dict approach offered initial flexibility, it has become a liability for the system's long-term reliability, maintainability, and cognitive fidelity.

**Key Findings:**

1. **Reliability:** Generics eliminate a vast class of runtime type errors, reducing the error budget consumption and aligning with SRE best practices.5  
2. **Cognitive Fidelity:** Binding tiers to Pydantic models ensures that the CIAR scoring logic is mathematically enforced, preserving the integrity of the agent's reasoning basis.1  
3. **Performance:** The overhead of Pydantic v2 is negligible (\<0.1ms) relative to the system's latency targets and provides significant safety benefits.19  
4. **Developer Velocity:** Explicit contracts reduce toil and cognitive load for developers, accelerating the final push toward the AIMS 2025 submission.1

**Recommendation:**

Proceed immediately with the refactoring of BaseTier to BaseTier. This should be executed as **Phase 2E (Intelligence Layer Refinement)** prior to the final "Phase 3" agent integration tests. This foundational hardening will pay dividends in the complex debugging scenarios anticipated during the multi-agent benchmark evaluation.

### **Detailed Implementation Plan for Refactoring**

The following section outlines the specific steps and code modifications required to execute this refactoring safely.

#### **1\. Define the Generic Interface**

Modify src/memory/tiers/base\_tier.py to introduce the generic type variable.

Python

from typing import Generic, TypeVar, List, Optional, Any  
from abc import ABC, abstractmethod  
from pydantic import BaseModel

\# Define T bound to BaseModel to ensure all returns are Pydantic models  
T \= TypeVar("T", bound=BaseModel)

class BaseTier(ABC, Generic):  
    """  
    Abstract base class for memory tiers with strict type enforcement.  
    """  
      
    @abstractmethod  
    async def retrieve(self, id: str) \-\> Optional:  
        """Retrieve a specific item by ID as a validated model."""  
        pass

    @abstractmethod  
    async def query(self, filters: Dict\[str, Any\]) \-\> List:  
        """Query the tier and return a list of validated models."""  
        pass

6

#### **2\. Update L2 Working Memory Tier**

Modify src/memory/tiers/working\_memory\_tier.py.

Python

class WorkingMemoryTier(BaseTier\[Fact\]):  
      
    async def retrieve(self, fact\_id: str) \-\> Optional\[Fact\]:  
        data \= await self.postgres.retrieve(fact\_id)  
        if not data:  
            return None  
          
        \# Validation happens here. If data is malformed, it raises ValidationError  
        fact \= Fact.model\_validate(data)  
          
        \# Access tracking now uses object attributes, not string keys  
        await self.\_update\_access\_tracking(fact)  
        return fact

This change explicitly links the retrieve method to the Fact model, enabling IDEs to autocomplete fields on the returned object and static analysis tools to verify that fact.ciar\_score is being accessed correctly.1

#### **3\. Update Lifecycle Engines**

The PromotionEngine (src/memory/engines/promotion\_engine.py) currently iterates over dictionaries. It must be updated to handle Fact objects.

Python

\# Before  
if fact\['ciar\_score'\] \>= self.threshold:...

\# After  
if fact.ciar\_score \>= self.threshold:...

This seemingly minor change prevents the "stringly typed" errors discussed in Section 1.3 and allows the engine to leverage methods like fact.calculate\_age\_decay() directly.1

#### **4\. Hardening Tests**

The test suite (tests/memory/test\_working\_memory\_tier.py, etc.) must be updated to assert that returned values are instances of Fact, Episode, etc., rather than dictionaries. This increases the rigor of the test suite (currently 574 tests) by validating the *structure* of the data, not just the *presence* of data.1

By executing this plan, the MAS Memory Layer will transition from a robust prototype to a hardened, enterprise-grade cognitive architecture capable of supporting the ambitious research goals of the AIMS 2025 submission.

# **Detailed Analysis of Research Findings**

The recommendation above relies on a synthesis of specific research topics and system components. The following sections detail the evidence backing this architectural shift.

## **Section A: The Reliability Imperative in MAS**

The transition to autonomous agents introduces non-determinism. Agents "think" and "decide" based on memory. If memory is unreliable, agent behavior becomes erratic.

### **A.1 The Cost of "Context Pollution"**

Research Topic 5 (RT5) highlighted that "Context Pollution"—the inclusion of irrelevant or malformed data in the context window—degrades agent performance significantly.1

* **Data Point:** Agents utilizing CIAR metadata showed a **10-20% improvement** in decision-making accuracy.1  
* **Implication:** We must guarantee that CIAR scores are accurate. A dict allows a score of 1.5 or "high" to slip through due to a bug. A Pydantic Fact model with Field(ge=0.0, le=1.0) *mathematically guarantees* the score is valid.1  
* **Conclusion:** Type safety is not just code hygiene; it is a mechanism for enforcing the *cognitive integrity* of the agent.

### **A.2 SRE Principles: Eliminating Toil**

The Google SRE book defines "toil" as manual, repetitive work devoid of enduring value.9 Debugging KeyError: 'content' exceptions in a distributed system is the definition of toil.

* **Observation:** The current unified\_tools.py implementation manually constructs return strings from dictionary keys.1 This is fragile.  
* **Solution:** Using model.model\_dump\_json() or model.to\_prompt\_string() centralizes serialization logic, removing toil from the tool implementation and ensuring consistency across all agents.1

## **Section B: Infrastructure and Performance Reality**

Is the system fast enough to handle object instantiation?

### **B.1 Redis Latency vs. Model Overhead**

The RedisAdapter (L1) achieves a mean retrieve latency of **0.24ms**.1

* **Comparison:** Pydantic v2 model validation takes approximately **5-50 microseconds** (0.005-0.05ms) for simple models.19  
* **Impact:** Adding 0.05ms to a 0.24ms operation results in \~0.29ms total latency. This is still well below the **5ms** target for L1.1  
* **L3 Comparison:** Qdrant/Neo4j operations take **10-100ms**.1 The overhead here is statistically zero (orders of magnitude less than network jitter).

### **B.2 Distributed Consistency**

The system runs on development-host (127.0.0.1) and local-yaam-host (127.0.0.1).1

* **Challenge:** Data serialization across nodes relies on JSON.  
* **Solution:** Pydantic models handle serialization (model\_dump\_json) and deserialization (model\_validate\_json) natively and efficiently. Using them ensures that the data sent from the Data Node (L3) is exactly what the Orchestrator Node (Agent) expects to receive, preventing subtle serialization bugs that occur with manual json.dumps usage.13

## **Section C: The Path to AIMS 2025**

The project is targeting the **AIMS 2025 (Artificial Intelligence Models and Systems) Conference**.1

### **C.1 Academic Rigor**

Academic codebases are scrutinized for reproducibility and clarity.

* **Current State:** dict returns make the data flow opaque. A reviewer reading engine.py cannot easily see what data is available.  
* **Proposed State:** Generic makes the data flow explicit. WorkingMemoryTier returns Fact. EpisodicMemoryTier returns Episode. This self-documenting nature enhances the "scientific quality" of the codebase.1

### **C.2 Benchmark Validity**

The evaluation plan involves running the **GoodAI LTM Benchmark**.1

* **Requirement:** The benchmark compares "Hybrid Memory" against "Standard RAG".  
* **Advantage:** Strongly typed memory tiers allow for precise instrumentation. We can tag every Fact retrieved with its exact ciar\_score and retrieval\_latency in the Phoenix traces.1 This granular telemetry is essential for generating the empirical results required for the paper.

## **Final Synthesis**

The "Hybrid, Multi-Layered Memory System" is a sophisticated piece of engineering. It has outgrown the flexible but fragile patterns of its initial prototyping phase. The dict\[str, Any\] return type is a vestige of this early stage. Refactoring BaseTier to use Python generics is the necessary maturation step to ensure the system is robust, performant, and rigorous enough for its intended deployment in multi-agent supply chain optimization and its presentation at AIMS 2025\.

The refactoring is feasible, low-risk (given the comprehensive test suite), and high-reward. It should be executed immediately.

**Final Verdict: REFACTOR TO GENERICS.**

#### **Источники**

1. maksim-tsi/mas-memory-layer  
2. Python best practices: Static Typing With Mypy \- Sunscrapers, дата последнего обращения: февраля 4, 2026, [https://sunscrapers.com/blog/python-best-practices-static-typing-with-mypy/](https://sunscrapers.com/blog/python-best-practices-static-typing-with-mypy/)  
3. PEP 484 – Type Hints \- Python Enhancement Proposals, дата последнего обращения: февраля 4, 2026, [https://peps.python.org/pep-0484/](https://peps.python.org/pep-0484/)  
4. PEP 483 – The Theory of Type Hints \- Python Enhancement Proposals, дата последнего обращения: февраля 4, 2026, [https://peps.python.org/pep-0483/](https://peps.python.org/pep-0483/)  
5. Using Generics in Python. If you are using type hints in Python… | by SteveYeah | Medium, дата последнего обращения: февраля 4, 2026, [https://medium.com/@steveYeah/using-generics-in-python-99010e5056eb](https://medium.com/@steveYeah/using-generics-in-python-99010e5056eb)  
6. Generics \- mypy 1.19.1 documentation, дата последнего обращения: февраля 4, 2026, [https://mypy.readthedocs.io/en/stable/generics.html](https://mypy.readthedocs.io/en/stable/generics.html)  
7. Type and TypeVar \- Pydantic, дата последнего обращения: февраля 4, 2026, [https://docs.pydantic.dev/2.0/usage/types/typevars/](https://docs.pydantic.dev/2.0/usage/types/typevars/)  
8. Ebook \- Designing high-quality distributed Cloud-Native applications on Azure \- V1.1.pdf  
9. Site Reliability Engineering How Google Runs Production Systems (Betsy Beyer, Chris Jones, Jennifer Petoff etc.) (Z-Library) (1).pdf  
10. How to make Pydantic Generic model type-safe with subclassed data and avoid mypy errors? \- Stack Overflow, дата последнего обращения: февраля 4, 2026, [https://stackoverflow.com/questions/79816067/how-to-make-pydantic-generic-model-type-safe-with-subclassed-data-and-avoid-mypy](https://stackoverflow.com/questions/79816067/how-to-make-pydantic-generic-model-type-safe-with-subclassed-data-and-avoid-mypy)  
11. covariant type annotation of BaseModel · pydantic pydantic · Discussion \#3459 \- GitHub, дата последнего обращения: февраля 4, 2026, [https://github.com/pydantic/pydantic/discussions/3459](https://github.com/pydantic/pydantic/discussions/3459)  
12. Mypy reports an incompatible supertype error with overridden method \- Stack Overflow, дата последнего обращения: февраля 4, 2026, [https://stackoverflow.com/questions/44656040/mypy-reports-an-incompatible-supertype-error-with-overridden-method](https://stackoverflow.com/questions/44656040/mypy-reports-an-incompatible-supertype-error-with-overridden-method)  
13. Performance \- Pydantic Validation, дата последнего обращения: февраля 4, 2026, [https://docs.pydantic.dev/latest/concepts/performance/](https://docs.pydantic.dev/latest/concepts/performance/)  
14. pydantic.mypy rejects use of covariant type variable for frozen models · Issue \#8607 \- GitHub, дата последнего обращения: февраля 4, 2026, [https://github.com/pydantic/pydantic/issues/8607](https://github.com/pydantic/pydantic/issues/8607)  
15. Mypy disallows overriding a generic type attribute with a property \#18189 \- GitHub, дата последнего обращения: февраля 4, 2026, [https://github.com/python/mypy/issues/18189](https://github.com/python/mypy/issues/18189)  
16. Mypy \- Pydantic Validation, дата последнего обращения: февраля 4, 2026, [https://docs.pydantic.dev/latest/integrations/mypy/](https://docs.pydantic.dev/latest/integrations/mypy/)  
17. Mypy plugin doesn't infer inherited fields' types · Issue \#7422 \- GitHub, дата последнего обращения: февраля 4, 2026, [https://github.com/pydantic/pydantic/issues/7422](https://github.com/pydantic/pydantic/issues/7422)  
18. Serialization \- Pydantic Validation, дата последнего обращения: февраля 4, 2026, [https://docs.pydantic.dev/latest/concepts/serialization/](https://docs.pydantic.dev/latest/concepts/serialization/)  
19. Introducing Pydantic v2 \- Key Features, дата последнего обращения: февраля 4, 2026, [https://pydantic.dev/articles/pydantic-v2](https://pydantic.dev/articles/pydantic-v2)  
20. Benchmarks testing the performance of various releases of Pydantic v2 \- GitHub, дата последнего обращения: февраля 4, 2026, [https://github.com/prrao87/pydantic-benchmarks](https://github.com/prrao87/pydantic-benchmarks)  
21. Pydantic v2 significantly slower than v1 \#6748 \- GitHub, дата последнего обращения: февраля 4, 2026, [https://github.com/pydantic/pydantic/discussions/6748](https://github.com/pydantic/pydantic/discussions/6748)  
22. Models \- Pydantic Validation, дата последнего обращения: февраля 4, 2026, [https://docs.pydantic.dev/latest/concepts/models/](https://docs.pydantic.dev/latest/concepts/models/)  
23. Persistence \- Docs by LangChain, дата последнего обращения: февраля 4, 2026, [https://docs.langchain.com/oss/python/langgraph/persistence](https://docs.langchain.com/oss/python/langgraph/persistence)