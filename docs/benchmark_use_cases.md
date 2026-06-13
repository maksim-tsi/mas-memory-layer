# Use Cases (Consolidated)

**Status:** Consolidated reference for UC-01, UC-02, UC-03

This document unifies the legacy UC-01, UC-02, and UC-03 use case specs. The original files are
preserved as archived references.

---

## UC-01: Full System (GoodAI LTM Benchmark)

### **Use Case Specification: Run GoodAI LTM Benchmark Test (Corrected Version)**

| **Use Case Name:** | Execute a Single Test from the GoodAI LTM Benchmark |
| :--- | :--- |
| **ID:** | UC-01 |
| **Actors:** | Benchmark Runner (Script), **MAS (Full System)**, `PlannerAgent`, `ConsolidationAgent`, **UnifiedMemorySystem** |
| **Description:** | The system processes a single turn from a long-running conversational test within the GoodAI LTM Benchmark. This demonstrates the system's ability to retrieve relevant information from a long, noisy history, synthesize it with the current context, generate a correct response, and update its memory state for future turns. |
| **Preconditions:** | 1. The full MAS, including the Asymmetric "Orchestrator/Data Node" infrastructure, is deployed and all services (Redis, Qdrant, Neo4j, Typesense, PostgreSQL) are running and accessible. <br> 2. The `UnifiedMemorySystem` is instantiated with the "Full System" configuration, connecting it to all live backend services. <br> 3. An "Agent Wrapper" API endpoint is running on the Orchestrator Node, ready to receive requests from the benchmark script. <br> 4. The GoodAI LTM Benchmark dataset and runner script are available. |
| **Postconditions:** | 1. The agent's final answer is returned to the Benchmark Runner for scoring. <br> 2. The state of the Operating Memory (L1/L2) and potentially the Persistent Knowledge Layer (L3) is updated. <br> 3. Detailed instrumentation logs for the entire transaction are written to the observability store (e.g., Arize Phoenix via PostgreSQL) for later analysis. |

---

| **Step** | **Action Description & Component Interaction** | **Requirements for this Step** |
| :--- | :--- | :--- |
| 1. **Initiation** | The **Benchmark Runner** script sends an HTTP request to the Agent Wrapper. The request payload contains the full conversational history and the latest user message. | - Agent Wrapper must expose a stable, well-defined API endpoint (e.g., `/run_turn`). <br> - Wrapper must correctly parse the benchmark's JSON payload format. |
| 2. **Task Delegation** | The Agent Wrapper forwards the request to the primary reasoning agent within the MAS, the **`PlannerAgent`**. The `PlannerAgent` is tasked with generating a correct response. | - The MAS must have a defined routing mechanism to assign incoming tasks. <br> - The `PlannerAgent` must be instantiated and in a ready state to accept tasks. |
| 3. **Internal State Retrieval (L1/L2)** | The **`PlannerAgent`** calls `memory.get_personal_state()`. The **`UnifiedMemorySystem`** handles this by retrieving the agent's `PersonalMemoryState` object from the **Operating Memory (Redis)** on the local Orchestrator Node. | - `UnifiedMemorySystem` must have a live connection to the Redis client. <br> - **Performance:** This local Redis GET operation must have sub-millisecond latency (<0.1ms). |
| 4. **Tiered Knowledge Retrieval (L3)** | The **`PlannerAgent`** determines it needs long-term knowledge. It calls `memory.query_knowledge()` (e.g., for 'vector' and 'graph'). The **`UnifiedMemorySystem`** delegates these calls to the **`KnowledgeStoreManager`**, which makes **network calls** to the Data Node to query the **Persistent Knowledge Layer**. | - `PlannerAgent` logic must be capable of formulating effective retrieval queries. <br> - A stable, low-latency network connection must exist between the Orchestrator and Data nodes. <br> - L3 databases (Qdrant, Neo4j) must be running, indexed, and capable of serving queries with acceptable network latency (target <50ms). |
| 5. **Synthesis & Response Generation** | The **`PlannerAgent`** receives the retrieved knowledge chunks. It synthesizes this context with the conversational history and its own state, assembles a final prompt, and calls the LLM to generate a response. | - **Agent Capability:** The agent's prompt template must be robust enough to synthesize information from multiple, potentially conflicting sources. <br> - The total assembled context must not exceed the LLM's context window limit. |
| 6. **Update Working Memory (L1/L2)** | The **`PlannerAgent`** updates its `PersonalMemoryState` object (e.g., updating its `scratchpad`). It then calls `memory.update_personal_state()`. The **`UnifiedMemorySystem`** serializes and writes this new state back to the **Operating Memory (Redis)**. | - **Performance:** This local Redis SET operation must have sub-millisecond latency. <br> - The state object must be serializable to JSON. |
| 7. **Asynchronous Consolidation (L3)** | A background **`ConsolidationAgent`** is triggered. It reads the updated `PersonalMemoryState`, applies its EPDL/Consolidation logic, and if necessary, calls the **`KnowledgeStoreManager`** to write updated knowledge to the **Persistent Knowledge Layer** on the Data Node. | - **Architectural:** This process **must** run asynchronously or with low priority to avoid blocking the main reasoning loop of the `PlannerAgent`. <br> - **Agent Capability:** The `ConsolidationAgent` must have a clearly defined logic for deciding whether to ADD, UPDATE, or NO-OP on a piece of knowledge. |
| 8. **Finalization** | The **`PlannerAgent`** returns its final generated text response to the Agent Wrapper, which sends it back to the **Benchmark Runner** via the HTTP response. | - The response format must strictly adhere to the schema expected by the benchmark's scoring script. |

---

## UC-02: Standard RAG Agent Baseline

### **Use Case Specification: Run GoodAI LTM Benchmark with Standard RAG Agent**

| **Use Case Name:** | Execute a Single Test from the GoodAI LTM Benchmark (Standard RAG Baseline) |
| :--- | :--- |
| **ID:** | UC-02 |
| **Actors:** | Benchmark Runner (Script), **MAS (Standard RAG Baseline)**, `RAGAgent`, **UnifiedMemorySystem** |
| **Description:** | The system processes a single turn from the GoodAI LTM Benchmark using a conventional, single-layer RAG agent. This baseline serves as a direct comparison to evaluate the performance gains of the full hybrid memory architecture. The agent is stateless and relies on a single vector store for all memory operations. |
| **Preconditions:** | 1. The infrastructure is deployed. A single vector store (Qdrant) is available on the Data Node to act as the sole memory layer. <br> 2. The `UnifiedMemorySystem` is instantiated with the "Standard RAG" configuration. In this mode, it bypasses all Operating Memory and Consolidation logic, routing all queries directly to the single Qdrant collection. <br> 3. The Agent Wrapper API endpoint is running. <br> 4. For each test, the *entire* conversational history is pre-loaded and indexed into the Qdrant collection. |
| **Postconditions:** | 1. The agent's final answer is returned to the Benchmark Runner for scoring. <br> 2. The state of the single vector store is updated with the new conversational turn. <br> 3. Instrumentation logs for the transaction are written to the observability store. |

---

| **Step** | **Action Description & Component Interaction** | **Requirements for this Step** |
| :--- | :--- | :--- |
| 1. **Initiation** | The **Benchmark Runner** sends an HTTP request to the Agent Wrapper with the full history and the latest user message. | - Agent Wrapper must expose the same API endpoint (`/run_turn`) as UC-01. <br> - Wrapper must correctly parse the benchmark's JSON payload. |
| 2. **Task Delegation** | The Agent Wrapper forwards the request to the `RAGAgent`. | - The MAS is configured to route all incoming tasks directly to the `RAGAgent`. |
| 3. **Internal State Retrieval** | The **`RAGAgent`** performs **no action** to retrieve internal state. By design, this baseline is stateless and begins each turn with a blank slate. | - **Architectural Constraint:** The agent's logic must *not* depend on any persistent internal state between turns (i.e., no concept of a Personal Scratchpad). |
| 4. **Knowledge Retrieval** | The **`RAGAgent`** executes a simple, single-pass retrieval strategy: <br> a) It takes the latest user message as the query. <br> b) It calls `memory.query_knowledge(store_type='vector', ...)` once. <br> c) The **`UnifiedMemorySystem`** (in its baseline configuration) makes a **network call** to the Data Node to perform a semantic search against the single **Qdrant** collection containing the entire history. | - The Qdrant collection must be pre-indexed with the full conversational history for each test. <br> - **Performance:** This single, large query is expected to have higher latency than the L2 cache lookups in the Full System, as it must search over a much larger and potentially noisier dataset. |
| 5. **Synthesis & Response Generation** | The **`RAGAgent`** receives the retrieved text chunks. It synthesizes this context with the latest user message, assembles a prompt, and calls the LLM to generate a response. | - **Agent Capability:** The agent's prompt engineering must be robust enough to handle potentially noisy or less relevant retrieved chunks from the single-pass retrieval. |
| 6. **Update Working Memory** | The **`RAGAgent`** performs **no action** to update a working memory. It does not maintain any transient state after the response is generated. | - **Architectural Constraint:** The system is intentionally configured without an L1/L2 Operating Memory layer for the agent to write to. |
| 7. **Asynchronous Consolidation** | This step is **not applicable** for the Standard RAG baseline. The new conversational turn (user message + AI response) is simply appended and re-indexed into the single Qdrant collection for the next turn. | - **Architectural Constraint:** The system has no concept of a multi-layered memory or an intelligent consolidation process. New data is added indiscriminately. |
| 8. **Finalization** | The **`RAGAgent`** returns its final generated text response to the Agent Wrapper, which sends it back to the **Benchmark Runner**. | - The response format must strictly adhere to the schema expected by the benchmark's scoring script. |

---

## UC-03: Full-Context Agent Baseline

This Use Case is designed to represent a theoretical "best case" for accuracy, but a "worst case" for efficiency. It serves as a powerful benchmark to demonstrate *why* sophisticated memory architectures are necessary in the first place. By comparing our full system to this baseline, we can make a clear, quantitative argument about the cost-performance trade-offs.

Here is the detailed Use Case Specification for the third experimental run.

### **Use Case Specification: Run GoodAI LTM Benchmark with Full-Context Agent**

| **Use Case Name:** | Execute a Single Test from the GoodAI LTM Benchmark (Full-Context Baseline) |
| :--- | :--- |
| **ID:** | UC-03 |
| **Actors:** | Benchmark Runner (Script), **MAS (Full-Context Baseline)**, `FullContextAgent`, **Redis** |
| **Description:** | The system processes a single turn from the GoodAI LTM Benchmark using a naive "infinite context" agent. This baseline appends the entire conversational history to the LLM's context for every turn, simulating a system with a theoretically perfect but practically inefficient memory. It is designed to establish an upper bound for accuracy while highlighting the severe latency and cost problems that our hybrid architecture solves. |
| **Preconditions:** | 1. The infrastructure is deployed. A Redis instance is available on the Orchestrator Node to act as a simple list store for the conversation history. <br> 2. The MAS is instantiated with the "Full-Context" configuration. The `UnifiedMemorySystem` is bypassed entirely. <br> 3. The Agent Wrapper API endpoint is running. |
| **Postconditions:** | 1. The agent's final answer is returned to the Benchmark Runner for scoring. <br> 2. The new conversational turn is appended to the history list in Redis. <br> 3. Instrumentation logs, particularly latency and token counts, are written to the observability store. |

---

| **Step** | **Action Description & Component Interaction** | **Requirements for this Step** |
| :--- | :--- | :--- |
| 1. **Initiation** | The **Benchmark Runner** sends an HTTP request to the Agent Wrapper with the full history and the latest user message. | - Agent Wrapper must expose the same API endpoint (`/run_turn`) as UC-01/UC-02. <br> - Wrapper must correctly parse the benchmark's JSON payload. |
| 2. **Task Delegation** | The Agent Wrapper forwards the request to the `FullContextAgent`. | - The MAS is configured to route all incoming tasks directly to the `FullContextAgent`. |
| 3. **Internal State Retrieval** | The **`FullContextAgent`** performs **no action** to retrieve a structured internal state. Its only "state" is the full, linear conversation history. | - **Architectural Constraint:** The agent's logic is stateless and does not use `PersonalMemoryState`. |
| 4. **Knowledge Retrieval** | The **`FullContextAgent`** performs a simple but massive retrieval: <br> a) It connects to **Redis** on the local Orchestrator Node. <br> b) It retrieves the *entire* conversational history, which is stored as a single, long string or list. | - **Performance:** While the Redis call itself is fast, retrieving and holding a potentially massive string (e.g., 120k+ tokens worth of text) in memory can be resource-intensive. |
| 5. **Synthesis & Response Generation** | The **`FullContextAgent`** performs a naive synthesis: <br> a) It concatenates the entire retrieved history with the latest user message. <br> b) This complete, massive text block is sent as a single prompt to the LLM to generate a response. | - **Architectural Constraint:** This step is intentionally inefficient and costly. It will consume a very large number of tokens for both the prompt and the generation. <br> - **Performance:** The time-to-first-token is expected to be extremely high due to the large prompt size. The system is likely to hit API rate limits or context window limits on longer tests. |
| 6. **Update Working Memory** | The **`FullContextAgent`** performs **no action** to update a structured working memory. | - **Architectural Constraint:** No L1/L2 Operating Memory layer is used. |
| 7. **Asynchronous Consolidation** | This step is **not applicable**. The agent's only memory update is to append the new conversational turn (user message + AI response) back to the single history list in **Redis**. | - **Architectural Constraint:** The system has no concept of a multi-layered memory or knowledge distillation. All information is treated as a single, undifferentiated stream. |
| 8. **Finalization** | The **`FullContextAgent`** returns its final generated text response to the Agent Wrapper, which sends it back to the **Benchmark Runner**. | - The response format must strictly adhere to the schema expected by the benchmark's scoring script. |
