#!/bin/bash

# Script: start_benchmark_wrappers.sh
# Purpose: Start wrapper services for GoodAI benchmark runs (no tests).
# Usage: ./scripts/start_benchmark_wrappers.sh

set -e
set -u
set -o pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

PYTHON="$PROJECT_ROOT/.venv/bin/python"
WRAPPER_LOG_DIR="$PROJECT_ROOT/logs"
ENV_FILE="$PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    set -a
    . "$ENV_FILE"
    set +a
fi

PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH

WRAPPER_PIDS=""

function start_wrapper() {
    agent_type="$1"
    port="$2"
    log_file="$WRAPPER_LOG_DIR/wrapper_${agent_type}.log"

    echo -e "${YELLOW}Starting wrapper ${agent_type} on port ${port}...${NC}"
    PYTHONPATH="$PROJECT_ROOT" "$PYTHON" "$PROJECT_ROOT/src/evaluation/agent_wrapper.py" \
        --agent-type "$agent_type" --port "$port" \
        > "$log_file" 2>&1 &
    pid=$!
    WRAPPER_PIDS="$WRAPPER_PIDS $pid"
    echo -e "${BLUE}  PID: $pid${NC}"
}

function wait_for_health() {
    agent="$1"
    port="$2"
    timeout=60
    elapsed=0

    echo -e "${YELLOW}Waiting for ${agent} health check...${NC}"
    while [ $elapsed -lt $timeout ]; do
        if curl -s "http://localhost:${port}/health" | grep -q '"status":"ok"'; then
            echo -e "${GREEN}${agent} healthy.${NC}"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    echo -e "${RED}Timeout waiting for ${agent} health.${NC}"
    return 1
}

function shutdown_all() {
    if [ -n "$WRAPPER_PIDS" ]; then
        echo -e "${YELLOW}Shutting down wrappers...${NC}"
        for pid in $WRAPPER_PIDS; do
            kill "$pid" >/dev/null 2>&1 || true
        done
    fi
}

function main() {
    mkdir -p "$WRAPPER_LOG_DIR"

    echo -e "${BLUE}=== Starting MAS Benchmark Wrappers ===${NC}"

    start_wrapper "full" 8080
    start_wrapper "rag" 8081
    start_wrapper "full_context" 8082

    echo ""
    echo -e "${YELLOW}Waiting for health checks...${NC}"
    
    wait_for_health "mas-full" 8080
    wait_for_health "mas-rag" 8081
    wait_for_health "mas-full-context" 8082

    echo ""
    echo -e "${GREEN}✅ All wrappers started successfully!${NC}"
    echo ""
    echo -e "${BLUE}Wrapper endpoints:${NC}"
    echo "  mas-full:         http://localhost:8080"
    echo "  mas-rag:          http://localhost:8081"
    echo "  mas-full-context: http://localhost:8082"
    echo ""
    echo -e "${BLUE}Logs:${NC}"
    echo "  ${WRAPPER_LOG_DIR}/wrapper_full.log"
    echo "  ${WRAPPER_LOG_DIR}/wrapper_rag.log"
    echo "  ${WRAPPER_LOG_DIR}/wrapper_full_context.log"
    echo ""
    echo -e "${YELLOW}Wrappers running. Press Ctrl+C to stop.${NC}"
    
    # Wait indefinitely
    wait
}

trap shutdown_all EXIT

main "$@"
