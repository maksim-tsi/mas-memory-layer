This is a decisive architectural choice. We are weighing **Producer Atomicity** (writing data + event together) against **Consumer Complexity** (reading from dynamic sources).

**Decision:**
**Use a Single Global Stream: `{mas}:lifecycle`.**

Do **not** use per-session streams for lifecycle events.

### **The Reasoning: Why Per-Session Streams Fail the Consumer**

If you use `{session:101}:lifecycle`, `{session:102}:lifecycle`, etc.:
1.  **The Consumer Problem:** Redis Streams **do not support pattern matching** (e.g., you cannot `XREAD keys session:*:lifecycle`).
2.  **The Discovery Trap:** Your `ConsolidationEngine` would need to know the ID of every active session instantly to subscribe to it. You would need a separate mechanism just to manage the list of streams to read from. This introduces massive, unnecessary complexity.
3.  **Resource Waste:** You would potentially have thousands of tiny, empty streams rather than one active pipeline.

### **The Solution: The Global Firehose**

By using a single global stream, your `ConsolidationEngine` becomes simple and robust: it connects to **one** key and processes events for **all** sessions as they arrive.

#### **Key Implementation Details (Crucial)**

1.  **The Key Name:** Use **`{mas}:lifecycle`**.
    *   **Why the `{}`?** Even though it's global, using a Hash Tag ensures this stream lives on a deterministic shard in your Redis Cluster. It prevents "CROSSSLOT" errors if you ever try to interact with this stream alongside other global system keys (like a `{mas}:status` key).

2.  **The Trade-off (Atomicity):**
    *   *The Consequence:* You cannot use a Lua script to atomically "Update Session L1 State" AND "Push to Global Stream" in one step, because `{session:101}` and `{mas}` will likely reside on different physical Redis nodes.
    *   *The Mitigation:* This is acceptable. Lifecycle events are, by definition, **asynchronous side effects**.
        *   **Step 1:** Agent updates L1 State (High Priority).
        *   **Step 2:** Agent pushes to `{mas}:lifecycle` (Fire and Forget).
        *   If Step 2 fails, the worst case is a delayed consolidation, which your **"Wake-Up Sweep"** (discussed previously) will catch anyway.

### **Updated `NamespaceManager` Code**

Here is how to implement this decision:

```python
class NamespaceManager:
    # ... existing session keys ...

    @staticmethod
    def lifecycle_stream() -> str:
        """
        Global stream for all lifecycle events across all sessions.
        Uses {mas} hash tag to pin to a specific cluster slot.
        """
        return "{mas}:lifecycle"

    # NOTE: REMOVE the session_id parameter from this method signature
    # compared to the previous version.
```

### **Summary**

*   **Producer (Agents):** Writes to `{mas}:lifecycle`.
*   **Consumer (Engines):** Reads from `{mas}:lifecycle` via Consumer Group.
*   **Safety:** The "Wake-Up Sweep" protects you against the rare case where the non-atomic write fails.