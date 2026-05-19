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
DEFAULT_PHOENIX_DIRECT_ENDPOINT = "http://192.168.107.187:6006/v1/traces"
DEFAULT_TUNNEL_ENDPOINT = "http://127.0.0.1:16006/v1/traces"
DEFAULT_MIN_CIAR = 0.6
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
    skz-data-lv directly or via an explicit SSH tunnel.
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
            "For MacBook development use http://192.168.107.187:6006/v1/traces, "
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
    skip_provider_health: bool = False


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
        if isinstance(fact, dict):
            fact_id = fact.get("fact_id", fact_id)
            content = fact.get("content", content)

        from src.observability import set_span_attributes, start_span

        with start_span(
            tracer_name="yaam.experiment",
            span_name="yaam.ciar.score",
            kind="TOOL",
            attributes={
                "yaam.ciar.threshold": self.threshold,
                "yaam.fact_id": fact_id,
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
        if scenario.scenario_id == "speculative_claim":
            certainty, impact = 0.45, 0.55
        elif scenario.scenario_id == "contradiction_update":
            certainty, impact = 0.9, 0.8
        elif scenario.scenario_id == "assistant_inferred":
            certainty, impact = 0.55, 0.65
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
        ) -> Any:
            return Fact(
                fact_id=f"{segment_id}-{suffix}",
                session_id=session_id,
                content=content,
                fact_type=fact_type,
                fact_category=FactCategory.OPERATIONAL,
                certainty=certainty,
                impact=impact,
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
            from src.llm.client import LLMClient

            health = await LLMClient.from_env().health_check()
            state.manifest["provider_health"] = {
                name: getattr(report, "__dict__", str(report)) for name, report in health.items()
            }

        write_json(self.output_dir / "run_manifest.json", state.manifest)
        return state

    async def build_scenarios(self, state: ExperimentState) -> ExperimentState:
        state.scenarios = build_default_scenarios()
        write_json(self.output_dir / "scenarios.json", [asdict(s) for s in state.scenarios])
        return state

    async def setup_runtime(self, state: ExperimentState) -> ExperimentState:
        if self.config.dry_run:
            return state

        from src.llm.client import LLMClient, ensure_phoenix_instrumentation
        from src.memory.ciar_scorer import CIARScorer
        from src.memory.engines.fact_extractor import FactExtractor
        from src.memory.engines.promotion_engine import PromotionEngine
        from src.memory.engines.topic_segmenter import TopicSegmenter
        from src.memory.tiers import ActiveContextTier, WorkingMemoryTier
        from src.storage.postgres_adapter import PostgresAdapter
        from src.storage.redis_adapter import RedisAdapter

        ensure_phoenix_instrumentation()
        redis_adapter = RedisAdapter({"url": os.environ["REDIS_URL"], "window_size": 20})
        postgres_l1 = PostgresAdapter({"url": os.environ["POSTGRES_URL"], "table": "active_context"})
        postgres_l2 = PostgresAdapter({"url": os.environ["POSTGRES_URL"], "table": "working_memory"})
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
        await l1_tier.initialize()
        await l2_tier.initialize()

        llm_client = LLMClient.from_env()
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
            config={"promotion_threshold": self.config.min_ciar, "batch_min_turns": 10},
            telemetry_stream=self.telemetry,
        )
        write_json(
            self.output_dir / "run_manifest.json",
            {k: v for k, v in state.manifest.items() if not k.startswith("_")},
        )
        return state

    async def seed_l1(self, state: ExperimentState) -> ExperimentState:
        for scenario in state.scenarios:
            session_id = f"{self.config.run_id}:{scenario.scenario_id}"
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
        for scenario in state.scenarios:
            session_id = state.session_by_scenario[scenario.scenario_id]
            stats = await engine.process_session(session_id)
            state.promotion_stats[scenario.scenario_id] = stats
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
        rows = []
        for scenario in state.scenarios:
            session_id = state.session_by_scenario[scenario.scenario_id]
            for fact in state.l2_facts.get(scenario.scenario_id, []):
                fact_id = str(fact.get("fact_id"))
                raw_call = raw_by_fact_id.get(fact_id, {})
                raw_score = raw_call.get("score")
                stored_score = fact.get("ciar_score")
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
                    "segment_ciar": segment_score_by_session.get(session_id),
                    "raw_fact_ciar": raw_score,
                    "current_runtime_ciar": stored_score,
                    "fact_gate_decision": bool(
                        isinstance(raw_score, int | float) and raw_score >= self.config.min_ciar
                    ),
                    "floor_applied": floor_applied,
                    "utility_candidate_v0": round(utility_candidate, 4),
                    "evidence_quality_flags": {
                        "llm_extracted": "llm" in str(fact.get("source_type", "")),
                        "rule_fallback": fact.get("source_type") == "rule_fallback",
                        "segment_inherited": raw_call.get("components", {}).get("certainty")
                        == fact.get("certainty"),
                        "contradiction_candidate": contradiction,
                    },
                }
                rows.append(row)

        state.alternative_scores = rows
        write_json(self.output_dir / "alternative_scores.json", rows)
        write_json(self.output_dir / "formula_probes.json", build_formula_probe_rows())
        return state

    async def summarize(self, state: ExperimentState) -> ExperimentState:
        lines = [
            "# CIAR Challenge Summary",
            "",
            f"- run_id: `{self.config.run_id}`",
            f"- dry_run: `{self.config.dry_run}`",
            f"- model: `{self.config.model}`",
            f"- phoenix_project: `{self.config.phoenix_project_name}`",
            f"- phoenix_access_mode: `{self.config.phoenix_access_mode}`",
            "",
            "## Scenario Outcomes",
            "",
            "| Scenario | Expected | Segments Promoted | Facts Promoted | Floor Flags |",
            "|---|---:|---:|---:|---:|",
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
                "| {scenario} | {expectation} | {segments} | {facts} | {floors} |".format(
                    scenario=scenario.scenario_id,
                    expectation=scenario.expectation,
                    segments=stats.get("segments_promoted", 0),
                    facts=stats.get("facts_promoted", 0),
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
        state.manifest["completed_at"] = utc_now().isoformat()
        write_json(
            self.output_dir / "run_manifest.json",
            {k: v for k, v in state.manifest.items() if not k.startswith("_")},
        )
        return state

    async def cleanup(self, state: ExperimentState) -> ExperimentState:
        if self.config.keep_data:
            state.manifest["cleanup"] = "skipped_keep_data"
            return state
        if self.config.dry_run:
            state.manifest["cleanup"] = "dry_run_noop"
            return state

        cleanup_results: dict[str, Any] = {}
        for session_id in state.session_by_scenario.values():
            result: dict[str, Any] = {"l1_deleted": False, "l2_deleted": False}
            try:
                result["l1_deleted"] = await state.resources.l1_tier.delete(session_id)
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
    parser.add_argument("--allow-localhost-phoenix", action="store_true")
    parser.add_argument("--skip-provider-health", action="store_true")
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
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
        skip_provider_health=bool(args.skip_provider_health),
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
