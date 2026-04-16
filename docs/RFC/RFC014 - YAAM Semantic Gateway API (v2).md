# RFC-014: YAAM Semantic Gateway API (v2)

**Status:** Proposed  
**Date:** 2026-04-15  
**Authors:** SCM-MAS Core Team  
**Scope:** Memory Substrate (YAAM) ↔ Orchestrator (TRA) Contract  

## 1. Introduction
This RFC defines the **Semantic Gateway API (v2)**, a high-level interface designed to decouple cognitive reasoning from semantic storage operations. 

### 1.1 The Brain-Spinal Cord Analogy
* **TRA (The Brain):** Responsible for high-level logic, SCM domain reasoning, multi-agent consensus, and task execution.
* **YAAM (The Spinal Cord):** Responsible for "reflexive" semantic operations: transforming Natural Language (NL) into vectors, generating Cypher/SQL queries, and performing high-performance retrieval across L1–L4 tiers.

## 2. Design Principles
1.  **Semantic Offloading:** The Orchestrator (TRA) shall NOT generate embeddings or Cypher queries. It delegates these tasks to YAAM.
2.  **Strict Provenance:** Every write/read operation must carry `session_id`, `agent_id`, and `task_id` to prevent "contextual spaghetti" in multi-agent environments.
3.  **Traceability:** YAAM must propagate the incoming `trace_id` to all internal LLM/Embedding calls for end-to-end observability in Phoenix.
4.  **Role Isolation:** YAAM acts as a translator and retriever. It does NOT perform reasoning or final decision-making.

## 3. API Specification

### 3.1 Working Memory (L2 Scratchpad)
**Endpoint:** `POST /v2/semantic/l2/facts`  
**Purpose:** Synchronous state sharing between agents within a single session.

* **Request Body:**
    ```json
    {
      "session_id": "string",
      "task_id": "string",
      "agent_id": "string",
      "action": "store | retrieve",
      "content": "string (optional for retrieve)"
    }
    ```

### 3.2 Knowledge Assimilation (L3 Store)
**Endpoint:** `POST /v2/semantic/l3/assimilate`  
**Purpose:** Transforming NL observations into long-term Episodic memory (Vector + Graph). YAAM handles embedding generation and entity extraction.

* **Request Body:**
    ```json
    {
      "session_id": "string",
      "agent_id": "string",
      "text_to_assimilate": "string",
      "domain_tags": ["string"],
      "metadata": { "trace_id": "hex_string" }
    }
    ```

### 3.3 Semantic Retrieval (L3 Query)
**Endpoint:** `POST /v2/semantic/l3/query`  
**Purpose:** Retrieving relevant prior knowledge using NL. YAAM performs vector search (Qdrant) and graph traversal (Neo4j).

* **Request Body:**
    ```json
    {
      "agent_id": "string",
      "nl_query": "string",
      "top_k": 3,
      "filters": { "task_id": "string (optional)" }
    }
    ```
* **Response:** Returns a list of facts with a `provenance` block containing the original `agent_id` and `session_id`.

### 3.4 Final Consensus Archiving (L4 Finalize)
**Endpoint:** `POST /v2/semantic/l4/finalize`  
**Purpose:** Storing the final verified result of the MAS consensus in full-text searchable storage (Typesense).

* **Request Body:**
    ```json
    {
      "task_id": "string",
      "session_id": "string",
      "title": "string",
      "final_artifact": "string",
      "consensus_metadata": { "votes": "int", "disagreements": "string" }
    }
    ```

## 4. Operational Requirements
* **Authentication:** Bearer Token via `YAAM_AGENT_API_KEY`.
* **Isolation:** Data written in one `session_id` to L1/L2 must be isolated. L3/L4 are globally searchable but must return provenance metadata.
* **Fault Handling:** If the internal LLM for Cypher/Vector generation fails, YAAM returns a `502 Bad Gateway` with the specific error from the LLM provider.