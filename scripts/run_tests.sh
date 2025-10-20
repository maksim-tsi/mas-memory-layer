#!/bin/bash

# Test Runner Script
# Runs all tests with proper environment setup

set -e

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found. Run setup first."
    exit 1
fi

# Run tests with pytest
# python-dotenv in conftest.py will handle .env file loading
echo "Running test suite..."
pytest "${@:-tests/}" -v

echo "✅ Test run complete"
