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


class L3SemanticAssimilateRequest(BaseModel):
    session_id: str = Field(..., description="The shared session identifier")
    agent_id: str = Field(..., description="Agent triggering the knowledge assimilation")
    text_to_assimilate: str = Field(..., description="Natural language observation")
    domain_tags: list[str] = Field(default_factory=list, description="Associated domain tags")


class L3SemanticQueryRequest(BaseModel):
    session_id: str = Field(..., description="The shared session identifier")
    agent_id: str = Field(..., description="Agent querying memory")
    nl_query: str = Field(..., description="Natural language query for semantic search")
    top_k: int = Field(default=3, ge=1)
    filters: dict[str, Any] = Field(
        default_factory=dict, description="Optional filters like task_id"
    )


class L4SemanticFinalizeRequest(BaseModel):
    task_id: str = Field(..., description="The completed task identifier")
    session_id: str = Field(..., description="The shared session identifier")
    title: str = Field(..., description="Title of the consensus finding")
    final_artifact: str = Field(..., description="The final verified content/output")
    consensus_metadata: dict[str, Any] = Field(..., description="Votes, disagreements, logic map")


class ScopeFields(BaseModel):
    session_id: str = Field(..., description="The shared session identifier")
    agent_id: str = Field(..., description="Agent or service invoking the operation")
    task_id: str | None = Field(default=None, description="Optional task identifier")
    tenant_id: str | None = Field(default=None, description="Optional tenant boundary")
    run_id: str | None = Field(default=None, description="Optional run identifier")
    caller_role: str | None = Field(default=None, description="Caller role for policy decisions")
    visibility_scope: str | None = Field(default=None, description="Requested visibility scope")


class MemoryQueryRequest(ScopeFields):
    query: str = Field(..., min_length=1, description="Natural language memory query")
    limit: int = Field(default=10, ge=1, le=100)
    l2_weight: float = Field(default=0.3, ge=0.0)
    l3_weight: float = Field(default=0.5, ge=0.0)
    l4_weight: float = Field(default=0.2, ge=0.0)
    allowed_fields: list[str] | None = Field(default=None)
    forbidden_fields: list[str] | None = Field(default=None)
    require_leakage_guard: bool = Field(default=False)


class ContextRequest(ScopeFields):
    min_ciar: float = Field(default=0.6, ge=0.0, le=1.0)
    max_turns: int = Field(default=20, ge=0, le=200)
    max_facts: int = Field(default=10, ge=0, le=200)
    allowed_fields: list[str] | None = Field(default=None)
    forbidden_fields: list[str] | None = Field(default=None)
    require_leakage_guard: bool = Field(default=False)


class CurationDecisionCreateRequest(ScopeFields):
    task_id: str = Field(..., description="Task identifier for the curation decision")
    decision: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    source_triad: dict[str, Any] = Field(default_factory=dict)
    reviewer: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceCorrelationCreateRequest(ScopeFields):
    trace_id: str | None = Field(default=None)
    artifact_ref: str | None = Field(default=None)
    openrouter_call_id: str | None = Field(default=None)
    linked_memory_ids: list[str] = Field(default_factory=list)
    error_summary: str | None = Field(default=None)
    trace_status: str = Field(default="unverified")
    metadata: dict[str, Any] = Field(default_factory=dict)
