# Memory System

The MAS Memory Layer - a multi-tier memory system for agent cognition and persistence.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      UnifiedMemorySystem                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │  L1 Tier   │ │  L2 Tier   │ │  L3 Tier   │ │  L4 Tier   │   │
│  │  Active    │ │  Working   │ │  Episodic  │ │  Semantic  │   │
│  │  Context   │ │  Memory    │ │  Memory    │ │  Memory    │   │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘   │
│        │              │              │              │           │
│        └──────────────┴──────────────┴──────────────┘           │
│                           │                                      │
│               LifecycleStreamProducer (Telemetry)               │
│                           │                                      │
│               Redis Stream {mas}:lifecycle                       │
└─────────────────────────────────────────────────────────────────┘
```

## Structure

| Directory/File | Purpose |
|---------------|---------|
| `engines/` | Memory processing engines (promotion, consolidation, distillation) |
| `tiers/` | Memory tier implementations (L1-L4) |
| `schemas/` | LLM output schemas for structured extraction |
| `models.py` | Pydantic data models (Fact, Episode, KnowledgeDocument) |
| `system.py` | `UnifiedMemorySystem` facade with feature flags |
| `lifecycle_stream.py` | Redis Streams telemetry producer/consumer |
| `ciar_scorer.py` | CIAR (Certainty, Impact, Actionability, Relevance) scoring |
| `namespace.py` | Redis key namespace management |

## Memory Tiers

| Tier | Storage | Purpose | TTL |
|------|---------|---------|-----|
| **L1** (Active Context) | Redis | Current conversation turns | Session |
| **L2** (Working Memory) | PostgreSQL | Extracted facts with CIAR scores | Hours |
| **L3** (Episodic Memory) | Qdrant + Neo4j | Clustered episodes with embeddings | Days |
| **L4** (Semantic Memory) | Typesense + Neo4j | Synthesized knowledge documents | Persistent |

## Engines

| Engine | Transition | Events |
|--------|------------|--------|
| `PromotionEngine` | L1 → L2 | `significance_scored`, `fact_promoted` |
| `ConsolidationEngine` | L2 → L3 | `consolidation_started`, `facts_clustered`, `episode_created`, `consolidation_completed` |
| `DistillationEngine` | L3 → L4 | `distillation_started`, `knowledge_created`, `distillation_completed` |

## Usage

```python
from src.memory.system import UnifiedMemorySystem

# Initialize with adapters
system = UnifiedMemorySystem(
    redis_client=redis_adapter,
    postgres_adapter=pg_adapter,
    neo4j_adapter=neo4j_adapter,
    qdrant_adapter=qdrant_adapter,
    typesense_adapter=ts_adapter,
    enable_telemetry=True,
)

# Store and process memory
await system.store(session_id, turn_data)
results = await system.retrieve(session_id, query="...")
```

## Telemetry

All engines emit events to Redis Streams via `LifecycleStreamProducer`:

```python
from src.memory.lifecycle_stream import LifecycleStreamProducer, LifecycleStreamConsumer

producer = LifecycleStreamProducer(redis_client)
await producer.publish(event_type="fact_promoted", session_id="...", data={...})

consumer = LifecycleStreamConsumer(redis_client)
consumer.register_handler("fact_promoted", handler_fn)
await consumer.start()
```
