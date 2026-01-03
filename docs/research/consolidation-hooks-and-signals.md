This is a crucial operational detail. Since your system is **not** guaranteed to run 24/7 (an "ephemeral" or "on-demand" deployment), relying on a wall-clock Cron job (e.g., "Run at 3 AM") is **dangerous**. If the system is off at 3 AM, the job never runs, and data remains inconsistent.

Here is the robust architectural pattern to replace Cron for intermittent systems: **Lifecycle Hooks + Threshold Triggers.**

### **1. The Answer: Where should the code live?**

**Decision:** **Do NOT create a separate `CatchUpEngine`.**

It should be a method **within `ConsolidationEngine`** (e.g., `run_recovery_sweep()`).
*   **Why:** Logic duplication is the enemy. The logic for "taking a fact and putting it into Neo4j" is complex (embedding, graph linking, temporal invalidation). You want that logic in exactly one place.

### **2. The Triggers: When to run it?**

Instead of "Time of Day" (Cron), use these three triggers:

#### **A. The "Wake-Up" Sweep (Startup Hook)**
**Concept:** Every time the `ConsolidationEngine` container starts up, it assumes it missed work while it was sleeping.
**Logic:**
1.  **On Startup:** Run `run_recovery_sweep()`.
2.  **Query:** `SELECT * FROM l2_facts WHERE consolidated = FALSE ORDER BY created_at ASC`.
3.  **Action:** Process the backlog immediately before starting to listen to the Redis Stream.
**Benefit:** Guarantees eventual consistency. Even if the system was off for a month, it catches up the moment you turn it on.

#### **B. The "Pressure Valve" (Threshold Trigger)**
**Concept:** Don't wait for a timer if the buffer is full.
**Logic:**
*   Monitor the count of unconsolidated facts in L2 (PostgreSQL).
*   **Trigger:** `IF unconsolidated_count >= 50 THEN trigger_batch_consolidation()`.
*   **Benefit:** Prevents memory debt from accumulating during high-load sessions.

#### **C. The "Session End" Signal (Event Trigger)**
**Concept:** When an agent finishes a task, the memory is "stable" and ready for archiving.
**Logic:**
*   **Agent Action:** When an agent reaches a terminal state (e.g., finishes a plan), it publishes a `session_status: "concluded"` event to the Redis Stream.
*   **Engine Action:** Upon receiving this specific event, the `ConsolidationEngine` forces a consolidation run for *that specific session*, regardless of the buffer size.

---

### **3. Implementation Specification**

Here is how to implement this in your `src/memory/engines/consolidation_engine.py`:

```python
class ConsolidationEngine:
    def __init__(self, db_client, ...):
        self.running = False

    async def start(self):
        """Called when the system boots up."""
        self.running = True
        
        # TRIGGER 1: The Wake-Up Sweep
        print("System Start: Running recovery sweep for missed data...")
        await self.run_recovery_sweep()
        
        # Start the continuous stream listener
        asyncio.create_task(self.listen_to_stream())

    async def run_recovery_sweep(self):
        """Scans L2 Postgres for any facts missed while system was offline."""
        # 1. Query L2 for all facts where consolidated=False
        backlog = await self.db.get_unconsolidated_facts()
        
        if backlog:
            print(f"Recovering {len(backlog)} missed facts...")
            # Reuse the standard logic
            await self.process_fact_batch(backlog)

    async def listen_to_stream(self):
        while self.running:
            # Read from Redis Stream (Real-time events)
            events = await self.redis.read_stream(...)
            
            for event in events:
                # TRIGGER 3: Session End
                if event.type == 'session_end':
                    await self.consolidate_session(event.session_id)
                
                # Standard processing
                else:
                    await self.buffer_fact(event)
                    
            # TRIGGER 2: Pressure Valve
            # If buffer gets too big while processing stream
            if self.buffer_size > 50:
                await self.flush_buffer()
```

### **Summary of Recommendation**

1.  **Abandon Cron:** It assumes a server that never sleeps.
2.  **Use Startup Hooks:** The system heals itself every time it boots.
3.  **Use Event Signals:** Let the "End of Session" be the natural trigger for long-term storage, rather than an arbitrary token counter (which is hard to track accurately across distributed components).

This ensures your data is safe whether you run the system for 10 minutes or 10 years.