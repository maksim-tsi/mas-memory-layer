#!/bin/bash
#
# Integration Test Runner for Memory Tier System
# Runs tests that connect to real DBMS instances on skz-dev-lv and skz-stg-lv
#
# Usage:
#   ./scripts/run_memory_integration_tests.sh [test_path]
#
# Examples:
#   ./scripts/run_memory_integration_tests.sh                    # Run all storage integration tests
#   ./scripts/run_memory_integration_tests.sh postgres           # Run only PostgreSQL tests
#   ./scripts/run_memory_integration_tests.sh neo4j              # Run only Neo4j tests
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Memory Tier Integration Tests${NC}"
echo -e "${BLUE}  Testing against real DBMS instances${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Step 1: Check for .env file
echo -e "${YELLOW}[1/5]${NC} Checking for .env file..."
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo ""
    echo "Please create a .env file from .env.example:"
    echo "  cp .env.example .env"
    echo ""
    echo "Then edit .env and add your actual credentials for:"
    echo "  - POSTGRES_PASSWORD (skz-dev-lv)"
    echo "  - NEO4J_PASSWORD (skz-stg-lv)"
    echo "  - TYPESENSE_API_KEY (skz-stg-lv)"
    exit 1
fi
echo -e "${GREEN}✓${NC} .env file found"
echo ""

# Step 2: Load environment variables
echo -e "${YELLOW}[2/5]${NC} Loading environment variables..."
set -a  # Automatically export all variables
source "$PROJECT_ROOT/.env"
set +a
echo -e "${GREEN}✓${NC} Environment variables loaded"
echo ""

# Step 3: Activate virtual environment
echo -e "${YELLOW}[3/5]${NC} Activating virtual environment..."
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo -e "${RED}ERROR: Virtual environment not found at $PROJECT_ROOT/.venv${NC}"
    echo ""
    echo "Please create a virtual environment first:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

source "$PROJECT_ROOT/.venv/bin/activate"
echo -e "${GREEN}✓${NC} Virtual environment activated"
echo ""

# Step 4: Display connection information
echo -e "${YELLOW}[4/5]${NC} Connection configuration:"
echo "  skz-dev-lv (${DEV_IP}):"
echo "    - PostgreSQL: ${POSTGRES_HOST}:${POSTGRES_PORT} (DB: ${POSTGRES_DB})"
echo "    - Redis: ${REDIS_HOST}:${REDIS_PORT}"
echo ""
echo "  skz-stg-lv (${STG_IP}):"
echo "    - Qdrant: ${QDRANT_HOST}:${QDRANT_PORT}"
echo "    - Neo4j: ${NEO4J_HOST}:${NEO4J_BOLT_PORT}"
echo "    - Typesense: ${TYPESENSE_HOST}:${TYPESENSE_PORT}"
echo ""

# Step 5: Run integration tests
echo -e "${YELLOW}[5/5]${NC} Running integration tests..."
echo ""

cd "$PROJECT_ROOT"

# Determine which tests to run based on argument
if [ $# -eq 0 ]; then
    # Run all storage integration tests
    TEST_PATH="tests/storage/ -m integration"
    TEST_DESC="all storage adapter integration tests"
elif [ "$1" == "postgres" ]; then
    TEST_PATH="tests/storage/test_postgres_adapter.py -m integration"
    TEST_DESC="PostgreSQL integration tests"
elif [ "$1" == "redis" ]; then
    TEST_PATH="tests/storage/test_redis_adapter.py -m integration"
    TEST_DESC="Redis integration tests"
elif [ "$1" == "qdrant" ]; then
    TEST_PATH="tests/storage/test_qdrant_adapter.py -m integration"
    TEST_DESC="Qdrant integration tests"
elif [ "$1" == "neo4j" ]; then
    TEST_PATH="tests/storage/test_neo4j_adapter.py -m integration"
    TEST_DESC="Neo4j integration tests"
elif [ "$1" == "typesense" ]; then
    TEST_PATH="tests/storage/test_typesense_adapter.py -m integration"
    TEST_DESC="Typesense integration tests"
else
    TEST_PATH="$1"
    TEST_DESC="tests matching: $1"
fi

echo -e "${BLUE}Running: ${TEST_DESC}${NC}"
echo ""

# Run pytest with integration marker
python -m pytest $TEST_PATH \
    --tb=short \
    --color=yes \
    -v \
    2>&1 | tee integration_test_results.log

# Check exit status
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  ✓ All integration tests passed!${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    echo "Test results saved to: integration_test_results.log"
    exit 0
else
    echo ""
    echo -e "${RED}================================================${NC}"
    echo -e "${RED}  ✗ Some integration tests failed${NC}"
    echo -e "${RED}================================================${NC}"
    echo ""
    echo "Check integration_test_results.log for details"
    exit 1
fi
