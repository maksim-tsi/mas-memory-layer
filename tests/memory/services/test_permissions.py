import pytest

from src.memory.services.permissions import PermissionPolicy, YAAMPermissionError


def test_read_tools_are_enabled_by_default() -> None:
    decision = PermissionPolicy().check("yaam.memory.query", "read")

    assert decision.allowed is True


def test_write_tools_are_denied_by_default() -> None:
    policy = PermissionPolicy()

    with pytest.raises(YAAMPermissionError) as exc:
        policy.require("yaam.l2.store_fact", "write")

    assert exc.value.payload.code == "permission.writes_disabled"
    assert exc.value.payload.operation == "yaam.l2.store_fact"


def test_allowlisted_write_requires_write_flag() -> None:
    policy = PermissionPolicy(allowlisted_tools=frozenset({"yaam.l2.store_fact"}))

    decision = policy.check("yaam.l2.store_fact", "write")

    assert decision.allowed is False
    assert decision.code == "permission.writes_disabled"


def test_allowlisted_write_is_permitted_when_write_flag_is_enabled() -> None:
    policy = PermissionPolicy(
        enable_writes=True,
        allowlisted_tools=frozenset({"yaam.l2.store_fact"}),
    )

    decision = policy.check("yaam.l2.store_fact", "write")

    assert decision.allowed is True


def test_policy_from_env_parses_flags_and_tool_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YAAM_MCP_ENABLE_WRITES", "true")
    monkeypatch.setenv("YAAM_MCP_ENABLE_LIFECYCLE", "1")
    monkeypatch.setenv(
        "YAAM_MCP_ALLOWLISTED_TOOLS", "yaam.l2.store_fact, yaam.l4.finalize_artifact"
    )

    policy = PermissionPolicy.from_env()

    assert policy.enable_writes is True
    assert policy.enable_lifecycle is True
    assert "yaam.l4.finalize_artifact" in policy.allowlisted_tools
