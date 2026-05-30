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
from src.memory.services.domain_views import (
    SKILL_FACTORY_METADATA_KEYS,
    SkillFactoryDomainViewService,
)
from src.memory.services.gateway import MemoryGatewayService
from src.memory.services.permissions import (
    PermissionDecision,
    PermissionPolicy,
    YAAMPermissionError,
)

__all__ = [
    "SKILL_FACTORY_METADATA_KEYS",
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
    "SkillFactoryDomainViewService",
    "TraceCorrelationRecord",
    "WriteAck",
    "YAAMErrorPayload",
    "YAAMPermissionError",
    "YAAMWarning",
]
