# Concept Document 2: MAS Memory Inspector (The System Capability)

**Goal:** To implement "Glass Box" observability into the *MAS Memory Layer* codebase, allowing researchers (and paper reviewers) to verify the **AIMS'25 Cognitive Lifecycle** claims.

### 1. Core Philosophy: "Cognitive Telemetry"

The system must broadcast its internal state changes (Perception → Promotion → Storage) in real-time, independent of the final text answer.

### 2. Functional Requirements (New Capabilities)

#### **Feature A: The Telemetry Stream (The "MRI Scan")**

The `GoodAIAgent` wrapper must emit a structured event stream.

* **Event 1: Significance Calculation (CIAR):**
    * *Payload:* `{ "input_segment": "...", "ciar_score": 0.85, "decision": "PROMOTE" }`
    * *Goal:* Prove the "Promotion via Calculated Significance" claim.
* **Event 2: Memory Tier Access:**
    * *Payload:* `{ "tier": "L1_REDIS", "operation": "HIT", "latency_ms": 1.2 }`
    * *Goal:* Prove the efficiency hierarchy (L1 vs L3).
* **Event 3: Scratchpad Update:**
    * *Payload:* `{ "scratchpad_before": "...", "scratchpad_after": "..." }`
    * *Goal:* Show the agent "thinking" before answering.

#### **Feature B: "Glass Box" UI Panel**

This is a specific frontend component (React) that consumes the Telemetry Stream. It can be embedded into the GoodAI Benchmark results page (via the "Universal Metadata" feature) or run as a standalone debugger.

* **Visualizer:** A "Layer Activity" indicator.
    * *Green Light:* L1 Active.
    * *Yellow Light:* L2 Consolidating.
    * *Red Light:* L3 Retrieving (High Latency).
* **Significance Heatmap:** Color-code the user's input based on the CIAR score assigned by the agent. Highlighting "Distraction" text in gray and "Core Facts" in red.

#### **Feature C: Experimental Toggles (Ablation Support)**

The System must implement "Feature Flags" in its constructor to support the Benchmark's A/B testing.

* **Code Change:** `UnifiedMemorySystem(enable_promotion=True, enable_l3=False)`
* **Purpose:** Allows the Benchmark to request "Run 1: No Memory" and "Run 2: Full Memory" without you deploying two different codebases.

### 3. Technical Implementation Strategy

* **Instrumentation:** Use a Python decorator `@trace_cognitive_step` on methods like `PromotionEngine.process` and `ActiveContextTier.retrieve`.
* **Protocol:** Pydantic models for Telemetry.
```python
class CognitiveEvent(BaseModel):
    step: str  # "PROMOTION", "RETRIEVAL"
    details: Dict[str, Any]
    timestamp: float
```
* **Exfiltration:** The `LTMAgentWrapper` collects these events during a turn and returns them as the "Metadata_JSON" required by the Benchmark v2.
