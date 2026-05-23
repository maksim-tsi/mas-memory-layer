"""Tests for YAAM data-node diagnostics."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_DEBUG_DIR = Path(__file__).parent.parent.parent / "scripts" / "debug"
sys.path.insert(0, str(_DEBUG_DIR))

import check_yaam_data_node as data_node_check  # noqa: E402


def test_endpoint_summary_redacts_url_password() -> None:
    summary = data_node_check.endpoint_summary(
        "postgresql://user:secret@example.test:5432/yaam", 5432
    )

    assert summary == {
        "scheme": "postgresql",
        "host": "example.test",
        "port": 5432,
        "path_present": True,
        "user_present": True,
        "password_present": True,
    }
    assert "secret" not in str(summary)


def test_endpoint_summary_handles_service_url_shapes() -> None:
    assert data_node_check.endpoint_summary("redis://cache.test:6379/0", 6379)["port"] == 6379
    assert data_node_check.endpoint_summary("http://phoenix.test:6006/v1/traces", 6006)[
        "path_present"
    ]
    assert data_node_check.endpoint_summary("bolt://neo4j.test:7687", 7687)["scheme"] == "bolt"


def test_json_output_is_stable_and_secret_free(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "REDIS_URL=redis://redis.test:6379/0",
                "POSTGRES_URL=postgresql://user:secret@postgres.test:5432/yaam",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(data_node_check, "tcp_check", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(data_node_check, "redis_ping", lambda *args, **kwargs: {"ok": True})

    exit_code = data_node_check.main(
        ["--env-file", str(env_file), "--service", "redis", "--json"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["services"][0]["service"] == "redis"
    assert "secret" not in captured.out


def test_selected_services_only_run_selected_checks(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "REDIS_URL=redis://redis.test:6379/0",
                "POSTGRES_URL=postgresql://postgres.test:5432/yaam",
            ]
        ),
        encoding="utf-8",
    )
    seen: list[str] = []

    def fake_check_service(spec, env_values, *, timeout_s):
        seen.append(spec.name)
        return {
            "service": spec.name,
            "env_key": spec.env_key,
            "present": True,
            "endpoint": {},
            "tcp": {"ok": True},
            "protocol": {"ok": True},
            "ok": True,
        }

    monkeypatch.setattr(data_node_check, "check_service", fake_check_service)

    payload = data_node_check.run_checks(env_file, ["redis", "postgres"])

    assert seen == ["redis", "postgres"]
    assert [service["service"] for service in payload["services"]] == ["redis", "postgres"]


def test_tcp_failure_returns_nonzero_without_printing_secrets(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "REDIS_URL=redis://:secret@redis.test:6379/0",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        data_node_check,
        "tcp_check",
        lambda *args, **kwargs: {"ok": False, "error_type": "TimeoutError", "error": "timed out"},
    )

    exit_code = data_node_check.main(["--env-file", str(env_file), "--service", "redis"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "secret" not in captured.out
    assert "tcp_ok=False" in captured.out
