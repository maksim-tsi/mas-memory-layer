"""FastAPI wrapper for MAS agents used in GoodAI LTM Benchmark runs."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import time
from collections.abc import Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import redis
import uvicorn
from fastapi import FastAPI, HTTPException, Query

from src.agents.base_agent import BaseAgent
from src.agents.full_context_agent import FullContextAgent
from src.agents.memory_agent import MemoryAgent
from src.agents.models import RunTurnRequest, RunTurnResponse
from src.agents.rag_agent import RAGAgent
from src.llm.client import LLMClient
from src.memory.ciar_scorer import CIARScorer
from src.memory.engines.fact_extractor import FactExtractor
from src.memory.engines.promotion_engine import PromotionEngine
from src.memory.engines.topic_segmenter import TopicSegmenter
from src.memory.models import TurnData
from src.memory.tiers import ActiveContextTier, WorkingMemoryTier
from src.memory.unified_memory_system import UnifiedMemorySystem
from src.storage.postgres_adapter import PostgresAdapter
from src.storage.redis_adapter import RedisAdapter

logger = logging.getLogger(__name__)


class RateLimiter:
    """Per-agent rate limiter with JSONL logging and circuit breaker."""

    def __init__(
        self,
        rpm: int = 100,
        tpm: int = 1_000_000,
        min_delay: float = 0.6,
        log_file: str | None = None,
    ) -> None:
        self.rpm = rpm
        self.tpm = tpm
        self.min_delay = min_delay
        self.request_times: list[datetime] = []
        self.token_usage: list[tuple[datetime, int]] = []
        self.consecutive_429s = 0
        self.log_file = log_file

    async def wait_if_needed(self, estimated_tokens: int) -> None:
        """Enforce RPM/TPM limits with sliding window, delay, and circuit breaker."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=60)
        self.request_times = [t for t in self.request_times if t >= cutoff]
        self.token_usage = [(t, tokens) for t, tokens in self.token_usage if t >= cutoff]

        await asyncio.sleep(self.min_delay)

        if len(self.request_times) >= self.rpm:
            wait_seconds = (self.request_times[0] - cutoff).total_seconds()
            await asyncio.sleep(max(0.0, wait_seconds))

        current_tpm = sum(tokens for _, tokens in self.token_usage)
        if current_tpm + estimated_tokens >= self.tpm:
            await asyncio.sleep(60)

        if self.consecutive_429s >= 3:
            logger.warning("Rate limiter circuit breaker triggered; pausing for 60s")
            await asyncio.sleep(60)
            self.consecutive_429s = 0

    def record_usage(self, estimated_tokens: int) -> None:
        """Record token usage and emit JSONL log entry."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=60)
        self.request_times = [t for t in self.request_times if t >= cutoff]
        self.token_usage = [(t, tokens) for t, tokens in self.token_usage if t >= cutoff]

        self.request_times.append(now)
        self.token_usage.append((now, estimated_tokens))

        current_rpm = len(self.request_times)
        current_tpm = sum(tokens for _, tokens in self.token_usage)
        self._log_state(now, estimated_tokens, current_rpm, current_tpm)

    def register_error(self, exc: Exception) -> None:
        """Track rate limit errors for circuit breaker logic."""
        message = str(exc)
        if "429" in message or "rate" in message.lower():
            self.consecutive_429s += 1

    def _log_state(
        self, timestamp: datetime, estimated_tokens: int, current_rpm: int, current_tpm: int
    ) -> None:
        if not self.log_file:
            return
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "estimated_tokens": estimated_tokens,
            "current_rpm": current_rpm,
            "current_tpm": current_tpm,
            "delay_applied": self.min_delay,
            "circuit_breaker_active": self.consecutive_429s >= 3,
        }
        try:
            with open(self.log_file, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(log_entry) + "\n")
        except Exception:
            logger.exception("Failed to write rate limiter log")


class NullKnowledgeStoreManager:
    """Placeholder knowledge manager for wrappers that only use L1/L2."""

    def query(
        self,
        store_type: str,
        query_text: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return []


@dataclass
class WrapperConfig:
    """Configuration values for the agent wrapper service."""

    agent_type: str
    agent_variant: str
    port: int
    model: str
    redis_url: str
    postgres_url: str
    session_prefix: str
    window_size: int = 20
    ttl_hours: int = 24
    min_ciar: float = 0.6


@dataclass
class AgentWrapperState:
    """Runtime state stored on the FastAPI application."""

    agent: BaseAgent
    memory_system: UnifiedMemorySystem
    l1_tier: ActiveContextTier
    l2_tier: WorkingMemoryTier
    redis_client: redis.StrictRedis
    agent_type: str
    agent_variant: str
    session_prefix: str
    rate_limiter: RateLimiter
    sessions: set[str] = field(default_factory=set)

    def apply_prefix(self, session_id: str) -> str:
        prefix = f"{self.session_prefix}:"
        if session_id.startswith(prefix):
            return session_id
        return f"{self.session_prefix}:{session_id}"

    def track_session(self, session_id: str) -> None:
        self.sessions.add(session_id)

    def remove_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            self.sessions.remove(session_id)


AGENT_TYPES: dict[str, type[BaseAgent]] = {
    "full": MemoryAgent,
    "rag": RAGAgent,
    "full_context": FullContextAgent,
}

SESSION_PREFIXES = {
    "full": "full",
    "rag": "rag",
    "full_context": "full_context",
}


def _read_env_or_raise(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Required environment variable '{key}' is not set.")
    return value


async def initialize_state(config: WrapperConfig) -> AgentWrapperState:
    """Initialize storage adapters, tiers, memory system, and agent."""

    os.makedirs("logs", exist_ok=True)
    log_stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    rate_log = f"logs/rate_limiter_{config.agent_type}_{config.agent_variant}_{log_stamp}.jsonl"
    rate_limiter = RateLimiter(rpm=100, tpm=1_000_000, min_delay=0.6, log_file=rate_log)

    redis_client = redis.StrictRedis.from_url(config.redis_url, decode_responses=True)
    try:
        if not redis_client.ping():
            raise RuntimeError("Redis ping failed.")
    except Exception as exc:
        raise RuntimeError(f"Redis connection failed: {exc}") from exc

    redis_adapter = RedisAdapter(
        {
            "url": config.redis_url,
            "window_size": config.window_size,
            "ttl_seconds": config.ttl_hours * 3600,
        }
    )

    postgres_l1 = PostgresAdapter({"url": config.postgres_url, "table": "active_context"})
    postgres_l2 = PostgresAdapter(
        {
            "url": config.postgres_url,
            "table": "working_memory",
            "lock_writes": True,
        }
    )

    l1_tier = ActiveContextTier(
        redis_adapter=redis_adapter,
        postgres_adapter=postgres_l1,
        config={"window_size": config.window_size, "ttl_hours": config.ttl_hours},
    )
    l2_tier = WorkingMemoryTier(
        postgres_adapter=postgres_l2,
        config={"ciar_threshold": config.min_ciar},
    )

    await l1_tier.initialize()
    await l2_tier.initialize()

    await l1_tier.initialize()
    await l2_tier.initialize()

    llm_client = LLMClient.from_env()

    # Initialize engines
    ciar_scorer = CIARScorer()
    fact_extractor = FactExtractor(llm_client)
    topic_segmenter = TopicSegmenter(llm_client)

    promotion_engine = PromotionEngine(
        l1_tier=l1_tier,
        l2_tier=l2_tier,
        topic_segmenter=topic_segmenter,
        fact_extractor=fact_extractor,
        ciar_scorer=ciar_scorer,
        config={"promotion_threshold": config.min_ciar},
    )

    memory_system = UnifiedMemorySystem(
        redis_client=redis_client,
        knowledge_manager=NullKnowledgeStoreManager(),
        l1_tier=l1_tier,
        l2_tier=l2_tier,
        promotion_engine=promotion_engine,
    )

    agent_cls = AGENT_TYPES[config.agent_type]
    agent = agent_cls(
        agent_id=f"mas-{config.agent_type}__{config.agent_variant}",
        llm_client=llm_client,
        memory_system=memory_system,
        config={"model": config.model, "agent_variant": config.agent_variant},
    )

    return AgentWrapperState(
        agent=agent,
        memory_system=memory_system,
        l1_tier=l1_tier,
        l2_tier=l2_tier,
        redis_client=redis_client,
        agent_type=config.agent_type,
        agent_variant=config.agent_variant,
        session_prefix=config.session_prefix,
        rate_limiter=rate_limiter,
    )


async def shutdown_state(state: AgentWrapperState) -> None:
    """Close storage connections and agent resources."""

    await state.l1_tier.cleanup()
    await state.l2_tier.cleanup()
    await state.agent.close()
    try:
        state.redis_client.close()
    except Exception:
        logger.exception("Failed to close Redis client cleanly.")


def create_app(config: WrapperConfig) -> FastAPI:
    """Create and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Initializing agent wrapper for '%s'", config.agent_type)
        state = await initialize_state(config)
        app.state.wrapper = state
        yield
        logger.info("Shutting down agent wrapper for '%s'", config.agent_type)
        await shutdown_state(state)

    app = FastAPI(title="MAS Agent Wrapper", version="1.0", lifespan=lifespan)

    @app.post("/run_turn", response_model=RunTurnResponse)
    async def run_turn(request: RunTurnRequest) -> RunTurnResponse:
        state: AgentWrapperState = app.state.wrapper
        session_id = state.apply_prefix(request.session_id)
        state.track_session(session_id)
        metadata = dict(request.metadata or {})
        metadata.setdefault("skip_l1_write", True)
        updated_request = request.model_copy(
            update={"session_id": session_id, "metadata": metadata}
        )

        estimated_input_tokens = _estimate_tokens(updated_request.content)
        await state.rate_limiter.wait_if_needed(estimated_input_tokens)

        try:
            t0 = time.perf_counter()
            await _store_turn(state, updated_request, role=updated_request.role)
            t1 = time.perf_counter()
            if updated_request.history:
                response = await state.agent.run_turn(
                    updated_request,
                    history=updated_request.history,
                )
            else:
                response = await state.agent.run_turn(updated_request)
            t2 = time.perf_counter()
            await _store_turn(state, response, role=response.role)
            t3 = time.perf_counter()
            estimated_total_tokens = _estimate_tokens(
                f"{updated_request.content}\n{response.content}"
            )
            state.rate_limiter.record_usage(estimated_total_tokens)
        except Exception as exc:
            state.rate_limiter.register_error(exc)
            logger.exception("Error handling /run_turn for session %s", session_id)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        metadata = dict(response.metadata or {})
        metadata.update(
            {
                "storage_ms_pre": (t1 - t0) * 1000,
                "llm_ms": (t2 - t1) * 1000,
                "storage_ms_post": (t3 - t2) * 1000,
                "storage_ms": (t1 - t0 + t3 - t2) * 1000,
            }
        )
        return response.model_copy(update={"metadata": metadata})

    @app.get("/sessions")
    async def list_sessions() -> dict[str, Any]:
        state: AgentWrapperState = app.state.wrapper
        return {"sessions": sorted(state.sessions)}

    @app.get("/memory_state")
    async def memory_state(session_id: str = Query(...)) -> dict[str, Any]:
        state: AgentWrapperState = app.state.wrapper
        prefixed_id = state.apply_prefix(session_id)
        try:
            l1_turns = await state.l1_tier.retrieve(prefixed_id)
            l2_facts = await state.l2_tier.query_by_session(prefixed_id)
        except Exception as exc:
            logger.exception("Failed to compute memory state for %s", prefixed_id)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return {
            "session_id": prefixed_id,
            "l1_turns": len(l1_turns or []),
            "l2_facts": len(l2_facts or []),
            "l3_episodes": 0,
            "l4_docs": 0,
        }

    @app.post("/cleanup_force")
    async def cleanup_force(session_id: str = Query(...)) -> dict[str, Any]:
        state: AgentWrapperState = app.state.wrapper
        if session_id == "all":
            target_sessions = list(state.sessions)
        else:
            target_sessions = [state.apply_prefix(session_id)]

        results: dict[str, Any] = {}
        for sid in target_sessions:
            results[sid] = await _cleanup_session(state, sid)
            state.remove_session(sid)

        return {"results": results}

    @app.get("/health")
    async def health() -> dict[str, Any]:
        state: AgentWrapperState = app.state.wrapper
        try:
            redis_ok = bool(state.redis_client.ping())
        except Exception:
            redis_ok = False
        return {
            "status": "ok" if redis_ok else "degraded",
            "agent_type": state.agent_type,
            "agent_variant": state.agent_variant,
            "redis": redis_ok,
            "l1": await state.l1_tier.health_check(),
            "l2": await state.l2_tier.health_check(),
            "agent": await state.agent.health_check(),
        }

    return app


async def _store_turn(
    state: AgentWrapperState, message: Any, role: Literal["user", "assistant"]
) -> None:
    """Store a user or assistant turn in L1 for context assembly."""

    def _encode_turn_id(turn_id: int, message_role: str) -> int:
        """Encode turn IDs so user/assistant turns do not collide in storage."""
        if message_role == "assistant":
            return (turn_id * 2) + 1
        return turn_id * 2

    timestamp = getattr(message, "timestamp", None) or datetime.now(UTC)
    metadata = getattr(message, "metadata", None) or {}
    stored_turn_id = _encode_turn_id(int(message.turn_id), role)
    turn = TurnData(
        session_id=message.session_id,
        turn_id=str(stored_turn_id),
        role=role,
        content=message.content,
        timestamp=timestamp,
        metadata=metadata,
    )
    try:
        await state.l1_tier.store(turn)
    except Exception as exc:
        if "duplicate key value violates unique constraint" in str(exc):
            logger.warning(
                "Ignored duplicate turn submission: session_id=%s, turn_id=%s",
                message.session_id,
                stored_turn_id,
            )
        else:
            raise


def _estimate_tokens(text: str) -> int:
    """Estimate token count using conservative heuristic (4 chars/token)."""
    return int(len(text) * 0.25)


async def _cleanup_session(state: AgentWrapperState, session_id: str) -> dict[str, Any]:
    """Remove session data from L1/L2 and notify agent."""

    l1_deleted = False
    l2_deleted = 0
    try:
        l1_deleted = await state.l1_tier.delete(session_id)
        facts = await state.l2_tier.query_by_session(session_id)
        for fact in facts:
            await state.l2_tier.delete(fact.fact_id)
            l2_deleted += 1
    except Exception:
        logger.exception("Cleanup failed for session %s", session_id)

    try:
        await state.agent.cleanup_session(session_id)
    except Exception:
        logger.exception("Agent cleanup failed for session %s", session_id)

    return {"l1_deleted": l1_deleted, "l2_deleted": l2_deleted}


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the wrapper service."""

    parser = argparse.ArgumentParser(description="MAS Agent Wrapper Service")
    parser.add_argument("--agent-type", choices=AGENT_TYPES.keys(), required=True)
    parser.add_argument(
        "--agent-variant",
        type=str,
        default="baseline",
        help="Variant identifier for research runs (used for session isolation and logging).",
    )
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--model", type=str, default="gemini-2.5-flash-lite")
    return parser.parse_args(argv)


def build_config(args: argparse.Namespace) -> WrapperConfig:
    """Build wrapper configuration from CLI args and environment variables."""

    os.environ["AGENT_TYPE"] = args.agent_type

    redis_url = _read_env_or_raise("REDIS_URL")
    postgres_url = _read_env_or_raise("POSTGRES_URL")
    session_prefix = f"{SESSION_PREFIXES[args.agent_type]}__{args.agent_variant}"

    window_size = int(os.environ.get("MAS_L1_WINDOW", "20"))
    ttl_hours = int(os.environ.get("MAS_L1_TTL_HOURS", "24"))
    min_ciar = float(os.environ.get("MAS_MIN_CIAR", "0.6"))

    return WrapperConfig(
        agent_type=args.agent_type,
        agent_variant=args.agent_variant,
        port=args.port,
        model=args.model,
        redis_url=redis_url,
        postgres_url=postgres_url,
        session_prefix=session_prefix,
        window_size=window_size,
        ttl_hours=ttl_hours,
        min_ciar=min_ciar,
    )


def main(argv: Iterable[str] | None = None) -> None:
    """Entrypoint for running the FastAPI wrapper via Uvicorn."""

    logging.basicConfig(level=logging.DEBUG)
    args = parse_args(argv)
    config = build_config(args)
    app = create_app(config)
    uvicorn.run(app, host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    main()
