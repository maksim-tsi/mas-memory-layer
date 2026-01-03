This is a classic distributed systems trade-off: **Memory Safety (RAM)** vs. **Data Durability (Time)**.

Given our specific infrastructure (**Node 1 with 32GB RAM shared between Agents and Redis**) and our specific use case (**Lifecycle Events**), my grounded recommendation is:

**Use `MAXLEN` with the `~` (approximate) modifier.**

Here is the detailed reasoning, the math to justify the limit, and the specific implementation strategy.

---

### **1. The Recommendation: Cap by Count, Not Time**

**Decision:**
Use `XADD key MAXLEN ~ 50000 * values`.

**Why `MAXLEN` (Count) over `MINID` (Time)?**
*   **Safety First:** Your Node 1 is the "Brain." If Redis consumes all 32GB of RAM because a bug caused an event flood (e.g., an agent loop generating 10k events/sec), the entire Orchestrator Node will crash, killing your Agents and n8n. `MAXLEN` provides a hard ceiling on memory usage. `MINID` does not protect against volume spikes.
*   **Predictability:** In Redis, memory is the scarcest resource. You can predict that 50,000 small JSON events will cost $\approx$ 50-100MB of RAM. You cannot predict the RAM cost of "1 hour of data" if the throughput fluctuates.

**Why the `~` (Approximate) modifier?**
*   **Performance:** `XADD ... MAXLEN 10000` (exact trimming) forces Redis to perform expensive cleanup operations on *every single write*.
*   **Optimization:** `XADD ... MAXLEN ~ 10000` tells Redis: "Trim it when you can efficiently remove a whole macro-node, as long as I have *at least* 10,000 entries." This makes the operation nearly as fast as a standard write.

---

### **2. Calculating the "Magic Number"**

How big should the buffer be? Let's do the math based on your benchmarks.

*   **Benchmark Throughput:** ~335 ops/sec (System Max).
*   **Realistic Lifecycle Load:** Likely significantly lower (e.g., 10-50 events/sec average), but let's plan for bursts.
*   **Recovery Window:** If your `ConsolidationEngine` crashes, how much time do you need to restart it before you start losing data? Let's say **15 minutes**.

$$ \text{Buffer Size} = \text{Ops/Sec} \times 60 \text{ sec} \times \text{Minutes} $$
$$ \text{Buffer Size} = 50 \text{ ops/s} \times 60 \times 15 = 45,000 \text{ events} $$

**Recommendation:** Set **`MAXLEN ~ 50000`**.
*   **RAM Cost:** Extremely low ($\approx$ 25-50MB).
*   **Safety:** Guarantees you can survive a 15-minute outage of your background workers during high load, or hours during normal load.

---

### **3. Implementation Strategy**

#### **A. In the `NamespaceManager` (Producer Side)**

You don't need to change the consumer. You enforce this at the point of creation.

```python
# src/memory/namespace.py (or wherever you wrap Redis)

async def publish_lifecycle_event(self, session_id: str, event_data: dict):
    stream_key = self.lifecycle_stream(session_id)
    
    # Enforce retention on write
    # MAXLEN ~ 50000 keeps the stream lean automatically
    await self.redis.xadd(
        stream_key, 
        event_data, 
        maxlen=50000, 
        approximate=True  # This adds the '~'
    )
```

#### **B. The "Fail-Safe" Pattern (Consumer Side)**

Since `MAXLEN` implies that data *will* eventually be deleted even if it hasn't been processed (e.g., if the engine is down for 2 days), you need a **Safety Net**.

*   **Scenario:** The `ConsolidationEngine` (Consumer) crashes over the weekend. The stream hits 50k events and trims the oldest ones. Data is lost.
*   **The Fix:** Implement a **"Catch-Up" Cron Job**.
    *   The Stream is for **Real-Time** reactivity.
    *   A nightly (or hourly) Cron Job scans the L2 PostgreSQL table for any facts where `consolidated = false` and older than X hours.
    *   This ensures that even if the Stream drops messages, the system is **eventually consistent**.

### **Summary**

1.  **Policy:** **`MAXLEN ~ 50000`**.
2.  **Rationale:** Protects Node 1 RAM from spikes; maintains high write performance.
3.  **Safety Net:** Ensure your `ConsolidationEngine` has a fallback query to catch missed items, so the Stream doesn't become a single point of failure.