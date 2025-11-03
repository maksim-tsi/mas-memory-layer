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
        "use_enum_values": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
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
