"""Pydantic models for agent request/response payloads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class RunTurnRequest(BaseModel):
    """Request payload for a single conversation turn.

    Args:
        session_id: Unique identifier for the session.
        role: Role for the incoming message (e.g., user/system).
        content: Message text content.
        turn_id: Monotonic turn index in the conversation.
        history: Optional full conversation history in message format.
        metadata: Optional metadata for downstream logging.
        timestamp: Optional ISO timestamp for the turn.
    """

    session_id: str = Field(..., description="Unique identifier for the session.")
    role: str = Field(..., description="Role for the incoming message.")
    content: str = Field(..., description="Message text content.")
    turn_id: int = Field(..., description="Monotonic turn index in the conversation.")
    history: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional full conversation history in OpenAI message format.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata for the request."
    )
    timestamp: datetime | None = Field(
        default=None,
        description="Optional timestamp for the incoming turn.",
    )

    @field_validator("session_id", "role", "content")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Value must be a non-empty string.")
        return value.strip()

    @field_validator("turn_id")
    @classmethod
    def _validate_turn_id(cls, value: int) -> int:
        if value < 0:
            raise ValueError("turn_id must be a non-negative integer.")
        return value

    @field_validator("timestamp")
    @classmethod
    def _ensure_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class RunTurnResponse(BaseModel):
    """Response payload for a single conversation turn.

    Args:
        session_id: Unique identifier for the session.
        role: Role for the response message (assistant).
        content: Response text content.
        turn_id: Turn index corresponding to the request.
        metadata: Optional metadata produced by the agent.
        timestamp: Timestamp when the response was generated.
    """

    session_id: str = Field(..., description="Unique identifier for the session.")
    role: str = Field(..., description="Role for the response message.")
    content: str = Field(..., description="Response text content.")
    turn_id: int = Field(..., description="Turn index corresponding to the request.")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata for the response."
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the response was generated.",
    )

    @field_validator("session_id", "role", "content")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Value must be a non-empty string.")
        return value.strip()

    @field_validator("turn_id")
    @classmethod
    def _validate_turn_id(cls, value: int) -> int:
        if value < 0:
            raise ValueError("turn_id must be a non-negative integer.")
        return value
