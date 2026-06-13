#!/usr/bin/env python3
"""Run a CIAR challenge experiment with Phoenix and local JSONL evidence.

This is a non-production experiment harness. It keeps current CIAR runtime
behavior unchanged while recording the data needed to challenge that behavior.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_MODEL = "x-ai/grok-4.1-fast"
DEFAULT_PHOENIX_DIRECT_ENDPOINT = "http://127.0.0.1:6006/v1/traces"
DEFAULT_TUNNEL_ENDPOINT = "http://127.0.0.1:16006/v1/traces"
DEFAULT_MIN_CIAR = 0.6
REQUIRED_OPERATIONAL_ARTIFACTS = (
    "summary.md",
    "promotion_results.json",
    "alternative_scores.json",
    "events.jsonl",
    "run_manifest.json",
)
LLM_WARNING_MARKERS = (
    "rule_fallback",
    "provider failure",
    "provider_failure",
    "provider failed",
    "provider_failed",
    "invalid response",
    "invalid_response",
    "empty response",
    "empty_response",
)
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_stamp() -> str:
    return utc_now().strftime("%Y%m%d-%H%M%S")


def json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "value"):
        return value.value
    return str(value)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=json_default),
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=json_default) + "\n")


def safe_env_presence(keys: list[str]) -> dict[str, bool]:
    return {key: bool(os.environ.get(key)) for key in keys}


def safe_endpoint_summary(value: str | None, default_port: int | None = None) -> dict[str, Any]:
    """Summarize a service endpoint without exposing credentials."""
    if not value:
        return {"present": False}
    parsed = urlparse(value)
    port = parsed.port or default_port
    return {
        "present": True,
        "scheme": parsed.scheme,
        "host": parsed.hostname,
        "port": port,
        "path_present": bool(parsed.path and parsed.path != "/"),
        "user_present": bool(parsed.username),
        "password_present": bool(parsed.password),
    }


def sanitized_service_endpoints() -> dict[str, dict[str, Any]]:
    return {
        "redis": safe_endpoint_summary(os.environ.get("REDIS_URL"), 6379),
        "postgres": safe_endpoint_summary(os.environ.get("POSTGRES_URL"), 5432),
        "phoenix": safe_endpoint_summary(os.environ.get("PHOENIX_COLLECTOR_ENDPOINT"), 6006),
    }


def sanitize_error_message(message: str) -> str:
    """Remove known secret-bearing values from diagnostic error strings."""
    sanitized = message
    for key in ["REDIS_URL", "POSTGRES_URL", "PHOENIX_COLLECTOR_ENDPOINT"]:
        value = os.environ.get(key)
        if value:
            sanitized = sanitized.replace(value, f"<{key}>")
    return re.sub(r"://([^:/@\s]+):([^@/\s]+)@", r"://\1:<redacted>@", sanitized)


def artifact_presence(
    output_dir: Path,
    *,
    assume_summary_present: bool = False,
) -> dict[str, bool]:
    presence = {name: (output_dir / name).exists() for name in REQUIRED_OPERATIONAL_ARTIFACTS}
    if assume_summary_present:
        presence["summary.md"] = True
    return presence


def cleanup_status(cleanup: Any) -> str:
    if cleanup is None:
        return "unknown"
    if isinstance(cleanup, str):
        if cleanup == "dry_run_noop":
            return "dry_run_noop"
        if cleanup.startswith("skipped"):
            return "skipped"
        return cleanup
    if not isinstance(cleanup, dict):
        return "unknown"
    if not cleanup:
        return "unknown"

    session_count = len(cleanup)
    error_count = 0
    for result in cleanup.values():
        if isinstance(result, dict) and any(key.endswith("_error") for key in result):
            error_count += 1
    if error_count == 0:
        return "ok"
    if error_count >= session_count:
        return "failed"
    return "partial"


def _contains_llm_warning(value: Any) -> bool:
    try:
        serialized = json.dumps(value, default=json_default).lower()
    except TypeError:
        serialized = str(value).lower()
    return any(marker in serialized for marker in LLM_WARNING_MARKERS)


def llm_response_warning_count(
    events: list[dict[str, Any]],
    alternative_scores: list[dict[str, Any]],
) -> int:
    warnings = sum(1 for event in events if _contains_llm_warning(event))
    for row in alternative_scores:
        if not isinstance(row, dict):
            continue
        flags = row.get("evidence_quality_flags") or {}
        if isinstance(flags, dict) and flags.get("rule_fallback"):
            warnings += 1
    return warnings


def scenario_error_count(promotion_stats: dict[str, Any]) -> int:
    total = 0
    for stats in promotion_stats.values():
        if isinstance(stats, dict):
            total += int(stats.get("errors", 0) or 0)
    return total


def classify_operational_run(
    *,
    manifest: dict[str, Any],
    promotion_stats: dict[str, Any],
    events: list[dict[str, Any]],
    alternative_scores: list[dict[str, Any]],
    artifacts: dict[str, bool],
) -> dict[str, Any]:
    provider_health = manifest.get("provider_health") or {}
    provider_health_status = (
        str(provider_health.get("status")) if isinstance(provider_health, dict) else "missing"
    )
    if provider_health_status == "None":
        provider_health_status = "missing"

    cleanup = cleanup_status(manifest.get("cleanup"))
    warning_count = llm_response_warning_count(events, alternative_scores)
    errors = scenario_error_count(promotion_stats)
    dry_run = bool(manifest.get("dry_run", False))
    phoenix_check = manifest.get("phoenix_ui_check") or {}
    phoenix_ui_ok = bool(phoenix_check.get("ok")) if isinstance(phoenix_check, dict) else False
    completed = bool(manifest.get("completed_at"))
    artifact_complete = all(artifacts.values())

    signals = {
        "completed": completed,
        "dry_run": dry_run,
        "provider_health_status": provider_health_status,
        "provider_fallback_detected": warning_count > 0,
        "phoenix_ui_ok": phoenix_ui_ok,
        "artifact_complete": artifact_complete,
        "cleanup_status": cleanup,
        "scenario_errors": errors,
        "llm_response_warning_count": warning_count,
    }

    reasons: list[str] = []
    if not completed:
        reasons.append("run did not record completed_at")
    if not artifact_complete:
        missing = ", ".join(name for name, present in artifacts.items() if not present)
        reasons.append(f"missing required artifacts: {missing}")
    if reasons:
        return {
            "run_quality": "incomplete",
            "policy_evidence": False,
            "reasons": reasons,
            "signals": signals,
        }

    if errors:
        reasons.append(f"promotion scenario errors recorded: {errors}")
    if warning_count:
        reasons.append(f"provider fallback or LLM response warnings detected: {warning_count}")
    if not dry_run and not phoenix_ui_ok:
        reasons.append("live Phoenix UI check did not succeed")
    if (
        isinstance(provider_health, dict)
        and provider_health_status == "failed"
        and provider_health.get("required")
    ):
        reasons.append("required provider health check failed")
    if reasons:
        return {
            "run_quality": "operational_noise",
            "policy_evidence": False,
            "reasons": reasons,
            "signals": signals,
        }

    warnings: list[str] = []
    if isinstance(provider_health, dict) and provider_health_status == "skipped":
        reason = provider_health.get("reason")
        warnings.append(
            f"provider health skipped: {reason}" if reason else "provider health skipped"
        )
    if isinstance(provider_health, dict) and provider_health_status == "failed":
        warnings.append("provider health failed but was not required")
    if dry_run and not phoenix_ui_ok:
        warnings.append("Phoenix UI check failed during dry run")
    if cleanup in {"partial", "failed"}:
        warnings.append(f"cleanup status is {cleanup}")

    if warnings:
        return {
            "run_quality": "policy_evidence_with_warnings",
            "policy_evidence": True,
            "reasons": warnings,
            "signals": signals,
        }

    return {
        "run_quality": "policy_evidence",
        "policy_evidence": True,
        "reasons": ["clean run"],
        "signals": signals,
    }


def normalize_fact_content(value: Any) -> str:
    """Normalize fact text for artifact joins across storage-generated ids."""
    return " ".join(str(value or "").casefold().split())


def endpoint_ui_base(endpoint: str) -> str:
    if endpoint.endswith("/v1/traces"):
        return endpoint[: -len("/v1/traces")]
    return endpoint.rstrip("/")


def resolve_phoenix_endpoint(
    explicit_endpoint: str | None,
    access_mode: str,
    allow_localhost_6006: bool = False,
) -> tuple[str, str]:
    """Resolve Phoenix collector endpoint and access mode.

    Localhost:6006 is rejected by default because MacBook development should use
    local-yaam-host directly or via an explicit SSH tunnel.
    """
    if explicit_endpoint:
        endpoint = explicit_endpoint
        resolved_mode = "configured"
    elif access_mode == "direct_ip":
        endpoint = DEFAULT_PHOENIX_DIRECT_ENDPOINT
        resolved_mode = "direct_ip"
    elif access_mode == "ssh_tunnel":
        endpoint = DEFAULT_TUNNEL_ENDPOINT
        resolved_mode = "ssh_tunnel"
    else:
        endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", DEFAULT_PHOENIX_DIRECT_ENDPOINT)
        resolved_mode = "env" if os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") else "direct_ip"

    parsed = urlparse(endpoint)
    is_localhost_6006 = parsed.hostname in {"localhost", "127.0.0.1"} and parsed.port == 6006
    if is_localhost_6006 and not allow_localhost_6006:
        raise ValueError(
            "Refusing PHOENIX_COLLECTOR_ENDPOINT on localhost:6006. "
            "For MacBook development use http://127.0.0.1:6006/v1/traces, "
            "or create an SSH tunnel and use http://127.0.0.1:16006/v1/traces."
        )
    return endpoint, resolved_mode


def check_http_reachable(url: str, timeout_s: float = 3.0) -> dict[str, Any]:
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return {"ok": True, "status": response.status, "url": url}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc), "url": url}


@dataclass
class Scenario:
    scenario_id: str
    title: str
    expectation: str
    turns: list[dict[str, str]]
    notes: str = ""


@dataclass
class ExperimentConfig:
    run_id: str
    output_dir: Path
    dry_run: bool
    keep_data: bool
    model: str
    min_ciar: float
    phoenix_endpoint: str
    phoenix_project_name: str
    phoenix_access_mode: str
    scenario_ids: list[str] = field(default_factory=list)
    skip_provider_health: bool = False
    provider_health_skip_reason: str = "operator requested skip"
    provider_health_timeout_s: float = 60.0
    require_provider_health: bool = False
    promotion_policy_mode: str = "hybrid_gate"
    contradiction_policy_mode: str = "off"
    scenario_delay_s: float = 0.0


@dataclass
class ExperimentResources:
    l1_tier: Any | None = None
    l2_tier: Any | None = None
    redis_adapter: Any | None = None
    postgres_l1: Any | None = None
    postgres_l2: Any | None = None


@dataclass
class ExperimentState:
    config: ExperimentConfig
    manifest: dict[str, Any] = field(default_factory=dict)
    scenarios: list[Scenario] = field(default_factory=list)
    session_by_scenario: dict[str, str] = field(default_factory=dict)
    promotion_stats: dict[str, Any] = field(default_factory=dict)
    l2_facts: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    ciar_calls: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    alternative_scores: list[dict[str, Any]] = field(default_factory=list)
    resources: ExperimentResources = field(default_factory=ExperimentResources)


class JsonlTelemetryStream:
    def __init__(self, output_dir: Path, state: ExperimentState) -> None:
        self.output_dir = output_dir
        self.state = state

    async def publish(self, event_type: str, session_id: str, data: dict[str, Any]) -> None:
        event = {
            "timestamp": utc_now().isoformat(),
            "event_type": event_type,
            "session_id": session_id,
            "data": data,
        }
        self.state.events.append(event)
        append_jsonl(self.output_dir / "events.jsonl", event)


class ObservedCIARScorer:
    """Delegating CIAR scorer that records calls without changing behavior."""

    def __init__(self, inner: Any, output_dir: Path, state: ExperimentState) -> None:
        self.inner = inner
        self.output_dir = output_dir
        self.state = state
        self.threshold = getattr(inner, "threshold", DEFAULT_MIN_CIAR)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def calculate(self, fact: Any) -> float:
        fact_id = getattr(fact, "fact_id", None)
        content = getattr(fact, "content", None)
        session_id = getattr(fact, "session_id", None)
        if isinstance(fact, dict):
            fact_id = fact.get("fact_id", fact_id)
            content = fact.get("content", content)
            session_id = fact.get("session_id", session_id)

        from src.observability import set_span_attributes, start_span

        with start_span(
            tracer_name="yaam.experiment",
            span_name="yaam.ciar.score",
            kind="TOOL",
            attributes={
                "yaam.ciar.threshold": self.threshold,
                "yaam.fact_id": fact_id,
                "session.id": session_id,
                "input.value": content,
            },
        ) as span:
            components = self.inner.calculate_components(fact)
            score = self.inner.calculate(fact)
            set_span_attributes(
                span,
                {
                    "output.value": score,
                    "yaam.ciar.certainty": components.get("certainty"),
                    "yaam.ciar.impact": components.get("impact"),
                    "yaam.ciar.age_decay": components.get("age_decay"),
                    "yaam.ciar.recency_boost": components.get("recency_boost"),
                    "yaam.ciar.base_score": components.get("base_score"),
                    "yaam.ciar.temporal_score": components.get("temporal_score"),
                },
            )

        record = {
            "timestamp": utc_now().isoformat(),
            "session_id": session_id,
            "fact_id": fact_id,
            "content": content,
            "score": score,
            "threshold": self.threshold,
            "components": components,
        }
        self.state.ciar_calls.append(record)
        append_jsonl(self.output_dir / "ciar_calls.jsonl", record)
        return score

    def calculate_components(self, fact: Any) -> dict[str, float]:
        return self.inner.calculate_components(fact)


class ObservedTopicSegmenter:
    """Delegating segmenter that creates experiment-level spans."""

    def __init__(self, inner: Any, state: ExperimentState) -> None:
        self.inner = inner
        self.state = state

    async def segment_turns(
        self, turns: list[dict[str, Any]], metadata: dict[str, Any] | None = None
    ) -> list[Any]:
        from src.observability import set_span_attributes, set_span_error, start_span

        session_id = str((metadata or {}).get("session_id", ""))
        with start_span(
            tracer_name="yaam.experiment",
            span_name="yaam.llm.topic_segment",
            kind="LLM",
            attributes={
                "session.id": session_id,
                "input.value": f"{len(turns)} turns",
                "llm.model_name": os.environ.get("MAS_TOPIC_SEGMENTER_MODEL"),
            },
        ) as span:
            try:
                segments = await self.inner.segment_turns(turns, metadata)
                set_span_attributes(
                    span,
                    {
                        "output.value": [
                            {
                                "segment_id": getattr(segment, "segment_id", None),
                                "topic": getattr(segment, "topic", None),
                                "certainty": getattr(segment, "certainty", None),
                                "impact": getattr(segment, "impact", None),
                            }
                            for segment in segments
                        ],
                        "yaam.segment.count": len(segments),
                    },
                )
                return segments
            except Exception as exc:
                set_span_error(span, exc)
                raise


class ObservedFactExtractor:
    """Delegating fact extractor that creates experiment-level spans."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner

    async def extract_facts(self, text: str, metadata: dict[str, Any] | None = None) -> list[Any]:
        from src.observability import set_span_attributes, set_span_error, start_span

        session_id = str((metadata or {}).get("session_id", ""))
        with start_span(
            tracer_name="yaam.experiment",
            span_name="yaam.llm.fact_extract",
            kind="LLM",
            attributes={
                "session.id": session_id,
                "input.value": text,
                "llm.model_name": os.environ.get("MAS_FACT_EXTRACTOR_MODEL"),
                "yaam.topic_segment_id": (metadata or {}).get("topic_segment_id"),
            },
        ) as span:
            try:
                facts = await self.inner.extract_facts(text, metadata)
                set_span_attributes(
                    span,
                    {
                        "output.value": [
                            {
                                "fact_id": getattr(fact, "fact_id", None),
                                "content": getattr(fact, "content", None),
                                "certainty": getattr(fact, "certainty", None),
                                "impact": getattr(fact, "impact", None),
                            }
                            for fact in facts
                        ],
                        "yaam.fact.count": len(facts),
                    },
                )
                return facts
            except Exception as exc:
                set_span_error(span, exc)
                raise


class CannedTopicSegmenter:
    """Dry-run segmenter with deterministic scenario outputs."""

    def __init__(self, scenario_by_session: dict[str, Scenario]) -> None:
        self.scenario_by_session = scenario_by_session

    async def segment_turns(
        self, turns: list[dict[str, Any]], metadata: dict[str, Any] | None = None
    ) -> list[Any]:
        from src.memory.engines.topic_segmenter import TopicSegment

        session_id = str((metadata or {}).get("session_id", ""))
        scenario = self.scenario_by_session[session_id]
        if scenario.scenario_id == "small_talk":
            return [
                TopicSegment(
                    segment_id=f"{scenario.scenario_id}-seg",
                    topic="Low value small talk",
                    summary="The conversation contains greetings and acknowledgments.",
                    key_points=["Greeting", "Thanks", "No durable user fact"],
                    turn_indices=list(range(min(len(turns), 10))),
                    certainty=0.95,
                    impact=0.15,
                    participant_count=2,
                    message_count=len(turns),
                )
            ]
        if scenario.scenario_id == "assistant_acknowledgement_noise":
            return [
                TopicSegment(
                    segment_id=f"{scenario.scenario_id}-seg",
                    topic="Assistant acknowledgement noise",
                    summary="The conversation contains only thanks and acknowledgements.",
                    key_points=["Thanks", "Acknowledgement", "No durable operational fact"],
                    turn_indices=list(range(min(len(turns), 10))),
                    certainty=0.95,
                    impact=0.12,
                    participant_count=2,
                    message_count=len(turns),
                )
            ]
        if scenario.scenario_id == "segment_mismatch":
            return [
                TopicSegment(
                    segment_id=f"{scenario.scenario_id}-seg",
                    topic="Urgent shipment issue with surrounding chatter",
                    summary="One urgent temperature excursion appears among routine logistics chatter.",
                    key_points=["Temperature excursion", "Routine acknowledgments"],
                    turn_indices=list(range(min(len(turns), 10))),
                    certainty=0.9,
                    impact=0.85,
                    participant_count=2,
                    message_count=len(turns),
                )
            ]
        if scenario.scenario_id == "repeated_correction":
            return [
                TopicSegment(
                    segment_id=f"{scenario.scenario_id}-seg",
                    topic="Repeated route correction for shipment ALFA-4421",
                    summary=(
                        "Shipment ALFA-4421 route changed from Oakland to Los Angeles "
                        "and then to Long Beach, with Long Beach explicitly current."
                    ),
                    key_points=[
                        "ALFA-4421 originally scheduled for Oakland",
                        "ALFA-4421 updated to Los Angeles",
                        "ALFA-4421 latest current route is Long Beach",
                    ],
                    turn_indices=list(range(min(len(turns), 10))),
                    certainty=0.95,
                    impact=0.9,
                    participant_count=2,
                    message_count=len(turns),
                )
            ]
        if scenario.scenario_id == "speculative_claim":
            certainty, impact = 0.85, 0.8
        elif scenario.scenario_id == "contradiction_update":
            certainty, impact = 0.9, 0.8
        elif scenario.scenario_id == "assistant_inferred":
            certainty, impact = 0.86, 0.78
        elif scenario.scenario_id == "access_reinforced_low_signal":
            certainty, impact = 0.92, 0.8
        else:
            certainty, impact = 0.92, 0.85

        return [
            TopicSegment(
                segment_id=f"{scenario.scenario_id}-seg",
                topic=scenario.title,
                summary=" ".join(turn["content"] for turn in scenario.turns[:4])[:500],
                key_points=[turn["content"] for turn in scenario.turns[:3]],
                turn_indices=list(range(min(len(turns), 10))),
                certainty=certainty,
                impact=impact,
                participant_count=2,
                message_count=len(turns),
            )
        ]


class CannedFactExtractor:
    """Dry-run fact extractor with deterministic fact outputs."""

    async def extract_facts(self, text: str, metadata: dict[str, Any] | None = None) -> list[Any]:
        from src.memory.models import Fact, FactCategory, FactType

        metadata = metadata or {}
        segment_id = str(metadata.get("topic_segment_id", "unknown"))
        session_id = str(metadata.get("session_id", "unknown"))
        topic = str(metadata.get("topic_label", "unknown"))

        def make_fact(
            suffix: str,
            content: str,
            fact_type: Any,
            certainty: float,
            impact: float,
            source_type: str = "dry_run",
            access_count: int = 0,
        ) -> Any:
            return Fact(
                fact_id=f"{segment_id}-{suffix}",
                session_id=session_id,
                content=content,
                fact_type=fact_type,
                fact_category=FactCategory.OPERATIONAL,
                certainty=certainty,
                impact=impact,
                access_count=access_count,
                source_type=source_type,
                topic_segment_id=segment_id,
                topic_label=topic,
                justification="Dry-run canned extraction for CIAR challenge.",
            )

        if "small_talk" in segment_id:
            return [
                make_fact(
                    "thanks",
                    "The user thanked the assistant.",
                    FactType.MENTION,
                    0.95,
                    0.1,
                )
            ]
        if "assistant_acknowledgement_noise" in segment_id:
            return [
                make_fact(
                    "thanks",
                    "The user thanked the assistant.",
                    FactType.MENTION,
                    0.95,
                    0.1,
                ),
                make_fact(
                    "acknowledgement",
                    "The assistant acknowledged the user's thanks.",
                    FactType.MENTION,
                    0.95,
                    0.1,
                ),
            ]
        if "segment_mismatch" in segment_id:
            return [
                make_fact(
                    "urgent",
                    "Container MAEU9182736 had a temperature excursion above threshold.",
                    FactType.EVENT,
                    0.92,
                    0.9,
                ),
                make_fact(
                    "chatter",
                    "The user said thanks and asked to continue later.",
                    FactType.MENTION,
                    0.9,
                    0.15,
                ),
            ]
        if "urgent_with_chatter" in segment_id:
            return [
                make_fact(
                    "urgent",
                    "Container MEDU7711009 missed its customs hold release window.",
                    FactType.EVENT,
                    0.94,
                    0.9,
                ),
                make_fact(
                    "assistant-recording",
                    (
                        "The assistant will record that container MEDU7711009 missed "
                        "its customs hold release window."
                    ),
                    FactType.MENTION,
                    0.92,
                    0.72,
                ),
            ]
        if "speculative_claim" in segment_id:
            return [
                make_fact(
                    "maybe",
                    "The supplier might miss the customs document deadline.",
                    FactType.EVENT,
                    0.42,
                    0.55,
                )
            ]
        if "contradiction_update" in segment_id:
            return [
                make_fact(
                    "old",
                    "The shipment was scheduled for Oakland.",
                    FactType.EVENT,
                    0.9,
                    0.75,
                ),
                make_fact(
                    "new",
                    "The shipment is now rerouted to Los Angeles instead of Oakland.",
                    FactType.EVENT,
                    0.92,
                    0.85,
                ),
            ]
        if "repeated_correction" in segment_id:
            return [
                make_fact(
                    "old-oakland",
                    "Shipment ALFA-4421 was scheduled for Oakland.",
                    FactType.EVENT,
                    0.9,
                    0.8,
                ),
                make_fact(
                    "middle-los-angeles",
                    "Update: shipment ALFA-4421 is now routed to Los Angeles.",
                    FactType.EVENT,
                    0.92,
                    0.82,
                ),
                make_fact(
                    "latest-long-beach",
                    (
                        "Latest correction: shipment ALFA-4421 is now routed to "
                        "Long Beach instead of Los Angeles or Oakland."
                    ),
                    FactType.EVENT,
                    0.95,
                    0.9,
                ),
            ]
        if "assistant_inferred" in segment_id:
            return [
                make_fact(
                    "inferred",
                    "The user likely prefers air freight for urgent shipments.",
                    FactType.PREFERENCE,
                    0.48,
                    0.7,
                )
            ]
        if "access_reinforced_low_signal" in segment_id:
            return [
                make_fact(
                    "reinforced-note",
                    "Carrier dashboard reference note was repeatedly opened by the operations team.",
                    FactType.MENTION,
                    0.5,
                    0.5,
                    access_count=20,
                )
            ]
        return [
            make_fact(
                "main",
                "The user requires customs paperwork before vessel release.",
                FactType.CONSTRAINT,
                0.92,
                0.88,
            )
        ]


def build_default_scenarios() -> list[Scenario]:
    def pad(turns: list[dict[str, str]]) -> list[dict[str, str]]:
        padded = list(turns)
        while len(padded) < 10:
            idx = len(padded)
            role = "assistant" if idx % 2 else "user"
            padded.append({"role": role, "content": f"Context filler turn {idx}."})
        return padded

    return [
        Scenario(
            scenario_id="clear_constraint",
            title="Clear high-certainty constraint",
            expectation="promote",
            turns=pad(
                [
                    {
                        "role": "user",
                        "content": "For Acme shipments, never release cargo without customs paperwork.",
                    },
                    {"role": "assistant", "content": "Understood."},
                    {
                        "role": "user",
                        "content": "This is a hard compliance rule for every LA port delivery.",
                    },
                ]
            ),
        ),
        Scenario(
            scenario_id="speculative_claim",
            title="Speculative supplier risk",
            expectation="needs_review",
            turns=pad(
                [
                    {
                        "role": "user",
                        "content": "The supplier might miss the customs document deadline, but I am not sure.",
                    },
                    {"role": "assistant", "content": "I will treat that as uncertain."},
                ]
            ),
        ),
        Scenario(
            scenario_id="small_talk",
            title="Low-value small talk",
            expectation="ignore",
            turns=pad(
                [
                    {"role": "user", "content": "Hi there."},
                    {"role": "assistant", "content": "Hello."},
                    {"role": "user", "content": "Thanks for the update."},
                ]
            ),
        ),
        Scenario(
            scenario_id="urgent_event",
            title="Urgent operational event",
            expectation="promote",
            turns=pad(
                [
                    {
                        "role": "user",
                        "content": "Urgent: reefer container MAEU9182736 is above temperature threshold.",
                    },
                    {
                        "role": "assistant",
                        "content": "I will mark this as a critical operational event.",
                    },
                    {"role": "user", "content": "Escalate it before vessel cutoff today."},
                ]
            ),
        ),
        Scenario(
            scenario_id="contradiction_update",
            title="Contradictory route update",
            expectation="should_conflict",
            turns=pad(
                [
                    {"role": "user", "content": "The shipment was scheduled for Oakland."},
                    {
                        "role": "user",
                        "content": "Correction: it is now rerouted to Los Angeles, not Oakland.",
                    },
                    {"role": "assistant", "content": "I will use Los Angeles as the current route."},
                ]
            ),
        ),
        Scenario(
            scenario_id="segment_mismatch",
            title="Segment gate with low-value extracted fact",
            expectation="should_not_floor",
            turns=pad(
                [
                    {
                        "role": "user",
                        "content": "Urgent: temperature excursion on container MAEU9182736.",
                    },
                    {"role": "assistant", "content": "I will record the exception."},
                    {"role": "user", "content": "Also thanks, we can continue later."},
                ]
            ),
        ),
        Scenario(
            scenario_id="assistant_inferred",
            title="Assistant-inferred preference",
            expectation="needs_review",
            turns=pad(
                [
                    {"role": "user", "content": "Can we get this shipment there by tomorrow?"},
                    {
                        "role": "assistant",
                        "content": "You probably prefer air freight for urgent shipments.",
                    },
                    {"role": "user", "content": "Maybe, but I did not say that as a rule."},
                ]
            ),
        ),
        Scenario(
            scenario_id="access_reinforced_low_signal",
            title="Access-reinforced low-signal note",
            expectation="needs_review",
            turns=pad(
                [
                    {
                        "role": "user",
                        "content": (
                            "Carrier dashboard reference note: this entry has been opened "
                            "many times by the operations team."
                        ),
                    },
                    {
                        "role": "assistant",
                        "content": "I see it has repeated access history.",
                    },
                    {
                        "role": "user",
                        "content": (
                            "Repeated access alone should not make it a confirmed operational "
                            "shipment fact."
                        ),
                    },
                ]
            ),
        ),
        Scenario(
            scenario_id="stale_preference",
            title="Stale routing preference replaced by current preference",
            expectation="should_conflict",
            turns=pad(
                [
                    {
                        "role": "user",
                        "content": "For West Coast overflow, prefer Oakland as the backup port.",
                    },
                    {
                        "role": "user",
                        "content": "Updated routing preference: use Los Angeles as the current backup port.",
                    },
                    {
                        "role": "assistant",
                        "content": "I will treat Los Angeles as the current backup preference.",
                    },
                ]
            ),
        ),
        Scenario(
            scenario_id="explicit_reversal",
            title="Explicit operational rule reversal",
            expectation="should_conflict",
            turns=pad(
                [
                    {
                        "role": "user",
                        "content": "For customer Helios, hold releases until finance approves.",
                    },
                    {
                        "role": "user",
                        "content": "Correction: Helios is now cleared for automatic release after customs approval.",
                    },
                    {
                        "role": "assistant",
                        "content": "I will use the automatic release rule for Helios going forward.",
                    },
                ]
            ),
        ),
        Scenario(
            scenario_id="repeated_correction",
            title="Critical repeated route correction",
            expectation="should_conflict",
            turns=pad(
                [
                    {
                        "role": "user",
                        "content": (
                            "Critical route-change log for shipment ALFA-4421: "
                            "Oakland was the active destination used for dispatch, "
                            "carrier booking, port appointment, customs destination, "
                            "and delivery planning."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Operational update for ALFA-4421: the shipment is now "
                            "routed to Los Angeles. Los Angeles supersedes Oakland "
                            "for dispatch, carrier booking, port appointment, customs "
                            "destination, and delivery planning."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Latest critical correction for shipment ALFA-4421: the "
                            "shipment is now routed to Long Beach instead of Los "
                            "Angeles or Oakland. Long Beach is the current route and "
                            "current customs destination; update dispatch, carrier "
                            "booking, port appointment, and delivery planning to Long "
                            "Beach. The previous routes, Oakland and Los Angeles, are "
                            "superseded."
                        ),
                    },
                ]
            ),
        ),
        Scenario(
            scenario_id="assistant_acknowledgement_noise",
            title="Assistant acknowledgement noise",
            expectation="ignore",
            turns=pad(
                [
                    {"role": "user", "content": "Thanks for checking that."},
                    {"role": "assistant", "content": "You are welcome."},
                    {"role": "user", "content": "No further action from me right now."},
                ]
            ),
        ),
        Scenario(
            scenario_id="urgent_with_chatter",
            title="Urgent operational fact with surrounding chatter",
            expectation="should_not_floor",
            turns=pad(
                [
                    {"role": "user", "content": "Morning, thanks again for yesterday."},
                    {
                        "role": "user",
                        "content": "Urgent: container MEDU7711009 missed its customs hold release window.",
                    },
                    {
                        "role": "assistant",
                        "content": "I will record the missed release window and escalation need.",
                    },
                    {"role": "user", "content": "Also, nice work on the earlier note."},
                ]
            ),
        ),
    ]


def build_formula_probe_rows() -> list[dict[str, Any]]:
    from src.memory.ciar_scorer import CIARScorer

    scorer = CIARScorer()
    now = utc_now()
    probes = [
        {"probe_id": "fresh_high", "certainty": 0.9, "impact": 0.9, "created_at": now},
        {
            "probe_id": "old_high",
            "certainty": 0.9,
            "impact": 0.9,
            "created_at": now.replace(year=max(1970, now.year - 1)),
        },
        {
            "probe_id": "reinforced_low",
            "certainty": 0.6,
            "impact": 0.5,
            "created_at": now,
            "access_count": 20,
        },
    ]
    rows = []
    for probe in probes:
        components = scorer.calculate_components(probe)
        rows.append({"probe": probe, "components": components})
    return rows


class CIARChallengeExperiment:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.state = ExperimentState(config=config)
        self.output_dir = config.output_dir / config.run_id
        self.telemetry = JsonlTelemetryStream(self.output_dir, self.state)

    async def run(self) -> ExperimentState:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._configure_environment()
        from src.observability import set_span_attributes, set_span_error, start_span

        with start_span(
            tracer_name="yaam.experiment",
            span_name="yaam.experiment.ciar_challenge",
            kind="CHAIN",
            attributes={
                "yaam.experiment.run_id": self.config.run_id,
                "yaam.experiment.dry_run": self.config.dry_run,
                "yaam.experiment.model": self.config.model,
                "tag.tags": ["ciar-challenge", f"run_id:{self.config.run_id}"],
            },
        ) as span:
            try:
                state = await self._run_graph()
                set_span_attributes(
                    span,
                    {
                        "yaam.experiment.scenario_count": len(state.scenarios),
                        "output.value": str(self.output_dir),
                    },
                )
                return state
            except Exception as exc:
                set_span_error(span, exc)
                raise

    def _configure_environment(self) -> None:
        os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = self.config.phoenix_endpoint
        os.environ["PHOENIX_PROJECT_NAME"] = self.config.phoenix_project_name
        os.environ["OPENROUTER_MODEL"] = self.config.model
        os.environ["MAS_MODEL"] = self.config.model
        os.environ["MAS_TOPIC_SEGMENTER_MODEL"] = self.config.model
        os.environ["MAS_FACT_EXTRACTOR_MODEL"] = self.config.model

    async def _run_graph(self) -> ExperimentState:
        try:
            from langgraph.graph import END, StateGraph
        except Exception:
            self.state.manifest["graph_backend"] = "sequential_fallback"
            for node in [
                self.preflight,
                self.build_scenarios,
                self.setup_runtime,
                self.seed_l1,
                self.run_promotion,
                self.collect_l2,
                self.score_alternatives,
                self.summarize,
                self.cleanup,
            ]:
                await node(self.state)
            return self.state

        self.state.manifest["graph_backend"] = "langgraph"

        async def node(
            name: str, fn: Callable[[ExperimentState], Awaitable[ExperimentState]]
        ) -> Callable[[ExperimentState], Awaitable[ExperimentState]]:
            async def wrapped(state: ExperimentState) -> ExperimentState:
                return await self._run_node(name, fn, state)

            return wrapped

        graph = StateGraph(ExperimentState)
        graph.add_node("preflight", await node("preflight", self.preflight))
        graph.add_node("build_scenarios", await node("build_scenarios", self.build_scenarios))
        graph.add_node("setup_runtime", await node("setup_runtime", self.setup_runtime))
        graph.add_node("seed_l1", await node("seed_l1", self.seed_l1))
        graph.add_node("run_promotion", await node("run_promotion", self.run_promotion))
        graph.add_node("collect_l2", await node("collect_l2", self.collect_l2))
        graph.add_node("score_alternatives", await node("score_alternatives", self.score_alternatives))
        graph.add_node("summarize", await node("summarize", self.summarize))
        graph.add_node("cleanup", await node("cleanup", self.cleanup))
        graph.set_entry_point("preflight")
        graph.add_edge("preflight", "build_scenarios")
        graph.add_edge("build_scenarios", "setup_runtime")
        graph.add_edge("setup_runtime", "seed_l1")
        graph.add_edge("seed_l1", "run_promotion")
        graph.add_edge("run_promotion", "collect_l2")
        graph.add_edge("collect_l2", "score_alternatives")
        graph.add_edge("score_alternatives", "summarize")
        graph.add_edge("summarize", "cleanup")
        graph.add_edge("cleanup", END)
        compiled = graph.compile()
        self.state = self._coerce_state(await compiled.ainvoke(self.state))
        return self.state

    def _coerce_state(self, value: Any) -> ExperimentState:
        if isinstance(value, ExperimentState):
            return value
        if isinstance(value, dict):
            return ExperimentState(**value)
        raise TypeError(f"Unexpected LangGraph state result: {type(value).__name__}")

    async def _run_node(
        self,
        node_name: str,
        fn: Callable[[ExperimentState], Awaitable[ExperimentState]],
        state: ExperimentState,
    ) -> ExperimentState:
        from src.observability import set_span_attributes, set_span_error, start_span

        started = time.perf_counter()
        with start_span(
            tracer_name="yaam.experiment",
            span_name=f"yaam.experiment.node.{node_name}",
            kind="CHAIN",
            attributes={
                "yaam.experiment.run_id": self.config.run_id,
                "yaam.experiment.node": node_name,
                "tag.tags": ["ciar-challenge", f"run_id:{self.config.run_id}"],
            },
        ) as span:
            try:
                result = await fn(state)
                set_span_attributes(
                    span,
                    {
                        "yaam.experiment.node.elapsed_ms": (time.perf_counter() - started) * 1000,
                    },
                )
                return result
            except Exception as exc:
                set_span_error(span, exc)
                raise

    async def preflight(self, state: ExperimentState) -> ExperimentState:
        phoenix_ui = endpoint_ui_base(self.config.phoenix_endpoint)
        phoenix_check = check_http_reachable(phoenix_ui)
        env_keys = ["OPENROUTER_API_KEY", "REDIS_URL", "POSTGRES_URL"]
        env_presence = safe_env_presence(env_keys)
        missing = [key for key, present in env_presence.items() if not present]
        if missing and not self.config.dry_run:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
        if not phoenix_check["ok"] and not self.config.dry_run:
            raise RuntimeError(f"Phoenix endpoint is not reachable: {phoenix_check}")

        state.manifest.update(
            {
                "run_id": self.config.run_id,
                "started_at": utc_now().isoformat(),
                "dry_run": self.config.dry_run,
                "model": self.config.model,
                "min_ciar": self.config.min_ciar,
                "phoenix_project_name": self.config.phoenix_project_name,
                "phoenix_endpoint": self.config.phoenix_endpoint,
                "phoenix_access_mode": self.config.phoenix_access_mode,
                "phoenix_ui_check": phoenix_check,
                "env_presence": env_presence,
            }
        )

        if not self.config.dry_run and not self.config.skip_provider_health:
            state.manifest["provider_health"] = await self._run_provider_health_check()
            if self.config.require_provider_health:
                if state.manifest["provider_health"].get("status") == "failed":
                    state.manifest["operational_classification"] = classify_operational_run(
                        manifest=state.manifest,
                        promotion_stats=state.promotion_stats,
                        events=state.events,
                        alternative_scores=state.alternative_scores,
                        artifacts=artifact_presence(self.output_dir),
                    )
                    write_json(self.output_dir / "run_manifest.json", state.manifest)
                    raise RuntimeError(
                        f"Provider health check failed: {state.manifest['provider_health']}"
                    )

                redis_probe = await self._run_post_health_redis_probe()
                state.manifest["provider_health"]["post_health_redis_probe"] = redis_probe
                if not redis_probe["ok"]:
                    state.manifest["operational_classification"] = classify_operational_run(
                        manifest=state.manifest,
                        promotion_stats=state.promotion_stats,
                        events=state.events,
                        alternative_scores=state.alternative_scores,
                        artifacts=artifact_presence(self.output_dir),
                    )
                    write_json(self.output_dir / "run_manifest.json", state.manifest)
                    raise RuntimeError(f"Post-health Redis probe failed: {redis_probe}")
        elif self.config.skip_provider_health:
            state.manifest["provider_health"] = {
                "status": "skipped",
                "reason": self.config.provider_health_skip_reason,
                "required": self.config.require_provider_health,
            }

        write_json(self.output_dir / "run_manifest.json", state.manifest)
        return state

    async def _run_provider_health_check(self) -> dict[str, Any]:
        from src.llm.client import LLMClient

        started = time.perf_counter()
        timeout_s = self.config.provider_health_timeout_s
        client: Any | None = None
        cleanup = {"status": "skipped", "errors": []}
        try:
            client = LLMClient.from_env()
            health = await asyncio.wait_for(client.health_check(), timeout=timeout_s)
            result = {
                "status": "checked",
                "required": self.config.require_provider_health,
                "timeout_s": timeout_s,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                "reports": {
                    name: getattr(report, "__dict__", str(report))
                    for name, report in health.items()
                },
            }
        except Exception as exc:
            result = {
                "status": "failed",
                "required": self.config.require_provider_health,
                "timeout_s": timeout_s,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        finally:
            if client is not None:
                try:
                    cleanup = await client.close()
                except Exception as exc:  # pragma: no cover - defensive cleanup fallback
                    cleanup = {
                        "status": "warning",
                        "errors": [
                            {
                                "error_type": type(exc).__name__,
                                "error": sanitize_error_message(str(exc)),
                            }
                        ],
                    }

        result["cleanup"] = cleanup
        return result

    async def _run_post_health_redis_probe(self) -> dict[str, Any]:
        from src.storage.redis_adapter import RedisAdapter

        started = time.perf_counter()
        redis_timeout = float(os.environ.get("MAS_REDIS_TIMEOUT", "15.0"))
        adapter = RedisAdapter(
            {
                "url": os.environ["REDIS_URL"],
                "window_size": 1,
                "socket_timeout": redis_timeout,
            }
        )
        result: dict[str, Any] = {
            "ok": False,
            "redis_timeout_s": redis_timeout,
            "endpoint": sanitized_service_endpoints()["redis"],
        }
        try:
            await adapter.connect()
            result["ok"] = True
        except Exception as exc:
            result.update(
                {
                    "error_type": type(exc).__name__,
                    "error": sanitize_error_message(str(exc)),
                }
            )
        finally:
            try:
                await adapter.disconnect()
            except Exception as exc:
                result["disconnect_warning"] = {
                    "error_type": type(exc).__name__,
                    "error": sanitize_error_message(str(exc)),
                }
            result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
        return result

    async def build_scenarios(self, state: ExperimentState) -> ExperimentState:
        scenarios = build_default_scenarios()
        if self.config.scenario_ids:
            requested = set(self.config.scenario_ids)
            scenarios = [scenario for scenario in scenarios if scenario.scenario_id in requested]
            missing = requested - {scenario.scenario_id for scenario in scenarios}
            if missing:
                raise ValueError(f"Unknown scenario ids: {', '.join(sorted(missing))}")
        state.scenarios = scenarios
        write_json(self.output_dir / "scenarios.json", [asdict(s) for s in state.scenarios])
        return state

    async def setup_runtime(self, state: ExperimentState) -> ExperimentState:
        if self.config.dry_run:
            return state

        redis_timeout = float(os.environ.get("MAS_REDIS_TIMEOUT", "15.0"))
        state.manifest["runtime_setup"] = {
            "status": "in_progress",
            "redis_timeout_s": redis_timeout,
            "service_endpoints": sanitized_service_endpoints(),
            "phases": [],
        }
        write_json(
            self.output_dir / "run_manifest.json",
            {k: v for k, v in state.manifest.items() if not k.startswith("_")},
        )

        setup_started = time.perf_counter()
        current_phase = "setup_started"

        def record_phase(name: str, status: str = "ok") -> None:
            state.manifest["runtime_setup"]["phases"].append(
                {
                    "name": name,
                    "status": status,
                    "elapsed_ms": round((time.perf_counter() - setup_started) * 1000, 3),
                }
            )

        try:
            from src.llm.client import LLMClient, ensure_phoenix_instrumentation
            from src.memory.ciar_scorer import CIARScorer
            from src.memory.engines.fact_extractor import FactExtractor
            from src.memory.engines.promotion_engine import PromotionEngine
            from src.memory.engines.topic_segmenter import TopicSegmenter
            from src.memory.tiers import ActiveContextTier, WorkingMemoryTier
            from src.storage.postgres_adapter import PostgresAdapter
            from src.storage.redis_adapter import RedisAdapter

            current_phase = "phoenix_instrumentation"
            ensure_phoenix_instrumentation()
            record_phase("phoenix_instrumentation")

            current_phase = "redis_adapter_created"
            redis_adapter = RedisAdapter(
                {
                    "url": os.environ["REDIS_URL"],
                    "window_size": 20,
                    "socket_timeout": redis_timeout,
                }
            )
            record_phase("redis_adapter_created")

            current_phase = "postgres_adapters_created"
            postgres_l1 = PostgresAdapter(
                {"url": os.environ["POSTGRES_URL"], "table": "active_context"}
            )
            postgres_l2 = PostgresAdapter(
                {"url": os.environ["POSTGRES_URL"], "table": "working_memory"}
            )
            record_phase("postgres_adapters_created")

            current_phase = "tiers_created"
            l1_tier = ActiveContextTier(
                redis_adapter=redis_adapter,
                postgres_adapter=postgres_l1,
                config={"window_size": 20, "ttl_hours": 24},
                telemetry_stream=self.telemetry,
            )
            l2_tier = WorkingMemoryTier(
                postgres_adapter=postgres_l2,
                config={"ciar_threshold": self.config.min_ciar},
                telemetry_stream=self.telemetry,
            )
            record_phase("tiers_created")
            write_json(
                self.output_dir / "run_manifest.json",
                {k: v for k, v in state.manifest.items() if not k.startswith("_")},
            )

            current_phase = "l1_initialize_started"
            record_phase("l1_initialize_started", "started")
            await l1_tier.initialize()
            current_phase = "l1_initialize_ok"
            record_phase("l1_initialize_ok")

            current_phase = "l2_initialize_started"
            record_phase("l2_initialize_started", "started")
            await l2_tier.initialize()
            current_phase = "l2_initialize_ok"
            record_phase("l2_initialize_ok")

            current_phase = "llm_client_created"
            llm_client = LLMClient.from_env()
            record_phase("llm_client_created")

            scorer = ObservedCIARScorer(CIARScorer(), self.output_dir, state)
            state.resources = ExperimentResources(
                l1_tier=l1_tier,
                l2_tier=l2_tier,
                redis_adapter=redis_adapter,
                postgres_l1=postgres_l1,
                postgres_l2=postgres_l2,
            )
            state.manifest["runtime"] = {
                "mode": "live_l1_l2",
                "provider_order": llm_client.available_providers(),
                "promotion_policy_mode": self.config.promotion_policy_mode,
                "contradiction_policy_mode": self.config.contradiction_policy_mode,
            }
            state.manifest["_promotion_engine"] = PromotionEngine(
                l1_tier=l1_tier,
                l2_tier=l2_tier,
                topic_segmenter=ObservedTopicSegmenter(
                    TopicSegmenter(llm_client=llm_client, min_turns=10, max_turns=20),
                    state,
                ),
                fact_extractor=ObservedFactExtractor(FactExtractor(llm_client=llm_client)),
                ciar_scorer=scorer,
                config={
                    "promotion_threshold": self.config.min_ciar,
                    "batch_min_turns": 10,
                    "enable_final_fallback": False,
                    "enable_segment_fallback": False,
                    "promotion_policy_mode": self.config.promotion_policy_mode,
                    "contradiction_policy_mode": self.config.contradiction_policy_mode,
                },
                telemetry_stream=self.telemetry,
            )
            state.manifest["runtime_setup"]["status"] = "ok"
            write_json(
                self.output_dir / "run_manifest.json",
                {k: v for k, v in state.manifest.items() if not k.startswith("_")},
            )
            return state
        except Exception as exc:
            error = {
                "run_id": self.config.run_id,
                "failed_at": utc_now().isoformat(),
                "failure_phase": current_phase,
                "error_type": type(exc).__name__,
                "error": sanitize_error_message(str(exc)),
            }
            state.manifest["runtime_setup"]["status"] = "failed"
            state.manifest["runtime_setup"]["failure_phase"] = current_phase
            state.manifest["runtime_setup"]["error_type"] = error["error_type"]
            state.manifest["runtime_setup"]["error"] = error["error"]
            state.manifest["operational_classification"] = classify_operational_run(
                manifest=state.manifest,
                promotion_stats=state.promotion_stats,
                events=state.events,
                alternative_scores=state.alternative_scores,
                artifacts=artifact_presence(self.output_dir),
            )
            write_json(self.output_dir / "run_error.json", error)
            write_json(
                self.output_dir / "run_manifest.json",
                {k: v for k, v in state.manifest.items() if not k.startswith("_")},
            )
            raise

    async def seed_l1(self, state: ExperimentState) -> ExperimentState:
        for scenario in state.scenarios:
            session_id = f"{self.config.run_id}__{scenario.scenario_id}"
            state.session_by_scenario[scenario.scenario_id] = session_id
            if self.config.dry_run:
                continue
            from src.memory.models import TurnData

            for idx, turn in enumerate(scenario.turns):
                await state.resources.l1_tier.store(
                    TurnData(
                        session_id=session_id,
                        turn_id=str(idx),
                        role=turn["role"],
                        content=turn["content"],
                        timestamp=utc_now(),
                        metadata={
                            "experiment_run_id": self.config.run_id,
                            "scenario_id": scenario.scenario_id,
                        },
                    )
                )
        return state

    async def run_promotion(self, state: ExperimentState) -> ExperimentState:
        if self.config.dry_run:
            await self._setup_dry_run_runtime(state)

        engine = state.manifest["_promotion_engine"]
        for idx, scenario in enumerate(state.scenarios):
            session_id = state.session_by_scenario[scenario.scenario_id]
            stats = await engine.process_session(session_id)
            state.promotion_stats[scenario.scenario_id] = stats
            if self.config.scenario_delay_s > 0 and idx < len(state.scenarios) - 1:
                await asyncio.sleep(self.config.scenario_delay_s)
        write_json(self.output_dir / "promotion_results.json", state.promotion_stats)
        return state

    async def _setup_dry_run_runtime(self, state: ExperimentState) -> None:
        from unittest.mock import AsyncMock

        from src.memory.ciar_scorer import CIARScorer
        from src.memory.engines.promotion_engine import PromotionEngine

        class MemoryL1:
            def __init__(self, turns_by_session: dict[str, list[dict[str, Any]]]) -> None:
                self.turns_by_session = turns_by_session

            async def retrieve(self, session_id: str) -> list[dict[str, Any]]:
                return list(reversed(self.turns_by_session[session_id]))

            async def health_check(self) -> dict[str, str]:
                return {"status": "healthy"}

        class MemoryL2:
            ciar_threshold = self.config.min_ciar

            def __init__(self) -> None:
                self.facts_by_session: dict[str, list[Any]] = {}
                self.store = AsyncMock(side_effect=self._store)

            async def _store(self, fact: Any) -> str:
                self.facts_by_session.setdefault(fact.session_id, []).append(fact)
                return fact.fact_id

            async def query(self, filters: dict[str, Any] | None = None, **_: Any) -> list[Any]:
                session_id = (filters or {}).get("session_id")
                return list(self.facts_by_session.get(session_id, []))

            async def health_check(self) -> dict[str, str]:
                return {"status": "healthy"}

        turns_by_session = {
            state.session_by_scenario[scenario.scenario_id]: scenario.turns
            for scenario in state.scenarios
        }
        scenario_by_session = {
            state.session_by_scenario[scenario.scenario_id]: scenario
            for scenario in state.scenarios
        }
        l1 = MemoryL1(turns_by_session)
        l2 = MemoryL2()
        state.resources.l1_tier = l1
        state.resources.l2_tier = l2
        scorer = ObservedCIARScorer(CIARScorer(), self.output_dir, state)
        state.manifest["runtime"] = {
            "mode": "dry_l1_l2",
            "provider_order": [],
            "promotion_policy_mode": self.config.promotion_policy_mode,
            "contradiction_policy_mode": self.config.contradiction_policy_mode,
        }
        state.manifest["_promotion_engine"] = PromotionEngine(
            l1_tier=l1,
            l2_tier=l2,
            topic_segmenter=CannedTopicSegmenter(scenario_by_session),
            fact_extractor=CannedFactExtractor(),
            ciar_scorer=scorer,
            config={
                "promotion_threshold": self.config.min_ciar,
                "batch_min_turns": 10,
                "enable_final_fallback": False,
                "enable_segment_fallback": False,
                "promotion_policy_mode": self.config.promotion_policy_mode,
                "contradiction_policy_mode": self.config.contradiction_policy_mode,
            },
            telemetry_stream=self.telemetry,
        )

    async def collect_l2(self, state: ExperimentState) -> ExperimentState:
        for scenario in state.scenarios:
            session_id = state.session_by_scenario[scenario.scenario_id]
            if self.config.dry_run:
                facts = await state.resources.l2_tier.query(filters={"session_id": session_id})
            else:
                facts = await state.resources.l2_tier.query(
                    filters={"session_id": session_id, "min_ciar_score": 0.0},
                    limit=100,
                    include_low_ciar=True,
                )
            state.l2_facts[scenario.scenario_id] = [fact.model_dump(mode="json") for fact in facts]
        write_json(self.output_dir / "promotion_results.json", state.promotion_stats)
        write_json(self.output_dir / "l2_facts.json", state.l2_facts)
        return state

    async def score_alternatives(self, state: ExperimentState) -> ExperimentState:
        segment_score_by_session = {
            event["session_id"]: event["data"].get("ciar_score")
            for event in state.events
            if event["event_type"] == "significance_scored"
        }
        raw_by_fact_id = {
            str(call.get("fact_id")): call for call in state.ciar_calls if call.get("fact_id")
        }
        raw_by_session_content: dict[tuple[str, str], list[dict[str, Any]]] = {}
        raw_by_content: dict[str, list[dict[str, Any]]] = {}
        for call in state.ciar_calls:
            content_key = normalize_fact_content(call.get("content"))
            if not content_key:
                continue
            raw_by_content.setdefault(content_key, []).append(call)
            call_session_id = call.get("session_id")
            if call_session_id:
                raw_by_session_content.setdefault((str(call_session_id), content_key), []).append(
                    call
                )
        provenance_by_fact_id: dict[str, dict[str, Any]] = {}
        provenance_by_session_content: dict[tuple[str, str], dict[str, Any]] = {}
        for event in state.events:
            if event.get("event_type") not in {"fact_promoted", "fact_review_only"}:
                continue
            event_data = event.get("data") or {}
            provenance = event_data.get("ciar_provenance") or {}
            if not provenance:
                continue
            event_fact_id = event_data.get("fact_id")
            if event_fact_id is not None:
                provenance_by_fact_id[str(event_fact_id)] = provenance
            event_content_key = normalize_fact_content(event_data.get("content"))
            event_session_id = event.get("session_id")
            if event_content_key and event_session_id:
                provenance_by_session_content[(str(event_session_id), event_content_key)] = (
                    provenance
                )
        rows = []
        for scenario in state.scenarios:
            session_id = state.session_by_scenario[scenario.scenario_id]
            for fact in state.l2_facts.get(scenario.scenario_id, []):
                fact_id = str(fact.get("fact_id"))
                raw_call = self._match_raw_ciar_call(
                    fact=fact,
                    session_id=session_id,
                    raw_by_fact_id=raw_by_fact_id,
                    raw_by_session_content=raw_by_session_content,
                    raw_by_content=raw_by_content,
                )
                raw_score = raw_call.get("score")
                provenance = (fact.get("metadata") or {}).get("ciar_provenance", {})
                contradiction_policy = (fact.get("metadata") or {}).get(
                    "contradiction_policy", {}
                )
                if not provenance:
                    provenance = provenance_by_fact_id.get(fact_id, {})
                if not provenance:
                    provenance = provenance_by_session_content.get(
                        (session_id, normalize_fact_content(fact.get("content"))),
                        {},
                    )
                raw_score = provenance.get("raw_fact_ciar", raw_score)
                stored_score = fact.get("ciar_score")
                stored_ciar = provenance.get("stored_ciar", stored_score)
                floor_applied = (
                    isinstance(raw_score, int | float)
                    and isinstance(stored_score, int | float)
                    and raw_score < self.config.min_ciar
                    and stored_score >= self.config.min_ciar
                )
                certainty = float(fact.get("certainty") or 0.0)
                impact = float(fact.get("impact") or 0.0)
                contradiction = scenario.expectation == "should_conflict"
                utility_candidate = min(
                    1.0,
                    (0.45 * float(raw_score or stored_score or 0.0))
                    + (0.20 * certainty)
                    + (0.20 * impact)
                    + (0.10 if "llm" in str(fact.get("source_type", "")) else 0.0)
                    - (0.15 if contradiction else 0.0),
                )
                row = {
                    "scenario_id": scenario.scenario_id,
                    "session_id": session_id,
                    "fact_id": fact_id,
                    "content": fact.get("content"),
                    "expectation": scenario.expectation,
                    "promotion_policy_mode": provenance.get(
                        "promotion_policy_mode", self.config.promotion_policy_mode
                    ),
                    "contradiction_policy_mode": contradiction_policy.get(
                        "mode", self.config.contradiction_policy_mode
                    ),
                    "contradiction_policy": contradiction_policy,
                    "segment_ciar": provenance.get("segment_ciar")
                    or segment_score_by_session.get(session_id),
                    "raw_fact_ciar": raw_score,
                    "pre_inheritance_ciar": provenance.get("pre_inheritance_ciar"),
                    "post_inheritance_ciar": provenance.get("post_inheritance_ciar"),
                    "stored_ciar": stored_ciar,
                    "ciar_score_source": provenance.get("ciar_score_source"),
                    "lifetime_decision_class": provenance.get("lifetime_decision_class"),
                    "lifetime_decision_reason": provenance.get("lifetime_decision_reason"),
                    "current_runtime_ciar": stored_score,
                    "fact_gate_decision": bool(
                        provenance.get("fact_gate_decision")
                        if "fact_gate_decision" in provenance
                        else isinstance(raw_score, int | float) and raw_score >= self.config.min_ciar
                    ),
                    "floor_applied": floor_applied,
                    "suppressed": False,
                    "utility_candidate_v0": round(utility_candidate, 4),
                    "evidence_quality_flags": {
                        "llm_extracted": "llm" in str(fact.get("source_type", "")),
                        "rule_fallback": fact.get("source_type") == "rule_fallback",
                        "segment_inherited": bool(
                            provenance.get(
                                "segment_inherited",
                                raw_call.get("components", {}).get("certainty")
                                == fact.get("certainty"),
                            )
                        ),
                        "contradiction_candidate": contradiction,
                        **provenance.get("evidence_quality_flags", {}),
                    },
                }
                rows.append(row)

        for event in state.events:
            if event.get("event_type") not in {"fact_review_only", "fact_suppressed"}:
                continue
            data = event.get("data") or {}
            provenance = data.get("ciar_provenance") or {}
            contradiction_policy = data.get("contradiction_policy") or {}
            scenario_id = self._scenario_id_for_session(state, str(event.get("session_id", "")))
            scenario = next((s for s in state.scenarios if s.scenario_id == scenario_id), None)
            suppressed = event.get("event_type") == "fact_suppressed"
            rows.append(
                {
                    "scenario_id": scenario_id,
                    "session_id": event.get("session_id"),
                    "fact_id": data.get("fact_id"),
                    "content": data.get("content"),
                    "expectation": scenario.expectation if scenario else None,
                    "promotion_policy_mode": provenance.get(
                        "promotion_policy_mode", self.config.promotion_policy_mode
                    ),
                    "contradiction_policy_mode": contradiction_policy.get(
                        "mode", self.config.contradiction_policy_mode
                    ),
                    "contradiction_policy": contradiction_policy,
                    "segment_ciar": provenance.get("segment_ciar"),
                    "raw_fact_ciar": provenance.get("raw_fact_ciar"),
                    "pre_inheritance_ciar": provenance.get("pre_inheritance_ciar"),
                    "post_inheritance_ciar": provenance.get("post_inheritance_ciar"),
                    "stored_ciar": None,
                    "ciar_score_source": provenance.get("ciar_score_source"),
                    "lifetime_decision_class": provenance.get("lifetime_decision_class")
                    or data.get("lifetime_decision_class"),
                    "lifetime_decision_reason": provenance.get("lifetime_decision_reason")
                    or data.get("lifetime_decision_reason"),
                    "current_runtime_ciar": None,
                    "fact_gate_decision": bool(provenance.get("fact_gate_decision")),
                    "floor_applied": False,
                    "review_only": not suppressed,
                    "suppressed": suppressed,
                    "utility_candidate_v0": None,
                    "evidence_quality_flags": provenance.get("evidence_quality_flags", {}),
                }
            )

        state.alternative_scores = rows
        write_json(self.output_dir / "alternative_scores.json", rows)
        write_json(self.output_dir / "formula_probes.json", build_formula_probe_rows())
        return state

    def _match_raw_ciar_call(
        self,
        fact: dict[str, Any],
        session_id: str,
        raw_by_fact_id: dict[str, dict[str, Any]],
        raw_by_session_content: dict[tuple[str, str], list[dict[str, Any]]],
        raw_by_content: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        """Match a stored L2 fact to its pre-store CIAR scorer call.

        Live PostgreSQL rows can expose the database row id as `fact_id`, while
        the scorer observes the original extracted fact id before storage. Use
        fact id first, then a session-scoped content match when ids diverge.
        """
        fact_id = fact.get("fact_id")
        if fact_id is not None:
            raw_call = raw_by_fact_id.get(str(fact_id))
            if raw_call:
                return raw_call

        content_key = normalize_fact_content(fact.get("content"))
        if not content_key:
            return {}

        session_candidates = raw_by_session_content.get((session_id, content_key), [])
        if len(session_candidates) == 1:
            return session_candidates[0]

        content_candidates = raw_by_content.get(content_key, [])
        if len(content_candidates) == 1:
            return content_candidates[0]

        return {}

    def _scenario_id_for_session(self, state: ExperimentState, session_id: str) -> str | None:
        for scenario_id, mapped_session_id in state.session_by_scenario.items():
            if mapped_session_id == session_id:
                return scenario_id
        return None

    async def summarize(self, state: ExperimentState) -> ExperimentState:
        state.manifest["completed_at"] = utc_now().isoformat()
        state.manifest["operational_classification"] = classify_operational_run(
            manifest=state.manifest,
            promotion_stats=state.promotion_stats,
            events=state.events,
            alternative_scores=state.alternative_scores,
            artifacts=artifact_presence(self.output_dir, assume_summary_present=True),
        )
        classification = state.manifest["operational_classification"]
        lines = [
            "# CIAR Challenge Summary",
            "",
            f"- run_id: `{self.config.run_id}`",
            f"- dry_run: `{self.config.dry_run}`",
            f"- model: `{self.config.model}`",
            f"- phoenix_project: `{self.config.phoenix_project_name}`",
            f"- phoenix_access_mode: `{self.config.phoenix_access_mode}`",
            "",
            "## Operational Classification",
            "",
            f"- run_quality: `{classification['run_quality']}`",
            f"- policy_evidence: `{classification['policy_evidence']}`",
            "- reasons:",
            *[f"  - {reason}" for reason in classification["reasons"]],
            "",
            "## Scenario Outcomes",
            "",
            "| Scenario | Expected | Segments Promoted | Facts Promoted | Facts Suppressed | Floor Flags |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        floors_by_scenario: dict[str, int] = {}
        for row in state.alternative_scores:
            if row["floor_applied"]:
                floors_by_scenario[row["scenario_id"]] = floors_by_scenario.get(
                    row["scenario_id"], 0
                ) + 1
        for scenario in state.scenarios:
            stats = state.promotion_stats.get(scenario.scenario_id, {})
            lines.append(
                "| {scenario} | {expectation} | {segments} | {facts} | {suppressed} | {floors} |".format(
                    scenario=scenario.scenario_id,
                    expectation=scenario.expectation,
                    segments=stats.get("segments_promoted", 0),
                    facts=stats.get("facts_promoted", 0),
                    suppressed=stats.get("facts_suppressed", 0),
                    floors=floors_by_scenario.get(scenario.scenario_id, 0),
                )
            )
        lines.extend(
            [
                "",
                "## Review Prompts",
                "",
                "- Inspect facts where `floor_applied=true`; these expose segment gate behavior.",
                "- Inspect contradiction scenarios; current CIAR has no truth-resolution layer.",
                "- Compare `raw_fact_ciar` with `utility_candidate_v0` before changing runtime policy.",
            ]
        )
        (self.output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        write_json(
            self.output_dir / "run_manifest.json",
            {k: v for k, v in state.manifest.items() if not k.startswith("_")},
        )
        return state

    async def cleanup(self, state: ExperimentState) -> ExperimentState:
        if self.config.keep_data:
            state.manifest["cleanup"] = "skipped_keep_data"
            state.manifest["operational_classification"] = classify_operational_run(
                manifest=state.manifest,
                promotion_stats=state.promotion_stats,
                events=state.events,
                alternative_scores=state.alternative_scores,
                artifacts=artifact_presence(self.output_dir),
            )
            write_json(
                self.output_dir / "run_manifest.json",
                {k: v for k, v in state.manifest.items() if not k.startswith("_")},
            )
            return state
        if self.config.dry_run:
            state.manifest["cleanup"] = "dry_run_noop"
            state.manifest["operational_classification"] = classify_operational_run(
                manifest=state.manifest,
                promotion_stats=state.promotion_stats,
                events=state.events,
                alternative_scores=state.alternative_scores,
                artifacts=artifact_presence(self.output_dir),
            )
            write_json(
                self.output_dir / "run_manifest.json",
                {k: v for k, v in state.manifest.items() if not k.startswith("_")},
            )
            return state

        cleanup_results: dict[str, Any] = {}
        for session_id in state.session_by_scenario.values():
            result: dict[str, Any] = {"l1_deleted": False, "l2_deleted": False}
            try:
                redis_key = f"l1:session:{session_id}"
                redis_deleted = await state.resources.redis_adapter.delete(redis_key)
                postgres_deleted = await state.resources.postgres_l1.delete_by_filters(
                    "active_context", {"session_id": session_id}
                )
                result["l1_deleted"] = bool(redis_deleted or postgres_deleted)
            except Exception as exc:
                result["l1_error"] = str(exc)
            try:
                result["l2_deleted"] = await state.resources.postgres_l2.delete_by_filters(
                    "working_memory", {"session_id": session_id}
                )
            except Exception as exc:
                result["l2_error"] = str(exc)
            cleanup_results[session_id] = result
        state.manifest["cleanup"] = cleanup_results
        state.manifest["operational_classification"] = classify_operational_run(
            manifest=state.manifest,
            promotion_stats=state.promotion_stats,
            events=state.events,
            alternative_scores=state.alternative_scores,
            artifacts=artifact_presence(self.output_dir),
        )
        write_json(
            self.output_dir / "run_manifest.json",
            {k: v for k, v in state.manifest.items() if not k.startswith("_")},
        )
        await self._close_resources(state)
        return state

    async def _close_resources(self, state: ExperimentState) -> None:
        for tier in [state.resources.l1_tier, state.resources.l2_tier]:
            if tier and hasattr(tier, "cleanup"):
                await tier.cleanup()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CIAR challenge experiment.")
    parser.add_argument("--run-id", default=f"ciar-exp-{utc_stamp()}")
    parser.add_argument("--output-dir", default="logs/ciar_challenge")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-data", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--min-ciar", type=float, default=DEFAULT_MIN_CIAR)
    parser.add_argument("--phoenix-endpoint")
    parser.add_argument(
        "--phoenix-access-mode",
        choices=["auto", "direct_ip", "ssh_tunnel"],
        default="auto",
    )
    parser.add_argument("--phoenix-project-name")
    parser.add_argument(
        "--scenario-id",
        action="append",
        default=[],
        help="Scenario id to run. Repeat to run multiple scenarios. Defaults to all scenarios.",
    )
    parser.add_argument("--allow-localhost-phoenix", action="store_true")
    parser.add_argument("--skip-provider-health", action="store_true")
    parser.add_argument(
        "--provider-health-skip-reason",
        default=os.environ.get("MAS_PROVIDER_HEALTH_SKIP_REASON", "operator requested skip"),
    )
    parser.add_argument(
        "--provider-health-timeout",
        type=float,
        default=float(os.environ.get("MAS_PROVIDER_HEALTH_TIMEOUT", "60.0")),
    )
    parser.add_argument(
        "--require-provider-health",
        action="store_true",
        help="Fail live preflight when provider health check fails or times out.",
    )
    parser.add_argument(
        "--promotion-policy-mode",
        choices=("segment_gate", "fact_gate", "hybrid_gate"),
        default=os.environ.get("MAS_PROMOTION_POLICY_MODE", "hybrid_gate"),
        help="Promotion policy mode used by the L1->L2 promotion engine.",
    )
    parser.add_argument(
        "--contradiction-policy-mode",
        choices=("off", "metadata_only", "suppress_superseded"),
        default=os.environ.get("MAS_CONTRADICTION_POLICY_MODE", "off"),
        help="Contradiction/supersession policy applied above CIAR.",
    )
    parser.add_argument(
        "--scenario-delay-s",
        type=float,
        default=float(os.environ.get("MAS_CIAR_SCENARIO_DELAY_S", "0.0")),
        help="Seconds to wait between scenario promotion runs for live provider pacing.",
    )
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    if args.skip_provider_health and args.require_provider_health:
        raise ValueError("--skip-provider-health cannot be combined with --require-provider-health")
    endpoint, access_mode = resolve_phoenix_endpoint(
        explicit_endpoint=args.phoenix_endpoint,
        access_mode=args.phoenix_access_mode,
        allow_localhost_6006=args.allow_localhost_phoenix,
    )
    project_name = args.phoenix_project_name or f"ciar-challenge-{utc_stamp()}"
    config = ExperimentConfig(
        run_id=args.run_id,
        output_dir=Path(args.output_dir),
        dry_run=bool(args.dry_run),
        keep_data=bool(args.keep_data),
        model=args.model,
        min_ciar=float(args.min_ciar),
        phoenix_endpoint=endpoint,
        phoenix_project_name=project_name,
        phoenix_access_mode=access_mode,
        scenario_ids=list(args.scenario_id),
        skip_provider_health=bool(args.skip_provider_health),
        provider_health_skip_reason=args.provider_health_skip_reason,
        provider_health_timeout_s=float(args.provider_health_timeout),
        require_provider_health=bool(args.require_provider_health),
        promotion_policy_mode=args.promotion_policy_mode,
        contradiction_policy_mode=args.contradiction_policy_mode,
        scenario_delay_s=float(args.scenario_delay_s),
    )
    experiment = CIARChallengeExperiment(config)
    state = await experiment.run()
    print(f"CIAR challenge artifacts: {experiment.output_dir}")
    print(f"Phoenix project: {state.manifest.get('phoenix_project_name')}")
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
