# Phase 1 Implementation Spec: Cognitive Telemetry Refactoring

**Context:** We are preparing the `mas-memory-layer` for the AIMS'25 "Glass Box" evaluation.
**Goal:** Implement the "Cognitive Telemetry" infrastructure and refactor models to capture LLM reasoning.
**Prerequisite for:** Building the Inspector UI (Concept 2).

## 1. New Module: Telemetry Infrastructure

**File:** `src/common/telemetry.py` (Create New)

**Requirement:** Implement a non-blocking, async telemetry system using Pydantic v2.

```python
import asyncio
import logging
from datetime import datetime, UTC
from typing import Any, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class CognitiveEvent(BaseModel):
    """
    Represents a discrete cognitive decision or operation within the memory system.
    Used for 'Glass Box' visualization in the Inspector UI.
    """
    event_type: Literal[
        "PROMOTION",        # L1 -> L2 Promotion decision
        "RETRIEVAL",        # Memory Tier Access
        "FILTER_REJECT",    # Item discarded by CIAR/Threshold
        "SCRATCHPAD_UPDATE" # Agent working memory change
    ]
    component: str          # e.g., "PromotionEngine", "ActiveContextTier"
    timestamp: float = Field(default_factory=lambda: datetime.now(UTC).timestamp())
    details: dict[str, Any] # Payload (must include 'justification' where applicable)

class TelemetrySystem:
    """Singleton-style telemetry queue wrapper."""
    _queue: asyncio.Queue[CognitiveEvent] = asyncio.Queue()
    _enabled: bool = True

    @classmethod
    async def emit(cls, event: CognitiveEvent):
        if cls._enabled:
            # Non-blocking put
            try:
                cls._queue.put_nowait(event)
            except Exception as e:
                logger.warning(f"Failed to emit telemetry: {e}")

    @classmethod
    async def consume(cls):
        """Generator for the WebSocket endpoint to consume events."""
        while True:
            event = await cls._queue.get()
            yield event
            cls._queue.task_done()

# Global Accessor
telemetry = TelemetrySystem()

```

---

## 2. Model Refactoring (The "Why" Field)

**File:** `src/memory/models.py`

**Requirement:** Update `Fact` and `TopicSegment` to store reasoning.

```python
# Update Fact model
class Fact(BaseModel):
    # ... existing fields ...
    justification: str | None = Field(
        default=None, 
        description="LLM-generated reasoning or Heuristic Rule ID explaining the impact score."
    )

# Update TopicSegment (if defined here or in topic_segmenter.py)
class TopicSegment(BaseModel):
    # ... existing fields ...
    reasoning: str | None = Field(
        default=None,
        description="Explanation for why this segment was formed/scored."
    )

```

---

## 3. Schema & Prompt Engineering

**File:** `src/memory/schemas/fact_extraction.py`

**Requirement:** Update the structured output schema to force the LLM to explain itself.

```python
from pydantic import BaseModel, Field

class ExtractedFactItem(BaseModel):
    content: str = Field(description="The factual statement extracted from text")
    type: str = Field(description="The type of fact (preference, entity, etc)")
    category: str = Field(description="The category (personal, business, etc)")
    certainty: float = Field(description="Confidence score 0.0-1.0")
    impact: float = Field(description="Importance score 0.0-1.0")
    # NEW FIELD
    justification: str = Field(
        description="A 1-sentence explanation of WHY this fact is significant/impactful."
    )

class FactExtractionResponse(BaseModel):
    facts: list[ExtractedFactItem]

# Update System Instruction
FACT_EXTRACTION_SYSTEM_INSTRUCTION = """
You are an expert Memory Archivist. Extract facts from the conversation.
For every fact, you MUST provide a 'justification' explaining why it is significant 
enough to be stored in Long Term Memory.
"""

```

---

## 4. Engine Instrumentation

**File:** `src/memory/engines/promotion_engine.py`

**Requirement:** Inject telemetry events at decision points.

```python
from src.common.telemetry import telemetry, CognitiveEvent

# In process_session loop, after scoring a segment:
await telemetry.emit(CognitiveEvent(
    event_type="PROMOTION",
    component="PromotionEngine",
    details={
        "step": "segment_scoring",
        "topic": segment.topic,
        "score": segment_score,
        "threshold": self.promotion_threshold,
        "decision": "PROCESS" if segment_score >= self.promotion_threshold else "IGNORE",
        "reasoning": segment.reasoning # Now available from Model update
    }
))

# In loop, when storing a Fact:
await telemetry.emit(CognitiveEvent(
    event_type="PROMOTION",
    component="PromotionEngine",
    details={
        "step": "fact_storage",
        "fact_id": fact.fact_id,
        "ciar_score": fact.ciar_score,
        "decision": "PROMOTE",
        "justification": fact.justification # Now available from Fact update
    }
))

```

**File:** `src/memory/engines/fact_extractor.py`

**Requirement:** Map the new LLM schema response to the `Fact` object.

```python
# Inside _extract_with_llm
for rf in raw_facts:
    fact = Fact(
        # ... existing mappings ...
        justification=rf.justification, # Map from new schema
        source_type="llm_extraction"
    )

```

---