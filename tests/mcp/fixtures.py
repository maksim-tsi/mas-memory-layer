"""Shared MCP test fixtures for in-process and stdio contract tests."""

from __future__ import annotations

from typing import Any

from src.memory.models import SearchWeights
from src.memory.services import (
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
        allowed_fields: list[str] | None = None,
        forbidden_fields: list[str] | None = None,
        require_leakage_guard: bool = False,
    ) -> list[MemoryResult]:
        self.calls.append(
            (
                "query_memory",
                (scope, query, limit, weights),
                {
                    "allowed_fields": allowed_fields,
                    "forbidden_fields": forbidden_fields,
                    "require_leakage_guard": require_leakage_guard,
                },
            )
        )
        return [_memory_result("L2", "fact-1", scope)]

    async def query_memory_checked(
        self,
        scope: ScopeEnvelope,
        query: str,
        limit: int = 10,
        weights: SearchWeights | None = None,
        allowed_fields: list[str] | None = None,
        forbidden_fields: list[str] | None = None,
        require_leakage_guard: bool = False,
    ) -> tuple[list[MemoryResult], LeakageGuardResult]:
        results = await self.query_memory(
            scope,
            query=query,
            limit=limit,
            weights=weights,
            allowed_fields=allowed_fields,
            forbidden_fields=forbidden_fields,
            require_leakage_guard=require_leakage_guard,
        )
        return results, LeakageGuardResult(
            leakage_guard_passed=require_leakage_guard
            or scope.caller_role == "benchmark_runtime_agent",
            visibility_scope=scope.visibility_scope,
            forbidden_fields=forbidden_fields or [],
            checked_item_count=len(results),
        )

    async def get_context(
        self,
        scope: ScopeEnvelope,
        min_ciar: float = 0.6,
        max_turns: int = 20,
        max_facts: int = 10,
        allowed_fields: list[str] | None = None,
        forbidden_fields: list[str] | None = None,
        require_leakage_guard: bool = False,
    ) -> ContextResponse:
        self.calls.append(
            (
                "get_context",
                (scope,),
                {
                    "min_ciar": min_ciar,
                    "max_turns": max_turns,
                    "max_facts": max_facts,
                    "allowed_fields": allowed_fields,
                    "forbidden_fields": forbidden_fields,
                    "require_leakage_guard": require_leakage_guard,
                },
            )
        )
        return ContextResponse(
            session_id=scope.session_id,
            items=[_memory_result("L2", "fact-context", scope)],
            context_summary="Context summary.",
            estimated_tokens=12,
            visibility_scope=scope.visibility_scope,
            leakage_guard_passed=require_leakage_guard
            or scope.caller_role == "benchmark_runtime_agent",
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

    async def review_contradiction(
        self,
        scope: ScopeEnvelope,
        claims: list[str],
        expected_behavior: str | None = None,
        limit: int = 5,
    ) -> ContradictionReviewResponse:
        self.calls.append(
            (
                "review_contradiction",
                (scope, claims),
                {"expected_behavior": expected_behavior, "limit": limit},
            )
        )
        return ContradictionReviewResponse(
            contradiction_detected=True,
            infeasibility_reason="Fixture conflict.",
            supporting_evidence=[_memory_result("L2", "supporting-evidence", scope)],
            conflicting_evidence=[_memory_result("L2", "conflicting-evidence", scope)],
            safe_refusal_rationale="Fixture safe refusal.",
            scope=scope,
        )

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

    async def record_curation_decision(
        self,
        scope: ScopeEnvelope,
        task_id: str,
        decision: str,
        reason: str,
        source_triad: dict[str, Any],
        reviewer: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.calls.append(
            (
                "record_curation_decision",
                (scope, task_id, decision, reason, source_triad, reviewer),
                {"metadata": metadata},
            )
        )
        raise YAAMPermissionError(
            YAAMErrorPayload(
                code="permission.writes_disabled",
                message="Write operations require YAAM_MCP_ENABLE_WRITES=true.",
                retryable=False,
                operation="yaam.curation.record_decision",
                affected_tier="SYSTEM",
                details={"mode": "write"},
            )
        )

    async def list_curation_decisions(
        self,
        scope: ScopeEnvelope,
        task_id: str | None = None,
        limit: int = 50,
    ) -> list[CurationDecisionRecord]:
        self.calls.append(("list_curation_decisions", (scope,), {"task_id": task_id, "limit": limit}))
        return [_curation_record(scope, task_id or "task-a")]

    async def record_trace_correlation(
        self,
        scope: ScopeEnvelope,
        trace_id: str | None = None,
        artifact_ref: str | None = None,
        openrouter_call_id: str | None = None,
        linked_memory_ids: list[str] | None = None,
        error_summary: str | None = None,
        trace_status: str = "unverified",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.calls.append(
            (
                "record_trace_correlation",
                (scope,),
                {
                    "trace_id": trace_id,
                    "artifact_ref": artifact_ref,
                    "openrouter_call_id": openrouter_call_id,
                    "linked_memory_ids": linked_memory_ids,
                    "error_summary": error_summary,
                    "trace_status": trace_status,
                    "metadata": metadata,
                },
            )
        )
        raise YAAMPermissionError(
            YAAMErrorPayload(
                code="permission.writes_disabled",
                message="Write operations require YAAM_MCP_ENABLE_WRITES=true.",
                retryable=False,
                operation="yaam.trace.record_correlation",
                affected_tier="SYSTEM",
                details={"mode": "write"},
            )
        )

    async def lookup_trace_correlation(
        self,
        scope: ScopeEnvelope,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        task_id: str | None = None,
        run_id: str | None = None,
        limit: int = 50,
    ) -> list[TraceCorrelationRecord]:
        self.calls.append(
            (
                "lookup_trace_correlation",
                (scope,),
                {
                    "correlation_id": correlation_id,
                    "trace_id": trace_id,
                    "task_id": task_id,
                    "run_id": run_id,
                    "limit": limit,
                },
            )
        )
        return [_trace_correlation(scope, correlation_id or "tracecorr-fixture")]


class PartialContextService(RecordingMCPService):
    """Recording service variant that returns a partial context response."""

    async def get_context(
        self,
        scope: ScopeEnvelope,
        min_ciar: float = 0.6,
        max_turns: int = 20,
        max_facts: int = 10,
        allowed_fields: list[str] | None = None,
        forbidden_fields: list[str] | None = None,
        require_leakage_guard: bool = False,
    ) -> ContextResponse:
        self.calls.append(
            (
                "get_context",
                (scope,),
                {
                    "min_ciar": min_ciar,
                    "max_turns": max_turns,
                    "max_facts": max_facts,
                    "allowed_fields": allowed_fields,
                    "forbidden_fields": forbidden_fields,
                    "require_leakage_guard": require_leakage_guard,
                },
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
            visibility_scope=scope.visibility_scope,
            leakage_guard_passed=require_leakage_guard
            or scope.caller_role == "benchmark_runtime_agent",
        )


class WriteEnabledRecordingMCPService(RecordingMCPService):
    """Recording service variant that acknowledges allowlisted writes."""

    async def store_l2_fact(
        self,
        scope: ScopeEnvelope,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> WriteAck:
        self.calls.append(("store_l2_fact", (scope, content), {"metadata": metadata}))
        return _write_ack("yaam.l2.store_fact", "L2", "fact-written", scope)

    async def assimilate_l3_episode(
        self,
        scope: ScopeEnvelope,
        text_to_assimilate: str,
        domain_tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WriteAck:
        self.calls.append(
            (
                "assimilate_l3_episode",
                (scope, text_to_assimilate),
                {"domain_tags": domain_tags, "metadata": metadata},
            )
        )
        return _write_ack("yaam.l3.assimilate_episode", "L3", "episode-written", scope)

    async def finalize_l4_artifact(
        self,
        scope: ScopeEnvelope,
        title: str,
        final_artifact: str,
        consensus_metadata: dict[str, Any] | None = None,
    ) -> WriteAck:
        self.calls.append(
            (
                "finalize_l4_artifact",
                (scope, title, final_artifact),
                {"consensus_metadata": consensus_metadata},
            )
        )
        return _write_ack("yaam.l4.finalize_artifact", "L4", "knowledge-written", scope)

    async def record_curation_decision(
        self,
        scope: ScopeEnvelope,
        task_id: str,
        decision: str,
        reason: str,
        source_triad: dict[str, Any],
        reviewer: str,
        metadata: dict[str, Any] | None = None,
    ) -> WriteAck:
        self.calls.append(
            (
                "record_curation_decision",
                (scope, task_id, decision, reason, source_triad, reviewer),
                {"metadata": metadata},
            )
        )
        return _write_ack(
            "yaam.curation.record_decision", "L2", "curation-written", scope
        )

    async def record_trace_correlation(
        self,
        scope: ScopeEnvelope,
        trace_id: str | None = None,
        artifact_ref: str | None = None,
        openrouter_call_id: str | None = None,
        linked_memory_ids: list[str] | None = None,
        error_summary: str | None = None,
        trace_status: str = "unverified",
        metadata: dict[str, Any] | None = None,
    ) -> WriteAck:
        self.calls.append(
            (
                "record_trace_correlation",
                (scope,),
                {
                    "trace_id": trace_id,
                    "artifact_ref": artifact_ref,
                    "openrouter_call_id": openrouter_call_id,
                    "linked_memory_ids": linked_memory_ids,
                    "error_summary": error_summary,
                    "trace_status": trace_status,
                    "metadata": metadata,
                },
            )
        )
        return _write_ack(
            "yaam.trace.record_correlation", "L2", "tracecorr-written", scope
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


def _write_ack(operation: str, tier: str, source_id: str, scope: ScopeEnvelope) -> WriteAck:
    return WriteAck(
        operation=operation,
        created_id=source_id,
        provenance=_provenance(tier, source_id, scope),
    )


def _curation_record(scope: ScopeEnvelope, task_id: str) -> CurationDecisionRecord:
    return CurationDecisionRecord(
        curation_record_id="curation-fixture",
        task_id=task_id,
        decision="accepted",
        reason="Fixture curation decision.",
        source_triad={"ctt_id": "ctt-fixture"},
        reviewer="maintainer",
        provenance=_provenance("L2", "curation-fixture", scope),
        metadata={"record_type": "scm_cert_bench_curation_decision"},
    )


def _trace_correlation(scope: ScopeEnvelope, correlation_id: str) -> TraceCorrelationRecord:
    return TraceCorrelationRecord(
        correlation_id=correlation_id,
        trace_id="phoenix-trace-fixture",
        task_id=scope.task_id,
        run_id=scope.run_id,
        artifact_ref="data/gold/golden_tasks_questions_only.jsonl",
        linked_memory_ids=["fact-fixture"],
        trace_status="unverified",
        provenance=_provenance("L2", correlation_id, scope),
        metadata={"record_type": "scm_cert_bench_trace_correlation"},
    )
