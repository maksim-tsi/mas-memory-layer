#!/bin/bash
# Run Redis adapter tests with proper environment setup

set -e
set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

PYTEST="${PROJECT_ROOT}/.venv/bin/pytest"
if [ ! -f "$PYTEST" ]; then
    echo "Virtual environment not found at $PYTEST"
    echo "Run: python3 -m venv .venv && .venv/bin/pip install -r requirements-test.txt"
    exit 1
fi

# Run tests
echo "Running Redis adapter tests..."
"$PYTEST" tests/storage/test_redis_adapter.py "$@" --cov=src --cov-fail-under=80
