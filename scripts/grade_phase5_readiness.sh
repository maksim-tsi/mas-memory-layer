#!/bin/bash
# Script: grade_phase5_readiness.sh
# Purpose: Orchestrate Phase 5 readiness checks (lint, unit/mocked, optional real integrations/benchmarks) and emit a summary.
# Usage: ./scripts/grade_phase5_readiness.sh [--mode fast|full] [--bench] [--skip-llm]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

PYTHON="$PROJECT_ROOT/.venv/bin/python"
PYTEST="$PROJECT_ROOT/.venv/bin/pytest"
RUFF="$PROJECT_ROOT/.venv/bin/ruff"

MODE="fast"          # fast: lint + unit/mocked; full: lint + unit + integration (real backends if env present)
RUN_BENCH=0
SKIP_LLM=0
SUMMARY_OUT=""

usage() {
    echo "Usage: $0 [--mode fast|full] [--bench] [--skip-llm]"
    echo "  --mode fast|full   Select scope (default: fast)"
    echo "  --bench            Run optional benchmarks (requires real backends)"
    echo "  --skip-llm         Skip real LLM/provider checks even if GOOGLE_API_KEY is set"
    echo "  -h, --help         Show this help"
    exit 0
}

have_cmd() { command -v "$1" >/dev/null 2>&1; }

ensure_prereqs() {
    if [ ! -x "$PYTHON" ] || [ ! -x "$PYTEST" ]; then
        echo "Virtual environment executables not found at $PROJECT_ROOT/.venv/bin."
        echo "Create the venv first: python3 -m venv .venv"
        exit 1
    fi
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --mode)
                MODE="${2:-}"
                shift 2
                ;;
            --bench)
                RUN_BENCH=1
                shift 1
                ;;
            --skip-llm)
                SKIP_LLM=1
                shift 1
                ;;
            --summary-out)
                SUMMARY_OUT="${2:-}"
                shift 2
                ;;
            -h|--help)
                usage
                ;;
            *)
                echo "Unknown option: $1"
                usage
                ;;
        esac
    done
}

run_lint() {
    if [ -x "$RUFF" ]; then
        echo "[lint] running ruff check"
        "$RUFF" check .
    else
        echo "[lint] ruff not installed; skipping"
    fi
}

run_unit_suite() {
    echo "[tests] running unit/mocked suite"
    "$PYTEST" tests -v -m "not integration and not llm_real"
}

run_integration_suite() {
    echo "[tests] running integration suite"
    "$PYTEST" tests/integration -v -m "integration"
}

run_real_llm_suite() {
    if [ "$SKIP_LLM" -eq 1 ]; then
        echo "[tests] skipping real LLM/provider checks (skip-llm set)"
        return 0
    fi
    if [ -z "${GOOGLE_API_KEY:-}" ]; then
        echo "[tests] GOOGLE_API_KEY not set; skipping real LLM/provider checks"
        return 0
    fi
    echo "[tests] running real LLM/provider checks"
    "$PYTEST" tests -v -m "llm_real"
}

run_benchmarks() {
    if [ "$RUN_BENCH" -ne 1 ]; then
        return 0
    fi
    echo "[bench] running benchmarks (requires real backends configured)"
    "$PYTHON" scripts/run_storage_benchmark.py run --size 10000
}

emit_summary() {
    if [ ! -x "$PYTHON" ]; then
        echo "[summary] python unavailable; skipping summary emission"
        return 0
    fi
    if [ -n "$SUMMARY_OUT" ]; then
        "$PYTHON" "$SCRIPT_DIR/grade_phase5_readiness.py" --output "$SUMMARY_OUT"
    else
        "$PYTHON" "$SCRIPT_DIR/grade_phase5_readiness.py"
    fi
}

main() {
    parse_args "$@"
    ensure_prereqs

    run_lint
    run_unit_suite

    if [ "$MODE" = "full" ]; then
        run_integration_suite
        run_real_llm_suite
        run_benchmarks
    fi

    emit_summary
}

main "$@"