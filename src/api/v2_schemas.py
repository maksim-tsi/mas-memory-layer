from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TurnCreateRequest(BaseModel):
    session_id: str
    turn_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class FactCreateRequest(BaseModel):
    fact_id: str
    session_id: str
    content: str
    ciar_score: float = Field(default=1.0, ge=0.0, le=1.0)
    certainty: float = Field(default=1.0, ge=0.0, le=1.0)
    impact: float = Field(default=1.0, ge=0.0, le=1.0)
    fact_type: str | None = None
    fact_category: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EpisodeCreateRequest(BaseModel):
    episode_id: str
    session_id: str
    summary: str
    narrative: str | None = None
    time_window_start: datetime
    time_window_end: datetime
    fact_valid_from: datetime
    source_observation_timestamp: datetime
    importance_score: float = Field(default=1.0, ge=0.0, le=1.0)
    vector_embedding: list[float]
    entities: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeCreateRequest(BaseModel):
    knowledge_id: str
    session_id: str | None = None
    title: str
    content: str
    knowledge_type: str = Field(default="insight")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
