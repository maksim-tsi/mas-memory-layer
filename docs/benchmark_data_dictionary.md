# Data Dictionary (Consolidated)

**Status:** Consolidated reference for benchmark data objects (DD-01, DD-02, DD-03)

This document unifies the legacy data dictionaries for the three benchmark variants. The
original files are preserved as archived references.

---

## DD-01: Hybrid Memory System (Full System)

This document provides the formal "ground truth" for the structure of the information flowing through our system. It is the definitive specification for our Pydantic models, ensuring that all agents and system components are speaking the same language. This prevents data-related bugs and makes the entire system more robust and easier to debug.

Here is the Data Dictionary, focusing on the key data objects used in the GoodAI LTM Benchmark run (UC-01).

### **Data Dictionary: Hybrid Memory System**

**Document ID:** DD-01
**Version:** 1.0
**Date:** September 14, 2025

#### **1. Object: `PersonalMemoryState`**

| | |
| :--- | :--- |
| **Object Name:** | `PersonalMemoryState` |
| **Description:** | Represents the private, transient state of a single agent. This object encapsulates the agent's internal "thoughts," intermediate calculations, and data staged for potential long-term storage. It is designed to be frequently read and overwritten within a single task. |
| **Physical Storage:** | Serialized to a JSON string and stored as the value of a single key in the **Operating Memory (Redis)**. The key follows the format `personal_state:{agent_id}`. |

| Field Name | Data Type | Constraints / Example | Description | Required? |
| :--- | :--- | :--- | :--- | :--- |
| `agent_id` | `string` | `planner_agent_001` | The unique, machine-readable identifier for the agent that owns this state object. | **Yes** |
| `current_task_id` | `string` (Optional) | `goodai_test_case_42` | An identifier for the high-level task the agent is currently focused on. Useful for logging and observability. | No |
| `scratchpad` | `JSON Object` (Dict[str, Any]) | `{"status": "retrieving", "query": "..."}` | A volatile key-value store for the agent's intermediate calculations, internal monologue (Chain-of-Thought), or temporary data. This is the agent's primary "thinking" space. | No (defaults to `{}`) |
| `promotion_candidates` | `JSON Object` (Dict[str, Any]) | `{"insight_1": {"content": "User prefers shipping via Port of Hamburg", "confidence": 0.95}}` | A staging area for pieces of information that the agent has deemed potentially valuable for long-term storage. The ConsolidationAgent will evaluate the contents of this field against the EPDL/Consolidation logic. | No (defaults to `{}`) |
| `last_updated` | `string` (ISO 8601 Datetime) | `2025-09-14T18:30:00.123Z` | An automatically managed timestamp indicating when this state object was last written to Redis. | **Yes** (auto-set) |

---

#### **2. Object: `SharedWorkspaceState`**

| | |
| :--- | :--- |
| **Object Name:** | `SharedWorkspaceState` |
| **Description:** | Represents the shared, collaborative state for a single, multi-agent task or event. It serves as the centralized "negotiation table" and source of truth for all agents participating in the resolution of that event. |
| **Physical Storage:** | Serialized to a JSON string and stored as the value of a single key in the **Operating Memory (Redis)**. The key follows the format `shared_state:{event_id}`. |

| Field Name | Data Type | Constraints / Example | Description | Required? |
| :--- | :--- | :--- | :--- | :--- |
| `event_id` | `string` | `evt_a1b2c3d4e5` | A unique identifier for this collaborative event, typically a UUID. | **Yes** (auto-set) |
| `status` | `string` | `active`, `resolved`, `cancelled` | The current status of the collaborative event. Drives agent behavior and triggers the Archiving process when set to a terminal state. | **Yes** |
| `shared_data` | `JSON Object` (Dict[str, Any]) | `{"alert": "Vessel V-123 delayed", "port_congestion": 0.91}` | The core data for the event. This is the "whiteboard" where all agents read and write shared facts and state information. | No (defaults to `{}`) |
| `participating_agents` | `Array of strings` | `["vessel_agent_123", "port_agent_007"]` | A log of the `agent_id`s of all agents that have contributed to this event. Useful for attribution and auditing. | No (defaults to `[]`) |
| `created_at` | `string` (ISO 8601 Datetime) | `2025-09-14T18:00:00.000Z` | Timestamp of when the event was first created. | **Yes** (auto-set) |
| `last_updated` | `string` (ISO 8601 Datetime) | `2025-09-14T18:45:10.500Z` | Timestamp of the last modification to this event's state. | **Yes** (auto-set) |

---

### **How These Documents Form a Coherent Whole**

With these three artifacts, we now have a complete and unambiguous specification for the benchmark run:

1. The **Use Case Specification** describes the narrative flow and high-level requirements.
2. The **Sequence Diagram** visualizes the precise, time-ordered interactions between system components that execute that narrative.
3. This **Data Dictionary** defines the exact structure and meaning of the data objects (`PersonalMemoryState`, `SharedWorkspaceState`) that are passed as messages in that sequence diagram.

An engineer can now take these three documents and implement the benchmark test with a very high degree of confidence that the final code will perfectly match our architectural design.

---

## DD-02: Standard RAG Agent Baseline

For the "Standard RAG Agent" baseline, a full data dictionary is simpler, but it's still a critical document for defining the experiment's constraints.

The key difference is that for this run, we are not using our custom Pydantic models (`PersonalMemoryState`, `SharedWorkspaceState`) because the entire concept of a structured operating memory is intentionally disabled. The "data" flowing through the system is much simpler.

Here is the Data Dictionary for the second benchmark run (UC-02).

### **Data Dictionary: Standard RAG Agent Baseline**

**Document ID:** DD-02
**Version:** 1.0
**Date:** September 14, 2025

#### **1. Object: `BenchmarkTurnPayload`**

| | |
| :--- | :--- |
| **Object Name:** | `BenchmarkTurnPayload` |
| **Description:** | A simple JSON object representing the input from the Benchmark Runner to the MAS for a single conversational turn. It contains the full context and the current user message. |
| **Physical Storage:** | Transient; exists only for the duration of the HTTP request from the Benchmark Runner to the Agent Wrapper. |

| Field Name | Data Type | Constraints / Example | Description | Required? |
| :--- | :--- | :--- | :--- | :--- |
| `history` | `string` | `"User: Hi\nAI: Hello!\nUser: What is..."` | The complete, concatenated text of the entire conversation history up to the current turn. | **Yes** |
| `message` | `string` | `"Can you tell me more about that?"` | The most recent user message that the agent must respond to. | **Yes** |

---

#### **2. Object: `QdrantDocument`**

| | |
| :--- | :--- |
| **Object Name:** | `QdrantDocument` |
| **Description:** | The data structure for a single document stored in the persistent vector store (Qdrant). For this baseline, each "document" represents a single, complete conversational turn. |
| **Physical Storage:** | Stored as a point with a payload in the **Qdrant** collection on the Data Node. The collection is named `goodai_ltm_full_history`. |

| Field Name | Data Type | Constraints / Example | Description | Required? |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `string` (UUID) | `uuid.uuid4()` | A unique identifier for the document point in Qdrant. | **Yes** |
| `content` | `string` | `"User: What is your name?\nAI: My name is AI."` | The concatenated text of a single user-AI exchange. This field is vectorized for semantic search. | **Yes** |
| `turn_number` | `integer` | `42` | The sequential index of this turn within the conversation. Useful for metadata filtering if needed. | **Yes** |
| `timestamp` | `string` (ISO 8601 Datetime) | `2025-09-14T18:30:00.123Z` | The timestamp of when this turn occurred or was indexed. | **Yes** |

---

### **Summary of Key Differences from the "Full System" Data Dictionary:**

- **Absence of `PersonalMemoryState` and `SharedWorkspaceState`:** This is the most critical point. The data dictionary for this run is defined by what it *lacks*. There are no formal data structures for an agent's internal state or for a collaborative workspace, because the baseline architecture does not have these concepts.
- **Simpler Data Flow:** The only data objects are the initial input (`BenchmarkTurnPayload`) and the final storage format (`QdrantDocument`). This reflects the simple, stateless "retrieve-then-read" workflow of the RAG agent.
- **"Dumb" Persistence:** The `QdrantDocument` simply stores the raw conversational turn. There is no concept of "distilled knowledge" or structured, multi-modal archiving. All knowledge is treated as unstructured text.

This Data Dictionary, when read alongside the one for the Full System, provides a clear and formal specification of the architectural differences we are testing in our experiment. It makes the comparison precise and unambiguous.

---

## DD-03: Full-Context Agent Baseline

This document is intentionally simple. Its simplicity is a key part of the story, as it formally documents the brute-force, unstructured nature of this baseline's "memory." When compared to the data dictionary for our full system, it starkly illustrates the architectural differences.

### **Data Dictionary: Full-Context Agent Baseline**

**Document ID:** DD-03
**Version:** 1.0
**Date:** September 14, 2025

#### **1. Object: `BenchmarkTurnPayload`**

| | |
| :--- | :--- |
| **Object Name:** | `BenchmarkTurnPayload` |
| **Description:** | A simple JSON object representing the input from the Benchmark Runner to the MAS for a single conversational turn. It contains the full context and the current user message. |
| **Physical Storage:** | Transient; exists only for the duration of the HTTP request from the Benchmark Runner to the Agent Wrapper. |

| Field Name | Data Type | Constraints / Example | Description | Required? |
| :--- | :--- | :--- | :--- | :--- |
| `history` | `string` | `"User: Hi\nAI: Hello!\nUser: What is..."` | The complete, concatenated text of the entire conversation history up to the current turn. | **Yes** |
| `message` | `string` | `"Can you tell me more about that?"` | The most recent user message that the agent must respond to. | **Yes** |

---

#### **2. Object: `ConversationHistoryLog`**

| | |
| :--- | :--- |
| **Object Name:** | `ConversationHistoryLog` |
| **Description:** | A single, unstructured text block representing the entire linear history of a conversation. It serves as the agent's sole source of memory and is retrieved in its entirety for every conversational turn. It contains no structured metadata or distilled insights. |
| **Physical Storage:** | Stored as a single `STRING` value in the **Operating Memory (Redis)**. The key follows the format `full_history:{conversation_id}`. |

| Field Name | Data Type | Constraints / Example | Description | Required? |
| :--- | :--- | :--- | :--- | :--- |
| `raw_text` | `string` | `"User: What is your name?\nAI: My name is AI.\nUser: ..."` | The complete, undifferentiated text of the conversation. Each new turn (user message and AI response) is appended to the end of this string. | **Yes** |

---

### **Summary of Key Differences from Other Data Dictionaries:**

- **Absence of All Structured Memory Objects:** This data model contains no `PersonalMemoryState`, `SharedWorkspaceState`, `QdrantDocument`, or any other structured object. This is by design, as the baseline lacks any concept of a structured memory architecture.
- **Unstructured, Monolithic Memory:** The `ConversationHistoryLog` represents a single, monolithic block of memory. Unlike the full system which separates and structures knowledge, this baseline treats all information as a simple, linear sequence of text.
- **No Lifecycle Data:** There are no fields for `promotion_candidates`, `status`, or any other metadata related to an information lifecycle. The data is simply recorded; it is not managed, curated, or distilled.

This Data Dictionary completes the full set of engineering documents for our three experimental runs. We now have a comprehensive, unambiguous specification for each test condition.
