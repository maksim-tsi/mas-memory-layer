"""Permission policy for MCP-facing memory operations."""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field

from src.memory.services.contracts import YAAMErrorPayload

OperationMode = Literal["read", "write", "lifecycle", "admin"]

READ_TOOLS = frozenset(
    {
        "yaam.memory.query",
        "yaam.memory.get_context",
        "yaam.contradiction.review",
        "yaam.curation.list_decisions",
        "yaam.trace.lookup",
        "yaam.l2.search_facts",
        "yaam.l3.search_episodes",
        "yaam.l4.search_knowledge",
        "yaam.ciar.explain",
        "yaam.evidence.table",
        "yaam.health.check",
    }
)

WRITE_TOOLS = frozenset(
    {
        "yaam.curation.record_decision",
        "yaam.trace.record_correlation",
        "yaam.l2.store_fact",
        "yaam.l3.assimilate_episode",
        "yaam.l4.finalize_artifact",
    }
)

LIFECYCLE_TOOLS = frozenset(
    {
        "yaam.l3.assimilate_episode",
        "yaam.l4.finalize_artifact",
    }
)


class PermissionDecision(BaseModel):
    """Structured decision returned by permission checks."""

    allowed: bool
    tool_name: str
    mode: OperationMode
    reason: str
    code: str = Field(default="permission.allowed")


class YAAMPermissionError(PermissionError):
    """Permission failure with a stable public error payload."""

    def __init__(self, payload: YAAMErrorPayload) -> None:
        super().__init__(payload.message)
        self.payload = payload


class PermissionPolicy(BaseModel):
    """Default-deny policy for mutating MCP tools."""

    enable_writes: bool = False
    allowlisted_tools: frozenset[str] = Field(default_factory=frozenset)
    enable_lifecycle: bool = False

    @classmethod
    def from_env(cls) -> PermissionPolicy:
        """Build policy from MCP-specific environment flags."""
        return cls(
            enable_writes=_truthy(os.environ.get("YAAM_MCP_ENABLE_WRITES")),
            allowlisted_tools=_parse_allowlist(os.environ.get("YAAM_MCP_ALLOWLISTED_TOOLS")),
            enable_lifecycle=_truthy(os.environ.get("YAAM_MCP_ENABLE_LIFECYCLE")),
        )

    def check(self, tool_name: str, mode: OperationMode) -> PermissionDecision:
        """Return whether a public operation is permitted."""
        if mode == "read":
            return PermissionDecision(
                allowed=True,
                tool_name=tool_name,
                mode=mode,
                reason="Read operations are enabled by default.",
            )

        if mode == "admin":
            return PermissionDecision(
                allowed=False,
                tool_name=tool_name,
                mode=mode,
                reason="Admin operations are not part of MCP v1.",
                code="permission.admin_disabled",
            )

        if mode == "lifecycle" and not self.enable_lifecycle:
            return PermissionDecision(
                allowed=False,
                tool_name=tool_name,
                mode=mode,
                reason="Lifecycle operations require YAAM_MCP_ENABLE_LIFECYCLE=true.",
                code="permission.lifecycle_disabled",
            )

        if mode in {"write", "lifecycle"} and not self.enable_writes:
            return PermissionDecision(
                allowed=False,
                tool_name=tool_name,
                mode=mode,
                reason="Write operations require YAAM_MCP_ENABLE_WRITES=true.",
                code="permission.writes_disabled",
            )

        if "*" in self.allowlisted_tools or tool_name in self.allowlisted_tools:
            return PermissionDecision(
                allowed=True,
                tool_name=tool_name,
                mode=mode,
                reason="Tool is allowlisted for mutating access.",
            )

        return PermissionDecision(
            allowed=False,
            tool_name=tool_name,
            mode=mode,
            reason="Mutating tool is not allowlisted.",
            code="permission.tool_not_allowlisted",
        )

    def require(self, tool_name: str, mode: OperationMode) -> PermissionDecision:
        """Raise a structured permission error when the decision is denied."""
        decision = self.check(tool_name, mode)
        if decision.allowed:
            return decision

        raise YAAMPermissionError(
            YAAMErrorPayload(
                code=decision.code,
                message=decision.reason,
                retryable=False,
                operation=tool_name,
                affected_tier="SYSTEM",
                details={"mode": mode},
            )
        )


def _parse_allowlist(value: str | None) -> frozenset[str]:
    if not value:
        return frozenset()
    return frozenset(item.strip() for item in value.split(",") if item.strip())


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}
