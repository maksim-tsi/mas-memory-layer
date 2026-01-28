#!/bin/bash

# Script: run_subset_experiments.sh
# Purpose: Orchestrate GoodAI subset runs with wrapper services and cleanup verification.
# Usage: ./scripts/run_subset_experiments.sh

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
PIP="$PROJECT_ROOT/.venv/bin/pip"
PYTEST="$PROJECT_ROOT/.venv/bin/pytest"
BENCH_VENV="$PROJECT_ROOT/benchmarks/.venv-benchmark"
BENCH_PYTHON="$BENCH_VENV/bin/python"

WRAPPER_LOG_DIR="$PROJECT_ROOT/logs"
BENCH_LOG_DIR="$PROJECT_ROOT/logs"
RESULTS_ROOT="$PROJECT_ROOT/benchmarks/results/goodai_ltm"
BENCH_CONFIG="$PROJECT_ROOT/benchmarks/goodai-ltm-benchmark/configurations/mas_subset_32k.yml"

WRAPPER_PIDS=""
POLL_PIDS=""

function require_file() {
    if [ ! -f "$1" ]; then
        echo -e "${RED}Error: Missing required file $1${NC}"
        exit 1
    fi
}

function check_prerequisites() {
    require_file "$PYTHON"
    require_file "$PYTEST"
    require_file "$BENCH_CONFIG"

    if [ ! -f "$BENCH_PYTHON" ]; then
        echo -e "${RED}Error: GoodAI benchmark venv not found at $BENCH_VENV${NC}"
        echo "Create it and install benchmark requirements before running this script."
        exit 1
    fi
}

function run_wrapper_tests() {
    echo -e "${BLUE}Running wrapper tests...${NC}"
    "$SCRIPT_DIR/run_wrapper_tests.sh"
}

function start_wrapper() {
    agent_type="$1"
    port="$2"
    log_file="$WRAPPER_LOG_DIR/wrapper_${agent_type}.log"

    echo -e "${YELLOW}Starting wrapper ${agent_type} on port ${port}...${NC}"
    "$PYTHON" "$PROJECT_ROOT/src/evaluation/agent_wrapper.py" --agent-type "$agent_type" --port "$port" \
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

function start_polling() {
    agent="$1"
    port="$2"
    output="$BENCH_LOG_DIR/${agent}_memory_timeline.jsonl"
    error_log="$BENCH_LOG_DIR/${agent}_memory_polling_errors.log"

    echo -e "${YELLOW}Starting memory polling for ${agent}...${NC}"
    "$PYTHON" "$SCRIPT_DIR/poll_memory_state.py" \
        --port "$port" \
        --output "$output" \
        --error-log "$error_log" \
        --interval 10 \
        > /dev/null 2>&1 &
    POLL_PIDS="$POLL_PIDS $!"
}

function verify_cleanup() {
    agent="$1"
    port="$2"
    log_file="$BENCH_LOG_DIR/subset_cleanup_${agent}_$(date +%Y%m%d).log"

    sessions_json=$(curl -s "http://localhost:${port}/sessions")
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) sessions=${sessions_json}" >> "$log_file"

    echo "$sessions_json" | grep -q '"sessions":\[\]' 
}

function force_cleanup() {
    agent="$1"
    port="$2"
    log_file="$BENCH_LOG_DIR/subset_cleanup_${agent}_$(date +%Y%m%d).log"

    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) forcing cleanup" >> "$log_file"
    curl -s -X POST "http://localhost:${port}/cleanup_force?session_id=all" >> "$log_file"
    echo "" >> "$log_file"
}

function run_benchmark() {
    agent_name="$1"
    echo -e "${BLUE}Running benchmark for ${agent_name}...${NC}"
    "$BENCH_PYTHON" "$PROJECT_ROOT/benchmarks/goodai-ltm-benchmark/runner/run_benchmark.py" -a "$agent_name" -c "$BENCH_CONFIG"
}

function copy_results() {
    timestamp=$(date +%Y%m%d)
    dest="$RESULTS_ROOT/subset_baseline_${timestamp}"
    mkdir -p "$dest"
    cp -r "$PROJECT_ROOT/benchmarks/goodai-ltm-benchmark/data/tests"/prospective_memory/results/mas-* "$dest" 2>/dev/null || true
    cp -r "$PROJECT_ROOT/benchmarks/goodai-ltm-benchmark/data/tests"/restaurant/results/mas-* "$dest" 2>/dev/null || true
    mkdir -p "$dest/logs"
    cp "$BENCH_LOG_DIR"/mas_*_memory_timeline.jsonl "$dest/logs" 2>/dev/null || true
    cp "$BENCH_LOG_DIR"/subset_cleanup_* "$dest/logs" 2>/dev/null || true

    echo -e "${GREEN}Results copied to ${dest}${NC}"
}

function shutdown_all() {
    if [ -n "$POLL_PIDS" ]; then
        for pid in $POLL_PIDS; do
            kill "$pid" >/dev/null 2>&1 || true
        done
    fi

    if [ -n "$WRAPPER_PIDS" ]; then
        for pid in $WRAPPER_PIDS; do
            kill "$pid" >/dev/null 2>&1 || true
        done
    fi
}

function main() {
    check_prerequisites
    mkdir -p "$WRAPPER_LOG_DIR" "$BENCH_LOG_DIR" "$RESULTS_ROOT"

    run_wrapper_tests

    start_wrapper "full" 8080
    start_wrapper "rag" 8081
    start_wrapper "full_context" 8082

    wait_for_health "full" 8080
    wait_for_health "rag" 8081
    wait_for_health "full_context" 8082

    start_polling "mas_full" 8080
    start_polling "mas_rag" 8081
    start_polling "mas_full_context" 8082

    for agent in mas-full mas-rag mas-full-context; do
        case "$agent" in
            mas-full)
                port=8080
                ;;
            mas-rag)
                port=8081
                ;;
            mas-full-context)
                port=8082
                ;;
        esac

        run_benchmark "$agent"

        if ! verify_cleanup "$agent" "$port"; then
            echo -e "${YELLOW}Cleanup needed for ${agent}. Forcing cleanup...${NC}"
            force_cleanup "$agent" "$port"
        else
            echo -e "${GREEN}Cleanup verified for ${agent}.${NC}"
        fi
    done

    copy_results

    echo -e "${GREEN}Subset benchmark run complete.${NC}"
}

trap shutdown_all EXIT

main "$@"
