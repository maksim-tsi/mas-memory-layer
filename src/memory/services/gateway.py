"""Shared memory service layer for public adapters."""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime
from typing import Any

from src.memory.ciar_formula import calculate_ciar_score
from src.memory.models import Episode, EpisodeStoreInput, Fact, KnowledgeDocument, SearchWeights
from src.memory.services.contracts import (
    ContextResponse,
    EvidenceRow,
    EvidenceTableResponse,
    HealthResponse,
    MemoryResult,
    Provenance,
    ScopeEnvelope,
    WriteAck,
    YAAMWarning,
    memory_result_from_episode,
    memory_result_from_fact,
    memory_result_from_knowledge,
    memory_result_from_unified,
    redact_metadata,
)
from src.memory.services.permissions import PermissionPolicy
from src.observability import set_span_attributes, set_span_error, start_span


class MemoryGatewayService:
    """Service façade shared by MCP, REST v2, and future public adapters."""

    def __init__(
        self,
        memory_system: Any,
        permission_policy: PermissionPolicy | None = None,
    ) -> None:
        self.memory_system = memory_system
        self.permission_policy = permission_policy or PermissionPolicy()

    async def query_memory(
        self,
        scope: ScopeEnvelope,
        query: str,
        limit: int = 10,
        weights: SearchWeights | None = None,
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
                raw_results = await self.memory_system.query_memory(
                    session_id=scope.session_id,
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

    async def get_context(
        self,
        scope: ScopeEnvelope,
        min_ciar: float = 0.6,
        max_turns: int = 20,
        max_facts: int = 10,
    ) -> ContextResponse:
        """Assemble bounded context with provenance-bearing result items."""
        self.permission_policy.require("yaam.memory.get_context", "read")
        context = await self.memory_system.get_context_block(
            session_id=scope.session_id,
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

        return ContextResponse(
            session_id=scope.session_id,
            items=items,
            context_summary=context.to_prompt_string(include_metadata=False),
            estimated_tokens=context.estimated_tokens,
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
        fact_id = str(uuid.uuid4())
        fact_metadata = self._write_metadata(scope, metadata)
        fact = Fact(
            fact_id=fact_id,
            session_id=scope.session_id,
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
        if query and hasattr(l2_tier, "search_facts"):
            facts = await l2_tier.search_facts(
                query=query,
                session_id=scope.session_id,
                limit=limit,
            )
        else:
            kwargs: dict[str, Any] = {"session_id": scope.session_id, "limit": limit}
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
        kwargs: dict[str, Any] = {"session_id": scope.session_id}
        if limit is not None:
            kwargs["limit"] = limit
        if min_ciar is not None:
            kwargs["min_ciar_score"] = min_ciar
        return list(await l2_tier.query_by_session(**kwargs) or [])

    async def get_fact(self, scope: ScopeEnvelope, fact_id: str) -> MemoryResult | None:
        """Resolve a single L2 fact through the tier API."""
        self.permission_policy.require("yaam.l2.search_facts", "read")
        l2_tier = self._require_tier("l2_tier", "L2")
        fact = await l2_tier.retrieve(fact_id)
        if fact is None:
            return None
        result = memory_result_from_fact(fact, scope)
        if (
            scope.session_id != "*"
            and result.provenance
            and result.provenance.session_id not in {None, scope.session_id}
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
        episodes = await self.memory_system._query_l3_episodes(
            session_id=scope.session_id,
            query=query,
            limit=limit,
        )
        return [memory_result_from_episode(episode, scope) for episode in episodes or []]

    async def get_episode(self, scope: ScopeEnvelope, episode_id: str) -> MemoryResult | None:
        """Resolve a single L3 episode through the tier API."""
        self.permission_policy.require("yaam.l3.search_episodes", "read")
        l3_tier = self._require_tier("l3_tier", "L3")
        episode = await l3_tier.retrieve(episode_id)
        if episode is None:
            return None
        result = memory_result_from_episode(episode, scope)
        if (
            scope.session_id != "*"
            and result.provenance
            and result.provenance.session_id not in {None, scope.session_id}
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
            session_id=scope.session_id,
            summary=text_to_assimilate[:100],
            time_window_start=now,
            time_window_end=now,
            fact_valid_from=now,
            source_observation_timestamp=now,
            topics=domain_tags or [],
            metadata=self._write_metadata(scope, metadata),
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

    async def get_knowledge(self, scope: ScopeEnvelope, knowledge_id: str) -> MemoryResult | None:
        """Resolve a single L4 knowledge document through the tier API."""
        self.permission_policy.require("yaam.l4.search_knowledge", "read")
        l4_tier = self._require_tier("l4_tier", "L4")
        document = await l4_tier.retrieve(knowledge_id)
        if document is None:
            return None
        result = memory_result_from_knowledge(document, scope)
        if (
            scope.session_id != "*"
            and result.provenance
            and result.provenance.session_id not in {None, scope.session_id}
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
        knowledge_id = f"kd-{uuid.uuid4().hex[:8]}"
        document_metadata = self._write_metadata(scope, consensus_metadata)
        document = KnowledgeDocument(
            knowledge_id=knowledge_id,
            session_id=scope.session_id,
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
            },
            warnings=warnings,
        )

    def _require_tier(self, attr_name: str, tier_label: str) -> Any:
        tier = getattr(self.memory_system, attr_name, None)
        if not tier:
            raise RuntimeError(f"{tier_label} memory tier is not configured.")
        return tier

    def _write_metadata(
        self, scope: ScopeEnvelope, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        merged = {
            **(metadata or {}),
            "agent_id": scope.agent_id,
            "task_id": scope.task_id,
            "tenant_id": scope.tenant_id,
            "run_id": scope.run_id,
            "traceparent": scope.traceparent,
            "source": "mcp_v1_service",
        }
        return redact_metadata({key: value for key, value in merged.items() if value is not None})

    def _trace_attributes(
        self, scope: ScopeEnvelope, operation: str, extra: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        attributes = {
            "session.id": scope.session_id,
            "yaam.agent_id": scope.agent_id,
            "yaam.task_id": scope.task_id or "",
            "yaam.operation": operation,
            "yaam.tenant_id": scope.tenant_id or "",
            "yaam.run_id": scope.run_id or "",
        }
        if extra:
            attributes.update(extra)
        return attributes


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value
