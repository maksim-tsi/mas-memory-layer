"""
Data models for memory system.

Defines Pydantic models for facts, episodes, and knowledge documents
with validation and serialization support.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum


class FactType(str, Enum):
    """Classification of fact types."""
    PREFERENCE = "preference"      # User preferences (high impact)
    CONSTRAINT = "constraint"      # Business rules, requirements
    ENTITY = "entity"             # Named entities, objects
    MENTION = "mention"           # Casual mentions (low impact)
    RELATIONSHIP = "relationship"  # Entity relationships
    EVENT = "event"               # Temporal events


class FactCategory(str, Enum):
    """Domain-specific fact categories."""
    PERSONAL = "personal"
    BUSINESS = "business"
    TECHNICAL = "technical"
    OPERATIONAL = "operational"


class Fact(BaseModel):
    """
    Represents a significant fact in L2 Working Memory.
    
    Attributes:
        fact_id: Unique identifier
        session_id: Associated session
        content: Natural language fact statement
        ciar_score: Computed CIAR significance score
        certainty: Confidence in fact accuracy (0.0-1.0)
        impact: Estimated importance (0.0-1.0)
        age_decay: Time-based decay factor
        recency_boost: Access-based boost factor
        source_uri: Reference to source turn in L1
        source_type: How fact was obtained
        fact_type: Classification of fact
        fact_category: Domain category
        metadata: Additional context
        extracted_at: When fact was extracted
        last_accessed: Most recent access time
        access_count: Number of times accessed
    """
    
    fact_id: str
    session_id: str
    content: str = Field(..., min_length=1, max_length=5000)
    
    # CIAR components
    ciar_score: float = Field(default=0.0, ge=0.0, le=1.0)
    certainty: float = Field(default=0.7, ge=0.0, le=1.0)
    impact: float = Field(default=0.5, ge=0.0, le=1.0)
    age_decay: float = Field(default=1.0, ge=0.0, le=1.0)
    recency_boost: float = Field(default=1.0, ge=0.0)
    
    # Provenance
    source_uri: Optional[str] = None
    source_type: str = Field(default="extracted")
    
    # Topic Segmentation (ADR-003: batch processing context)
    topic_segment_id: Optional[str] = None  # Links to source TopicSegment
    topic_label: Optional[str] = None       # Brief topic from segment
    
    # Classification
    fact_type: Optional[FactType] = None
    fact_category: Optional[FactCategory] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamps
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = Field(default=0, ge=0)
    
    model_config = {
        "use_enum_values": True
    }
    
    @field_validator('ciar_score')
    @classmethod
    def validate_ciar_score(cls, v: float, info) -> float:
        """Ensure CIAR score is consistent with components if all are present."""
        values = info.data
        if all(k in values for k in ['certainty', 'impact', 'age_decay', 'recency_boost']):
            expected = (
                values['certainty'] * values['impact']
            ) * values['age_decay'] * values['recency_boost']
            # Allow small floating point differences
            if abs(v - expected) > 0.01:
                return round(expected, 4)
        return v
    
    def mark_accessed(self) -> None:
        """Update access tracking."""
        self.last_accessed = datetime.now(timezone.utc)
        self.access_count += 1
        # Recalculate recency boost based on access pattern
        self.recency_boost = 1.0 + (0.05 * self.access_count)  # 5% boost per access
        # Recalculate CIAR score
        self.ciar_score = round(
            (self.certainty * self.impact) * self.age_decay * self.recency_boost,
            4
        )
    
    def calculate_age_decay(self, decay_lambda: float = 0.1) -> None:
        """
        Calculate age decay factor based on time since extraction.
        
        Args:
            decay_lambda: Decay rate (default: 0.1 per day)
        """
        age_days = (datetime.now(timezone.utc) - self.extracted_at).days
        self.age_decay = round(max(0.0, min(1.0, 2 ** (-decay_lambda * age_days))), 4)
        # Recalculate CIAR score
        self.ciar_score = round(
            (self.certainty * self.impact) * self.age_decay * self.recency_boost,
            4
        )
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database-compatible dictionary."""
        import json
        return {
            'fact_id': self.fact_id,
            'session_id': self.session_id,
            'content': self.content,
            'ciar_score': self.ciar_score,
            'certainty': self.certainty,
            'impact': self.impact,
            'age_decay': self.age_decay,
            'recency_boost': self.recency_boost,
            'source_uri': self.source_uri,
            'source_type': self.source_type,
            'topic_segment_id': self.topic_segment_id,
            'topic_label': self.topic_label,
            'fact_type': self.fact_type.value if isinstance(self.fact_type, FactType) else self.fact_type,
            'fact_category': self.fact_category.value if isinstance(self.fact_category, FactCategory) else self.fact_category,
            'metadata': json.dumps(self.metadata) if self.metadata else '{}',
            'extracted_at': self.extracted_at,
            'last_accessed': self.last_accessed,
            'access_count': self.access_count
        }


class FactQuery(BaseModel):
    """Query parameters for retrieving facts."""
    session_id: Optional[str] = None
    min_ciar_score: Optional[float] = Field(default=0.6, ge=0.0, le=1.0)
    fact_types: Optional[List[FactType]] = None
    fact_categories: Optional[List[FactCategory]] = None
    limit: int = Field(default=10, ge=1, le=100)
    order_by: str = Field(default="ciar_score DESC")


class Episode(BaseModel):
    """
    Represents a consolidated episode in L3 Episodic Memory.
    
    Episodes are clusters of related facts from L2, summarized into
    coherent narrative experiences. Dual-indexed in Qdrant (vector)
    and Neo4j (graph) for hybrid retrieval.
    """
    
    episode_id: str
    session_id: str
    
    # Content
    summary: str = Field(..., min_length=10, max_length=10000)
    narrative: Optional[str] = None  # Longer form narrative
    
    # Source facts
    source_fact_ids: List[str] = Field(default_factory=list)
    fact_count: int = Field(default=0, ge=0)
    
    # Temporal boundaries
    time_window_start: datetime
    time_window_end: datetime
    duration_seconds: float = Field(default=0.0, ge=0.0)
    
    # Bi-temporal properties (ADR-003 requirement)
    fact_valid_from: datetime  # When facts became true
    fact_valid_to: Optional[datetime] = None  # When facts stopped being true
    source_observation_timestamp: datetime  # When we observed/recorded this
    
    # Embeddings and indexing
    embedding_model: str = Field(default="text-embedding-ada-002")
    vector_id: Optional[str] = None  # Qdrant point ID
    graph_node_id: Optional[str] = None  # Neo4j node ID
    
    # Metadata
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Provenance
    consolidated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    consolidation_method: str = Field(default="llm_clustering")
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_qdrant_payload(self) -> Dict[str, Any]:
        """Convert to Qdrant payload format."""
        return {
            'episode_id': self.episode_id,
            'session_id': self.session_id,
            'summary': self.summary,
            'narrative': self.narrative,
            'source_fact_ids': self.source_fact_ids,
            'fact_count': self.fact_count,
            'time_window_start': self.time_window_start.isoformat(),
            'time_window_end': self.time_window_end.isoformat(),
            'fact_valid_from': self.fact_valid_from.isoformat(),
            'fact_valid_to': self.fact_valid_to.isoformat() if self.fact_valid_to else None,
            'topics': self.topics,
            'importance_score': self.importance_score,
            'graph_node_id': self.graph_node_id,
            'consolidated_at': self.consolidated_at.isoformat()
        }
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j node properties."""
        return {
            'episodeId': self.episode_id,
            'sessionId': self.session_id,
            'summary': self.summary,
            'narrative': self.narrative or '',
            'factCount': self.fact_count,
            'timeWindowStart': self.time_window_start.isoformat(),
            'timeWindowEnd': self.time_window_end.isoformat(),
            'durationSeconds': self.duration_seconds,
            'factValidFrom': self.fact_valid_from.isoformat(),
            'factValidTo': self.fact_valid_to.isoformat() if self.fact_valid_to else None,
            'sourceObservationTimestamp': self.source_observation_timestamp.isoformat(),
            'importanceScore': self.importance_score,
            'vectorId': self.vector_id,
            'consolidatedAt': self.consolidated_at.isoformat(),
            'consolidationMethod': self.consolidation_method
        }


class KnowledgeDocument(BaseModel):
    """
    Represents distilled knowledge in L4 Semantic Memory.
    
    Knowledge documents are generalized patterns mined from L3 episodes,
    representing durable, reusable insights.
    """
    
    knowledge_id: str
    
    # Content
    title: str = Field(..., min_length=5, max_length=500)
    content: str = Field(..., min_length=10, max_length=50000)
    knowledge_type: str = Field(default="insight")  # insight, pattern, rule, preference
    
    # Confidence and provenance
    confidence_score: float = Field(default=0.7, ge=0.0, le=1.0)
    source_episode_ids: List[str] = Field(default_factory=list)
    episode_count: int = Field(default=0, ge=0)
    
    # Provenance links (for traceability)
    provenance_links: List[str] = Field(default_factory=list)
    
    # Classification
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    domain: Optional[str] = None
    
    # Lifecycle
    distilled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_validated: Optional[datetime] = None
    validation_count: int = Field(default=0, ge=0)
    
    # Usage tracking
    access_count: int = Field(default=0, ge=0)
    last_accessed: Optional[datetime] = None
    usefulness_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_typesense_document(self) -> Dict[str, Any]:
        """Convert to Typesense document format."""
        return {
            'id': self.knowledge_id,
            'title': self.title,
            'content': self.content,
            'knowledge_type': self.knowledge_type,
            'confidence_score': self.confidence_score,
            'source_episode_ids': self.source_episode_ids,
            'episode_count': self.episode_count,
            'provenance_links': self.provenance_links,
            'category': self.category or '',
            'tags': self.tags,
            'domain': self.domain or '',
            'distilled_at': int(self.distilled_at.timestamp()),
            'access_count': self.access_count,
            'usefulness_score': self.usefulness_score,
            'validation_count': self.validation_count
        }


class EpisodeQuery(BaseModel):
    """Query parameters for retrieving episodes."""
    session_id: Optional[str] = None
    min_importance: Optional[float] = Field(default=0.0, ge=0.0, le=1.0)
    topics: Optional[List[str]] = None
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
    limit: int = Field(default=10, ge=1, le=100)


class KnowledgeQuery(BaseModel):
    """Query parameters for retrieving knowledge documents."""
    search_text: Optional[str] = None
    knowledge_type: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    min_confidence: Optional[float] = Field(default=0.0, ge=0.0, le=1.0)
    limit: int = Field(default=10, ge=1, le=100)


class SearchWeights(BaseModel):
    """
    Configuration for hybrid cross-tier search weighting.
    
    Controls how results from different memory tiers are weighted
    when merged into a unified result set. Weights must sum to 1.0.
    """
    l2_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight for L2 Working Memory results")
    l3_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Weight for L3 Episodic Memory results")
    l4_weight: float = Field(default=0.2, ge=0.0, le=1.0, description="Weight for L4 Semantic Memory results")
    
    @field_validator('l4_weight')
    @classmethod
    def validate_weights_sum(cls, v: float, info) -> float:
        """Ensure weights sum to 1.0."""
        values = info.data
        if 'l2_weight' in values and 'l3_weight' in values:
            total = values['l2_weight'] + values['l3_weight'] + v
            if abs(total - 1.0) > 0.01:
                raise ValueError(f"Weights must sum to 1.0, got {total}")
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"l2_weight": 0.3, "l3_weight": 0.5, "l4_weight": 0.2},
                {"l2_weight": 0.4, "l3_weight": 0.4, "l4_weight": 0.2}
            ]
        }
    }


class ContextBlock(BaseModel):
    """
    Assembled context for prompt injection into agent conversations.
    
    Contains recent L1 turns and high-significance L2 facts filtered
    by CIAR score threshold. Used by agents to retrieve focused context
    without overwhelming the prompt window.
    """
    session_id: str
    
    # L1 Active Context (recent turns)
    recent_turns: List[Dict[str, Any]] = Field(default_factory=list, description="Recent conversation turns from L1")
    turn_count: int = Field(default=0, ge=0)
    
    # L2 Working Memory (CIAR-filtered facts)
    significant_facts: List[Fact] = Field(default_factory=list, description="High-CIAR facts from L2")
    fact_count: int = Field(default=0, ge=0)
    min_ciar_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum CIAR score used for filtering")
    
    # Metadata
    assembled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    l1_time_window_hours: float = Field(default=24.0, description="Time window for L1 turns retrieval")
    estimated_tokens: Optional[int] = Field(default=None, description="Rough token count estimate for LLM context")
    
    # Optional L3/L4 summary
    episode_summaries: List[str] = Field(default_factory=list, description="Optional episode summaries from L3")
    knowledge_snippets: List[str] = Field(default_factory=list, description="Optional knowledge from L4")
    
    def to_prompt_string(self, include_metadata: bool = False) -> str:
        """
        Convert context block to formatted string for LLM prompt injection.
        
        Args:
            include_metadata: Include metadata like timestamps and CIAR scores
            
        Returns:
            Formatted context string ready for prompt injection
        """
        sections = []
        
        # Recent conversation
        if self.recent_turns:
            sections.append("## Recent Conversation")
            for i, turn in enumerate(self.recent_turns[-10:], 1):  # Last 10 turns
                role = turn.get('role', 'unknown')
                content = turn.get('content', '')
                if include_metadata:
                    timestamp = turn.get('timestamp', 'N/A')
                    sections.append(f"{i}. [{role.upper()}] ({timestamp}): {content}")
                else:
                    sections.append(f"{i}. [{role.upper()}]: {content}")
        
        # Significant facts
        if self.significant_facts:
            sections.append("\n## Key Facts (Working Memory)")
            for i, fact in enumerate(self.significant_facts, 1):
                if include_metadata:
                    sections.append(f"{i}. {fact.content} [CIAR: {fact.ciar_score:.2f}, Type: {fact.fact_type or 'N/A'}]")
                else:
                    sections.append(f"{i}. {fact.content}")
        
        # Episode summaries
        if self.episode_summaries:
            sections.append("\n## Related Episodes (Episodic Memory)")
            for i, summary in enumerate(self.episode_summaries, 1):
                sections.append(f"{i}. {summary}")
        
        # Knowledge snippets
        if self.knowledge_snippets:
            sections.append("\n## Relevant Knowledge (Semantic Memory)")
            for i, snippet in enumerate(self.knowledge_snippets, 1):
                sections.append(f"{i}. {snippet}")
        
        return "\n".join(sections)
    
    def estimate_token_count(self, chars_per_token: float = 4.0) -> int:
        """
        Estimate token count for context block using character-based heuristic.
        
        Args:
            chars_per_token: Average characters per token (default: 4.0 for GPT models)
            
        Returns:
            Estimated token count
        """
        total_chars = 0
        
        # Count turn content
        for turn in self.recent_turns:
            total_chars += len(turn.get('content', ''))
        
        # Count fact content
        for fact in self.significant_facts:
            total_chars += len(fact.content)
        
        # Count summaries
        total_chars += sum(len(s) for s in self.episode_summaries)
        total_chars += sum(len(s) for s in self.knowledge_snippets)
        
        estimated = int(total_chars / chars_per_token)
        self.estimated_tokens = estimated
        return estimated


# Export all models
__all__ = [
    'FactType',
    'FactCategory',
    'Fact',
    'FactQuery',
    'Episode',
    'EpisodeQuery',
    'KnowledgeDocument',
    'KnowledgeQuery',
    'SearchWeights',
    'ContextBlock'
]
