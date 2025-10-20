#!/bin/bash
# Run Redis adapter tests with proper environment setup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Use venv Python if available
PYTHON="${PROJECT_ROOT}/.venv/bin/python"
if [ ! -f "$PYTHON" ]; then
    echo "Virtual environment not found. Using system Python."
    PYTHON="python3"
fi

# Run tests
echo "Running Redis adapter tests..."
"$PYTHON" -m pytest tests/storage/test_redis_adapter.py "$@"
