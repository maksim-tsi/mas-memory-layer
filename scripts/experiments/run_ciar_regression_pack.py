#!/usr/bin/env python3
"""Run the local CIAR regression pack."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_CMD = ("./.venv/bin/python", "-c", "import sys; print(sys.executable)")
RUFF_CMD = ("./.venv/bin/ruff", "check", ".")
PYTEST_CMD = (
    "./.venv/bin/pytest",
    "tests/memory/test_ciar_scorer.py",
    "tests/agents/tools/test_ciar_tools.py",
    "tests/api/test_v2_router_ciar.py",
    "tests/memory/test_working_memory_tier.py",
    "tests/memory/engines/test_promotion_engine.py",
    "tests/memory/test_contradiction_policy.py",
    "tests/memory/test_unified_memory_system.py",
    "tests/scripts/test_ciar_challenge_experiment.py",
    "tests/scripts/test_ciar_challenge_with_env.py",
    "tests/scripts/test_ciar_policy_analysis.py",
    "-v",
)


def shell_join(command: Sequence[str]) -> str:
    """Render commands without shell-specific quoting needs for this fixed pack."""
    return " ".join(command)


def build_commands(*, skip_ruff: bool) -> list[tuple[str, ...]]:
    commands = [PYTHON_CMD]
    if not skip_ruff:
        commands.append(RUFF_CMD)
    commands.append(PYTEST_CMD)
    return commands


def verify_repo_root(cwd: Path) -> int:
    if (cwd / "pyproject.toml").exists() and (cwd / "scripts").is_dir():
        return 0
    print(
        "CIAR regression pack must be run from the repository root.",
        file=sys.stderr,
    )
    print(f"Current directory: {cwd}", file=sys.stderr)
    return 2


def run_command(command: Sequence[str]) -> int:
    print(f"$ {shell_join(command)}", flush=True)
    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


def run_pack(*, skip_ruff: bool, list_only: bool, cwd: Path | None = None) -> int:
    cwd = cwd or Path.cwd()
    commands = build_commands(skip_ruff=skip_ruff)
    if list_only:
        for command in commands:
            print(shell_join(command))
        return 0

    root_status = verify_repo_root(cwd)
    if root_status != 0:
        return root_status

    for command in commands:
        status = run_command(command)
        if status != 0:
            return status
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local CIAR regression pack.")
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the commands that would run and exit.",
    )
    parser.add_argument(
        "--skip-ruff",
        action="store_true",
        help="Run only the CIAR pytest pack after a separate ruff pass.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    return run_pack(skip_ruff=bool(args.skip_ruff), list_only=bool(args.list))


if __name__ == "__main__":
    raise SystemExit(main())
