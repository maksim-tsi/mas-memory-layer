# YAAM Memory Subsystem Audit Report

## 1. L1 Working Memory
The L1 Working Memory manages the short-term context of the agent and intermediate draft states. It utilizes a caching pattern with Redis (hot) and PostgreSQL (cold fallback) under the `ActiveContextTier`, while the `UnifiedMemorySystem` manages explicit personal and shared workspace states.

### Methods
- **`UnifiedMemorySystem.get_personal_state(agent_id: str) -> PersonalMemoryState`**
  Retrieves the current draft/working state for a specific agent.
- **`UnifiedMemorySystem.update_personal_state(state: PersonalMemoryState) -> None`**
  Updates the agent's short-term scratchpad and working memory draft limits.
- **`UnifiedMemorySystem.get_shared_state(event_id: str) -> SharedWorkspaceState`**
  Retrieves the current draft state of a multi-agent shared workspace.
- **`UnifiedMemorySystem.update_shared_state(state: SharedWorkspaceState) -> None`**
  Updates the shared workspace state.
- **`ActiveContextTier.store(data: TurnData) -> str`**
  Stores conversational turns (short-term context) into the active context buffer.
- **`ActiveContextTier.retrieve_session(session_id: str) -> list[TurnData] | None`**
  Retrieves the most recent conversational turns (default: 20) for a given session.

### Schemas
```python
class PersonalMemoryState(BaseModel):
    agent_id: str
    current_task_id: str | None = None
    scratchpad: dict[str, Any] = Field(default_factory=dict)
    promotion_candidates: dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class SharedWorkspaceState(BaseModel):
    event_id: str
    status: Literal["active", "resolved", "cancelled"] = "active"
    shared_data: dict[str, Any] = Field(default_factory=dict)
    participating_agents: list[str] = Field(default_factory=list)
    created_at: datetime
    last_updated: datetime

class TurnData(BaseModel):
    session_id: str
    turn_id: str
    role: str # 'user' or 'assistant'
    content: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
```

## 2. L2 Episodic Memory (Internally tracked as L3 EpisodicMemoryTier)
The framework stores completed episodes using dual-indexing: a vector index (Qdrant) for semantic similarity searches, and a graph index (Neo4j) for bi-temporal relationship traversal.

### Methods
- **`EpisodicMemoryTier.store(data: EpisodeStoreInput) -> str`**
  Stores an episode simultaneously in Qdrant (vectors) and Neo4j (graph entities/relationships), seamlessly linking the indices automatically.
- **`EpisodicMemoryTier.retrieve(episode_id: str) -> Episode | None`**
  Retrieves a specific episode directly from the graph storage by its identifier.
- **`EpisodicMemoryTier.search_similar(query_embedding: list[float], limit: int = 10, filters: dict[str, Any] | None = None) -> list[Episode]`**
  Performs a semantic similarity search via Qdrant and returns matching episodes.
- **`EpisodicMemoryTier.query_temporal(query_time: datetime, session_id: str | None = None, limit: int = 10) -> list[Episode]`**
  Queries the database for episodes that were contextually valid during a specific time boundary using bi-temporal graphs.

### Schemas
```python
class EpisodeStoreInput(BaseModel):
    episode: Episode
    embedding: list[float]
    entities: list[dict[str, Any]]
    relationships: list[dict[str, Any]]

class Episode(BaseModel):
    episode_id: str
    session_id: str
    summary: str
    narrative: str | None
    source_fact_ids: list[str]
    fact_count: int
    time_window_start: datetime
    time_window_end: datetime
    duration_seconds: int
    fact_valid_from: datetime
    fact_valid_to: datetime | None
    source_observation_timestamp: datetime
    importance_score: float
    vector_id: str | None
    graph_node_id: str | None
```

## 3. Lineage Audit
The `ArtifactRepository` class handles tracking the lineage of decisions through an interconnected graph pattern connecting Artifacts, Revisions, Feedback, and Commits. 

### Methods
- **`ArtifactRepository.get_lineage(query_model: ArtifactLineageQuery) -> ArtifactLineageResult`**
  Reconstructs the full lineage history of an artifact, ordering the chain of revisions, external feedbacks, and final commits.
- **`ArtifactRepository.store_revision(artifact: Artifact, revision: ArtifactRevision) -> None`**
  Stores a new iteration (revision) of an artifact, tying it to existing nodes and optionally projecting it into working memory for active recall.

### Schemas
```python
class ArtifactLineageQuery(BaseModel):
    artifact_id: str
    revision_id: str | None = None

class ArtifactLineageResult(BaseModel):
    artifact_id: str
    current_revision_id: str | None = None
    nodes: list[ArtifactLineageNode] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

class ArtifactLineageNode(BaseModel):
    node_type: Literal["artifact", "revision", "feedback", "commit", "knowledge"]
    node_id: str
    artifact_id: str
    relation: str | None
    revision_id: str | None
    parent_id: str | None
    timestamp: datetime | None
    content: str | None
    metadata: dict[str, Any]
```

## 4. Entry Points
The root entry interfaces designed to be instantiated and injected by external systems.

### Main Facades
- **`src.memory.unified_memory_system.UnifiedMemorySystem`**
  The central operational facade for the entire memory subsystem. It unifies operations across all 4 tiers (Active Context, Working Memory, Episodic Memory, Semantic Knowledge) and triggers consolidation/distillation cycles.
- **`src.agents.memory_agent.MemoryAgent`**
  The primary LangGraph-driven agent entry point that natively hooks into the `UnifiedMemorySystem` to perform RAG-driven context fetching (`get_context_block`), execution reasoning, and automatic memory promotion routines.
