#!/bin/bash
#
# Infrastructure Connectivity Verification Script
# Verifies all DBMS services are accessible before running tests
#
# Usage: ./scripts/verify_infrastructure.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Infrastructure Connectivity Verification${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Load environment variables
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo "Please copy .env.example to .env and configure credentials"
    exit 1
fi

set -a
source "$PROJECT_ROOT/.env"
set +a

echo -e "${YELLOW}Testing connectivity to all services...${NC}"
echo ""

# Track failures
FAILED=0

# PostgreSQL (skz-dev-lv)
echo -n "PostgreSQL (${POSTGRES_HOST}:${POSTGRES_PORT})... "
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/${POSTGRES_HOST}/${POSTGRES_PORT}" 2>/dev/null; then
    echo -e "${GREEN}✓ Reachable${NC}"
else
    echo -e "${RED}✗ Unreachable${NC}"
    FAILED=$((FAILED + 1))
fi

# Redis (skz-dev-lv)
echo -n "Redis (${REDIS_HOST}:${REDIS_PORT})... "
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/${REDIS_HOST}/${REDIS_PORT}" 2>/dev/null; then
    echo -e "${GREEN}✓ Reachable${NC}"
else
    echo -e "${RED}✗ Unreachable${NC}"
    FAILED=$((FAILED + 1))
fi

# Qdrant (skz-stg-lv)
echo -n "Qdrant (${QDRANT_HOST}:${QDRANT_PORT})... "
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/${QDRANT_HOST}/${QDRANT_PORT}" 2>/dev/null; then
    if command -v curl &> /dev/null; then
        if curl -s -f "${QDRANT_URL}/collections" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Reachable & Responding${NC}"
        else
            echo -e "${YELLOW}✓ Reachable${NC}"
        fi
    else
        echo -e "${GREEN}✓ Reachable${NC}"
    fi
else
    echo -e "${RED}✗ Unreachable${NC}"
    FAILED=$((FAILED + 1))
fi

# Neo4j (skz-stg-lv)
echo -n "Neo4j Bolt (${NEO4J_HOST}:${NEO4J_BOLT_PORT})... "
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/${NEO4J_HOST}/${NEO4J_BOLT_PORT}" 2>/dev/null; then
    echo -e "${GREEN}✓ Reachable${NC}"
else
    echo -e "${RED}✗ Unreachable${NC}"
    FAILED=$((FAILED + 1))
fi

echo -n "Neo4j HTTP (${NEO4J_HOST}:${NEO4J_HTTP_PORT})... "
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/${NEO4J_HOST}/${NEO4J_HTTP_PORT}" 2>/dev/null; then
    echo -e "${GREEN}✓ Reachable${NC}"
else
    echo -e "${RED}✗ Unreachable${NC}"
    FAILED=$((FAILED + 1))
fi

# Typesense (skz-stg-lv)
echo -n "Typesense (${TYPESENSE_HOST}:${TYPESENSE_PORT})... "
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/${TYPESENSE_HOST}/${TYPESENSE_PORT}" 2>/dev/null; then
    if command -v curl &> /dev/null; then
        if curl -s -f "${TYPESENSE_URL}/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Reachable & Healthy${NC}"
        else
            echo -e "${YELLOW}✓ Reachable${NC}"
        fi
    else
        echo -e "${GREEN}✓ Reachable${NC}"
    fi
else
    echo -e "${RED}✗ Unreachable${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""

# Summary
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  ✓ All services are reachable!${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    echo "You can now run integration tests:"
    echo "  ./scripts/run_memory_integration_tests.sh"
    exit 0
else
    echo -e "${RED}================================================${NC}"
    echo -e "${RED}  ✗ $FAILED service(s) unreachable${NC}"
    echo -e "${RED}================================================${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo "  1. Verify services are running on respective nodes"
    echo "  2. Check firewall rules (ufw status)"
    echo "  3. Verify network connectivity between nodes"
    echo "  4. See docs/IAC/INFRASTRUCTURE_ACCESS_GUIDE.md"
    exit 1
fi
