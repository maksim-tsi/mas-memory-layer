# **ADR-007: LangGraph Integration Architecture**

**Title:** LangGraph Integration Architecture: Hybrid Tooling, Hierarchical State, and Async Execution
**Status:** Accepted
**Date:** December 28, 2025
**Related:** [ADR-003](003-four-layers-memory.md), [ADR-004](004-ciar-scoring-model.md), [Phase 3 Spec](../specs/spec-phase3-agent-integration.md)

## **1. Context**

Phase 3 focuses on integrating the foundational four-tier memory system with autonomous agents. We have selected **LangGraph** as the orchestration framework due to its stateful, graph-based execution model. However, integrating a complex memory system with LangGraph presents specific architectural challenges identified in our research (RT1, RT4):
1.  **Context Pollution:** Passing global IDs (user_id, session_id) via LLM prompts risks hallucination and wastes tokens.
2.  **Tool Bloat:** Exposing all memory operations as a flat list of tools overwhelms the LLM's reasoning capabilities.
3.  **Concurrency Safety:** Running synchronous tools within an ASGI (FastAPI) environment risks blocking the event loop and losing request context.
4.  **State Conflicts:** Parallel tool execution can lead to race conditions if state updates are not handled via reducers.

## **2. Decision**

We will implement a **Hierarchical, Async-First Agent Architecture** using the following specific patterns:

### **2.1. The `ToolRuntime` Pattern for Context Security (Updated Dec 28, 2025)**

**Note:** This ADR has been updated to reflect the modern LangChain tool pattern. The original `InjectedState` annotation is superseded by `ToolRuntime`, a unified parameter providing tools with access to state, context, store, and streaming capabilities.

We will **strictly prohibit** passing infrastructure IDs (`user_id`, `session_id`, `thread_id`) as explicit arguments in LLM tool schemas. Instead, we will use LangChain's `ToolRuntime` parameter to access these values from the graph state, immutable context, and persistent store.

*   **Why:** Prevents the LLM from hallucinating invalid IDs or cross-contaminating sessions. Reduces input token cost. Provides unified access to state management, persistence, and streaming.
*   **Implementation:**
    ```python
    from langchain.tools import tool, ToolRuntime

    @tool
    async def memory_store(
        content: str, 
        runtime: ToolRuntime  # Hidden from LLM schema
    ) -> str:
        """Store content in memory for the current session."""
        # IDs are trusted because they come from system state, not the model
        session_id = runtime.state["session_id"]  # Mutable graph state
        user_id = runtime.context.user_id          # Immutable context
        
        # Access persistent store for long-term memory
        # store_data = await runtime.store.get(...)
        
        # Stream progress updates
        # await runtime.stream_writer.write({"status": "storing..."})
        
        # ... storage logic ...
        return f"Stored content for session {session_id}"
    ```

**Key `ToolRuntime` Features:**
- **`runtime.state`**: Mutable graph state (messages, counters, session_id)
- **`runtime.context`**: Immutable configuration (user_id, permissions)
- **`runtime.store`**: Persistent key-value store for cross-session memory
- **`runtime.stream_writer`**: Real-time updates to client
- **`runtime.tool_call_id`**: Unique ID for this tool invocation
- **`runtime.config`**: Graph-level configuration

**Legacy Pattern (Still Supported):**
For compatibility with older LangGraph code, the `InjectedState` pattern remains functional:
```python
from typing import Annotated
from langgraph.prebuilt import InjectedState

@tool
async def memory_store(
    content: str, 
    state: Annotated[dict, InjectedState]  # Hidden from LLM schema
):
    session_id = state["session_id"]
    # ... logic ...
```

However, **new code MUST use `ToolRuntime`** for unified access and future compatibility.

### **2.2. Hierarchical Topology (Supervisor & Sub-Graphs)**
We will not implement a single, flat graph. We will use a **Supervisor** topology where a top-level node routes execution to isolated **Sub-Graphs** based on intent.

*   **Top Level:** Manages global state, routing, and final response generation.
*   **Memory Sub-Graph:** A dedicated graph for complex memory operations (e.g., executing a CIAR calculation -> Promotion -> Retrieval loop).
*   **Why:** Encapsulates logic. Prevents "tool confusion" by ensuring the LLM only sees the tools relevant to its current mode (e.g., "Reasoning Mode" vs. "Retrieval Mode").

### **2.3. Hybrid Tool Architecture (Unified + Granular)**
We will expose two distinct layers of tools to the agents:
1.  **Unified Tools:** High-level abstractions (e.g., `memory_query`, `get_context_block`) for general reasoning.
2.  **Granular Tools:** Low-level, tier-specific operations (e.g., `l2_search_facts`, `l3_query_graph`) for "surgical" information gathering.
*   **Why:** Validates the research finding that agents need different granularities of control depending on task complexity.

### **2.4. Async-First Mandate**
All tools and graph nodes **must be implemented as `async def`**.
*   **Why:** Our system runs inside a FastAPI wrapper (ASGI). Blocking synchronous calls will freeze the server and break the high-throughput requirement validated in the benchmarks. This also ensures `contextvars` are propagated correctly for tracing (Arize Phoenix).

### **2.5. State Reducers for Parallel Execution**
The global agent state schema will utilize **Reducers** (specifically `operator.add` for message lists) to handle updates.
*   **Why:** Allows the `ToolNode` to execute multiple retrieval tools in parallel (e.g., querying L3 and L4 simultaneously) without race conditions overwriting the message history.

## **3. Rationale**

These decisions are grounded in the findings from Research Topics RT1 (LangGraph Integration) and RT4 (Context Injection):
*   **RT1** confirmed that `ToolRuntime` (formerly `InjectedState`) is the only secure way to handle multi-tenant context in LangGraph.
*   **RT1** validated that Sub-Graphs are necessary to manage tool complexity as the system scales.
*   **RT4** demonstrated that optimizing the context window (via hidden IDs) reduces latency and cost.

**Update (Dec 28, 2025):**
- LangChain documentation now recommends `ToolRuntime` as the unified pattern for state/context/store access
- Provides better separation between mutable state and immutable context
- Enables native streaming and persistent storage access within tools

## **4. Consequences**

### **Positive**
*   **Security:** Impossible for an agent to "accidentally" read/write to the wrong session ID via hallucination.
*   **Performance:** Non-blocking async I/O ensures the 335 ops/sec throughput of the storage layer translates to agent performance.
*   **Maintainability:** Feature logic is isolated in sub-graphs, preventing a monolithic "God Object" agent.

### **Negative**
*   **Complexity:** Debugging hierarchical graphs is more difficult than flat chains.
*   **Boilerplate:** Requires strict type hinting and Pydantic schemas for all tools.

## **5. Implementation Guidelines**

1.  **Tool Definitions:** Must use `@tool` decorator and include `runtime: ToolRuntime` parameter (hidden from LLM).
2.  **State Definition:** Use `TypedDict` with `Annotated[list, add_messages]` for the conversation history.
3.  **Graph Compilation:** Use `compile(checkpointer=AsyncPostgresSaver)` to ensure persistence.
4.  **Context Access Patterns:**
    - **Mutable state** (session_id, messages): `runtime.state["key"]`
    - **Immutable config** (user_id, permissions): `runtime.context.attr`
    - **Persistent memory** (cross-session): `await runtime.store.get/put(...)`
    - **Streaming** (progress updates): `await runtime.stream_writer.write(...)`
5.  **Legacy Compatibility:** Existing `InjectedState` tools remain functional but should be migrated to `ToolRuntime` during refactoring.

**Example Tool Signature:**
```python
from langchain.tools import tool, ToolRuntime

@tool
async def l2_search_facts(
    query: str,
    min_ciar_score: float = 0.6,
    runtime: ToolRuntime = None  # Hidden from LLM, auto-injected
) -> List[Dict[str, Any]]:
    """Search working memory for facts matching query with minimum CIAR score."""
    session_id = runtime.state["session_id"]
    # ... implementation ...
```