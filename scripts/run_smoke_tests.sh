#!/bin/bash
#
# Smoke Test Runner - Infrastructure Connectivity Tests
# 
# This script runs connectivity tests for all infrastructure services.
# Can be run from any machine with network access to the services.
#
# Usage: ./scripts/run_smoke_tests.sh [options]
#
# Options:
#   --verbose, -v     Show detailed output
#   --service NAME    Test only specific service (postgres, redis, qdrant, neo4j, typesense)
#   --summary         Show only the summary
#   --help, -h        Show this help message
#

set -e
set -u
set -o pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Default options
VERBOSE=""
SERVICE=""
SUMMARY_ONLY=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE="-v -s"
            shift
            ;;
        --service)
            SERVICE="$2"
            shift 2
            ;;
        --summary)
            SUMMARY_ONLY="yes"
            shift
            ;;
        -h|--help)
            head -n 15 "$0" | tail -n +3 | sed 's/^# //'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}======================================"
echo "Infrastructure Connectivity Tests"
echo "======================================${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found!${NC}"
    echo "Tests will use default values from .env.example"
    echo ""
fi

PYTEST="$PROJECT_ROOT/.venv/bin/pytest"
if [ ! -f "$PYTEST" ]; then
    echo -e "${RED}Error: Virtual environment not found at $PYTEST${NC}"
    echo "Run: python3 -m venv .venv && .venv/bin/pip install -r requirements-test.txt"
    exit 1
fi

# Determine which tests to run
if [ -n "$SERVICE" ]; then
    echo -e "${YELLOW}Testing service: ${SERVICE}${NC}"
    TEST_ARGS="-k test_${SERVICE} tests/test_connectivity.py"
elif [ -n "$SUMMARY_ONLY" ]; then
    echo -e "${YELLOW}Running summary only${NC}"
    TEST_ARGS="tests/test_connectivity.py::test_all_services_summary"
else
    echo -e "${YELLOW}Testing all services${NC}"
    TEST_ARGS="tests/test_connectivity.py"
fi

echo ""

# Run the tests
echo -e "${BLUE}Running tests...${NC}"
echo ""

if "$PYTEST" $TEST_ARGS $VERBOSE --tb=short --cov=src --cov-fail-under=80; then
    echo ""
    echo -e "${GREEN}======================================"
    echo "✓ All connectivity tests passed!"
    echo "======================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}======================================"
    echo "✗ Some connectivity tests failed"
    echo "======================================${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check .env file has correct credentials"
    echo "  2. Verify services are running:"
    echo "     - PostgreSQL: psql \"\$POSTGRES_URL\" -c 'SELECT 1;'"
    echo "     - Redis: redis-cli -h \$DEV_IP PING"
    echo "     - Qdrant: curl http://\$STG_IP:6333/collections"
    echo "     - Neo4j: Check http://\$STG_IP:7474"
    echo "     - Typesense: curl http://\$STG_IP:8108/health"
    echo "  3. Check network connectivity and firewall rules"
    echo ""
    exit 1
fi
