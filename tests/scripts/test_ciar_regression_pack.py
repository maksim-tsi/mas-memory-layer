"""Tests for the CIAR regression pack runner."""

from __future__ import annotations

import sys
from pathlib import Path

_EXPERIMENTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "experiments"
sys.path.insert(0, str(_EXPERIMENTS_DIR))

import run_ciar_regression_pack as regression_pack  # noqa: E402


def test_list_prints_commands_without_executing(
    capsys,
    monkeypatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        regression_pack,
        "run_command",
        lambda command: calls.append(tuple(command)) or 0,
    )

    status = regression_pack.run_pack(skip_ruff=False, list_only=True)

    assert status == 0
    assert calls == []
    output = capsys.readouterr().out
    assert "./.venv/bin/ruff check ." in output
    assert "./.venv/bin/pytest" in output
    assert "tests/memory/test_ciar_scorer.py" in output


def test_default_mode_runs_ruff_before_pytest(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool]\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    calls: list[tuple[str, ...]] = []

    def fake_run(command):
        calls.append(tuple(command))
        return 0

    monkeypatch.setattr(regression_pack, "run_command", fake_run)

    status = regression_pack.run_pack(skip_ruff=False, list_only=False, cwd=tmp_path)

    assert status == 0
    assert calls == [
        regression_pack.PYTHON_CMD,
        regression_pack.RUFF_CMD,
        regression_pack.PYTEST_CMD,
    ]


def test_skip_ruff_runs_only_python_check_and_pytest(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool]\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    calls: list[tuple[str, ...]] = []

    def fake_run(command):
        calls.append(tuple(command))
        return 0

    monkeypatch.setattr(regression_pack, "run_command", fake_run)

    status = regression_pack.run_pack(skip_ruff=True, list_only=False, cwd=tmp_path)

    assert status == 0
    assert calls == [regression_pack.PYTHON_CMD, regression_pack.PYTEST_CMD]


def test_ruff_failure_returns_status_and_stops(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool]\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    calls: list[tuple[str, ...]] = []

    def fake_run(command):
        calls.append(tuple(command))
        return 7 if tuple(command) == regression_pack.RUFF_CMD else 0

    monkeypatch.setattr(regression_pack, "run_command", fake_run)

    status = regression_pack.run_pack(skip_ruff=False, list_only=False, cwd=tmp_path)

    assert status == 7
    assert calls == [regression_pack.PYTHON_CMD, regression_pack.RUFF_CMD]


def test_pytest_failure_returns_status(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool]\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()

    def fake_run(command):
        return 5 if tuple(command) == regression_pack.PYTEST_CMD else 0

    monkeypatch.setattr(regression_pack, "run_command", fake_run)

    status = regression_pack.run_pack(skip_ruff=False, list_only=False, cwd=tmp_path)

    assert status == 5


def test_pytest_command_is_ciar_local_only() -> None:
    rendered = regression_pack.shell_join(regression_pack.PYTEST_CMD)

    assert "tests/memory/test_ciar_scorer.py" in rendered
    assert "tests/scripts/test_ciar_policy_analysis.py" in rendered
    assert "integration" not in rendered
    assert "llm_real" not in rendered
    assert "run_ciar_challenge.py" not in rendered
