from typing import Any, Literal

from pydantic import BaseModel, Field


class TurnCreateRequest(BaseModel):
    session_id: str = Field(..., description="The shared session ID")
    agent_id: str = Field(..., description="Agent performing the action")
    turn_id: str = Field(..., description="Turn sequence identifier")
    role: Literal["user", "assistant", "system"]
    content: str
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Must contain trace_id for Phoenix"
    )


class L2SemanticFactRequest(BaseModel):
    session_id: str = Field(..., description="The shared session identifier")
    task_id: str = Field(..., description="Current task being executed")
    agent_id: str = Field(..., description="Agent invoking the action")
    action: Literal["store", "retrieve"] = Field(..., description="Action to perform")
    content: str | None = Field(default=None, description="Fact content (required for store)")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Must contain trace_id for Phoenix"
    )


class L3SemanticAssimilateRequest(BaseModel):
    session_id: str = Field(..., description="The shared session identifier")
    agent_id: str = Field(..., description="Agent triggering the knowledge assimilation")
    text_to_assimilate: str = Field(..., description="Natural language observation")
    domain_tags: list[str] = Field(default_factory=list, description="Associated domain tags")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Must contain trace_id for Phoenix"
    )


class L3SemanticQueryRequest(BaseModel):
    session_id: str = Field(..., description="The shared session identifier")
    agent_id: str = Field(..., description="Agent querying memory")
    nl_query: str = Field(..., description="Natural language query for semantic search")
    top_k: int = Field(default=3, ge=1)
    filters: dict[str, Any] = Field(
        default_factory=dict, description="Optional filters like task_id"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Must contain trace_id for Phoenix"
    )


class L4SemanticFinalizeRequest(BaseModel):
    task_id: str = Field(..., description="The completed task identifier")
    session_id: str = Field(..., description="The shared session identifier")
    title: str = Field(..., description="Title of the consensus finding")
    final_artifact: str = Field(..., description="The final verified content/output")
    consensus_metadata: dict[str, Any] = Field(..., description="Votes, disagreements, logic map")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Must contain trace_id for Phoenix"
    )
