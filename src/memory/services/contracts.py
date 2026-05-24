"""Public service contracts shared by REST, LangChain, and MCP adapters."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

SECRET_MARKERS = (
    "api_key",
    "apikey",
    "auth",
    "credential",
    "password",
    "secret",
    "token",
)


class ScopeEnvelope(BaseModel):
    """Caller, session, and trace scope for a public memory operation."""

    session_id: str = Field(..., min_length=1, description="Scoped memory session identifier")
    agent_id: str = Field(..., min_length=1, description="Calling or producing agent identifier")
    caller_role: str | None = Field(default=None, description="Calling role for policy decisions")
    visibility_scope: str | None = Field(default=None, description="Requested memory visibility scope")
    task_id: str | None = Field(default=None, description="Optional task or benchmark identifier")
    tenant_id: str | None = Field(default=None, description="Optional tenant boundary")
    run_id: str | None = Field(default=None, description="Optional benchmark or scenario run id")
    user_id: str | None = Field(default=None, description="Optional end-user identifier")
    domain_ids: dict[str, str] = Field(
        default_factory=dict,
        description="Optional domain-specific identifiers, deferred from generic v1 resources",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Redacted caller metadata")
    traceparent: str | None = Field(default=None, description="W3C traceparent header value")

    @field_validator("traceparent")
    @classmethod
    def validate_traceparent(cls, value: str | None) -> str | None:
        """Reject empty trace headers while allowing adapter-specific parsing later."""
        if value is not None and not value.strip():
            raise ValueError("traceparent cannot be blank")
        return value


class Provenance(BaseModel):
    """Source metadata returned with each externally visible memory item."""

    source_tier: Literal["L1", "L2", "L3", "L4", "SYSTEM"]
    source_id: str = Field(..., min_length=1)
    session_id: str | None = None
    agent_id: str | None = None
    task_id: str | None = None
    tenant_id: str | None = None
    run_id: str | None = None
    created_at: datetime | None = None
    trace_id: str | None = None
    audit_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class YAAMWarning(BaseModel):
    """Non-fatal warning for partial or degraded responses."""

    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    affected_tier: Literal["L1", "L2", "L3", "L4", "SYSTEM"] | None = None
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class YAAMErrorPayload(BaseModel):
    """Stable structured error shape for public adapters."""

    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    retryable: bool = False
    partial: bool = False
    operation: str | None = None
    affected_tier: Literal["L1", "L2", "L3", "L4", "SYSTEM"] | None = None
    trace_id: str | None = None
    audit_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class MemoryResult(BaseModel):
    """Normalized read result from any memory tier."""

    content: str
    tier: Literal["L1", "L2", "L3", "L4"]
    score: float | None = Field(default=None, ge=0.0)
    source_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance | None = None


class ContextResponse(BaseModel):
    """Bounded context response for agent prompt injection."""

    session_id: str
    items: list[MemoryResult] = Field(default_factory=list)
    context_summary: str | None = None
    estimated_tokens: int | None = Field(default=None, ge=0)
    partial: bool = False
    warnings: list[YAAMWarning] = Field(default_factory=list)
    visibility_scope: str | None = None
    leakage_guard_passed: bool | None = None
    filtered_item_count: int = 0


class LeakageGuardResult(BaseModel):
    """Visibility filtering metadata for benchmark-safe reads."""

    leakage_guard_passed: bool
    visibility_scope: str | None = None
    forbidden_fields: list[str] = Field(default_factory=list)
    filtered_item_count: int = 0
    checked_item_count: int = 0
    warnings: list[YAAMWarning] = Field(default_factory=list)


class EvidenceRow(BaseModel):
    """One row in an audit-oriented evidence table."""

    claim: str
    source_tier: Literal["L1", "L2", "L3", "L4"]
    source_id: str | None = None
    evidence: str
    provenance: Provenance | None = None
    policy_metadata: dict[str, Any] = Field(default_factory=dict)
    visibility: Literal["standard", "audit"] = "standard"


class EvidenceTableResponse(BaseModel):
    """Deterministic evidence table assembled from scoped memory reads."""

    rows: list[EvidenceRow] = Field(default_factory=list)
    partial: bool = False
    warnings: list[YAAMWarning] = Field(default_factory=list)
    query: str | None = None
    scope: ScopeEnvelope | None = None


class HealthResponse(BaseModel):
    """Service and tier health without secrets or raw environment values."""

    status: Literal["ok", "degraded", "unavailable"]
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tiers: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    warnings: list[YAAMWarning] = Field(default_factory=list)


class WriteAck(BaseModel):
    """Acknowledgement returned only after a write is confirmed."""

    status: Literal["success"] = "success"
    operation: str
    created_id: str | None = None
    updated_id: str | None = None
    provenance: Provenance | None = None
    audit_id: str | None = None


class ContradictionReviewResponse(BaseModel):
    """Deterministic contradiction and safe-refusal review result."""

    contradiction_detected: bool = False
    infeasibility_reason: str | None = None
    supporting_evidence: list[MemoryResult] = Field(default_factory=list)
    conflicting_evidence: list[MemoryResult] = Field(default_factory=list)
    safe_refusal_rationale: str | None = None
    partial: bool = False
    warnings: list[YAAMWarning] = Field(default_factory=list)
    scope: ScopeEnvelope | None = None


class CurationDecisionRecord(BaseModel):
    """Maintainer-only benchmark curation decision."""

    curation_record_id: str
    task_id: str
    decision: str
    reason: str
    source_triad: dict[str, Any] = Field(default_factory=dict)
    reviewer: str
    visibility_scope: str = "maintainer_only"
    provenance: Provenance | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceCorrelationRecord(BaseModel):
    """External trace and artifact correlation metadata."""

    correlation_id: str
    trace_id: str | None = None
    task_id: str | None = None
    run_id: str | None = None
    artifact_ref: str | None = None
    openrouter_call_id: str | None = None
    linked_memory_ids: list[str] = Field(default_factory=list)
    error_summary: str | None = None
    trace_status: str = "unverified"
    provenance: Provenance | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def redact_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Return metadata with secret-shaped keys redacted recursively."""
    if not metadata:
        return {}

    redacted: dict[str, Any] = {}
    for key, value in metadata.items():
        key_lower = key.lower()
        if any(marker in key_lower for marker in SECRET_MARKERS):
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = redact_metadata(value)
        elif isinstance(value, list):
            redacted[key] = [
                redact_metadata(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            redacted[key] = value
    return redacted


def model_metadata(item: Any) -> dict[str, Any]:
    """Extract and redact metadata from model or mapping-like objects."""
    metadata = _get_value(item, "metadata", {})
    return redact_metadata(metadata if isinstance(metadata, dict) else {})


def memory_result_from_fact(fact: Any, scope: ScopeEnvelope | None = None) -> MemoryResult:
    """Normalize an L2 fact into the public memory result contract."""
    metadata = model_metadata(fact)
    source_id = str(_get_value(fact, "fact_id", "")) or None
    session_id = _get_value(fact, "session_id", None)
    provenance = Provenance(
        source_tier="L2",
        source_id=source_id or "unknown",
        session_id=session_id,
        agent_id=metadata.get("agent_id") or (scope.agent_id if scope else None),
        task_id=metadata.get("task_id") or (scope.task_id if scope else None),
        tenant_id=scope.tenant_id if scope else None,
        run_id=scope.run_id if scope else None,
        created_at=_get_value(fact, "created_at", None) or _get_value(fact, "extracted_at", None),
        trace_id=metadata.get("trace_id"),
        audit_id=metadata.get("audit_id"),
        metadata=metadata,
    )
    return MemoryResult(
        content=str(_get_value(fact, "content", "")),
        tier="L2",
        score=_get_float(fact, "ciar_score"),
        source_id=source_id,
        metadata=metadata,
        provenance=provenance,
    )


def memory_result_from_episode(episode: Any, scope: ScopeEnvelope | None = None) -> MemoryResult:
    """Normalize an L3 episode into the public memory result contract."""
    metadata = model_metadata(episode)
    source_id = str(_get_value(episode, "episode_id", "")) or None
    session_id = _get_value(episode, "session_id", None)
    similarity_score = metadata.get("similarity_score")
    score = (
        float(similarity_score)
        if similarity_score is not None
        else _get_float(episode, "importance_score")
    )
    provenance = Provenance(
        source_tier="L3",
        source_id=source_id or "unknown",
        session_id=session_id,
        agent_id=metadata.get("agent_id") or (scope.agent_id if scope else None),
        task_id=metadata.get("task_id") or (scope.task_id if scope else None),
        tenant_id=scope.tenant_id if scope else None,
        run_id=scope.run_id if scope else None,
        created_at=_get_value(episode, "consolidated_at", None),
        trace_id=metadata.get("trace_id"),
        audit_id=metadata.get("audit_id"),
        metadata=metadata,
    )
    return MemoryResult(
        content=str(_get_value(episode, "summary", "")),
        tier="L3",
        score=score,
        source_id=source_id,
        metadata=metadata,
        provenance=provenance,
    )


def memory_result_from_knowledge(document: Any, scope: ScopeEnvelope | None = None) -> MemoryResult:
    """Normalize an L4 knowledge document into the public memory result contract."""
    metadata = model_metadata(document)
    source_id = str(_get_value(document, "knowledge_id", "")) or None
    session_id = _get_value(document, "session_id", None)
    search_score = metadata.get("search_score")
    score = (
        float(search_score)
        if search_score is not None
        else _get_float(document, "confidence_score")
    )
    provenance = Provenance(
        source_tier="L4",
        source_id=source_id or "unknown",
        session_id=session_id,
        agent_id=metadata.get("agent_id") or (scope.agent_id if scope else None),
        task_id=metadata.get("task_id") or (scope.task_id if scope else None),
        tenant_id=scope.tenant_id if scope else None,
        run_id=scope.run_id if scope else None,
        created_at=_get_value(document, "distilled_at", None),
        trace_id=metadata.get("trace_id"),
        audit_id=metadata.get("audit_id"),
        metadata=metadata,
    )
    return MemoryResult(
        content=str(_get_value(document, "content", "")),
        tier="L4",
        score=score,
        source_id=source_id,
        metadata=metadata,
        provenance=provenance,
    )


def memory_result_from_unified(
    result: dict[str, Any], scope: ScopeEnvelope | None = None
) -> MemoryResult:
    """Normalize a UnifiedMemorySystem query result into the public contract."""
    tier = result.get("tier", "L2")
    metadata = redact_metadata(result.get("metadata", {}))
    source_key = {
        "L2": "fact_id",
        "L3": "episode_id",
        "L4": "knowledge_id",
    }.get(tier, "source_id")
    source_id = metadata.get(source_key) or result.get("source_id")
    provenance = Provenance(
        source_tier=tier,
        source_id=str(source_id or "unknown"),
        session_id=scope.session_id if scope else metadata.get("session_id"),
        agent_id=metadata.get("agent_id") or (scope.agent_id if scope else None),
        task_id=metadata.get("task_id") or (scope.task_id if scope else None),
        tenant_id=scope.tenant_id if scope else None,
        run_id=scope.run_id if scope else None,
        trace_id=metadata.get("trace_id"),
        audit_id=metadata.get("audit_id"),
        metadata=metadata,
    )
    return MemoryResult(
        content=str(result.get("content", "")),
        tier=tier,
        score=float(result["score"]) if result.get("score") is not None else None,
        source_id=str(source_id) if source_id is not None else None,
        metadata=metadata,
        provenance=provenance,
    )


def _get_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _get_float(item: Any, key: str) -> float | None:
    value = _get_value(item, key, None)
    return float(value) if value is not None else None
