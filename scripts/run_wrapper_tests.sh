#!/bin/bash

# Script: run_wrapper_tests.sh
# Purpose: Run wrapper unit and integration tests with separate reports.
# Usage: ./scripts/run_wrapper_tests.sh

set -e
set -u
set -o pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

PYTEST="$PROJECT_ROOT/.venv/bin/pytest"

if [ ! -f "$PYTEST" ]; then
    echo -e "${RED}Error: Virtual environment not found at $PROJECT_ROOT/.venv${NC}"
    echo "Run: python3 -m venv $PROJECT_ROOT/.venv && $PROJECT_ROOT/.venv/bin/pip install -r requirements-test.txt"
    exit 1
fi

UNIT_REPORT_DIR="$PROJECT_ROOT/tests/reports/unit"
INTEGRATION_REPORT_DIR="$PROJECT_ROOT/tests/reports/integration"

mkdir -p "$UNIT_REPORT_DIR" "$INTEGRATION_REPORT_DIR"

if [ ! -f "$PROJECT_ROOT/tests/reports/.gitkeep" ]; then
    touch "$PROJECT_ROOT/tests/reports/.gitkeep"
fi
if [ ! -f "$UNIT_REPORT_DIR/.gitkeep" ]; then
    touch "$UNIT_REPORT_DIR/.gitkeep"
fi
if [ ! -f "$INTEGRATION_REPORT_DIR/.gitkeep" ]; then
    touch "$INTEGRATION_REPORT_DIR/.gitkeep"
fi

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
UNIT_XML="$UNIT_REPORT_DIR/wrapper_unit_${TIMESTAMP}.xml"
UNIT_HTML="$UNIT_REPORT_DIR/wrapper_unit_${TIMESTAMP}.html"
INTEGRATION_XML="$INTEGRATION_REPORT_DIR/wrapper_integration_${TIMESTAMP}.xml"
INTEGRATION_HTML="$INTEGRATION_REPORT_DIR/wrapper_integration_${TIMESTAMP}.html"

echo -e "${YELLOW}Running wrapper unit tests...${NC}"
"$PYTEST" tests/evaluation/ -m unit -v \
    --junit-xml="$UNIT_XML" \
    --html="$UNIT_HTML" \
    --self-contained-html \
    --cov=src \
    --cov-fail-under=80

echo -e "${YELLOW}Running wrapper integration tests...${NC}"
"$PYTEST" tests/integration/test_wrapper_agents_integration.py -m integration -v \
    --junit-xml="$INTEGRATION_XML" \
    --html="$INTEGRATION_HTML" \
    --self-contained-html \
    --cov=src \
    --cov-fail-under=80

echo -e "${GREEN}✅ Wrapper tests complete.${NC}"
echo "Unit reports: $UNIT_XML, $UNIT_HTML"
echo "Integration reports: $INTEGRATION_XML, $INTEGRATION_HTML"
