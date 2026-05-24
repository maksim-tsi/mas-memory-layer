"""Service-layer contracts for public YAAM memory interfaces."""

from src.memory.services.contracts import (
    ContextResponse,
    ContradictionReviewResponse,
    CurationDecisionRecord,
    EvidenceRow,
    EvidenceTableResponse,
    HealthResponse,
    LeakageGuardResult,
    MemoryResult,
    Provenance,
    ScopeEnvelope,
    TraceCorrelationRecord,
    WriteAck,
    YAAMErrorPayload,
    YAAMWarning,
)
from src.memory.services.gateway import MemoryGatewayService
from src.memory.services.permissions import (
    PermissionDecision,
    PermissionPolicy,
    YAAMPermissionError,
)

__all__ = [
    "ContextResponse",
    "ContradictionReviewResponse",
    "CurationDecisionRecord",
    "EvidenceRow",
    "EvidenceTableResponse",
    "HealthResponse",
    "LeakageGuardResult",
    "MemoryGatewayService",
    "MemoryResult",
    "PermissionDecision",
    "PermissionPolicy",
    "Provenance",
    "ScopeEnvelope",
    "TraceCorrelationRecord",
    "WriteAck",
    "YAAMErrorPayload",
    "YAAMPermissionError",
    "YAAMWarning",
]
