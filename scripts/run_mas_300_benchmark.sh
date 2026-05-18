#!/bin/bash

# Script: run_mas_300_benchmark.sh
# Purpose: Automate the execution of the MAS benchmark for 4 agents:
#   1. mas-full
#   2. mas-rag
#   3. mas-full-context
#   4. gemini (Naive LLM)
#
# Pre-requisites:
#   - Wrapper services must be running (this script will attempt to start them)
#   - Google Cloud credentials must be set in .env
#
# Usage: ./scripts/run_mas_300_benchmark.sh [--dry-run]

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
BENCHMARK_DIR="${GOODAI_BENCHMARK_DIR:-$PROJECT_ROOT/../goodai-ltm-benchmark-yaam}"

cd "$PROJECT_ROOT"

# Default configuration
CONFIG_FILE="configurations/mas_300_run.yml"
DRY_RUN=false

# Check for dry-run argument
for arg in "$@"; do
    if [ "$arg" == "--dry-run" ]; then
        CONFIG_FILE="configurations/mas_dry_run_5.yml"
        DRY_RUN=true
        echo -e "${YELLOW}Running in DRY-RUN mode with configuration: $CONFIG_FILE${NC}"
        break
    fi
done

LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RUN_LOG="$LOG_DIR/run_mas_benchmark_$TIMESTAMP.log"

# Function to log message to console and file
log() {
    echo -e "$1" | tee -a "$RUN_LOG"
}

log "${BLUE}=== Starting MAS Benchmark Automation ===${NC}"
log "Configuration: $CONFIG_FILE"
log "Log File: $RUN_LOG"

# 1. Pre-flight Checks
log "\n${YELLOW}--- 1. Pre-flight Checks ---${NC}"

# Check .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    . "$PROJECT_ROOT/.env"
    set +a
    log "${GREEN}Loaded .env file.${NC}"
else
    log "${RED}Error: .env file not found in project root.${NC}"
    exit 1
fi

# Check Google Credentials
log "Checking Gemini Connectivity..."
PYTHON_VENV="$PROJECT_ROOT/.venv/bin/python"
if [ ! -f "$PYTHON_VENV" ]; then
    log "${RED}Error: Virtual environment python not found at $PYTHON_VENV${NC}"
    exit 1
fi

if "$PYTHON_VENV" "$PROJECT_ROOT/scripts/test_gemini_flash_lite.py" >> "$RUN_LOG" 2>&1; then
    log "${GREEN}Gemini connectivity test PASSED.${NC}"
else
    log "${RED}Gemini connectivity test FAILED. Check logs.${NC}"
    exit 1
fi

# Run Smoke Tests
log "Running Infrastructure Smoke Tests..."
if "$PYTHON_VENV" -m pytest tests/test_connectivity.py::test_all_services_summary --tb=short >> "$RUN_LOG" 2>&1; then
    log "${GREEN}Infrastructure smoke tests PASSED.${NC}"
else
    log "${RED}Infrastructure smoke tests FAILED. Check logs.${NC}"
    exit 1
fi

# 2. Wrapper Management
log "\n${YELLOW}--- 2. Wrapper Management ---${NC}"

# Check if wrappers are running, start if not
start_wrappers=false
for port in 8080 8081 8082; do
    if ! lsof -i:$port -t >/dev/null; then
        start_wrappers=true
        break
    fi
done

if [ "$start_wrappers" = true ]; then
    log "Starting wrapper services..."
    "$PROJECT_ROOT/scripts/start_benchmark_wrappers.sh" &
    
    # Wait for wrappers to be healthy (simple wait for now, script handles health check)
    sleep 10
else
    log "${GREEN}Wrapper services appear to be running.${NC}"
fi

# 3. Benchmark Execution
log "\n${YELLOW}--- 3. Benchmark Execution ---${NC}"

AGENTS=("mas-full" "mas-rag" "mas-full-context" "gemini")
PYTHON_BENCH="$BENCHMARK_DIR/.venv/bin/python"

if [ ! -f "$PYTHON_BENCH" ]; then
    log "${RED}Error: Benchmark virtual environment python not found at $PYTHON_BENCH${NC}"
    log "Set GOODAI_BENCHMARK_DIR to the external benchmark checkout, then run poetry install there."
    exit 1
fi

export MAS_WRAPPER_TIMEOUT=600  # Increase timeout for MAS wrappers
export PYTHONPATH="$BENCHMARK_DIR:${PYTHONPATH:-}"

# AGENTS=("mas-full" "mas-rag" "mas-full-context" "gemini")
AGENTS=("mas-full" "mas-rag" "mas-full-context" "gemini")

for agent in "${AGENTS[@]}"; do
    log "Starting run for agent: ${BLUE}$agent${NC}"
    
    # Construct run name
    if [ "$DRY_RUN" = true ]; then
        RUN_NAME_ARG="MAS Dry Run 5 - $agent - $TIMESTAMP"
    else
        RUN_NAME_ARG="MAS 300 Run - $agent - $TIMESTAMP"
    fi

    # Execute benchmark
    set +e # Don't exit on failure of one agent
    "$PYTHON_BENCH" "$BENCHMARK_DIR/runner/run_benchmark.py" \
        --configuration "$CONFIG_FILE" \
        --agent-name "$agent" \
        --run-name "$RUN_NAME_ARG" \
        -y >> "$RUN_LOG" 2>&1
    
    EXIT_CODE=$?
    set -e

    if [ $EXIT_CODE -eq 0 ]; then
        log "${GREEN}Run for $agent COMPLETED successfully.${NC}"
    else
        log "${RED}Run for $agent FAILED with exit code $EXIT_CODE. Check logs.${NC}"
    fi
    
    # Small pause between runs
    sleep 5
done

log "\n${GREEN}=== Automation Completed ===${NC}"
log "Summary logs available at: $RUN_LOG"
