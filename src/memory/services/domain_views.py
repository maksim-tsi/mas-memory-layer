"""Optional customer/domain views built on top of public memory services."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

from src.memory.services.contracts import MemoryResult, ScopeEnvelope, redact_metadata

SKILL_FACTORY_DOMAIN = "skill_factory"
SKILL_FACTORY_METADATA_KEYS = (
    "domain",
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
COGNITIVE_SANDWICH_METADATA_KEYS = (
    "domain",
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


class SkillFactoryDomainViewService:
    """Read-only Skill Factory projections over generic YAAM memory services."""

    def __init__(self, gateway: Any, project_id: str | None = None) -> None:
        self.gateway = gateway
        self.project_id = project_id or getattr(gateway, "project_id", "test")

    async def skill_view(self, skill_name: str, limit: int = 20) -> dict[str, Any]:
        filters = {"skill_name": skill_name}
        items, warnings = await self._collect(
            query=f"Skill Factory skill {skill_name} generation QA repair curation",
            filters=filters,
            limit=limit,
        )
        return self._payload("skill", filters, items, warnings)

    async def ctt_view(self, ctt_id: str, limit: int = 20) -> dict[str, Any]:
        filters = {"ctt_id": ctt_id}
        items, warnings = await self._collect(
            query=f"Skill Factory CTT {ctt_id} skill generation QA repair curation",
            filters=filters,
            limit=limit,
        )
        return self._payload("ctt", filters, items, warnings)

    async def run_episodes(self, run_id: str, limit: int = 20) -> dict[str, Any]:
        filters = {"run_id": run_id}
        items, warnings = await self._collect_domain_records(
            filters=filters,
            limit=limit,
        )
        l3_items = [item for item in _matching_items(items, filters) if item.tier == "L3"]
        if not l3_items:
            scope = self._scope(filters)
            fallback_items, fallback_warnings = await self._call_results(
                "L3",
                lambda: self.gateway.search_l3_episodes(
                    scope,
                    query=f"Skill Factory run {run_id} repair generation episode",
                    limit=limit,
                ),
            )
            l3_items = [
                item for item in _matching_items(fallback_items, filters) if item.tier == "L3"
            ]
            warnings.extend(fallback_warnings)
        return self._payload("run_episodes", filters, l3_items[:limit], warnings)

    async def qa_status_runs(self, qa_status: str, limit: int = 20) -> dict[str, Any]:
        filters = {"qa_status": qa_status}
        items, warnings = await self._collect(
            query=f"Skill Factory QA status {qa_status} runs repair validation",
            filters=filters,
            limit=limit,
        )
        return self._runs_payload("qa_status_runs", filters, items, warnings)

    async def active_tool_status_runs(
        self, active_tool_status: str, limit: int = 20
    ) -> dict[str, Any]:
        filters = {"active_tool_status": active_tool_status}
        items, warnings = await self._collect(
            query=f"Skill Factory active tool status {active_tool_status} runs repair validation",
            filters=filters,
            limit=limit,
        )
        return self._runs_payload("active_tool_status_runs", filters, items, warnings)

    async def _collect(
        self,
        query: str,
        filters: dict[str, str],
        limit: int,
    ) -> tuple[list[MemoryResult], list[dict[str, Any]]]:
        domain_items, domain_warnings = await self._collect_domain_records(
            filters=filters,
            limit=limit,
        )
        if domain_items:
            return _matching_items(domain_items, filters)[:limit], domain_warnings

        scope = self._scope(filters)
        warnings: list[dict[str, Any]] = []
        collected: list[MemoryResult] = []

        for tier, call in (
            (
                "L2",
                lambda: self.gateway.search_l2_facts(scope, query=query, limit=limit),
            ),
            (
                "L3",
                lambda: self.gateway.search_l3_episodes(scope, query=query, limit=limit),
            ),
            (
                "L4",
                lambda: self.gateway.search_l4_knowledge(scope, query=query, limit=limit),
            ),
        ):
            items, tier_warnings = await self._call_results(tier, call)
            collected.extend(items)
            warnings.extend(tier_warnings)

        return _matching_items(collected, filters)[:limit], warnings

    async def _collect_domain_records(
        self,
        filters: dict[str, str],
        limit: int,
    ) -> tuple[list[MemoryResult], list[dict[str, Any]]]:
        list_records = getattr(self.gateway, "list_skill_factory_domain_records", None)
        if not callable(list_records):
            return [], []

        try:
            return (
                list(
                    await list_records(
                        self._scope(filters),
                        filters=filters,
                        limit=limit,
                    )
                    or []
                ),
                [],
            )
        except Exception as exc:
            return [], [
                {
                    "code": "domain_pack.partial_projection",
                    "message": (
                        "Skill Factory deterministic domain projection failed: "
                        f"{type(exc).__name__}"
                    ),
                    "affected_tier": "DOMAIN",
                    "retryable": True,
                }
            ]

    async def _call_results(
        self,
        tier: str,
        call: Callable[[], Awaitable[list[MemoryResult]]],
    ) -> tuple[list[MemoryResult], list[dict[str, Any]]]:
        try:
            return list(await call() or []), []
        except Exception as exc:
            return [], [
                {
                    "code": "domain_pack.partial_tier",
                    "message": f"Skill Factory {tier} domain view query failed: {type(exc).__name__}",
                    "affected_tier": tier,
                    "retryable": True,
                }
            ]

    def _scope(self, filters: dict[str, str]) -> ScopeEnvelope:
        return ScopeEnvelope(
            session_id="*",
            agent_id="skill-factory-domain-pack",
            caller_role="benchmark_runtime_agent",
            visibility_scope="benchmark_runtime",
            domain_ids={key: value for key, value in filters.items() if value},
            metadata={
                "domain": SKILL_FACTORY_DOMAIN,
                "project_id": self.project_id,
                **{key: value for key, value in filters.items() if value},
            },
        )

    def _payload(
        self,
        view: str,
        filters: dict[str, str],
        items: list[MemoryResult],
        warnings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        dumped = [_dump_result(item) for item in items]
        return {
            "domain_pack": "skill-factory",
            "view": view,
            "project_id": self.project_id,
            "filters": filters,
            "counts": {
                "items": len(dumped),
                "l2": sum(1 for item in dumped if item.get("tier") == "L2"),
                "l3": sum(1 for item in dumped if item.get("tier") == "L3"),
                "l4": sum(1 for item in dumped if item.get("tier") == "L4"),
            },
            "items": dumped,
            "partial": bool(warnings),
            "warnings": warnings,
        }

    def _runs_payload(
        self,
        view: str,
        filters: dict[str, str],
        items: list[MemoryResult],
        warnings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = self._payload(view, filters, items, warnings)
        runs: dict[str, dict[str, Any]] = {}
        for item in payload["items"]:
            metadata = item.get("metadata", {})
            provenance = item.get("provenance") or {}
            run_id = str(
                metadata.get("run_id")
                or provenance.get("run_id")
                or _content_key_value(item.get("content", ""), "run_id")
                or ""
            )
            if not run_id:
                continue
            summary = runs.setdefault(
                run_id,
                {
                    "run_id": run_id,
                    "skill_names": set(),
                    "ctt_ids": set(),
                    "qa_statuses": set(),
                    "active_tool_statuses": set(),
                    "source_ids": [],
                },
            )
            content = item.get("content", "")
            _add_optional(
                summary["skill_names"],
                metadata.get("skill_name") or _content_key_value(content, "skill_name"),
            )
            _add_optional(
                summary["ctt_ids"],
                metadata.get("ctt_id") or _content_key_value(content, "ctt_id"),
            )
            _add_optional(
                summary["qa_statuses"],
                metadata.get("qa_status") or _content_key_value(content, "qa_status"),
            )
            _add_optional(
                summary["active_tool_statuses"],
                metadata.get("active_tool_status")
                or _content_key_value(content, "active_tool_status"),
            )
            _add_optional(summary["source_ids"], item.get("source_id"))

        payload["runs"] = [
            {
                **summary,
                "skill_names": sorted(summary["skill_names"]),
                "ctt_ids": sorted(summary["ctt_ids"]),
                "qa_statuses": sorted(summary["qa_statuses"]),
                "active_tool_statuses": sorted(summary["active_tool_statuses"]),
            }
            for summary in runs.values()
        ]
        payload["counts"]["runs"] = len(payload["runs"])
        return payload


class CognitiveSandwichDomainViewService:
    """Read-only Cognitive Sandwich artifact projections over YAAM memory services."""

    def __init__(self, gateway: Any, project_id: str | None = None) -> None:
        self.gateway = gateway
        self.project_id = project_id or getattr(gateway, "project_id", "test")

    async def artifact_lineage(self, artifact_id: str, limit: int = 50) -> dict[str, Any]:
        filters = {"artifact_id": artifact_id}
        items, warnings = await self._collect(
            query=f"Cognitive Sandwich artifact {artifact_id} lineage feedback revision commit",
            filters=filters,
            limit=limit,
        )
        return self._lineage_payload("artifact_lineage", filters, items, warnings)

    async def session_artifacts(self, session_id: str, limit: int = 50) -> dict[str, Any]:
        filters = {"client_session_id": session_id}
        items, warnings = await self._collect(
            query=f"Cognitive Sandwich session {session_id} artifacts lineage feedback",
            filters=filters,
            limit=limit,
        )
        return self._artifacts_payload("session_artifacts", filters, items, warnings)

    async def run_artifacts(self, run_id: str, limit: int = 50) -> dict[str, Any]:
        filters = {"run_id": run_id}
        items, warnings = await self._collect(
            query=f"Cognitive Sandwich run {run_id} artifacts evidence feedback report",
            filters=filters,
            limit=limit,
        )
        return self._artifacts_payload("run_artifacts", filters, items, warnings)

    async def run_evidence(self, run_id: str, limit: int = 50) -> dict[str, Any]:
        filters = {"run_id": run_id}
        items, warnings = await self._collect(
            query=f"Cognitive Sandwich run {run_id} solver feedback sandbox evidence",
            filters=filters,
            limit=limit,
        )
        payload = self._payload("run_evidence", filters, items, warnings)
        payload["evidence"] = [_evidence_row(item) for item in payload["items"]]
        payload["counts"]["evidence"] = len(payload["evidence"])
        return payload

    async def incident_reports(self, incident_id: str, limit: int = 50) -> dict[str, Any]:
        filters = {"incident_id": incident_id}
        items, warnings = await self._collect(
            query=f"Cognitive Sandwich incident {incident_id} final report fatal validation",
            filters=filters,
            limit=limit,
        )
        reports = [item for item in items if item.tier == "L4"]
        return self._payload("incident_reports", filters, reports[:limit], warnings)

    async def _collect(
        self,
        query: str,
        filters: dict[str, str],
        limit: int,
    ) -> tuple[list[MemoryResult], list[dict[str, Any]]]:
        domain_items, domain_warnings = await self._collect_domain_records(filters, limit)
        if domain_items:
            return _matching_items(domain_items, filters)[:limit], domain_warnings

        scope = self._scope(filters)
        warnings: list[dict[str, Any]] = []
        collected: list[MemoryResult] = []

        for tier, call in (
            (
                "L2",
                lambda: self.gateway.search_l2_facts(scope, query=query, limit=limit),
            ),
            (
                "L3",
                lambda: self.gateway.search_l3_episodes(scope, query=query, limit=limit),
            ),
            (
                "L4",
                lambda: self.gateway.search_l4_knowledge(scope, query=query, limit=limit),
            ),
        ):
            items, tier_warnings = await self._call_results(tier, call)
            collected.extend(items)
            warnings.extend(tier_warnings)

        return _matching_items(collected, filters)[:limit], warnings

    async def _collect_domain_records(
        self,
        filters: dict[str, str],
        limit: int,
    ) -> tuple[list[MemoryResult], list[dict[str, Any]]]:
        list_records = getattr(self.gateway, "list_cognitive_sandwich_domain_records", None)
        if not callable(list_records):
            return [], []

        try:
            return (
                list(await list_records(self._scope(filters), filters=filters, limit=limit) or []),
                [],
            )
        except Exception as exc:
            return [], [
                {
                    "code": "domain_pack.partial_projection",
                    "message": (
                        "Cognitive Sandwich deterministic domain projection failed: "
                        f"{type(exc).__name__}"
                    ),
                    "affected_tier": "DOMAIN",
                    "retryable": True,
                }
            ]

    async def _call_results(
        self,
        tier: str,
        call: Callable[[], Awaitable[list[MemoryResult]]],
    ) -> tuple[list[MemoryResult], list[dict[str, Any]]]:
        try:
            return list(await call() or []), []
        except Exception as exc:
            return [], [
                {
                    "code": "domain_pack.partial_tier",
                    "message": (
                        f"Cognitive Sandwich {tier} domain view query failed: "
                        f"{type(exc).__name__}"
                    ),
                    "affected_tier": tier,
                    "retryable": True,
                }
            ]

    def _scope(self, filters: dict[str, str]) -> ScopeEnvelope:
        return ScopeEnvelope(
            session_id="*",
            agent_id="cognitive-sandwich-domain-pack",
            caller_role="benchmark_runtime_agent",
            visibility_scope="benchmark_runtime",
            domain_ids={key: value for key, value in filters.items() if value},
            metadata={
                "domain": COGNITIVE_SANDWICH_DOMAIN,
                "project_id": self.project_id,
                **{key: value for key, value in filters.items() if value},
            },
        )

    def _payload(
        self,
        view: str,
        filters: dict[str, str],
        items: list[MemoryResult],
        warnings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        dumped = [_dump_result(item) for item in items]
        return {
            "domain_pack": "cognitive-sandwich",
            "view": view,
            "project_id": self.project_id,
            "filters": filters,
            "counts": {
                "items": len(dumped),
                "l2": sum(1 for item in dumped if item.get("tier") == "L2"),
                "l3": sum(1 for item in dumped if item.get("tier") == "L3"),
                "l4": sum(1 for item in dumped if item.get("tier") == "L4"),
            },
            "items": dumped,
            "partial": bool(warnings),
            "warnings": warnings,
        }

    def _lineage_payload(
        self,
        view: str,
        filters: dict[str, str],
        items: list[MemoryResult],
        warnings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = self._payload(view, filters, items, warnings)
        payload["nodes"] = [_lineage_node(item) for item in payload["items"]]
        payload["nodes"].sort(key=_lineage_sort_key)
        payload["counts"]["nodes"] = len(payload["nodes"])
        return payload

    def _artifacts_payload(
        self,
        view: str,
        filters: dict[str, str],
        items: list[MemoryResult],
        warnings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = self._payload(view, filters, items, warnings)
        artifacts: dict[str, dict[str, Any]] = {}
        for item in payload["items"]:
            metadata = item.get("metadata", {})
            artifact_id = str(metadata.get("artifact_id") or "")
            if not artifact_id:
                continue
            summary = artifacts.setdefault(
                artifact_id,
                {
                    "artifact_id": artifact_id,
                    "revision_ids": set(),
                    "feedback_ids": set(),
                    "commit_ids": set(),
                    "statuses": set(),
                    "verification_states": set(),
                    "source_ids": [],
                },
            )
            _add_optional(summary["revision_ids"], metadata.get("revision_id"))
            _add_optional(summary["feedback_ids"], metadata.get("feedback_id"))
            _add_optional(summary["commit_ids"], metadata.get("commit_id"))
            _add_optional(summary["statuses"], metadata.get("artifact_status"))
            _add_optional(summary["verification_states"], metadata.get("verification_state"))
            _add_optional(summary["source_ids"], item.get("source_id"))

        payload["artifacts"] = [
            {
                **summary,
                "revision_ids": sorted(summary["revision_ids"]),
                "feedback_ids": sorted(summary["feedback_ids"]),
                "commit_ids": sorted(summary["commit_ids"]),
                "statuses": sorted(summary["statuses"]),
                "verification_states": sorted(summary["verification_states"]),
            }
            for summary in artifacts.values()
        ]
        payload["counts"]["artifacts"] = len(payload["artifacts"])
        return payload


def _matching_items(items: list[MemoryResult], filters: dict[str, str]) -> list[MemoryResult]:
    return [item for item in items if _matches_filters(item, filters)]


def _matches_filters(item: MemoryResult, filters: dict[str, str]) -> bool:
    haystack = item.content.lower()

    for key, expected in filters.items():
        expected_normalized = str(expected).lower()
        actual = _metadata_value(item, key)
        if actual is not None and str(actual).lower() == expected_normalized:
            continue
        if expected_normalized in haystack:
            continue
        return False
    return True


def _metadata_value(item: MemoryResult, key: str) -> Any:
    metadata = item.metadata or {}
    provenance_metadata = item.provenance.metadata if item.provenance else {}
    for source in (metadata, provenance_metadata):
        value = source.get(key)
        if value is not None:
            return value
        nested = source.get("metadata")
        if isinstance(nested, dict) and nested.get(key) is not None:
            return nested[key]
    provenance_value = getattr(item.provenance, key, None) if item.provenance else None
    if provenance_value is not None:
        return provenance_value
    return _content_key_value(item.content, key)


def _content_key_value(content: str, key: str) -> str | None:
    match = re.search(rf"\b{re.escape(key)}=([^\s,.;]+)", content)
    return match.group(1) if match else None


def _dump_result(item: MemoryResult) -> dict[str, Any]:
    dumped = item.model_dump(mode="json")
    dumped["metadata"] = redact_metadata(dumped.get("metadata", {}))
    if dumped.get("provenance"):
        dumped["provenance"]["metadata"] = redact_metadata(
            dumped["provenance"].get("metadata", {})
        )
    return dumped


def _lineage_node(item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata", {})
    return {
        "node_type": _lineage_node_type(item),
        "source_tier": item.get("tier"),
        "source_id": item.get("source_id"),
        "artifact_id": metadata.get("artifact_id"),
        "revision_id": metadata.get("revision_id"),
        "parent_revision_id": metadata.get("parent_revision_id"),
        "feedback_id": metadata.get("feedback_id"),
        "commit_id": metadata.get("commit_id"),
        "revision_number": metadata.get("revision_number"),
        "artifact_status": metadata.get("artifact_status"),
        "verification_state": metadata.get("verification_state"),
        "feedback_type": metadata.get("feedback_type"),
        "payload_hash": metadata.get("payload_hash"),
        "timestamp": (item.get("provenance") or {}).get("created_at"),
        "content": item.get("content"),
        "metadata": metadata,
    }


def _lineage_node_type(item: dict[str, Any]) -> str:
    metadata = item.get("metadata", {})
    if metadata.get("commit_id") or metadata.get("artifact_status") == "committed":
        return "commit"
    if metadata.get("feedback_id") or metadata.get("feedback_type"):
        return "feedback"
    if metadata.get("revision_id"):
        return "revision"
    if item.get("tier") == "L4":
        return "knowledge"
    return "evidence"


def _lineage_sort_key(node: dict[str, Any]) -> tuple[int, int, str]:
    type_rank = {"revision": 0, "feedback": 1, "commit": 2, "knowledge": 3, "evidence": 4}
    try:
        revision_number = int(node.get("revision_number") or 0)
    except (TypeError, ValueError):
        revision_number = 0
    return (
        revision_number,
        type_rank.get(str(node.get("node_type")), 9),
        str(node.get("source_id") or ""),
    )


def _evidence_row(item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata", {})
    provenance = item.get("provenance") or {}
    return {
        "evidence_id": item.get("source_id"),
        "source_tier": item.get("tier"),
        "source_id": item.get("source_id"),
        "source_system": metadata.get("source_system"),
        "claim": metadata.get("claim") or item.get("content"),
        "artifact_id": metadata.get("artifact_id"),
        "revision_id": metadata.get("revision_id"),
        "feedback_id": metadata.get("feedback_id"),
        "run_id": metadata.get("run_id") or provenance.get("run_id"),
        "incident_id": metadata.get("incident_id"),
        "trace_id": provenance.get("trace_id") or metadata.get("trace_id"),
        "metadata": metadata,
    }


def _add_optional(target: set[str] | list[str], value: Any) -> None:
    if value is None:
        return
    text = str(value)
    if not text:
        return
    if isinstance(target, set):
        target.add(text)
    elif text not in target:
        target.append(text)
