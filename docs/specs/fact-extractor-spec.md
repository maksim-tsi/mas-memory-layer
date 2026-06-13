# Task Specification: FactExtractor Debugging & Improvement (Prospective Memory)

**Goal:** Ensure correct extraction of deferred instructions (e.g., *"After responding to X, do Y"*), so they are stored in `L2 Working Memory` and properly appear in the `[ACTIVE STANDING ORDERS]` section of the agent's prompt.

**Context:**
The Agent has successfully learned to count turns (State Tracking is working), but it fails to execute the benchmark instructions because it **does not remember** them. The `[ACTIVE STANDING ORDERS]` section is completely missing from the previous logs, indicating a critical failure at the perception stage (Fact Extraction).

---

## 1. Working Assumptions

Before starting work, we rely on the following assumptions based on the log analysis:

1. **The "Blind Spot" Hypothesis:** `FactExtractor` is currently ignoring user input that contains complex temporal or conditional instructions, classifying them as "chatter" (low impact) or failing to extract them entirely.
2. **The "LLM Silence" Hypothesis:** The model used for extraction (`gemini-2.5-flash-lite`) does not consider the phrase *"Count your response..."* as a fact worthy of preservation because the current system prompt does not sufficiently emphasize *meta-instructions*.
3. **Localization:** The issue resides exclusively within `src/memory/engines/fact_extractor.py` (execution logic) and `src/memory/schemas/fact_extraction.py` (system prompt).

---

## 2. Implementation Plan

### Step 1: Verify Assumptions (Diagnostics)

**Do not apply fixes until you see the problem "face to face" in the logs.**

**Action:**

1. Open `src/memory/engines/fact_extractor.py`.
2. In the `_extract_with_llm` method, immediately after receiving the response from the LLM (`response = ...`), add **detailed logging**:
```python
# Temporary Debug Log
logger.info(f"DEBUG: Input text to extractor: {text[:100]}...")
logger.info(f"DEBUG: Raw LLM Extraction Response: {response.text}")

```


3. Run **only the single test** that was failing (Prospective Memory) using the validation script.

**Expected Result:**
In the logs, you will see that the instruction *"After responding..."* is passed as input, but the LLM response contains either an empty list `[]` or a fact of type `mention`/`entity`, but NOT `instruction`.
*If this is confirmed — proceed to Step 2.*

### Step 2: Strengthen the Prompt (Prompt Engineering)

We need to force the model to react to triggers for deferred actions.

**Action:**

1. Open `src/memory/schemas/fact_extraction.py`.
2. Locate `FACT_EXTRACTION_SYSTEM_INSTRUCTION`.
3. Add an explicit, "aggressive" instruction to look for meta-instructions.

**Example Change (Insert this into the prompt):**

> "CRITICAL: You act as the agent's Executive Function. You MUST extract any user statement that implies a **future action**, **delayed task**, **condition**, or **counting rule** as a `FactType.INSTRUCTION`.
> Examples of MUST-EXTRACT instructions:
> * 'After responding to the following...'
> * 'Count your response to this message...'
> * 'In 5 turns, say...'
> * 'Whenever I say X, you say Y'
> 
> 
> Do NOT ignore these. Assign them High Impact (0.9+) to ensure they are stored."

### Step 3: Verify the Fix

**Action:**

1. Run the same test again (Prospective Memory).
2. Check the `agent_wrapper` logs.

**Success Criteria (Definition of Done):**

1. In the `FactExtractor` logs (from Step 1), a JSON object with type `instruction` is visible.
2. In the agent prompt generation logs (`Generated Prompt`), the following section appears:
```text
## [ACTIVE STANDING ORDERS]
- After responding to the following unrelated user prompts...

```


3. The Agent *actually* executes the instruction (quotes Emerson on the 5th turn).

---

## Important Note for the Assistant

* **Focus:** Work **only** with files in `src/memory/engines/` and `src/memory/schemas/`.
* **Refactoring Prohibition:** Do not change the structure of `AgentWrapper`, database adapters, or `UnifiedMemorySystem` configuration. Our task is to fix the *brain* (the prompt), not the *body* (the code).