"""
Repository-level pytest policy.

This conftest lives at repo root (not under tests/) so it can enforce a default
"local-only" test mode without rewriting test files.
"""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require network/external services.",
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests (e.g., real provider calls).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: tests that require network/external services (skipped by default).",
    )
    config.addinivalue_line(
        "markers",
        "slow: slow tests (skipped by default).",
    )
    config.addinivalue_line(
        "markers",
        "llm_real: tests that call real LLM/provider endpoints (skipped by default).",
    )
    config.addinivalue_line(
        "markers",
        "concurrency: tests that exercise concurrency behavior.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    run_integration = bool(config.getoption("--run-integration"))
    run_slow = bool(config.getoption("--run-slow"))

    skip_integration = pytest.mark.skip(reason="needs --run-integration")
    skip_slow = pytest.mark.skip(reason="needs --run-slow")
    skip_llm_real = pytest.mark.skip(reason="needs --run-slow")

    for item in items:
        if not run_integration and item.get_closest_marker("integration") is not None:
            item.add_marker(skip_integration)
        if not run_slow and item.get_closest_marker("slow") is not None:
            item.add_marker(skip_slow)
        if not run_slow and item.get_closest_marker("llm_real") is not None:
            item.add_marker(skip_llm_real)
