#!/bin/bash

# Script: run_prospective_validation.sh
# Purpose: Validate Intelligent Instruction Handling with 2 Prospective Memory questions.
# Agents: mas-full, mas-rag, mas-full-context
# Usage: ./scripts/run_prospective_validation.sh

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
BENCH_ROOT="${GOODAI_BENCHMARK_DIR:-$PROJECT_ROOT/../goodai-ltm-benchmark-yaam}"

cd "$PROJECT_ROOT"

# MAS Memory Layer venv
PYTHON="$PROJECT_ROOT/.venv/bin/python"

# GoodAI Benchmark venv
BENCH_VENV="$BENCH_ROOT/.venv"
BENCH_PYTHON="$BENCH_VENV/bin/python"

WRAPPER_LOG_DIR="$PROJECT_ROOT/logs"
BENCH_LOG_DIR="$PROJECT_ROOT/logs"
RESULTS_ROOT="$PROJECT_ROOT/benchmarks/results/validation_prospective_2"
BENCH_CONFIG="$BENCH_ROOT/configurations/mas_prospective_2.yml"

ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    . "$ENV_FILE"
    set +a
fi

PYTHONPATH="$PROJECT_ROOT:$BENCH_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH

WRAPPER_PIDS=""

function require_file() {
    if [ ! -f "$1" ]; then
        echo -e "${RED}Error: Missing required file $1${NC}"
        exit 1
    fi
}

function cleanup_existing_wrappers() {
    echo -e "${YELLOW}Cleaning up any existing wrappers...${NC}"
    pkill -f "agent_wrapper.py" || true
    sleep 2
}

function start_wrapper() {
    agent_type="$1"
    port="$2"
    log_file="$WRAPPER_LOG_DIR/wrapper_${agent_type}.log"

    echo -e "${YELLOW}Starting wrapper ${agent_type} on port ${port}...${NC}"
    PYTHONPATH="$PROJECT_ROOT" "$PYTHON" "$PROJECT_ROOT/src/evaluation/agent_wrapper.py" --agent-type "$agent_type" --port "$port" \
        > "$log_file" 2>&1 &
    WRAPPER_PIDS="$WRAPPER_PIDS $!"
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

function run_benchmark() {
    agent_name="$1"
    echo -e "${BLUE}Running benchmark for ${agent_name}...${NC}"
    PYTHONPATH="$BENCH_ROOT" \
        "$BENCH_PYTHON" "$BENCH_ROOT/runner/run_benchmark.py" -a "$agent_name" -c "$BENCH_CONFIG"
}

function cleanup_mas_memory() {
    agent="$1"
    port="$2"
    echo -e "${YELLOW}Forcing memory cleanup for ${agent}...${NC}"
    curl -s -X POST "http://localhost:${port}/cleanup_force?session_id=all" > /dev/null
}

function shutdown_all() {
    if [ -n "$WRAPPER_PIDS" ]; then
        echo -e "${BLUE}Stopping wrappers...${NC}"
        pkill -P $$ || true # Kill child processes
        for pid in $WRAPPER_PIDS; do
            kill "$pid" >/dev/null 2>&1 || true
        done
    fi
}

function copy_results() {
    mkdir -p "$RESULTS_ROOT"
    # Copy results for all agents
    cp -r "$BENCH_ROOT/data/tests"/prospective_memory/results/* "$RESULTS_ROOT" 2>/dev/null || true
    echo -e "${GREEN}Results copied to ${RESULTS_ROOT}${NC}"
}

function main() {
    require_file "$PYTHON"
    require_file "$BENCH_PYTHON"
    require_file "$BENCH_CONFIG"
    mkdir -p "$WRAPPER_LOG_DIR" "$BENCH_LOG_DIR" "$RESULTS_ROOT"

    cleanup_existing_wrappers

    # Start Wrappers for MAS Agents
    start_wrapper "full" 8080
    start_wrapper "rag" 8081
    start_wrapper "full_context" 8082

    wait_for_health "full" 8080
    wait_for_health "rag" 8081
    wait_for_health "full_context" 8082

    # Run Benchmark for each agent
    # Skipping Gemini baseline to save time

    # 1. MAS Full
    cleanup_mas_memory "mas-full" 8080
    run_benchmark "mas-full"

    # 2. MAS RAG
    # cleanup_mas_memory "mas-rag" 8081
    # run_benchmark "mas-rag"

    # 3. MAS Full Context
    # cleanup_mas_memory "mas-full-context" 8082
    # run_benchmark "mas-full-context"

    copy_results
    echo -e "${GREEN}Validation run complete.${NC}"
}

trap shutdown_all EXIT

main "$@"
