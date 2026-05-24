"""Service-layer contracts for public YAAM memory interfaces."""

from src.memory.services.contracts import (
    ContextResponse,
    EvidenceRow,
    EvidenceTableResponse,
    HealthResponse,
    MemoryResult,
    Provenance,
    ScopeEnvelope,
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
    "EvidenceRow",
    "EvidenceTableResponse",
    "HealthResponse",
    "MemoryGatewayService",
    "MemoryResult",
    "PermissionDecision",
    "PermissionPolicy",
    "Provenance",
    "ScopeEnvelope",
    "WriteAck",
    "YAAMErrorPayload",
    "YAAMPermissionError",
    "YAAMWarning",
]
