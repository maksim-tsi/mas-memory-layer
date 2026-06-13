# Memory Engines

Processing engines for memory tier transitions.

## Engine Flow

```
PromotionEngine          L1 → L2
    Segments turns into topics
    Extracts facts with CIAR scores
    Promotes significant facts to Working Memory

ConsolidationEngine      L2 → L3
    Clusters facts by time windows
    Creates episode summaries via LLM
    Stores episodes with embeddings in Qdrant

DistillationEngine       L3 → L4
    Synthesizes knowledge from episodes
    Creates domain-specific documents
    Stores in Typesense for full-text search
```

## Files

| File | Purpose |
|------|---------|
| `base_engine.py` | Abstract base with metrics |
| `promotion_engine.py` | L1→L2 promotion |
| `consolidation_engine.py` | L2→L3 consolidation |
| `distillation_engine.py` | L3→L4 distillation |
| `topic_segmenter.py` | Conversation segmentation |
| `fact_extractor.py` | Fact extraction from turns |
| `knowledge_synthesizer.py` | Knowledge synthesis utilities |

## Telemetry Events

### PromotionEngine
- `significance_scored` - CIAR score calculated for segment
- `fact_promoted` - Fact stored in L2

### ConsolidationEngine
- `consolidation_started` - Session consolidation begins
- `facts_clustered` - Facts grouped by time windows
- `episode_created` - Episode stored in L3
- `consolidation_completed` - Session consolidation ends

### DistillationEngine
- `distillation_started` - Knowledge synthesis begins
- `knowledge_created` - Knowledge document stored in L4
- `distillation_completed` - Synthesis ends

## Usage

```python
from src.memory.engines.promotion_engine import PromotionEngine

engine = PromotionEngine(
    l1_tier=active_context,
    l2_tier=working_memory,
    topic_segmenter=segmenter,
    fact_extractor=extractor,
    ciar_scorer=scorer,
    telemetry_stream=producer,
)

stats = await engine.process(session_id)
```
