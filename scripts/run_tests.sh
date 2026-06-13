#!/bin/bash

# Test Runner Script
# Runs all tests with proper environment setup

set -e
set -u
set -o pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Define virtual environment executables
PYTEST="$PROJECT_ROOT/.venv/bin/pytest"

if [ ! -f "$PYTEST" ]; then
    echo -e "${RED}❌ Error: Virtual environment not found at $PYTEST${NC}"
    echo "Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Run tests with pytest (python-dotenv in conftest.py will handle .env file loading)
echo -e "${BLUE}ℹ️  Running test suite...${NC}"
"$PYTEST" "${@:-tests/}" -v --cov=src --cov-fail-under=80

echo -e "${GREEN}✅ Test run complete${NC}"
