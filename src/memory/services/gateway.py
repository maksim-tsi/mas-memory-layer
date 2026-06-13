"""Shared memory service layer for public adapters."""

from __future__ import annotations

import inspect
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from src.memory.ciar_formula import calculate_ciar_score
from src.memory.models import Episode, EpisodeStoreInput, Fact, KnowledgeDocument, SearchWeights
from src.memory.namespace import normalize_project_id, project_scoped_session_id
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
    memory_result_from_episode,
    memory_result_from_fact,
    memory_result_from_knowledge,
    memory_result_from_unified,
    redact_metadata,
)
from src.memory.services.permissions import PermissionPolicy, YAAMPermissionError
from src.observability import set_span_attributes, set_span_error, start_span

BENCHMARK_RUNTIME_ROLE = "benchmark_runtime_agent"
MAINTAINER_ROLES = frozenset({"benchmark_maintainer", "post_run_ingestion_service"})
BENCHMARK_RUNTIME_SCOPE = "benchmark_runtime"
MAINTAINER_ONLY_SCOPE = "maintainer_only"
DEFAULT_FORBIDDEN_BENCHMARK_FIELDS = (
    "ground_truth_answer",
    "ground_truth_reasoning",
    "judge_reasoning",
    "judge_notes",
    "curation_notes",
    "curation_record",
    "rejected_task_diagnostics",
    "hidden_gold",
)
HIDDEN_VISIBILITY_SCOPES = frozenset(
    {"maintainer_only", "curation_only", "judge_only", "audit_only", "hidden_gold"}
)
CURATION_RECORD_TYPE = "scm_cert_bench_curation_decision"
TRACE_CORRELATION_RECORD_TYPE = "scm_cert_bench_trace_correlation"
SKILL_FACTORY_DOMAIN = "skill_factory"
SKILL_FACTORY_DOMAIN_SCAN_LIMIT = 500
SKILL_FACTORY_METADATA_KEYS = (
    "skill_name",
    "ctt_id",
    "run_id",
    "qa_status",
    "active_tool_status",
    "sandbox_outcome",
    "repair_action",
    "artifact_kind",
)
COGNITIVE_SANDWICH_DOMAIN = "cognitive_sandwich"
COGNITIVE_SANDWICH_DOMAIN_SCAN_LIMIT = 500
COGNITIVE_SANDWICH_METADATA_KEYS = (
    "artifact_id",
    "revision_id",
    "parent_revision_id",
    "feedback_id",
    "commit_id",
    "run_id",
    "thread_id",
    "incident_id",
    "scenario_id",
    "artifact_kind",
    "artifact_status",
    "revision_number",
    "verification_state",
    "feedback_type",
    "source_system",
    "payload_hash",
    "fatal_status",
    "retry_count",
)
COGNITIVE_SANDWICH_L4_EXACT_STRING_FILTER_FIELDS = frozenset(
    {
        "project_id",
        "client_session_id",
        "domain",
        *(
            key
            for key in COGNITIVE_SANDWICH_METADATA_KEYS
            if key not in {"revision_number", "retry_count"}
        ),
    }
)


class MemoryGatewayService:
    """Service façade shared by MCP, REST v2, and future public adapters."""

    def __init__(
        self,
        memory_system: Any,
        permission_policy: PermissionPolicy | None = None,
        project_id: str | None = None,
    ) -> None:
        self.memory_system = memory_system
        self.permission_policy = permission_policy or PermissionPolicy()
        self.project_id = normalize_project_id(project_id)

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
        """Run scoped unified memory retrieval across L2/L3/L4."""
        self.permission_policy.require("yaam.memory.query", "read")
        with start_span(
            tracer_name="yaam.service",
            span_name="yaam.mcp.memory.query",
            kind="RETRIEVER",
            attributes=self._trace_attributes(scope, "yaam.memory.query", {"input.value": query}),
        ) as span:
            try:
                storage_scope = self._storage_scope(scope)
                raw_results = await self.memory_system.query_memory(
                    session_id=storage_scope.session_id,
                    query=query,
                    limit=limit,
                    weights=weights,
                )
                results = [memory_result_from_unified(item, scope) for item in raw_results]
                set_span_attributes(span, {"yaam.retrieval.result_count": len(results)})
                return results
            except Exception as exc:
                set_span_error(span, exc)
                raise

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
        """Run retrieval and return explicit leakage guard metadata."""
        results = await self.query_memory(
            scope,
            query=query,
            limit=limit,
            weights=weights,
            allowed_fields=allowed_fields,
            forbidden_fields=forbidden_fields,
            require_leakage_guard=require_leakage_guard,
        )
        return self._apply_leakage_guard(
            results,
            scope=scope,
            allowed_fields=allowed_fields,
            forbidden_fields=forbidden_fields,
            require_leakage_guard=require_leakage_guard,
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
        """Assemble bounded context with provenance-bearing result items."""
        self.permission_policy.require("yaam.memory.get_context", "read")
        storage_scope = self._storage_scope(scope)
        context = await self.memory_system.get_context_block(
            session_id=storage_scope.session_id,
            min_ciar=min_ciar,
            max_turns=max_turns,
            max_facts=max_facts,
        )
        items: list[MemoryResult] = []
        for fact in context.significant_facts:
            items.append(memory_result_from_fact(fact, scope))
        for index, turn in enumerate(context.recent_turns):
            content = str(turn.get("content", "")) if isinstance(turn, dict) else ""
            turn_id = str(turn.get("turn_id", index)) if isinstance(turn, dict) else str(index)
            items.append(
                MemoryResult(
                    content=content,
                    tier="L1",
                    source_id=turn_id,
                    metadata=redact_metadata(
                        turn.get("metadata", {}) if isinstance(turn, dict) else {}
                    ),
                    provenance=Provenance(
                        source_tier="L1",
                        source_id=turn_id,
                        session_id=scope.session_id,
                        agent_id=scope.agent_id,
                        task_id=scope.task_id,
                        tenant_id=scope.tenant_id,
                        run_id=scope.run_id,
                    ),
                )
            )

        items, guard = self._apply_leakage_guard(
            items,
            scope=scope,
            allowed_fields=allowed_fields,
            forbidden_fields=forbidden_fields,
            require_leakage_guard=require_leakage_guard,
        )
        context_summary = context.to_prompt_string(include_metadata=False)
        if guard.filtered_item_count:
            context_summary = "\n".join(item.content for item in items)
        return ContextResponse(
            session_id=scope.session_id,
            items=items,
            context_summary=context_summary,
            estimated_tokens=context.estimated_tokens,
            partial=bool(guard.warnings),
            warnings=guard.warnings,
            visibility_scope=guard.visibility_scope,
            leakage_guard_passed=guard.leakage_guard_passed,
            filtered_item_count=guard.filtered_item_count,
        )

    async def store_l2_fact(
        self,
        scope: ScopeEnvelope,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> WriteAck:
        """Persist an explicitly authorized L2 fact."""
        self.permission_policy.require("yaam.l2.store_fact", "write")
        l2_tier = self._require_tier("l2_tier", "L2")
        storage_scope = self._storage_scope(scope)
        fact_id = str(uuid.uuid4())
        fact_metadata = self._write_metadata(storage_scope, metadata)
        fact_metadata["fact_id"] = fact_id
        fact = Fact(
            fact_id=fact_id,
            session_id=storage_scope.session_id,
            content=content,
            fact_type="event",
            ciar_score=calculate_ciar_score(1.0, 1.0, 1.0, 1.0),
            certainty=1.0,
            impact=1.0,
            age_decay=1.0,
            recency_boost=1.0,
            metadata=fact_metadata,
        )
        stored_id = await l2_tier.store(fact)
        created_id = str(stored_id or fact_id)
        return WriteAck(
            operation="yaam.l2.store_fact",
            created_id=created_id,
            provenance=Provenance(
                source_tier="L2",
                source_id=created_id,
                session_id=scope.session_id,
                agent_id=scope.agent_id,
                task_id=scope.task_id,
                tenant_id=scope.tenant_id,
                run_id=scope.run_id,
                created_at=fact.extracted_at,
                metadata=redact_metadata(fact_metadata),
            ),
        )

    async def search_l2_facts(
        self,
        scope: ScopeEnvelope,
        query: str | None = None,
        min_ciar: float | None = None,
        limit: int = 20,
    ) -> list[MemoryResult]:
        """Search or list scoped L2 facts."""
        self.permission_policy.require("yaam.l2.search_facts", "read")
        l2_tier = self._require_tier("l2_tier", "L2")
        storage_scope = self._storage_scope(scope)
        if query and hasattr(l2_tier, "search_facts"):
            facts = await l2_tier.search_facts(
                query=query,
                session_id=storage_scope.session_id,
                limit=limit,
            )
        else:
            kwargs: dict[str, Any] = {"session_id": storage_scope.session_id, "limit": limit}
            if min_ciar is not None:
                kwargs["min_ciar_score"] = min_ciar
            facts = await l2_tier.query_by_session(**kwargs)
        return [memory_result_from_fact(fact, scope) for fact in facts or []]

    async def list_l2_facts(
        self,
        scope: ScopeEnvelope,
        min_ciar: float | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        """List scoped L2 facts without changing legacy adapter response shape."""
        self.permission_policy.require("yaam.l2.search_facts", "read")
        l2_tier = self._require_tier("l2_tier", "L2")
        storage_scope = self._storage_scope(scope)
        kwargs: dict[str, Any] = {"session_id": storage_scope.session_id}
        if limit is not None:
            kwargs["limit"] = limit
        if min_ciar is not None:
            kwargs["min_ciar_score"] = min_ciar
        return list(await l2_tier.query_by_session(**kwargs) or [])

    async def get_fact(self, scope: ScopeEnvelope, fact_id: str) -> MemoryResult | None:
        """Resolve a single L2 fact through the tier API."""
        self.permission_policy.require("yaam.l2.search_facts", "read")
        l2_tier = self._require_tier("l2_tier", "L2")
        storage_scope = self._storage_scope(scope)
        fact = await l2_tier.retrieve(fact_id)
        if fact is None:
            return None
        result = memory_result_from_fact(fact, scope)
        if result.source_id != fact_id:
            return None
        metadata = result.metadata or {}
        project_id = metadata.get("project_id")
        result_session_id = result.provenance.session_id if result.provenance else None
        if project_id not in {None, self.project_id}:
            return None
        if (
            isinstance(result_session_id, str)
            and ":" in result_session_id
            and not result_session_id.startswith(f"{self.project_id}:")
        ):
            return None
        if (
            scope.session_id != "*"
            and result.provenance
            and result.provenance.session_id not in {None, scope.session_id, storage_scope.session_id}
        ):
            return None
        return result

    async def search_l3_episodes(
        self,
        scope: ScopeEnvelope,
        query: str,
        limit: int = 10,
    ) -> list[MemoryResult]:
        """Search scoped L3 episodes using existing unified retrieval helpers."""
        self.permission_policy.require("yaam.l3.search_episodes", "read")
        if not getattr(self.memory_system, "l3_tier", None):
            return []
        storage_scope = self._storage_scope(scope)
        episodes = await self.memory_system._query_l3_episodes(
            session_id=storage_scope.session_id,
            query=query,
            limit=limit,
        )
        return [memory_result_from_episode(episode, scope) for episode in episodes or []]

    async def get_episode(self, scope: ScopeEnvelope, episode_id: str) -> MemoryResult | None:
        """Resolve a single L3 episode through the tier API."""
        self.permission_policy.require("yaam.l3.search_episodes", "read")
        l3_tier = self._require_tier("l3_tier", "L3")
        storage_scope = self._storage_scope(scope)
        episode = await l3_tier.retrieve(episode_id)
        if episode is None:
            return None
        result = memory_result_from_episode(episode, scope)
        if (
            scope.session_id != "*"
            and result.provenance
            and result.provenance.session_id not in {None, scope.session_id, storage_scope.session_id}
        ):
            return None
        return result

    async def assimilate_l3_episode(
        self,
        scope: ScopeEnvelope,
        text_to_assimilate: str,
        domain_tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WriteAck:
        """Persist an explicitly authorized L3 episode."""
        self.permission_policy.require("yaam.l3.assimilate_episode", "lifecycle")
        l3_tier = self._require_tier("l3_tier", "L3")
        storage_scope = self._storage_scope(scope)
        llm_client = getattr(self.memory_system, "llm_client", None)
        if not llm_client:
            raise RuntimeError("L3 assimilation requires an LLM client for embeddings.")

        embedding = await llm_client.get_embedding(text_to_assimilate)
        prompt = f"Extract structured graph entities from: {text_to_assimilate}"
        await llm_client.generate(prompt)

        episode_id = f"ep-{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC)
        episode = Episode(
            episode_id=episode_id,
            session_id=storage_scope.session_id,
            project_id=self.project_id,
            summary=text_to_assimilate[:100],
            time_window_start=now,
            time_window_end=now,
            fact_valid_from=now,
            source_observation_timestamp=now,
            topics=domain_tags or [],
            metadata=self._write_metadata(storage_scope, metadata),
        )
        episode_input = EpisodeStoreInput(
            episode=episode,
            embedding=embedding,
            entities=[
                {
                    "entity_id": f"ent-{uuid.uuid4().hex[:8]}",
                    "name": "ExtractedEntity",
                    "type": "Concept",
                    "label": "Concept",
                }
            ],
            relationships=[],
        )
        stored_id = await l3_tier.store(episode_input)
        created_id = str(stored_id or episode_id)
        return WriteAck(
            operation="yaam.l3.assimilate_episode",
            created_id=created_id,
            provenance=Provenance(
                source_tier="L3",
                source_id=created_id,
                session_id=scope.session_id,
                agent_id=scope.agent_id,
                task_id=scope.task_id,
                tenant_id=scope.tenant_id,
                run_id=scope.run_id,
                created_at=episode.consolidated_at,
                metadata=redact_metadata(episode.metadata),
            ),
        )

    async def search_l4_knowledge(
        self,
        scope: ScopeEnvelope,
        query: str,
        limit: int = 10,
    ) -> list[MemoryResult]:
        """Search L4 knowledge documents."""
        self.permission_policy.require("yaam.l4.search_knowledge", "read")
        docs = await self.memory_system._query_l4_documents(query=query, limit=limit)
        return [memory_result_from_knowledge(document, scope) for document in docs or []]

    async def list_skill_factory_domain_records(
        self,
        scope: ScopeEnvelope,
        filters: dict[str, str] | None = None,
        limit: int = 20,
    ) -> list[MemoryResult]:
        """List bounded Skill Factory records by canonical metadata across tiers."""
        self.permission_policy.require("yaam.memory.query", "read")
        requested_filters = filters or {}
        scan_limit = max(limit * 10, SKILL_FACTORY_DOMAIN_SCAN_LIMIT)
        records: list[MemoryResult] = []

        l2_tier = getattr(self.memory_system, "l2_tier", None)
        if l2_tier and hasattr(l2_tier, "query"):
            facts = await l2_tier.query(
                filters={},
                limit=scan_limit,
                include_low_ciar=True,
                order_by="created_at DESC",
            )
            records.extend(memory_result_from_fact(fact, scope) for fact in facts or [])

        l3_tier = getattr(self.memory_system, "l3_tier", None)
        qdrant = getattr(l3_tier, "qdrant", None)
        if qdrant and hasattr(qdrant, "scroll"):
            points = await qdrant.scroll(
                collection_name=getattr(l3_tier, "collection_name", None),
                filter_dict={
                    "must": [
                        {"key": "project_id", "match": {"value": self.project_id}},
                    ]
                },
                limit=scan_limit,
            )
            records.extend(memory_result_from_episode(point, scope) for point in points or [])

        l4_tier = getattr(self.memory_system, "l4_tier", None)
        if l4_tier and hasattr(l4_tier, "search"):
            query = " ".join(
                [
                    "Skill Factory",
                    *(str(value) for value in requested_filters.values() if value),
                ]
            )
            documents = await l4_tier.search(
                query_text=query or "Skill Factory",
                filters={"project_id": self.project_id},
                limit=limit,
            )
            records.extend(
                memory_result_from_knowledge(document, scope) for document in documents or []
            )

        return [
            record
            for record in records
            if self._is_skill_factory_domain_record(record)
            and self._record_matches_filters(record, requested_filters)
        ][:limit]

    async def list_cognitive_sandwich_domain_records(
        self,
        scope: ScopeEnvelope,
        filters: dict[str, str] | None = None,
        limit: int = 20,
    ) -> list[MemoryResult]:
        """List bounded Cognitive Sandwich records by canonical metadata across tiers."""
        self.permission_policy.require("yaam.memory.query", "read")
        requested_filters = filters or {}
        scan_limit = max(limit * 10, COGNITIVE_SANDWICH_DOMAIN_SCAN_LIMIT)
        records: list[MemoryResult] = []

        l2_tier = getattr(self.memory_system, "l2_tier", None)
        if l2_tier and hasattr(l2_tier, "query"):
            facts = await l2_tier.query(
                filters={},
                limit=scan_limit,
                include_low_ciar=True,
                order_by="created_at DESC",
            )
            records.extend(memory_result_from_fact(fact, scope) for fact in facts or [])

        l3_tier = getattr(self.memory_system, "l3_tier", None)
        qdrant = getattr(l3_tier, "qdrant", None)
        if qdrant and hasattr(qdrant, "scroll"):
            points = await qdrant.scroll(
                collection_name=getattr(l3_tier, "collection_name", None),
                filter_dict={
                    "must": [
                        {"key": "project_id", "match": {"value": self.project_id}},
                    ]
                },
                limit=scan_limit,
            )
            records.extend(memory_result_from_episode(point, scope) for point in points or [])

        l4_tier = getattr(self.memory_system, "l4_tier", None)
        if l4_tier and hasattr(l4_tier, "search"):
            l4_records: list[MemoryResult] = []
            filter_by = _cognitive_sandwich_l4_filter_by(self.project_id, requested_filters)
            if filter_by:
                exact_search = getattr(l4_tier, "search_by_exact_metadata", None)
                if inspect.iscoroutinefunction(exact_search):
                    exact_documents = await exact_search(filter_by=filter_by, limit=scan_limit)
                else:
                    exact_documents = await l4_tier.search(
                        query_text="*",
                        filters={"project_id": self.project_id},
                        filter_by=filter_by,
                        limit=scan_limit,
                    )
                l4_records.extend(
                    memory_result_from_knowledge(document, scope)
                    for document in exact_documents or []
                )

            query = " ".join(
                [
                    "Cognitive Sandwich artifact evidence lineage",
                    *(str(value) for value in requested_filters.values() if value),
                ]
            )
            documents = await l4_tier.search(
                query_text=query,
                filters={"project_id": self.project_id},
                limit=limit,
            )
            l4_records.extend(
                memory_result_from_knowledge(document, scope)
                for document in documents or []
            )
            records.extend(_dedupe_results(l4_records))

        return [
            record
            for record in records
            if self._is_cognitive_sandwich_domain_record(record)
            and self._record_matches_filters(record, requested_filters)
        ][:limit]

    async def get_knowledge(self, scope: ScopeEnvelope, knowledge_id: str) -> MemoryResult | None:
        """Resolve a single L4 knowledge document through the tier API."""
        self.permission_policy.require("yaam.l4.search_knowledge", "read")
        l4_tier = self._require_tier("l4_tier", "L4")
        storage_scope = self._storage_scope(scope)
        document = await l4_tier.retrieve(knowledge_id)
        if document is None:
            return None
        result = memory_result_from_knowledge(document, scope)
        if (
            scope.session_id != "*"
            and result.provenance
            and result.provenance.session_id not in {None, scope.session_id, storage_scope.session_id}
        ):
            return None
        return result

    async def finalize_l4_artifact(
        self,
        scope: ScopeEnvelope,
        title: str,
        final_artifact: str,
        consensus_metadata: dict[str, Any] | None = None,
    ) -> WriteAck:
        """Persist an explicitly authorized final L4 knowledge artifact."""
        self.permission_policy.require("yaam.l4.finalize_artifact", "lifecycle")
        l4_tier = self._require_tier("l4_tier", "L4")
        storage_scope = self._storage_scope(scope)
        knowledge_id = f"kd-{uuid.uuid4().hex[:8]}"
        document_metadata = self._write_metadata(storage_scope, consensus_metadata)
        document = KnowledgeDocument(
            knowledge_id=knowledge_id,
            session_id=storage_scope.session_id,
            project_id=self.project_id,
            title=title,
            content=final_artifact,
            metadata=document_metadata,
        )
        stored_id = await l4_tier.store(document)
        created_id = str(stored_id or knowledge_id)
        return WriteAck(
            operation="yaam.l4.finalize_artifact",
            created_id=created_id,
            provenance=Provenance(
                source_tier="L4",
                source_id=created_id,
                session_id=scope.session_id,
                agent_id=scope.agent_id,
                task_id=scope.task_id,
                tenant_id=scope.tenant_id,
                run_id=scope.run_id,
                created_at=document.distilled_at,
                metadata=redact_metadata(document_metadata),
            ),
        )

    async def explain_ciar(
        self,
        scope: ScopeEnvelope,
        fact: Fact | None = None,
        components: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Return deterministic CIAR component explanation."""
        self.permission_policy.require("yaam.ciar.explain", "read")
        source_components = components or {}
        certainty = float(source_components.get("certainty", getattr(fact, "certainty", 0.0)))
        impact = float(source_components.get("impact", getattr(fact, "impact", 0.0)))
        age_decay = float(source_components.get("age_decay", getattr(fact, "age_decay", 1.0)))
        recency_boost = float(
            source_components.get("recency_boost", getattr(fact, "recency_boost", 1.0))
        )
        score = calculate_ciar_score(certainty, impact, age_decay, recency_boost)
        return {
            "scope": scope.model_dump(mode="json"),
            "score": score,
            "components": {
                "certainty": certainty,
                "impact": impact,
                "age_decay": age_decay,
                "recency_boost": recency_boost,
            },
            "formula": "(certainty * impact) * age_decay * recency_boost",
        }

    async def evidence_table(
        self,
        scope: ScopeEnvelope,
        query: str,
        limit: int = 10,
    ) -> EvidenceTableResponse:
        """Build a deterministic evidence table from scoped memory retrieval."""
        self.permission_policy.require("yaam.evidence.table", "read")
        results = await self.query_memory(scope=scope, query=query, limit=limit)
        rows = [
            EvidenceRow(
                claim=result.content,
                source_tier=result.tier,
                source_id=result.source_id,
                evidence=result.content,
                provenance=result.provenance,
                policy_metadata={
                    "score": result.score,
                    "query": query,
                },
            )
            for result in results
        ]
        return EvidenceTableResponse(rows=rows, query=query, scope=scope)

    async def review_contradiction(
        self,
        scope: ScopeEnvelope,
        claims: list[str],
        expected_behavior: str | None = None,
        limit: int = 5,
    ) -> ContradictionReviewResponse:
        """Review claims for explicit supporting/conflicting evidence."""
        self.permission_policy.require("yaam.contradiction.review", "read")
        supporting: list[MemoryResult] = []
        conflicting: list[MemoryResult] = []
        warnings: list[YAAMWarning] = []

        for claim in claims:
            results, guard = await self.query_memory_checked(
                scope,
                query=claim,
                limit=limit,
                require_leakage_guard=_requires_benchmark_guard(scope),
            )
            warnings.extend(guard.warnings)
            for result in results:
                relation = str(result.metadata.get("evidence_relation", "")).lower()
                relation = relation or str(result.metadata.get("relation", "")).lower()
                if relation in {"conflict", "conflicting", "contradicts", "refutes"}:
                    conflicting.append(result)
                elif relation in {"support", "supporting", "supports"}:
                    supporting.append(result)

        contradiction_detected = bool(supporting and conflicting)
        if not supporting and not conflicting:
            warnings.append(
                YAAMWarning(
                    code="contradiction.insufficient_evidence",
                    message="No explicit supporting or conflicting evidence was found.",
                    affected_tier="SYSTEM",
                    retryable=False,
                    details={"claims": claims},
                )
            )

        rationale: str | None = None
        infeasibility_reason: str | None = None
        if contradiction_detected:
            infeasibility_reason = "Scoped evidence contains both supporting and conflicting records."
            if expected_behavior:
                rationale = (
                    "Safe refusal is recommended when the planning context contains unresolved "
                    f"conflicts and expected_behavior={expected_behavior}."
                )

        return ContradictionReviewResponse(
            contradiction_detected=contradiction_detected,
            infeasibility_reason=infeasibility_reason,
            supporting_evidence=supporting,
            conflicting_evidence=conflicting,
            safe_refusal_rationale=rationale,
            partial=bool(warnings),
            warnings=warnings,
            scope=scope,
        )

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
        """Store a maintainer-only SCM-Cert-Bench curation decision."""
        self.permission_policy.require("yaam.curation.record_decision", "write")
        _require_maintainer_or_ingestion(scope, "yaam.curation.record_decision")
        curation_record_id = f"curation-{uuid.uuid4().hex[:8]}"
        record_metadata = {
            "record_type": CURATION_RECORD_TYPE,
            "curation_record_id": curation_record_id,
            "task_id": task_id,
            "decision": decision,
            "reason": reason,
            "source_triad": source_triad,
            "reviewer": reviewer,
            "visibility_scope": MAINTAINER_ONLY_SCOPE,
            **(metadata or {}),
        }
        content = f"SCM-Cert-Bench curation decision for {task_id}: {decision}. {reason}"
        return await self._store_l2_record(
            scope=scope.model_copy(
                update={"task_id": task_id, "visibility_scope": MAINTAINER_ONLY_SCOPE}
            ),
            operation="yaam.curation.record_decision",
            content=content,
            metadata=record_metadata,
            created_id=curation_record_id,
        )

    async def list_curation_decisions(
        self,
        scope: ScopeEnvelope,
        task_id: str | None = None,
        limit: int = 50,
    ) -> list[CurationDecisionRecord]:
        """List visible SCM-Cert-Bench curation decisions."""
        self.permission_policy.require("yaam.curation.list_decisions", "read")
        _require_maintainer_or_ingestion(scope, "yaam.curation.list_decisions")
        facts = await self.list_l2_facts(scope, limit=limit)
        records: list[CurationDecisionRecord] = []
        for fact in facts:
            record = _curation_record_from_fact(fact, scope)
            if record is None:
                continue
            if task_id is None or record.task_id == task_id:
                records.append(record)
        return records

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
        """Store a safe external trace and artifact correlation record."""
        self.permission_policy.require("yaam.trace.record_correlation", "write")
        _require_maintainer_or_ingestion(scope, "yaam.trace.record_correlation")
        correlation_id = f"tracecorr-{uuid.uuid4().hex[:8]}"
        record_metadata = {
            "record_type": TRACE_CORRELATION_RECORD_TYPE,
            "correlation_id": correlation_id,
            "trace_id": trace_id,
            "artifact_ref": artifact_ref,
            "openrouter_call_id": openrouter_call_id,
            "linked_memory_ids": linked_memory_ids or [],
            "error_summary": error_summary,
            "trace_status": trace_status,
            **(metadata or {}),
        }
        content = f"Trace correlation {correlation_id} for task {scope.task_id or 'unscoped'}."
        return await self._store_l2_record(
            scope=scope,
            operation="yaam.trace.record_correlation",
            content=content,
            metadata=record_metadata,
            created_id=correlation_id,
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
        """Look up safe external trace and artifact correlation records."""
        self.permission_policy.require("yaam.trace.lookup", "read")
        _require_maintainer_or_ingestion(scope, "yaam.trace.lookup")
        facts = await self.list_l2_facts(scope, limit=limit)
        records: list[TraceCorrelationRecord] = []
        for fact in facts:
            record = _trace_correlation_from_fact(fact, scope)
            if record is None:
                continue
            if correlation_id is not None and record.correlation_id != correlation_id:
                continue
            if trace_id is not None and record.trace_id != trace_id:
                continue
            if task_id is not None and record.task_id != task_id:
                continue
            if run_id is not None and record.run_id != run_id:
                continue
            records.append(record)
        return records

    async def health_check(self) -> HealthResponse:
        """Return redacted health status for configured memory tiers."""
        self.permission_policy.require("yaam.health.check", "read")
        tiers: dict[str, Any] = {}
        warnings: list[YAAMWarning] = []
        for attr_name, tier_name in (
            ("l1_tier", "L1"),
            ("l2_tier", "L2"),
            ("l3_tier", "L3"),
            ("l4_tier", "L4"),
        ):
            tier = getattr(self.memory_system, attr_name, None)
            if not tier:
                tiers[tier_name] = {"configured": False, "status": "unavailable"}
                continue
            try:
                health = await _maybe_await(tier.health_check())
                tiers[tier_name] = redact_metadata(
                    health if isinstance(health, dict) else {"status": str(health)}
                )
                tiers[tier_name]["configured"] = True
            except Exception as exc:
                tiers[tier_name] = {"configured": True, "status": "unavailable"}
                warnings.append(
                    YAAMWarning(
                        code="health.tier_unavailable",
                        message=f"{tier_name} health check failed: {exc}",
                        affected_tier=tier_name,
                        retryable=True,
                    )
                )

        status = "ok" if not warnings else "degraded"
        if all(tier.get("status") == "unavailable" for tier in tiers.values()):
            status = "unavailable"
        return HealthResponse(
            status=status,
            tiers=tiers,
            config={
                "writes_enabled": self.permission_policy.enable_writes,
                "lifecycle_enabled": self.permission_policy.enable_lifecycle,
                "project_id": self.project_id,
            },
            warnings=warnings,
        )

    def _apply_leakage_guard(
        self,
        items: list[MemoryResult],
        scope: ScopeEnvelope,
        allowed_fields: list[str] | None = None,
        forbidden_fields: list[str] | None = None,
        require_leakage_guard: bool = False,
    ) -> tuple[list[MemoryResult], LeakageGuardResult]:
        strict = require_leakage_guard or _requires_benchmark_guard(scope)
        forbidden = _normalized_forbidden_fields(forbidden_fields)
        if not strict and not allowed_fields and not forbidden_fields:
            return items, LeakageGuardResult(
                leakage_guard_passed=False,
                visibility_scope=scope.visibility_scope,
                checked_item_count=0,
            )

        filtered: list[MemoryResult] = []
        filtered_count = 0
        for item in items:
            if _item_has_forbidden_visibility(item, forbidden, scope):
                filtered_count += 1
                continue
            filtered.append(item)

        warnings: list[YAAMWarning] = []
        if filtered_count:
            warnings.append(
                YAAMWarning(
                    code="leakage_guard.filtered",
                    message="Benchmark leakage guard removed hidden or forbidden memory items.",
                    affected_tier="SYSTEM",
                    retryable=False,
                    details={
                        "filtered_item_count": filtered_count,
                        "forbidden_fields": list(forbidden),
                    },
                )
            )

        return filtered, LeakageGuardResult(
            leakage_guard_passed=True,
            visibility_scope=scope.visibility_scope,
            forbidden_fields=list(forbidden),
            filtered_item_count=filtered_count,
            checked_item_count=len(items),
            warnings=warnings,
        )

    async def _store_l2_record(
        self,
        scope: ScopeEnvelope,
        operation: str,
        content: str,
        metadata: dict[str, Any],
        created_id: str,
    ) -> WriteAck:
        l2_tier = self._require_tier("l2_tier", "L2")
        storage_scope = self._storage_scope(scope)
        record_metadata = self._write_metadata(storage_scope, metadata)
        fact = Fact(
            fact_id=created_id,
            session_id=storage_scope.session_id,
            content=content,
            fact_type="event",
            ciar_score=calculate_ciar_score(1.0, 1.0, 1.0, 1.0),
            certainty=1.0,
            impact=1.0,
            age_decay=1.0,
            recency_boost=1.0,
            metadata=record_metadata,
        )
        stored_id = await l2_tier.store(fact)
        final_id = str(stored_id or created_id)
        return WriteAck(
            operation=operation,
            created_id=final_id,
            provenance=Provenance(
                source_tier="L2",
                source_id=final_id,
                session_id=scope.session_id,
                agent_id=scope.agent_id,
                task_id=scope.task_id,
                tenant_id=scope.tenant_id,
                run_id=scope.run_id,
                created_at=fact.extracted_at,
                metadata=redact_metadata(record_metadata),
            ),
        )

    def _require_tier(self, attr_name: str, tier_label: str) -> Any:
        tier = getattr(self.memory_system, attr_name, None)
        if not tier:
            raise RuntimeError(f"{tier_label} memory tier is not configured.")
        return tier

    def _write_metadata(
        self, scope: ScopeEnvelope, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        merged = dict(metadata or {})
        for key, value in (
            ("caller_role", scope.caller_role),
            ("visibility_scope", scope.visibility_scope),
            ("task_id", scope.task_id),
            ("tenant_id", scope.tenant_id),
            ("run_id", scope.run_id),
            ("traceparent", scope.traceparent),
        ):
            if value is not None:
                merged[key] = value

        merged.update(
            {
                "agent_id": scope.agent_id,
                "source": "mcp_v1_service",
                "project_id": self.project_id,
                "client_session_id": scope.metadata.get("client_session_id")
                or merged.get("client_session_id"),
            }
        )
        return redact_metadata(
            {key: value for key, value in merged.items() if value is not None}
        )

    def _is_skill_factory_domain_record(self, record: MemoryResult) -> bool:
        metadata = _merged_record_metadata(record)
        project_id = metadata.get("project_id")
        session_id = metadata.get("client_session_id") or (
            record.provenance.session_id if record.provenance else None
        )
        in_project = project_id == self.project_id or (
            isinstance(session_id, str) and session_id.startswith(f"{self.project_id}:")
        )
        content = record.content.lower()
        has_domain_marker = metadata.get("domain") == SKILL_FACTORY_DOMAIN or (
            "skill factory" in content or "skill_factory" in content
        )
        return in_project and has_domain_marker

    def _is_cognitive_sandwich_domain_record(self, record: MemoryResult) -> bool:
        metadata = _merged_record_metadata(record)
        project_id = metadata.get("project_id")
        session_id = metadata.get("client_session_id") or (
            record.provenance.session_id if record.provenance else None
        )
        in_project = project_id == self.project_id or (
            isinstance(session_id, str) and session_id.startswith(f"{self.project_id}:")
        )
        content = record.content.lower()
        has_domain_marker = metadata.get("domain") == COGNITIVE_SANDWICH_DOMAIN or (
            "cognitive sandwich" in content or "cognitive_sandwich" in content
        )
        return in_project and has_domain_marker

    def _record_matches_filters(
        self,
        record: MemoryResult,
        filters: dict[str, str],
    ) -> bool:
        metadata = _merged_record_metadata(record)
        content = record.content.lower()
        for key, expected in filters.items():
            expected_text = str(expected).lower()
            actual = metadata.get(key)
            if actual is not None and str(actual).lower() == expected_text:
                continue
            if expected_text in content:
                continue
            return False
        return True

    def _storage_scope(self, scope: ScopeEnvelope) -> ScopeEnvelope:
        if scope.session_id == "*":
            return scope.model_copy(update={"metadata": {**scope.metadata, "project_id": self.project_id}})
        return scope.model_copy(
            update={
                "session_id": project_scoped_session_id(scope.session_id, self.project_id),
                "metadata": {
                    **scope.metadata,
                    "client_session_id": scope.session_id,
                    "project_id": self.project_id,
                },
            }
        )

    def _trace_attributes(
        self, scope: ScopeEnvelope, operation: str, extra: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        attributes = {
            "session.id": scope.session_id,
            "yaam.agent_id": scope.agent_id,
            "yaam.caller_role": scope.caller_role or "",
            "yaam.visibility_scope": scope.visibility_scope or "",
            "yaam.task_id": scope.task_id or "",
            "yaam.operation": operation,
            "yaam.tenant_id": scope.tenant_id or "",
            "yaam.run_id": scope.run_id or "",
            "yaam.project_id": self.project_id,
        }
        if extra:
            attributes.update(extra)
        return attributes


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _requires_benchmark_guard(scope: ScopeEnvelope) -> bool:
    return (
        scope.caller_role == BENCHMARK_RUNTIME_ROLE
        or scope.visibility_scope == BENCHMARK_RUNTIME_SCOPE
    )


def _normalized_forbidden_fields(forbidden_fields: list[str] | None) -> set[str]:
    return {field.lower() for field in (forbidden_fields or DEFAULT_FORBIDDEN_BENCHMARK_FIELDS)}


def _dedupe_results(records: list[MemoryResult]) -> list[MemoryResult]:
    deduped: list[MemoryResult] = []
    seen: set[tuple[str, str | None]] = set()
    for record in records:
        key = (record.tier, record.source_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def _cognitive_sandwich_l4_filter_by(
    project_id: str, filters: dict[str, str]
) -> str | None:
    terms = [
        _typesense_exact_filter("project_id", project_id),
        _typesense_exact_filter("domain", COGNITIVE_SANDWICH_DOMAIN),
    ]
    for key, value in filters.items():
        if key not in COGNITIVE_SANDWICH_L4_EXACT_STRING_FILTER_FIELDS:
            continue
        term = _typesense_exact_filter(key, value)
        if term is None:
            return None
        terms.append(term)
    if any(term is None for term in terms):
        return None
    return " && ".join(str(term) for term in terms)


def _typesense_exact_filter(field: str, value: Any) -> str | None:
    if field not in COGNITIVE_SANDWICH_L4_EXACT_STRING_FILTER_FIELDS:
        return None
    text = str(value)
    if not text or any(char in text for char in ("`", "\n", "\r", "\t")):
        return None
    return f"{field}:=`{text}`"


def _merged_record_metadata(record: MemoryResult) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    if record.provenance and record.provenance.metadata:
        merged.update(record.provenance.metadata)
        nested = record.provenance.metadata.get("metadata")
        if isinstance(nested, dict):
            merged.update(nested)
    if record.metadata:
        merged.update(record.metadata)
        nested = record.metadata.get("metadata")
        if isinstance(nested, dict):
            merged.update(nested)
    if record.provenance:
        for key in ("session_id", "agent_id", "task_id", "tenant_id", "run_id"):
            value = getattr(record.provenance, key, None)
            if value is not None and key not in merged:
                merged[key] = value
    for key in (*SKILL_FACTORY_METADATA_KEYS, *COGNITIVE_SANDWICH_METADATA_KEYS):
        if key not in merged:
            value = _content_key_value(record.content, key)
            if value is not None:
                merged[key] = value
    return merged


def _content_key_value(content: str, key: str) -> str | None:
    match = re.search(rf"\b{re.escape(key)}=([^\s,.;]+)", content)
    return match.group(1) if match else None


def _item_has_forbidden_visibility(
    item: MemoryResult,
    forbidden_fields: set[str],
    scope: ScopeEnvelope,
) -> bool:
    metadata = item.metadata or {}
    if _requires_benchmark_guard(scope):
        item_scope = str(metadata.get("visibility_scope", "")).lower()
        if item_scope in HIDDEN_VISIBILITY_SCOPES:
            return True
    content = item.content.lower()
    for field in forbidden_fields:
        if field in content:
            return True
        if _metadata_has_forbidden_key(metadata, field):
            return True
    return False


def _metadata_has_forbidden_key(metadata: dict[str, Any], field: str) -> bool:
    for key, value in metadata.items():
        key_lower = key.lower()
        if field in key_lower:
            return True
        if isinstance(value, dict) and _metadata_has_forbidden_key(value, field):
            return True
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and _metadata_has_forbidden_key(item, field):
                    return True
    return False


def _require_maintainer_or_ingestion(scope: ScopeEnvelope, operation: str) -> None:
    if scope.caller_role in MAINTAINER_ROLES:
        return
    raise YAAMPermissionError(
        YAAMErrorPayload(
            code="permission.role_denied",
            message="Operation requires benchmark maintainer or post-run ingestion role.",
            retryable=False,
            operation=operation,
            affected_tier="SYSTEM",
            details={
                "caller_role": scope.caller_role,
                "allowed_roles": sorted(MAINTAINER_ROLES),
            },
        )
    )


def _curation_record_from_fact(
    fact: Any,
    scope: ScopeEnvelope,
) -> CurationDecisionRecord | None:
    metadata = _model_metadata(fact)
    if metadata.get("record_type") != CURATION_RECORD_TYPE:
        return None
    task_id = str(metadata.get("task_id") or scope.task_id or "")
    if not task_id:
        return None
    record_id = str(metadata.get("curation_record_id") or _model_value(fact, "fact_id", ""))
    return CurationDecisionRecord(
        curation_record_id=record_id,
        task_id=task_id,
        decision=str(metadata.get("decision", "")),
        reason=str(metadata.get("reason", "")),
        source_triad=_dict_value(metadata.get("source_triad")),
        reviewer=str(metadata.get("reviewer", "")),
        visibility_scope=str(metadata.get("visibility_scope") or MAINTAINER_ONLY_SCOPE),
        provenance=Provenance(
            source_tier="L2",
            source_id=record_id or "unknown",
            session_id=_model_value(fact, "session_id", scope.session_id),
            agent_id=metadata.get("agent_id") or scope.agent_id,
            task_id=task_id,
            tenant_id=scope.tenant_id,
            run_id=scope.run_id,
            created_at=_model_value(fact, "created_at", None)
            or _model_value(fact, "extracted_at", None),
            metadata=metadata,
        ),
        metadata=metadata,
    )


def _trace_correlation_from_fact(
    fact: Any,
    scope: ScopeEnvelope,
) -> TraceCorrelationRecord | None:
    metadata = _model_metadata(fact)
    if metadata.get("record_type") != TRACE_CORRELATION_RECORD_TYPE:
        return None
    correlation_id = str(metadata.get("correlation_id") or _model_value(fact, "fact_id", ""))
    linked_memory_ids = metadata.get("linked_memory_ids", [])
    if not isinstance(linked_memory_ids, list):
        linked_memory_ids = []
    return TraceCorrelationRecord(
        correlation_id=correlation_id,
        trace_id=_optional_str(metadata.get("trace_id")),
        task_id=_optional_str(metadata.get("task_id") or scope.task_id),
        run_id=_optional_str(metadata.get("run_id") or scope.run_id),
        artifact_ref=_optional_str(metadata.get("artifact_ref")),
        openrouter_call_id=_optional_str(metadata.get("openrouter_call_id")),
        linked_memory_ids=[str(item) for item in linked_memory_ids],
        error_summary=_optional_str(metadata.get("error_summary")),
        trace_status=str(metadata.get("trace_status") or "unverified"),
        provenance=Provenance(
            source_tier="L2",
            source_id=correlation_id or "unknown",
            session_id=_model_value(fact, "session_id", scope.session_id),
            agent_id=metadata.get("agent_id") or scope.agent_id,
            task_id=_optional_str(metadata.get("task_id") or scope.task_id),
            tenant_id=scope.tenant_id,
            run_id=_optional_str(metadata.get("run_id") or scope.run_id),
            created_at=_model_value(fact, "created_at", None)
            or _model_value(fact, "extracted_at", None),
            metadata=metadata,
        ),
        metadata=metadata,
    )


def _model_metadata(item: Any) -> dict[str, Any]:
    metadata = _model_value(item, "metadata", {})
    return redact_metadata(metadata if isinstance(metadata, dict) else {})


def _model_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _dict_value(value: Any) -> dict[str, Any]:
    return redact_metadata(value if isinstance(value, dict) else {})


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
