# Memory Schemas

Pydantic schemas for structured LLM output extraction.

## Files

| File | Purpose |
|------|---------|
| `fact_extraction.py` | Schema for extracting facts from conversation turns |
| `topic_segmentation.py` | Schema for segmenting conversations into topic blocks |

## Usage

These schemas are used by engines to get structured JSON output from LLM calls:

```python
from src.memory.schemas.fact_extraction import FactExtractionSchema

# Used in FactExtractor to parse LLM responses
schema = FactExtractionSchema.model_json_schema()
```

## Schema Fields

### FactExtractionSchema
- `facts`: List of extracted facts
- `fact.content`: The factual statement
- `fact.certainty`: Confidence level (0-1)
- `fact.impact`: Potential impact (0-1)
- `fact.justification`: LLM reasoning for extraction

### TopicSegmentationSchema
- `segments`: List of topic segments
- `segment.topic`: Topic name
- `segment.start_turn`: Starting turn index
- `segment.end_turn`: Ending turn index
- `segment.justification`: LLM reasoning for segmentation
