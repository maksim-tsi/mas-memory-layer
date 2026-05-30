"""Optional customer/domain views built on top of public memory services."""

from __future__ import annotations

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
            run_id = str(metadata.get("run_id") or provenance.get("run_id") or "")
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
            _add_optional(summary["skill_names"], metadata.get("skill_name"))
            _add_optional(summary["ctt_ids"], metadata.get("ctt_id"))
            _add_optional(summary["qa_statuses"], metadata.get("qa_status"))
            _add_optional(summary["active_tool_statuses"], metadata.get("active_tool_status"))
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
    return None


def _dump_result(item: MemoryResult) -> dict[str, Any]:
    dumped = item.model_dump(mode="json")
    dumped["metadata"] = redact_metadata(dumped.get("metadata", {}))
    if dumped.get("provenance"):
        dumped["provenance"]["metadata"] = redact_metadata(
            dumped["provenance"].get("metadata", {})
        )
    return dumped


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
