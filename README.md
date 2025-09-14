# A Hybrid, Multi-Layered Memory System for Advanced Multi-Agent Systems

This repository contains the source code and architectural documentation for a novel, multi-layered memory architecture designed to enable state-of-the-art performance in Multi-Agent Systems (MAS) for complex decision support, with a specific focus on logistics and supply chain management.

This work is being developed in preparation for a submission to the **AIMS 2025 (Artificial Intelligence Models and Systems) Conference**.

## 1. Abstract & Core Problem

Standard Large Language Model (LLM) agents are often limited by their stateless nature and finite context windows. In complex, dynamic domains like supply chain management, these limitations prevent agents from performing sophisticated, long-term reasoning and effective real-time collaboration.

This project addresses this critical gap by introducing a hybrid memory architecture that provides agents with a cognitive framework inspired by human memory. The system cleanly separates high-speed, volatile "working memory" from a durable, structured "long-term memory," enabling a group of specialized agents to reason individually, collaborate seamlessly, and learn from their collective experience.

## 2. Core Architectural Principles

The design of this system is founded on five core principles that collectively enable advanced agentic capabilities:

1.  **Computational State Persistence:** Memory serves as an active computational workspace, allowing agents to persist and manipulate intermediate states for complex, multi-step reasoning.
2.  **Collaborative Workspace:** The system provides a shared, negotiable state space where multiple agents can jointly construct, modify, and agree upon solutions in real-time.
3.  **Structured Reasoning for High-Stakes Reliability:** It enforces structured, auditable reasoning schemas (Schema-Guided Reasoning) to ensure safety, compliance, and predictable performance in mission-critical domains.
4.  **Promotion via Calculated Significance:** An intelligent information lifecycle engine promotes information from private to shared memory only when its calculated significance (based on certainty, impact, and criticality) exceeds a dynamic threshold.
5.  **Archiving via Knowledge Distillation:** The system actively learns by "distilling" resolved events from shared memory into high-value assets (patterns, metrics, relationships) that are stored in a specialized, persistent knowledge layer for future strategic use.

## 3. System Architecture

The architecture is composed of two primary layers, unified by a single access facade:

![System Architecture Diagram](docs/architecture.png)
*(Self-referential note: It would be best to generate this Mermaid diagram as an image and place it in a `docs` folder)*

```mermaid
graph TD
    subgraph "Multi-Agent System (LangGraph Orchestrator)"
        A1[Vessel Agent]
        A2[Port Agent]
        A3[Customs Agent]
    end

    subgraph "Unified Memory System (Single Facade)"
        subgraph "Operating Memory Layer (Redis)"
            direction LR
            P[Personal Scratchpads]
            SWS[Shared Workspace]
        end

        subgraph "Persistent Knowledge Layer"
            direction LR
            VEC[(Qdrant)]
            GPH[(Neo4j)]
            SRCH[(Meilisearch)]
            REL[(PostgreSQL)]
        end
    end

    A1 & A2 & A3 -- "Unified API" --> Unified Memory System

```

### Components

*   **Operating Memory Layer (Redis):** Serves as the high-speed, volatile working memory.
    *   **Personal Scratchpads (Redis Hashes):** Private, isolated state for each agent.
    *   **Shared Workspace (Redis Hashes & Pub/Sub):** The real-time "negotiation table" for inter-agent collaboration.

*   **Persistent Knowledge Layer (Specialized Databases):** The system's long-term memory, where distilled knowledge is archived.
    *   **Qdrant (Vector Store):** Stores experiential patterns for semantic similarity search.
    *   **Neo4j (Graph Store):** Stores entities and relationships for causal and relational analysis.
    *   **Meilisearch (Search Store):** Stores operational knowledge (e.g., protocols, documents) for fast full-text search.
    *   **PostgreSQL (Relational Store):** Stores structured metrics and auditable event logs.

*   **Unified Memory System (`UnifiedMemorySystem`):** A single, clean facade that provides agents with a unified interface for all memory operations, intelligently routing requests to the appropriate underlying layer.

## 4. Code Structure

The repository is organized into a modular and decoupled structure:

```
.
├── memory_system.py          # The core UnifiedMemorySystem facade
├── knowledge_store_manager.py # The facade for the persistent knowledge layer
|
├── clients/
│   ├── __init__.py
│   ├── vector_store_client.py   # Qdrant client
│   ├── graph_store_client.py    # Neo4j client
│   └── search_store_client.py   # Meilisearch client
|
├── examples/
│   └── logistics_simulation.py # A demo script showing the system in action
|
└── README.md
```

## 5. Getting Started

### Prerequisites

*   Python 3.9+
*   Docker and Docker Compose
*   An active Python virtual environment

### 1. Set Up Backend Services

This project requires Redis, Qdrant, Neo4j, and Meilisearch. A `docker-compose.yml` file is provided for a one-command setup.

```bash
# This will start all required database services in the background
docker-compose up -d
```

### 2. Install Dependencies

Install the required Python packages from `requirements.txt`.

```bash
pip install -r requirements.txt
```

### 3. Run the Demonstration

The `examples/logistics_simulation.py` script provides a concrete demonstration of the memory system in action, simulating the collaborative resolution of a supply chain disruption.

```bash
python examples/logistics_simulation.py
```

## 6. How to Use

The core of the system is the `UnifiedMemorySystem` class. An agent interacts with it through a simple and clean API.

```python
# 1. Initialize all clients and the unified system
# (See examples/logistics_simulation.py for full setup)
memory = UnifiedMemorySystem(redis_client, knowledge_manager)

# 2. An agent uses its personal (short-term) memory
agent_id = "port_agent_007"
state = memory.get_personal_state(agent_id)
state.scratchpad["congestion_level"] = 0.91
memory.update_personal_state(state)

# 3. An agent queries the persistent (long-term) knowledge layer
past_patterns = memory.query_knowledge(
    store_type="vector",
    query_text="Find similar congestion events from last quarter"
)

# 4. An agent queries the graph knowledge base
vessel_info = memory.query_knowledge(
    store_type="graph",
    query_text="MATCH (v:Vessel {id: 'V-123'}) RETURN v.name, v.capacity"
)
```

## 7. Future Work & Contributions

This architecture provides a robust foundation for building highly capable multi-agent systems. Future research will focus on:

*   **Implementing the CIAR/EPDL Lifecycle Engine:** Building the intelligent logic for automatic information promotion and knowledge distillation.
*   **Integration with LangGraph:** Integrating this memory system as the backend for a stateful LangGraph orchestrator.
*   **Advanced Benchmarking:** Evaluating the system's performance on standardized logistics and supply chain management benchmarks.

Contributions and feedback are welcome. Please open an issue to discuss any proposed changes or enhancements.