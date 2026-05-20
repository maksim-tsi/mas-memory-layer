"""Tests for the CIAR .env live-run wrapper."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_EXPERIMENTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "experiments"
sys.path.insert(0, str(_EXPERIMENTS_DIR))

from run_ciar_challenge_with_env import (  # noqa: E402
    build_harness_command,
    force_data_node_service_urls,
    load_env_values,
    parse_env_file,
    replace_url_host_port,
)


def test_parse_env_file_supports_export_and_quotes(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "# comment",
                "export OPENROUTER_API_KEY='secret-value'",
                'REDIS_URL="redis://host:6379/0"',
                "POSTGRES_URL=postgresql://user:pass@host/db",
            ]
        ),
        encoding="utf-8",
    )

    values = parse_env_file(env_file)

    assert values["OPENROUTER_API_KEY"] == "secret-value"
    assert values["REDIS_URL"] == "redis://host:6379/0"
    assert values["POSTGRES_URL"] == "postgresql://user:pass@host/db"


def test_load_env_values_reports_key_names_without_values(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "OPENROUTER_API_KEY=secret-value",
                "REDIS_URL=redis://host:6379/0",
                "POSTGRES_URL=postgresql://user:pass@host/db",
            ]
        ),
        encoding="utf-8",
    )
    for key in ["OPENROUTER_API_KEY", "REDIS_URL", "POSTGRES_URL"]:
        monkeypatch.delenv(key, raising=False)

    summary = load_env_values(env_file)

    assert summary["missing_required_keys"] == []
    assert set(summary["loaded_keys"]) >= {"OPENROUTER_API_KEY", "REDIS_URL", "POSTGRES_URL"}
    assert "OPENROUTER_API_KEY" in summary["available_sensitive_key_names"]
    assert "secret-value" not in str(summary)


def test_build_harness_command_defaults_to_focused_live_scenarios(monkeypatch) -> None:
    monkeypatch.setenv("DATA_NODE_IP", "192.168.107.187")
    monkeypatch.delenv("MAS_REDIS_TIMEOUT", raising=False)
    monkeypatch.delenv("MAS_OPENROUTER_TIMEOUT", raising=False)
    monkeypatch.delenv("MAS_MAX_OUTPUT_TOKENS", raising=False)
    namespace = type(
        "Args",
        (),
        {
            "run_id": "ciar-exp-live-env-test",
            "output_dir": "logs/ciar_challenge",
            "model": "tencent/hy3-preview",
            "phoenix_endpoint": None,
            "phoenix_project_name": None,
            "data_node_ip": None,
            "provider_health_timeout": 45.0,
            "skip_provider_health": True,
            "provider_health_skip_reason": "test skip",
            "require_provider_health": False,
            "scenario_id": [],
            "redis_timeout": 15.0,
            "openrouter_timeout": 120.0,
            "max_output_tokens": 8192,
            "promotion_policy_mode": "hybrid_gate",
            "contradiction_policy_mode": "suppress_superseded",
        },
    )()

    command = build_harness_command(namespace)
    command_text = " ".join(command)

    assert "--scenario-id segment_mismatch" in command_text
    assert "--scenario-id contradiction_update" in command_text
    assert "--scenario-id small_talk" in command_text
    assert "--promotion-policy-mode hybrid_gate" in command_text
    assert "--contradiction-policy-mode suppress_superseded" in command_text
    assert "http://192.168.107.187:6006/v1/traces" in command
    assert os.environ["MAS_OPENROUTER_TIMEOUT"] == "120.0"


def test_replace_url_host_port_preserves_credentials_and_path() -> None:
    rewritten = replace_url_host_port(
        "postgresql://user:secret@old-host:5432/yaam-test?sslmode=disable",
        "192.168.107.187",
        5432,
    )

    assert rewritten == "postgresql://user:secret@192.168.107.187:5432/yaam-test?sslmode=disable"


def test_force_data_node_service_urls_rewrites_names_without_printing_values(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_URL", "postgresql://user:secret@old-host:5432/yaam-test")
    monkeypatch.setenv("REDIS_URL", "redis://old-host:6379/0")

    changed = force_data_node_service_urls("192.168.107.187")

    assert changed == ["REDIS_URL", "POSTGRES_URL", "PHOENIX_COLLECTOR_ENDPOINT"]
    assert os.environ["REDIS_URL"] == "redis://192.168.107.187:6379/0"
    assert os.environ["POSTGRES_URL"] == "postgresql://user:secret@192.168.107.187:5432/yaam-test"
    assert os.environ["PHOENIX_COLLECTOR_ENDPOINT"] == "http://192.168.107.187:6006/v1/traces"
