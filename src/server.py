"""API Wall server exposing OpenAI-compatible chat completions."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
import uuid
from collections.abc import Iterable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Literal

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict

from src.agents.models import RunTurnRequest
from src.evaluation import agent_wrapper

logger = logging.getLogger(__name__)


class ChatCompletionMessage(BaseModel):
    """OpenAI-compatible chat message payload."""

    role: str
    content: Any

    model_config = ConfigDict(extra="allow")


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request payload."""

    model: str | None = None
    messages: list[ChatCompletionMessage]
    stream: bool = False

    model_config = ConfigDict(extra="allow")


class ChatCompletionChoice(BaseModel):
    """Single chat completion choice."""

    index: int
    message: ChatCompletionMessage
    finish_reason: str | None = "stop"


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response payload."""

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: dict[str, int] | None = None
    metadata: dict[str, Any] | None = None


def _parse_mock_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid X-Mock-Time: {value}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _coerce_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=True)
    except TypeError:
        return str(content)


def _latest_message(messages: list[ChatCompletionMessage]) -> ChatCompletionMessage:
    for message in reversed(messages):
        if message.role.lower() == "user":
            return message
    return messages[-1]


def _compute_turn_id(messages: list[ChatCompletionMessage]) -> int:
    user_count = sum(1 for message in messages if message.role.lower() == "user")
    return max(user_count - 1, 0)


def create_app(config: agent_wrapper.WrapperConfig) -> FastAPI:
    """Create and configure the API Wall FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "Initializing API Wall for agent_type=%s agent_variant=%s",
            config.agent_type,
            config.agent_variant,
        )
        state = await agent_wrapper.initialize_state(config)
        app.state.wrapper = state
        yield
        logger.info(
            "Shutting down API Wall for agent_type=%s agent_variant=%s",
            config.agent_type,
            config.agent_variant,
        )
        await agent_wrapper.shutdown_state(state)

    app = FastAPI(title="MAS API Wall", version="1.0", lifespan=lifespan)

    @app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
    async def chat_completions(
        request: ChatCompletionRequest,
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
        x_mock_time: str | None = Header(default=None, alias="X-Mock-Time"),
        traceparent: str | None = Header(default=None),
    ) -> ChatCompletionResponse:
        if request.stream:
            raise HTTPException(status_code=400, detail="streaming is not supported")
        if not x_session_id:
            raise HTTPException(status_code=400, detail="X-Session-Id header is required")
        if not request.messages:
            raise HTTPException(status_code=400, detail="messages cannot be empty")

        state: agent_wrapper.AgentWrapperState = app.state.wrapper
        session_id = state.apply_prefix(x_session_id)
        state.track_session(session_id)

        history = [message.model_dump() for message in request.messages]
        latest_message = _latest_message(request.messages)
        mock_timestamp = _parse_mock_time(x_mock_time)

        metadata: dict[str, Any] = {}
        if traceparent:
            metadata["traceparent"] = traceparent
        if x_mock_time:
            metadata["mock_time"] = x_mock_time

        run_request = RunTurnRequest(
            session_id=session_id,
            role=latest_message.role,
            content=_coerce_message_content(latest_message.content),
            turn_id=_compute_turn_id(request.messages),
            metadata=metadata or None,
            timestamp=mock_timestamp,
            history=history,
        )

        estimated_input_tokens = agent_wrapper._estimate_tokens(run_request.content)
        await state.rate_limiter.wait_if_needed(estimated_input_tokens)

        try:
            t0 = time.perf_counter()
            await agent_wrapper._store_turn(state, run_request, role=run_request.role)
            t1 = time.perf_counter()
            response = await state.agent.run_turn(run_request, history=history)
            t2 = time.perf_counter()
            await agent_wrapper._store_turn(state, response, role=response.role)
            t3 = time.perf_counter()
            estimated_total_tokens = agent_wrapper._estimate_tokens(
                f"{run_request.content}\n{response.content}"
            )
            state.rate_limiter.record_usage(estimated_total_tokens)
        except Exception as exc:
            state.rate_limiter.register_error(exc)
            logger.exception("Error handling /v1/chat/completions for session %s", session_id)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        response_metadata = dict(response.metadata or {})
        response_metadata.update(
            {
                "storage_ms_pre": (t1 - t0) * 1000,
                "llm_ms": (t2 - t1) * 1000,
                "storage_ms_post": (t3 - t2) * 1000,
                "storage_ms": (t1 - t0 + t3 - t2) * 1000,
            }
        )
        response = response.model_copy(update={"metadata": response_metadata})

        completion_message = ChatCompletionMessage(
            role=response.role,
            content=response.content,
        )
        completion_tokens = agent_wrapper._estimate_tokens(response.content)

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=request.model or config.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=completion_message,
                    finish_reason="stop",
                )
            ],
            usage={
                "prompt_tokens": estimated_input_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": estimated_total_tokens,
            },
            metadata=response_metadata,
        )

    @app.post("/control/session/reset")
    async def reset_session(
        x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
    ) -> dict[str, Any]:
        if not x_session_id:
            raise HTTPException(status_code=400, detail="X-Session-Id header is required")
        state: agent_wrapper.AgentWrapperState = app.state.wrapper
        session_id = state.apply_prefix(x_session_id)
        result = await agent_wrapper._cleanup_session(state, session_id)
        state.remove_session(session_id)
        return {"session_id": session_id, "result": result}

    @app.get("/health")
    async def health() -> dict[str, Any]:
        state: agent_wrapper.AgentWrapperState = app.state.wrapper
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


def build_config_from_env() -> agent_wrapper.WrapperConfig:
    """Build wrapper configuration from environment variables."""
    agent_type = os.environ.get("MAS_AGENT_TYPE") or os.environ.get("AGENT_TYPE") or "full"
    os.environ["AGENT_TYPE"] = agent_type
    agent_variant = os.environ.get("MAS_AGENT_VARIANT", "baseline")

    redis_url = agent_wrapper._read_env_or_raise("REDIS_URL")
    postgres_url = agent_wrapper._read_env_or_raise("POSTGRES_URL")
    session_prefix = f"{agent_wrapper.SESSION_PREFIXES[agent_type]}__{agent_variant}"

    window_size = int(os.environ.get("MAS_L1_WINDOW", "20"))
    ttl_hours = int(os.environ.get("MAS_L1_TTL_HOURS", "24"))
    min_ciar = float(os.environ.get("MAS_MIN_CIAR", "0.6"))
    model = os.environ.get("MAS_MODEL", "gemini-2.5-flash-lite")
    port = int(os.environ.get("MAS_PORT", "8080"))

    return agent_wrapper.WrapperConfig(
        agent_type=agent_type,
        agent_variant=agent_variant,
        port=port,
        model=model,
        redis_url=redis_url,
        postgres_url=postgres_url,
        session_prefix=session_prefix,
        window_size=window_size,
        ttl_hours=ttl_hours,
        min_ciar=min_ciar,
    )


app = create_app(build_config_from_env())


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the API Wall service."""
    parser = argparse.ArgumentParser(description="MAS API Wall Service")
    parser.add_argument("--agent-type", choices=agent_wrapper.AGENT_TYPES.keys(), required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--model", type=str, default="gemini-2.5-flash-lite")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> None:
    """Entrypoint for running the API Wall via Uvicorn."""
    logging.basicConfig(level=logging.INFO)
    args = parse_args(argv)
    config = agent_wrapper.build_config(args)
    app = create_app(config)
    uvicorn.run(app, host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    main()
