"""Shared MCP test fixtures for in-process and stdio contract tests."""

from __future__ import annotations

from typing import Any

from src.memory.models import SearchWeights
from src.memory.services import (
    ContextResponse,
    EvidenceRow,
    EvidenceTableResponse,
    HealthResponse,
    MemoryResult,
    Provenance,
    ScopeEnvelope,
    YAAMErrorPayload,
    YAAMWarning,
)
from src.memory.services.permissions import YAAMPermissionError


class RecordingMCPService:
    """In-memory MCP service that records calls and returns deterministic data."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    async def query_memory(
        self,
        scope: ScopeEnvelope,
        query: str,
        limit: int = 10,
        weights: SearchWeights | None = None,
    ) -> list[MemoryResult]:
        self.calls.append(("query_memory", (scope, query, limit, weights), {}))
        return [_memory_result("L2", "fact-1", scope)]

    async def get_context(
        self,
        scope: ScopeEnvelope,
        min_ciar: float = 0.6,
        max_turns: int = 20,
        max_facts: int = 10,
    ) -> ContextResponse:
        self.calls.append(
            (
                "get_context",
                (scope,),
                {"min_ciar": min_ciar, "max_turns": max_turns, "max_facts": max_facts},
            )
        )
        return ContextResponse(
            session_id=scope.session_id,
            items=[_memory_result("L2", "fact-context", scope)],
            context_summary="Context summary.",
            estimated_tokens=12,
        )

    async def store_l2_fact(
        self,
        scope: ScopeEnvelope,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.calls.append(("store_l2_fact", (scope, content), {"metadata": metadata}))
        raise YAAMPermissionError(
            YAAMErrorPayload(
                code="permission.writes_disabled",
                message="Write operations require YAAM_MCP_ENABLE_WRITES=true.",
                retryable=False,
                operation="yaam.l2.store_fact",
                affected_tier="SYSTEM",
                details={"mode": "write"},
            )
        )

    async def search_l2_facts(
        self,
        scope: ScopeEnvelope,
        query: str | None = None,
        min_ciar: float | None = None,
        limit: int = 20,
    ) -> list[MemoryResult]:
        self.calls.append(
            ("search_l2_facts", (scope,), {"query": query, "min_ciar": min_ciar, "limit": limit})
        )
        return [_memory_result("L2", "fact-search", scope)]

    async def search_l3_episodes(
        self,
        scope: ScopeEnvelope,
        query: str,
        limit: int = 10,
    ) -> list[MemoryResult]:
        self.calls.append(("search_l3_episodes", (scope, query, limit), {}))
        return [_memory_result("L3", "episode-search", scope)]

    async def search_l4_knowledge(
        self,
        scope: ScopeEnvelope,
        query: str,
        limit: int = 10,
    ) -> list[MemoryResult]:
        self.calls.append(("search_l4_knowledge", (scope, query, limit), {}))
        return [_memory_result("L4", "knowledge-search", scope)]

    async def explain_ciar(
        self,
        scope: ScopeEnvelope,
        fact: Any = None,
        components: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        self.calls.append(("explain_ciar", (scope, fact, components), {}))
        return {"scope": scope.model_dump(mode="json"), "score": 0.42, "components": components}

    async def evidence_table(
        self,
        scope: ScopeEnvelope,
        query: str,
        limit: int = 10,
    ) -> EvidenceTableResponse:
        self.calls.append(("evidence_table", (scope, query, limit), {}))
        row = EvidenceRow(
            claim="Claim one.",
            source_tier="L2",
            source_id="fact-evidence",
            evidence="Evidence one.",
            provenance=_provenance("L2", "fact-evidence", scope),
        )
        return EvidenceTableResponse(rows=[row], query=query, scope=scope)

    async def health_check(self) -> HealthResponse:
        self.calls.append(("health_check", (), {}))
        return HealthResponse(status="ok", tiers={"L2": {"configured": True, "status": "ok"}})

    async def get_fact(self, scope: ScopeEnvelope, fact_id: str) -> MemoryResult | None:
        self.calls.append(("get_fact", (scope, fact_id), {}))
        return _memory_result("L2", fact_id, scope)

    async def get_episode(self, scope: ScopeEnvelope, episode_id: str) -> MemoryResult | None:
        self.calls.append(("get_episode", (scope, episode_id), {}))
        return _memory_result("L3", episode_id, scope)

    async def get_knowledge(self, scope: ScopeEnvelope, knowledge_id: str) -> MemoryResult | None:
        self.calls.append(("get_knowledge", (scope, knowledge_id), {}))
        return _memory_result("L4", knowledge_id, scope)


class PartialContextService(RecordingMCPService):
    """Recording service variant that returns a partial context response."""

    async def get_context(
        self,
        scope: ScopeEnvelope,
        min_ciar: float = 0.6,
        max_turns: int = 20,
        max_facts: int = 10,
    ) -> ContextResponse:
        self.calls.append(
            (
                "get_context",
                (scope,),
                {"min_ciar": min_ciar, "max_turns": max_turns, "max_facts": max_facts},
            )
        )
        return ContextResponse(
            session_id=scope.session_id,
            items=[_memory_result("L2", "fact-context", scope)],
            partial=True,
            warnings=[
                YAAMWarning(
                    code="tier.timeout",
                    message="L3 timed out.",
                    affected_tier="L3",
                    retryable=True,
                )
            ],
        )


def memory_result(tier: str, source_id: str, scope: ScopeEnvelope) -> MemoryResult:
    """Return deterministic memory result data for tests."""
    return _memory_result(tier, source_id, scope)


def provenance(tier: str, source_id: str, scope: ScopeEnvelope) -> Provenance:
    """Return deterministic provenance data for tests."""
    return _provenance(tier, source_id, scope)


def _memory_result(tier: str, source_id: str, scope: ScopeEnvelope) -> MemoryResult:
    return MemoryResult(
        content=f"{tier} content {source_id}",
        tier=tier,
        score=0.8,
        source_id=source_id,
        provenance=_provenance(tier, source_id, scope),
    )


def _provenance(tier: str, source_id: str, scope: ScopeEnvelope) -> Provenance:
    return Provenance(
        source_tier=tier,
        source_id=source_id,
        session_id=scope.session_id,
        agent_id=scope.agent_id,
        task_id=scope.task_id,
        tenant_id=scope.tenant_id,
        run_id=scope.run_id,
    )
